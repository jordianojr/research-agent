import os
import logging
from datetime import datetime
from typing import Optional, Dict, List
from openai import OpenAI
from unstructured.partition.auto import partition
import tiktoken  # for OpenAI-style tokenization
import nltk  # for general purpose tokenization
from PIL import Image
import pytesseract
import pdf2image  # for converting PDF pages to images
from fastapi import UploadFile
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
nltk.download('punkt')  # Download required NLTK data

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI setup
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_TOKENS = 120_000

class FileProcessor:
    def __init__(self):
        self.supported_formats = {"pdf", "docx", "doc", "xlsx", "xls", "ppt", "pptx"}
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # Default GPT-4 tokenizer
        self.total_tokens = 0
        self.db = None

    async def init_db(self, mongodb_url: str = "mongodb://localhost:27017"):
        """Initialize database connection"""
        try:
            client = AsyncIOMotorClient(mongodb_url)
            self.db = client.agents_db
            await client.admin.command('ping')
            logger.info("FileProcessor connected to MongoDB!")
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            raise

    async def process_files(self, agent_id: str, files: List[UploadFile]) -> None:
        """Process files and update the database"""
        if self.db is None:
            await self.init_db()

        processed_files = []
        self.total_tokens = 0

        try:
            for file in files:
                # Save file temporarily to process with unstructured
                temp_path = f"/tmp/{file.filename}"
                try:
                    contents = await file.read()
                    with open(temp_path, "wb") as temp_file:
                        temp_file.write(contents)
                    
                    # Extract text using unstructured
                    extracted_text = self.extract_text(temp_path)
                    if extracted_text is None:
                        logger.error(f"Failed to extract text from {file.filename}")
                        continue

                    # Tokenize the extracted text
                    tokenization_info = self.tokenize_text(extracted_text)
                    new_tokens = tokenization_info["token_count"]

                    # Check token limit
                    if self.total_tokens + new_tokens > MAX_TOKENS:
                        logger.warning(f"Skipping {file.filename} as it would exceed token limit")
                        continue

                    self.total_tokens += new_tokens

                    # Prepare file document
                    file_doc = {
                        "filename": file.filename,
                        "content_type": file.content_type,
                        "content": {
                            "content": extracted_text,
                            "tokens": tokenization_info["tokens"],
                            "token_count": tokenization_info["token_count"]
                        },
                        "processed_at": datetime.utcnow()
                    }
                    processed_files.append(file_doc)

                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            # Update database with all processed files
            if processed_files:
                await self.db.agents.update_one(
                    {"_id": ObjectId(agent_id)},
                    {"$set": {"files": processed_files}}  # Changed from $push to $set
                )
                logger.info(f"Successfully processed and stored {len(processed_files)} files")

        except Exception as e:
            logger.error(f"Error processing files: {e}")
            raise

    def extract_text(self, file_path: str) -> Optional[str]:
        """Extract text from a given file."""
        try:
            elements = partition(filename=file_path)
            return "\n".join([str(element) for element in elements])
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return None

    def tokenize_text(self, text: str, method: str = "openai") -> Dict:
        """
        Tokenize the extracted text using specified method.
        
        Args:
            text: The text to tokenize
            method: 'openai' for tiktoken or 'nltk' for basic tokenization
        
        Returns:
            Dictionary containing tokens and token count
        """
        if not text:
            return {"tokens": [], "token_count": 0}

        try:
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
        except Exception as e:
            logger.error(f"Tokenization error: {e}")
            return {"tokens": [], "token_count": 0}

    def check_token_limit(self, new_tokens: int) -> bool:
        """Check if adding new tokens would exceed the limit"""
        if self.total_tokens + new_tokens > MAX_TOKENS:
            raise ValueError(f"Adding this content would exceed the maximum token limit of {MAX_TOKENS}")
        return True

    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(image_path)
            return pytesseract.image_to_string(image)
        except Exception as e:
            logger.error(f"OCR failed for image {image_path}: {str(e)}")
            return ""

    def extract_text_from_pdf_with_ocr(self, pdf_path: str) -> str:
        """Extract text from PDF using OCR if needed"""
        try:
            # First try normal text extraction
            text = self.extract_text(pdf_path)
            if text.strip():
                return text
            
            # If no text found, try OCR
            pages = pdf2image.convert_from_path(pdf_path)
            text_parts = []
            for page in pages:
                text_parts.append(pytesseract.image_to_string(page))
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF OCR failed for {pdf_path}: {str(e)}")
            return ""

    def process_file(self, file_path: str, tokenize_method: str = "openai") -> Optional[Dict]:
        """Process a file and return its content with tokenization."""
        # Reset total tokens for new file processing
        self.total_tokens = 0
        
        # Determine file type and extract text
        ext = os.path.splitext(file_path)[1].lower()
        if ext in {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}:
            text = self.extract_text_from_image(file_path)
        elif ext == '.pdf':
            text = self.extract_text_from_pdf_with_ocr(file_path)
        else:
            text = self.extract_text(file_path)

        if text is None:
            return None

        tokenization_info = self.tokenize_text(text, tokenize_method)
        
        # Check token limit
        self.check_token_limit(tokenization_info["token_count"])
        self.total_tokens += tokenization_info["token_count"]
        
        return {
            "filename": os.path.basename(file_path),
            "content": {
                "content": text,
                "tokens": tokenization_info["tokens"],
                "token_count": tokenization_info["token_count"]
            },
            "timestamp": datetime.now().isoformat()
        }

# Create a singleton instance
file_processor = FileProcessor()