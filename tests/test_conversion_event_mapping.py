"""Analytics mappings must not prevent the application from starting."""

import json

from app import app, db
from models import ConversionEvent
from sqlalchemy.orm import configure_mappers


def test_mapping_retains_database_column_without_reserved_attribute():
    configure_mappers()
    assert ConversionEvent.event_metadata.property.columns[0].name == "metadata"
    assert ConversionEvent.metadata is db.Model.metadata


def test_event_writer_uses_mapped_attribute(monkeypatch):
    import routes

    saved = []
    commits = []
    monkeypatch.setattr(db.session, "add", saved.append)
    monkeypatch.setattr(db.session, "commit", lambda: commits.append(True))

    def unexpected_rollback():
        raise AssertionError("Event construction or write failed")

    monkeypatch.setattr(db.session, "rollback", unexpected_rollback)
    with app.test_request_context("/"):
        routes._track_event("upgrade_clicked", {"source": "/pricing"})
    assert commits == [True]
    assert len(saved) == 1
    assert json.loads(saved[0].event_metadata) == {"source": "/pricing"}
