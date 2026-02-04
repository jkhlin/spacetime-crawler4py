import re
from urllib.parse import urlparse

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
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        # blocks UCI Machine Learning Repository given in discussion slides
        if "archive.ics.uci.edu" in parsed.netloc:
            return False
            
        # block dataset related to big machine learning files
        if "datasets" in parsed.path.lower():
            return False
                    
        # match the 4 specified UCI domains and their subdomains
        if not re.match(r"^(?:.*\.)?(?:ics|cs|informatics|stat)\.uci\.edu$", parsed.netloc):
            return False

        # trap prevention rules
        
        # block file extensions
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            return False

        # wiki block
        if re.search(r"[?&](action|do|export|share|type|format|rev|rev2|image|diff|oldid|replytocom)=", url):
            return False
            
        # blocks specific dynamic endpoints that aren't web pages
        if re.search(r"/(api|feed|rss|atom|xmlrpc|wp-json|wp-content|wp-includes)/", parsed.path.lower()):
            return False

        # catches repeating directories that repeats 3+ times
        if re.search(r"^.*?(/.+?/).*?\1.*?\1.*?$", parsed.path):
            return False
            
        # calendar blocks for infinite date loops
        # blocks YYYY-MM-DD or YYYY-MM patterns in the URL
        if re.search(r"\d{4}-\d{2}(-\d{2})?", parsed.path):
            return False
        
        # blocks paths specifically ending in numbers usually dates
        if re.search(r"/(19|20)\d{2}(-\d{2})?(/|$)", parsed.path):
            return False

        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise
