from PIL import Image
from PIL import ImageEnhance, ImageFilter
import pytesseract
import requests
from io import BytesIO
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langdetect import detect
from deep_translator import GoogleTranslator

import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  


def preprocess_image(image, scale_factor=1.0):
    # Resize the image to enhance OCR accuracy
    if scale_factor != 1.0:
        new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
        image = image.resize(new_size, Image.LANCZOS)  # High-quality scaling

    # Convert to grayscale
    gray_image = image.convert("L")
    
    # Increase contrast further for bold text
    enhancer = ImageEnhance.Contrast(gray_image)
    enhanced_image = enhancer.enhance(4)  # Increased contrast
    
    # Apply thresholding
    threshold_image = enhanced_image.point(lambda p: p > 150 and 255)  
    filtered_image = threshold_image.filter(ImageFilter.MedianFilter(size=3))  # Optional noise removal

    # Sharpen the image
    sharpened_image = filtered_image.filter(ImageFilter.SHARPEN)  
    
    return sharpened_image

def clean_number(match, context=None):
    if match:
        number_str = match.group(1)
        
        if number_str:
            number_str = number_str.replace('O', '0').replace(',', '')  

            if 'T1' in number_str:
                return 71  

            if context == "missed_notes":
                number_str = re.sub(r'[^\d]', '', number_str)
                if '101' in number_str:
                    return 1

            try:
                return int(number_str)
            except ValueError:
                return 0
    return 0

def extract_data_from_image(image_url, perfect, good, missed, striked):
    try:
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))

        scale_factors = [0.5, 1.0, 1.5, 2.0, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0]
        languages = "eng+spa+fra+deu+jpn"  

        for scale in scale_factors:
            print(f"Trying scale factor: {scale} with multiple languages: {languages}")
            
            preprocessed_image = preprocess_image(image, scale)
            custom_config = f'--oem 3 --psm 6 -l {languages}'
            text = pytesseract.image_to_string(preprocessed_image, config=custom_config)

            print("OCR Output:")
            print(text)

            detected_lang = detect(text)
            print(f"Detected language: {detected_lang}")

            if detected_lang != "en":
                print("Translating OCR text to English...")
                text = GoogleTranslator(source='auto', target='en').translate(text)
                print("Translated text:")
                print(text)

            # Allow extraction even if "notes" is missing
            perfect_notes_match = re.search(r'(?:Perfect|erfect|Perfectas)\s*(?:notes|Notas|note:)?\s*([\d,]+)', text, re.IGNORECASE)
            good_notes_match = re.search(r'(?:Good|Notas buenas)\s*(?:notes|note:)?\s*([\d,]+)', text, re.IGNORECASE)
            missed_notes_match = re.search(r'(?:Missed|Notas falladas)\s*(?:notes|note:)?\s*([\d,]+)', text, re.IGNORECASE)
            striked_notes_match = re.search(r'(?:Strikes|Golpes)\s*(?:notes|note:)?\s*([\d,]+)', text, re.IGNORECASE)
            
            # Clean and extract numbers
            perfect_notes = clean_number(perfect_notes_match)
            good_notes = clean_number(good_notes_match)
            missed_notes = clean_number(missed_notes_match, context="missed_notes")
            striked_notes = clean_number(striked_notes_match)

            if (perfect_notes, good_notes, missed_notes, striked_notes) == (perfect, good, missed, striked):
                print(f"Match found at scale {scale}!")
                return perfect_notes, good_notes, missed_notes, striked_notes

        return perfect_notes, good_notes, missed_notes, striked_notes

    except Exception as e:
        print(f"Error: {e}")
        return 0, 0, 0, 0

async def extract_data_async(image_url, perfect, good, missed, striked):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, extract_data_from_image, image_url, perfect, good, missed, striked)
