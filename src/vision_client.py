# backend/vision_client.py
import io
import json
import base64
import logging
import pathlib
from typing import Dict
import os
from google.cloud import vision
from google.oauth2 import service_account

# ------------------------- LOGGER CONFIG -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
_LOGGER = logging.getLogger(__name__)

# ------------------------- CREDENTIAL LOADING -------------------------
def _load_credentials():
    """
    1. If GCLOUD_API_JSON contains JSON → parse it
    2. If GCLOUD_API_JSON is a path → read the file
    3. Else fallback to /app/api.json
    """
    json_str = os.getenv("GCLOUD_API_JSON")

    if json_str:
        # Case A: env var contains actual JSON text
        try:
            info = json.loads(json_str)
            _LOGGER.info("✅ Using Vision credentials from JSON env-var")
            return service_account.Credentials.from_service_account_info(info)
        except json.JSONDecodeError:
            # Case B: env-var is a file path
            try:
                key_path = pathlib.Path(json_str)
                with key_path.open() as f:
                    info = json.load(f)
                _LOGGER.info("✅ Using Vision credentials from file path in GCLOUD_API_JSON")
                return service_account.Credentials.from_service_account_info(info)
            except Exception as e:
                _LOGGER.error("❌ GCLOUD_API_JSON was neither valid JSON nor a readable file path: %s", e)
                raise

    # Fallback to local
    key_file = pathlib.Path(__file__).resolve().parent.parent / "api.json"
    if key_file.exists():
        _LOGGER.info("✅ Using Vision credentials from file %s", key_file)
        return service_account.Credentials.from_service_account_file(key_file)

    raise RuntimeError("Vision API credentials not found")


# ------------------------- CLIENT CLASS -------------------------
class VisionApiClient:
    def __init__(self) -> None:
        try:
            self._creds = _load_credentials()
            self.client = vision.ImageAnnotatorClient(credentials=self._creds)
            _LOGGER.info("✅ Google Vision API client initialised")
        except Exception as exc:
            _LOGGER.error("❌ Failed to initialise Vision API client: %s", exc)
            raise

    # --------------- your existing methods (unchanged) ---------------
    def extract_text_from_image(self, image_path: str) -> Dict:
        """
        Extract text from prescription image using Google Vision API
        """
        try:
            _LOGGER.info(f"📷 Loading image: {image_path}")
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)

            _LOGGER.info("🔍 Running text detection")
            response = self.client.text_detection(image=image)

            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")

            texts = response.text_annotations
            if not texts:
                _LOGGER.warning("⚠ No text detected in image")
                return {"error": "No text detected in image"}

            full_text = texts[0].description
            _LOGGER.debug(f"Full extracted text:\n{full_text}")

            words_data = []
            for text in texts[1:]:
                words_data.append({
                    'text': text.description,
                    'bounding_box': [(vertex.x, vertex.y) for vertex in text.bounding_poly.vertices]
                })

            result = {
                'full_text': full_text,
                'words': words_data,
                'language': getattr(response.full_text_annotation, 'locale', 'unknown'),
                'confidence': self._calculate_confidence(response)
            }

            _LOGGER.info(f"✅ Successfully extracted text from {image_path}")
            return result

        except Exception as e:
            _LOGGER.error(f"❌ Error extracting text from {image_path}: {str(e)}")
            return {"error": str(e)}

    def detect_document_text(self, image_path: str) -> Dict:
        """
        Use document text detection for better structured text extraction
        """
        try:
            _LOGGER.info(f"📷 Loading document image: {image_path}")
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()

            image = vision.Image(content=content)

            _LOGGER.info("🔍 Running document text detection")
            response = self.client.document_text_detection(image=image)

            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")

            document = response.full_text_annotation

            structured_data = self._parse_document_structure(document)
            structured_data["text"] = document.text

            _LOGGER.debug(f"Structured OCR output: {structured_data}")
            return structured_data

        except Exception as e:
            _LOGGER.error(f"❌ Error in document text detection: {str(e)}")
            return {"error": str(e)}

    def _calculate_confidence(self, response) -> float:
        """Calculate overall confidence score"""
        try:
            if hasattr(response.full_text_annotation, 'pages'):
                page = response.full_text_annotation.pages[0]
                if hasattr(page, 'confidence'):
                    return float(page.confidence)
            return 0.0
        except Exception as e:
            _LOGGER.warning(f"Could not calculate confidence: {e}")
            return 0.0

    def _parse_document_structure(self, document) -> Dict:
        """Parse document structure into blocks, paragraphs, and words"""
        structured_data = {
            'pages': [],
            'blocks': [],
            'paragraphs': [],
            'words': []
        }

        for page in document.pages:
            page_data = {
                'width': page.width,
                'height': page.height,
                'blocks': []
            }

            for block in page.blocks:
                block_data = {
                    'type': block.block_type,
                    'bounding_box': [(vertex.x, vertex.y) for vertex in block.bounding_box.vertices],
                    'paragraphs': []
                }

                for paragraph in block.paragraphs:
                    para_data = {
                        'bounding_box': [(vertex.x, vertex.y) for vertex in paragraph.bounding_box.vertices],
                        'words': []
                    }

                    for word in paragraph.words:
                        word_text = ''.join([symbol.text for symbol in word.symbols])
                        word_data = {
                            'text': word_text,
                            'bounding_box': [(vertex.x, vertex.y) for vertex in word.bounding_box.vertices],
                            'confidence': getattr(word, 'confidence', 0.0)
                        }
                        para_data['words'].append(word_data)
                        structured_data['words'].append(word_data)

                    block_data['paragraphs'].append(para_data)
                    structured_data['paragraphs'].append(para_data)

                page_data['blocks'].append(block_data)
                structured_data['blocks'].append(block_data)

            structured_data['pages'].append(page_data)

        return structured_data