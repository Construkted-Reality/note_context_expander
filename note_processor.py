#!/usr/bin/env python3
"""
Note Context Expander
Processes markdown notes by scraping URLs and adding AI-generated summaries.
"""

import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

from dotenv import load_dotenv
from tavily import TavilyClient
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
VLLM_BASE_URL = "http://vllm-03.internal:42069/v1"
SCRAPING_TAG_PREFIX = "### Scraping updated"

# Initialize clients
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
llm_client = OpenAI(
    base_url=VLLM_BASE_URL,
    api_key="outsider"  # vLLM doesn't require an API key
)


def extract_urls(content: str) -> List[str]:
    """Extract all URLs from markdown content."""
    # Match URLs in markdown format [text](url) and plain URLs
    markdown_urls = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    plain_urls = re.findall(r'https?://[^\s\)]+', content)
    
    # Combine both, preferring markdown URLs
    urls = [url for _, url in markdown_urls]
    
    # Add plain URLs that aren't already in markdown format
    for url in plain_urls:
        if url not in urls:
            urls.append(url)
    
    return urls


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video."""
    youtube_patterns = [
        r'youtube\.com/watch\?v=',
        r'youtu\.be/',
        r'youtube\.com/embed/'
    ]
    return any(re.search(pattern, url) for pattern in youtube_patterns)


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'youtube\.com/watch\?v=([^&]+)',
        r'youtu\.be/([^?]+)',
        r'youtube\.com/embed/([^?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_youtube_transcript(video_id: str) -> Optional[str]:
    """Fetch YouTube video transcript."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([entry['text'] for entry in transcript_list])
        return transcript
    except Exception as e:
        print(f"Error fetching YouTube transcript for {video_id}: {e}")
        return None


def scrape_web_content(url: str) -> Optional[str]:
    """Scrape web content using Tavily API."""
    try:
        response = tavily_client.extract(urls=[url])
        if response and 'results' in response and len(response['results']) > 0:
            return response['results'][0].get('raw_content', '')
        return None
    except Exception as e:
        print(f"Error scraping {url} with Tavily: {e}")
        return None


def summarize_with_llm(content: str, url: str) -> Optional[str]:
    """Generate summary using local vLLM server."""
    try:
        prompt = f"""Summarize the following content from {url} in 2-4 concise sentences. Focus on the main points and key takeaways.

Content:
{content[:4000]}  # Limit content to avoid token limits

Summary:"""

        response = llm_client.chat.completions.create(
            model="default",  # vLLM uses whatever model is loaded
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        print(f"Error generating summary with LLM: {e}")
        return None


def has_scraping_tag(content: str) -> bool:
    """Check if note already has a scraping updated tag."""
    return SCRAPING_TAG_PREFIX in content


def process_note(file_path: Path) -> bool:
    """Process a single markdown note file."""
    print(f"\nProcessing: {file_path}")
    
    try:
        # Read the note
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already processed
        if has_scraping_tag(content):
            print(f"  Skipping (already processed)")
            return False
        
        # Extract URLs
        urls = extract_urls(content)
        if not urls:
            print(f"  No URLs found")
            return False
        
        print(f"  Found {len(urls)} URL(s)")
        
        # Process each URL
        summaries = []
        for i, url in enumerate(urls, 1):
            print(f"  Processing URL {i}/{len(urls)}: {url}")
            
            if is_youtube_url(url):
                # Handle YouTube video
                video_id = extract_youtube_id(url)
                if video_id:
                    print(f"    Fetching YouTube transcript...")
                    transcript = get_youtube_transcript(video_id)
                    if transcript:
                        print(f"    Generating summary...")
                        summary = summarize_with_llm(transcript, url)
                        if summary:
                            summaries.append((url, summary))
                            print(f"    ✓ Summary generated")
                        else:
                            print(f"    ✗ Failed to generate summary")
                    else:
                        print(f"    ✗ Failed to fetch transcript")
                else:
                    print(f"    ✗ Could not extract video ID")
            else:
                # Handle regular web URL
                print(f"    Scraping web content...")
                web_content = scrape_web_content(url)
                if web_content:
                    print(f"    Generating summary...")
                    summary = summarize_with_llm(web_content, url)
                    if summary:
                        summaries.append((url, summary))
                        print(f"    ✓ Summary generated")
                    else:
                        print(f"    ✗ Failed to generate summary")
                else:
                    print(f"    ✗ Failed to scrape content")
        
        if not summaries:
            print(f"  No summaries generated")
            return False
        
        # Build the updated content
        updated_content = content
        
        # Add summaries after each URL
        for url, summary in summaries:
            # Find the URL in the content and add summary after it
            # Handle both markdown and plain URLs
            url_pattern = re.escape(url)
            
            # Try to find markdown link first
            markdown_pattern = rf'(\[([^\]]+)\]\({url_pattern}\))'
            match = re.search(markdown_pattern, updated_content)
            
            if match:
                # Insert summary after markdown link
                insert_pos = match.end()
                summary_text = f"\n\n**Summary:** {summary}\n"
                updated_content = updated_content[:insert_pos] + summary_text + updated_content[insert_pos:]
            else:
                # Try plain URL
                plain_pattern = rf'({url_pattern})'
                match = re.search(plain_pattern, updated_content)
                if match:
                    insert_pos = match.end()
                    summary_text = f"\n\n**Summary:** {summary}\n"
                    updated_content = updated_content[:insert_pos] + summary_text + updated_content[insert_pos:]
        
        # Add scraping tag at the end
        current_date = datetime.now().strftime("%Y-%m-%d")
        scraping_tag = f"\n\n{SCRAPING_TAG_PREFIX} {current_date}\n"
        updated_content += scraping_tag
        
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"  ✓ Note updated with {len(summaries)} summary/summaries")
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing note: {e}")
        return False


def process_directory(directory: Path) -> Tuple[int, int]:
    """Process all markdown files in directory recursively."""
    processed = 0
    skipped = 0
    
    # Find all .md files recursively
    md_files = list(directory.rglob("*.md"))
    
    if not md_files:
        print(f"No markdown files found in {directory}")
        return 0, 0
    
    print(f"Found {len(md_files)} markdown file(s)")
    
    for md_file in md_files:
        if process_note(md_file):
            processed += 1
        else:
            skipped += 1
    
    return processed, skipped


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process markdown notes by scraping URLs and adding AI summaries"
    )
    parser.add_argument(
        "directory",
        type=str,
        help="Directory containing markdown notes to process"
    )
    
    args = parser.parse_args()
    
    # Validate directory
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        sys.exit(1)
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory")
        sys.exit(1)
    
    # Check API key
    if not TAVILY_API_KEY:
        print("Error: TAVILY_API_KEY not found in .env file")
        sys.exit(1)
    
    print(f"Starting note processing in: {directory.absolute()}")
    print(f"Using vLLM server at: {VLLM_BASE_URL}")
    print("=" * 60)
    
    # Process directory
    processed, skipped = process_directory(directory)
    
    print("=" * 60)
    print(f"\nProcessing complete!")
    print(f"  Processed: {processed} note(s)")
    print(f"  Skipped: {skipped} note(s)")


if __name__ == "__main__":
    main()