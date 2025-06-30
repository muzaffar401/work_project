import csv
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse
import logging
from typing import List, Dict, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompetitorPriceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.results = []
        
    def extract_price_from_html(self, html_content: str, competitor_name: str) -> Optional[str]:
        """
        Extract price from HTML content based on competitor-specific patterns
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Common price patterns
        price_patterns = [
            r'Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'Price:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'[\d,]+(?:\.\d{2})?\s*Rs',
            r'[\d,]+(?:\.\d{2})?\s*PKR',
            r'Rs\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*Rs',
            r'([\d,]+(?:\.\d{2})?)\s*PKR',
            # Metro specific patterns
            r'[\d,]+(?:\.\d{2})?',
            r'Price\s*:?\s*([\d,]+(?:\.\d{2})?)',
            r'[\d,]+(?:\.\d{2})?\s*PKR',
            r'PKR\s*([\d,]+(?:\.\d{2})?)'
        ]
        
        # Competitor-specific selectors
        competitor_selectors = {
            'Cartpk': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper'
            ],
            'Diamond': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper'
            ],
            'Naheed': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper'
            ],
            'Metro': [
                '.price', '.product-price', '.amount', '[class*="price"]',
                '[class*="Price"]', '.current-price', '.regular-price',
                '.product-details-price', '.price-box', '.price-wrapper',
                '.product-price-box', '.price-display', '.price-value',
                '.product-price-value', '.price-amount', '.product-amount',
                '[data-price]', '[data-amount]', '.cost', '.value',
                '.product-cost', '.product-value', '.selling-price',
                '.offer-price', '.discount-price', '.final-price'
            ]
        }
        
        # Special handling for Metro
        if competitor_name == 'Metro':
            # Debug: Log the HTML structure for Metro
            logger.info(f"Debug: Analyzing Metro page structure")
            
            # Look for data attributes first
            for element in soup.find_all(attrs={'data-price': True}):
                price = getattr(element, 'attrs', {}).get('data-price')
                if price and isinstance(price, str) and self.is_valid_price(price):
                    logger.info(f"Debug: Found Metro price in data-price: {price}")
                    return self.format_price(price)
            
            for element in soup.find_all(attrs={'data-amount': True}):
                price = getattr(element, 'attrs', {}).get('data-amount')
                if price and isinstance(price, str) and self.is_valid_price(price):
                    logger.info(f"Debug: Found Metro price in data-amount: {price}")
                    return self.format_price(price)
            
            # Metro-specific price selectors based on their website structure
            metro_price_selectors = [
                '.product-price', '.price-display', '.price-value',
                '.product-price-value', '.price-amount', '.product-amount',
                '.cost', '.value', '.product-cost', '.product-value',
                '.selling-price', '.offer-price', '.discount-price', '.final-price',
                '.price-box', '.price-container', '.product-price-box',
                '.price-wrapper', '.price-section', '.product-price-section',
                # Metro specific classes
                '.price', '.amount', '.product-price',
                '[class*="price"]', '[class*="Price"]', '[class*="amount"]',
                '[class*="Amount"]', '[class*="cost"]', '[class*="Cost"]',
                # More specific Metro selectors
                '.product-details-price', '.current-price', '.regular-price',
                '.product-price-display', '.price-text', '.price-label'
            ]
            
            # First try to find price in specific Metro elements
            for selector in metro_price_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    # Skip very short or very long text
                    if len(text) < 3 or len(text) > 100:
                        continue
                    logger.info(f"Debug: Metro selector '{selector}' found text: '{text}'")
                    price = self.extract_price_from_text(text)
                    if price:
                        logger.info(f"Debug: Found Metro price in selector '{selector}': {price}")
                        return price
            
            # If no price found in specific selectors, try broader search
            logger.info("Debug: No price found in specific selectors, trying broader search")
            
            # Look for any element containing price patterns
            all_elements = soup.find_all(['span', 'div', 'p', 'strong', 'b'])
            for element in all_elements:
                text = element.get_text(strip=True)
                if len(text) > 5 and len(text) < 50:  # Reasonable text length
                    # Look for price patterns in this element
                    if re.search(r'Rs\.?\s*\d+', text) or re.search(r'PKR\s*\d+', text) or re.search(r'\d+\s*Rs', text):
                        logger.info(f"Debug: Found potential price element: '{text}'")
                        price = self.extract_price_from_text(text)
                        if price:
                            logger.info(f"Debug: Found Metro price in element: {price}")
                            return price
        
        # Try competitor-specific selectors first
        if competitor_name in competitor_selectors:
            for selector in competitor_selectors[competitor_name]:
                price_elements = soup.select(selector)
                for element in price_elements:
                    text = element.get_text(strip=True)
                    price = self.extract_price_from_text(text)
                    if price:
                        return price
        
        # Fallback: search entire text for price patterns
        text = soup.get_text()
        return self.extract_price_from_text(text)
    
    def extract_price_from_text(self, text: str) -> Optional[str]:
        """
        Extract price from text using various patterns
        """
        price_patterns = [
            r'Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'Price:\s*Rs\.?\s*([\d,]+(?:\.\d{2})?)',
            r'[\d,]+(?:\.\d{2})?\s*Rs',
            r'[\d,]+(?:\.\d{2})?\s*PKR',
            r'Rs\s*([\d,]+(?:\.\d{2})?)',
            r'PKR\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*Rs',
            r'([\d,]+(?:\.\d{2})?)\s*PKR',
            r'Price\s*:?\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    if self.is_valid_price(match):
                        return self.format_price(match)
        
        return None
    
    def is_valid_price(self, price_str: str) -> bool:
        """
        Check if a string represents a valid price
        """
        try:
            # Remove commas and extract only digits and decimal
            clean_price = re.sub(r'[^\d.]', '', str(price_str))
            if clean_price and float(clean_price) > 0:  # Any positive price is valid
                return True
        except (ValueError, TypeError):
            pass
        return False
    
    def format_price(self, price_str: str) -> str:
        """
        Format price to 2 decimal places
        """
        try:
            # Remove commas and extract only digits and decimal
            clean_price = re.sub(r'[^\d.]', '', str(price_str))
            if clean_price:
                formatted_price = f"{float(clean_price):.2f}"
                return formatted_price
        except (ValueError, TypeError):
            pass
        return price_str
    
    def scrape_price(self, url: str, competitor_name: str) -> Optional[str]:
        """
        Scrape price from a given URL with retry logic
        """
        max_retries = 3
        base_delay = 10  # Increased base delay
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Scraping price from {competitor_name}: {url} (Attempt {attempt + 1}/{max_retries})")
                
                # Add longer delay to avoid detection
                if attempt > 0:
                    delay = base_delay * (attempt + 1)  # 20s, 30s delays
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                
                response = self.session.get(url, timeout=45)  # Increased timeout
                response.raise_for_status()
                
                price = self.extract_price_from_html(response.text, competitor_name)
                
                if price:
                    logger.info(f"Found price for {competitor_name}: Rs. {price}")
                else:
                    logger.warning(f"No price found for {competitor_name}: {url}")
                
                return price
                
            except (requests.ConnectionError, requests.Timeout, requests.RequestException) as e:
                # Handle 404 errors immediately - skip to next product
                if "404" in str(e) or "Not Found" in str(e):
                    logger.warning(f"404 error for {competitor_name}: {url} - Skipping to next product")
                    return None
                
                logger.error(f"Connection error scraping {competitor_name}: {url} - {str(e)} (Attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to scrape {competitor_name} after {max_retries} attempts")
                    return None
                continue
            except Exception as e:
                logger.error(f"Unexpected error scraping {competitor_name}: {url} - {str(e)} (Attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return None
                continue
        
        return None
    
    def get_competitor_name_from_url(self, url: str) -> str:
        """
        Extract competitor name from URL
        """
        # Handle URLs without protocol
        if url.startswith('www.'):
            url = 'https://' + url
        
        domain = urlparse(url).netloc.lower()
        
        if 'cartpk.com' in domain:
            return 'Cartpk'
        elif 'dsmonline.pk' in domain:
            return 'Diamond'
        elif 'naheed.pk' in domain:
            return 'Naheed'
        elif 'metro-online.pk' in domain:
            return 'Metro'
        else:
            return 'Unknown'
    
    def process_csv(self, csv_file_path: str):
        """
        Process the CSV file and scrape prices from all competitors one by one
        """
        logger.info("Starting to process CSV file...")
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)
                
                if len(rows) < 3:
                    logger.error("CSV file doesn't have enough rows")
                    return
                
                # Extract competitor URLs from header
                competitor_urls = rows[0][1:]  # Skip first empty column
                competitor_names = [self.get_competitor_name_from_url(url) for url in competitor_urls]
                
                logger.info(f"Found competitors: {competitor_names}")
                
                # Process each competitor separately
                for comp_idx, (comp_url, comp_name) in enumerate(zip(competitor_urls, competitor_names)):
                    logger.info(f"\n{'='*50}")
                    logger.info(f"Processing competitor: {comp_name}")
                    logger.info(f"{'='*50}")
                    
                    # Reset results for this competitor
                    self.results = []
                    
                    # Process each product row for this competitor
                    for row_idx, row in enumerate(rows[2:], start=3):  # Start from row 3 (after headers)
                        if len(row) < 2:
                            continue
                        
                        sku = row[0]
                        product_link = row[comp_idx + 1]  # Get link for this specific competitor
                        
                        if not product_link or product_link.strip() == '':
                            logger.info(f"Skipping empty link for {comp_name} - SKU: {sku}")
                            continue
                        
                        logger.info(f"Processing SKU: {sku}")
                        
                        # Add delay between requests to be respectful
                        if row_idx > 3:  # Not the first request
                            time.sleep(5)  # Increased from 2 to 5 seconds
                        
                        price = self.scrape_price(product_link.strip(), comp_name)
                        
                        if price:
                            self.results.append({
                                'SKU': sku,
                                'Competitor_Price': price,
                                'Competitor_Name': comp_name,
                                'Competitor_Link': product_link.strip()
                            })
                    
                    # Save results for this competitor
                    if self.results:
                        self.save_competitor_results(comp_name)
                        logger.info(f"Completed {comp_name}: {len(self.results)} products found")
                    else:
                        logger.warning(f"No results found for {comp_name}")
                    
                    # Add delay between competitors
                    if comp_idx < len(competitor_names) - 1:
                        logger.info("Waiting 5 seconds before processing next competitor...")
                        time.sleep(5)
                
                logger.info(f"\nCompleted processing all competitors.")
                
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
    
    def save_competitor_results(self, competitor_name: str):
        """
        Save results for a specific competitor to a separate CSV file
        """
        if not self.results:
            logger.warning(f"No results to save for {competitor_name}")
            return
        
        # Create filename based on competitor name
        filename = f"{competitor_name.lower()}_prices.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                fieldnames = ['SKU', 'Competitor_Price', 'Competitor_Name', 'Competitor_Link']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in self.results:
                    writer.writerow(result)
            
            logger.info(f"Results saved to {filename}")
            logger.info(f"Total entries for {competitor_name}: {len(self.results)}")
            
        except Exception as e:
            logger.error(f"Error saving results for {competitor_name}: {str(e)}")
    
    def save_results(self, output_file: str = 'competitor_prices.csv'):
        """
        This method is kept for backward compatibility but is no longer used
        """
        logger.warning("This method is deprecated. Use save_competitor_results() instead.")
        pass

def main():
    """
    Main function to run the price scraping process
    """
    print("Competitor Price Scraper")
    print("="*40)
    
    # Initialize scraper
    scraper = CompetitorPriceScraper()
    
    # Process the CSV file
    csv_file = "Cartpk competitors link(Developer Sample File).csv"
    scraper.process_csv(csv_file)
    
    print("\nProcess completed!")
    print("Check the generated CSV files for each competitor.")

if __name__ == "__main__":
    main()
