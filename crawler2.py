from playwright.sync_api import sync_playwright, TimeoutError
import time
import json
from datetime import datetime
import spacy
from collections import Counter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    logger.info(f"Found {len(elements)} announcement elements")
    
    for element in elements:
        try:
            authority = element.query_selector('.title .helvetica-light')
            title = element.query_selector('.subhead-2.cl-black.level3')
            date = element.query_selector('.date-1.cl-gray9')
            link = element.get_attribute('href')

            # Extract content from the linked page
            content = ""
            if link:
                try:
                    with page.context.new_page() as content_page:
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
        except Exception as e:
            logger.error(f"Error extracting announcement: {str(e)}")
    
    return announcements

def save_announcements_to_file(announcements, file_name):
    # Convert announcements to JSON
    data = {"announcements": announcements}
    json_data = json.dumps(data, ensure_ascii=False, indent=2)
    
    # Save the file locally
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(json_data)
        logger.info(f"Saved {len(announcements)} announcements to {file_name}")
    except Exception as e:
        logger.error(f"Error saving to file: {str(e)}")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to False for debugging
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            page.goto("https://www.adgm.com/media/announcements")
            logger.info("Page loaded, waiting for content...")
            
            # Wait for the main content to load
            page.wait_for_selector('.element.level3', timeout=30000)
            
            logger.info(f"Page title: {page.title()}")
            logger.info(f"Current URL: {page.url}")
            
            all_announcements = []
            page_number = 1
            max_pages = 5  # Set a maximum number of pages to scrape

            while page_number <= max_pages:
                logger.info(f"Scraping page {page_number}")
                
                # Take a screenshot for debugging
                page.screenshot(path=f"adgm_page_{page_number}.png")
                logger.info(f"Screenshot saved as adgm_page_{page_number}.png")
                
                announcements = extract_announcements(page)
                all_announcements.extend(announcements)
                
                next_button = page.query_selector('.bottom-nav__item_revert:not(.disabled)')
                if not next_button:
                    logger.info("Reached the last page")
                    break
                
                next_button.click()
                page.wait_for_load_state('networkidle')
                page_number += 1
                time.sleep(3)  # Additional wait to ensure page is fully loaded

            logger.info(f"Total announcements extracted: {len(all_announcements)}")
            
            # Save to local file
            file_name = f'adgm_announcements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            save_announcements_to_file(all_announcements, file_name)
            
        except TimeoutError:
            logger.error("Timeout waiting for content to load")
            page.screenshot(path="adgm_page_timeout.png")
            logger.info("Timeout screenshot saved as adgm_page_timeout.png")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()