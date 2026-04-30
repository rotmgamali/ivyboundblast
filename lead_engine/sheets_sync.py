"""
Batch sync verified contacts from SQLite to Google Sheets.
Reuses existing sheets_integration.py for auth and API.

Two modes:
    1. sync_run(run_id, db, sheet_name)  → sync to a top-level spreadsheet
    2. sync_run_to_tab(run_id, db, parent_sheet, tab_name) → sync to a tab
       inside an existing spreadsheet (workaround for service-account
       Drive quota limits)
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lead_engine.db import HarvestDB

logger = logging.getLogger("lead_engine.sheets_sync")


# Default tab inside the Ivy Bound spreadsheet that holds Bahamas leads.
# This works around the service-account Drive quota issue: instead of creating
# a new spreadsheet, we add a worksheet (tab) inside an existing spreadsheet.
DEFAULT_PARENT_SPREADSHEET = "Ivy Bound - Campaign Leads"
BAHAMAS_TAB_NAME = "Bahamas Retreat - Leads"


def _get_parent_spreadsheet(parent_name: str):
    """Open and return the parent spreadsheet object."""
    from sheets_integration import GoogleSheetsClient
    client = GoogleSheetsClient(input_sheet_name=parent_name)
    client.setup_sheets()
    return client.input_sheet  # The Spreadsheet object


def _ensure_tab(spreadsheet, tab_name: str, headers: list):
    """Get or create a tab with the given headers."""
    existing = {ws.title: ws for ws in spreadsheet.worksheets()}
    if tab_name in existing:
        return existing[tab_name]
    ws = spreadsheet.add_worksheet(title=tab_name, rows=10000, cols=max(25, len(headers)))
    ws.update(values=[headers], range_name="A1")
    return ws


def sync_run_to_tab(run_id: int, db: HarvestDB,
                     parent_spreadsheet: str = DEFAULT_PARENT_SPREADSHEET,
                     tab_name: str = BAHAMAS_TAB_NAME) -> int:
    """Sync verified contacts from a run to a TAB inside an existing
    spreadsheet. Avoids creating new top-level files (service account
    Drive quota workaround)."""
    stats = db.get_run_stats(run_id)
    if not stats:
        logger.error(f"Run {run_id} not found")
        return 0

    try:
        ss = _get_parent_spreadsheet(parent_spreadsheet)
    except Exception as e:
        logger.error(f"Failed to open parent spreadsheet '{parent_spreadsheet}': {e}")
        return 0

    headers = ["email", "first_name", "last_name", "role", "school_name", "domain",
               "state", "city", "phone", "status", "email_1_sent_at", "email_2_sent_at",
               "sender_email", "notes", "school_type", "custom_data"]
    try:
        ws = _ensure_tab(ss, tab_name, headers)
    except Exception as e:
        logger.error(f"Failed to ensure tab '{tab_name}': {e}")
        return 0

    total_synced = 0
    while True:
        contacts = db.get_unsynced_contacts(run_id, limit=50)
        if not contacts:
            break

        # Build deduped list (skip emails already in the sheet)
        try:
            existing_emails = set(e.lower() for e in ws.col_values(1)[1:] if e)
        except Exception:
            existing_emails = set()

        rows = []
        contact_ids = []
        for c in contacts:
            email = (c.get("email") or "").lower().strip()
            if not email or email in existing_emails:
                # Mark as synced so we don't keep retrying
                contact_ids.append(c["id"])
                continue
            existing_emails.add(email)
            rows.append([
                email, c.get("first_name", ""), c.get("last_name", ""),
                c.get("title", ""), c.get("business_name", ""),
                c.get("website", ""), c.get("state", ""), c.get("city", ""),
                c.get("business_phone", ""), "pending", "", "", "",
                f"Bahamas scrape | verified={c.get('email_status', 'unknown')} | catchall={bool(c.get('is_catch_all'))}",
                c.get("category", ""), "",
            ])
            contact_ids.append(c["id"])

        if rows:
            try:
                ws.append_rows(rows, value_input_option="RAW")
                total_synced += len(rows)
                logger.info(f"Synced {len(rows)} new contacts to tab '{tab_name}' ({total_synced} total)")
            except Exception as e:
                logger.error(f"Append rows failed: {e}")
                break

        # Mark as synced even if dupes — prevents re-attempts
        if contact_ids:
            db.mark_synced(contact_ids, f"{parent_spreadsheet}::{tab_name}")

    return total_synced


def sync_run(run_id: int, db: HarvestDB, sheet_name: str = None) -> int:
    """Sync run to Google Sheets.

    For "executives" niche, syncs to the Bahamas tab inside the Ivy Bound
    spreadsheet (Drive quota workaround). For other niches, syncs to a
    standalone spreadsheet by name.
    """
    stats = db.get_run_stats(run_id)
    if not stats:
        logger.error(f"Run {run_id} not found")
        return 0

    niche = stats["niche"].lower().strip()

    # Bahamas (executives) uses the tab approach
    if niche == "executives":
        tab_name = sheet_name or BAHAMAS_TAB_NAME
        return sync_run_to_tab(run_id, db, DEFAULT_PARENT_SPREADSHEET, tab_name)

    # Original flow for other niches
    try:
        from sheets_integration import GoogleSheetsClient
    except ImportError:
        logger.error("Could not import GoogleSheetsClient")
        return 0

    default_sheet = sheet_name or f"Harvest - {stats['niche']}"
    try:
        sheets = GoogleSheetsClient(input_sheet_name=default_sheet)
        sheets.setup_sheets()
    except Exception as e:
        logger.error(f"Sheets setup failed: {e}")
        return 0

    total_synced = 0
    while True:
        contacts = db.get_unsynced_contacts(run_id, limit=50)
        if not contacts:
            break

        batch = []
        contact_ids = []
        for c in contacts:
            batch.append({
                "email": c["email"],
                "first_name": c.get("first_name", ""),
                "last_name": c.get("last_name", ""),
                "role": c.get("title", ""),
                "school_name": c.get("business_name", ""),
                "domain": c.get("website", ""),
                "city": c.get("city", ""),
                "state": c.get("state", ""),
                "phone": c.get("business_phone", ""),
                "status": "pending",
                "email_verified": c.get("email_status", "unknown"),
                "school_type": c.get("category", ""),
            })
            contact_ids.append(c["id"])

        try:
            sheets.add_leads_batch(batch)
            db.mark_synced(contact_ids, default_sheet)
            total_synced += len(batch)
            logger.info(f"Synced batch of {len(batch)} ({total_synced} total)")
        except Exception as e:
            logger.error(f"Sheets sync batch failed: {e}")
            break

    return total_synced
