from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text_into_chunks(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    return splitter.split_text(text)


def split_pages_into_chunks(pages, source_file):
    """
    pages: list of (page_number, text)
    Returns list of dicts: {text, source_file, page_number}
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = []
    for page_number, text in pages:
        for c in splitter.split_text(text):
            chunks.append({
                "text": c,
                "source_file": source_file,
                "page_number": page_number
            })
    return chunks