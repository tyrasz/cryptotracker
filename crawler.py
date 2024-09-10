# Old crawler for reference
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import os
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ADGMCryptoBlockchainCrawler:
    def __init__(self):
        self.base_url = "https://www.adgm.com/media/announcements"
        self.announcements = []
        self.download_folder = "announcements"
        self.setup_driver()

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--proxy-server='direct://'")
        chrome_options.add_argument("--proxy-bypass-list=*")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver_path = ChromeDriverManager().install()
        service = ChromeService(driver_path)
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def crawl_announcements(self):
        page = 1
        while True:
            url = f"{self.base_url}?page={page}"
            logging.info(f"Crawling page {page}: {url}")
            
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(5)  # Wait for any JavaScript to load
                
                # Check if the page has loaded correctly
                if "Access Denied" in self.driver.title or "403 Forbidden" in self.driver.page_source:
                    logging.error("Access denied or forbidden. The website might be blocking automated access.")
                    break
                
                # Wait for the specific element containing announcements
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "announcement-item"))
                )
            except TimeoutException:
                logging.warning(f"Timeout occurred while loading page {page}. Stopping.")
                break
            except Exception as e:
                logging.error(f"An error occurred while loading page {page}: {e}")
                break

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            announcements = soup.find_all('div', class_='announcement-item')

            if not announcements:
                logging.info(f"No announcements found on page {page}. Stopping.")
                break

            logging.info(f"Found {len(announcements)} announcements on page {page}")

            for announcement in announcements:
                try:
                    title_elem = announcement.find('h3')
                    date_elem = announcement.find('span', class_='date')
                    link_elem = announcement.find('a')

                    if not all([title_elem, date_elem, link_elem]):
                        logging.warning(f"Skipping announcement due to missing elements: {announcement}")
                        continue

                    title = title_elem.text.strip()
                    date = date_elem.text.strip()
                    link = link_elem['href']
                    if not link.startswith('http'):
                        link = f"https://www.adgm.com{link}"

                    logging.info(f"Downloading announcement: {title}")
                    content = self.download_announcement(link)
                    
                    self.announcements.append({
                        'date': date,
                        'title': title,
                        'link': link,
                        'content': content
                    })
                except Exception as e:
                    logging.error(f"Error processing announcement: {e}")

            page += 1
            time.sleep(random.uniform(3, 7))  # Increased delay between requests

    def download_announcement(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "announcement-detail"))
            )
            time.sleep(3)  # Wait for any JavaScript to load
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            content = soup.find('div', class_='announcement-detail')
            return content.get_text(strip=True) if content else ""
        except Exception as e:
            logging.error(f"Error downloading announcement from {url}: {e}")
            return ""

    def save_to_csv(self, filename='adgm_announcements.csv'):
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['date', 'title', 'link', 'content'])
            writer.writeheader()
            for announcement in self.announcements:
                writer.writerow(announcement)

    def save_announcements_to_files(self):
        os.makedirs(self.download_folder, exist_ok=True)
        for announcement in self.announcements:
            filename = f"{self.download_folder}/{announcement['date']}_{announcement['title'][:50]}.txt"
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '_', '-', '.')).rstrip()
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(f"Date: {announcement['date']}\n")
                file.write(f"Title: {announcement['title']}\n")
                file.write(f"Link: {announcement['link']}\n\n")
                file.write(announcement['content'])

    def run(self):
        logging.info("Starting to crawl ADGM announcements...")
        try:
            self.crawl_announcements()
        except Exception as e:
            logging.error(f"An error occurred during crawling: {e}")
        finally:
            self.driver.quit()
        
        logging.info(f"Crawling complete. Found {len(self.announcements)} announcements.")
        if self.announcements:
            self.save_to_csv()
            logging.info("Announcements saved to CSV file.")
            self.save_announcements_to_files()
            logging.info(f"Announcements saved to individual files in the '{self.download_folder}' folder.")
        else:
            logging.warning("No announcements were found or downloaded.")

if __name__ == "__main__":
    crawler = ADGMCryptoBlockchainCrawler()
    crawler.run()
