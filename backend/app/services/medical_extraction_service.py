from app.schemas.extraction import MedicalFinding, MedicalFindingsResponse
from app.services.llm.base import LLMProvider

#SYSTEM_PROMPT = """You extract structured medical report findings. Do not explain, diagnose, prescribe, or invent values. Preserve the report's values, units, and reference ranges exactly when present. If status is not explicit, infer low/normal/high only when the report gives a clear numeric reference range; otherwise use unknown."""

SYSTEM_PROMPT = """
You extract structured findings from medical reports.

Extract clinically meaningful findings explicitly present in the report.

These may include:
- laboratory test results
- ECG findings
- imaging findings
- stress-test findings
- pathology findings
- stated diagnoses
- clinically important observations

For laboratory findings:
- preserve value
- unit
- reference range
- status when available

For narrative findings:
- place the clinically meaningful text in description
- do not invent a numeric value
- do not invent units
- do not invent reference ranges

If the report explicitly states a diagnosis, it may be extracted as
finding_type="diagnosis". Do not create new diagnoses that are not
stated in the source report.

Never:
- invent findings
- change numerical values
- prescribe treatment
- infer unsupported diagnoses
"""


def extract_medical_findings(
    report_text: str,
    llm: LLMProvider,
) -> list[MedicalFinding]:

    user_prompt = f"""
Extract all clinically meaningful findings from this medical report.

Do not limit extraction to numeric laboratory results.

REPORT TEXT:
{report_text}
"""

    result = llm.generate_structured(
        SYSTEM_PROMPT,
        user_prompt,
        MedicalFindingsResponse,
    )

    if not result.findings:
        raise ValueError(
            "No structured medical findings could be extracted from this report."
        )

    return result.findings