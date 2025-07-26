@import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import time
import random
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import urllib.parse
import re
from difflib import SequenceMatcher

def extract_job_id_from_url(url):
    """Extract LinkedIn job ID from URL"""
    # Pattern to match LinkedIn job IDs
    patterns = [
        r'/jobs/view/(\d+)',
        r'jobId=(\d+)',
        r'/job/(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def normalize_linkedin_url(url):
    """Remove tracking parameters from LinkedIn URLs"""
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Remove tracking parameters
    query_params = urllib.parse.parse_qs(parsed.query)
    
    # Keep only essential parameters, remove tracking ones
    tracking_params_to_remove = [
        'refId', 'trackingId', 'position', 'pageNum', 'origin', 
        'trk', 'originalSubdomain', 'currentJobId', 'lipi'
    ]
    
    clean_params = {}
    for key, values in query_params.items():
        if key not in tracking_params_to_remove:
            clean_params[key] = values
    
    # Reconstruct URL without tracking parameters
    clean_query = urllib.parse.urlencode(clean_params, doseq=True)
    clean_url = urllib.parse.urlunparse((
        parsed.scheme, parsed.netloc, parsed.path, 
        parsed.params, clean_query, ''
    ))
    
    return clean_url

def calculate_job_similarity(job1, job2):
    """Calculate similarity score between two jobs"""
    # Compare titles
    title_similarity = SequenceMatcher(None, 
        job1['title'].lower(), 
        job2['title'].lower()
    ).ratio()
    
    # Compare companies
    company_similarity = SequenceMatcher(None,
        job1['company'].lower(),
        job2['company'].lower()
    ).ratio()
    
    # Compare locations
    location_similarity = SequenceMatcher(None,
        job1['location'].lower(),
        job2['location'].lower()
    ).ratio()
    
    # Weighted average
    overall_similarity = (title_similarity * 0.6 + 
                         company_similarity * 0.3 + 
                         location_similarity * 0.1)
    
    return overall_similarity

def remove_similar_jobs(jobs, similarity_threshold=0.85):
    """Remove jobs that are too similar to existing ones"""
    unique_jobs = []
    
    for job in jobs:
        is_similar = False
        
        for existing_job in unique_jobs:
            similarity = calculate_job_similarity(job, existing_job)
            
            if similarity > similarity_threshold:
                print(f"Similar job found ({similarity:.2f}): {job['title']} at {job['company']}")
                is_similar = True
                break
        
        if not is_similar:
            unique_jobs.append(job)
    
    return unique_jobs

def scrape_linkedin_jobs_24h(keywords, location, max_jobs=50):
    """
    Scrape LinkedIn jobs from the past 24 hours with fixed URL handling
    """
    jobs = []
    
    # LinkedIn's public job search endpoint
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    
    # Headers to mimic a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.linkedin.com/jobs/search",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate"
    }
    
    # Search parameters
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR": "r86400",  # Past 24 hours filter
        "sortBy": "DD",     # Sort by date (most recent first)
        "start": 0
    }
    
    # Calculate number of pages (25 jobs per page)
    max_pages = min(3, (max_jobs // 25) + 1)  # Conservative limit
    
    print(f"Searching for '{keywords}' jobs in '{location}' from past 24 hours...")
    
    for page in range(max_pages):
        params["start"] = page * 25
        
        try:
            print(f"Fetching page {page + 1}...")
            response = requests.get(base_url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Find all job cards
                job_cards = soup.find_all("li")
                
                page_jobs = 0
                for card in job_cards:
                    try:
                        # Extract job link - FIXED VERSION
                        link_elem = card.find("a", {"data-tracking-control-name": "public_jobs_jserp-result_search-card"})
                        if not link_elem:
                            continue
                        
                        # Get href and clean it properly
                        raw_href = link_elem.get("href", "")
                        if not raw_href:
                            continue
                        
                        # Fix malformed URLs
                        if raw_href.startswith("https://"):
                            # URL is already complete
                            clean_link = raw_href
                        elif raw_href.startswith("/jobs/view/"):
                            # Relative URL - add LinkedIn domain
                            clean_link = "https://www.linkedin.com" + raw_href
                        else:
                            # Malformed or unusual format - extract job ID
                            job_id = raw_href.split("/")[-1].split("?")[0]
                            clean_link = f"https://www.linkedin.com/jobs/view/{job_id}"
                        
                        # Remove duplicate domains if present
                        clean_link = clean_link.replace("https://www.linkedin.comhttps://", "https://")
                        clean_link = clean_link.replace("https://www.linkedin.com//", "https://www.linkedin.com/")
                        
                        # Extract job title
                        title_elem = card.find("h3", class_="base-search-card__title")
                        if not title_elem:
                            continue
                            
                        # Extract company name
                        company_elem = card.find("h4", class_="base-search-card__subtitle")
                        
                        # Extract location
                        location_elem = card.find("span", class_="job-search-card__location")
                        
                        # Extract posting date
                        date_elem = card.find("time")
                        
                        # Check for Easy Apply
                        easy_apply_elem = card.find("span", string=lambda text: text and "Easy Apply" in text if text else False)
                        has_easy_apply = easy_apply_elem is not None
                        
                        # Clean and format the data
                        job_data = {
                            "title": title_elem.get_text().strip(),
                            "company": company_elem.get_text().strip() if company_elem else "N/A",
                            "location": location_elem.get_text().strip() if location_elem else location,
                            "link": clean_link,
                            "date_posted": date_elem.get("datetime", "N/A") if date_elem else "N/A",
                            "search_keywords": keywords,
                            "easy_apply": has_easy_apply,
                            "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        jobs.append(job_data)
                        page_jobs += 1
                        
                        if len(jobs) >= max_jobs:
                            break
                            
                    except Exception as e:
                        print(f"Error parsing job card: {e}")
                        continue
                
                print(f"Found {page_jobs} jobs on page {page + 1}")
                
                if len(jobs) >= max_jobs:
                    break
                    
            else:
                print(f"Request failed with status code: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error fetching page {page + 1}: {e}")
            break
            
        # Random delay between requests (important for avoiding rate limits)
        delay = random.uniform(3, 7)
        print(f"Waiting {delay:.1f} seconds before next request...")
        time.sleep(delay)
    
    print(f"Total jobs found: {len(jobs)}")
    return jobs

def remove_duplicates(jobs):
    """Enhanced deduplication using multiple criteria"""
    unique_jobs = []
    seen_combinations = set()
    seen_job_ids = set()
    seen_titles_companies = set()
    
    print(f"Starting deduplication of {len(jobs)} jobs...")
    
    for job in jobs:
        # Extract job ID from LinkedIn URL
        job_id = extract_job_id_from_url(job['link'])
        
        # Create a combination key for title + company
        title_company_key = f"{job['title'].lower().strip()}|{job['company'].lower().strip()}"
        
        # Create a normalized URL without tracking parameters
        base_url = normalize_linkedin_url(job['link'])
        
        # Check multiple deduplication criteria
        duplicate_found = False
        
        # 1. Check by Job ID (most reliable)
        if job_id and job_id in seen_job_ids:
            duplicate_found = True
            print(f"Duplicate by Job ID: {job['title']} at {job['company']}")
        
        # 2. Check by Title + Company combination
        elif title_company_key in seen_titles_companies:
            duplicate_found = True
            print(f"Duplicate by Title+Company: {job['title']} at {job['company']}")
        
        # 3. Check by normalized URL
        elif base_url in seen_combinations:
            duplicate_found = True
            print(f"Duplicate by URL: {job['title']} at {job['company']}")
        
        if not duplicate_found:
            unique_jobs.append(job)
            if job_id:
                seen_job_ids.add(job_id)
            seen_titles_companies.add(title_company_key)
            seen_combinations.add(base_url)
    
    removed_count = len(jobs) - len(unique_jobs)
    print(f"✅ Removed {removed_count} duplicates, kept {len(unique_jobs)} unique jobs")
    
    return unique_jobs

def filter_jobs(jobs, config):
    """Apply enhanced filters for senior-level product management roles"""
    filtered_jobs = []
    current_time = datetime.now()
    
    for job in jobs:
        # Skip excluded companies
        if any(company.lower() in job['company'].lower() 
               for company in config.get('companies_to_exclude', [])):
            continue
        
        # ENHANCED SENIORITY FILTERING
        job_text = f"{job['title']} {job['company']}".lower()
        
        # Check for junior-level exclusions
        if config.get('exclude_junior_keywords'):
            has_junior = any(keyword.lower() in job_text 
                           for keyword in config['exclude_junior_keywords'])
            if has_junior:
                print(f"Skipping junior role: {job['title']}")
                continue
        
        # Check for senior-level indicators
        seniority_score = 0
        if config.get('seniority_keywords'):
            for keyword in config['seniority_keywords']:
                if keyword.lower() in job_text:
                    seniority_score += 1
        
        # Require minimum seniority score for inclusion
        if seniority_score < 1:  # At least 1 senior indicator required
            print(f"Skipping non-senior role: {job['title']} (score: {seniority_score})")
            continue
        
        # Location preference scoring (India first)
        location_score = 0
        job_location = job['location'].lower()
        if 'india' in job_location:
            location_score += 10  # High preference for India
        elif 'mumbai' in job_location or 'bangalore' in job_location or 'delhi' in job_location:
            location_score += 15  # Even higher for major Indian cities
        elif 'remote' in job_location:
            location_score += 5   # Medium preference for remote
        
        # TIME-BASED FILTERING
        if config.get('time_filters'):
            time_config = config['time_filters']
            
            try:
                if job['date_posted'] != "N/A":
                    if 'T' in job['date_posted']:
                        job_date = datetime.fromisoformat(job['date_posted'].replace('Z', '+00:00'))
                        job_date = job_date.replace(tzinfo=None)
                    else:
                        job_date = datetime.strptime(job['date_posted'][:10], '%Y-%m-%d')
                    
                    hours_old = (current_time - job_date).total_seconds() / 3600
                    
                    max_hours = time_config.get('max_hours_old', 24)
                    if hours_old > max_hours:
                        continue
                    
                    # Freshness scoring
                    preferred_hours = time_config.get('preferred_hours_old', 12)
                    if hours_old <= preferred_hours:
                        job['freshness_score'] = 10
                    elif hours_old <= 24:
                        job['freshness_score'] = 5
                    else:
                        job['freshness_score'] = 1
                        
                    job['hours_since_posted'] = round(hours_old, 1)
                    
            except Exception as e:
                job['freshness_score'] = 1
                job['hours_since_posted'] = "Unknown"
        
        # Check for required keywords
        if config.get('required_keywords'):
            has_required = any(keyword.lower() in job_text 
                             for keyword in config['required_keywords'])
            if not has_required:
                continue
        
        # Calculate comprehensive scoring
        job['seniority_score'] = seniority_score
        job['location_score'] = location_score
        job['relevance_score'] = seniority_score  # For backward compatibility
        
        # Total score combines seniority, location, and freshness
        total_score = (seniority_score * 3) + location_score + job.get('freshness_score', 1)
        job['total_score'] = total_score
        
        filtered_jobs.append(job)
    
    # Sort by total score (highest first), then by posting time (newest first)
    filtered_jobs.sort(key=lambda x: (x['total_score'], -x.get('hours_since_posted', 999)), reverse=True)
    
    print(f"Filtered to {len(filtered_jobs)} senior-level product management jobs")
    return filtered_jobs

def categorize_jobs(jobs):
    """Categorize jobs by type for better organization"""
    categories = {
        'senior': [],
        'mid_level': [],
        'entry_level': [],
        'remote': [],
        'other': []
    }
    
    for job in jobs:
        title_lower = job['title'].lower()
        location_lower = job['location'].lower()
        
        # Categorize by seniority
        if any(word in title_lower for word in ['senior', 'lead', 'principal', 'staff', 'director', 'vp', 'head', 'chief']):
            categories['senior'].append(job)
        elif any(word in title_lower for word in ['junior', 'entry', 'associate', 'graduate']):
            categories['entry_level'].append(job)
        elif 'remote' in location_lower or 'remote' in title_lower:
            categories['remote'].append(job)
        else:
            categories['mid_level'].append(job)
    
    return categories

def save_to_csv(jobs, filename):
    """Save jobs to CSV file"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    if not jobs:
        print("No jobs to save")
        return
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)
    
    print(f"Saved {len(jobs)} jobs to {filename}")

def create_html_report(jobs, filename, title="LinkedIn Jobs Report"):
    """Create an HTML report for easy viewing"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Group jobs by category for better organization
    categories = categorize_jobs(jobs)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .header {{
                background: linear-gradient(135deg, #0077b5, #00a0dc);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .stats {{
                display: flex;
                justify-content: space-around;
                margin: 20px 0;
                flex-wrap: wrap;
            }}
            .stat-box {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin: 5px;
                text-align: center;
                min-width: 120px;
            }}
            .category {{
                margin: 30px 0;
            }}
            .category-title {{
                color: #0077b5;
                border-bottom: 2px solid #0077b5;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            .job {{
                background: white;
                border: 1px solid #e1e5e9;
                margin: 15px 0;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                transition: box-shadow 0.3s ease;
            }}
            .job:hover {{
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            .job-title {{
                color: #0077b5;
                font-weight: bold;
                font-size: 18px;
                margin-bottom: 8px;
            }}
            .job-title a {{
                color: #0077b5;
                text-decoration: none;
            }}
            .job-title a:hover {{
                text-decoration: underline;
            }}
            .company {{
                color: #666;
                font-weight: 500;
                margin-bottom: 5px;
            }}
            .location {{
                color: #888;
                font-size: 14px;
                margin-bottom: 5px;
            }}
            .date {{
                color: #999;
                font-size: 12px;
            }}
            .easy-apply {{
                background: #28a745;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                margin-left: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{title}</h1>
            <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <h3>{len(jobs)}</h3>
                <p>Total Jobs</p>
            </div>
            <div class="stat-box">
                <h3>{len(categories['senior'])}</h3>
                <p>Senior Level</p>
            </div>
            <div class="stat-box">
                <h3>{len(categories['mid_level'])}</h3>
                <p>Mid Level</p>
            </div>
            <div class="stat-box">
                <h3>{len(categories['entry_level'])}</h3>
                <p>Entry Level</p>
            </div>
            <div class="stat-box">
                <h3>{len(categories['remote'])}</h3>
                <p>Remote</p>
            </div>
        </div>
    """
    
    # Add jobs by category
    for category_name, category_jobs in categories.items():
        if category_jobs:
            html_content += f"""
            <div class="category">
                <h2 class="category-title">{category_name.replace('_', ' ').title()} Jobs ({len(category_jobs)})</h2>
            """
            
            for job in category_jobs:
                hours_old = job.get('hours_since_posted', 'Unknown')
                if isinstance(hours_old, (int, float)) and hours_old <= 6:
                    time_badge = f'<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 5px;">🔥 {hours_old}h ago</span>'
                elif isinstance(hours_old, (int, float)) and hours_old <= 12:
                    time_badge = f'<span style="background: #ffc107; color: black; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 5px;">⚡ {hours_old}h ago</span>'
                elif isinstance(hours_old, (int, float)):
                    time_badge = f'<span style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 5px;">🕒 {hours_old}h ago</span>'
                else:
                    time_badge = ''
                
                easy_apply_badge = '<span class="easy-apply">✅ Easy Apply</span>' if job.get('easy_apply', False) else ''
                
                html_content += f"""
                <div class="job">
                    <div class="job-title">
                        <a href="{job['link']}" target="_blank">{job['title']}</a>
                        {time_badge}
                        {easy_apply_badge}
                    </div>
                    <div class="company">{job['company']}</div>
                    <div class="location">📍 {job['location']}</div>
                    <div class="date">🕒 Posted: {job['date_posted']}</div>
                </div>
                """
            
            html_content += "</div>"
    
    html_content += """
    </body>
    </html>
    """
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML report saved to {filename}")

def send_daily_job_email(jobs, sender_email, sender_password, receiver_email, html_report_path=None):
    """Send daily job report via email with link to full HTML report"""
    if not jobs:
        print("No jobs to email")
        return False
    
    # Sort jobs by time (earliest first) and limit to top 30
    sorted_jobs = sorted(jobs, key=lambda x: x.get('hours_since_posted', 999))
    top_jobs = sorted_jobs[:30]
    remaining_count = max(0, len(jobs) - 30)
    
    print(f"📧 Emailing top {len(top_jobs)} jobs (earliest first) out of {len(jobs)} total")
    
    # Convert file path to proper format for email link
    if html_report_path:
        # Convert Windows path to file URL
        file_url = f"file:///{html_report_path.replace('\\', '/').replace(' ', '%20')}"
        report_filename = os.path.basename(html_report_path)
    else:
        file_url = "#"
        report_filename = "report.html"
    
    # Create HTML email content with prominent report link
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
            .header {{ background: #0077b5; color: white; padding: 20px; text-align: center; border-radius: 8px; }}
            .report-link {{ 
                background: #28a745; 
                color: white; 
                padding: 20px; 
                text-align: center; 
                border-radius: 8px; 
                margin: 20px 0;
                border: none;
            }}
            .report-link a {{ 
                color: white; 
                text-decoration: none; 
                font-weight: bold; 
                font-size: 18px;
                display: block;
            }}
            .job {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
            .job-title {{ color: #0077b5; font-weight: bold; font-size: 16px; margin-bottom: 5px; }}
            .company {{ color: #666; margin: 5px 0; }}
            .fresh-job {{ background-color: #e8f4f8; }}
            .easy-apply {{ background: #0077b5; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🎯 Daily Senior Product Management Jobs</h2>
            <p>Top {len(top_jobs)} opportunities (sorted by posting time)</p>
            <p>{datetime.now().strftime('%B %d, %Y')}</p>
            {f'<p style="font-size: 14px;">({remaining_count} more jobs in full report)</p>' if remaining_count > 0 else ''}
        </div>
        
        <div class="report-link">
            <a href="{file_url}" target="_blank">
                📊 CLICK HERE: View Complete Report ({len(jobs)} jobs)
            </a>
            <p style="margin: 10px 0 0 0; font-size: 14px;">
                File: {report_filename}
            </p>
        </div>
        
        <h3 style="color: #0077b5; border-bottom: 2px solid #0077b5; padding-bottom: 5px;">
            🕒 Latest Jobs (Sorted by Posting Time - Earliest First)
        </h3>
    """
    
    # Add jobs sorted by time
    for i, job in enumerate(top_jobs, 1):
        hours_ago = job.get('hours_since_posted', 'Unknown')
        easy_apply = job.get('easy_apply', False)
        
        # Time-based styling
        if isinstance(hours_ago, (int, float)) and hours_ago <= 6:
            job_class = "job fresh-job"
            time_badge = f'<span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 12px; font-size: 11px;">🔥 {hours_ago}h ago</span>'
        elif isinstance(hours_ago, (int, float)) and hours_ago <= 12:
            job_class = "job fresh-job"
            time_badge = f'<span style="background: #ffc107; color: black; padding: 2px 6px; border-radius: 12px; font-size: 11px;">⚡ {hours_ago}h ago</span>'
        else:
            job_class = "job"
            time_badge = f'<span style="background: #6c757d; color: white; padding: 2px 6px; border-radius: 12px; font-size: 11px;">🕒 {hours_ago}h ago</span>'
        
        easy_apply_badge = '<span class="easy-apply">✅ Easy Apply</span>' if easy_apply else ''
        
        html_content += f"""
        <div class="{job_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <div class="job-title">
                        {i}. <a href="{job['link']}" target="_blank">{job['title']}</a>
                    </div>
                    <div class="company">🏢 {job['company']}</div>
                    <div style="color: #888; font-size: 14px;">📍 {job['location']}</div>
                </div>
                <div style="text-align: right;">
                    {time_badge}
                    <br>
                    {easy_apply_badge}
                </div>
            </div>
        </div>
        """
    
    html_content += """
        <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; text-align: center; border-radius: 8px;">
            <p><strong>📊 Don't forget to check the complete HTML report above for all jobs!</strong></p>
            <p><em>Sent automatically by your LinkedIn Job Scraper</em></p>
            <p style="font-size: 12px; color: #666;">Happy job hunting! 🚀</p>
        </div>
    </body>
    </html>
    """
    
    # Send email
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎯 Daily Jobs: {len(jobs)} Senior Product Management Opportunities"
        msg['From'] = sender_email
        msg['To'] = receiver_email
        
        part = MIMEText(html_content, 'html')
        msg.attach(part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        
        print(f"✅ Daily job email sent successfully to {receiver_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending daily email: {e}")
        return False

def automated_daily_run():
    """Main function for automated daily job scraping and emailing with enhanced deduplication"""
    from config import SEARCH_CONFIG, OUTPUT_CONFIG
    
    # Email configuration - ADD YOUR ACTUAL DETAILS
    EMAIL_CONFIG = {
        "sender_email": "",        # Replace with your email
        "sender_password": "" # Replace with your App Password
        "receiver_email": ""       # Where to send the daily report
    }
    
    print(f"🚀 Starting automated senior-level job search at {datetime.now()}")
    
    all_jobs = []
    job_urls_seen = set()  # Track URLs we've already found
    
    # Search with enhanced configuration and inline deduplication
    for job_type in SEARCH_CONFIG['job_types']:
        for location in SEARCH_CONFIG['locations']:
            print(f"📍 Searching: {job_type} in {location}")
            
            try:
                jobs = scrape_linkedin_jobs_24h(job_type, location, SEARCH_CONFIG['max_jobs_per_search'])
                
                # Quick deduplication during collection
                for job in jobs:
                    job_id = extract_job_id_from_url(job['link'])
                    base_key = f"{job['title'].lower()}|{job['company'].lower()}"
                    
                    if job_id not in job_urls_seen and base_key not in job_urls_seen:
                        all_jobs.append(job)
                        job_urls_seen.add(job_id or job['link'])
                        job_urls_seen.add(base_key)
                
                time.sleep(random.uniform(12, 20))  # Increased delay for safety
            except Exception as e:
                print(f"❌ Error searching {job_type} in {location}: {e}")
                continue
    
    if not all_jobs:
        print("❌ No jobs found in automated run")
        return
    
    print(f"🔍 Total jobs before deduplication: {len(all_jobs)}")
    
    # ENHANCED DEDUPLICATION PROCESS
    # Step 1: Remove exact duplicates
    unique_jobs = remove_duplicates(all_jobs)
    
    # Step 2: Remove similar jobs (optional, for very strict deduplication)
    # unique_jobs = remove_similar_jobs(unique_jobs, similarity_threshold=0.90)
    
    # Step 3: Apply your existing filters
    filtered_jobs = filter_jobs(unique_jobs, SEARCH_CONFIG)
    
    print(f"📊 Final job count: {len(filtered_jobs)} unique, relevant jobs")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"{OUTPUT_CONFIG['csv_folder']}senior_jobs_{timestamp}.csv"
    html_filename = f"{OUTPUT_CONFIG['html_folder']}senior_jobs_{timestamp}.html"
    
    os.makedirs(OUTPUT_CONFIG['csv_folder'], exist_ok=True)
    os.makedirs(OUTPUT_CONFIG['html_folder'], exist_ok=True)
    
    save_to_csv(filtered_jobs, csv_filename)
    create_html_report(filtered_jobs, html_filename, "Senior Product Management Jobs - India Focus")
    
    # Send enhanced email with HTML report link
    email_sent = send_daily_job_email(
        filtered_jobs,
        EMAIL_CONFIG['sender_email'],
        EMAIL_CONFIG['sender_password'], 
        EMAIL_CONFIG['receiver_email'],
        html_filename  # Pass HTML file path for the link
    )
    
    print(f"📊 Daily run completed:")
    print(f"   Found: {len(filtered_jobs)} senior-level jobs")
    print(f"   CSV: {csv_filename}")
    print(f"   HTML: {html_filename}")
    print(f"   Email: {'✅ Sent with HTML link' if email_sent else '❌ Failed'}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "daily":
        # Run automated daily job
        automated_daily_run()
    else:
        # Run test
        from config import SEARCH_CONFIG, OUTPUT_CONFIG
        
        print("🔍 Testing LinkedIn job scraper with YOUR config...")
        print("This will test your actual job search preferences.\n")
        
        # Use YOUR first job type and location from config
        test_keyword = SEARCH_CONFIG["job_types"][0]
        test_location = SEARCH_CONFIG["locations"][0]
        
        print(f"Testing search: '{test_keyword}' in '{test_location}'")
        
        # Single test search using YOUR preferences
        test_jobs = scrape_linkedin_jobs_24h(test_keyword, test_location, 15)
        
        if test_jobs:
            print(f"\n✅ Success! Found {len(test_jobs)} jobs")
            
            # Apply YOUR filters
            filtered_jobs = filter_jobs(test_jobs, SEARCH_CONFIG)
            
            print(f"After filtering: {len(filtered_jobs)} relevant jobs")
            
            if filtered_jobs:
                # Remove duplicates
                unique_jobs = remove_duplicates(filtered_jobs)
                
                # Create output directories
                os.makedirs(OUTPUT_CONFIG["csv_folder"], exist_ok=True)
                os.makedirs(OUTPUT_CONFIG["html_folder"], exist_ok=True)
                
                # Save test results
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filename = f"{OUTPUT_CONFIG['csv_folder']}test_jobs_{timestamp}.csv"
                html_filename = f"{OUTPUT_CONFIG['html_folder']}test_jobs_{timestamp}.html"
                
                save_to_csv(unique_jobs, csv_filename)
                create_html_report(unique_jobs, html_filename, "LinkedIn Senior Product Manager Jobs Test")
                
                print(f"\n📁 Test files created:")
                print(f"   CSV: {csv_filename}")
                print(f"   HTML: {html_filename}")
                
                if unique_jobs:
                    print(f"\n🎯 Sample job found:")
                    print(f"   Title: {unique_jobs[0]['title']}")
                    print(f"   Company: {unique_jobs[0]['company']}")
                    print(f"   Link: {unique_jobs[0]['link']}")
                    print(f"   Easy Apply: {'✅ Yes' if unique_jobs[0].get('easy_apply', False) else '❌ No'}")
                
                print("\n🛑 Test completed successfully!")
                print("Your config is working! Ready for full searches.")
            else:
                print("❌ No jobs passed your filters. Try relaxing your criteria.")
                
        else:
            print("❌ No jobs found in test.")
            print("Try different keywords or check your internet connection.")
