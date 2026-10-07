import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class KnowledgeDocument:
    source: str
    topic: str
    organization: str
    title: str
    source_reference: str
    text: str


def load_documents(directory: Path) -> list[KnowledgeDocument]:
    docs=[]
    if not directory.exists():
        return docs
    for path in sorted(directory.glob("*.txt")):
        text=path.read_text(encoding="utf-8").strip()
        meta_path=path.with_suffix(".json")
        meta=json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        docs.append(KnowledgeDocument(
            source=path.name,
            topic=meta.get("topic",path.stem),
            organization=meta.get("organization","Development knowledge base"),
            title=meta.get("title",path.stem.replace("_"," ").title()),
            source_reference=meta.get("source_reference","local-development-content"),
            text=text,
        ))
    return docs


def load_cached_online_documents(directory: Path) -> list[KnowledgeDocument]:
    docs=[]
    if not directory.exists():
        return docs
    for path in sorted(directory.glob("*.json")):
        try:
            meta=json.loads(path.read_text(encoding="utf-8"))
            text=str(meta.get("text") or "").strip()
            if not text:
                continue
            docs.append(KnowledgeDocument(
                source=meta.get("source", path.name),
                topic=meta.get("topic", "medical concept"),
                organization=meta.get("organization", "Trusted online medical source"),
                title=meta.get("title", meta.get("topic", "Medical reference")),
                source_reference=meta.get("source_reference", ""),
                text=text,
            ))
        except Exception:
            continue
    return docs
