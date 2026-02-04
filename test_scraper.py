from scraper import is_valid

print(is_valid("http://www.ics.uci.edu/"))
print(is_valid("http://google.com/"))
print(is_valid("http://www.ics.uci.edu/foo/bar"))
print(is_valid("http://www.ics.uci.edu/a/b/a/b/a/b"))
print(is_valid("http://www.ics.uci.edu/calendar"))