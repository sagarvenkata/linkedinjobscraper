# Job search configuration - ENHANCED FOR SENIOR ROLES
SEARCH_CONFIG = {
    "job_types": [
        "Principal Product Manager", 
        "Director of Product",
        "VP Product",
        "Head of Product",
        "Chief Product Officer",
        "Lead Product Manager",
        "Staff Product Manager",
        "Group Product Manager",
        "Senior Director Product"
    ],
    "locations": [
        "India",           # First preference
        "Mumbai, India",
        "Bangalore, India", 
	"Bengaluru, India",
        "Delhi, India",
        "Hyderabad, India",
        "Remote"           # Secondary option
    ],
    "max_jobs_per_search": 25,
    "companies_to_exclude": [
        "Amazon"  # Add more as needed
    ],
    "required_keywords": [
        "Product Manager",
        "Product Management", 
        "Senior",
        "Principal",
        "Director",
        "VP",
        "Head",
        "Lead",
        "Staff",
        "Chief",
        "Group"
    ],
    "pm_jd_keywords": [
        "product strategy",
        "cross-functional collaboration",
        "stakeholder management",
        "data-driven decision making",
        "user research",
        "go-to-market",
        "roadmap prioritization",
        "agile methodologies",
        "OKRs",
        "KPIs",
        "product lifecycle management",
        "A/B testing",
        "UX",
        "UI design",
        "market analysis",
        "technical background",
        "scalability",
        "performance",
        "backlog management",
        "launch coordination",
        "business case development",
        "customer segmentation",
        "vision",
        "evangelism"
    ],

    "seniority_keywords": [
        # Keywords that indicate senior roles
        "10+ years",
        "10-15 years",
        "senior",
        "principal", 
        "director",
        "head of",
        "vp",
        "vice president",
        "chief",
        "lead",
        "staff",
        "group",
        "experienced",
        "leadership",
        "strategy",
        "vision"
    ],
    "exclude_junior_keywords": [
        # Filter out junior roles
        "junior",
        "associate", 
        "entry level",
        "fresher",
        "graduate",
        "intern",
        "trainee",
        "0-2 years",
        "1-3 years"
    ],
    # Enhanced time-based filters
    "time_filters": {
        "max_hours_old": 24,
        "preferred_hours_old": 12,
        "exclude_older_than_days": 1
    }
}

# File output settings (unchanged)
OUTPUT_CONFIG = {
    "csv_folder": "output/csv/",
    "html_folder": "output/html/",
    "include_timestamp": True
}

# Safety settings (unchanged)
SAFETY_CONFIG = {
    "min_delay_between_searches": 12,  # Slightly increased for safety
    "max_requests_per_minute": 5,
    "request_timeout": 15,
    "max_retries": 2
}
