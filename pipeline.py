#!/usr/bin/env python3
"""
Ivy Bound School Partnership Campaign Pipeline

Usage:
    python pipeline.py --input leads/school/input.csv --output enriched_leads.json
    python pipeline.py --domain example.edu --test
"""

import argparse
import csv
import json
import logging
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EnrichedLead:
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    role: str = ""
    school_name: str = ""
    domain: str = ""
    district_name: Optional[str] = None
    state: Optional[str] = None
    subject_area: Optional[str] = None
    program_type: Optional[str] = None
    mission_statement: str = ""
    program_emphasis: str = ""
    recent_initiative: str = ""
    nearby_school: str = ""
    template_variables: Dict[str, str] = field(default_factory=dict)
    template_folder: str = ""
    email_variant: str = "email_1"
    scrape_status: str = "pending"
    generated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CampaignPipeline:
    # Role keywords → template folder mapping
    # Private schools in Florida focus
    ROLE_MAPPING = {
        # Head of School (strategic decisions)
        'head of school': 'head_of_school',
        'headmaster': 'head_of_school',
        'headmistress': 'head_of_school',
        'superintendent': 'head_of_school',
        'executive director': 'head_of_school',
        # Principal (operations)
        'principal': 'principal',
        'assistant principal': 'principal',
        'vice principal': 'principal',
        # Academic Dean (curriculum)
        'academic dean': 'academic_dean',
        'dean of academics': 'academic_dean',
        'curriculum director': 'academic_dean',
        'director of academics': 'academic_dean',
        'dean of studies': 'academic_dean',
        # College Counseling (student outcomes)
        'college counselor': 'college_counseling',
        'college counseling': 'college_counseling',
        'director of college counseling': 'college_counseling',
        'guidance director': 'college_counseling',
        'guidance counselor': 'college_counseling',
        # Business Manager (finances)
        'business manager': 'business_manager',
        'cfo': 'business_manager',
        'chief financial': 'business_manager',
        'director of finance': 'business_manager',
        'business office': 'business_manager'
    }
    
    # Sender per role (from playbook) - first name only for signature
    SENDER_MAPPING = {
        'head_of_school': 'Mark',
        'principal': 'Andrew',
        'academic_dean': 'Genelle',
        'college_counseling': 'Andrew',
        'business_manager': 'Mark',
        'general': 'Mark'  # Fallback for unknown roles
    }
    
    # Map email prefixes to sender names
    EMAIL_TO_NAME = {
        'andrew': 'Andrew',
        'genelle': 'Genelle',
        'mark': 'Mark',
        'outreach': 'Mark'  # outreach@ uses Mark
    }

    
    def __init__(self, template_dir: str = "templates/school"):
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, Dict[str, str]] = {}
        self._load_templates()
    
    def _load_templates(self):
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
        role_lower = role_string.lower()
        for keyword, template_folder in self.ROLE_MAPPING.items():
            if keyword in role_lower:
                return template_folder
        return 'general'  # Fallback for unknown role titles
    
    def _scrape_school(self, domain: str) -> Dict[str, str]:
        result = {
            'school_name': '',
            'mission_statement': '',
            'program_emphasis': '',
            'recent_initiative': ''
        }
        
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0'})
            response = session.get(f"https://{domain}", timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract school name
                title = soup.find('title')
                if title:
                    text = title.get_text()
                    match = text.split('|')[0].split('-')[0].strip()
                    if match and len(match) > 3:
                        result['school_name'] = match
                
                # Extract program emphasis
                text = soup.get_text().lower()
                emphases = {
                    'STEM': ['stem', 'science', 'technology', 'engineering', 'math'],
                    'Arts': ['arts', 'visual arts', 'performing arts', 'music'],
                    'College Prep': ['college prep', 'college preparation', 'counseling'],
                    'International': ['ib', 'international baccalaureate', 'global']
                }
                
                for emphasis, keywords in emphases.items():
                    if any(kw in text for kw in keywords):
                        result['program_emphasis'] = emphasis
                        break
        
        except Exception as e:
            logger.warning(f"Scraping error for {domain}: {e}")
        
        return result
    
    def _inject_variables(self, template: str, variables: Dict[str, str]) -> str:
        result = template
        for key, value in variables.items():
            placeholder = f'{{{{ {key} }}}}'
            result = result.replace(placeholder, str(value))
        return result
    
    def process_leads(self, input_file: str, output_file: str, 
                      skip_scrape: bool = False) -> List[Dict[str, Any]]:
        logger.info(f"Processing leads from {input_file}")
        
        leads = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                lead = EnrichedLead(
                    email=row.get('email', ''),
                    first_name=row.get('first_name', row.get('firstname', '')),
                    last_name=row.get('last_name', row.get('lastname', '')),
                    role=row.get('role', ''),
                    school_name=row.get('school_name', row.get('schoolname', '')),
                    domain=row.get('domain', row.get('school_domain', '')),
                    district_name=row.get('district_name', ''),
                    state=row.get('state', ''),
                    subject_area=row.get('subject_area', ''),
                    program_type=row.get('program_type', '')
                )
                leads.append(lead)
        
        logger.info(f"Loaded {len(leads)} leads")
        
        processed = []
        for i, lead in enumerate(leads):
            logger.info(f"Processing {i+1}/{len(leads)}: {lead.email}")
            
            scraped = {}
            if lead.domain and not skip_scrape:
                scraped = self._scrape_school(lead.domain)
                lead.scrape_status = "success"
            
            # Determine sender name based on role
            sender_name = self.SENDER_MAPPING.get(self._detect_role(lead.role), 'Mark')
            
            variables = {
                'first_name': lead.first_name,
                'school_name': lead.school_name or scraped.get('school_name', lead.domain.split('.')[0]),
                'district_name': lead.district_name or '',
                'subject_area': lead.subject_area or '',
                'program_type': lead.program_type or '',
                'state': lead.state or '',
                'mission_statement': scraped.get('mission_statement', ''),
                'program_emphasis': scraped.get('program_emphasis', 'academic excellence'),
                'recent_initiative': scraped.get('recent_initiative', ''),
                'nearby_school': 'a comparable private school',
                'sender_name': sender_name
            }
            
            lead.template_variables = variables
            lead.template_folder = self._detect_role(lead.role)
            
            template_folder = self.templates.get(lead.template_folder, self.templates['head_of_school'])
            
            email_1 = self._inject_variables(template_folder.get('email_1', ''), variables)
            email_2 = self._inject_variables(template_folder.get('email_2', ''), variables)
            
            record = lead.to_dict()
            record['email_1'] = email_1
            record['email_2'] = email_2
            record['sender'] = self.SENDER_MAPPING.get(lead.template_folder, 'Mark Greenstein')
            processed.append(record)
            
            if not skip_scrape and i < len(leads) - 1:
                time.sleep(1)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(processed)} records to {output_file}")
        return processed


def main():
    parser = argparse.ArgumentParser(description='Ivy Bound School Partnership Campaign Pipeline')
    parser.add_argument('--input', '-i', help='Input CSV file path')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--skip-scrape', '-s', action='store_true', help='Skip website scraping')
    parser.add_argument('--domain', '-d', help='Single domain to test')
    parser.add_argument('--role', '-r', default='principal', help='Role for single domain test')
    
    args = parser.parse_args()
    
    pipeline = CampaignPipeline()
    
    if args.domain:
        lead = EnrichedLead(
            email=f"test@{args.domain}",
            first_name="Test",
            last_name="User",
            role=args.role,
            school_name=args.domain.split('.')[0].title(),
            domain=args.domain
        )
        scraped = pipeline._scrape_school(args.domain)
        print(f"\nScraped Data: {scraped}")
        variables = {
            'first_name': lead.first_name,
            'school_name': lead.school_name or scraped.get('school_name', ''),
            'program_emphasis': scraped.get('program_emphasis', 'academic excellence')
        }
        print(f"Variables: {variables}")
    
    elif args.input:
        output = args.output or args.input.replace('.csv', '_enriched.json')
        pipeline.process_leads(args.input, output, skip_scrape=args.skip_scrape)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
