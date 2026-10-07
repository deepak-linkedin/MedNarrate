from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.config import get_settings
from app.rag.chunker import chunk_document
from app.rag.documents import KnowledgeDocument
from app.schemas.rag import EvidenceChunk


class TrustedOnlineRetriever:
    """
    Retrieve medical evidence only from allow-listed domains.

    Responsibilities:
    - Tavily trusted-domain search
    - prefer Tavily's cleaned search content over raw webpage content
    - remove obvious web/navigation boilerplate
    - deduplicate URLs
    - deduplicate near-identical text chunks
    - preserve provenance

    Persistence is handled by PgVectorStore so bundled and online
    knowledge follow the same storage path.
    """

    TAVILY_SEARCH_URL = "https://api.tavily.com/search"

    # Prefer patient-facing authoritative medical sources before
    # research-heavy literature sources.
    SOURCE_PRIORITY = {
        "medlineplus.gov": 1,
        "nhs.uk": 1,

        "nih.gov": 2,
        "nlm.nih.gov": 2,
        "cdc.gov": 2,
        "who.int": 2,

        "msdmanuals.com": 3,

        "ncbi.nlm.nih.gov": 4,
    }

    def __init__(self):
        self.settings = get_settings()

    @property
    def available(self) -> bool:
        return (
            self.settings.online_rag_enabled
            and self.settings.web_search_provider.lower() == "tavily"
            and bool(self.settings.tavily_api_key.strip())
        )

    def _trusted(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()

        return any(
            host == domain or host.endswith("." + domain)
            for domain in self.settings.trusted_medical_domain_list
        )

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize URLs so the same page with fragments/trailing slashes
        is treated as one source.
        """

        try:
            parsed = urlparse(url)

            normalized = parsed._replace(
                fragment="",
                query="",
            )

            clean = urlunparse(normalized).rstrip("/")

            return clean
        except Exception:
            return url.rstrip("/")

    @staticmethod
    def _clean_web_text(text: str) -> str:
        if not text:
            return ""

        # Markdown images
        text = re.sub(
            r"!\[[^\]]*\]\([^)]+\)",
            " ",
            text,
        )

        # Markdown links — keep label, remove URL
        text = re.sub(
            r"\[([^\]]+)\]\([^)]+\)",
            r"\1",
            text,
        )

        # Raw URLs
        text = re.sub(
            r"https?://\S+",
            " ",
            text,
        )

        boilerplate_patterns = [
            r"skip to main content",
            r"primary site navigation",
            r"secondary site navigation",
            r"search",
            r"close",
            r"expand",
            r"collapse",
            r"log in",
            r"sign in",
            r"menu",
            r"share",
            r"print",
            r"download",
            r"save",
            r"cite",
            r"permissions",
            r"copyright",
            r"ncbi home page",
            r"pubmed disclaimer",
            r"the site is secure",
            r"official websites use \.gov",
            r"share sensitive information only on official.*?websites",
            r"https means you've safely connected.*",
        ]

        for pattern in boilerplate_patterns:
            text = re.sub(
                pattern,
                " ",
                text,
                flags=re.IGNORECASE,
            )

        # Remove common markdown/HTML-ish leftovers
        text = re.sub(r"#{1,6}\s*", " ", text)
        text = re.sub(r"\*{1,3}", " ", text)
        text = re.sub(r"`+", " ", text)

        # Remove excessive bracket artifacts
        text = re.sub(r"\[\s*\]", " ", text)

        # Normalize whitespace
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    @staticmethod
    def _text_hash(text: str) -> str:
        normalized = re.sub(
            r"\s+",
            " ",
            text.lower().strip(),
        )

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    def _source_priority(self, url: str) -> int:
        host = (urlparse(url).hostname or "").lower()

        for domain, priority in self.SOURCE_PRIORITY.items():
            if host == domain or host.endswith("." + domain):
                return priority

        return 10

    def _organization_name(self, url: str) -> str:
        host = (urlparse(url).hostname or "").lower()

        if host.endswith("medlineplus.gov"):
            return "MedlinePlus / U.S. National Library of Medicine"

        if host.endswith("ncbi.nlm.nih.gov"):
            return "NCBI / U.S. National Library of Medicine"

        if host.endswith("nlm.nih.gov"):
            return "U.S. National Library of Medicine"

        if host.endswith("nih.gov"):
            return "National Institutes of Health"

        if host.endswith("cdc.gov"):
            return "Centers for Disease Control and Prevention"

        if host.endswith("who.int"):
            return "World Health Organization"

        if host.endswith("nhs.uk"):
            return "NHS"

        if host.endswith("msdmanuals.com"):
            return "MSD Manual"

        return host or "Trusted medical source"

    def search(
        self,
        query: str,
        topic: str,
    ) -> list[EvidenceChunk]:

        if not self.available:
            return []

        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "search_depth": self.settings.online_rag_search_depth,
            "max_results": self.settings.online_rag_max_results,
            "include_domains": self.settings.trusted_medical_domain_list,

            # Important:
            # We don't need full raw-page dumps for our normal retrieval.
            "include_raw_content": False,

            "topic": "general",
        }

        try:
            with httpx.Client(
                timeout=18.0,
                follow_redirects=True,
            ) as client:

                response = client.post(
                    self.TAVILY_SEARCH_URL,
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

        except Exception as exc:
            print(
                f"[Online RAG] Search unavailable: {exc}"
            )

            # RAG can still continue using pgvector.
            return []

        raw_results = data.get("results", [])

        # ---------------------------------------------------------
        # STEP 1:
        # Validate URLs and remove duplicate source pages.
        # ---------------------------------------------------------

        unique_results: list[dict] = []
        seen_urls: set[str] = set()

        for result in raw_results:

            url = str(
                result.get("url") or ""
            ).strip()

            if not url:
                continue

            if not self._trusted(url):
                continue

            normalized_url = self._normalize_url(url)

            if normalized_url in seen_urls:
                continue

            seen_urls.add(normalized_url)

            result["_normalized_url"] = normalized_url

            unique_results.append(result)

        # ---------------------------------------------------------
        # STEP 2:
        # Patient-facing sources first, research papers later.
        #
        # Within the same source tier, preserve Tavily relevance.
        # ---------------------------------------------------------

        unique_results.sort(
            key=lambda result: (
                self._source_priority(
                    result["_normalized_url"]
                ),
                -float(result.get("score") or 0),
            )
        )

        evidence: list[EvidenceChunk] = []

        seen_chunk_hashes: set[str] = set()

        retrieved_at = datetime.now(
            timezone.utc
        ).isoformat()

        # ---------------------------------------------------------
        # STEP 3:
        # Clean and chunk each unique source.
        # ---------------------------------------------------------

        for result in unique_results:

            url = result["_normalized_url"]

            # Prefer Tavily's extracted relevant content.
            #
            # This prevents storing an entire page full of NCBI
            # navigation, icons, login links, etc.
            raw_text = str(
                result.get("content") or ""
            ).strip()

            cleaned_text = self._clean_web_text(
                raw_text
            )

            if len(cleaned_text) < 80:
                continue

            host = (
                urlparse(url).hostname
                or "Trusted medical source"
            )

            title = str(
                result.get("title") or topic
            ).strip()

            score = float(
                result.get("score") or 0.70
            )

            document = KnowledgeDocument(
                source=f"online:{host}",
                topic=topic,
                organization=self._organization_name(
                    url
                ),
                title=title,
                source_reference=url,
                text=cleaned_text,
            )

            chunks = chunk_document(
                document,
                chunk_size=900,
                overlap=120,
            )

            # Limit how much one article can dominate retrieval.
            for chunk in chunks[:2]:

                chunk_text = str(
                    chunk.get("text") or ""
                ).strip()

                if len(chunk_text) < 80:
                    continue

                chunk_hash = self._text_hash(
                    chunk_text
                )

                if chunk_hash in seen_chunk_hashes:
                    continue

                seen_chunk_hashes.add(
                    chunk_hash
                )

                evidence.append(
                    EvidenceChunk(
                        **chunk,
                        score=score,
                        origin="online",
                        retrieved_at=retrieved_at,
                    )
                )

        print(
            f"[Online RAG] Retrieved "
            f"{len(evidence)} cleaned evidence chunks "
            f"from {len(unique_results)} unique trusted sources."
        )

        return evidence