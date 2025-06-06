# bot.py
import logging
import os
import io

from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TEMP_DIR
from video_processor import extract_distinct_frames, cleanup_files
from ocr_extractor import extract_data_from_frame_gemini, extract_data_from_video_gemini # This is our (mock) OCR call
from data_aggregator import aggregate_receipt_data
# from google_sheets_handler import update_google_sheet # Uncomment if using GSheets

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! Send me a video of a receipt, and I'll try to extract the items into a table."
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes the received video."""
    message = update.message
    if not message.video:
        await message.reply_text("Please send a video file.")
        return

    video_file = await message.video.get_file()
    video_path = os.path.join(TEMP_DIR, f"{video_file.file_id}.mp4")
    
    await message.reply_text("Video received. Processing, please wait... This might take a while.")
    logger.info(f"Downloading video to {video_path}")
    await video_file.download_to_drive(video_path)

    all_frame_files_to_clean = [video_path]
    
    try:
        # # Process video directly with Gemini
        # logger.info(f"Processing video directly: {video_path}")
        # extracted_items_from_video = extract_data_from_video_gemini(video_path)

        # if not extracted_items_from_video: # If Gemini returns empty list or error
        #     await message.reply_text("Could not extract any items from the video. The video might be unclear, not a receipt, or an error occurred.")
        #     return
        
        # await message.reply_text(f"Gemini processing complete. Found {len(extracted_items_from_video)} potential items. Now aggregating and formatting...")

        # # Aggregate data (data_aggregator can still refine or format)
        # logger.info("Aggregating data from Gemini's video output.")
        # final_df = aggregate_receipt_data([extracted_items_from_video]) # Pass as list of lists

        # 1. Extract distinct frames from video
        logger.info(f"Extracting distinct frames from {video_path}")
        distinct_frame_paths = extract_distinct_frames(video_path)
        all_frame_files_to_clean.extend(distinct_frame_paths)

        if not distinct_frame_paths:
            await message.reply_text("Could not extract any distinct frames from the video. Please try again with a clearer video.")
            return

        await message.reply_text(f"Found {len(distinct_frame_paths)} distinct frames. Now extracting data from each...")

        # 2. Process each frame with OCR (simulated)
        all_extracted_items_from_frames = []
        for i, frame_path in enumerate(distinct_frame_paths):
            logger.info(f"Processing frame {i+1}/{len(distinct_frame_paths)}: {frame_path}")
            # In a real scenario, this call might be slow and could be done asynchronously
            # or you might provide progress updates.
            try:
                items_in_frame = extract_data_from_frame_gemini(frame_path) # Call to (mock) OCR
                if items_in_frame:
                    all_extracted_items_from_frames.append(items_in_frame)
            except Exception as e:
                logger.error(f"Error processing frame {frame_path}: {e}")
                await message.reply_text(f"Error processing one of the frames. Continuing with others if possible.")


        if not all_extracted_items_from_frames:
            await message.reply_text("No items could be extracted from the video frames.")
            return
        
        await message.reply_text("Data extraction complete. Aggregating results...")

        # 3. Aggregate data from all frames
        logger.info("Aggregating data from all frames.")
        final_df = aggregate_receipt_data(all_extracted_items_from_frames)

        if final_df.empty:
            await message.reply_text("Could not aggregate any structured item data from the receipt.")
            return

        # 4. Prepare and send CSV output
        csv_buffer = io.StringIO()
        final_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Convert StringIO to BytesIO for sending as a file
        csv_bytes_buffer = io.BytesIO(csv_buffer.getvalue().encode())
        
        await message.reply_document(
            document=InputFile(csv_bytes_buffer, filename="receipt_data.csv"),
            caption="Here are the extracted items from your receipt."
        )
        logger.info("Sent CSV to user.")

        # 5. (Optional) Populate Google Sheet
        # sheet_url = update_google_sheet(final_df)
        # if sheet_url:
        #     await message.reply_text(f"Data also uploaded to Google Sheets: {sheet_url}")
        # else:
        #     await message.reply_text("Could not upload to Google Sheets (check configuration or logs).")

    except Exception as e:
        logger.error(f"An error occurred during video processing: {e}", exc_info=True)
        await message.reply_text(f"Sorry, an error occurred while processing your video: {e}")
    finally:
        # 6. Cleanup temporary files
        logger.info(f"Cleaning up temporary files: {all_frame_files_to_clean}")
        cleanup_files(all_frame_files_to_clean)


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("TELEGRAM_BOT_TOKEN not set! Please set it in config.py or .env file.")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))

    # Message handlers
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
        lambda u,c: u.message.reply_text("Please send a video of a receipt.")))


    logger.info("Bot started. Press Ctrl+C to stop.")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    main()