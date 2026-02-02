#!/usr/bin/env python3
"""
Ivy Bound School Partnership Campaign Pipeline

This pipeline orchestrates the entire cold email campaign process:
1. Lead enrichment (website scraping and data extraction)
2. Personalization variable generation
3. Template selection based on decision maker role
4. Email generation and variable injection
5. Export for email sending platform

Usage:
    python pipeline.py --campaign school --input leads/school/input.csv
    python pipeline.py --campaign school --domain example.edu --test
    python pipeline.py --campaign school --input leads.csv --dry-run
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

# Import local modules
from scrape_school_data import SchoolWebsiteScraper, SchoolData, generate_template_variables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('campaign.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class EnrichedLead:
    """
    Enriched lead data combining original lead information with scraped data.
    """
    # Original lead fields
    email: str
    first_name: str
    last_name: str
    role: str
    school_name: str
    domain: str
    
    # Additional lead data
    district_name: Optional[str] = None
    state: Optional[str] = None
    subject_area: Optional[str] = None
    program_type: Optional[str] = None
    
    # Scraped data
    mission_statement: str = ""
    program_emphasis: str = ""
    recent_initiative: str = ""
    nearby_school: str = ""
    comparable_district: str = ""
    existing_test_prep: str = ""
    college_counseling_messaging: str = ""
    
    # Template variables
    template_variables: Dict[str, str] = field(default_factory=dict)
    
    # Template selection
    template_folder: str = ""
    email_variant: str = "email_1"
    
    # Metadata
    scrape_status: str = "pending"
    generated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_lead_csv(cls, row: Dict[str, str]) -> 'EnrichedLead':
        """Create from CSV row."""
        lead = cls(
            email=row.get('email', ''),
            first_name=row.get('first_name', row.get('firstname', '')),
            last_name=row.get('last_name', row.get('lastname', '')),
            role=row.get('role', ''),
            school_name=row.get('school_name', row.get('schoolname', row.get('school', ''))),
            domain=row.get('domain', row.get('school_domain', '')),
            district_name=row.get('district_name', ''),
            state=row.get('state', ''),
            subject_area=row.get('subject_area', ''),
            program_type=row.get('program_type', '')
        )
        return lead


class CampaignPipeline:
    """
    Main campaign orchestration class.
    """
    
    # Role to template folder mapping
    ROLE_MAPPING = {
        'superintendent': 'superintendent',
        'head of school': 'superintendent',
        'headmaster': 'superintendent',
        'principal': 'principal',
        'assistant principal': 'principal',
        'curriculum director': 'curriculum_director',
        'academic dean': 'curriculum_director',
        'curriculum': 'curriculum_director',
        'federal program director': 'federal_program_director',
        'title i director': 'federal_program_director',
        'compliance': 'federal_program_director',
        'college counselor': 'college_counseling',
        'college counseling': 'college_counseling',
        'director of college counseling': 'college_counseling'
    }
    
    # Sender mapping by role
    SENDER_MAPPING = {
        'superintendent': 'Mark Greenstein',
        'principal': 'Andrew',
        'curriculum_director': 'Genelle',
        'federal_program_director': 'Mark Greenstein',
        'college_counseling': 'Andrew'
    }
    
    def __init__(self, template_dir: str = "templates/school"):
        """
        Initialize pipeline.
        
        Args:
            template_dir: Directory containing email templates
        """
        self.template_dir = Path(template_dir)
        self.scraper = SchoolWebsiteScraper()
        
        # Load templates
        self.templates: Dict[str, Dict[str, str]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all email templates from template directory."""
        logger.info(f"Loading templates from {self.template_dir}")
        
        for role_folder in self.template_dir.iterdir():
            if role_folder.is_dir():
                role_name = role_folder.name
                self.templates[role_name] = {}
                
                for template_file in role_folder.glob('*.txt'):
                    template_name = template_file.stem
                    with open(template_file, 'r', encoding='utf-8') as f:
                        self.templates[role_name][template_name] = f.read()
        
        logger.info(f"Loaded templates: {list(self.templates.keys())}")
    
    def _detect_role(self, role_string: str) -> str:
        """
        Detect template folder from role string.
        
        Args:
            role_string: Raw role description from lead data
            
        Returns:
            Template folder name
        """
        role_lower = role_string.lower()
        
        for keyword, template_folder in self.ROLE_MAPPING.items():
            if keyword in role_lower:
                return template_folder
        
        # Default to superintendent for unknown roles
        return 'superintendent'
    
    def _generate_variables(self, lead: EnrichedLead, school_data: Optional[SchoolData] = None) -> Dict[str, str]:
        """
        Generate template variables for a lead.
        
        Args:
            lead: Original lead data
            school_data: Optional scraped school data
            
        Returns:
            Dictionary of template variables
        """
        variables = {
            # Core personalizations
            'first_name': lead.first_name,
            'school_name': lead.school_name,
            'district_name': lead.district_name or '',
            
            # Program-specific
            'subject_area': lead.subject_area or '',
            'program_type': lead.program_type or '',
            'state': lead.state or '',
            
            # Scraped data
            'mission_statement': '',
            'program_emphasis': '',
            'recent_initiative': '',
            'nearby_school': '',
            'comparable_district': '',
            'existing_test_prep': '',
            'college_counseling_messaging': ''
        }
        
        if school_data:
            scraped_vars = generate_template_variables(school_data)
            for key, value in scraped_vars.items():
                if key in variables:
                    variables[key] = value
        
        # Set nearby_school default if not found
        if not variables.get('nearby_school'):
            variables['nearby_school'] = 'a comparable private school'
        
        # Set comparable_district default
        if not variables.get('comparable_district'):
            variables['comparable_district'] = 'similar districts'
        
        return variables
    
    def _inject_variables(self, template: str, variables: Dict[str, str]) -> str:
        """
        Inject variables into email template.
        
        Args:
            template: Email template string
            variables: Dictionary of variable values
            
        Returns:
            Completed email string
        """
        result = template
        
        for key, value in variables.items():
            placeholder = f'{{{{ {key} }}}}'
            result = result.replace(placeholder, str(value))
        
        return result
    
    def _select_template(self, lead: EnrichedLead, variant: str = "email_1") -> str:
        """
        Select and populate email template.
        
        Args:
            lead: Enriched lead data
            variant: Template variant (email_1 or email_2)
            
        Returns:
            Completed email string
        """
        template_folder = self._detect_role(lead.role)
        lead.template_folder = template_folder
        
        if template_folder not in self.templates:
            template_folder = 'superintendent'
        
        if variant not in self.templates[template_folder]:
            variant = 'email_1'
        
        template = self.templates[template_folder][variant]
        
        # Generate and inject variables
        variables = self._generate_variables(lead)
        lead.template_variables = variables
        
        email = self._inject_variables(template, variables)
        
        return email
    
    def enrich_lead(self, lead: EnrichedLead, skip_scrape: bool = False) -> EnrichedLead:
        """
        Enrich a single lead with scraped data.
        
        Args:
            lead: Lead to enrich
            skip_scrape: Skip website scraping
            
        Returns:
            Enriched lead
        """
        if lead.domain and not skip_scrape:
            try:
                school_data = self.scraper.scrape(lead.domain)
                lead.scrape_status = school_data.scrape_status
                
                # Map scraped data to lead
                lead.mission_statement = school_data.mission_statement
                lead.program_emphasis = school_data.program_emphasis
                lead.recent_initiative = school_data.recent_initiatives[0] if school_data.recent_initiatives else ''
                lead.nearby_school = school_data.school_name or 'a nearby private school'
                lead.existing_test_prep = school_data.existing_test_prep
                lead.college_counseling_messaging = school_data.college_counseling_info
                
                logger.info(f"Enriched lead: {lead.school_name} - {lead.program_emphasis}")
                
            except Exception as e:
                lead.scrape_status = f"error: {str(e)}"
                logger.warning(f"Scrape error for {lead.domain}: {e}")
        else:
            lead.scrape_status = "skipped"
        
        lead.generated_at = datetime.now().isoformat()
        
        return lead
    
    def process_leads(self, input_file: str, output_file: str, 
                      skip_scrape: bool = False, dry_run: bool = False,
                      max_records: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Process leads from input CSV and generate emails.
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output JSON file
            skip_scrape: Skip website scraping
            dry_run: Don't save files, just show sample
            max_records: Limit records to process
            
        Returns:
            List of processed lead dictionaries
        """
        logger.info(f"Processing leads from {input_file}")
        
        # Load leads from CSV
        leads = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if max_records and len(leads) >= max_records:
                    break
                lead = EnrichedLead.from_lead_csv(row)
                leads.append(lead)
        
        logger.info(f"Loaded {len(leads)} leads")
        
        # Process each lead
        processed = []
        for i, lead in enumerate(leads):
            logger.info(f"Processing {i+1}/{len(leads)}: {lead.email}")
            
            # Enrich with scraped data
            lead = self.enrich_lead(lead, skip_scrape)
            
            # Generate email 1
            email_1 = self._select_template(lead, "email_1")
            
            # Generate email 2 (for follow-up)
            email_2 = self._select_template(lead, "email_2")
            
            # Create output record
            record = lead.to_dict()
            record['email_1'] = email_1
            record['email_2'] = email_2
            record['sender'] = self.SENDER_MAPPING.get(lead.template_folder, 'Mark Greenstein')
            
            processed.append(record)
            
            # Rate limiting for scraping
            if not skip_scrape and i < len(leads) - 1:
                time.sleep(1)
        
        # Save output
        if not dry_run:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(processed)} records to {output_file}")
            
            # Generate CSV summary
            self._generate_summary(processed, output_file.replace('.json', '_summary.csv'))
        
        return processed
    
    def _generate_summary(self, records: List[Dict], output_file: str):
        """Generate CSV summary of processed leads."""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'email', 'first_name', 'school_name', 'role', 
                'template_folder', 'scrape_status', 'program_emphasis'
            ])
            
            for record in records:
                writer.writerow([
                    record.get('email', ''),
                    record.get('first_name', ''),
                    record.get('school_name', ''),
                    record.get('role', ''),
                    record.get('template_folder', ''),
                    record.get('scrape_status', ''),
                    record.get('program_emphasis', '')
                ])
        
        logger.info(f"Generated summary: {output_file}")
    
    def test_single_domain(self, domain: str, role: str = "principal"):
        """
        Test scraping and template generation for a single domain.
        
        Args:
            domain: School domain to test
            role: Role to use for template selection
        """
        logger.info(f"Testing single domain: {domain}")
        
        # Create test lead
        lead = EnrichedLead(
            email=f"test@{domain}",
            first_name="Test",
            last_name="User",
            role=role,
            school_name=domain.split('.')[0].title(),
            domain=domain
        )
        
        # Enrich
        lead = self.enrich_lead(lead)
        
        # Generate emails
        email_1 = self._select_template(lead, "email_1")
        email_2 = self._select_template(lead, "email_2")
        
        # Output results
        print("\n" + "="*80)
        print("SCRAPED DATA:")
        print("="*80)
        print(f"School Name: {lead.school_name}")
        print(f"Program Emphasis: {lead.program_emphasis}")
        print(f"Mission: {lead.mission_statement[:200]}...")
        print(f"Recent Initiative: {lead.recent_initiative}")
        print(f"Scrape Status: {lead.scrape_status}")
        
        print("\n" + "="*80)
        print("EMAIL 1:")
        print("="*80)
        print(email_1)
        
        print("\n" + "="*80)
        print("EMAIL 2:")
        print("="*80)
        print(email_2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ivy Bound School Partnership Campaign Pipeline'
    )
    
    parser.add_argument(
        '--campaign', '-c',
        default='school',
        help='Campaign type (default: school)'
    )
    
    parser.add_argument(
        '--input', '-i',
        help='Input CSV file path'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output JSON file path'
    )
    
    parser.add_argument(
        '--domain', '-d',
        help='Single domain to test (for testing)'
    )
    
    parser.add_argument(
        '--role', '-r',
        default='principal',
        help='Role for single domain test'
    )
    
    parser.add_argument(
        '--skip-scrape', '-s',
        action='store_true',
        help='Skip website scraping'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show sample output without saving'
    )
    
    parser.add_argument(
        '--max-records', '-m',
        type=int,
        help='Limit number of records to process'
    )
    
    parser.add_argument(
        '--template-dir',
        default='templates/school',
        help='Template directory path'
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = CampaignPipeline(template_dir=args.template_dir)
    
    if args.domain:
        # Single domain test
        pipeline.test_single_domain(args.domain, args.role)
    
    elif args.input:
        # Process leads file
        output_file = args.output or args.input.replace('.csv', '_enriched.json')
        pipeline.process_leads(
            args.input, 
            output_file,
            skip_scrape=args.skip_scrape,
            dry_run=args.dry_run,
            max_records=args.max_records
        )
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
