import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List, Dict, Optional
from datetime import datetime
import logging
import tiktoken  # for OpenAI-style tokenization
import nltk  # for general purpose tokenization
nltk.download('punkt')  # Download required NLTK data
from PIL import Image
import pytesseract
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_TOKENS = 120_000  # Maximum allowable context

class WebScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Default GPT-4 tokenizer
        self.total_tokens = 0
    
    def validate_url(self, url: str) -> bool:
        """Validate if the URL is properly formatted."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception as e:
            logger.error(f"URL validation error for {url}: {str(e)}")
            return False
    
    def check_token_limit(self, new_tokens: int) -> bool:
        """Check if adding new tokens would exceed the limit"""
        if self.total_tokens + new_tokens > MAX_TOKENS:
            raise ValueError(f"Adding this content would exceed the maximum token limit of {MAX_TOKENS}")
        return True

    def extract_image_text(self, image_url: str) -> Optional[str]:
        """Extract text from images using OCR"""
        try:
            response = requests.get(image_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            return pytesseract.image_to_string(image)
        except Exception as e:
            logger.error(f"OCR failed for image {image_url}: {str(e)}")
            return None

    def scrape_url(self, url: str) -> Optional[str]:
        """Scrape content from a single URL."""
        try:
            if not self.validate_url(url):
                logger.warning(f"Invalid URL format: {url}")
                return None
            
            # Fetch webpage
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Check if URL points to an image
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('image/'):
                return self.extract_image_text(url)
            
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
    
    def tokenize_text(self, text: str, method: str = "openai") -> Dict:
        """
        Tokenize the text using specified method.
        
        Args:
            text: The text to tokenize
            method: 'openai' for tiktoken or 'nltk' for basic tokenization
        
        Returns:
            Dictionary containing tokens and token count
        """
        if not text:
            return {"tokens": [], "token_count": 0}

        if method == "openai":
            tokens = self.tokenizer.encode(text)
            return {
                "tokens": tokens,
                "token_count": len(tokens)
            }
        elif method == "nltk":
            tokens = nltk.word_tokenize(text)
            return {
                "tokens": tokens,
                "token_count": len(tokens)
            }
        else:
            raise ValueError("Unsupported tokenization method")

    def process_websites(self, urls: List[str], tokenize_method: str = "openai") -> List[Dict]:
        """Process a list of websites and return their content with tokenization."""
        processed_websites = []
        self.total_tokens = 0
        
        for url in urls:
            content = self.scrape_url(url)
            if content:
                tokenization_info = self.tokenize_text(content, tokenize_method)
                # Check token limit before adding
                self.check_token_limit(tokenization_info["token_count"])
                self.total_tokens += tokenization_info["token_count"]
                
                processed_websites.append({
                    "url": url,
                    "content": {
                        "content": content,
                        "tokens": tokenization_info["tokens"],
                        "token_count": tokenization_info["token_count"]
                    },
                    "timestamp": datetime.utcnow()
                })
            else:
                logger.warning(f"No content extracted from {url}")
        
        return processed_websites

# Create a singleton instance
scraper = WebScraper()
