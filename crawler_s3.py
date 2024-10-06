from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import json
import os
from datetime import datetime
import spacy
from collections import Counter
import boto3
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
import random
import requests
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

# S3 bucket ARN
S3_BUCKET_ARN = "arn:aws:s3:::crypto-crawler-bucket321"

def extract_tags(text, max_tags=5):
    # Process the text with spaCy
    doc = nlp(text)
    
    # Extract named entities
    entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ['ORG', 'PERSON', 'GPE', 'PRODUCT']]
    
    # Extract noun phrases
    noun_phrases = [chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
    
    # Combine entities and noun phrases
    potential_tags = entities + noun_phrases
    
    # Count occurrences and get the most common tags
    tag_counts = Counter(potential_tags)
    top_tags = [tag for tag, _ in tag_counts.most_common(max_tags)]
    
    return top_tags

def extract_announcements(page):
    announcements = []
    elements = page.query_selector_all('.element.level3')
    logger.info(f"Found {len(elements)} elements on the page")
    for element in elements:
        authority = element.query_selector('.title .helvetica-light')
        title = element.query_selector('.subhead-2.cl-black.level3')
        date = element.query_selector('.date-1.cl-gray9')
        link = element.get_attribute('href')

        # Extract content from the linked page
        content = ""
        if link:
            try:
                content_page = page.context.new_page()
                content_page.goto(f"https://www.adgm.com{link}", wait_until="networkidle")
                
                # Try different selectors for content
                selectors = [
                    '.announcement-content',
                    '.content-area',
                    'main',
                    'article',
                    'body'  # Fallback to entire body if specific content area not found
                ]
                
                for selector in selectors:
                    content_element = content_page.query_selector(selector)
                    if content_element:
                        content = content_element.inner_text()
                        if content.strip():
                            break

                if not content.strip():
                    logger.warning(f"Empty content for link: https://www.adgm.com{link}")
            except Exception as e:
                logger.error(f"Error extracting content from https://www.adgm.com{link}: {str(e)}")
            finally:
                content_page.close()

        title_text = title.inner_text() if title else ''
        content_text = content

        # Extract tags from title and content
        tags = extract_tags(title_text + " " + content_text)

        announcement = {
            "title": title_text,
            "date": date.inner_text() if date else '',
            "source": authority.inner_text() if authority else 'ADGM',
            "content": content_text,
            "tags": tags,
            "url": f"https://www.adgm.com{link}" if link else ''
        }
        logger.info(f"Extracted announcement: {title_text}")
        announcements.append(announcement)
    return announcements

def save_announcements_to_s3(announcements, file_name):
    # Extract bucket name from ARN
    bucket_name = S3_BUCKET_ARN.split(':')[-1]
    
    # Create an S3 client
    s3 = boto3.client('s3')
    
    # Convert announcements to JSON
    data = {"announcements": announcements}
    json_data = json.dumps(data, ensure_ascii=False, indent=2)
    
    # Upload the file to S3
    try:
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=json_data)
        logger.info(f"Saved {len(announcements)} announcements to s3://{bucket_name}/{file_name}")
    except Exception as e:
        logger.error(f"Error saving to S3: {str(e)}")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def navigate_to_page(page, url):
    page.goto(url)
    page.wait_for_load_state('networkidle')
    if "Access Denied" in page.title():
        raise Exception("Access Denied")

def get_free_proxies():
    url = "https://free-proxy-list.net/"
    response = requests.get(url)
    proxy_list = []
    if response.status_code == 200:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        for row in soup.find("table", attrs={"class": "table table-striped table-bordered"}).find_all("tr")[1:]:
            tds = row.find_all("td")
            try:
                ip = tds[0].text.strip()
                port = tds[1].text.strip()
                proxy_list.append(f"{ip}:{port}")
            except IndexError:
                continue
    return proxy_list

proxies = get_free_proxies()

def run(playwright):
    for attempt in range(3):  # Try 3 times
        try:
            browser = playwright.chromium.launch(headless=False)  # Set to True for production
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            page = context.new_page()
            
            logger.info(f"Attempt {attempt + 1}: Accessing the page")
            page.goto("https://www.adgm.com/media/announcements", timeout=60000)
            page.wait_for_load_state('networkidle')
            
            if "Access Denied" not in page.title():
                logger.info("Successfully accessed the page")
                
                # Take a screenshot for debugging
                page.screenshot(path=f"debug_screenshot_attempt_{attempt + 1}.png")
                
                logger.info(f"Page title: {page.title()}")
                logger.info(f"Number of .element.level3 elements: {len(page.query_selector_all('.element.level3'))}")
                
                all_announcements = []
                page_number = 1
                max_pages = 5

                while page_number <= max_pages:
                    logger.info(f"Scraping page {page_number}")
                    try:
                        page.wait_for_selector('.element.level3', timeout=30000)
                        announcements = extract_announcements(page)
                        logger.info(f"Extracted {len(announcements)} announcements from page {page_number}")
                        all_announcements.extend(announcements)
                        
                        next_button = page.query_selector('.bottom-nav__item_revert:not(.disabled)')
                        if not next_button:
                            logger.info("Reached the last page")
                            break
                        
                        next_button.click()
                        page_number += 1
                        page.wait_for_load_state('networkidle')
                    except PlaywrightTimeoutError:
                        logger.error(f"Timeout error on page {page_number}")
                        break
        except Exception as e:
            logger.error(f"Error with attempt {attempt + 1}: {str(e)}")
            if browser:
                browser.close()
    else:
        logger.error("Failed to access the page after trying multiple attempts")
        return

    logger.info(f"Total announcements extracted: {len(all_announcements)}")
    
    # Save to S3
    file_name = f'adgm_announcements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    save_announcements_to_s3(all_announcements, file_name)

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)