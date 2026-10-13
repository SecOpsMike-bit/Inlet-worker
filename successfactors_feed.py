"""Read-only SuccessFactors public career-listing adapter.

The initial supported employer is Descartes. Only verified links to the
employer's own public job pages are followed. No authentication, scraping
of candidate data, or production DB writes are involved.
"""
import html
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


class _JobLinks(HTMLParser):
    def __init__(self, hostname):
        super().__init__(convert_charrefs=True)
        self.hostname = hostname
        self.links = []
        self._href = None
        self._label = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        parsed = urlsplit(urljoin("https://" + self.hostname, href))
        if parsed.hostname == self.hostname and re.fullmatch(
            r"/job/[^/]+/\d+/?", parsed.path
        ):
            self._href = parsed._replace(query="", fragment="").geturl()
            self._label = []

    def handle_data(self, data):
        if self._href:
            self._label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            title = html.unescape(" ".join(self._label)).strip()
            title = re.sub(r"\s+", " ", title)
            if title:
                self.links.append((title, self._href))
            self._href = None
            self._label = []


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        clean = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if clean:
            self.parts.append(clean)


def _get_page(url, timeout=12):
    request = urllib.request.Request(
        url, headers={"User-Agent": "GetInlets/1.0 (public careers research)"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_listing(page, board_url):
    """Extract distinct official job detail links, not navigation or apply URLs."""
    hostname = urlsplit(board_url).hostname
    if not hostname:
        raise ValueError("A valid employer board URL is required")
    parser = _JobLinks(hostname)
    parser.feed(page)
    return list(dict.fromkeys(parser.links))


def parse_job_detail(page):
    """Extract location from the actual posting; never infer it from prose."""
    parser = _Text()
    parser.feed(page)
    text = "\n".join(parser.parts)
    lines = parser.parts
    location = ""
    for index, line in enumerate(lines):
        if line.lower() == "location:" and index + 1 < len(lines):
            location = lines[index + 1]
            break
        if line.lower().startswith("location:") and len(line) > 9:
            location = line.split(":", 1)[1].strip()
            break
    # The description is retained for matching; missing location must not
    # become an unverified "remote" recommendation.
    return location, text


def fetch_successfactors(board_url, cap=35, get_page=None):
    """Fetch the first public listing page and up to cap job detail pages.

    Returns normalized job dicts. A missing or broken board raises an error
    so diagnostics distinguish feed failure from a real zero-opening result.
    """
    if not board_url or urlsplit(board_url).scheme != "https":
        raise ValueError("Expected an HTTPS SuccessFactors board URL")
    getter = get_page or _get_page
    listing = getter(board_url)
    links = parse_listing(listing, board_url)
    if not links:
        raise ValueError("No job detail links found; board markup may have changed")
    jobs = []
    for title, url in links[:cap]:
        try:
            location, description = parse_job_detail(getter(url))
        except Exception:
            continue
        if not location or len(description) < 100:
            continue
        jobs.append({
            "title": title,
            "location": location,
            "url": url,
            "posted": "",
            "text": description,
        })
    if not jobs:
        raise ValueError("No readable job detail pages; board markup may have changed")
    return jobs
