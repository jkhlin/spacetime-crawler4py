import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import analytics

# Matches only the allowed UCI department domains (ics, cs, informatics, stat),
# including any subdomains (e.g., vision.ics.uci.edu), and nothing outside uci.edu.
ALLOWED_HOST_NAMES = re.compile(r"^(?:.*\.)?(?:ics|cs|informatics|stat)\.uci\.edu$", re.IGNORECASE)

NON_CONTENT_ELEMENTS = [
    'script', 'style', 'noscript', 'link', 'meta', 'base',
    'nav', 'header', 'footer', 'aside', 'menu',
    'form', 'input', 'button', 'select', 'textarea', 'label', 'datalist', 'output',
    'iframe', 'svg', 'canvas', 'template', 'dialog',
    'object', 'embed', 'applet', 'video', 'audio', 'track',
    'picture', 'source', 'map', 'area', 'param'
]

BAD_EXTENSIONS = re.compile(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", re.IGNORECASE
)

# Thresholds for valid pages
MIN_CONTENT_LENGTH = 100        # Minimum bytes
MAX_CONTENT_LENGTH = 10_000_000 # 10MB max
MIN_WORD_COUNT = 50             # Minimum words for "high information" page


def scraper(url, resp):
    # make sure status code is good or else early return
    if resp.status != 200:
        return []
    
    # Check for empty or missing content (dead URLs with 200 status)
    if not resp.raw_response or not resp.raw_response.content:
        return []
    
    content = resp.raw_response.content
    
    # valid webpage are often at max around 3-5 MB, so 10MB is a safe upper bound to avoid large non-webpage files
    # but not accidently filter out valid pages with lots of content
    if len(content) > MAX_CONTENT_LENGTH:
        print(f"Skipping large file ({len(content)} bytes): {url}")
        return []
    
    # avoid very small files (likely empty or error pages)
    if len(content) < MIN_CONTENT_LENGTH:
        print(f"Skipping small file ({len(content)} bytes): {url}")
        return []
    
    try:
        soup = BeautifulSoup(content, 'lxml')
        
        # Remove non-content elements and get text
        for element in soup(NON_CONTENT_ELEMENTS):
            element.decompose()
        text = soup.get_text(separator=' ', strip=True)
        
        # Count words (simple split)
        words = text.split()
        
        # Check for low information content
        if len(words) < MIN_WORD_COUNT:
            print(f"Skipping low-content page ({len(words)} words): {url}")
            return []
        
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []

    # Record analytics for this page
    analytics.record_page(url, resp)

    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    
    links = []
        
    # we actually have page content to parse
    if resp.status != 200 or not resp.raw_response or not resp.raw_response.content:
        return links
        
    try:
        soup = BeautifulSoup(resp.raw_response.content, 'lxml')
        
        # extract links
        for tag in soup.find_all('a', href=True): # href=True filters out <a> tags without href
            href = tag['href'].strip()
            
            # skip empty links
            if not href:
                continue
                
            # filter non-navigation links
            if href.startswith(("javascript:", "mailto:", "tel:")) or href == "#":
                continue

            # defragmentation to remove the '#' part ("page.html#section" -> "page.html")
            href = href.split('#')[0]
            if not href: # if it was just #section, it becomes empty after split
                continue

            # absolute URL conversion
            full_url = urljoin(url, href)
            
            # ensure we only keep http/https links
            parsed_url = urlparse(full_url)
            if parsed_url.scheme in ["http", "https"]:
                links.append(full_url)
                    
    except Exception as e:
        # if parsing fails print error but don't crash the crawler
        print(f"Error parsing {url}: {e}")
        
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        
        # Remove fragment per assignment spec
        url, _ = urldefrag(url)
        
        parsed = urlparse(url)

        # scheme validation 
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        # gets URL hostname or set to empty if None
        host_name = (parsed.hostname or "").lower()

        # If empty string -> false 
        if not host_name:
            return False

        # allowed domains only
        # match the 4 specified UCI domains and their subdomains
        if not ALLOWED_HOST_NAMES.match(host_name):
            return False
                    
        ### Trap Prevention Rules ### 

        # gets URL path or set to empty string if None
        path = (parsed.path or "").lower()

        # block bad file extensions
        if BAD_EXTENSIONS.match(path):
            return False
        
        # don't include the wiki because of internal admin pages with no value
        if "doku.php/group:" in path or "doku.php/support:" in path:
            return False

        # block dataset directories (avoid large downloads)
        if re.search(r"/datasets?/", path):
            return False
        
        # gets URL query or set to empty string if None
        query = (parsed.query or "").lower()

        # block Apache directory listing sort parameters (trap)
        # e.g., ?C=N;O=D, ?C=M;O=A - these are the same content with different sort orders
        # Use (^|...) to also match at the start of the query string
        if re.search(r"(^|[&;])(c|o)=", query):
            return False

        # Block calendar/event related query parameters (infinite trap)
        if re.search(r"(^|[&])(ical|outlook-ical|eventdisplay|tribe)=", query):
            return False
        
        # grape is a server with login errors that we don't have 
        if "grape.ics.uci.edu" in host_name:
            # timeline is an infinite calendar trap
            if "timeline" in path or "timeline" in query:
                return False
            # attachments are often binary files or code archives
            if "attachment" in path or "raw-attachment" in path:
                return False

        # block ngs (WordPress Login trap) but should allow blog posts and other content
        if "ngs.ics.uci.edu" in host_name:
            if "wp-login.php" in path:
                return False
            # also block the 'redirect_to' parameter just in case
            if "redirect_to=" in query:
                return False

        # blocks UCI Machine Learning Repository given in discussion slides
        if "archive.ics.uci.edu" in host_name:
            if "ml/machine-learning-databases" in path or "/dataset/" in path:
                return False
                        
        # blocks gitlab domains to infinite number of urls
        if "gitlab" in host_name:
            if re.search(r"/(tree|blob|blame|raw|commits?|graph|network|compare|pipelines|jobs?|archive)/", path):
                return False

        # wiki and CMS action parameters block
        if re.search(r"(^|[&])(action|do|export|share|type|format|rev|rev2|image|diff|oldid|replytocom|idx|view|expanded|sort)=", query):
            return False
            
        # block event directories (calendar traps)
        if "/event/" in path or "/events/" in path:
            return False
        
        # block Eppstein's pictures
        if re.search(r"/~eppstein/pix/", path):
            return False
        
        # blocks specific dynamic endpoints that aren't web pages
        if re.search(r"/(api|feed|rss|atom|xmlrpc|wp-json|wp-content|wp-includes)/", path):
            return False

        # catches repeating directories that repeats 3+ times
        if re.search(r"^.*?(/.+?/).*?\1.*?\1.*?$", path):
            return False
            
        # calendar blocks for infinite date loops
        # blocks YYYY-MM-DD or YYYY-MM patterns in the URL
        if re.search(r"\d{4}-\d{2}(-\d{2})?", path):
            return False
        
        # blocks MM-DD patterns often found in event URLs (e.g., /event/something-11-21)
        if re.search(r"-\d{1,2}-\d{1,2}$", path):
            return False
        
        # blocks paths specifically ending in numbers usually dates
        if re.search(r"/(19|20)\d{2}(-\d{2})?(/|$)", path):
            return False
        
        # block pagination traps (page/2, page/3, etc.) in list contexts
        if re.search(r"/page/\d+", path):
            return False

        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise
