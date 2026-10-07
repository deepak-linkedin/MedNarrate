from app.schemas.profile import UserProfile
from app.services.narrative_engine import build_narrative_spec

def test_child_beginner_is_simple():
    spec=build_narrative_spec(UserProfile(age=8,education="Primary School",medical_knowledge="Beginner"))
    assert spec.vocabulary_level=="very_simple"
    assert spec.analogy_usage=="high"

def test_medical_knowledge_is_separate_from_education():
    spec=build_narrative_spec(UserProfile(age=65,education="Primary School",medical_knowledge="Advanced"))
    assert spec.technical_terms=="high"
    assert spec.detail_level=="high"
