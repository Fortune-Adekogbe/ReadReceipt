# ocr_extractor.py
from datetime import datetime
import google.generativeai as genai
from PIL import Image # For handling images
import json
import os
import logging
import mimetypes # To determine video MIME type

from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Configure the Gemini API key
if GOOGLE_API_KEY and GOOGLE_API_KEY != "YOUR_GOOGLE_GEMINI_API_KEY":
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        # Decide how to handle this: raise error, or allow fallback if any
else:
    logger.warning("GOOGLE_API_KEY not configured. OCR functionality will be disabled.")


# Model name - use the latest flash model
GEMINI_MODEL_NAME = "models/gemini-2.0-flash"


def extract_date(frame_path, limit_of_reason=365):
    """
    Extracts date from an image using Gemini 2.0 Flash.
    Returns a list of dictionaries:
    """
    
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_GEMINI_API_KEY":
        logger.error("Gemini API key not available. Cannot process image.")
        return []

    try:
        logger.info(f"Checking for date Gemini: {os.path.basename(frame_path)}")
        img = Image.open(frame_path)

        # Safety settings - adjust as needed, though for receipts, harmful content is unlikely
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        # Generation config - tune temperature for more/less creative responses 
        generation_config = genai.types.GenerationConfig(
            # candidate_count=1, # Get only one response
            # stop_sequences=['\n\n\n'], # stop if it generates too much
            # max_output_tokens=1024, # Adjust if needed
            temperature=0.2 # Lower temperature for more deterministic output
        )

        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config
        )

        prompt = """
        Analyze this image and extract a single date written in the format MM/DD/YY.
        Focus ONLY on the date.
        Ensure the output is ONLY the DATE string and nothing else.
        IF no date exists, return an empty string.
        """

        response = model.generate_content([prompt, img]) # Multimodal input
        response_text = response.text.strip()
        print(response_text)

        format_string = "%m/%d/%y"
        date_object = datetime.strptime(response_text, format_string)
        # If the receipt lists a date beyond the limit of reason, ignore
        if (datetime.now() - date_object).days > limit_of_reason:
            response_text = ""

        return response_text

    except Exception as e:
        logger.error(f"Error during Gemini API call for {os.path.basename(frame_path)}: {e}", exc_info=True)
        return ''

def extract_data_from_frame_gemini(frame_path):
    """
    Extracts structured item data from an image using Gemini 2.0 Flash.
    Returns a list of dictionaries:
    [{'item_name': '...', 'item_size': ..., 'price_per_unit': ...}, ...]
    """
    
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_GEMINI_API_KEY":
        logger.error("Gemini API key not available. Cannot process image.")
        return []

    try:
        logger.info(f"Processing image with Gemini: {os.path.basename(frame_path)}")
        img = Image.open(frame_path)

        # Safety settings - adjust as needed, though for receipts, harmful content is unlikely
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        # Generation config - tune temperature for more/less creative responses 
        generation_config = genai.types.GenerationConfig(
            # candidate_count=1, # Get only one response
            # stop_sequences=['\n\n\n'], # stop if it generates too much
            # max_output_tokens=1024, # Adjust if needed
            temperature=0.2 # Lower temperature for more deterministic output
        )

        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config
        )

        prompt = """
        Analyze this receipt image. Extract all line items ignoring the supermarket discounts. 
        For each item, provide:
        1. 'item_name': The description of the item. Be as specific as possible from the text.
        2. 'item_size': The quantity purchased for that line item. If not explicitly stated, assume 1. If it's a weight (e.g., 0.5 kg), use that value. If it's an interpretable fractional quantity like "1/2 DOZEN", represent it as 6.
        3. 'price_per_unit': The price for a single unit of the item. If only a total price for multiple units is given (e.g., "2 for $5.00"), calculate the per-unit price (e.g., 2.50). If it's a price per kg/lb, use that. Ensure this is a numerical value.

        Return the data as a valid JSON list of objects. Each object should represent one line item and have the keys "item_name", "item_size", and "price_per_unit".
        Example: [{"item_name": "Fuji Apples", "item_size": 3, "price_per_unit": 1.50}, {"item_name": "Organic Milk 1L", "item_size": 1, "price_per_unit": 2.79}]
        If no items are found, or the image is not a receipt, return an empty JSON list [].
        Focus ONLY on the individual purchased line items. IGNORE headers, footers, store name, date, loyalty card information, subtotals, taxes, total amount, payment details, and any promotional text not part of a line item.
        Ensure the output is ONLY the JSON list and nothing else.
        """

        response = model.generate_content([prompt, img]) # Multimodal input

        # Debugging the raw response:
        # logger.debug(f"Gemini raw response parts: {response.parts}")
        # logger.debug(f"Gemini raw response text: {response.text}")
        
        # Extract the JSON string from the response. Gemini sometimes wraps it.
        # Look for the first ```json and the last ``` or just try to parse directly.
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[len("```json"):].strip()
        if response_text.endswith("```"):
            response_text = response_text[:-len("```")].strip()

        if not response_text:
            logger.warning(f"Gemini returned empty text for {os.path.basename(frame_path)}")
            return []

        try:
            extracted_data = json.loads(response_text)
            if not isinstance(extracted_data, list):
                logger.warning(f"Gemini did not return a list for {os.path.basename(frame_path)}. Got: {type(extracted_data)}")
                return []
            
            # Validate structure of each item
            valid_items = []
            for item in extracted_data:
                if isinstance(item, dict) and \
                   'item_name' in item and \
                   'item_size' in item and \
                   'price_per_unit' in item:
                    valid_items.append(item)
                else:
                    logger.warning(f"Invalid item structure from Gemini: {item} for image {os.path.basename(frame_path)}")
            
            logger.info(f"Successfully extracted {len(valid_items)} items from {os.path.basename(frame_path)} using Gemini.")
            return valid_items
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response for {os.path.basename(frame_path)}: {e}. Response text: '{response_text}'")
            return []
        except Exception as e: # Catch other potential errors from response processing
            logger.error(f"Error processing Gemini response: {e}. Response text: '{response_text}'")
            return []

    except Exception as e:
        logger.error(f"Error during Gemini API call for {os.path.basename(frame_path)}: {e}", exc_info=True)
        return []

def extract_data_from_video_gemini(video_path):
    """
    Extracts structured item data directly from a video file using Gemini.
    Returns a list of dictionaries:
    [{'item_name': '...', 'item_size': ..., 'price_per_unit': ...}, ...]
    """
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_GEMINI_API_KEY":
        logger.error("Gemini API key not available. Cannot process video.")
        return []

    try:
        logger.info(f"Uploading video for Gemini processing: {os.path.basename(video_path)}")
        
        # Upload the video file to Gemini. This is necessary for larger files.
        # For smaller files, you could pass bytes directly, but file API is more robust.
        video_file = genai.upload_file(path=video_path)
        logger.info(f"Video '{video_file.display_name}' uploaded successfully. Status: {video_file.state}")

        # Wait for the video to be processed by Google if it's not immediately ready
        # This is crucial as the file needs to be in an 'ACTIVE' state.
        while video_file.state.name == "PROCESSING":
            logger.info("Video is processing...")
            # You might want a timeout here in a production system
            import time
            time.sleep(5) # Wait 5 seconds before checking again
            video_file = genai.get_file(name=video_file.name)
            if video_file.state.name == "FAILED":
                logger.error(f"Video processing failed: {video_file.name}")
                # It's good practice to delete the uploaded file if processing failed or after use
                # genai.delete_file(video_file.name) # Uncomment if you want to delete on failure
                return []
        
        if video_file.state.name != "ACTIVE":
            logger.error(f"Uploaded video is not active. Current state: {video_file.state.name}")
            # genai.delete_file(video_file.name) # Uncomment if you want to delete
            return []


        logger.info(f"Processing video with Gemini: {video_file.display_name}")

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        generation_config = genai.types.GenerationConfig(
            # candidate_count=1, # Get only one response
            temperature=0.2 # Factual for receipt data
        )

        model = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config
        )

        # CRITICAL: Prompt engineered for video input
        # If the same list item is visible at different points in the video, treat it as one item and try to get the clearest information for it.
        prompt = """
        Analyze the entire content of this video, which shows a single grocery receipt being scanned or panned across.
        Your goal is to extract all individual items from this single receipt ignoring the supermarket discounts.

        For each distinct line item on the receipt, provide:
        1. 'item_name': The full description of the item as accurately as possible.
        2. 'item_size': The quantity purchased for that line item. If not explicitly stated, assume 1. If it's a weight (e.g., 0.5 kg), use that value. If it's an interpretable fractional quantity like "1/2 DOZEN", represent it as 6.
        3. 'price_per_unit': The price for a single unit of the item. If only a total price for multiple units is given (e.g., "2 for $5.00" or "APPLES @ 2/$3.00"), calculate and provide the per-unit price (e.g., 2.50 or 1.50). If it's a price per weight (e.g., $2.99/LB), use that. Ensure this is a numerical value.

        Return the data as a single, valid JSON list of objects. Each object in the list should represent one line item from the receipt and must have the keys "item_name", "item_size", and "price_per_unit".
        Example format: [{"item_name": "Organic Bananas", "item_size": 1.25, "price_per_unit": 0.79}, {"item_name": "Whole Milk Gallon", "item_size": 1, "price_per_unit": 3.99}]
        
        If no items can be clearly identified from the receipt in the video, or if the video does not appear to be a receipt, return an empty JSON list: [].

        Focus ONLY on the individual purchased line items. IGNORE general store information (name, address, phone), date/time, transaction numbers, loyalty card details, cashier name, marketing text, subtotals, taxes, total amount due, payment methods, and any other text not part of a specific purchased item line.

        Ensure your entire response is ONLY the JSON list and nothing else. Do not include any explanatory text before or after the JSON.
        Video to analyze:""" + f"{video_file.uri}\n"

        response = model.generate_content([prompt, video_file]) # Pass the uploaded file object

        # After processing, delete the uploaded file from Google's storage
        try:
            genai.delete_file(video_file.name)
            logger.info(f"Deleted uploaded video file: {video_file.name}")
        except Exception as e_del:
            logger.warning(f"Could not delete uploaded video file {video_file.name}: {e_del}")
        
        response_text = response.text.strip()
        # Clean potential markdown ```json ... ```
        if response_text.startswith("```json"):
            response_text = response_text[len("```json"):].strip()
        if response_text.endswith("```"):
            response_text = response_text[:-len("```")].strip()

        if not response_text:
            logger.warning(f"Gemini returned empty text for video {os.path.basename(video_path)}")
            return []

        try:
            extracted_data = json.loads(response_text)
            if not isinstance(extracted_data, list):
                logger.warning(f"Gemini did not return a list for video {os.path.basename(video_path)}. Got: {type(extracted_data)}")
                return []
            
            valid_items = []
            for item in extracted_data:
                if isinstance(item, dict) and \
                   'item_name' in item and \
                   'item_size' in item and \
                   'price_per_unit' in item:
                    valid_items.append(item)
                else:
                    logger.warning(f"Invalid item structure from Gemini (video): {item} for video {os.path.basename(video_path)}")
            
            logger.info(f"Successfully extracted {len(valid_items)} items from video {os.path.basename(video_path)} using Gemini.")
            return valid_items
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini video response for {os.path.basename(video_path)}: {e}. Response text: '{response_text}'")
            return []
        except Exception as e:
            logger.error(f"Error processing Gemini video response: {e}. Response text: '{response_text}'", exc_info=True)
            return []

    except Exception as e:
        logger.error(f"Error during Gemini video API call for {os.path.basename(video_path)}: {e}", exc_info=True)
        return []


# Example usage (for direct testing of this file)
if __name__ == '__main__':
    extract_date("temp_files/frame_1749233019.5217779.png")
    # sample_test_video = "test_data/PXL_20250606_064422557.mp4"

    # if os.path.exists(sample_test_video):
    #     print(f"\nTesting direct video processing with Gemini using video: {sample_test_video}")
    #     # Note: This direct test might take a while depending on video size and API response
    #     data_video = extract_data_from_video_gemini(sample_test_video)
    #     print("Extracted data from video:")
    #     if data_video:
    #         for item_data in data_video:
    #             print(item_data)
    #     else:
    #         print("No data extracted or an error occurred.")
    
#     frame_path = "temp_files/frame_13b88bff-85a0-46d3-8cad-65be0f51c287.png"
#     try:
#         if os.path.exists(frame_path):
#             print(f"Testing with Gemini using image: {frame_path}")
#             data = extract_data_from_frame_gemini(frame_path)
#             print("Extracted data:")
#             for item_data in data:
#                 print(item_data)

#     except ImportError:
#         print("Pillow (PIL) or google.generativeai is not installed. Cannot run direct test.")
#     except Exception as e:
#         print(f"An error occurred during direct test: {e}")
