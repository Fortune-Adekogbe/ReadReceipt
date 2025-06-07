import tempfile
import gradio as gr
import logging
import os
import io
import pandas as pd 
import time 

from config import TEMP_DIR
from video_processor import extract_distinct_frames, cleanup_files
from ocr_extractor import extract_data_from_frame_gemini #, extract_data_from_video_gemini
from data_aggregator import aggregate_receipt_data

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ensure TEMP_DIR for frames exists
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def process_video_for_gradio(video_path_input, progress=gr.Progress(track_tqdm=True)):
    """
    Core logic adapted from the Telegram bot's handle_video.
    Yields status updates and final results for Gradio components.
    """
    if video_path_input is None:
        yield "Please upload a video file.", None, None
        return

    video_path = video_path_input # Gradio's Video component provides the temp path directly

    status_updates = "Video received. Processing...\n"
    yield status_updates, None, None # Update status, no file/df yet

    all_files_to_clean = []# [video_path] # Gradio manages its own temp input file, but good to list if we copied it
    final_df = pd.DataFrame()
    temp_csv_path_for_gradio = None

    try:
        # Extract distinct frames from video
        status_updates += f"Extracting distinct frames from video...\n"
        yield status_updates, None, None
        progress(0.1, desc="Extracting frames")

        # extract_distinct_frames handles its temp storage or uses TEMP_DIR
        distinct_frame_paths = extract_distinct_frames(video_path)
        all_files_to_clean.extend(distinct_frame_paths)

        if not distinct_frame_paths:
            status_updates += "Could not extract any distinct frames. Try a clearer video.\n"
            yield status_updates, None, None
            return

        status_updates += f"Found {len(distinct_frame_paths)} distinct frames. Extracting data from each...\n"
        yield status_updates, None, None

        # Process each frame with OCR
        all_extracted_items_from_frames = []
        total_frames = len(distinct_frame_paths)
        for i, frame_path in enumerate(distinct_frame_paths):
            progress_val = 0.1 + (0.7 * (i + 1) / total_frames)
            progress(progress_val, desc=f"Processing frame {i+1}/{total_frames}") # Progress from 10% to 80%
            status_updates += f"Processing frame {i+1}/{total_frames}: {os.path.basename(frame_path)}\n"
            yield status_updates, None, None
            try:
                items_in_frame = extract_data_from_frame_gemini(frame_path)
                if items_in_frame:
                    all_extracted_items_from_frames.append(items_in_frame)
                    status_updates += f"  -> Found {len(items_in_frame)} potential items in frame {i+1}.\n"
                else:
                    status_updates += f"  -> No items found in frame {i+1}.\n"
                yield status_updates, None, None
            except Exception as e:
                logger.error(f"Error processing frame {frame_path}: {e}")
                status_updates += f"Error processing frame {os.path.basename(frame_path)}. Continuing...\n"
                yield status_updates, None, None


        if not all_extracted_items_from_frames:
            status_updates += "No items could be extracted from any video frames.\n"
            yield status_updates, None, None
            return
        
        status_updates += "Data extraction complete. Aggregating results...\n"
        progress(0.85, desc="Aggregating data")
        yield status_updates, None, None

        # Aggregate data from all frames
        final_df = aggregate_receipt_data(all_extracted_items_from_frames)

        if final_df.empty:
            status_updates += "Could not aggregate any structured item data.\n"
            yield status_updates, None, final_df # Show empty DataFrame
            return

        status_updates += "Aggregation complete. Preparing CSV.\n"
        progress(0.95, desc="Preparing output")
        yield status_updates, None, final_df # Show DataFrame, CSV not ready yet

        # Create CSV on disk
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False, dir=TEMP_DIR, encoding='utf-8') as tmp:
             final_df.to_csv(tmp.name, index=False)
             csv_path_to_serve = tmp.name # Get path string
        
        # DO NOT add csv_path_to_serve to frames_to_clean
             
        status_updates += "Done."
        progress(1.0, desc="Done")
        logger.info("Yielding final SUCCESS results (Path, DF) to Gradio.")
        # THE final successful yield, before finally runs
        yield status_updates, csv_path_to_serve, final_df 

    except Exception as e:
        logger.error(f"An error occurred during Gradio video processing: {e}", exc_info=True)
        status_updates += f"Sorry, an error occurred: {e}\n"
        yield status_updates, None, None # Error, no file/df
    finally:
        # Cleanup temporary files (frames, our temp CSV)
        status_updates += f"Cleaning up temporary files...\n"
        
        # Filter out the input video path if Gradio manages it fully (which it does)
        files_we_created = [f for f in all_files_to_clean if f != video_path_input]
        cleanup_files(files_we_created) # Cleanup frames and our temp CSV

        status_updates += f"Cleanup finished."


# Define Gradio Interface
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Read Receipts 🧾➡️📊")
    gr.Markdown("Upload a video of a receipt, and this tool will attempt to extract items into a CSV file.")

    with gr.Row():
        with gr.Column(scale=1): # Left column for inputs
            video_input = gr.Video(label="Upload Receipt Video", sources=["upload"], height=350)
            process_button = gr.Button("Process Video", variant="primary")

        with gr.Column(scale=2): # Right column for outputs
            with gr.Accordion("Processing Log", open=True):
                 status_log_output = gr.Textbox(
                    label="Status", lines=10, interactive=False, show_label=False
                )
            
            file_output = gr.File(label="Download Extracted CSV")
            dataframe_output = gr.DataFrame(
                label="Extracted Items Preview", wrap=True,
            )

    process_button.click(
        fn=process_video_for_gradio,
        inputs=[video_input],
        outputs=[status_log_output, file_output, dataframe_output]
    )

if __name__ == "__main__":
    demo.launch()