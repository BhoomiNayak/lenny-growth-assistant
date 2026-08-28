"""Transcript chunking and parsing utilities.

Pure functions shared between the ingestion script and the test suite.
No external dependencies beyond the standard library + pyyaml.
"""

import re
from pathlib import Path

import yaml

# Chunking parameters
CHUNK_SIZE = 500  # target tokens per chunk (approx)
CHUNK_OVERLAP = 50  # overlap tokens between chunks
CHAR_PER_TOKEN = 4  # rough approximation


def parse_transcript(filepath: Path) -> dict | None:
    """Parse a transcript.md file into metadata + transcript text.

    Returns {"metadata": {...}, "transcript": "..."} or None if the file
    can't be read or is too short to be useful.
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    parts = content.split("---")
    if len(parts) >= 3:
        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            frontmatter = {}
        transcript = "---".join(parts[2:]).strip()
    else:
        frontmatter = {}
        transcript = content.strip()

    if not transcript or len(transcript) < 100:
        return None

    return {"metadata": frontmatter or {}, "transcript": transcript}


def split_sentences(text: str) -> list[str]:
    """Split text into sentences on terminal punctuation."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s for s in sentences if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks by approximate token count.

    Uses paragraph boundaries when possible, falling back to sentence
    splitting for oversized paragraphs.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_size = 0
    target_chars = chunk_size * CHAR_PER_TOKEN
    overlap_chars = overlap * CHAR_PER_TOKEN

    for para in paragraphs:
        para_len = len(para)

        if para_len > target_chars:
            # Flush current chunk
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                overlap_text = current_chunk[-1][-overlap_chars:] if current_chunk else ""
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text)

            # Split long paragraph by sentences
            sentences = split_sentences(para)
            for sent in sentences:
                sent_len = len(sent)
                if current_size + sent_len > target_chars and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    overlap_text = " ".join(current_chunk)[-overlap_chars:]
                    current_chunk = [overlap_text] if overlap_text else []
                    current_size = len(overlap_text)
                current_chunk.append(sent)
                current_size += sent_len
        else:
            if current_size + para_len > target_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                overlap_text = current_chunk[-1][-overlap_chars:] if current_chunk else ""
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(overlap_text)

            current_chunk.append(para)
            current_size += para_len

    if current_chunk:
        final = "\n\n".join(current_chunk)
        if final.strip():
            chunks.append(final)

    return chunks
