

def chunk_text(text: str, words_per_chunk: int = 120, overlap: int = 20):
    """Split text into overlapping word windows. Returns a list of strings.

    Example with words_per_chunk=120, overlap=20:
      chunk 0 = words 0..120, chunk 1 = words 100..220, chunk 2 = words 200..320
    each chunk starts 100 words after the previous one (120 - 20), so
    consecutive chunks share their last/first 20 words.
    """
    # Nothing to chunk.
    if not text or not text.strip():
        return []

    words = text.split()  # split on whitespace into a list of words

    # Guard against a nonsensical window size — treat the whole text as one chunk.
    if words_per_chunk <= 0:
        return [text.strip()]

    # How far the window advances each step. max(1, …) stops an overlap >=
    # words_per_chunk from making step 0 (which would loop forever).
    step = max(1, words_per_chunk - overlap)

    chunks = []
    for start in range(0, len(words), step):
        window = words[start : start + words_per_chunk]
        if window:
            chunks.append(" ".join(window))
        # Once this window reaches the end of the text, stop — otherwise the
        # trailing overlap would keep producing ever-shorter tail chunks.
        if start + words_per_chunk >= len(words):
            break
    return chunks
