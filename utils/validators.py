import os
import logging
from typing import Tuple, Optional
from PIL import Image
import filetype
 
logger = logging.getLogger(__name__)
 
class FileValidator:
    @staticmethod
    def validate_image(file_path: str, max_size_mb: int = 10) -> Tuple[bool, Optional[str]]:
        """
        Validate image file for processing
        
        Args:
            file_path (str): Path to the image file
            max_size_mb (int): Maximum file size in MB
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            # Check file size
            file_size = os.path.getsize(file_path)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if file_size > max_size_bytes:
                return False, f"File size exceeds {max_size_mb}MB limit"
            
            # Check file type
            kind = filetype.guess(file_path)
            if not kind:
                return False, "Unable to determine file type"
            
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
            file_extension = f".{kind.extension.lower()}"
            
            if file_extension not in allowed_extensions:
                return False, f"Unsupported file type: {file_extension}"
            
            # Try to open with PIL
            try:
                with Image.open(file_path) as img:
                    # Check image dimensions
                    width, height = img.size
                    if width < 100 or height < 100:
                        return False, "Image dimensions too small"
                    if width > 10000 or height > 10000:
                        return False, "Image dimensions too large"
                    
                    # Verify image can be processed
                    img.verify()
                    
            except Exception as e:
                return False, f"Invalid image file: {str(e)}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {str(e)}")
            return False, f"Validation error: {str(e)}"
 
    @staticmethod
    def preprocess_image(file_path: str) -> str:
        """
        Preprocess image for better OCR results
        
        Args:
            file_path (str): Path to the image file
            
        Returns:
            str: Path to processed image
        """
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Enhance contrast
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.5)
                
                # Enhance sharpness
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.2)
                
                # Save processed image
                processed_path = f"{file_path}.processed.jpg"
                img.save(processed_path, 'JPEG', quality=95)
                
                return processed_path
                
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return file_path  # Return original if processing fails
 
class DataValidator:
    @staticmethod
    def validate_prescription_data(data: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate parsed prescription data
        
        Args:
            data (dict): Parsed prescription data
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Check for required fields
            required_fields = ['raw_text', 'medications', 'parsed_at']
            
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
            
            # Validate medications
            if not isinstance(data['medications'], list):
                return False, "Medications must be a list"
            
            # Validate confidence score if present
            if 'confidence_score' in data:
                confidence = data['confidence_score']
                if not isinstance(confidence, (int, float)):
                    return False, "Confidence score must be a number"
                if not (0 <= confidence <= 1):
                    return False, "Confidence score must be between 0 and 1"
            
            # Validate date formats
            if 'prescription_date' in data and data['prescription_date']:
                try:
                    from datetime import datetime
                    # Try to parse the date
                    datetime.strptime(data['prescription_date'], '%Y-%m-%d')
                except ValueError:
                    # If specific format fails, just check if it's a string
                    if not isinstance(data['prescription_date'], str):
                        return False, "Prescription date must be a string"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating prescription data: {str(e)}")
            return False, f"Validation error: {str(e)}"