"""Read-only TELUS Digital Canada listing adapter; no login or undocumented API.

Strictly fails when the public HTML format changes or listing coverage is incomplete.
"""
import html
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlsplit

CANADA_URL = "https://careers.telusdigital.com/search/jobs/in/country/canada"
HOST = "careers.telusdigital.com"
JOB_PATH = re.compile(r"^/jobs/\d+-[a-z0-9-]+/?$", re.I)
COUNT = re.compile(r"Showing\s+1\s*[-–]\s*(\d+)\s+of\s+(\d+)\s+result", re.I)

class JobLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = None
        self.depth = 0
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and self.active is None:
            href = attrs.get("href", "")
            url = urljoin(CANADA_URL, href)
            parsed = urlsplit(url)
            if parsed.scheme == "https" and parsed.hostname == HOST and JOB_PATH.match(parsed.path):
                self.active = [url, []]
                self.depth = 0
        elif self.active is not None and tag == "a":
            self.depth += 1
    def handle_data(self, data):
        if self.active is not None:
            self.active[1].append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            if self.depth:
                self.depth -= 1
            else:
                url, chunks = self.active
                title = " ".join(" ".join(chunks).split())
                if title:
                    self.links.append((url, title))
                self.active = None

def parse_canada_jobs(document):
    text = html.unescape(re.sub(r"<[^>]*>", " ", document))
    text = " ".join(text.split())
    match = COUNT.search(text)
    if not match:
        raise ValueError("TELUS Canada listing count missing or page format changed")
    displayed, total = map(int, match.groups())
    if displayed != total:
        raise ValueError(f"TELUS Canada listing is paginated ({displayed}/{total}); refusing partial coverage")
    parser = JobLinks()
    parser.feed(document)
    unique = dict(parser.links)
    if len(unique) != total:
        raise ValueError(f"TELUS Canada listing mismatch: {len(unique)} job links vs {total} reported")
    return [{"title": title, "location": "Canada (listing filter)", "url": url,
             "posted": "", "text": title} for url, title in unique.items()]

def fetch_telus_digital_canada():
    req = Request(CANADA_URL, headers={"User-Agent": "InletJobDiscovery/1.0", "Accept": "text/html"})
    with urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise ValueError(f"TELUS careers listing unexpected HTTP {response.status}")
        document = response.read(2_000_001)
    if len(document) > 2_000_000:
        raise ValueError("TELUS careers listing exceeded safe page size")
    return parse_canada_jobs(document.decode("utf-8", errors="replace"))
