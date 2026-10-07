from app.schemas.extraction import MedicalFinding
from app.schemas.interpretation import ClinicalInterpretation
from app.schemas.rag import EvidenceChunk
from app.services.llm.base import LLMProvider

SYSTEM_PROMPT="""You are a medical report interpretation component for an educational system. Interpret all findings together using only the supplied report findings and evidence. Distinguish findings from diagnoses. Never prescribe medication or treatment. Never invent values. Use uncertainty language for associations and patterns. Return a report-level structured interpretation."""

def _finding_text(f: MedicalFinding) -> str:
    parts = [f"- {f.test_name}"]

    if f.value:
        value_text = f.value
        if f.unit:
            value_text += f" {f.unit}"
        parts.append(f"value={value_text}")

    if f.description:
        parts.append(f"description={f.description}")

    parts.append(f"status={f.status}")

    if f.reference_range:
        parts.append(f"reference={f.reference_range}")

    return "; ".join(parts)

def interpret_report(findings: list[MedicalFinding], evidence: list[EvidenceChunk], llm: LLMProvider) -> ClinicalInterpretation:
    #finding_lines="\n".join(f"- {f.test_name}: {f.value} {f.unit or ''}, status={f.status}, reference={f.reference_range or 'not provided'}" for f in findings)
    finding_lines = "\n".join(
        _finding_text(f)
        for f in findings
    )
    evidence_lines="\n".join(f"[{e.source}#{e.chunk_id}] {e.text}" for e in evidence) or "No external evidence retrieved."
    prompt=f"""FINDINGS:\n{finding_lines}\n\nRETRIEVED EVIDENCE:\n{evidence_lines}\n\nInterpret the report as a whole. Do not issue a definitive diagnosis."""
    return llm.generate_structured(SYSTEM_PROMPT,prompt,ClinicalInterpretation)
