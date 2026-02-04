import re
from urllib.parse import urlparse

# Matches only the allowed UCI department domains (ics, cs, informatics, stat),
# including any subdomains (e.g., vision.ics.uci.edu), and nothing outside uci.edu.
ALLOWED_HOST_NAMES = re.compile(r"^(?:.*\.)?(?:ics|cs|informatics|stat)\.uci\.edu$", re.IGNORECASE)

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

def scraper(url, resp):
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
    return list()

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        # scheme validation 
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        # Gets URL hostname or set to empty if None
        host_name = (parsed.hostname or "").lower()

        # If empty string -> false 
        if not host_name:
            return False

        # allowed domains only
        # match the 4 specified UCI domains and their subdomains
        if not ALLOWED_HOST_NAMES.match(host_name):
            return False
        
        # blocks UCI Machine Learning Repository given in discussion slides
        if host_name == "archive.ics.uci.edu":
            return False

        ### Trap Prevention Rules ### 

        # Gets URL path or set to empty string if None
        path = (parsed.path or "").lower()

        # Block bad file extensions
        if BAD_EXTENSIONS.match(path):
            return False
        
        # Block dataset directories (avoid large downloads)
        if re.search(r"/datasets?/", path):
            return False
        # Gets URL query or set to empty string if None
        query = (parsed.query or "").lower()

        # wiki block
        if re.search(r"[?&](action|do|export|share|type|format|rev|rev2|image|diff|oldid|replytocom)=", query):
            return False
            
        # blocks specific dynamic endpoints that aren't web pages
        if re.search(r"/(api|feed|rss|atom|xmlrpc|wp-json|wp-content|wp-includes)/", path):
            return False

        # catches repeating directories that repeats 3+ times
        if re.search(r"^.*?(/.+?/).*?\1.*?\1.*?$", path):
            return False
            
        # calendar blocks for infinite date loops
        if re.search(r"(^|/)calendar(/|$|\.)", path):
            return False

        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise
