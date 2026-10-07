from dataclasses import asdict
from app.rag.documents import KnowledgeDocument


def chunk_document(doc: KnowledgeDocument, chunk_size: int = 700, overlap: int = 120) -> list[dict]:
    text=" ".join(doc.text.split())
    chunks=[]; start=0; idx=0
    while start < len(text):
        end=min(len(text),start+chunk_size)
        if end < len(text):
            boundary=text.rfind(". ",start,end)
            if boundary > start+chunk_size//2: end=boundary+1
        chunk=text[start:end].strip()
        if chunk:
            item=asdict(doc); item.update({"chunk_id":idx,"text":chunk}); chunks.append(item); idx+=1
        if end>=len(text): break
        start=max(end-overlap,start+1)
    return chunks
