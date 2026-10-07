from app.schemas.extraction import MedicalFinding
from app.schemas.narrative_output import NarrativeOutput
from app.services.safety_service import validate_narrative

def test_preserves_mentioned_value_and_unit():
    f=[MedicalFinding(test_name="Hemoglobin",value="8.2",unit="g/dL",status="low")]
    n=NarrativeOutput(title="Report",explanation="Hemoglobin is 8.2 g/dL and is low.",key_points=[],important_note="Educational only; speak with a qualified healthcare professional.")
    assert validate_narrative(f,n).passed
