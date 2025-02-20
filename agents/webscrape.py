import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
    
    def validate_url(self, url: str) -> bool:
        """Validate if the URL is properly formatted."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception as e:
            logger.error(f"URL validation error for {url}: {str(e)}")
            return False
    
    def scrape_url(self, url: str) -> Optional[str]:
        """Scrape content from a single URL."""
        try:
            if not self.validate_url(url):
                logger.warning(f"Invalid URL format: {url}")
                return None
            
            # Fetch webpage
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe']):
                element.decompose()
            
            # Extract text from relevant tags
            content = []
            for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
                text = tag.get_text(strip=True)
                if text:
                    content.append(text)
            
            return " ".join(content)
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            return None
    
    def process_websites(self, urls: List[str]) -> List[Dict]:
        """Process a list of websites and return their content."""
        processed_websites = []
        
        for url in urls:
            content = self.scrape_url(url)
            if content:
                processed_websites.append({
                    "url": url,
                    "content": content,
                    "timestamp": datetime.utcnow()
                })
            else:
                logger.warning(f"No content extracted from {url}")
        
        return processed_websites

# Create a singleton instance
scraper = WebScraper()
