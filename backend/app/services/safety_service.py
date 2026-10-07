# import re
# from app.schemas.extraction import MedicalFinding
# from app.schemas.narrative_output import NarrativeOutput
# from app.schemas.safety import SafetyValidation

# DIAGNOSIS_PATTERNS=[r"you have [a-z]",r"you are diagnosed",r"this confirms",r"definitively indicates"]
# TREATMENT_PATTERNS=[r"take \d+",r"start (?:taking|using)",r"stop (?:taking|using)",r"prescribe",r"dosage",r"mg (?:daily|twice)"]


# def validate_narrative(findings: list[MedicalFinding], narrative: NarrativeOutput) -> SafetyValidation:
#     text=" ".join([narrative.title,narrative.explanation,*narrative.key_points,narrative.important_note]).lower()
#     issues=[]
#     mentioned=[f for f in findings if f.test_name.lower() in text]
#     values_to_check = [
#         f for f in mentioned
#         if f.value
#     ]

#     preserved_values = all(
#         f.value.lower() in text
#         for f in values_to_check
#     )
#     #preserved_values=all(f.value.lower() in text for f in mentioned)
#     units_to_check=[f for f in mentioned if f.unit]
#     preserved_units=all(f.unit.lower() in text for f in units_to_check)
#     if not preserved_values: issues.append("At least one mentioned finding does not preserve its original numeric value.")
#     if not preserved_units: issues.append("At least one mentioned finding does not preserve its original unit.")
#     diagnosis=any(re.search(p,text) for p in DIAGNOSIS_PATTERNS)
#     treatment=any(re.search(p,text) for p in TREATMENT_PATTERNS)
#     if diagnosis: issues.append("Potential unsupported definitive diagnosis language detected.")
#     if treatment: issues.append("Potential prescription/treatment language detected.")
#     passed=preserved_values and preserved_units and not diagnosis and not treatment
#     return SafetyValidation(passed=passed,preserved_values=preserved_values,preserved_units=preserved_units,unsupported_diagnosis_detected=diagnosis,treatment_language_detected=treatment,issues=issues)

import re

from app.schemas.extraction import MedicalFinding
from app.schemas.narrative_output import NarrativeOutput
from app.schemas.safety import SafetyValidation


# Strong wording that can imply the system itself is making a diagnosis.
DIAGNOSIS_PATTERNS = [
    r"\byou have\s+([^.!?\n]+)",
    r"\byou are diagnosed with\s+([^.!?\n]+)",
    r"\bthis confirms\s+([^.!?\n]+)",
    r"\bthis proves\s+([^.!?\n]+)",
    r"\bdefinitively indicates\s+([^.!?\n]+)",
    r"\bdefinitely indicates\s+([^.!?\n]+)",
]


# Detect direct treatment/prescription instructions from MedNarrate.
# We intentionally do NOT flag neutral sentences such as:
# "The report states that your doctor prescribed a beta-blocker."
TREATMENT_PATTERNS = [
    r"\byou should take\b",
    r"\byou should start\b",
    r"\byou should stop\b",
    r"\bstart taking\b",
    r"\bstop taking\b",
    r"\btake \d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b",
    r"\buse \d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b",
    r"\b(?:once|twice|three times) daily\b",
    r"\bwe recommend starting\b",
    r"\bi recommend starting\b",
    r"\byour dosage should be\b",
]


# These phrases are appropriate because they attribute the diagnosis
# to the uploaded source report rather than MedNarrate itself.
ATTRIBUTION_PATTERNS = [
    r"\bthe report states\b",
    r"\bthe report says\b",
    r"\bthe report notes\b",
    r"\bthe report describes\b",
    r"\bthe report suggests\b",
    r"\bthe findings suggest\b",
    r"\baccording to the report\b",
    r"\bthe clinician documented\b",
    r"\bthe physician documented\b",
    r"\bwas diagnosed\b",
    r"\bdiagnosis documented\b",
    r"\bconsistent with\b",
]


def _build_narrative_text(narrative: NarrativeOutput) -> str:
    """
    Combine all user-visible narrative fields into one normalized string.
    Handles optional fields safely.
    """

    parts = [
        narrative.title or "",
        narrative.explanation or "",
        *(narrative.key_points or []),
        narrative.important_note or "",
    ]

    return " ".join(parts).lower()


def _supported_diagnosis_text(findings: list[MedicalFinding]) -> str:
    """
    Build text containing diagnoses explicitly extracted from the source report.

    Uses getattr so this remains safe even while older stored records exist.
    """

    supported_parts: list[str] = []

    for finding in findings:
        finding_type = getattr(finding, "finding_type", "other")

        if finding_type == "diagnosis":
            supported_parts.append(finding.test_name or "")

            description = getattr(finding, "description", None)
            if description:
                supported_parts.append(description)

    return " ".join(supported_parts).lower()


def _contains_attribution(text: str, match_start: int) -> bool:
    """
    Check whether suspicious diagnostic wording is preceded by language
    attributing it to the source report.

    We inspect a limited amount of text before the match.
    """

    context_start = max(0, match_start - 160)
    preceding_text = text[context_start:match_start]

    return any(
        re.search(pattern, preceding_text)
        for pattern in ATTRIBUTION_PATTERNS
    )


def _diagnosis_is_supported(
    diagnosis_text: str,
    supported_diagnoses: str,
) -> bool:
    """
    Check whether diagnosis wording roughly corresponds to a diagnosis
    explicitly extracted from the uploaded report.

    This is intentionally conservative rather than attempting clinical
    synonym inference here.
    """

    diagnosis_text = diagnosis_text.strip().lower()

    if not diagnosis_text or not supported_diagnoses:
        return False

    # Direct containment.
    if diagnosis_text in supported_diagnoses:
        return True

    # Reverse containment can help with phrases such as:
    # "stable angina" vs "stable angina pectoris"
    if supported_diagnoses in diagnosis_text:
        return True

    # Token-overlap fallback.
    diagnosis_tokens = {
        token
        for token in re.findall(r"[a-zA-Z]+", diagnosis_text)
        if len(token) > 3
    }

    source_tokens = {
        token
        for token in re.findall(r"[a-zA-Z]+", supported_diagnoses)
        if len(token) > 3
    }

    if not diagnosis_tokens or not source_tokens:
        return False

    overlap = diagnosis_tokens & source_tokens

    # Require meaningful overlap rather than one coincidental word.
    return len(overlap) >= min(2, len(diagnosis_tokens))


def _detect_unsupported_diagnosis(
    text: str,
    findings: list[MedicalFinding],
) -> bool:
    """
    Return True only when MedNarrate appears to make a strong diagnosis
    that is not supported or properly attributed to the uploaded report.
    """

    supported_diagnoses = _supported_diagnosis_text(findings)

    for pattern in DIAGNOSIS_PATTERNS:
        for match in re.finditer(pattern, text):
            diagnosis_text = (
                match.group(1)
                if match.lastindex
                else match.group(0)
            )

            # Example:
            # "According to the report, you have..."
            #
            # This is clearly attributed to source material.
            if _contains_attribution(text, match.start()):
                continue

            # If the actual diagnosis was explicitly extracted from the
            # source report, do not treat the mention as invented.
            if _diagnosis_is_supported(
                diagnosis_text,
                supported_diagnoses,
            ):
                continue

            return True

    return False


def _detect_treatment_language(text: str) -> bool:
    """
    Detect direct treatment instructions generated by MedNarrate.

    Mentions of treatments already documented in the source report should
    ideally be phrased as:
      "The report states..."
      "Your clinician recommended..."
    """

    for pattern in TREATMENT_PATTERNS:
        for match in re.finditer(pattern, text):

            # Allow an attributed statement about an existing treatment plan.
            if _contains_attribution(text, match.start()):
                continue

            return True

    return False


def validate_narrative(
    findings: list[MedicalFinding],
    narrative: NarrativeOutput,
) -> SafetyValidation:

    text = _build_narrative_text(narrative)

    issues: list[str] = []

    # Only check value/unit preservation for findings actually mentioned
    # in the generated explanation.
    mentioned = [
        finding
        for finding in findings
        if finding.test_name
        and finding.test_name.lower() in text
    ]

    values_to_check = [
        finding
        for finding in mentioned
        if getattr(finding, "value", None)
    ]

    preserved_values = all(
        str(finding.value).lower() in text
        for finding in values_to_check
    )

    units_to_check = [
        finding
        for finding in mentioned
        if getattr(finding, "unit", None)
    ]

    preserved_units = all(
        str(finding.unit).lower() in text
        for finding in units_to_check
    )

    if not preserved_values:
        issues.append(
            "At least one mentioned finding does not preserve "
            "its original numeric value."
        )

    if not preserved_units:
        issues.append(
            "At least one mentioned finding does not preserve "
            "its original unit."
        )

    unsupported_diagnosis = _detect_unsupported_diagnosis(
        text,
        findings,
    )

    treatment_language = _detect_treatment_language(text)

    if unsupported_diagnosis:
        issues.append(
            "Potential unsupported definitive diagnosis language detected."
        )

    if treatment_language:
        issues.append(
            "Potential prescription/treatment language detected."
        )

    passed = (
        preserved_values
        and preserved_units
        and not unsupported_diagnosis
        and not treatment_language
    )

    return SafetyValidation(
        passed=passed,
        preserved_values=preserved_values,
        preserved_units=preserved_units,
        unsupported_diagnosis_detected=unsupported_diagnosis,
        treatment_language_detected=treatment_language,
        issues=issues,
    )