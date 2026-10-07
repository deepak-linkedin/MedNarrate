import re
from typing import TypeVar
from pydantic import BaseModel
from app.services.llm.base import LLMProvider
from app.schemas.extraction import MedicalFinding, MedicalFindingsResponse
from app.schemas.interpretation import ClinicalInterpretation, FindingInterpretation
from app.schemas.narrative_output import NarrativeOutput

T = TypeVar("T", bound=BaseModel)


class MockProvider(LLMProvider):
    """Deterministic development provider. No network or API key required."""

    FINDING_RE = re.compile(
        r"(?P<name>[A-Za-z][A-Za-z0-9 %()/_-]{1,50}?)\s*[:=]\s*"
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z/%µμ0-9^.-]+(?:/[A-Za-z0-9^.-]+)?)?",
        re.IGNORECASE,
    )

    def generate_structured(self, system_prompt: str, user_prompt: str, response_model: type[T]) -> T:
        if response_model is MedicalFindingsResponse:
            return self._extract(user_prompt)  # type: ignore[return-value]
        if response_model is ClinicalInterpretation:
            return self._interpret(user_prompt)  # type: ignore[return-value]
        if response_model is NarrativeOutput:
            return self._narrate(user_prompt)  # type: ignore[return-value]
        raise ValueError(f"MockProvider does not support {response_model.__name__}")

    def _extract(self, prompt: str) -> MedicalFindingsResponse:
        text = prompt.split("REPORT TEXT:", 1)[-1]
        findings = []
        for match in self.FINDING_RE.finditer(text):
            name = match.group("name").strip(" -\n\t")
            value = match.group("value")
            unit = match.group("unit")
            nearby = text[match.end(): match.end()+140]
            ref_match = re.search(r"(?:reference(?: range)?|ref(?: range)?)\s*[:=]?\s*([0-9.]+)\s*[-–to]+\s*([0-9.]+)\s*([A-Za-z/%µμ0-9^.-]+)?", nearby, re.I)
            ref = None
            status = "unknown"
            if ref_match:
                lo, hi = float(ref_match.group(1)), float(ref_match.group(2))
                ref_unit = ref_match.group(3)
                ref = f"{ref_match.group(1)}-{ref_match.group(2)}" + (f" {ref_unit}" if ref_unit else "")
                num = float(value)
                status = "low" if num < lo else "high" if num > hi else "normal"
            findings.append(MedicalFinding(test_name=name, value=value, unit=unit, reference_range=ref, status=status))
        # common fallback for simple lab-line formats
        if not findings:
            raise ValueError("Mock extraction could not identify numeric lab findings. Try the supplied sample report or use Gemini mode.")
        # de-duplicate by name/value
        seen=set(); unique=[]
        for f in findings:
            key=(f.test_name.lower(),f.value,f.unit)
            if key not in seen:
                seen.add(key); unique.append(f)
        return MedicalFindingsResponse(findings=unique[:30])

    def _interpret(self, prompt: str) -> ClinicalInterpretation:
        lines = [ln.strip() for ln in prompt.splitlines() if ln.strip().startswith("-")]
        interpretations=[]
        abnormal=[]
        for line in lines:
            m=re.match(r"-\s*(.*?):\s*([^,]+),\s*status=([a-z]+)", line, re.I)
            if not m: continue
            name,value,status=m.group(1),m.group(2),m.group(3).lower()
            meaning = f"{name} is {status} relative to the report's supplied reference information." if status in {"low","high","abnormal"} else f"{name} is recorded as {status}."
            significance = f"This result should be interpreted together with symptoms, history, and the other report findings; the value recorded is {value}."
            interpretations.append(FindingInterpretation(test_name=name, meaning=meaning, significance=significance, possible_associations=[], uncertainty="This result alone does not establish a diagnosis."))
            if status in {"low","high","abnormal"}: abnormal.append(name)
        overall = "The report contains " + (f"abnormal or out-of-range findings involving {', '.join(abnormal)}." if abnormal else "no findings clearly marked as out of range by the extracted data.")
        rel=[]
        lowered={x.lower() for x in abnormal}
        if "hemoglobin" in lowered and ("rbc" in lowered or "red blood cell count" in lowered):
            rel.append("Low hemoglobin together with a low red-cell measure may be clinically related, but the pattern requires professional interpretation in context.")
        return ClinicalInterpretation(overall_summary=overall, finding_interpretations=interpretations, relationships=rel, possible_patterns=[], limitations=["Automated interpretation is educational and cannot confirm a diagnosis.", "Reference ranges can vary by laboratory, age, sex, pregnancy status, and clinical context."])

    def _narrate(self, prompt: str) -> NarrativeOutput:
        def field(name, default=""):
            m=re.search(rf"{re.escape(name)}:\s*(.+)",prompt,re.I)
            return m.group(1).strip() if m else default
        age=int(re.search(r"AGE:\s*(\d+)",prompt,re.I).group(1)) if re.search(r"AGE:\s*(\d+)",prompt,re.I) else 30
        knowledge=field("MEDICAL KNOWLEDGE","Beginner")
        vocab=field("VOCABULARY","moderate")
        facts=[]
        in_facts=False
        for ln in prompt.splitlines():
            if ln.strip()=="FACTS:": in_facts=True; continue
            if in_facts and ln.startswith("-"): facts.append(ln[1:].strip())
            elif in_facts and ln and not ln.startswith("-"): break
        if age <= 12:
            intro="This report is a set of clues about how your body is working. I’ll explain the main numbers in simple words."
            analogy="Think of some blood components as helpers with different jobs in the body."
        elif knowledge.lower()=="advanced":
            intro="This report shows several laboratory measurements that should be interpreted against the supplied reference intervals and the broader clinical context."
            analogy=""
        else:
            intro="This report contains laboratory measurements that can help describe what is happening in your body."
            analogy=""
        fact_text=" ".join(facts[:5]) if facts else "The extracted findings should be reviewed together rather than used as a stand-alone diagnosis."
        explanation=f"{intro} {analogy} {fact_text}".strip()
        if vocab in {"very_simple","simple"}:
            explanation=explanation.replace("laboratory measurements","test results").replace("clinical context","health information")
        return NarrativeOutput(title="Your Medical Report, Explained", explanation=explanation, key_points=facts[:5] or ["Review the complete report with a qualified healthcare professional."], important_note="This explanation is for education only. It does not diagnose a condition or replace advice from a qualified healthcare professional.")
