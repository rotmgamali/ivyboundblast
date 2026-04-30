"""
Thread-safe SQLite database layer for the lead generation engine.
Uses WAL mode for concurrent reads from 10 worker threads.
"""
import sqlite3
import threading
import csv
import os
from datetime import datetime
from typing import List, Dict, Optional


class HarvestDB:
    def __init__(self, db_path: str = "harvest.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                niche TEXT NOT NULL,
                cities TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                total_businesses INTEGER DEFAULT 0,
                total_contacts INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running'
            );

            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                niche TEXT,
                category TEXT,
                website TEXT,
                phone TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, city, state),
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL,
                email TEXT UNIQUE,
                first_name TEXT,
                last_name TEXT,
                title TEXT,
                seniority_score INTEGER DEFAULT 0,
                email_status TEXT DEFAULT 'unknown',
                mx_host TEXT,
                is_catch_all BOOLEAN DEFAULT 0,
                verified_at TIMESTAMP,
                FOREIGN KEY (business_id) REFERENCES businesses(id)
            );

            CREATE TABLE IF NOT EXISTS sheets_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                sheet_name TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_contacts_email_status ON contacts(email_status);
            CREATE INDEX IF NOT EXISTS idx_contacts_business ON contacts(business_id);
            CREATE INDEX IF NOT EXISTS idx_businesses_run ON businesses(run_id);
        """)
        conn.commit()

    def create_run(self, niche: str, cities: str) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO runs (niche, cities) VALUES (?, ?)",
            (niche, cities)
        )
        conn.commit()
        return cursor.lastrowid

    def complete_run(self, run_id: int):
        conn = self._get_conn()
        # Count totals
        biz_count = conn.execute(
            "SELECT COUNT(*) FROM businesses WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        contact_count = conn.execute(
            "SELECT COUNT(*) FROM contacts c JOIN businesses b ON c.business_id = b.id WHERE b.run_id = ?",
            (run_id,)
        ).fetchone()[0]
        conn.execute(
            "UPDATE runs SET completed_at = CURRENT_TIMESTAMP, total_businesses = ?, total_contacts = ?, status = 'completed' WHERE id = ?",
            (biz_count, contact_count, run_id)
        )
        conn.commit()

    def insert_business(self, run_id: int, data: Dict) -> Optional[int]:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO businesses
                   (run_id, name, niche, category, website, phone, address, city, state)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, data.get("name", ""), data.get("niche", ""),
                 data.get("category", ""), data.get("website", ""),
                 data.get("phone", ""), data.get("address", ""),
                 data.get("city", ""), data.get("state", ""))
            )
            conn.commit()
            if cursor.lastrowid and cursor.rowcount > 0:
                return cursor.lastrowid
            # If IGNORE'd (duplicate), find existing
            row = conn.execute(
                "SELECT id FROM businesses WHERE name = ? AND city = ? AND state = ?",
                (data.get("name", ""), data.get("city", ""), data.get("state", ""))
            ).fetchone()
            return row["id"] if row else None
        except Exception:
            return None

    def insert_contact(self, business_id: int, data: Dict) -> Optional[int]:
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO contacts
                   (business_id, email, first_name, last_name, title, seniority_score,
                    email_status, mx_host, is_catch_all, verified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (business_id, data.get("email", ""), data.get("first_name", ""),
                 data.get("last_name", ""), data.get("title", ""),
                 data.get("seniority_score", 0), data.get("email_status", "unknown"),
                 data.get("mx_host", ""), data.get("is_catch_all", False),
                 datetime.now().isoformat() if data.get("email_status") != "unknown" else None)
            )
            conn.commit()
            return cursor.lastrowid if cursor.rowcount > 0 else None
        except Exception:
            return None

    def get_run_stats(self, run_id: int) -> Dict:
        conn = self._get_conn()
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not run:
            return {}
        biz_count = conn.execute(
            "SELECT COUNT(*) FROM businesses WHERE run_id = ?", (run_id,)
        ).fetchone()[0]
        contact_count = conn.execute(
            "SELECT COUNT(*) FROM contacts c JOIN businesses b ON c.business_id = b.id WHERE b.run_id = ?",
            (run_id,)
        ).fetchone()[0]
        verified = conn.execute(
            "SELECT COUNT(*) FROM contacts c JOIN businesses b ON c.business_id = b.id WHERE b.run_id = ? AND c.email_status = 'verified'",
            (run_id,)
        ).fetchone()[0]
        return {
            "run_id": run_id, "niche": run["niche"], "cities": run["cities"],
            "status": run["status"], "started_at": run["started_at"],
            "completed_at": run["completed_at"],
            "businesses": biz_count, "contacts": contact_count, "verified": verified,
        }

    def get_all_runs(self) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def get_unsynced_contacts(self, run_id: int, limit: int = 50) -> List[Dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT c.*, b.name as business_name, b.website, b.phone as business_phone,
                   b.city, b.state, b.niche, b.category
            FROM contacts c
            JOIN businesses b ON c.business_id = b.id
            LEFT JOIN sheets_sync ss ON c.id = ss.contact_id
            WHERE b.run_id = ?
              AND c.email_status IN ('verified', 'catch_all')
              AND ss.id IS NULL
            LIMIT ?
        """, (run_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def mark_synced(self, contact_ids: List[int], sheet_name: str):
        conn = self._get_conn()
        for cid in contact_ids:
            conn.execute(
                "INSERT INTO sheets_sync (contact_id, sheet_name) VALUES (?, ?)",
                (cid, sheet_name)
            )
        conn.commit()

    def export_run_csv(self, run_id: int, output_path: str):
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT b.name, b.category, b.website, b.phone, b.address, b.city, b.state,
                   c.email, c.first_name, c.last_name, c.title, c.seniority_score,
                   c.email_status, c.is_catch_all
            FROM contacts c
            JOIN businesses b ON c.business_id = b.id
            WHERE b.run_id = ?
            ORDER BY c.seniority_score DESC
        """, (run_id,)).fetchall()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "business_name", "category", "website", "phone", "address",
                "city", "state", "email", "first_name", "last_name", "title",
                "seniority_score", "email_status", "is_catch_all"
            ])
            for row in rows:
                writer.writerow(list(row))
        return len(rows)
