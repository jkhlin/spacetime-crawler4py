"""
Analytics module for web crawler.
Tracks all metrics required for the assignment report:
1. Unique pages count
2. Longest page by word count
3. Top 50 most common words (stopwords excluded)
4. Subdomains with unique page counts
"""

import os
import re
import atexit
import signal
from collections import Counter
from urllib.parse import urlparse, urldefrag
from bs4 import BeautifulSoup
from threading import Lock

# Thread-safe lock for analytics updates
_lock = Lock()

# ============== Global Analytics State ==============

# Set of defragmented URLs that were successfully fetched (status 200)
unique_pages = set()

# Longest page tracking
longest_page_url = ""
longest_page_word_count = 0

# Global word frequency counter
word_frequency = Counter()

# Subdomain tracking: {subdomain_hostname: set of unique defragmented URLs}
subdomain_pages = {}

# Stopwords set (loaded once)
_stopwords = None

# Flag to prevent double-writing on exit
_report_written = False


# ============== Stopwords Loading ==============

def load_stopwords():
    """Load stopwords from stopwords.txt file."""
    global _stopwords
    if _stopwords is not None:
        return _stopwords
    
    _stopwords = set()
    stopwords_path = os.path.join(os.path.dirname(__file__), "stopwords.txt")
    
    try:
        with open(stopwords_path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    _stopwords.add(word)
    except FileNotFoundError:
        print(f"Warning: stopwords.txt not found at {stopwords_path}")
    
    return _stopwords


# ============== Text Processing ==============

def get_visible_text(html_content):
    """
    Extract visible text from HTML content.
    Removes scripts, styles, and HTML markup.
    """
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'head', 'meta', 'link', 'noscript']):
            element.decompose()
        
        # Get text and normalize whitespace
        text = soup.get_text(separator=' ')
        return text
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""


def tokenize(text):
    """
    Tokenize text into words.
    Rules:
    - Lowercase
    - Alphabetic characters only
    - Minimum length of 2
    Returns list of tokens.
    """
    # Find all sequences of alphabetic characters
    tokens = re.findall(r'[a-zA-Z]+', text.lower())
    # Filter by minimum length
    return [token for token in tokens if len(token) > 3]


def count_words(text):
    """
    Count words in text (for longest page calculation).
    Returns total word count.
    """
    tokens = tokenize(text)
    return len(tokens)


def get_word_frequencies(text, stopwords):
    """
    Get word frequencies from text, excluding stopwords.
    Returns Counter of word frequencies.
    """
    tokens = tokenize(text)
    # Filter out stopwords
    filtered_tokens = [t for t in tokens if t not in stopwords]
    return Counter(filtered_tokens)


# ============== URL Processing ==============

def defragment_url(url):
    """Remove fragment from URL."""
    defragged, _ = urldefrag(url)
    return defragged


def get_subdomain(url):
    """
    Extract subdomain/hostname from URL.
    Only returns hostnames ending in uci.edu.
    """
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname.endswith("uci.edu"):
            return hostname
        return None
    except Exception:
        return None


# ============== Main Recording Function ==============

def record_page(url, resp):
    """
    Record analytics for a successfully fetched page.
    Called from scraper.py when resp.status == 200.
    
    Args:
        url: The URL that was fetched
        resp: Response object with raw_response.content
    """
    global longest_page_url, longest_page_word_count
    
    # Defragment the URL for uniqueness
    defragged_url = defragment_url(url)
    
    # Check if we have valid HTML content
    if not resp.raw_response or not resp.raw_response.content:
        return
    
    # Check content type - only process HTML
    content_type = ""
    try:
        content_type = resp.raw_response.headers.get("Content-Type", "").lower()
    except Exception:
        pass
    
    # Skip non-HTML content
    if content_type and "text/html" not in content_type and "text/plain" not in content_type:
        # Still count as unique page if it was fetched successfully
        pass
    
    with _lock:
        # Check if already processed (uniqueness)
        if defragged_url in unique_pages:
            return
        
        # Add to unique pages
        unique_pages.add(defragged_url)
        
        # Track subdomain
        subdomain = get_subdomain(defragged_url)
        if subdomain:
            if subdomain not in subdomain_pages:
                subdomain_pages[subdomain] = set()
            subdomain_pages[subdomain].add(defragged_url)
        
        # Process text content
        try:
            html_content = resp.raw_response.content
            text = get_visible_text(html_content)
            
            # Count words for longest page
            word_count = count_words(text)
            
            if word_count > longest_page_word_count:
                longest_page_word_count = word_count
                longest_page_url = defragged_url
            
            # Update word frequencies (excluding stopwords)
            stopwords = load_stopwords()
            frequencies = get_word_frequencies(text, stopwords)
            word_frequency.update(frequencies)
            
        except Exception as e:
            print(f"Error processing page {url}: {e}")


# ============== Report Generation ==============

def save_report():
    """
    Save all analytics to output files.
    Creates ./output/ directory if it doesn't exist.
    """
    global _report_written
    
    if _report_written:
        return
    
    _report_written = True
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    with _lock:
        # 1. Report summary
        summary_path = os.path.join(output_dir, "report_summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("WEB CRAWLER REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            # Question 1: Unique pages
            f.write("1. NUMBER OF UNIQUE PAGES\n")
            f.write("-" * 40 + "\n")
            f.write(f"   Total unique pages: {len(unique_pages)}\n\n")
            
            # Question 2: Longest page
            f.write("2. LONGEST PAGE BY WORD COUNT\n")
            f.write("-" * 40 + "\n")
            f.write(f"   URL: {longest_page_url}\n")
            f.write(f"   Word count: {longest_page_word_count}\n\n")
            
            # Question 3: Top 50 words
            f.write("3. TOP 50 MOST COMMON WORDS\n")
            f.write("-" * 40 + "\n")
            top_50 = word_frequency.most_common(50)
            for i, (word, count) in enumerate(top_50, 1):
                f.write(f"   {i:2}. {word}: {count}\n")
            f.write("\n")
            
            # Question 4: Subdomains
            f.write("4. SUBDOMAINS AND UNIQUE PAGE COUNTS\n")
            f.write("-" * 40 + "\n")
            f.write(f"   Total subdomains found: {len(subdomain_pages)}\n\n")
            # Sort alphabetically
            for subdomain in sorted(subdomain_pages.keys()):
                count = len(subdomain_pages[subdomain])
                f.write(f"   {subdomain}, {count}\n")
        
        print(f"\n[Analytics] Report saved to {summary_path}")
        
        # 2. Top 50 words CSV
        words_path = os.path.join(output_dir, "top50_words.csv")
        with open(words_path, "w", encoding="utf-8") as f:
            f.write("word,count\n")
            top_50 = word_frequency.most_common(50)
            for word, count in top_50:
                f.write(f"{word},{count}\n")
        
        print(f"[Analytics] Top 50 words saved to {words_path}")
        
        # 3. Subdomains CSV
        subdomains_path = os.path.join(output_dir, "subdomains.csv")
        with open(subdomains_path, "w", encoding="utf-8") as f:
            f.write("subdomain,count\n")
            for subdomain in sorted(subdomain_pages.keys()):
                count = len(subdomain_pages[subdomain])
                f.write(f"{subdomain},{count}\n")
        
        print(f"[Analytics] Subdomains saved to {subdomains_path}")
        
        # Print summary to console
        print("\n" + "=" * 60)
        print("CRAWLER ANALYTICS SUMMARY")
        print("=" * 60)
        print(f"Unique pages crawled: {len(unique_pages)}")
        print(f"Longest page: {longest_page_url} ({longest_page_word_count} words)")
        print(f"Unique words tracked: {len(word_frequency)}")
        print(f"Subdomains found: {len(subdomain_pages)}")
        print("=" * 60 + "\n")


# ============== Exit Handlers ==============

def _exit_handler():
    """Called on normal exit."""
    print("\n[Analytics] Saving report on exit...")
    save_report()


def _signal_handler(signum, frame):
    """Called on Ctrl+C (SIGINT) or SIGTERM."""
    print(f"\n[Analytics] Received signal {signum}, saving report...")
    save_report()
    # Exit cleanly without re-raising (let atexit handle final cleanup)
    import sys
    sys.exit(0)


# Register exit handlers
atexit.register(_exit_handler)

# Register signal handlers (SIGINT = Ctrl+C)
try:
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
except Exception:
    # Signal handling may not work on all platforms
    pass


# ============== Module Initialization ==============

# Load stopwords at module import time (once)
load_stopwords()
print(f"[Analytics] Loaded {len(_stopwords)} stopwords from stopwords.txt")
