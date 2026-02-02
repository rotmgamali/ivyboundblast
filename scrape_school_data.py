#!/usr/bin/env python3
"""
School Website Scraping and Personalization Module

This module handles the extraction of relevant information from private school
websites to enable personalization in cold email outreach campaigns.

Usage:
    python scrape_school_data.py --input leads.csv --output enriched_leads.csv
    python scrape_school_data.py --domain example-school.edu --output school_data.json
"""

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime

# Third-party imports (install via requirements.txt)
try:
    import requests
    from bs4 import BeautifulSoup
    import html2text
except ImportError:
    print("Required packages not installed. Run: pip install requests beautifulsoup4 html2text")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SchoolData:
    """
    Data class to store extracted school information for personalization.
    """
    # Basic identification
    domain: str = ""
    school_name: str = ""
    website_url: str = ""
    
    # Mission and values
    mission_statement: str = ""
    core_values: List[str] = field(default_factory=list)
    
    # Academic programs
    program_emphasis: str = ""  # STEM, arts, college prep, etc.
    special_programs: List[str] = field(default_factory=list)
    academic_approaches: List[str] = field(default_factory=list)
    
    # College counseling
    college_counseling_info: str = ""
    college_outcomes_claimed: str = ""
    
    # Test prep (existing offerings)
    existing_test_prep: str = ""
    test_prep_approach: str = ""
    
    # Recent initiatives
    recent_initiatives: List[str] = field(default_factory=list)
    news_items: List[Dict[str, str]] = field(default_factory=list)
    
    # Leadership
    head_of_school: str = ""
    key_administrators: List[Dict[str, str]] = field(default_factory=list)
    
    # Contact patterns
    email_pattern: str = ""
    
    # Metadata
    scrape_date: str = ""
    scrape_status: str = "pending"
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchoolData':
        """Create instance from dictionary."""
        school = cls()
        for key, value in data.items():
            if hasattr(school, key):
                setattr(school, key, value)
        return school


class SchoolWebsiteScraper:
    """
    Main scraping class for extracting school website data.
    """
    
    # Common URL patterns for different page types
    URL_PATTERNS = {
        'homepage': [
            '',
            '/',
            '/index.html',
            '/index.htm'
        ],
        'about': [
            '/about',
            '/about-us',
            '/our-story',
            '/mission',
            '/philosophy'
        ],
        'academics': [
            '/academics',
            '/academic-programs',
            '/curriculum',
            '/programs'
        ],
        'college': [
            '/college-counseling',
            '/college-preparation',
            '/college-success',
            '/higher-education'
        ],
        'news': [
            '/news',
            '/news-events',
            '/blog',
            '/announcements',
            '/recent-news'
        ],
        'contact': [
            '/contact',
            '/contact-us',
            '/directory',
            '/staff'
        ]
    }
    
    # Program emphasis keywords
    PROGRAM_KEYWORDS = {
        'STEM': ['stem', 'science', 'technology', 'engineering', 'math', 'robotics', 'coding'],
        'Arts': ['arts', 'visual arts', 'performing arts', 'music', 'drama', 'theater'],
        'College Prep': ['college prep', 'college preparation', 'college counseling', 'ivy league'],
        'International': ['ib', 'international baccalaureate', 'global', 'abroad', 'study abroad'],
        'STEM': ['stem', 'steam', 'science', 'technology', 'engineering', 'mathematics'],
        'Classical': ['classical', 'great books', 'liberal arts', 'humanities'],
        'Religious': ['faith', 'religious', 'christian', 'catholic', 'jesuit', 'spiritual']
    }
    
    def __init__(self, request_timeout: int = 10, retry_count: int = 3):
        """
        Initialize the scraper.
        
        Args:
            request_timeout: Timeout for HTTP requests in seconds
            retry_count: Number of retry attempts for failed requests
        """
        self.timeout = request_timeout
        self.retry_count = retry_count
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.width = 120
    
    def scrape(self, domain: str) -> SchoolData:
        """
        Main entry point for scraping a school website.
        
        Args:
            domain: School domain (e.g., 'example.edu' or 'https://example.edu')
            
        Returns:
            SchoolData object with extracted information
        """
        school_data = SchoolData()
        school_data.scrape_date = datetime.now().isoformat()
        
        # Normalize domain
        domain = self._normalize_domain(domain)
        school_data.domain = domain
        school_data.website_url = f"https://{domain}"
        
        logger.info(f"Starting scrape for domain: {domain}")
        
        try:
            # Scrape homepage first
            homepage_content = self._fetch_page(school_data.website_url)
            if homepage_content:
                self._parse_homepage(homepage_content, school_data)
            
            # Scrape additional pages for deeper information
            self._scrape_additional_pages(school_data)
            
            school_data.scrape_status = "success"
            logger.info(f"Successfully scraped {domain}")
            
        except Exception as e:
            school_data.scrape_status = "error"
            school_data.error_message = str(e)
            logger.error(f"Error scraping {domain}: {e}")
        
        return school_data
    
    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain string."""
        # Remove protocol
        if '://' in domain:
            domain = urlparse(domain).netloc
        
        # Remove trailing slash and path
        domain = domain.split('/')[0]
        
        # Remove www prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain.lower().strip()
    
    def _fetch_page(self, url: str, retries: Optional[int] = None) -> Optional[str]:
        """
        Fetch a single page with retry logic.
        
        Args:
            url: Full URL to fetch
            retries: Number of retries remaining
            
        Returns:
            HTML content or None if failed
        """
        if retries is None:
retries = self.retry_count
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None
        
        return None
    
    def _parse_homepage(self, html: str, school_data: SchoolData):
        """Parse homepage content to extract basic information."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract school name
        school_data.school_name = self._extract_school_name(soup)
        
        # Extract mission statement
        school_data.mission_statement = self._extract_mission(soup)
        
        # Identify program emphasis
        school_data.program_emphasis = self._identify_program_emphasis(soup, html)
        
        # Extract core values
        school_data.core_values = self._extract_core_values(soup)
        
        # Look for college counseling info
        school_data.college_counseling_info = self._extract_college_info(soup)
        
        # Check for existing test prep offerings
        school_data.existing_test_prep = self._identify_test_prep(soup, html)
    
    def _extract_school_name(self, soup: BeautifulSoup) -> str:
        """Extract school name from homepage."""
        # Check common name locations
        name_selectors = [
            'meta[property="og:site_name"]',
            'meta[name="application-name"]',
            '.logo-text',
            '.site-title',
            'h1.logo',
            '.brand',
            '#logo',
            'header h1',
            'nav .school-name'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                if name and len(name) > 3:
                    return name
        
        # Fallback: look for text patterns
        title = soup.find('title')
        if title:
            text = title.get_text()
            # Common patterns: "School Name | Tagline" or "School Name - Tagline"
            match = re.match(r'^([A-Z][A-Za-z\s&\'\-\.]+(?:School|Academy|Institute|College))', text)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_mission(self, soup: BeautifulSoup) -> str:
        """Extract mission statement from homepage."""
        # Look for mission-related sections
        mission_keywords = ['mission', 'purpose', 'values', 'philosophy', 'about us']
        
        # Check various page elements
        for keyword in mission_keywords:
            # Look for headings with keywords
            heading = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3', 'h4'] and 
                             keyword in tag.get_text().lower())
            if heading:
                # Get the following paragraph
                next_p = heading.find_next('p')
                if next_p:
                    return self.h2t.handle(str(next_p)).strip()[:500]
        
        # Check meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()[:500]
        
        return ""
    
    def _identify_program_emphasis(self, soup: BeautifulSoup, html: str) -> str:
        """Identify the school's primary program emphasis."""
        text = soup.get_text().lower()
        html_lower = html.lower()
        
        emphasis_scores = {}
        
        for emphasis, keywords in self.PROGRAM_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                emphasis_scores[emphasis] = score
        
        if emphasis_scores:
            return max(emphasis_scores, key=emphasis_scores.get)
        
        return ""
    
    def _extract_core_values(self, soup: BeautifulSoup) -> List[str]:
        """Extract core values from homepage."""
        values = []
        
        # Look for values section
        values_heading = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and 
                                 'value' in tag.get_text().lower())
        if values_heading:
            # Get following list
            values_list = values_heading.find_next('ul')
            if values_list:
                for li in values_list.find_all('li', limit=5):
                    value = li.get_text(strip=True)
                    if value:
                        values.append(value)
        
        return values
    
    def _extract_college_info(self, soup: BeautifulSoup) -> str:
        """Extract college counseling information."""
        # Look for college-related sections
        college_keywords = ['college counseling', 'college preparation', 'college success', 
                           'higher education', 'admissions']
        
        for keyword in college_keywords:
            section = soup.find(lambda tag: tag.name in ['section', 'div', 'article'] and 
                              keyword in tag.get_text().lower())
            if section:
                text = section.get_text()[:300]
                return text.strip()
        
        return ""
    
    def _identify_test_prep(self, soup: BeautifulSoup, html: str) -> str:
        """Identify existing test prep offerings."""
        test_prep_keywords = ['sat prep', 'act prep', 'test preparation', ' standardized testing',
                             'ssat', 'isee', 'gre', 'gmat']
        
        text = soup.get_text().lower()
        found = [kw for kw in test_prep_keywords if kw in text]
        
        if found:
            return ', '.join(found)
        
        return ""
    
    def _scrape_additional_pages(self, school_data: SchoolData):
        """Scrape additional pages for deeper information."""
        base_url = school_data.website_url
        
        # Scrape academic programs page
        academic_url = self._find_page_url(base_url, 'academics')
        if academic_url:
            content = self._fetch_page(academic_url)
            if content:
                self._parse_academics(content, school_data)
        
        # Scrape college counseling page
        college_url = self._find_page_url(base_url, 'college')
        if college_url:
            content = self._fetch_page(college_url)
            if content:
                self._parse_college_counseling(content, school_data)
        
        # Scrape news page
        news_url = self._find_page_url(base_url, 'news')
        if news_url:
            content = self._fetch_page(news_url)
            if content:
                self._parse_news(content, school_data)
        
        # Scrape contact/directory page for leadership
        contact_url = self._find_page_url(base_url, 'contact')
        if contact_url:
            content = self._fetch_page(contact_url)
            if content:
                self._parse_contact(content, school_data)
    
    def _find_page_url(self, base_url: str, page_type: str) -> Optional[str]:
        """Find URL for a specific page type."""
        patterns = self.URL_PATTERNS.get(page_type, [])
        
        for pattern in patterns:
            url = urljoin(base_url, pattern)
            response = self.session.head(url, timeout=self.timeout)
            if response.status_code == 200:
                return url
        
        # Try direct URL construction
        for pattern in patterns:
            url = f"{base_url}{pattern}"
            response = self.session.head(url, timeout=self.timeout)
            if response.status_code == 200:
                return url
        
        return None
    
    def _parse_academics(self, html: str, school_data: SchoolData):
        """Parse academic programs page."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract program descriptions
        programs = []
        program_headings = soup.find_all(['h2', 'h3'], limit=10)
        
        for heading in program_headings:
            program_name = heading.get_text(strip=True)
            if program_name and len(program_name) > 3:
                programs.append(program_name)
        
        school_data.special_programs = programs[:5]
    
    def _parse_college_counseling(self, html: str, school_data: SchoolData):
        """Parse college counseling page."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract college outcomes claims
        text = soup.get_text()
        
        # Look for statistics
        percentage_match = re.search(r'(\d{1,3})%?\s*(college|university|admission|acceptance)', text, re.IGNORECASE)
        if percentage_match:
            school_data.college_outcomes_claimed = percentage_match.group(0)
    
    def _parse_news(self, html: str, school_data: SchoolData):
        """Parse news/announcements page."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract recent news items
        news_items = []
        articles = soup.find_all(['article', 'div'], class_=['news-item', 'announcement', 'post'], limit=5)
        
        for article in articles:
            title_elem = article.find(['h2', 'h3', 'h4'])
            date_elem = article.find(['time', 'span', 'div'], class_=['date', 'timestamp'])
            
            if title_elem:
                item = {
                    'title': title_elem.get_text(strip=True)[:100],
                    'date': date_elem.get_text(strip=True) if date_elem else ''
                }
                news_items.append(item)
        
        school_data.news_items = news_items[:3]
        
        # Extract recent initiatives from titles
        if news_items:
            school_data.recent_initiatives = [item['title'] for item in news_items[:2]]
    
    def _parse_contact(self, html: str, school_data: SchoolData):
        """Parse contact/directory page."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract email pattern
        emails = re.findall(r'@[\w.-]+\.\w+', html)
        if emails:
            # Find common pattern
            patterns = {}
            for email in emails[:10]:
                local = email.split('@')[0]
                # Check for common patterns
                if '.' in local:
                    parts = local.split('.')
                    pattern = f"{parts[0][0]}{parts[1]}"
                    patterns[pattern] = patterns.get(pattern, 0) + 1
            
            if patterns:
                most_common = max(patterns, key=patterns.get)
                school_data.email_pattern = most_common + "@" + emails[0].split('@')[1]
        
        # Extract head of school
        head_keywords = ['head of school', 'headmaster', 'principal', 'director', 'chief']
        
        for keyword in head_keywords:
            heading = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3'] and 
                              keyword in tag.get_text().lower())
            if heading:
                # Look for name in following elements
                name_elem = heading.find_next(['p', 'div', 'span'])
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    # Clean up name
                    name = re.sub(r'^(of|for)\s+', '', name, flags=re.IGNORECASE)
                    if name and len(name.split()) >= 2:
                        school_data.head_of_school = name
                        break
        
        # Extract key administrators
        admin_section = soup.find_all(['tr', 'li'], class_=['staff', 'faculty', 'admin'], limit=10)
        admins = []
        
        for admin in admin_section[:5]:
            text = admin.get_text()
            # Look for title and name patterns
            title_match = re.search(r'(Director|Dean|Coordinator|Chair)', text)
            name_match = re.search(r'([A-Z][a-z]+\s[A-Z][a-z]+)', text)
            
            if title_match and name_match:
                admins.append({
                    'title': title_match.group(1),
                    'name': name_match.group(1)
                })
        
        school_data.key_administrators = admins


def scrape_school(domain: str, output_file: Optional[str] = None) -> SchoolData:
    """
    Convenience function to scrape a single school.
    
    Args:
        domain: School domain to scrape
        output_file: Optional file path to save JSON output
        
    Returns:
        SchoolData object
    """
    scraper = SchoolWebsiteScraper()
    data = scraper.scrape(domain)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved data to {output_file}")
    
    return data


def process_leads_file(input_file: str, output_file: str) -> List[SchoolData]:
    """
    Process a CSV file of school domains and scrape each one.
    
    Args:
        input_file: Path to input CSV with 'domain' column
        output_file: Path to save enriched JSON output
        
    Returns:
        List of SchoolData objects
    """
    import csv
    
    results = []
    scraper = SchoolWebsiteScraper()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        domains = [row.get('domain', row.get('school_domain', '')) for row in reader if row]
    
    logger.info(f"Processing {len(domains)} domains...")
    
    for i, domain in enumerate(domains):
        if domain:
            logger.info(f"Processing {i+1}/{len(domains)}: {domain}")
            data = scraper.scrape(domain)
            results.append(data)
            
            # Rate limiting
            time.sleep(1)
    
    # Save results
    output_data = [school.to_dict() for school in results]
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(results)} records to {output_file}")
    return results


def generate_template_variables(school_data: SchoolData) -> Dict[str, str]:
    """
    Generate template variables from scraped data.
    
    Args:
        school_data: SchoolData object
        
    Returns:
        Dictionary of variable names and values for template injection
    """
    variables = {
        'school_name': school_data.school_name or school_data.domain.split('.')[0].title(),
        'program_emphasis': school_data.program_emphasis or 'academic excellence',
        'mission_statement': school_data.mission_statement[:100] if school_data.mission_statement else '',
        'recent_initiative': school_data.recent_initiatives[0] if school_data.recent_initiatives else '',
        'nearby_school': 'a nearby private school',
        'head_of_school': school_data.head_of_school,
        'existing_test_prep': school_data.existing_test_prep,
        'college_counseling_messaging': school_data.college_counseling_info[:100] if school_data.college_counseling_info else ''
    }
    
    return variables


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Scrape school websites for personalization data'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Single domain command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape a single school domain')
    scrape_parser.add_argument('domain', help='School domain (e.g., example.edu)')
    scrape_parser.add_argument('--output', '-o', help='Output file path (JSON)')
    
    # Batch processing command
    batch_parser = subparsers.add_parser('batch', help='Process multiple domains from CSV')
    batch_parser.add_argument('input', help='Input CSV file path')
    batch_parser.add_argument('--output', '-o', required=True, help='Output JSON file path')
    
    # Variable generation command
    var_parser = subparsers.add_parser('variables', help='Generate template variables from JSON')
    var_parser.add_argument('input', help='Input JSON file from scrape')
    
    args = parser.parse_args()
    
    if args.command == 'scrape':
        data = scrape_school(args.domain, args.output)
        print(f"Scraped: {data.school_name}")
        print(f"Program Emphasis: {data.program_emphasis}")
        print(f"Mission: {data.mission_statement[:100]}...")
    
    elif args.command == 'batch':
        results = process_leads_file(args.input, args.output)
        print(f"Processed {len(results)} schools")
    
    elif args.command == 'variables':
        with open(args.input, 'r') as f:
            data_list = json.load(f)
        
        for data_dict in data_list[:5]:  # Show first 5
            school_data = SchoolData.from_dict(data_dict)
            variables = generate_template_variables(school_data)
            print(f"\n{school_data.domain}:")
            for key, value in variables.items():
                if value:
                    print(f"  {key}: {value}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
