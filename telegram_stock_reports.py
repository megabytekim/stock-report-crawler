import requests
from bs4 import BeautifulSoup
import csv
import os
from urllib.parse import urljoin, quote
import time
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from dotenv import load_dotenv
import logging
import asyncio
import json
from openai import OpenAI
import PyPDF2
import io
import sys

# Enable logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Stock Report Telegram Bot initialized...")

# Load environment variables
load_dotenv()
print("Environment variables loaded")

# Get credentials from environment variables
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

# Test mode support
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'
SINGLE_FILE_TEST = os.getenv('SINGLE_FILE_TEST', 'false').lower() == 'true'

if TEST_MODE:
    TARGET_CHANNEL = os.getenv('TEST_TARGET_CHANNEL')
    print(f"[TEST MODE ENABLED] Using test target channel: {TARGET_CHANNEL}")
else:
    # Use STOCK_REPORT_CHANNEL for production, fallback to TARGET_CHANNEL
    TARGET_CHANNEL = os.getenv('STOCK_REPORT_CHANNEL') or os.getenv('TARGET_CHANNEL')
    print(f"[PRODUCTION MODE] Using target channel: {TARGET_CHANNEL}")

TIMEZONE = pytz.timezone('Asia/Seoul')

# Initialize client
client = TelegramClient('stock_reports_session', API_ID, API_HASH)

# Checkpoint file for resuming
CHECKPOINT_FILE = 'report_checkpoint.json'

# Checkpoint file structure:
# {
#   "date": "24.07.15",
#   "reports": [
#     {
#       "company_name": "삼성전자",
#       "report_title": "2Q24 실적 전망",
#       "research_firm": "키움증권",
#       "pdf_url": "https://...",
#       "date": "24.07.15",
#       "view_count": "1234"
#     },
#     ...
#   ],
#   "processed_indices": [0, 1, 2, 5, 8],
#   "timestamp": "2024-07-15T10:30:00"
# }

def save_checkpoint(reports, processed_indices):
    """Save checkpoint with reports and processed indices"""
    checkpoint_data = {
        'date': get_yesterday_date(),
        'reports': reports,
        'processed_indices': processed_indices,
        'timestamp': datetime.now().isoformat()
    }
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        print(f"Checkpoint saved: {len(processed_indices)}/{len(reports)} reports processed")
    except Exception as e:
        print(f"Error saving checkpoint: {e}")

def load_checkpoint():
    """Load checkpoint if it exists and is for today"""
    if not os.path.exists(CHECKPOINT_FILE):
        return None, []
    
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        # Check if checkpoint is for today
        if checkpoint_data.get('date') == get_yesterday_date():
            print(f"Found checkpoint for today: {len(checkpoint_data['processed_indices'])}/{len(checkpoint_data['reports'])} reports already processed")
            return checkpoint_data['reports'], checkpoint_data['processed_indices']
        else:
            print("Checkpoint is for a different date, starting fresh")
            return None, []
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        return None, []

def clear_checkpoint():
    """Clear the checkpoint file"""
    try:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
            print("Checkpoint cleared")
    except Exception as e:
        print(f"Error clearing checkpoint: {e}")

def get_yesterday_date():
    """Get yesterday's date in the format used by Naver Finance (YY.MM.DD)"""
    seoul_now = datetime.now(TIMEZONE)
    yesterday = seoul_now - timedelta(days=1)
    return yesterday.strftime('%y.%m.%d')  # Use YY.MM.DD format

def extract_text_from_pdf_first_page(pdf_content):
    """Extract text from the first page of a PDF"""
    try:
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        if len(pdf_reader.pages) > 0:
            first_page = pdf_reader.pages[0]
            text = first_page.extract_text()
            return text.strip()
        else:
            return "No text found in PDF"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return f"Error extracting text: {str(e)}"

def summarize_pdf_with_llm(pdf_text, company_name, report_title, research_firm):
    """Summarize PDF content using OpenAI API"""
    api_key = os.getenv('OPEN_API_KEY')
    if not api_key:
        print("OPEN_API_KEY not found in environment. Returning mock summary.")
        return "[MOCK SUMMARY] No API key found."
    
    print(f"Summarizing PDF for {company_name} by {research_firm}...")
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 주식 투자 리포트를 분석하고 요약하는 전문가야. "
                        "기관 투자자와 개인 투자자들이 빠르게 핵심 내용을 파악할 수 있도록 "
                        "투자 의견, 목표가, 핵심 논리, 리스크 요인 등을 간결하고 명확하게 정리해. "
                        "한국어로 작성하고, 실제 투자 판단에 도움이 되도록 작성해."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"다음은 {company_name}에 대한 {research_firm}의 투자 리포트 내용이야. "
                        f"제목: {report_title}\n\n"
                        f"PDF 첫 페이지 내용:\n{pdf_text}\n\n"
                        f"이 내용을 투자 관점에서 핵심만 요약해줘. "
                        f"투자 의견, 목표가, 핵심 논리, 주요 리스크 등을 포함해서 작성해."
                    )
                }
            ],
            max_tokens=800,
            temperature=0.3,
            top_p=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return f"[요약 실패] OpenAI API 오류: {e}"

def scrape_yesterday_reports():
    """Scrape yesterday's stock reports from Naver Finance"""
    yesterday_date = get_yesterday_date()
    print(f"Scraping reports for date: {yesterday_date}")

    reports = []
    page_number = 1
    consecutive_empty_pages = 0
    max_consecutive_empty = 5  # Stop after 5 consecutive pages with no yesterday reports
    
    while True:
        target_url = f'https://finance.naver.com/research/company_list.naver?&page={page_number}'
        
        try:
            response = requests.get(target_url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                table = soup.find('table')
                
                if not table:
                    print(f"No table found on page {page_number}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_consecutive_empty:
                        print(f"Stopping after {max_consecutive_empty} consecutive pages with no table")
                        break
                    page_number += 1
                    continue
                
                found_yesterday_reports = False
                
                # Iterate over each row in the table
                for row in table.find_all('tr')[1:]:  # Skip the header row
                    columns = row.find_all('td')
                    if len(columns) == 6:
                        company_name = columns[0].get_text(strip=True)
                        report_title = columns[1].get_text(strip=True)
                        research_firm = columns[2].get_text(strip=True)
                        pdf_link_tag = columns[3].find('a')
                        date = columns[4].get_text(strip=True)  # Do not strip dots
                        view_count = columns[5].get_text(strip=True)
                        
                        # Check if this report is from yesterday
                        if date == yesterday_date and pdf_link_tag and 'href' in pdf_link_tag.attrs:
                            pdf_link = pdf_link_tag['href']
                            pdf_url = urljoin('https://stock.pstatic.net', pdf_link)
                            
                            report_data = {
                                'company_name': company_name,
                                'report_title': report_title,
                                'research_firm': research_firm,
                                'pdf_url': pdf_url,
                                'date': date,
                                'view_count': view_count
                            }
                            reports.append(report_data)
                            found_yesterday_reports = True
                            print(f"Found yesterday's report: {company_name} - {report_title}")
                            
                            # If in single file test mode, return after first report
                            if SINGLE_FILE_TEST:
                                print("Single file test mode: Found first report, stopping search")
                                return reports
                
                # If no yesterday reports found on this page
                if not found_yesterday_reports:
                    consecutive_empty_pages += 1
                    print(f"No yesterday reports found on page {page_number} (consecutive empty: {consecutive_empty_pages})")
                    
                    # Stop if we've had too many consecutive empty pages
                    if consecutive_empty_pages >= max_consecutive_empty:
                        print(f"Stopping after {max_consecutive_empty} consecutive pages with no yesterday reports")
                        break
                else:
                    # Reset consecutive empty counter if we found reports
                    consecutive_empty_pages = 0
                
                page_number += 1
                time.sleep(1)  # Delay between pages
                
            else:
                print(f"Failed to retrieve page {page_number}. Status code: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error processing page {page_number}: {e}")
            break
    
    print(f"Total yesterday reports found: {len(reports)}")
    print(f"Total pages searched: {page_number}")
    return reports

async def test_single_pdf_url(pdf_url, company_name="테스트 회사", report_title="테스트 리포트", research_firm="테스트 연구사"):
    """Test function to process a single PDF URL"""
    print(f"Testing single PDF URL: {pdf_url}")
    
    try:
        # Start the client
        await client.start()
        
        if not client.is_connected():
            print("Error: Could not connect to Telegram. Please check your credentials.")
            return
        
        # Get target channel entity once
        try:
            target_channel = await client.get_entity(TARGET_CHANNEL)
            print(f"Connected to target channel: {TARGET_CHANNEL}")
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"Rate limited when getting channel entity. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            target_channel = await client.get_entity(TARGET_CHANNEL)
            print(f"Connected to target channel: {TARGET_CHANNEL}")
        except Exception as e:
            print(f"Error getting target channel entity: {e}")
            return
        
        # Create test report data
        test_report = {
            'company_name': company_name,
            'report_title': report_title,
            'research_firm': research_firm,
            'pdf_url': pdf_url,
            'date': get_yesterday_date(),
            'view_count': '0'
        }
        
        # Download and summarize
        report_summary = await download_and_summarize_report(test_report)
        
        if report_summary:
            # Send to Telegram
            await send_report_to_telegram(report_summary, target_channel)
            print("Test completed successfully!")
        else:
            print("Test failed: Could not process the PDF")
        
    except Exception as e:
        print(f"Error in test_single_pdf_url: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        await client.disconnect()

async def download_and_summarize_report(report_data):
    """Download PDF and create summary"""
    try:
        print(f"Downloading PDF for {report_data['company_name']}...")
        print(f"PDF URL: {report_data['pdf_url']}")
        
        # Download the PDF
        response = requests.get(report_data['pdf_url'], headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        print(f"PDF downloaded successfully. Size: {len(response.content)} bytes")
        
        # Extract text from first page
        pdf_text = extract_text_from_pdf_first_page(response.content)
        
        print(f"Extracted text length: {len(pdf_text)} characters")
        print(f"First 200 characters: {pdf_text[:200]}...")
        
        if len(pdf_text) < 50:  # If text is too short, might be an error
            print(f"Warning: Extracted text seems too short for {report_data['company_name']}")
            return None
        
        # Summarize with LLM
        summary = summarize_pdf_with_llm(
            pdf_text, 
            report_data['company_name'], 
            report_data['report_title'], 
            report_data['research_firm']
        )
        
        return {
            **report_data,
            'summary': summary,
            'pdf_text_length': len(pdf_text)
        }
        
    except Exception as e:
        print(f"Error processing report for {report_data['company_name']}: {e}")
        return None

async def send_report_to_telegram(report_summary, target_channel):
    """Send summarized report to Telegram channel"""
    try:
        # Format the message
        message = f"""
📊 **{report_summary['company_name']} 투자 리포트**

🏢 **연구사**: {report_summary['research_firm']}
📋 **제목**: {report_summary['report_title']}
📅 **날짜**: {report_summary['date']}
👁️ **조회수**: {report_summary['view_count']}

📝 **요약**:
{report_summary['summary']}

🔗 **원본 PDF**: [다운로드]({report_summary['pdf_url']})
        """.strip()
        
        # Send to target channel
        await client.send_message(target_channel, message, parse_mode='markdown')
        
        print(f"Sent report for {report_summary['company_name']} to Telegram")
        
        # Add delay to avoid rate limiting
        await asyncio.sleep(2)
        
    except FloodWaitError as e:
        wait_time = e.seconds
        print(f"Rate limited by Telegram. Waiting {wait_time} seconds...")
        await asyncio.sleep(wait_time)
        # Retry once after waiting
        try:
            await client.send_message(target_channel, message, parse_mode='markdown')
            print(f"Successfully sent report for {report_summary['company_name']} after waiting")
        except Exception as retry_e:
            print(f"Failed to send report after retry: {retry_e}")
    except Exception as e:
        print(f"Error sending report to Telegram: {e}")

async def process_yesterday_reports():
    """Main function to process yesterday's stock reports"""
    try:
        print("Starting to process yesterday's stock reports...")
        
        # Start the client
        await client.start()
        
        if not client.is_connected():
            print("Error: Could not connect to Telegram. Please check your credentials.")
            return
        
        # Get target channel entity once
        try:
            target_channel = await client.get_entity(TARGET_CHANNEL)
            print(f"Connected to target channel: {TARGET_CHANNEL}")
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"Rate limited when getting channel entity. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            target_channel = await client.get_entity(TARGET_CHANNEL)
            print(f"Connected to target channel: {TARGET_CHANNEL}")
        except Exception as e:
            print(f"Error getting target channel entity: {e}")
            return
        
        # Try to load checkpoint first
        reports, processed_indices = load_checkpoint()
        
        if reports is None:
            # No checkpoint found, scrape fresh reports
            reports = scrape_yesterday_reports()
            
            if not reports:
                print("No yesterday reports found.")
                # Send notification to Telegram
                await client.send_message(target_channel, "📊 어제 등록된 새로운 투자 리포트가 없습니다.")
                return
            
            processed_indices = []
            print(f"Found {len(reports)} new reports to process")
        else:
            print(f"Resuming from checkpoint: {len(processed_indices)}/{len(reports)} reports already processed")
        
        # Process remaining reports
        remaining_reports = [i for i in range(len(reports)) if i not in processed_indices]
        
        if not remaining_reports:
            print("All reports already processed!")
            # Send completion message
            await client.send_message(
                target_channel, 
                f"✅ 어제 등록된 {len(reports)}개 투자 리포트 처리 완료!"
            )
            # Clear checkpoint since we're done
            clear_checkpoint()
            return
        
        print(f"Processing {len(remaining_reports)} remaining reports...")
        
        # Process each remaining report
        for i, report_index in enumerate(remaining_reports, 1):
            report = reports[report_index]
            print(f"\nProcessing report {report_index + 1}/{len(reports)}: {report['company_name']}")
            
            try:
                # Download and summarize
                report_summary = await download_and_summarize_report(report)
                
                if report_summary:
                    # Send to Telegram
                    await send_report_to_telegram(report_summary, target_channel)
                    
                    # Mark as processed and save checkpoint
                    processed_indices.append(report_index)
                    save_checkpoint(reports, processed_indices)
                else:
                    print(f"Failed to process report for {report['company_name']}")
                
                # Add delay between reports
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error processing report {report_index + 1}: {e}")
                print("Checkpoint saved. You can resume later by running the script again.")
                return
        
        # Send completion message
        await client.send_message(
            target_channel, 
            f"✅ 어제 등록된 {len(reports)}개 투자 리포트 처리 완료!"
        )
        
        # Clear checkpoint since we're done
        clear_checkpoint()
        print("All reports processed successfully!")
        
    except Exception as e:
        print(f"Error in process_yesterday_reports: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        # Disconnect after completion
        await client.disconnect()

async def main():
    print("Starting stock report processing...")
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--clear-checkpoint':
            clear_checkpoint()
            print("Checkpoint cleared. Starting fresh...")
        elif sys.argv[1] == '--help':
            print("""
Usage: python telegram_stock_reports.py [OPTIONS]

Options:
  --clear-checkpoint    Clear the checkpoint file and start fresh
  --help               Show this help message

Examples:
  python telegram_stock_reports.py                    # Normal run (resumes if checkpoint exists)
  python telegram_stock_reports.py --clear-checkpoint # Clear checkpoint and start fresh
            """)
            return
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use --help for usage information")
            return
    
    # Check if we should test with a single PDF URL
    test_pdf_url = os.getenv('TEST_PDF_URL')
    if test_pdf_url:
        print(f"TEST MODE: Testing with specific PDF URL: {test_pdf_url}")
        await test_single_pdf_url(test_pdf_url)
        return
    
    try:
        await process_yesterday_reports()
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
        print("Checkpoint saved. You can resume later by running the script again.")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == '__main__':
    # Create a new event loop and run the main function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main()) 