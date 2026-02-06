import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

MAX_CHARS = 4000


def clean_text(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def validate_wikipedia_url(url: str):
    parsed = urlparse(url)
    if "wikipedia.org" not in parsed.netloc:
        raise ValueError("Only Wikipedia URLs are supported")
    if "(disambiguation)" in parsed.path.lower():
        raise ValueError("Disambiguation pages are not supported")


def scrape_wikipedia(url: str):
    validate_wikipedia_url(url)

    res = requests.get(url, headers=HEADERS, timeout=15)
    if res.status_code != 200:
        raise Exception(f"Failed to fetch page ({res.status_code})")

    soup = BeautifulSoup(res.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.text.strip() if title_tag else "Unknown Title"

    raw_paragraphs = soup.select("p")
    paragraphs = []

    for p in raw_paragraphs:
        if p.find("span", class_="IPA"):
            continue

        text = clean_text(p.get_text())
        if len(text) > 60:
            paragraphs.append(text)

    if not paragraphs:
        raise Exception("No readable content found")

    summary = " ".join(paragraphs[:2])

    content = ""
    for p in paragraphs:
        if len(content) + len(p) > MAX_CHARS:
            break
        content += " " + p

    content = content.strip()

    sections = [
        h.text.strip()
        for h in soup.select("h2 span.mw-headline")
    ]

    return {
        "title": title,
        "summary": summary,
        "sections": sections,
        "content": content
    }
