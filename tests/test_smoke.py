"""Smoke test — does the package import?"""

def test_import_consent_engine():
    import consent_engine
    assert consent_engine.__version__
