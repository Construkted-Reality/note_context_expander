# Note Context Expander

A Python script that automatically processes markdown notes by scraping URLs and adding AI-generated summaries.

## Features

- **Recursive Processing**: Scans all markdown files in a directory and subdirectories
- **URL Detection**: Extracts both markdown-formatted and plain URLs
- **Web Scraping**: Uses Tavily API to scrape web content
- **YouTube Support**: Extracts transcripts from YouTube videos using youtube-transcript-api
- **AI Summarization**: Generates 2-4 sentence summaries using a local vLLM server
- **Smart Skipping**: Avoids reprocessing notes that have already been updated
- **Inline Summaries**: Adds summaries directly after each URL in the note

## Prerequisites

- Python 3.8+
- Tavily API key (get one at [tavily.com](https://tavily.com))
- Local vLLM server running at `http://192.168.8.90:42069/v1`

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your Tavily API key in `.env`:
```bash
TAVILY_API_KEY=your_actual_api_key_here
```

## Usage

Run the script with the path to your notes directory:

```bash
python note_processor.py /path/to/your/notes
```

### Example

```bash
python note_processor.py ~/Documents/Notes
```

The script will:
1. Find all `.md` files recursively
2. Skip notes that have already been processed (contain `### Scraping updated` tag)
3. Extract all URLs from each note
4. For each URL:
   - If it's a YouTube video: fetch the transcript
   - If it's a web page: scrape the content using Tavily
   - Generate a 2-4 sentence summary using your local LLM
   - Insert the summary after the URL in the note
5. Add a `### Scraping updated YYYY-MM-DD` tag at the end

## How It Works

### URL Processing

The script handles two types of URLs:

1. **Web URLs**: Scraped using Tavily API, then summarized
2. **YouTube URLs**: Transcript extracted using youtube-transcript-api, then summarized

### Summary Insertion

Summaries are inserted directly after each URL in the format:

```markdown
[Link Text](https://example.com)

**Summary:** This is a 2-4 sentence summary of the content...
```

### Skip Logic

Notes containing `### Scraping updated` are automatically skipped to avoid duplicate processing. This tag is added at the end of each processed note with the current date.

## Configuration

You can modify these settings in `note_processor.py`:

- `VLLM_BASE_URL`: URL of your local vLLM server (default: `http://192.168.8.90:42069/v1`)
- `SCRAPING_TAG_PREFIX`: Tag used to mark processed notes (default: `### Scraping updated`)

## Error Handling

The script includes comprehensive error handling:
- Failed URL scraping is logged but doesn't stop processing
- YouTube transcript errors are caught and reported
- LLM summarization failures are handled gracefully
- File I/O errors are caught and reported

## Example Output

```
Starting note processing in: /home/user/notes
Using vLLM server at: http://192.168.8.90:42069/v1
============================================================
Found 5 markdown file(s)

Processing: /home/user/notes/research.md
  Found 3 URL(s)
  Processing URL 1/3: https://example.com/article
    Scraping web content...
    Generating summary...
    ✓ Summary generated
  Processing URL 2/3: https://youtube.com/watch?v=abc123
    Fetching YouTube transcript...
    Generating summary...
    ✓ Summary generated
  Processing URL 3/3: https://another-site.com
    Scraping web content...
    Generating summary...
    ✓ Summary generated
  ✓ Note updated with 3 summary/summaries

Processing: /home/user/notes/already-processed.md
  Skipping (already processed)

============================================================

Processing complete!
  Processed: 1 note(s)
  Skipped: 4 note(s)
```

## Troubleshooting

### "TAVILY_API_KEY not found in .env file"
Make sure you've created a `.env` file with your Tavily API key.

### "Error generating summary with LLM"
Check that your vLLM server is running and accessible at the configured URL.

### "Error fetching YouTube transcript"
Some YouTube videos don't have transcripts available. The script will skip these and continue processing other URLs.

## License

MIT License - feel free to use and modify as needed.