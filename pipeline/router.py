from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
import pandas as pd
import re


@dataclass
class Lead:
    """Standardized lead format across all pipelines."""
    source_data: dict
    email: str
    first_name: str
    last_name: str
    company: str
    role: str = ""  # Added role field for template selection
    enrichment_data: dict = field(default_factory=dict)
    generated_emails: list = field(default_factory=list)
    status: str = "pending"


class PipelineRouter:
    """
    Routes leads to the appropriate campaign and role-specific templates.
    Supports tiered decision-maker targeting for school campaigns.
    """

    PIPELINE_DETECTORS = {
        "school": ["school_name", "district", "principal", "superintendent", "school_admin", "website", "title"],
        "real_estate": ["property_address", "purchase_date", "home_value", "buyer_name", "owner_name"],
        "pac": ["donor", "contribution_amount", "political_affiliation", "donation_date", "contributor_name"]
    }

    # Role detection patterns for school decision-makers
    # Order matters: more specific patterns first
    # Aligned with IVY_BOUND_SCHOOL_PARTNERSHIP_CAMPAIGN_COMPLETE.md
    ROLE_PATTERNS = {
        # Check specific roles FIRST before broad patterns
        "curriculum_director": [
            r"\bcurriculum\s+director\b",
            r"\bcurriculum\b",
            r"\bacademic\s+dean\b",
            r"\bdean\s+of\s+academics\b",
            r"\binstruction(al)?\s+director\b",
            r"\bacademic\s+director\b",
            r"\bchief\s+academic\b",
            r"\bdepartment\s+head\b",
            r"\bdean\s+of\s+faculty\b",
        ],
        "federal_program_director": [
            r"\btitle\s*[iI1]+\b",
            r"\bfederal\s+program\b",
            r"\bgrant\s+coordinator\b",
            r"\bgrant\s+director\b",
            r"\bfederal\s+coordinator\b",
            r"\bspecial\s+programs?\s+director\b",
            r"\bcompliance\b",
            r"\bbusiness\s+manager\b",
            r"\bcfo\b",
            r"\bchief\s+financial\b",
            r"\boperations\s+director\b",
        ],
        "college_counseling": [
            r"\bcollege\s+counsel",
            r"\bcollege\s+advisor\b",
            r"\buniversity\s+counsel",
            r"\bdirector\s+of\s+college\b",
            r"\bcollege\s+guidance\b",
            r"\badmissions\s+counsel",
        ],
        # Superintendent patterns (includes Head of School for private schools)
        "superintendent": [
            r"\bsuperintendent\b",
            r"\bsupt\b",
            r"\bhead\s+of\s+school\b",
            r"\bheadmaster\b",
            r"\bheadmistress\b",
            r"\bchief\s+executive\b",
            r"\bschool\s+director\b",
        ],
        # Principal is the default fallback
        "principal": [
            r"\bprincipal\b",
            r"\bassistant\s+principal\b",
            r"\bvice\s+principal\b",
            r"\bschool\s+leader\b",
            r"\bbuilding\s+administrator\b",
            r"\bassociate\s+head\b",
        ],
    }

    # Default role fallback priority (Tier 1 > Tier 2 > Tier 3)
    DEFAULT_ROLE = "principal"

    def classify_lead(self, df: pd.DataFrame) -> str:
        """
        Determine pipeline based on DataFrame columns.
        """
        columns = [col.lower().replace(" ", "_") for col in df.columns]

        for pipeline, identifiers in self.PIPELINE_DETECTORS.items():
            if any(ident in columns for ident in identifiers):
                return pipeline

        return "school"  # Default fallback

    def classify_role(self, title: str) -> str:
        """
        Classify a contact's role based on their job title.
        Returns the role key for template selection.
        """
        if not title:
            return self.DEFAULT_ROLE

        title_lower = title.lower().strip()

        for role, patterns in self.ROLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower, re.IGNORECASE):
                    return role

        return self.DEFAULT_ROLE

    def get_template_path(self, pipeline: str, role: str) -> str:
        """
        Get the template directory path for a given pipeline and role.
        """
        if pipeline == "school" and role in self.ROLE_PATTERNS:
            return f"templates/school/{role}"
        return f"templates/{pipeline}"

    def route(self, csv_path: str) -> str:
        """
        Route a CSV file to its appropriate pipeline.
        """
        df = pd.read_csv(csv_path)
        return self.classify_lead(df)

    def route_with_roles(self, csv_path: str) -> Tuple[str, pd.DataFrame]:
        """
        Route a CSV file and classify each lead's role.
        Returns the pipeline name and DataFrame with added 'role' and 'template_path' columns.
        """
        df = pd.read_csv(csv_path)
        pipeline = self.classify_lead(df)

        # Find title column
        title_col = None
        for col in df.columns:
            if col.lower().replace(" ", "_") in ["title", "job_title", "position", "role"]:
                title_col = col
                break

        if title_col and pipeline == "school":
            df["role"] = df[title_col].fillna("").apply(self.classify_role)
            df["template_path"] = df["role"].apply(lambda r: self.get_template_path(pipeline, r))
        else:
            df["role"] = self.DEFAULT_ROLE if pipeline == "school" else ""
            df["template_path"] = f"templates/{pipeline}"

        return pipeline, df

