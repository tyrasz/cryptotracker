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

def extract_offers(page):
    offers = []
    try:
        # Wait for any content to load
        page.wait_for_selector('body', timeout=10000)
        
        # Log the page content for debugging
        logger.info(f"Page content: {page.content()[:1000]}...")  # Log first 1000 characters
        
        # Try to find offer elements directly
        offer_elements = page.query_selector_all('.offer-item')
        
        if not offer_elements:
            logger.warning("No offer items found. Trying alternative selectors...")
            # Try alternative selectors
            offer_elements = page.query_selector_all('.card-offer-item')  # Example alternative selector
        
        logger.info(f"Found {len(offer_elements)} offer elements")
        
        for offer in offer_elements:
            try:
                title = offer.query_selector('.offer-title')
                description = offer.query_selector('.offer-description')
                
                title_text = title.inner_text().strip() if title else "No title found"
                description_text = description.inner_text().strip() if description else "No description found"
                
                # Extract tags from title and description
                tags = extract_tags(title_text + " " + description_text)
                
                offer_data = {
                    "title": title_text,
                    "description": description_text,
                    "tags": tags
                }
                offers.append(offer_data)
            except Exception as e:
                logger.error(f"Error extracting offer: {str(e)}")
    except Exception as e:
        logger.error(f"Error in extract_offers: {str(e)}")
    
    return offers

def save_offers_to_file(offers, file_name):
    # Convert offers to JSON
    data = {"offers": offers}
    json_data = json.dumps(data, ensure_ascii=False, indent=2)
    
    # Save the file locally
    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(json_data)
        logger.info(f"Saved {len(offers)} offers to {file_name}")
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
            page.goto("https://www.bankfab.com/en-ae/personal/credit-cards/offers")
            logger.info("Page loaded, waiting for content...")
            
            logger.info(f"Page title: {page.title()}")
            logger.info(f"Current URL: {page.url}")
            
            # Take initial screenshot
            page.screenshot(path="fab_offers_page_initial.png")
            logger.info("Initial screenshot saved as fab_offers_page_initial.png")
            
            # Scroll to load all content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(5)  # Wait for any lazy-loaded content
            
            # Take another screenshot after scrolling
            page.screenshot(path="fab_offers_page_scrolled.png")
            logger.info("Scrolled screenshot saved as fab_offers_page_scrolled.png")
            
            # Extract all offers
            all_offers = extract_offers(page)

            logger.info(f"Total offers extracted: {len(all_offers)}")
            
            # Save to local file
            file_name = f'fab_credit_card_offers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            save_offers_to_file(all_offers, file_name)
            
        except TimeoutError:
            logger.error("Timeout waiting for content to load")
            page.screenshot(path="fab_offers_page_timeout.png")
            logger.info("Timeout screenshot saved as fab_offers_page_timeout.png")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    run()