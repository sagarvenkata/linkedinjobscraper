# LinkedIn Senior Product Management Job Scraper

🎯 An intelligent Python automation tool that finds and filters senior product management positions, removes duplicates, and delivers personalized daily email reports.

## ✨ Key Features

- **🔍 Smart Filtering**: Targets 10+ years senior product management roles
- **🇮🇳 India-First**: Prioritizes Indian locations with remote backup
- **⚡ Fresh Jobs Only**: Finds positions posted within 24 hours  
- **📧 Daily Email Reports**: HTML-formatted emails with clickable job links
- **🔄 Intelligent Deduplication**: Removes 10-15x duplicate listings
- **⏰ Automated Scheduling**: Runs daily via Windows Task Scheduler
- **📊 Multiple Outputs**: CSV data + beautiful HTML reports

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Gmail account with 2FA and App Password
- Windows (for Task Scheduler automation)

### Installation


### Configuration
1. Edit `config.py` with your job preferences
2. Update email credentials in `main.py` (search for EMAIL_CONFIG)
3. Test: `python main.py`
4. Run daily search: `python main.py daily`

## 📁 Project Structure


## ⚙️ How It Works

1. **Search**: Queries LinkedIn for multiple job types across Indian cities
2. **Filter**: Removes junior roles, applies seniority scoring  
3. **Deduplicate**: Eliminates 10-15x duplicate listings intelligently
4. **Rank**: Sorts by posting time and relevance score
5. **Report**: Generates CSV + HTML files
6. **Email**: Sends top 30 jobs with full report link

## 🔒 Privacy & Security

- **No personal data committed** to repository
- **Rate limiting** to respect LinkedIn servers  
- **Email credentials** stored locally only
- **For personal job search use only**

## 📋 Sample Output

**Email Report**: Top 30 jobs sorted by posting time
**CSV File**: Complete job data for analysis  
**HTML Report**: Clickable, categorized job listings
**Console Logs**: Detailed execution feedback

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests!

## ⚖️ Legal

This tool is for personal job search automation only. Users must comply with LinkedIn's Terms of Service. The tool includes respectful rate limiting.

## 📄 License

MIT License - see LICENSE file for details.

