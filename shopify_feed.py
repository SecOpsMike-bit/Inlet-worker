"""Public Shopify first-party careers feed.

Shopify's careers page lists roles in HTML, but the public Ashby job-board
endpoint does not serve the 'shopify' slug (404 as verified 2026-10-13).
Parse only employer-hosted role links; do not invent a board slug or
treat a fetch failure as evidence of no vacancies.
"""

from html.parser import HTMLParser
from html import unescape
from urllib.parse import urljoin
import re
import urllib.request

CAREERS_URL = "https://www.shopify.com/careers"
ROLE_PATH = re.compile(r"^/careers/[a-z0-9][a-z0-9-]*_[0-9a-f]{8}-[0-9a-f-]{27,}$", re.I)
CYBER_TITLE = re.compile(
    r"\b(?:security|cyber|soc|incident|threat|detection|malware|identity)\b", re.I
)


def _fetch_html(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; GetInlets/3.0)"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read(2_000_000).decode("utf-8", "replace")


class _RoleLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.roles = []
        self.active = None
        self.field = None
        self.field_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.active is None and tag == "a":
            href = attrs.get("href", "")
            if ROLE_PATH.match(href):
                self.active = {"href": href, "title": "", "location": ""}
                self.field = None
                self.field_depth = 0
        elif self.active is not None:
            if tag == "h4":
                self.field = "title"
                self.field_depth = 1
            elif tag == "span" and not self.active["location"]:
                self.field = "location"
                self.field_depth = 1
            elif self.field:
                self.field_depth += 1

    def handle_data(self, data):
        if self.active and self.field:
            self.active[self.field] += data

    def handle_endtag(self, tag):
        if self.active is None:
            return
        if tag == "a":
            if self.active["title"]:
                self.roles.append(self.active)
            self.active = None
            self.field = None
        elif self.field:
            self.field_depth -= 1
            if self.field_depth <= 0:
                self.field = None


class _MainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.main_depth = 0
        self.blocked = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.main_depth += 1
        elif self.main_depth and tag in {"script", "style", "noscript", "nav", "footer"}:
            self.blocked += 1

    def handle_data(self, data):
        if self.main_depth and not self.blocked:
            s = data.strip()
            if s:
                self.parts.append(s)

    def handle_endtag(self, tag):
        if tag == "main":
            self.main_depth = max(0, self.main_depth - 1)
        elif self.blocked and tag in {"script", "style", "noscript", "nav", "footer"}:
            self.blocked -= 1


def fetch_shopify(cap=250, detail_cap=15):
    """Return normalized jobs; fetch full detail only for potentially cyber titles.

    Errors propagate so diagnostic status distinguishes failures from empty feeds.
    """
    parser = _RoleLinks()
    parser.feed(_fetch_html(CAREERS_URL))
    jobs = []
    seen = set()
    detail_calls = 0
    for role in parser.roles:
        url = urljoin(CAREERS_URL, role["href"])
        if url in seen:
            continue
        seen.add(url)
        title = re.sub(r"\s+", " ", unescape(role["title"])).strip()
        location = re.sub(r"\s+", " ", unescape(role["location"])).strip()
        if not title:
            continue
        text = ""
        if CYBER_TITLE.search(title) and detail_calls < detail_cap:
            detail_calls += 1
            try:
                detail = _MainText()
                detail.feed(_fetch_html(url))
                text = " ".join(detail.parts)[:25000]
            except Exception:
                # The index is authoritative for the vacancy. Keep the title
                # without pretending that a failed detail fetch is a description.
                pass
        jobs.append({"title": title, "location": location, "url": url,
                     "posted": "", "text": text})
        if len(jobs) >= cap:
            break
    return jobs
