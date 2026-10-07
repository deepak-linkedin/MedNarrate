from app.schemas.profile import UserProfile
from app.services.mednarrate_pipeline import process_report

def test_mock_pipeline(monkeypatch,tmp_path):
    # Avoid sentence-transformer download in unit tests by replacing retrieval.
    from app.services import mednarrate_pipeline as mp
    monkeypatch.setattr(mp,"_retrieve_evidence",lambda findings, db=None: [])
    report=b"Hemoglobin: 8.2 g/dL Reference Range: 12-16 g/dL\nWBC: 7.0 x10^3/uL Reference Range: 4-11 x10^3/uL"
    result=process_report("sample.txt",report,UserProfile(full_name="Test User",age=25,education="Engineering",medical_knowledge="Beginner"),user_id="test-user",db=None,debug=True)
    assert result.findings
    assert result.narrative.title
    assert result.safety.passed
