from app.service import SERVICE_VERSION


def test_adaptive_atomic_release_version():
    assert SERVICE_VERSION == "1.7.1"
