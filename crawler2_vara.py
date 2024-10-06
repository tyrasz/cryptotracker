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
    elements = page.query_selector_all('.news-item')
    logger.info(f"Found {len(elements)} news items")
    
    for element in elements:
        try:
            title = element.query_selector('h3')
            date = element.query_selector('.date')
            content = element.query_selector('.excerpt')
            link = element.query_selector('a')

            title_text = title.inner_text().strip() if title else "No title found"
            date_text = date.inner_text().strip() if date else "No date found"
            content_text = content.inner_text().strip() if content else "No content found"
            link_href = link.get_attribute('href') if link else None

            # Extract tags from title and content
            tags = extract_tags(title_text + " " + content_text)

            announcement = {
                "title": title_text,
                "date": date_text,
                "content": content_text,
                "tags": tags,
                "url": f"https://www.vara.ae{link_href}" if link_href else 'No URL found'
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
            page.goto("https://www.vara.ae/en/news/")
            logger.info("Page loaded, waiting for content...")
            
            # Take an initial screenshot
            page.screenshot(path="vara_page_initial.png")
            logger.info("Initial screenshot saved as vara_page_initial.png")
            
            # Wait for any element to appear
            page.wait_for_selector('body', timeout=10000)
            
            logger.info(f"Page title: {page.title()}")
            logger.info(f"Current URL: {page.url}")
            
            # Log the page content for debugging
            logger.info(f"Page content: {page.content()[:500]}...")  # Log first 500 characters
            
            # Scroll to load all content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(5)  # Wait for any lazy-loaded content
            
            # Take another screenshot after scrolling
            page.screenshot(path="vara_page_scrolled.png")
            logger.info("Scrolled screenshot saved as vara_page_scrolled.png")
            
            all_announcements = extract_announcements(page)

            logger.info(f"Total announcements extracted: {len(all_announcements)}")
            
            # Save to local file
            file_name = f'vara_announcements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            save_announcements_to_file(all_announcements, file_name)
            
        except TimeoutError:
            logger.error("Timeout waiting for content to load")
            page.screenshot(path="vara_page_timeout.png")
            logger.info("Timeout screenshot saved as vara_page_timeout.png")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()