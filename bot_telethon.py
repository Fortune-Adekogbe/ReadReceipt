# bot_telethon.py
import logging
import os
import io
import asyncio
import time

from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeFilename # For sending files with specific names

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH, TEMP_DIR
from video_processor import extract_distinct_frames, cleanup_files
from ocr_extractor import extract_data_from_frame_gemini, extract_date, extract_data_from_video_gemini # This is our (mock) OCR call
from data_aggregator import aggregate_receipt_data
import pymupdf
# from google_sheets_handler import update_google_sheet # Uncomment if using GSheets

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
)
logger = logging.getLogger(__name__)

# logging.getLogger("telethon").setLevel(logging.WARNING) # Quieten Telethon's own info logs if desired
logging.getLogger("httpx").setLevel(logging.WARNING)


# Initialize Telethon client
# Ensure API_ID is an integer if read from environment, otherwise they should be fine from config.py
if isinstance(TELEGRAM_API_ID, str) and TELEGRAM_API_ID.isdigit():
    API_ID = int(TELEGRAM_API_ID)
else:
    API_ID = TELEGRAM_API_ID
API_HASH = TELEGRAM_API_HASH

client = TelegramClient('receipt_bot_session', API_ID, API_HASH)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event: events.NewMessage.Event) -> None:
    """Sends a welcome message when the /start command is issued."""
    await event.reply(
        "Hello! Send me a video or PDF of a receipt, and I'll try to extract the items into a table."
    )

@client.on(events.NewMessage(func=lambda e: e.video is not None))
async def handle_video(event: events.NewMessage.Event) -> None:
    """Processes the received video."""
    message = event.message
    if not message.video: # Should be redundant due to func filter, but good practice
        await event.reply("Please send a video file.")
        return

    # Use message ID for unique temporary filenames
    video_path = os.path.join(TEMP_DIR, f"video_{message.id}.mp4")
    
    await event.reply("Video received. Processing, please wait... This might take a while.")
    logger.info(f"Downloading video to {video_path}")
    # In Telethon, event.media or message.media can be used. message.video is more specific.
    await client.download_media(message.video, video_path)

    all_frame_files_to_clean = [video_path]
    
    try:
        # # Process video directly with Gemini (Optional path, currently commented out)
        # logger.info(f"Processing video directly: {video_path}")
        # extracted_items_from_video = extract_data_from_video_gemini(video_path)
        # if not extracted_items_from_video:
        #     await event.reply("Could not extract any items from the video. The video might be unclear, not a receipt, or an error occurred.")
        #     return
        # await event.reply(f"Gemini processing complete. Found {len(extracted_items_from_video)} potential items. Now aggregating and formatting...")
        # logger.info("Aggregating data from Gemini's video output.")
        # final_df = aggregate_receipt_data([extracted_items_from_video])

        # Extract distinct frames from video
        logger.info(f"Extracting distinct frames from {video_path}")
        distinct_frame_paths = extract_distinct_frames(video_path)
        all_frame_files_to_clean.extend(distinct_frame_paths)

        if not distinct_frame_paths:
            await event.reply("Could not extract any distinct frames from the video. Please try again with a clearer video.")
            return

        await event.reply(f"Found {len(distinct_frame_paths)} distinct frames. Now extracting data from each...")

        # Process each frame with OCR
        all_extracted_items_from_frames = []
        for i, frame_path in enumerate(distinct_frame_paths):
            logger.info(f"Processing frame {i+1}/{len(distinct_frame_paths)}: {frame_path}")
            try:
                items_in_frame = extract_data_from_frame_gemini(frame_path)
                if items_in_frame:
                    all_extracted_items_from_frames.append(items_in_frame)
                
                date_str = extract_date(frame_path) # this is designed to extract just the date
                if date_str: # If a date is found
                    # Add it as a special item or handle it as metadata
                    # For simplicity, adding as an item for now.
                    all_extracted_items_from_frames.append([{"item_name": date_str, "item_size": None, "price_per_unit": None}])
                    logger.info(f"Extracted date: {date_str} from {frame_path}")
            except Exception as e:
                logger.error(f"Error processing frame {frame_path}: {e}")
                await event.reply(f"Error processing one of the frames. Continuing with others if possible.")

        if not all_extracted_items_from_frames:
            await event.reply("No items could be extracted from the video frames.")
            return
        
        await event.reply("Data extraction complete. Aggregating results...")

        # Aggregate data from all frames
        logger.info("Aggregating data from all frames.")
        final_df = aggregate_receipt_data(all_extracted_items_from_frames)

        if final_df.empty:
            await event.reply("Could not aggregate any structured item data from the receipt.")
            return

        # Prepare and send CSV output
        csv_buffer = io.StringIO()
        final_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        csv_bytes_buffer = io.BytesIO(csv_buffer.getvalue().encode())
        
        await event.reply(
            file=csv_bytes_buffer,
            attributes=[DocumentAttributeFilename("receipt_data.csv")],
            message="Here are the extracted items from your receipt."
        )
        logger.info("Sent CSV to user.")

        # Populate Google Sheet
        # sheet_url = update_google_sheet(final_df)
        # if sheet_url:
        #     await event.reply(f"Data also uploaded to Google Sheets: {sheet_url}")
        # else:
        #     await event.reply("Could not upload to Google Sheets (check configuration or logs).")

    except Exception as e:
        logger.error(f"An error occurred during video processing: {e}", exc_info=True)
        await event.reply(f"Sorry, an error occurred while processing your video: {e}")
    finally:
        logger.info(f"Cleaning up temporary files: {all_frame_files_to_clean}")
        cleanup_files(all_frame_files_to_clean)

@client.on(events.NewMessage(func=lambda e: e.document is not None))
async def handle_document(event: events.NewMessage.Event) -> None:
    """Processes received documents, expecting PDFs."""
    message = event.message
    document = message.document

    if not(document.mime_type == "application/pdf" or message.video):
        await event.reply("❌ Please send me a PDF file or a Video, not something else.")
        return

    # Use message ID for unique temporary filenames
    pdf_filename = f"pdf_{message.id}.pdf"
    pdf_path = os.path.join(TEMP_DIR, pdf_filename)

    await event.reply("⬇️ Downloading your PDF...")
    await client.download_media(document, pdf_path)
    logger.info(f"Saved PDF to {pdf_path}")

    await event.reply("⚙️ Converting PDF pages to images... This may take a few seconds.")
        
    all_frame_files_to_clean = [pdf_path]
    
    try:
        distinct_frame_paths = []
        doc = pymupdf.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            zoom = 200 / 72 
            mat = pymupdf.Matrix(zoom, zoom)
            pix: pymupdf.Pixmap = page.get_pixmap(matrix=mat)

            image_filename = f"pdf_{message.id}_page_{page_index}.png"
            image_path = os.path.join(TEMP_DIR, image_filename)
            pix.save(image_path)
            distinct_frame_paths.append(image_path)
        doc.close()
            
        all_frame_files_to_clean.extend(distinct_frame_paths)

        if not distinct_frame_paths:
            await event.reply("Could not extract any images from the PDF.")
            return

        await event.reply(f"Found {len(distinct_frame_paths)} page(s). Now extracting data from each...")

        all_extracted_items_from_frames = []
        for i, frame_path in enumerate(distinct_frame_paths):
            logger.info(f"Processing page {i+1}/{len(distinct_frame_paths)}: {frame_path}")
            try:
                items_in_frame = extract_data_from_frame_gemini(frame_path)
                if items_in_frame:
                    all_extracted_items_from_frames.append(items_in_frame)
                
                date_str = extract_date(frame_path) # this is designed to extract just the date
                if date_str: # If a date is found
                    # Add it as a special item or handle it as metadata
                    # For simplicity, adding as an item for now.
                    all_extracted_items_from_frames.append([{"item_name": date_str, "item_size": None, "price_per_unit": None}])
                    logger.info(f"Extracted date: {date_str} from {frame_path}")

            except Exception as e:
                logger.error(f"Error processing page {frame_path}: {e}")
                await event.reply(f"Error processing one of the pages. Continuing with others if possible.")

        if not all_extracted_items_from_frames:
            await event.reply("No items could be extracted from the PDF pages.")
            return
        
        await event.reply("Data extraction complete. Aggregating results...")

        logger.info("Aggregating data from PDF.")
        final_df = aggregate_receipt_data(all_extracted_items_from_frames)

        if final_df.empty:
            await event.reply("Could not aggregate any structured item data from the receipt.")
            return

        csv_buffer = io.StringIO()
        final_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        csv_bytes_buffer = io.BytesIO(csv_buffer.getvalue().encode())
        
        await event.reply(
            file=csv_bytes_buffer,
            attributes=[DocumentAttributeFilename("receipt_data.csv")],
            message="Here are the extracted items from your receipt."
        )
        logger.info("Sent CSV to user.")

        # Populate Google Sheet
        # sheet_url = update_google_sheet(final_df)
        # if sheet_url:
        #     await event.reply(f"Data also uploaded to Google Sheets: {sheet_url}")
        # else:
        #     await event.reply("Could not upload to Google Sheets (check configuration or logs).")

    except Exception as e:
        logger.error(f"An error occurred during PDF processing: {e}", exc_info=True)
        await event.reply(f"Sorry, an error occurred while processing your PDF: {e}")
    finally:
        logger.info(f"Cleaning up temporary files: {all_frame_files_to_clean}")
        cleanup_files(all_frame_files_to_clean)

@client.on(events.NewMessage(func=lambda e: e.text and not e.text.startswith('/') and not e.video and not e.document))
async def handle_other_text(event: events.NewMessage.Event) -> None:
    """Handles other text messages that are not commands or media."""
    await event.reply("Please send a video or PDF of a receipt.")

async def main_telethon() -> None:
    """Start the bot using Telethon."""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH]):
        logger.error("TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, or TELEGRAM_API_HASH not set! Please set them in config.py or .env file.")
        return
    
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or \
       str(TELEGRAM_API_ID) == "1234567" or \
       TELEGRAM_API_HASH == "your_api_hash_here":
        logger.warning("Using default/placeholder API credentials or Bot Token. Please update them in config.py.")


    # Start the client
    # For bot accounts, bot_token parameter is used 
    await client.start(bot_token=TELEGRAM_BOT_TOKEN)
    logger.info("Bot started using Telethon. Press Ctrl+C to stop.")
    
    # Ensure TEMP_DIR exists
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        logger.info(f"Created temporary directory: {TEMP_DIR}")

    # Run the client until disconnected
    await client.run_until_disconnected()

if __name__ == "__main__":
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    # Use asyncio.run to start the main_telethon coroutine
    try:
        asyncio.run(main_telethon())
    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")