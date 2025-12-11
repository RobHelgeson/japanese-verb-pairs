#!/usr/bin/env python3
"""
Scraper for edewakaru.com transitive/intransitive verb pairs.
Extracts verb pairs, example sentences, and images.
"""

import json
import os
import re
import time
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.edewakaru.com"
CATEGORY_URLS = {
    "beginner": "https://www.edewakaru.com/archives/cat_116824.html",
    "intermediate": "https://www.edewakaru.com/archives/cat_116825.html",
    "advanced": "https://www.edewakaru.com/archives/cat_116826.html",
}
OUTPUT_DIR = Path(__file__).parent
DATA_DIR = OUTPUT_DIR / "data"
IMAGES_DIR = OUTPUT_DIR / "images"

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests

# Headers to mimic browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def ensure_dirs():
    """Create output directories if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)


def fetch_page(url: str) -> BeautifulSoup | None:
    """Fetch a page and return BeautifulSoup object."""
    try:
        time.sleep(REQUEST_DELAY)
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_article_urls_from_category(category_url: str) -> list[str]:
    """Extract all article URLs from a category page (handles pagination)."""
    urls = []
    current_url = category_url

    while current_url:
        print(f"  Fetching category page: {current_url}")
        soup = fetch_page(current_url)
        if not soup:
            break

        # Find article links - they're in the main content area
        articles = soup.select(".article-title a, h2.article-title a, .article-body a")
        for a in articles:
            href = a.get("href", "")
            if "/archives/" in href and href.endswith(".html") and "cat_" not in href:
                full_url = urljoin(BASE_URL, href)
                if full_url not in urls:
                    urls.append(full_url)

        # Check for next page
        next_link = soup.select_one('a[rel="next"], .pager-next a, a:contains("次のページ")')
        if next_link:
            current_url = urljoin(BASE_URL, next_link.get("href", ""))
        else:
            # Try finding numbered pagination
            pager = soup.select(".pager a, .pagination a")
            current_page = None
            for p in pager:
                if "current" in p.get("class", []) or p.parent.get("class", []) == ["current"]:
                    try:
                        current_page = int(p.text.strip())
                    except ValueError:
                        pass

            if current_page:
                next_page_link = None
                for p in pager:
                    try:
                        if int(p.text.strip()) == current_page + 1:
                            next_page_link = p.get("href")
                            break
                    except ValueError:
                        continue
                if next_page_link:
                    current_url = urljoin(BASE_URL, next_page_link)
                else:
                    current_url = None
            else:
                current_url = None

    return urls


def download_image(img_url: str, verb_pair_id: str) -> str | None:
    """Download an image and return the local filename."""
    try:
        # Create a unique filename based on URL hash
        url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
        ext = Path(urlparse(img_url).path).suffix or ".jpg"
        filename = f"{verb_pair_id}_{url_hash}{ext}"
        filepath = IMAGES_DIR / filename

        if filepath.exists():
            return filename

        time.sleep(REQUEST_DELAY / 2)  # Shorter delay for images
        response = requests.get(img_url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        return filename
    except Exception as e:
        print(f"Error downloading image {img_url}: {e}")
        return None


def parse_verb_pair_title(title: str) -> tuple[str, str] | None:
    """Parse a title like '開く・開ける｜自動詞・他動詞' into verb pair."""
    # Remove the grammar category suffix
    title = re.split(r"[｜|]", title)[0].strip()

    # Split by various separators
    for sep in ["・", "／", "/"]:
        if sep in title:
            parts = title.split(sep)
            if len(parts) == 2:
                return (parts[0].strip(), parts[1].strip())

    return None


def extract_readings(soup: BeautifulSoup, verb: str) -> str | None:
    """Try to extract furigana/reading for a verb from the page."""
    # Look for ruby annotations or parenthetical readings
    text = soup.get_text()

    # Pattern: verb（reading）or verb(reading)
    patterns = [
        rf"{re.escape(verb)}[（(]([ぁ-んァ-ン]+)[）)]",
        rf"{re.escape(verb)}【([ぁ-んァ-ン]+)】",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None


def parse_article(url: str, level: str) -> dict | None:
    """Parse a single verb pair article."""
    print(f"  Parsing: {url}")
    soup = fetch_page(url)
    if not soup:
        return None

    # Extract title
    title_elem = soup.select_one("h2.article-title a, h1.article-title, .article-title")
    if not title_elem:
        title_elem = soup.select_one("h2 a, h1")

    if not title_elem:
        print(f"    Could not find title")
        return None

    title = title_elem.get_text(strip=True)
    verb_pair = parse_verb_pair_title(title)

    if not verb_pair:
        print(f"    Could not parse verb pair from: {title}")
        return None

    intransitive, transitive = verb_pair

    # Create ID from verb pair
    verb_id = f"{intransitive}_{transitive}".replace(" ", "")

    # Extract main content
    content = soup.select_one(".article-body, .article-content, .entry-content")
    if not content:
        content = soup

    text = content.get_text()

    # Extract example sentences
    examples = []

    # Look for basic examples with が and を particles
    # Pattern: Nounが + intransitive verb (自動詞)
    # Pattern: Nounを + transitive verb (他動詞)

    intransitive_examples = []
    transitive_examples = []

    # Find lines with the verbs and particles
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for examples with が (intransitive)
        if "が" in line and intransitive in line and "自動詞" in line:
            intransitive_examples.append(line)
        elif "が" in line and intransitive in line and len(line) < 100:
            intransitive_examples.append(line)

        # Look for examples with を (transitive)
        if "を" in line and transitive in line and "他動詞" in line:
            transitive_examples.append(line)
        elif "を" in line and transitive in line and len(line) < 100:
            transitive_examples.append(line)

    # Extract practice questions (①②③ etc.)
    practice_questions = []
    circled_numbers = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
    for char in circled_numbers:
        pattern = rf"{char}[^\n①②③④⑤⑥⑦⑧⑨⑩]+"
        matches = re.findall(pattern, text)
        for m in matches:
            if "【" in m and "】" not in m:
                m = m + "】"  # Fix incomplete brackets
            if len(m) > 5:  # Filter out very short matches
                practice_questions.append(m.strip())

    # Extract answers if present
    answers = []
    answer_section = re.search(r"【答え】(.+?)(?=【|$)", text, re.DOTALL)
    if answer_section:
        answer_text = answer_section.group(1)
        for char in circled_numbers:
            pattern = rf"{char}([^①②③④⑤⑥⑦⑧⑨⑩\n]+)"
            match = re.search(pattern, answer_text)
            if match:
                answers.append(match.group(1).strip())

    # Download images
    images = []
    img_tags = content.select("img")
    for img in img_tags[:5]:  # Limit to first 5 images
        src = img.get("src", "")
        if src and "resize.blogsys.jp" in src or "livedoor.blogimg.jp" in src:
            filename = download_image(src, verb_id)
            if filename:
                images.append({
                    "filename": filename,
                    "original_url": src,
                    "alt": img.get("alt", "")
                })

    # Try to get readings
    intransitive_reading = extract_readings(soup, intransitive)
    transitive_reading = extract_readings(soup, transitive)

    return {
        "id": verb_id,
        "title": title,
        "level": level,
        "intransitive": {
            "kanji": intransitive,
            "reading": intransitive_reading,
            "examples": intransitive_examples[:3],  # Limit examples
        },
        "transitive": {
            "kanji": transitive,
            "reading": transitive_reading,
            "examples": transitive_examples[:3],
        },
        "practice_questions": practice_questions[:10],
        "answers": answers,
        "images": images,
        "source_url": url,
        "attribution": "Source: edewakaru.com (絵でわかる日本語)"
    }


def scrape_level(level: str, category_url: str) -> list[dict]:
    """Scrape all verb pairs from a level category."""
    print(f"\nScraping {level} level from {category_url}")

    article_urls = get_article_urls_from_category(category_url)
    print(f"Found {len(article_urls)} articles")

    results = []
    for url in article_urls:
        data = parse_article(url, level)
        if data:
            results.append(data)
            # Save individual JSON
            filepath = DATA_DIR / f"{data['id']}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"    Saved: {filepath.name}")

    return results


def scrape_all():
    """Scrape all verb pairs from all levels."""
    ensure_dirs()

    all_data = {}

    for level, url in CATEGORY_URLS.items():
        data = scrape_level(level, url)
        all_data[level] = data

    # Save combined JSON
    combined_path = DATA_DIR / "all_verb_pairs.json"
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\nScraping complete!")
    print(f"Total verb pairs: {sum(len(v) for v in all_data.values())}")
    print(f"Combined data saved to: {combined_path}")


def scrape_beginner_only():
    """Scrape only the beginner level for testing."""
    ensure_dirs()

    data = scrape_level("beginner", CATEGORY_URLS["beginner"])

    # Save level JSON
    level_path = DATA_DIR / "beginner_verb_pairs.json"
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nBeginner scraping complete!")
    print(f"Total verb pairs: {len(data)}")
    print(f"Data saved to: {level_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--beginner":
        scrape_beginner_only()
    else:
        scrape_all()
