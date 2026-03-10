import pytest
from app import app
import routes  # noqa: F401


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def app_context():
    with app.app_context():
        yield app
