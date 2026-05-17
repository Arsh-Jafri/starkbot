import re
import os
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class TextChunk:
    content: str
    source: str
    source_url: str
    chunk_id: int
    start_char: int
    end_char: int
    metadata: Dict[str, str]

class TextChunker:
    def __init__(self, chunk_size: int = 800, overlap_size: int = 200):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size

    def clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\|.*?\|', '', text)
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'^Source:.*?\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()

    def create_chunks_with_overlap(self, text: str, source: str, source_url: str) -> List[TextChunk]:
        cleaned_text = self.clean_text(text)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', cleaned_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_id = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size and current_chunk:
                chunk = TextChunk(
                    content=current_chunk.strip(),
                    source=source,
                    source_url=source_url,
                    chunk_id=chunk_id,
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    metadata={"chunk_size": len(current_chunk), "has_overlap": chunk_id > 0}
                )
                chunks.append(chunk)

                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                current_start = current_start + len(current_chunk) - len(overlap_text) - len(sentence) - 1
                chunk_id += 1
            else:
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence

        if current_chunk.strip():
            chunk = TextChunk(
                content=current_chunk.strip(),
                source=source,
                source_url=source_url,
                chunk_id=chunk_id,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                metadata={"chunk_size": len(current_chunk), "has_overlap": chunk_id > 0}
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        if len(text) <= self.overlap_size:
            return text
        overlap_start = len(text) - self.overlap_size
        while overlap_start < len(text) and text[overlap_start] != ' ':
            overlap_start += 1
        return text[overlap_start:].strip()


# Maps filename → (display name, canonical URL)
SOURCE_MAPPING = {
    # Original 3 sources
    "https_en.wikipedia.org_wiki_Iron_Man.txt": ("Wikipedia - Iron Man", "https://en.wikipedia.org/wiki/Iron_Man"),
    "https_marvelcinematicuniverse.fandom.com_wiki_Iron_Man.txt": ("MCU Wiki - Iron Man", "https://marvelcinematicuniverse.fandom.com/wiki/Iron_Man"),
    "https_www.marvel.com_characters_iron-man-tony-stark_in-comics.txt": ("Marvel.com - Iron Man Comics", "https://www.marvel.com/characters/iron-man-tony-stark/in-comics"),
    # 18 scraped sources
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
}


def main():
    chunker = TextChunker(chunk_size=800, overlap_size=200)
    all_chunks = []
    data_dir = "data"

    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith('.txt'):
            continue

        if filename not in SOURCE_MAPPING:
            print(f"⚠  No metadata for {filename}, skipping")
            continue

        source_name, source_url = SOURCE_MAPPING[filename]
        file_path = os.path.join(data_dir, filename)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = chunker.create_chunks_with_overlap(content, source_name, source_url)
        all_chunks.extend(chunks)
        print(f"  {source_name}: {len(chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)} from {len(set(c.source for c in all_chunks))} sources")
    return all_chunks


if __name__ == "__main__":
    chunks = main()
