from app.schemas.profile import UserProfile
from app.schemas.narrative import NarrativeSpecification


def build_narrative_spec(profile: UserProfile) -> NarrativeSpecification:
    # Medical knowledge primarily controls medical depth.
    if profile.medical_knowledge == "Advanced":
        technical_terms="high"; detail="high"; causal="clinical"
    elif profile.medical_knowledge == "Intermediate":
        technical_terms="moderate"; detail="moderate"; causal="logical"
    else:
        technical_terms="minimal"; detail="moderate"; causal="simple"

    # Education primarily influences communication complexity, independently of medical knowledge.
    edu=profile.education.lower()
    advanced_education=any(x in edu for x in ["mbbs","md","medical","phd","doctorate","master","engineering","b.tech","btech","graduate","degree"])
    primary_education=any(x in edu for x in ["primary","elementary","school"])
    if advanced_education:
        vocabulary="technical" if profile.medical_knowledge=="Advanced" else "moderate"
        sentence_complexity="high" if profile.medical_knowledge=="Advanced" else "moderate"
    elif primary_education:
        vocabulary="simple"
        sentence_complexity="low"
    else:
        vocabulary="moderate"
        sentence_complexity="moderate"

    # Age modifies accessibility/tone/analogy, not medical knowledge itself.
    if profile.age <= 12:
        vocabulary="very_simple" if profile.medical_knowledge=="Beginner" else vocabulary
        sentence_complexity="low"
        analogy="high"
        tone="friendly_and_reassuring"
        structure=["simple_finding","familiar_analogy","what_it_means","safe_next_step"]
    elif profile.age >= 60:
        analogy="moderate" if profile.medical_knowledge=="Beginner" else "low"
        tone="clear_and_reassuring" if profile.medical_knowledge!="Advanced" else "clinical_and_precise"
        structure=["finding","what_it_means","practical_meaning","possible_context","safe_next_step"]
    else:
        analogy="moderate" if profile.medical_knowledge=="Beginner" else "low"
        tone="informative_and_reassuring" if profile.medical_knowledge!="Advanced" else "clinical_and_precise"
        structure=["finding","what_it_means","why_it_matters","possible_context","safe_next_step"] if profile.medical_knowledge!="Advanced" else ["finding","clinical_interpretation","relevant_relationships","limitations"]

    guidance=[
        "Preserve every report value and unit exactly when mentioned.",
        "Do not claim that an abnormal finding is a confirmed diagnosis.",
        "Do not prescribe medication or specific treatment.",
        "Explain uncertainty and encourage professional interpretation when appropriate.",
    ]
    if profile.age <= 12: guidance.append("Use age-appropriate familiar analogies without sounding frightening or childish.")
    if profile.age >= 60: guidance.append("Prioritize practical meaning and clarity; avoid patronizing language.")
    return NarrativeSpecification(vocabulary_level=vocabulary,sentence_complexity=sentence_complexity,technical_terms=technical_terms,analogy_usage=analogy,detail_level=detail,causal_explanation=causal,tone=tone,structure=structure,guidance=guidance)
