"""
Project P6: Sliding Window Text Chunker with Overlap
"""

def chunk_text(
    text: str,
    chunk_size: int = 300,
    chunk_overlap: int = 50,
) -> list[str]:
    """
    Chunks text into overlapping segments preserving word boundaries.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += (chunk_size - chunk_overlap)

    return chunks
