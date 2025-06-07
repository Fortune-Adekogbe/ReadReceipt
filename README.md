# ReadReceipt

This project implements a bot that can extract line items from a scanned grocery receipt either as a PDF or as a video. It currently leverages Google's Gemini models for its advanced video understanding and OCR capabilities. Video processing is best done via the included Gradio app as Telegram has a size limit.

## Features
*   Telegram bot interface for easy interaction with PDFs.
*   Gradio app interface for easy interaction with Videos.
*   Utilizes Google Gemini models for powerful image- or video-based OCR and data extraction.
*   Extracts item name, quantity purchased, and cost per item.
*   Handles scrolling/panning videos of receipts.
*   Outputs data in a convenient CSV format.
*   Modular code structure for video processing, OCR, data aggregation, and bot logic.

## Project Structure

```
receipt-bot/
├── bot.py                     # Main Telegram bot logic
├── app_gradio.py              # Main Gradio app logic
├── video_processor.py         # Utility for video file cleanup and frame extraction methods
├── ocr_extractor.py           # Handles OCR and data extraction using Gemini API
├── data_aggregator.py         # Aggregates and formats data from OCR
├── config.py                  # For API keys and settings
├── .env.example               # Example environment file (copy to .env)
├── requirements.txt           # Python dependencies
└── temp_files/                # Directory for temporary video/frame files (auto-created)
```

## Telegram Bot Setup and Installation

**1. Prerequisites:**

*   Python 3.8+
*   A Telegram Bot Token (get from BotFather on Telegram)
*   A Google API Key for Gemini (create from Google AI Studio or Google Cloud Console).
*   (Optional) For Google Sheets:
    *   Google Sheets API and Google Drive API enabled in your Google Cloud Project.
    *   A Service Account JSON key file.
    *   A Google Sheet shared with the service account's email.

**2. Clone the Repository:**

```bash
git clone <your-repository-url>
cd receipt-bot
```

**3. Create a Virtual Environment (Recommended):**

```bash
python -m venv venv
venv/Scripts/activate.bat # On Linux: source venv/bin/activate
```

**4. Install Dependencies:**

```bash
pip install -r requirements.txt
```

**5. Configure Environment Variables:**
*   Create a `.env` file and fill in your actual credentials:
    ```env
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    GOOGLE_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"

    ```
    *   **`TELEGRAM_BOT_TOKEN`**: Your bot token from BotFather.
    *   **`GOOGLE_API_KEY`**: Your API key for accessing Gemini models.

**6. Create Temporary Files Directory:**

The `temp_files/` directory should be created automatically by `config.py` if it doesn't exist. If not, create it manually:
```bash
mkdir temp_files
```

## Running the Bot

Once all configurations are set, run the main bot script:

```bash
python bot.py
```

The bot will start polling for updates from Telegram.

## How to Use

1.  Find your bot on Telegram (the one you created with BotFather).
2.  Send the `/start` command to initiate a conversation.
3.  Send a video file of a receipt to the bot.
    *   Ensure the video clearly shows the receipt items.
    *   A smooth pan or scroll across the receipt is ideal.
4.  The bot will acknowledge the video and start processing. This may take some time depending on video length and API response times.
5.  Once processed, the bot will send back a CSV file containing the extracted receipt items.

## Key Technologies Used

*   **Python:** Core programming language.
*   **`python-telegram-bot`:** For interacting with the Telegram Bot API.
*   **gradio:** For building a minimal user interface.
*   **`google-generativeai`:** Python SDK for Google's Generative AI models (Gemini).
*   **`OpenCV-Python`:**  For video processing tasks like frame reading.
*   **`Pillow` (PIL Fork):** For image handling, particularly when preparing data for Gemini.
*   **`Pandas`:** For data manipulation and creating the CSV output.
*   **`scikit-image`:**  For SSIM calculation.
*   **`python-dotenv`:** For managing environment variables.

## Future Enhancements / To-Do

*   **Support for Image Inputs:** Allow users to send static images of receipts directly.
*   **Support for PDF Inputs:** Allow users to send static PDFs of receipts directly. ✅
*   **User Feedback & Progress:** Provide more granular feedback to the user during long processing steps.
*   **Configuration Options via Bot Commands:** Allow users to set preferences (e.g., output format).
*   **Advanced Aggregation Logic:** Further refine data aggregation if Gemini's direct output sometimes contains duplicates or needs cleaning. 
*   **Alternative OCR Models:** Integrate options for other OCR services or local OCR (e.g., Tesseract) as a fallback or alternative.
    - Try Mistral OCR
    - Consider Landing AI Document Agent
    - ...
*   **Testing:** Add unit and integration tests.
*   **Deployment:** Document steps for deploying the bot (e.g., using Docker, cloud platforms).
*   **More Robust Error Handling:** Implement more comprehensive error handling for API failures, invalid video formats, etc.


## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.