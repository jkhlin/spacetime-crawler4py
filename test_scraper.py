# TODO: delete when done
import re
from urllib.parse import urlparse
from scraper import is_valid

###  Test RegEx ###

example_url = "http://www.ics.uci.edu:443"
example_url_path = "http://www.ics.uci.edu/foo/bar"

print(f"RegEx Hostname Test:\n")
parsed = urlparse(example_url)
print(f"URL: {example_url}\nHost Name: {parsed.hostname}\n")

print(f"RegEx Path Test:\n")
parsed = urlparse(example_url_path)
print(f"URL: {example_url}\nPath: {parsed.path}\n")

### is_valid test ###

url_list = ["http://www.ics.uci.edu/", "http://google.com/", "http://www.ics.uci.edu/foo/bar",
            "http://www.ics.uci.edu/a/b/a/b/a/b", "http://www.ics.uci.edu/calendar"]

print(f"is_valid Test:\n")

for urls in url_list:
    print(f"{urls} -> {is_valid(urls)}")

print("\nEND OF TESTS")

# print(is_valid("http://www.ics.uci.edu/"))
# print(is_valid("http://google.com/"))
# print(is_valid("http://www.ics.uci.edu/foo/bar"))
# print(is_valid("http://www.ics.uci.edu/a/b/a/b/a/b"))
# print(is_valid("http://www.ics.uci.edu/calendar"))