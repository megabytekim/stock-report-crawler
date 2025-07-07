# Stock Report Crawler

A Python web scraper that downloads company research reports in PDF format from Naver Finance. The script scrapes research reports from multiple pages and organizes them by company name.

## Features

- **Multi-page scraping**: Downloads reports from multiple pages (configurable start page)
- **Duplicate prevention**: Avoids downloading duplicate reports based on PDF links
- **Organized storage**: Creates separate folders for each company
- **CSV logging**: Maintains a database of all downloaded reports
- **Resumable**: Can resume from where it left off if interrupted
- **Configurable**: Easy to modify start page and other parameters

## Requirements

- Python 3.7+
- requests
- beautifulsoup4
- urllib3

## Installation

1. Clone the repository:
```bash
git clone https://github.com/megabytekim/stock-report-crawler.git
cd stock-report-crawler
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install requests beautifulsoup4
```

## Usage

1. Configure the start page in `web_scraper.py`:
```python
page_number_start = 973  # Change this to your desired start page
```

2. Run the script:
```bash
python web_scraper.py
```

## Output

- **PDF files**: Downloaded to `reports/[Company Name]/` folders
- **CSV file**: `company_reports.csv` containing metadata for all reports
- **File naming**: `[Date]_[Company]_[Title]_[Research Firm]_네이버증권.pdf`

## Configuration

### Page Range
- Modify `page_number_start` in the script to change the starting page
- The script downloads from the start page down to page 1

### Download Settings
- **Delay**: 1.5 seconds between downloads (configurable)
- **Headers**: Uses Mozilla User-Agent to avoid blocking
- **File organization**: Each company gets its own folder

## File Structure

```
stock-report-crawler/
├── web_scraper.py          # Main scraping script
├── company_reports.csv     # Database of downloaded reports
├── reports/                # Downloaded PDF files
│   ├── Company1/
│   ├── Company2/
│   └── ...
├── README.md              # This file
└── .gitignore            # Git ignore rules
```

## CSV Format

The `company_reports.csv` file contains:
- Company Name
- Report Title
- Research Firm
- PDF Link
- Date
- View Count

## Features

### Duplicate Prevention
- Checks existing PDF links in CSV before downloading
- Checks if PDF file already exists in filesystem
- Skips duplicates automatically

### Error Handling
- Graceful handling of network errors
- Continues processing even if individual downloads fail
- Logs errors for debugging

### Performance
- Configurable delays to avoid server overload
- Efficient parsing using BeautifulSoup
- Memory-efficient processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Disclaimer

This tool is for educational and research purposes. Please respect the terms of service of the websites you scrape and ensure you have permission to download the content.

## Author

Created by [megabytekim](https://github.com/megabytekim) 