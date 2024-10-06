import json
import boto3
from playwright.sync_api import sync_playwright
import spacy
from collections import Counter

# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

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
                    print(f"Warning: Empty content for link: https://www.adgm.com{link}")
            except Exception as e:
                print(f"Error extracting content from https://www.adgm.com{link}: {str(e)}")
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
        announcements.append(announcement)
    return announcements

def save_announcements(announcements, bucket_name, file_name):
    s3 = boto3.client('s3')
    data = {"announcements": announcements}
    json_data = json.dumps(data, ensure_ascii=False)
    s3.put_object(Bucket=bucket_name, Key=file_name, Body=json_data)
    print(f"Saved {len(announcements)} announcements to s3://{bucket_name}/{file_name}")

def lambda_handler(event, context):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.adgm.com/media/announcements")

        all_announcements = []
        page_number = 1
        max_pages = 1  # Set a maximum number of pages to scrape

        while page_number <= max_pages:
            print(f"Scraping page {page_number}")
            try:
                announcements = extract_announcements(page)
                all_announcements.extend(announcements)
                
                next_button = page.query_selector('.bottom-nav__item_revert:not(.disabled)')
                if not next_button:
                    print("Reached the last page")
                    break
                
                next_button.click()
                page_number += 1
                page.wait_for_load_state('networkidle')
            except Exception as e:
                print(f"An error occurred on page {page_number}: {str(e)}")
                break

        browser.close()

    bucket_name = 'crypto-crawler-bucket321'
    file_name = 'adgm_announcements.json'
    save_announcements(all_announcements, bucket_name, file_name)

    return {
        'statusCode': 200,
        'body': json.dumps(f'Scraped and saved {len(all_announcements)} announcements')
    }