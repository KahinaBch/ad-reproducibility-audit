"""
get_ad_dois_by_year.py
----------------------
Step 1 of the AD Reproducibility Audit pipeline.

Queries the Crossref API to retrieve all journal articles published in
"Alzheimer's & Dementia" (Wiley, ISSN: 1552-5260 / 1552-5279) for a given year.

Adapted from: KahinaBch/mrm-reproducible-research-2025
Original methodology: Boudreau et al. "On the open-source landscape of MRM"

Differences from MRM pipeline:
- Target journal: Alzheimer's & Dementia (not MRM)
- No author gender analysis
- Added: sex-specific keyword detection (Step 3)
- Added: geographic origin analysis (Step 4)
"""

import argparse
import csv
import time
import requests
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Alzheimer's & Dementia — ISSN identifiers
AD_JOURNAL_ISSN = "1552-5260"        # Print ISSN
AD_JOURNAL_ISSN_ONLINE = "1552-5279" # Online ISSN
CROSSREF_BASE = "https://api.crossref.org/works"
CROSSREF_POLITE_EMAIL = "gbm6330e-project@example.com"  # polite pool

OUTPUT_COLUMNS = [
    "doi", "title", "year", "published_online",
    "volume", "issue", "page", "type",
    "n_authors", "first_author", "last_author",
    "url", "abstract_available",
]


def crossref_query(issn: str, year: int, offset: int = 0, rows: int = 100) -> dict:
    """Query Crossref for articles in a journal by ISSN and year."""
    params = {
        "filter": f"issn:{issn},type:journal-article,from-pub-date:{year}-01-01,until-pub-date:{year}-12-31",
        "rows": rows,
        "offset": offset,
        "mailto": CROSSREF_POLITE_EMAIL,
        "select": "DOI,title,published,published-online,volume,issue,page,type,author,abstract,URL",
        "sort": "published",
        "order": "asc",
    }
    resp = requests.get(CROSSREF_BASE, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_date(date_obj: dict | None) -> str:
    """Extract ISO date string from Crossref date object."""
    if not date_obj:
        return ""
    parts = date_obj.get("date-parts", [[]])[0]
    return "-".join(str(p).zfill(2) for p in parts if p is not None)


def parse_item(item: dict) -> dict:
    """Parse a single Crossref work item into our flat record."""
    authors = item.get("author", [])
    first_author = ""
    last_author = ""
    if authors:
        def fmt(a):
            given = a.get("given", "")
            family = a.get("family", "")
            return f"{given} {family}".strip()
        first_author = fmt(authors[0])
        last_author = fmt(authors[-1]) if len(authors) > 1 else first_author

    title = item.get("title", [""])[0] if item.get("title") else ""
    pub = item.get("published") or item.get("published-print") or item.get("published-online")
    pub_online = item.get("published-online")

    return {
        "doi": item.get("DOI", ""),
        "title": title,
        "year": extract_date(pub)[:4] if pub else "",
        "published_online": extract_date(pub_online),
        "volume": item.get("volume", ""),
        "issue": item.get("issue", ""),
        "page": item.get("page", ""),
        "type": item.get("type", ""),
        "n_authors": len(authors),
        "first_author": first_author,
        "last_author": last_author,
        "url": item.get("URL", ""),
        "abstract_available": "yes" if item.get("abstract") else "no",
    }


def fetch_all_dois(issn: str, year: int) -> list[dict]:
    """Paginate through Crossref to collect all articles for a given year."""
    records = []
    offset = 0
    rows = 100
    total = None

    log.info(f"Querying Crossref for ISSN={issn}, year={year}…")

    while True:
        try:
            data = crossref_query(issn, year, offset=offset, rows=rows)
        except requests.RequestException as e:
            log.error(f"Crossref request failed at offset {offset}: {e}")
            break

        message = data.get("message", {})
        if total is None:
            total = message.get("total-results", 0)
            log.info(f"  Total results reported by Crossref: {total}")

        items = message.get("items", [])
        if not items:
            break

        for item in items:
            records.append(parse_item(item))

        offset += rows
        log.info(f"  Retrieved {len(records)}/{total} records…")

        if offset >= total:
            break

        time.sleep(0.5)  # polite rate limiting

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve DOI list for Alzheimer's & Dementia articles from Crossref."
    )
    parser.add_argument("--year", type=int, required=True, help="Publication year to query")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path (default: data/derived/ad_{year}_dois.csv)",
    )
    args = parser.parse_args()

    out_path = args.out or Path(f"data/derived/ad_{args.year}_dois.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Try both ISSNs and merge (deduplication by DOI)
    seen_dois = set()
    all_records = []

    for issn in [AD_JOURNAL_ISSN, AD_JOURNAL_ISSN_ONLINE]:
        records = fetch_all_dois(issn, args.year)
        for r in records:
            if r["doi"] and r["doi"] not in seen_dois:
                seen_dois.add(r["doi"])
                all_records.append(r)
        time.sleep(1)

    log.info(f"\nTotal unique articles found: {len(all_records)}")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(all_records)

    log.info(f"Saved to: {out_path}")


if __name__ == "__main__":
    main()
