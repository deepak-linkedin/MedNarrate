import uuid
from urllib.parse import urlparse, urlunparse

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.api import (
    AnalyzeResponse,
    ReportSummary,
    MedicalSource,
)
from app.schemas.profile import UserProfile
from app.services.document_service import extract_text
from app.services.medical_extraction_service import extract_medical_findings
from app.services.clinical_interpretation_service import interpret_report
from app.services.narrative_engine import build_narrative_spec
from app.services.narrative_realization_service import realize_narrative
from app.services.safety_service import validate_narrative
from app.services.llm import get_llm_provider


def _retrieve_evidence(findings, db=None):
    from app.rag.retriever import Retriever

    return Retriever(db=db).retrieve_report(findings)


def _normalize_source_url(url: str) -> str:
    """
    Normalize source URLs so multiple chunks from the same webpage
    are shown as one user-facing medical source.
    """

    if not url:
        return ""

    try:
        parsed = urlparse(url)

        normalized = parsed._replace(
            query="",
            fragment="",
        )

        return urlunparse(normalized).rstrip("/")

    except Exception:
        return url.split("#")[0].split("?")[0].rstrip("/")


def _friendly_organization(
    organization: str | None,
    url: str,
) -> str:
    """
    Convert raw domains such as ncbi.nlm.nih.gov into cleaner
    patient-facing organization names.
    """

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

    return organization or host or "Trusted medical source"


def _build_user_sources(
    evidence,
    limit: int = 5,
) -> list[MedicalSource]:
    """
    Convert internal RAG chunks into user-facing source references.

    Several pgvector chunks may belong to the same document. The
    patient should see the document once, not every retrieved chunk.
    """

    sources: list[MedicalSource] = []

    seen_urls: set[str] = set()
    seen_local_sources: set[str] = set()

    for item in evidence:

        source_reference = (
            getattr(item, "source_reference", None)
            or ""
        ).strip()

        title = (
            getattr(item, "title", None)
            or "Medical reference"
        )

        organization = getattr(
            item,
            "organization",
            None,
        )

        topic = getattr(
            item,
            "topic",
            None,
        )

        origin = (
            getattr(item, "origin", None)
            or "local"
        )

        source_name = (
            getattr(item, "source", None)
            or "Medical knowledge base"
        )

        # -----------------------------------------------------
        # ONLINE SOURCE
        # -----------------------------------------------------

        if source_reference.startswith(
            ("http://", "https://")
        ):
            normalized_url = _normalize_source_url(
                source_reference
            )

            if not normalized_url:
                continue

            if normalized_url in seen_urls:
                continue

            seen_urls.add(normalized_url)

            sources.append(
                MedicalSource(
                    title=title,
                    organization=_friendly_organization(
                        organization,
                        normalized_url,
                    ),
                    topic=topic,
                    url=normalized_url,
                    origin=origin,
                )
            )

        # -----------------------------------------------------
        # LOCAL CURATED SOURCE
        # -----------------------------------------------------

        else:
            # Local KB sources may not have public URLs.
            # Deduplicate using source/title combination.

            local_key = (
                f"{source_name}|{title}"
            ).lower()

            if local_key in seen_local_sources:
                continue

            seen_local_sources.add(local_key)

            sources.append(
                MedicalSource(
                    title=title,
                    organization=(
                        organization
                        or "MedNarrate curated knowledge base"
                    ),
                    topic=topic,
                    url=None,
                    origin=origin,
                )
            )

        if len(sources) >= limit:
            break

    return sources


def _questions(findings, interpretation):
    """
    Generate useful questions the user may discuss with a clinician.
    """

    abnormal = [
        f.test_name
        for f in findings
        if f.status
        in {
            "low",
            "high",
            "abnormal",
            "diagnostic",
        }
    ]

    questions = []

    if abnormal:
        questions.append(
            "What could explain the findings involving "
            f"{', '.join(abnormal[:3])} in my situation?"
        )

        questions.append(
            "Should these findings be compared with my previous "
            "reports or reassessed later?"
        )

    if interpretation.relationships:
        questions.append(
            "Are the related findings in this report clinically "
            "meaningful when considered together?"
        )

    questions.append(
        "Do my symptoms, medical history, or other tests change "
        "how these results should be interpreted?"
    )

    return questions[:4]


def process_report(
    filename: str,
    content: bytes,
    profile: UserProfile,
    user_id: str,
    db: Session | None = None,
    debug: bool = False,
) -> AnalyzeResponse:

    settings = get_settings()

    llm = get_llm_provider()

    # ---------------------------------------------------------
    # 1. DOCUMENT EXTRACTION
    # ---------------------------------------------------------

    report_text = extract_text(
        filename,
        content,
    )

    # Keep this during development.
    # Remove or disable before production because medical reports
    # can contain sensitive patient information.
    if debug:
        print(
            "\n========== EXTRACTED REPORT TEXT =========="
        )
        print(report_text)
        print(
            "===========================================\n"
        )

    # ---------------------------------------------------------
    # 2. STRUCTURED MEDICAL FINDING EXTRACTION
    # ---------------------------------------------------------

    findings = extract_medical_findings(
        report_text,
        llm,
    )

    # ---------------------------------------------------------
    # 3. HYBRID RAG
    # ---------------------------------------------------------

    evidence = _retrieve_evidence(
        findings,
        db,
    )

    # Evidence contains individual pgvector chunks.
    # This remains internal.
    #
    # sources contains deduplicated user-facing references.
    user_sources = _build_user_sources(
        evidence,
        limit=5,
    )

    # ---------------------------------------------------------
    # 4. REPORT-LEVEL CLINICAL INTERPRETATION
    # ---------------------------------------------------------

    interpretation = interpret_report(
        findings,
        evidence,
        llm,
    )

    # ---------------------------------------------------------
    # 5. NARRATIVE ENGINEERING
    # ---------------------------------------------------------

    spec = build_narrative_spec(
        profile
    )

    # ---------------------------------------------------------
    # 6. NARRATIVE REALIZATION
    # ---------------------------------------------------------

    narrative = realize_narrative(
        profile,
        spec,
        findings,
        interpretation,
        evidence,
        llm,
    )

    # ---------------------------------------------------------
    # 7. SAFETY / FIDELITY VALIDATION
    # ---------------------------------------------------------

    safety = validate_narrative(
        findings,
        narrative,
    )

    if not safety.passed:
        raise ValueError(
            "Generated narrative failed safety/fidelity "
            "validation: "
            + "; ".join(safety.issues)
        )

    # ---------------------------------------------------------
    # 8. DATABASE PERSISTENCE
    # ---------------------------------------------------------

    session_id = str(
        uuid.uuid4()
    )

    if (
        db is not None
        and settings.persist_results
    ):
        from app.services.persistence_service import (
            persist_result,
        )

        # Persist full RAG evidence, not only the reduced
        # user-facing source list.
        session_id = persist_result(
            db,
            user_id,
            filename,
            profile,
            findings,
            interpretation,
            spec,
            narrative,
            safety,
            evidence,
        )

    # ---------------------------------------------------------
    # 9. REPORT SUMMARY
    # ---------------------------------------------------------

    abnormal = [
        f
        for f in findings
        if f.status
        in {
            "low",
            "high",
            "abnormal",
            "diagnostic",
        }
    ]

    normal = [
        f
        for f in findings
        if f.status == "normal"
    ]

    unknown = [
        f
        for f in findings
        if f.status == "unknown"
    ]

    # Prefer clinically important findings.
    # If none are abnormal, show the first five.
    important = (
        abnormal
        if abnormal
        else findings[:5]
    )

    summary = ReportSummary(
        total_findings=len(findings),
        abnormal_findings=len(abnormal),
        normal_findings=len(normal),
        unknown_findings=len(unknown),
    )

    # ---------------------------------------------------------
    # 10. POSSIBLE ASSOCIATIONS
    # ---------------------------------------------------------

    associations: list[str] = []

    for item in interpretation.finding_interpretations:

        for association in item.possible_associations:

            if association not in associations:
                associations.append(
                    association
                )

    # ---------------------------------------------------------
    # 11. FINAL RESPONSE
    # ---------------------------------------------------------

    return AnalyzeResponse(
        session_id=session_id,
        profile=profile,
        summary=summary,
        narrative=narrative,
        important_findings=important,
        relationships=interpretation.relationships,
        possible_patterns=interpretation.possible_patterns,
        possible_associations=associations[:8],
        limitations=interpretation.limitations,
        questions_for_clinician=_questions(
            findings,
            interpretation,
        ),

        # IMPORTANT:
        # Do not expose all evidence chunks here.
        sources=user_sources,

        safety=safety,

        # Detailed internal information is available only
        # during development/debug mode.
        findings=(
            findings
            if debug
            else None
        ),

        interpretation=(
            interpretation
            if debug
            else None
        ),

        narrative_specification=spec,
    )