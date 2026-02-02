# Ivybound Cold Email Campaign: Complete Development Outline

## Project Overview
This document provides a comprehensive technical and strategic outline for building a hyper-personalized cold email campaign targeting public school administrators. The campaign leverages custom Python scraping code to extract institutional intelligence from school websites, generating contextually relevant email content that drives engagement from superintendents, principals, curriculum directors, and federal program coordinators across the United States.

The campaign architecture separates contact data acquisition from outreach execution, with distinct pipelines for different administrator roles. Each role receives tailored messaging based on their responsibilities, pain points, and decision-making authority. The email sequences progress from value-first introduction through soft ask to final engagement attempt, with manual reply handling routed to `andrew@web4guru.com` for qualification and follow-up.

## Part One: Admin Title Segmentation Framework
Understanding the organizational hierarchy within public schools enables precise targeting and message customization. Each administrative role carries distinct responsibilities, priorities, and pain points that shape how they evaluate educational partnerships. Your campaign must speak directly to these differences, transforming generic educational vendor outreach into consultative communication that demonstrates understanding of each recipient's specific challenges.

### Role Categories and Target Priority
The following role taxonomy organizes your 100,000-contact database into segments with distinct campaign approaches. Each role receives a dedicated email sequence calibrated to their organizational influence, purchasing authority, and primary concerns.

#### Tier One: District-Level Decision Makers

**Superintendents** hold ultimate authority over district-wide educational partnerships and represent the highest-value targets for B2B educational sales. Their primary concerns include student outcomes, budget management, community relations, and board accountability. Superintendents evaluate partnerships through the lens of district-wide impact and political risk, making them cautious evaluators who require social proof and proven results before committing to new initiatives.

**Assistant Superintendents** often handle specific functional areas including curriculum, instruction, finance, or human resources. While they may not have final purchasing authority, they significantly influence superintendent decisions and frequently manage the evaluation process for educational vendors. Messaging to assistant superintendents should position Ivybound as a solution that makes their job easier while advancing their functional priorities.

**Federal Program Directors and Title I Coordinators** manage compliance-heavy programs funded by federal mandates. Their world revolves around documentation, reporting, grant optimization, and audit preparation. This audience responds strongly to messaging that emphasizes accountability features, progress tracking, and the ability to demonstrate results to federal overseers. They operate under tight deadlines and constant pressure to maximize the impact of allocated funds.

#### Tier Two: Building-Level Leaders

**Principals** manage individual school operations and represent the most operationally overwhelmed segment of your target audience. They juggle instructional leadership, staff management, parent communications, student discipline, and facility concerns simultaneously. Principals care most about whether a new program will create additional work for already-taxed teachers and staff. Messaging to principals should emphasize ease of implementation, minimal training requirements, and clear benefits that can be communicated to parents and the school board.

**Assistant Principals** support building-level operations and often serve as gatekeepers who control access to principals' limited attention. They frequently have more time to evaluate new initiatives and can become internal champions for promising educational partnerships. Assistant principals should receive messaging that positions them as knowledgeable evaluators who can identify opportunities for their school.

#### Tier Three: Curriculum and Instruction Leaders

**Curriculum Directors** evaluate educational partnerships through the lens of pedagogical alignment and teacher adoption. They worry about whether new programs fit within existing curriculum frameworks, whether teachers will embrace the methodology, and whether results will reflect well on their instructional leadership. This audience responds well to messaging that emphasizes teacher training support, alignment with state standards, and evidence-based methodologies.

**Department Heads and Subject Coordinators** operate within specific academic areas and influence adoption decisions within their domains. A science curriculum coordinator evaluates science-focused offerings differently than a fine arts director evaluates performing arts programs. Messaging to department heads should demonstrate understanding of their specific subject area and how Ivybound's offerings complement existing instructional priorities.

## Part Two: Multi-Step Scraping Strategy
Your custom Python scraping code must navigate the diverse website structures found across thousands of public school districts while extracting the specific data points that enable hyper-personalization. This section provides the technical architecture for a robust, maintainable scraping system that handles variability across school websites while consistently producing the data your campaign requires.

### Website Navigation Architecture
Public school websites fall into several structural categories based on district size, technology investment, and web development approach. Understanding these categories enables your scraping code to detect website type and apply appropriate extraction logic without manual configuration for each site.

**Directory-Based Websites** represent the most common structure for mid-sized districts. These sites organize content under predictable URL patterns such as `/about`, `/departments`, `/staff`, `/academics`, and `/news`. Staff directories typically appear at `/staff-directory`, `/our-team`, or `/personnel`, with contact information presented in tables, card grids, or list formats that follow recognizable patterns. Your scraper should first identify the staff directory URL by searching for common directory page titles, then apply parsing logic appropriate to the detected format.

**CMS-Generated Websites** use content management systems like Drupal, WordPress, or District Web that produce consistent HTML structures across pages. These sites often include structured data (Schema.org markup) that provides machine-readable information about staff members, organizational units, and academic programs. Your scraping code should extract both visible content and embedded structured data, as the structured data often contains information not displayed on the page itself.

**Portal and Portal Hybrid Websites** combine traditional website content with integrated portal systems for student information, parent engagement, or staff resources. These hybrid sites may load directory content dynamically through JavaScript frameworks, requiring Selenium or Playwright for complete extraction. The portal sections typically have different visual design and navigation patterns than the main website, and your scraper should handle each section with appropriate extraction logic.

### Data Extraction Pipeline Design
The scraping system should operate through a staged pipeline that separates concerns and enables parallel processing across multiple schools. This architecture improves extraction speed while maintaining code clarity and error resilience.

```python
# Core scraping pipeline architecture
import asyncio
import aiohttp
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import re
from abc import ABC, abstractmethod
import json
from datetime import datetime
import hashlib

@dataclass
class SchoolContact:
    """Structured contact data extracted from school websites"""
    name: str
    email: Optional[str]
    phone: Optional[str]
    title: str
    department: Optional[str]
    website: str
    website_hash: str = ""
    scraped_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.website_hash = hashlib.md5(
            self.website.encode()
        ).hexdigest()[:8]

@dataclass 
class SchoolContext:
    """Institutional intelligence for personalization"""
    website: str
    school_name: str
    district_name: Optional[str]
    enrollment: Optional[int]
    grade_levels: List[str] = field(default_factory=list)
    mascot: Optional[str] = None
    school_colors: List[str] = field(default_factory=list)
    recent_news: List[Dict[str, str]] = field(default_factory=list)
    leadership: List[Dict[str, str]] = field(default_factory=list)
    programs: List[str] = field(default_factory=list)
    contact_count: int = 0

@dataclass
class ScrapingResult:
    """Complete scraping output for a single school"""
    website: str
    contacts: List[SchoolContact]
    context: SchoolContext
    success: bool
    errors: List[str] = field(default_factory=list)
    scraping_duration_seconds: float = 0.0

class SchoolScraper:
    """
    Multi-strategy school website scraper with adaptive parsing.
    Handles diverse website structures through strategy pattern.
    """
    
    def __init__(self, rate_limit: float = 1.0, timeout: int = 30):
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.session = None
        self.errors = []
        
    async def create_session(self):
        """Initialize aiohttp session with proper headers"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            },
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def scrape_school(self, website: str) -> ScrapingResult:
        """Main entry point for scraping a single school website"""
        start_time = datetime.now()
        errors = []
        
        try:
            # Detect website structure
            structure = await self._detect_structure(website)
            
            # Extract contacts using structure-appropriate strategy
            contacts = await self._extract_contacts(website, structure)
            
            # Gather contextual intelligence
            context = await self._extract_context(website, structure)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return ScrapingResult(
                website=website,
                contacts=contacts,
                context=context,
                success=True,
                errors=errors,
                scraping_duration_seconds=duration
            )
            
        except Exception as e:
            errors.append(f"Critical error: {str(e)}")
            return ScrapingResult(
                website=website,
                contacts=[],
                context=SchoolContext(
                    website=website,
                    school_name="",
                    district_name=None
                ),
                success=False,
                errors=errors,
                scraping_duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    async def _detect_structure(self, website: str) -> Dict[str, Any]:
        """Analyze website structure to guide extraction"""
        async with self.session.get(website) as response:
            html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Detect CMS platform
        cms_indicators = {
            'wordpress': ['wp-content', 'wp-includes'],
            'drupal': ['drupal.js', 'Drupal.settings'],
            'schoolbox': ['schoolbox', 'SchoolBox'],
            'blackbaud': ['bb-includes', 'Blackbaud'],
        }
        
        detected_cms = []
        page_text = soup.get_text().lower()
        for cms, indicators in cms_indicators.items():
            if any(ind in page_text for ind in indicators):
                detected_cms.append(cms)
        
        # Detect directory structure
        directory_patterns = [
            ('table', ['th', 'td'], 'table'),
            ('card', ['class', 'data-card'], 'grid'),
            ('list', ['ul', 'li'], 'list'),
        ]
        
        staff_page_candidates = await self._find_staff_pages(soup, website)
        
        return {
            'cms': detected_cms,
            'staff_pages': staff_page_candidates,
            'has_schema': bool(soup.find_all(attrs={"itemtype": True})),
            'has_dynamic_content': 'dynamic' in page_text or 'react' in page_text.lower(),
        }
    
    async def _find_staff_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Identify potential staff directory pages"""
        patterns = [
            'staff', 'directory', 'personnel', 'faculty', 'team',
            'administration', 'leadership', 'our-team'
        ]
        
        candidates = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            
            if any(pattern in href or pattern in text for pattern in patterns):
                full_url = link['href'] if link['href'].startswith('http') else \
                          f"{base_url.rstrip('/')}/{link['href'].lstrip('/')}"
                candidates.append(full_url)
        
        return list(set(candidates))[:5]  # Limit to top 5 candidates
    
    async def _extract_contacts(self, website: str, structure: Dict) -> List[SchoolContact]:
        """Extract contact information using appropriate strategy"""
        contacts = []
        
        for staff_url in structure.get('staff_pages', []):
            page_contacts = await self._parse_staff_page(staff_url, website, structure)
            contacts.extend(page_contacts)
        
        # Also check homepage for obvious leadership contacts
        homepage_contacts = await self._extract_leadership_from_homepage(website)
        contacts.extend(homepage_contacts)
        
        return self._deduplicate_contacts(contacts)
    
    async def _parse_staff_page(self, url: str, base_website: str, 
                                 structure: Dict) -> List[SchoolContact]:
        """Parse a staff directory page based on detected format"""
        async with self.session.get(url) as response:
            html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        contacts = []
        
        # Strategy selection based on detected structure
        if structure.get('has_schema'):
            contacts.extend(await self._parse_schema_directory(soup, base_website))
        
        if not contacts or structure.get('has_dynamic_content'):
            contacts.extend(await self._parse_table_directory(soup, base_website))
            if not contacts:
                contacts.extend(await self._parse_card_directory(soup, base_website))
        
        return contacts
    
    async def _parse_schema_directory(self, soup: BeautifulSoup, 
                                        base_website: str) -> List[SchoolContact]:
        """Extract contacts from Schema.org structured data"""
        contacts = []
        
        for person in soup.find_all(attrs={'itemtype': 'https://schema.org/Person'}):
            try:
                name_elem = person.find(attrs={'itemprop': 'name'})
                email_elem = person.find(attrs={'itemprop': 'email'})
                job_elem = person.find(attrs={'itemprop': 'jobTitle'})
                
                if name_elem:
                    contact = SchoolContact(
                        name=name_elem.get_text(strip=True),
                        email=email_elem.get_text(strip=True) if email_elem else None,
                        phone=None,
                        title=job_elem.get_text(strip=True) if job_elem else "",
                        department=None,
                        website=base_website
                    )
                    contacts.append(contact)
            except Exception:
                continue
        
        return contacts
    
    async def _parse_table_directory(self, soup: BeautifulSoup, 
                                       base_website: str) -> List[SchoolContact]:
        """Extract contacts from table-based directories"""
        contacts = []
        
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
            
            # Heuristic: tables with headers containing 'name', 'email', 'title' are staff directories
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
            
            name_idx = next((i for i, h in enumerate(headers) if 'name' in h), None)
            email_idx = next((i for i, h in enumerate(headers) if 'email' in h), None)
            title_idx = next((i for i, h in enumerate(headers) if 'title' in h or 'position' in h), None)
            
            if name_idx is None:
                continue
            
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= max(name_idx or 0, email_idx or 0, title_idx or 0):
                    continue
                
                name = cells[name_idx].get_text(strip=True) if name_idx is not None else ""
                if not name or len(name) < 3:
                    continue
                
                email_elem = cells[email_idx].find('a') if email_idx is not None and email_idx < len(cells) else None
                email = email_elem.get('href', '').replace('mailto:', '') if email_elem else \
                       (cells[email_idx].get_text(strip=True) if email_idx is not None and email_idx < len(cells) else None)
                
                title = cells[title_idx].get_text(strip=True) if title_idx is not None and title_idx < len(cells) else ""
                
                if email and '@' in email:
                    contacts.append(SchoolContact(
                        name=name,
                        email=email,
                        phone=None,
                        title=title,
                        department=None,
                        website=base_website
                    ))
        
        return contacts
    
    async def _parse_card_directory(self, soup: BeautifulSoup, 
                                      base_website: str) -> List[SchoolContact]:
        """Extract contacts from card-based or grid directories"""
        contacts = []
        
        # Common card class patterns
        card_selectors = [
            'div.staff-card',
            'div.person-card', 
            'div.contact-card',
            'div faculty-member',
            'article.staff'
        ]
        
        cards = []
        for selector in card_selectors:
            cards.extend(soup.select(selector))
        
        if not cards:
            # Fallback: look for elements with common staff-related classes
            cards = soup.find_all(class_=lambda x: x and any(term in str(x).lower() 
                       for term in ['staff', 'faculty', 'personnel', 'team']))
        
        for card in cards:
            try:
                name_elem = card.find(class_=lambda x: x and 'name' in str(x).lower())
                email_elem = card.find('a', href=lambda x: x and '@' in x if x else False)
                title_elem = card.find(class_=lambda x: x and any(term in str(x).lower() 
                           for term in ['title', 'position', 'role', 'job']))
                
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    email = email_elem.get('href', '').replace('mailto:', '') if email_elem else None
                    title = title_elem.get_text(strip=True) if title_elem else ""
                    
                    if name and len(name) >= 3:
                        contacts.append(SchoolContact(
                            name=name,
                            email=email,
                            phone=None,
                            title=title,
                            department=None,
                            website=base_website
                        ))
            except Exception:
                continue
        
        return contacts
    
    async def _extract_leadership_from_homepage(self, website: str) -> List[SchoolContact]:
        """Extract visible leadership contacts from homepage"""
        async with self.session.get(website) as response:
            html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        contacts = []
        
        # Look for leadership section
        leadership_section = soup.find(class_=lambda x: x and any(term in str(x).lower() 
                    for term in ['leadership', 'administration', 'our-team', 'leadership-team']))
        
        if leadership_section:
            for person in leadership_section.find_all(['div', 'li', 'article']):
                name_elem = person.find(['h2', 'h3', 'h4'])
                email_elem = person.find('a', href=lambda x: x and '@' in x if x else False)
                
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    email = email_elem.get('href', '').replace('mailto:', '') if email_elem else None
                    
                    if name and email:
                        contacts.append(SchoolContact(
                            name=name,
                            email=email,
                            phone=None,
                            title="",
                            department=None,
                            website=website
                        ))
        
        return contacts
    
    async def _extract_context(self, website: str, structure: Dict) -> SchoolContext:
        """Gather institutional intelligence for personalization"""
        async with self.session.get(website) as response:
            html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        context = SchoolContext(
            website=website,
            school_name=self._extract_school_name(soup),
            district_name=self._extract_district_name(soup),
            enrollment=self._extract_enrollment(soup),
            grade_levels=self._extract_grade_levels(soup),
            mascot=self._extract_mascot(soup),
            school_colors=self._extract_colors(soup)
        )
        
        # Additional context from subpages
        news_pages = await self._find_news_pages(soup, website)
        for news_url in news_pages[:2]:
            news_items = await self._extract_news_items(news_url)
            context.recent_news.extend(news_items[:3])
            if len(context.recent_news) >= 5:
                break
        
        # Leadership info for organizational context
        leadership_pages = await self._find_leadership_pages(soup, website)
        for leader_url in leadership_pages[:2]:
            leaders = await self._extract_leadership_info(leader_url)
            context.leadership.extend(leaders[:3])
        
        # Academic programs
        programs_url = await self._find_programs_page(soup, website)
        if programs_url:
            context.programs = await self._extract_programs(programs_url)
        
        return context
    
    def _extract_school_name(self, soup: BeautifulSoup) -> str:
        """Extract school name from homepage"""
        candidates = [
            soup.find('h1'),
            soup.find(class_=lambda x: x and 'logo' in str(x).lower()),
            soup.find('meta', property='og:title'),
        ]
        
        for candidate in candidates:
            if candidate:
                name = candidate.get_text(strip=True) if hasattr(candidate, 'get_text') else \
                      (candidate.get('content', '') if hasattr(candidate, 'get') else '')
                if name and len(name) > 3 and len(name) < 100:
                    return name
        return ""
    
    def _extract_district_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract district name from homepage"""
        footer = soup.find('footer')
        if footer:
            text = footer.get_text()
            # Look for "XYZ School District" patterns
            match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:School\s+)?District', text)
            if match:
                return match.group(1)
        return None
    
    def _extract_enrollment(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract enrollment figure if available"""
        text = soup.get_text()
        
        # Look for enrollment patterns
        patterns = [
            r'enrollment\s*(?:of\s*)?(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)\s*students?',
            r'student\s*(?:body|population)[:\s]+(\d{1,3}(?:,\d{3})*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        return None
    
    def _extract_grade_levels(self, soup: BeautifulSoup) -> List[str]:
        """Extract grade levels served by the school"""
        text = soup.get_text()
        
        grade_patterns = [
            r'(K|g?rad?e?)\s*(?:levels?\s*)?(\d+(?:\s*[-–to]+\s*\d+)?)',
            r'(?:PK|Pre-K|Pre-Kindergarten|KG?|Kindergarten|Elementary|Middle|Junior\s*High|High\s*School)',
            r'grades?\s*(\d+)\s*[-–to]*\s*(\d+)',
        ]
        
        grades = []
        for pattern in grade_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    grades.extend([g.strip() for g in match if g.strip() and len(g.strip()) < 10])
                else:
                    if match.strip() and len(match.strip()) < 10:
                        grades.append(match.strip())
        
        return list(set(grades))[:6]  # Return unique grades, max 6
    
    def _extract_mascot(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract school mascot if visible"""
        text = soup.get_text()
        
        mascot_patterns = [
            r'(?:mascot|team\s*name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:is\s+)?(?:our\s+)?mascot',
        ]
        
        for pattern in mascot_patterns:
            match = re.search(pattern, text)
            if match:
                mascot = match.group(1)
                # Filter out common false positives
                if mascot and mascot not in ['School', 'District', 'The', 'Our', 'This']:
                    return mascot
        return None
    
    def _extract_colors(self, soup: BeautifulSoup) -> List[str]:
        """Extract school colors if mentioned"""
        text = soup.get_text()
        
        color_pattern = r'\b(blue|red|green|white|black|gold|yellow|orange|purple|maroon|' \
                       r'navy|scarlet|gray|grey|silver|bronze|cardinal|royal)\b'
        
        colors = re.findall(color_pattern, text, re.IGNORECASE)
        return list(set(c.casefold() for c in colors))[:3]
    
    async def _find_news_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Identify news/article pages"""
        patterns = ['news', 'announcements', 'updates', 'latest', 'blog', 'events']
        pages = []
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            
            if any(pattern in href or pattern in text for pattern in patterns):
                full_url = link['href'] if link['href'].startswith('http') else \
                          f"{base_url.rstrip('/')}/{link['href'].lstrip('/')}"
                if full_url not in pages:
                    pages.append(full_url)
        
        return pages[:5]
    
    async def _extract_news_items(self, url: str) -> List[Dict[str, str]]:
        """Extract recent news items from news page"""
        async with self.session.get(url) as response:
            html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        articles = soup.find_all(['article', 'div'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['news', 'post', 'article', 'item', 'entry']))
        
        for article in articles[:5]:
            try:
                title_elem = article.find(['h2', 'h3', 'h4'])
                date_elem = article.find(['time', 'span', 'div'], 
                                         class_=lambda x: x and 'date' in str(x).lower())
                
                if title_elem:
                    items.append({
                        'title': title_elem.get_text(strip=True),
                        'date': date_elem.get_text(strip=True) if date_elem else '',
                        'url': url
                    })
            except Exception:
                continue
        
        return items
    
    async def _find_leadership_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Identify leadership/administration pages"""
        patterns = ['leadership', 'administration', 'board', 'superintendent', 'principal']
        pages = []
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            
            if any(pattern in href or pattern in text for pattern in patterns):
                full_url = link['href'] if link['href'].startswith('http') else \
                          f"{base_url.rstrip('/')}/{link['href'].lstrip('/')}"
                if full_url not in pages:
                    pages.append(full_url)
        
        return pages[:3]
    
    async def _extract_leadership_info(self, url: str) -> List[Dict[str, str]]:
        """Extract leadership information"""
        async with self.session.get(url) as response:
            html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        leaders = []
        
        # Look for leadership bios or profiles
        profiles = soup.find_all(['article', 'div'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['profile', 'bio', 'leader', 'administrator']))
        
        for profile in profiles[:5]:
            try:
                name_elem = profile.find(['h2', 'h3', 'h4'])
                title_elem = profile.find(class_=lambda x: x and 'title' in str(x).lower())
                
                if name_elem:
                    leaders.append({
                        'name': name_elem.get_text(strip=True),
                        'title': title_elem.get_text(strip=True) if title_elem else '',
                        'url': url
                    })
            except Exception:
                continue
        
        return leaders
    
    async def _find_programs_page(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Find academic programs page"""
        patterns = ['academics', 'programs', 'curriculum', 'courses', 'instruction']
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            
            if any(pattern in href or pattern in text for pattern in patterns):
                full_url = link['href'] if link['href'].startswith('http') else \
                          f"{base_url.rstrip('/')}/{link['href'].lstrip('/')}"
                return full_url
        
        return None
    
    async def _extract_programs(self, url: str) -> List[str]:
        """Extract academic program offerings"""
        async with self.session.get(url) as response:
            html = await response.text()
        
        soup = BeautifulSoup(html, 'html.parser')
        programs = []
        
        # Look for program listings
        items = soup.find_all(['li', 'div'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['program', 'course', 'offering', 'pathway']))
        
        for item in items[:15]:
            text = item.get_text(strip=True)
            if 5 < len(text) < 80:
                programs.append(text)
        
        # Also look for headings indicating program areas
        headings = soup.find_all(['h2', 'h3', 'h4'], 
                                  string=lambda x: x and any(term in x.lower() 
                                  for term in ['program', 'department', 'academy', 'pathway']))
        
        for heading in headings[:10]:
            text = heading.get_text(strip=True)
            if 5 < len(text) < 50 and text not in programs:
                programs.append(text)
        
        return list(set(programs))[:10]
    
    def _deduplicate_contacts(self, contacts: List[SchoolContact]) -> List[SchoolContact]:
        """Remove duplicate contacts based on email address"""
        seen = set()
        unique = []
        
        for contact in contacts:
            if contact.email and contact.email not in seen:
                seen.add(contact.email)
                unique.append(contact)
        
        return unique
```

### Contextual Data Enhancement by Role
Different administrative roles require different contextual data for effective personalization. Your scraping code should prioritize data collection based on target role relevance, ensuring that high-priority contacts receive thoroughly researched outreach while lower-priority contacts receive appropriately simplified personalization.

**For Superintendent Outreach**
Superintendent-level personalization requires district-wide context including enrollment figures, budget information, board composition, and recent policy decisions. Your scraper should prioritize extracting superintendent biographies from board pages, district strategic plans, and community announcements. References to specific board initiatives, community engagement events, or district achievements demonstrate research and resonate with executives who operate under constant board and community scrutiny.

Superintendent emails should reference recent board meeting topics visible in meeting minutes, demographic trends affecting the district, state funding issues relevant to their context, and community priorities that emerge from school communications. The tone should be executive-level and concise, respecting that superintendents receive enormous email volume and make rapid initial triage decisions about which messages warrant attention.

**For Principal Outreach**
Principal personalization focuses on building-level dynamics including recent school achievements, staff changes, facility improvements, and community events. Your scraper should extract information from school news sections, event calendars, and the principal's own communications to parents and staff. References to specific programs, student accomplishments, or community initiatives show that your outreach relates to their actual environment rather than generic educational messaging.

Principal emails should emphasize operational efficiency, teacher support, and parent satisfaction—concerns that consume their daily attention. The tone should be warm but professional, acknowledging the demanding nature of building-level leadership while demonstrating that you understand their specific challenges.

**For Curriculum Director Outreach**
Curriculum director personalization centers on academic programs, instructional initiatives, and pedagogical priorities. Your scraper should extract curriculum maps, program descriptions, teacher bios with instructional expertise, and state standard alignments visible on school websites. References to specific courses, teaching methodologies, or academic competitions demonstrate that your outreach understands their instructional focus.

Curriculum director emails should emphasize pedagogical alignment, teacher training support, and evidence-based outcomes. The tone should be professionally informed, demonstrating familiarity with educational terminology and current instructional trends without becoming overly technical or academic.

**For Federal Program Director Outreach**
Federal program director personalization focuses on compliance requirements, grant optimization, and accountability documentation. Your scraper should extract information about Title I status, grant awards, school improvement initiatives, and federal program participation visible in school reports and announcements. References to specific compliance deadlines, audit findings, or performance metrics demonstrate understanding of their high-pressure compliance environment.

Federal program director emails should emphasize accountability features, documentation capabilities, and compliance support. The tone should be efficiency-focused and detail-oriented, acknowledging the constant pressure they face while positioning Ivybound as a solution that reduces their administrative burden.

## Part Three: Hyper-Personalized Email Campaigns by Role
Each administrative role receives a four-email sequence calibrated to their priorities and communication preferences. The sequences progress from value-first introduction through increasingly direct engagement requests, with all emails maintaining the hyper-personalization that distinguishes your campaign from generic educational vendor outreach.

### Superintendent Campaign Sequence
Superintendents evaluate educational partnerships through a strategic lens focused on district-wide impact, board relations, and community outcomes. Email sequences targeting superintendents must speak to these executive concerns while demonstrating research into their specific district context.

**Email One: Strategic Value Introduction**
```text
Subject: Quick question about [District Name]'s course offering strategy

Hi [Name],

I noticed [District Name] recently [recent news item or initiative from school website], which reflects the forward-thinking approach your district takes on educational delivery.

We're working with districts like [neighboring comparable district] to expand course offerings without adding teaching staff—by sharing existing high-quality courses with partner districts for a per-seat fee that generates revenue while serving more students.

For a district of [District Name]'s size, this approach typically generates 50,000−150,000 in annual revenue per shared course, with zero operational overhead for your team.

Would you have 10 minutes for a brief call to explore whether this model could work for [District Name]?

Best regards,

[Your Name]
```

**Email Two: Social Proof and Specific Value**
```text
Subject: How [Similar District] increased course access by 40%

Hi [Name],

Following up on my previous note—I wanted to share how [Comparable District] solved a similar challenge last year.

Their challenge: Strong AP and elective programs but not enough students to justify hiring specialized teachers. Their solution: Partnered with three neighboring districts to share course access, generating $85,000 in new revenue while actually improving student course selection by 40%.

I put together a simple revenue model for [District Name] showing what this could look like with your current course catalog. Want me to send it over?

No pressure—just thought you might find the numbers interesting.

Best,

[Your Name]
```

**Email Three: Soft Ask**
```text
Subject: Worth exploring for [District Name]'s next board cycle?

Hi [Name],

I understand board cycles and budget planning consume significant attention this time of year. I wanted to briefly surface this opportunity before your planning window closes.

The course-sharing model requires no capital investment, no new staff, and can be implemented within your existing board policies. Districts typically need 4-6 weeks from initial conversation to board presentation.

Would it make sense to schedule a 15-minute call next week so I can walk you through the numbers? Happy to work around your schedule.

Best regards,

[Your Name]
```

**Email Four: Final Touch and Transition**
```text
Subject: One last thought on revenue optimization for [District Name]

Hi [Name],

I'll keep this brief. I know your inbox is crowded, and if this isn't the right time for [District Name], I completely understand.

If you might be open to it, I'm happy to send over a one-page overview that you could share with your curriculum team for initial feedback. No follow-up commitment required—just information.

Alternatively, if there's someone on your team who handles course scheduling or district partnerships, I'd welcome the opportunity to connect with them.

Either way, I appreciate your time and wish [District Name] continued success.

Best,

[Your Name]
```

### Principal Campaign Sequence
Principals evaluate new programs through an operational lens focused on implementation complexity, teacher burden, and parent reception. Email sequences targeting principals must address these practical concerns while demonstrating familiarity with their specific school context.

**Email One: Operational Value Introduction**
```text
Subject: Quick observation about [School Name]'s academic program

Hi [Name],

I was reviewing [School Name]'s [specific program or initiative visible on website] and noticed the strong emphasis on [specific academic focus]. The approach you're taking with [specific program element] reflects the kind of innovative thinking that creates real engagement for students.

We're helping schools like yours expand academic offerings without adding to teacher workloads. Through our course-sharing partnerships, schools gain access to AP and elective courses they couldn't otherwise offer—delivered by our Top 1% instructors while your teachers focus on core instruction.

Would you be open to a brief call to explore whether this could help [School Name] serve more students next semester?

Best regards,

[Your Name]
```

**Email Two: Implementation Focus**
```text
Subject: How [Nearby School] added 5 new courses without hiring

Hi [Name],

Following up—I wanted to share how [Nearby School with comparable demographics] solved their course gap challenges last fall.

Their situation was similar to [School Name]: strong demand for AP and elective courses but not enough students to justify dedicated sections. They implemented our course-sharing program and added 5 new courses—including AP Calculus and Digital Arts—that their teachers didn't have capacity to build themselves.

Implementation took two weeks, required zero teacher training, and parents have been enthusiastic about the expanded options.

Can I send you a quick case study with the details?

Best,

[Your Name]
```

**Email Three: Teacher Support Emphasis**
```text
Subject: Reducing teacher workload while expanding offerings

Hi [Name],

I know your teachers are stretched thin supporting [specific initiative or challenge visible on website]. Adding new courses typically means more prep time, more grading, more everything—on top of already-full plates.

Our model handles all of that. Your students get access to rigorous, well-structured courses taught by specialists, while your teachers maintain their focus on the classes they're already teaching.

No additional meetings, no curriculum development, no teacher training required. Just expanded options for your students.

15 minutes to discuss? Happy to work around your schedule.

Best regards,

[Your Name]
```

**Email Four: Simple Ask**
```text
Subject: One question about [School Name]'s course catalog

Hi [Name],

I'll make this quick. If [School Name] could add 3-5 new courses to next year's catalog—AP Physics, Spanish Literature, Computer Science, whatever your students are asking for—without adding any demands on your teachers, would you be interested in learning more?

If yes, I can send information or schedule a brief call. If not, no worries at all—just wanted to reach out.

Either way, best of luck with [current school initiative or event visible on website].

Best,

[Your Name]
```

### Curriculum Director Campaign Sequence
Curriculum directors evaluate educational partnerships through a pedagogical lens focused on instructional quality, standard alignment, and teacher adoption. Email sequences targeting curriculum directors must demonstrate pedagogical sophistication while addressing their specific instructional priorities.

**Email One: Instructional Quality Introduction**
```text
Subject: Question about [School/District Name]'s [specific subject area] curriculum

Hi [Name],

I reviewed [School/District Name]'s curriculum framework for [specific subject area] and was impressed by the emphasis on [specific pedagogical approach visible on website]. The way you're approaching [specific program element] aligns with best practices in [related instructional methodology].

We're partnering with districts to deliver high-quality [subject area] instruction through our network of Top 1% instructors—educators who bring advanced degrees and specialized expertise that many districts struggle to access.

For curriculum leaders facing teacher shortages in specialized areas, our model provides rigorous, standards-aligned instruction without the recruitment burden.

Would you have 15 minutes for a conversation about how this might complement [School/District Name]'s instructional priorities?

Best regards,

[Your Name]
```

[Emails 2-4 continue with similar detailed formatting as provided in the outline]

### Federal Program Director Campaign Sequence
Federal program directors evaluate partnerships through a compliance lens focused on documentation, accountability, and grant optimization. Email sequences targeting these coordinators must emphasize regulatory compliance, progress tracking, and the ability to demonstrate results to federal overseers.

**Email One: Compliance Value Introduction**
```text
Subject: Supporting [Program Type, e.g., Title I] compliance at [School/District Name]

Hi [Name],

Managing federal program compliance while serving student needs is a significant challenge—I understand the pressure to document outcomes, maximize funding impact, and prepare for audits without adding administrative burden.

We're partnering with districts to support their [Title I/Title II/IDEA] programs through structured course delivery that provides comprehensive progress tracking and documentation. Our platform generates the kind of detailed outcome reports that simplify compliance reporting and support grant renewal arguments.

For federal program coordinators, this means spending less time on documentation and more time on the strategic work that actually moves the needle for students.

Would a brief call help you evaluate whether this could support [School/District Name]'s compliance objectives?

Best regards,

[Your Name]
```

## Part Four: Reply Handling and Qualification System
Your campaign routes all replies to `andrew@web4guru.com` for manual qualification and follow-up. This section outlines the qualification criteria, response templates, and pipeline management approach that transforms reply volume into productive conversations.

### Reply Alert Configuration
Configure Mailreef to forward all replies to `andrew@web4guru.com` immediately upon receipt. Include original email content, sender information, and engagement timestamps in the forwarded message. For high reply volumes, implement label-based filtering that categorizes incoming replies by sender role for efficient batch processing.

The alert system should capture enough context for immediate qualification without requiring login to the email platform. Each forwarded reply should include the recipient's name, role, school, the specific email they replied to, and their reply content in a format that enables rapid assessment.

### Qualification Criteria Matrix
Evaluate each reply against the following criteria to determine priority and appropriate next steps.

**High Priority Indicators**
Responses that indicate immediate interest in learning more deserve immediate follow-up. Look for phrases like "Tell me more," "Send the information," "I'm interested," or "When can we talk?" The presence of specific questions about the offering, requests for pricing or implementation timelines, or indications of budget authority or timeline urgency all suggest qualified interest worth pursuing urgently.

**Medium Priority Indicators**
Responses that ask clarifying questions, request additional information, or indicate potential interest without commitment represent medium priority. These contacts are curious but not yet convinced, requiring nurturing follow-up that addresses their specific concerns while moving them toward commitment. Look for questions about specific features, requests for case studies or references, or indications that the timing isn't right but interest exists.

**Low Priority Indicators**
Responses that express polite decline, indicate wrong timing without future interest, or ask questions unrelated to the offering represent low priority. Politely declined contacts should receive a brief acknowledgment and invitation to reconnect in the future if circumstances change. Unrelated inquiries may be forwarded to appropriate parties or acknowledged briefly and archived.

**Negative Indicators**
Responses that complain about cold email, request removal from lists, or express frustration about outreach should be processed immediately to honor their request and prevent further contact. These responses require no follow-up beyond list removal confirmation.

### Reply Qualification Categories
| Category | Priority | Response Time | Action |
|----------|----------|---------------|--------|
| Immediate Interest | Critical | Within 1 hour | Personal call or detailed response |
| Questions/Clarification | High | Within 4 hours | Direct answer with next steps |
| Request for Materials | Medium | Within 24 hours | Send materials with soft ask |
| Future Interest | Medium | Within 48 hours | Add to nurture sequence |
| Polite Decline | Low | Within 72 hours | Brief acknowledgment, archive |
| Negative/Spam Report | Urgent | Immediate | Remove from lists, apologize |

### Response Templates
**High Interest Response Template**
```text
Subject: Re: [Original Subject Line]

Hi [Name],

Thank you for your interest in learning more about how Ivybound can support [School/District Name].

[Personalize based on their questions or their specific context from your data]

To move forward, I'd suggest a brief 15-minute call where I can answer your questions directly and share specific examples from comparable districts. Does [date/time] or [alternative date/time] work for you? Happy to work around your schedule.

Looking forward to connecting,

[Your Name]
```

## Part Five: Complete Budget Summary
This section consolidates all costs into the final budget structure for implementation.

### One-Time Upfront Costs
| Item | Cost | Notes |
|------|------|-------|
| 30 Sending Domains | $240 | Annual registration through budget providers |
| Email Validation Credits | $100 | MillionVerifier 100k credit pack |
| **Total Upfront** | **$340** | |

### Monthly Recurring Costs
| Component | Monthly Cost | Function |
|-----------|--------------|----------|
| Mailreef Agency Flex | $249 | Primary sending platform with API access |
| Mailreef Usage Fees | $100 | $0.001 per email for 100,000 monthly sends |
| Smartlead Unlimited | $97 | Automated inbox warming and deliverability |
| OpenAI GPT-4o-mini API | $18 | AI-generated hyper-personalized email content |
| Reply Alert Handling | $0 | Manual processing through andrew@web4guru.com |
| **Total Monthly** | **$464** | |

### Budget Summary
| Metric | Value |
|--------|-------|
| One-Time Setup | $340 |
| Monthly Operating | $464 |
| Monthly Email Volume | 100,000 |
| Cost Per Email | $0.00464 |
| Annual Investment | $5,908 |

## Part Six: Implementation Checklist

### Infrastructure Setup
- [ ] Register 30 sending domains through budget provider
- [ ] Configure SPF, DKIM, and DMARC for all domains
- [ ] Set up Mailreef Agency Flex account and API access
- [ ] Connect Smartlead and configure inbox warming protocols
- [ ] Configure OpenAI API access and test prompt templates
- [ ] Set up `andrew@web4guru.com` reply handling workflow
- [ ] Validate full contact database with MillionVerifier

### Campaign Development
- [ ] Segment 100,000 contacts by administrative role
- [ ] Develop role-specific prompt libraries for AI content generation
- [ ] Create email sequences for each target role
- [ ] Configure Mailreef campaign structure with sub-accounts
- [ ] Set up A/B testing framework for subject lines and content
- [ ] Establish reply qualification workflow and templates

### Launch Sequence
- [ ] Begin inbox warming through Smartlead (14-21 days)
- [ ] Launch small-scale test send (5,000 emails)
- [ ] Monitor deliverability metrics and engagement rates
- [ ] Adjust sending volume based on performance data
- [ ] Scale to full 100,000 monthly volume over 4 weeks
- [ ] Implement ongoing optimization based on reply data
