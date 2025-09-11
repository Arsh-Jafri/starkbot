import re
import os
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class TextChunk:
    content: str
    source: str
    chunk_id: int
    start_char: int
    end_char: int
    metadata: Dict[str, str]

class TextChunker:
    def __init__(self, chunk_size: int = 800, overlap_size: int = 200):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\|.*?\|', '', text)
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'^Source:.*?\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()
    
    def create_chunks_with_overlap(self, text: str, source: str) -> List[TextChunk]:
        """Create overlapping chunks from text."""
        cleaned_text = self.clean_text(text)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', cleaned_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_id = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > self.chunk_size and current_chunk:
                # Create chunk
                chunk = TextChunk(
                    content=current_chunk.strip(),
                    source=source,
                    chunk_id=chunk_id,
                    start_char=current_start,
                    end_char=current_start + len(current_chunk),
                    metadata={"chunk_size": len(current_chunk), "has_overlap": chunk_id > 0}
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                current_start = current_start + len(current_chunk) - len(overlap_text) - len(sentence) - 1
                chunk_id += 1
            else:
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunk = TextChunk(
                content=current_chunk.strip(),
                source=source,
                chunk_id=chunk_id,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                metadata={"chunk_size": len(current_chunk), "has_overlap": chunk_id > 0}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Extract overlap text from the end of a chunk."""
        if len(text) <= self.overlap_size:
            return text
        
        overlap_start = len(text) - self.overlap_size
        while overlap_start < len(text) and text[overlap_start] != ' ':
            overlap_start += 1
        
        return text[overlap_start:].strip()

def main():
    """Process all Iron Man data files."""
    chunker = TextChunker(chunk_size=800, overlap_size=200)
    all_chunks = []
    
    source_mapping = {
        "https_en.wikipedia.org_wiki_Iron_Man.txt": "Wikipedia",
        "https_marvelcinematicuniverse.fandom.com_wiki_Iron_Man.txt": "MCU_Fandom", 
        "https_www.marvel.com_characters_iron-man-tony-stark_in-comics.txt": "Marvel_Comics"
    }
    
    data_dir = "data"
    
    for filename in os.listdir(data_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(data_dir, filename)
            source = source_mapping.get(filename, filename)
            
            print(f"Processing {filename}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks = chunker.create_chunks_with_overlap(content, source)
            all_chunks.extend(chunks)
            
            print(f"Created {len(chunks)} chunks from {filename}")
    
    print(f"\nTotal chunks created: {len(all_chunks)}")
    
    # Show distribution
    source_counts = {}
    for chunk in all_chunks:
        source_counts[chunk.source] = source_counts.get(chunk.source, 0) + 1
    
    for source, count in source_counts.items():
        print(f"{source}: {count} chunks")
    
    return all_chunks

if __name__ == "__main__":
    chunks = main()