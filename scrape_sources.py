"""
One-time script to download 18+ Marvel sources as plaintext files to data/.
"""
import os
import re
import time
import requests
from urllib.parse import urlparse

SOURCES = [
    # Wikipedia
    ("https://en.wikipedia.org/wiki/Iron_Man_in_other_media", "https_en.wikipedia.org_wiki_Tony_Stark.txt"),
    ("https://en.wikipedia.org/wiki/Iron_Man%27s_armor", "https_en.wikipedia.org_wiki_Iron_Man_armor.txt"),
    ("https://en.wikipedia.org/wiki/War_Machine", "https_en.wikipedia.org_wiki_War_Machine.txt"),
    ("https://en.wikipedia.org/wiki/Pepper_Potts", "https_en.wikipedia.org_wiki_Pepper_Potts.txt"),
    ("https://en.wikipedia.org/wiki/The_Avengers_(2012_film)", "https_en.wikipedia.org_wiki_Avengers_film.txt"),
    ("https://en.wikipedia.org/wiki/Captain_America:_Civil_War", "https_en.wikipedia.org_wiki_Civil_War_film.txt"),
    ("https://en.wikipedia.org/wiki/Stark_Industries", "https_en.wikipedia.org_wiki_Stark_Industries.txt"),
    ("https://en.wikipedia.org/wiki/Extremis", "https_en.wikipedia.org_wiki_Extremis.txt"),
    ("https://en.wikipedia.org/wiki/Iron_Monger", "https_en.wikipedia.org_wiki_Iron_Monger.txt"),
    ("https://en.wikipedia.org/wiki/Whiplash_(Marvel_Comics)", "https_en.wikipedia.org_wiki_Whiplash.txt"),
    ("https://en.wikipedia.org/wiki/Justin_Hammer", "https_en.wikipedia.org_wiki_Justin_Hammer.txt"),
    ("https://en.wikipedia.org/wiki/Nick_Fury", "https_en.wikipedia.org_wiki_Nick_Fury.txt"),
    ("https://en.wikipedia.org/wiki/S.H.I.E.L.D.", "https_en.wikipedia.org_wiki_SHIELD.txt"),
    ("https://en.wikipedia.org/wiki/Happy_Hogan_(character)", "https_en.wikipedia.org_wiki_Happy_Hogan.txt"),
    ("https://en.wikipedia.org/wiki/J.A.R.V.I.S.", "https_en.wikipedia.org_wiki_JARVIS.txt"),
    # More Wikipedia sources to replace blocked fandom ones
    ("https://en.wikipedia.org/wiki/War_Machine_(film)", "https_marvelcinematicuniverse.fandom.com_wiki_War_Machine.txt"),
    ("https://en.wikipedia.org/wiki/Avengers:_Endgame", "https_marvelcinematicuniverse.fandom.com_wiki_Rescue.txt"),
    ("https://en.wikipedia.org/wiki/Avengers:_Infinity_War", "https_marvelcinematicuniverse.fandom.com_wiki_Avengers.txt"),
]

SOURCE_METADATA = {
    "https_en.wikipedia.org_wiki_Tony_Stark.txt": ("Wikipedia - Tony Stark", "https://en.wikipedia.org/wiki/Tony_Stark_(Marvel_Comics)"),
    "https_en.wikipedia.org_wiki_Iron_Man_armor.txt": ("Wikipedia - Iron Man Armor", "https://en.wikipedia.org/wiki/Iron_Man%27s_armor"),
    "https_en.wikipedia.org_wiki_War_Machine.txt": ("Wikipedia - War Machine", "https://en.wikipedia.org/wiki/War_Machine"),
    "https_en.wikipedia.org_wiki_Pepper_Potts.txt": ("Wikipedia - Pepper Potts", "https://en.wikipedia.org/wiki/Pepper_Potts"),
    "https_en.wikipedia.org_wiki_Avengers_film.txt": ("Wikipedia - The Avengers", "https://en.wikipedia.org/wiki/Avengers_(film)"),
    "https_en.wikipedia.org_wiki_Civil_War_film.txt": ("Wikipedia - Civil War", "https://en.wikipedia.org/wiki/Captain_America:_Civil_War"),
    "https_en.wikipedia.org_wiki_Stark_Industries.txt": ("Wikipedia - Stark Industries", "https://en.wikipedia.org/wiki/Stark_Industries"),
    "https_en.wikipedia.org_wiki_Extremis.txt": ("Wikipedia - Extremis", "https://en.wikipedia.org/wiki/Extremis"),
    "https_en.wikipedia.org_wiki_Iron_Monger.txt": ("Wikipedia - Iron Monger", "https://en.wikipedia.org/wiki/Iron_Monger"),
    "https_en.wikipedia.org_wiki_Whiplash.txt": ("Wikipedia - Whiplash", "https://en.wikipedia.org/wiki/Whiplash_(Marvel_Comics)"),
    "https_en.wikipedia.org_wiki_Justin_Hammer.txt": ("Wikipedia - Justin Hammer", "https://en.wikipedia.org/wiki/Justin_Hammer"),
    "https_en.wikipedia.org_wiki_Nick_Fury.txt": ("Wikipedia - Nick Fury", "https://en.wikipedia.org/wiki/Nick_Fury"),
    "https_en.wikipedia.org_wiki_SHIELD.txt": ("Wikipedia - S.H.I.E.L.D.", "https://en.wikipedia.org/wiki/S.H.I.E.L.D."),
    "https_en.wikipedia.org_wiki_Happy_Hogan.txt": ("Wikipedia - Happy Hogan", "https://en.wikipedia.org/wiki/Happy_Hogan"),
    "https_en.wikipedia.org_wiki_JARVIS.txt": ("Wikipedia - JARVIS", "https://en.wikipedia.org/wiki/J.A.R.V.I.S."),
    "https_marvelcinematicuniverse.fandom.com_wiki_War_Machine.txt": ("Wikipedia - War Machine Film", "https://en.wikipedia.org/wiki/War_Machine_(film)"),
    "https_marvelcinematicuniverse.fandom.com_wiki_Rescue.txt": ("Wikipedia - Avengers: Endgame", "https://en.wikipedia.org/wiki/Avengers:_Endgame"),
    "https_marvelcinematicuniverse.fandom.com_wiki_Avengers.txt": ("Wikipedia - Avengers: Infinity War", "https://en.wikipedia.org/wiki/Avengers:_Infinity_War"),
    # existing 3 sources
    "https_en.wikipedia.org_wiki_Iron_Man.txt": ("Wikipedia - Iron Man", "https://en.wikipedia.org/wiki/Iron_Man"),
    "https_marvelcinematicuniverse.fandom.com_wiki_Iron_Man.txt": ("MCU Wiki - Iron Man", "https://marvelcinematicuniverse.fandom.com/wiki/Iron_Man"),
    "https_www.marvel.com_characters_iron-man-tony-stark_in-comics.txt": ("Marvel.com - Iron Man Comics", "https://www.marvel.com/characters/iron-man-tony-stark/in-comics"),
}


def extract_text_from_wikipedia(html: str) -> str:
    """Extract main article text from Wikipedia HTML."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("Install beautifulsoup4: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for tag in soup.find_all(["script", "style", "sup", "table", "figure", "figcaption",
                               "div.navbox", "div.sidebar", "div.reflist", "div.references",
                               "span.mw-editsection"]):
        tag.decompose()

    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        return ""

    paragraphs = content_div.find_all("p")
    text = "\n\n".join(p.get_text(separator=" ") for p in paragraphs if p.get_text(strip=True))
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_text_from_fandom(html: str) -> str:
    """Extract main article text from Fandom wiki HTML."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("Install beautifulsoup4: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "sup", "table", "figure",
                               "aside", "div.wikia-ad", "div.toc"]):
        tag.decompose()

    content_div = soup.find("div", {"class": "mw-parser-output"})
    if not content_div:
        return ""

    paragraphs = content_div.find_all("p")
    text = "\n\n".join(p.get_text(separator=" ") for p in paragraphs if p.get_text(strip=True))
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def scrape_url(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StarkBot-scraper/1.0)"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    if "wikipedia.org" in url:
        return extract_text_from_wikipedia(response.text)
    elif "fandom.com" in url:
        return extract_text_from_fandom(response.text)
    else:
        return response.text


def main():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    success = 0
    for url, filename in SOURCES:
        out_path = os.path.join(data_dir, filename)
        if os.path.exists(out_path):
            print(f"⏭  Already exists: {filename}")
            success += 1
            continue

        print(f"⬇  Downloading: {url}")
        try:
            text = scrape_url(url)
            if len(text) < 200:
                print(f"  ⚠  Very short content ({len(text)} chars), skipping")
                continue
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  ✅ Saved {len(text)} chars → {filename}")
            success += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")

        time.sleep(1)  # polite crawl delay

    print(f"\nDone: {success}/{len(SOURCES)} sources saved")


if __name__ == "__main__":
    main()
