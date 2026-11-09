"""Additive tables in CricPredict's existing SQLAlchemy database."""
from app import db


class FieldingPerson(db.Model):
    __tablename__ = "fielding_person"
    id = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.Text, nullable=False)
    # Existing identities are linked only by provider IDs, never name guesses.
    discovered_player_id = db.Column(db.Integer, db.ForeignKey("discovered_player.id"))


class FieldingIdentifier(db.Model):
    __tablename__ = "fielding_identifier"
    source = db.Column(db.String(40), primary_key=True)
    external_id = db.Column(db.String(100), primary_key=True)
    person_id = db.Column(db.String(80), db.ForeignKey("fielding_person.id"), nullable=False, index=True)


class FieldingAlias(db.Model):
    __tablename__ = "fielding_alias"
    person_id = db.Column(db.String(80), db.ForeignKey("fielding_person.id"), primary_key=True)
    name = db.Column(db.Text, primary_key=True)
    normalized_name = db.Column(db.Text, nullable=False, index=True)


class FieldingMatch(db.Model):
    __tablename__ = "fielding_match"
    id = db.Column(db.String(100), primary_key=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    # First creation date supplied by the source, not a claim of revision availability.
    source_created = db.Column(db.Date, nullable=False)
    match_format = db.Column(db.String(20), nullable=False, index=True)
    gender = db.Column(db.String(20), nullable=False, index=True)
    competition = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(40), nullable=False)
    source_sha256 = db.Column(db.String(64), nullable=False)
    revision = db.Column(db.Integer, nullable=False)
    # Aggregate observed dismissal involvements and fielding exposure, not opportunities.
    facts = db.Column(db.JSON, nullable=False)


class FieldingTrial(db.Model):
    """Licensed, explicitly labelled events, including non-opportunity deliveries.

    No Cricsheet catch is automatically converted into a complete opportunity
    trial: failed chances are absent from that source.
    """
    __tablename__ = "fielding_trial"
    source = db.Column(db.String(40), primary_key=True)
    event_id = db.Column(db.String(160), primary_key=True)
    kind = db.Column(db.String(20), primary_key=True)
    match_id = db.Column(db.String(100), nullable=False, index=True)
    event_date = db.Column(db.Date, nullable=False, index=True)
    available_date = db.Column(db.Date, nullable=False)
    match_format = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    person_id = db.Column(db.String(80), db.ForeignKey("fielding_person.id"), index=True)
    opportunity = db.Column(db.Boolean, nullable=True)
    success = db.Column(db.Boolean, nullable=True)
    direct_hit = db.Column(db.Boolean, nullable=True)
    runs_saved = db.Column(db.Float, nullable=True)
    # Position, difficulty, shot/batter/bowler identifiers, if supplied by provider.
    context = db.Column(db.JSON, nullable=False)
    provenance = db.Column(db.Text, nullable=False)
    exhaustive_delivery_coverage = db.Column(db.Boolean, nullable=False, default=False)
    __table_args__ = (
        db.CheckConstraint("kind IN ('catch', 'run_out', 'ground')", name="fielding_trial_kind"),
        db.CheckConstraint("success IS NULL OR opportunity IS TRUE", name="fielding_trial_success_opportunity"),
        db.CheckConstraint("direct_hit IS NULL OR kind = 'run_out'", name="fielding_trial_direct_hit"),
    )


class FieldingCache(db.Model):
    __tablename__ = "fielding_cache"
    cache_key = db.Column(db.String(180), primary_key=True)
    source_digest = db.Column(db.String(64), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
