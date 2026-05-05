from acquire.models import ProspectCandidate


def test_prospect_candidate_defaults():
    candidate = ProspectCandidate(name="Lodge", source="manual", region="Bahamas", country="Bahamas")
    assert candidate.raw_data == {}
