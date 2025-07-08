import requests
from bs4 import BeautifulSoup
import csv
import os
from urllib.parse import urljoin, quote
import time

page_number_start = 1

# Loop through pages from 974 to 1
# for page_number in range(974, 0, -1):
for page_number in range(page_number_start, 30):
    # Update the target URL with the current page number
    target_url = f'https://finance.naver.com/research/company_list.naver?&page={page_number}'
    
    # Send a GET request to the webpage
    response = requests.get(target_url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the table containing the company research reports
        table = soup.find('table')
        
        # Function to read existing CSV and get existing PDF links
        def get_existing_links(csv_file):
            existing_links = set()
            if os.path.exists(csv_file):
                with open(csv_file, 'r', newline='', encoding='utf-8-sig') as csvfile:
                    csvreader = csv.reader(csvfile)
                    next(csvreader, None)  # Skip header
                    for row in csvreader:
                        if len(row) > 3:  # Ensure there is a PDF link
                            existing_links.add(row[3])
            return existing_links

        # Get existing PDF links
        existing_links = get_existing_links('company_reports.csv')

        # Check if the CSV file exists
        file_exists = os.path.exists('company_reports.csv')

        # Open the CSV file in append mode
        with open('company_reports.csv', 'a', newline='', encoding='utf-8-sig') as csvfile:
            csvwriter = csv.writer(csvfile)
            
            # Write the header row only if the file is new
            if not file_exists:
                csvwriter.writerow(['Company Name', 'Report Title', 'Research Firm', 'PDF Link', 'Date', 'View Count'])
            
            # Base directory for saving reports
            base_dir = 'reports'

            # Ensure the base directory exists
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)

            # Base URL for constructing absolute URLs
            base_url = 'https://stock.pstatic.net'

            # Extract PDF links
            pdf_links = []
            file_cells = soup.select('td.file a[href]')
            for link_tag in file_cells:
                href = link_tag['href']
                # Convert to absolute URL
                pdf_url = urljoin(base_url, href)
                # Encode special characters
                pdf_url = quote(pdf_url, safe=':/?=&')
                pdf_links.append(pdf_url)

            print(f"Page {page_number}: Found {len(pdf_links)} PDF links.")

            # Download PDFs
            download_folder = 'reports'
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            # Iterate over each row in the table
            for row in table.find_all('tr')[1:]:  # Skip the header row
                columns = row.find_all('td')
                if len(columns) == 6:
                    # Extract data from each column
                    company_name = columns[0].get_text(strip=True)
                    report_title = columns[1].get_text(strip=True)
                    research_firm = columns[2].get_text(strip=True)
                    pdf_link_tag = columns[3].find('a')
                    date = columns[4].get_text(strip=True).replace('.', '')
                    view_count = columns[5].get_text(strip=True)
                    
                    if pdf_link_tag and 'href' in pdf_link_tag.attrs:
                        pdf_link = pdf_link_tag['href']
                        # Check if the PDF link is already in the existing links
                        if pdf_link in existing_links:
                            print(f"Duplicate report found for {company_name}, skipping.")
                            continue
                        
                        # Construct the full URL
                        pdf_url = urljoin(base_url, pdf_link)
                        
                        # Create a directory for the company
                        company_dir = os.path.join(download_folder, company_name)
                        if not os.path.exists(company_dir):
                            os.makedirs(company_dir)
                        
                        # Construct the filename
                        filename = f'{date}_{company_name}_{report_title}_{research_firm}_네이버증권.pdf'
                        filename = filename.replace('/', '_')  # Replace any slashes
                        file_path = os.path.join(company_dir, filename)
                        
                        # Check if the file already exists
                        if os.path.exists(file_path):
                            print(f"File already exists: {file_path}, skipping download.")
                            continue
                        
                        # Download the PDF
                        try:
                            r = requests.get(pdf_url, headers=headers)
                            r.raise_for_status()
                            with open(file_path, 'wb') as f:
                                f.write(r.content)
                            print(f"Downloaded: {file_path}")
                            
                            # Add a delay to avoid being blocked
                            time.sleep(0.5)  # Sleep for 0.5 seconds
                        except Exception as e:
                            print(f"Failed to download: {pdf_url}\nError: {e}")
                        
                        # Write the data to the CSV file
                        csvwriter.writerow([company_name, report_title, research_firm, pdf_link, date, view_count])
                        
                        # Add the PDF link to the set of existing links
                        existing_links.add(pdf_link)
                    else:
                        print(f"No PDF link found for {company_name}.")
    else:
        print(f"Failed to retrieve the webpage for page {page_number}. Status code: {response.status_code}") 