"""Fast, read-only diagnostic for configured Workday listing endpoints."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from directory import DIRECTORY

def main():
    company = next(c for c in DIRECTORY if c["name"] == "TELUS International")
    w = company["workday"]
    url = f'https://{w["tenant"]}.{w["pod"]}.myworkdayjobs.com/wday/cxs/{w["tenant"]}/{w["site"]}/jobs'
    payload = json.dumps({"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": "security"}).encode()
    req = Request(url, data=payload, method="POST",
                  headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "inlet/1.0"})
    try:
        with urlopen(req, timeout=12) as response:
            body = json.load(response)
            if not isinstance(body.get("jobPostings"), list):
                raise SystemExit("FAIL: endpoint responded without Workday jobPostings array")
            print(f'PASS: TELUS Workday listing HTTP {response.status}; sample={len(body["jobPostings"])}')
    except HTTPError as exc:
        raise SystemExit(f"FAIL: TELUS Workday listing HTTP {exc.code}; verify tenant/pod/site") from None
    except (URLError, TimeoutError) as exc:
        raise SystemExit(f"FAIL: TELUS Workday listing transport error: {type(exc).__name__}") from None

if __name__ == "__main__":
    main()
