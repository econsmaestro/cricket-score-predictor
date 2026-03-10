from app import db
from datetime import datetime
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint


class User(UserMixin, db.Model):
    """User model for Replit Auth"""
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def display_name(self):
        """Return the best available display name: first name, email prefix, or truncated ID."""
        if self.first_name:
            return self.first_name
        if self.email:
            return self.email.split('@')[0]
        return f"User {self.id[:8]}"


class OAuth(OAuthConsumerMixin, db.Model):
    """OAuth tokens for Replit Auth"""
    __tablename__ = 'flask_dance_oauth'
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)
    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)


class Prediction(db.Model):
    """Stores a single score prediction made by the engine for historical tracking."""
    id = db.Column(db.Integer, primary_key=True)
    venue = db.Column(db.String(100), nullable=False)
    current_score = db.Column(db.Integer, nullable=False)
    wickets_fallen = db.Column(db.Integer, nullable=False)
    overs_remaining = db.Column(db.Float, nullable=False)
    predicted_final_score = db.Column(db.Integer, nullable=False)
    predicted_wickets = db.Column(db.Integer, nullable=False)
    predicted_next_over_runs = db.Column(db.Integer, nullable=False)
    next_over_bowler = db.Column(db.String(100), nullable=False)
    actual_final_score = db.Column(db.Integer, nullable=True)
    actual_wickets = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Player(db.Model):
    """Cricket player profile with career batting and bowling statistics."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    team = db.Column(db.String(100), nullable=True)
    is_batsman = db.Column(db.Boolean, default=True)
    is_bowler = db.Column(db.Boolean, default=False)
    batting_style = db.Column(db.String(50), nullable=True)
    bowling_style = db.Column(db.String(50), nullable=True)
    
    career_runs = db.Column(db.Integer, default=0)
    career_balls_faced = db.Column(db.Integer, default=0)
    career_wickets = db.Column(db.Integer, default=0)
    career_overs_bowled = db.Column(db.Float, default=0)
    career_runs_conceded = db.Column(db.Integer, default=0)
    career_matches = db.Column(db.Integer, default=0)
    career_fifties = db.Column(db.Integer, default=0)
    career_hundreds = db.Column(db.Integer, default=0)
    
    @property
    def career_strike_rate(self):
        """Calculate batting strike rate as (runs / balls faced) * 100."""
        if self.career_balls_faced == 0:
            return 0.0
        return (self.career_runs / self.career_balls_faced) * 100
    
    @property
    def career_average(self):
        """Calculate career batting average as runs per match."""
        if self.career_matches == 0:
            return 0.0
        return self.career_runs / self.career_matches
    
    @property
    def career_economy(self):
        """Calculate bowling economy rate as runs conceded per over."""
        if self.career_overs_bowled == 0:
            return 0.0
        return self.career_runs_conceded / self.career_overs_bowled
    
    @property
    def career_bowling_average(self):
        """Calculate bowling average as runs conceded per wicket taken."""
        if self.career_wickets == 0:
            return 0.0
        return self.career_runs_conceded / self.career_wickets

class HistoricalMatch(db.Model):
    """Record of a completed cricket match with team scores and result."""
    id = db.Column(db.Integer, primary_key=True)
    match_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(100), nullable=False)
    team1 = db.Column(db.String(100), nullable=False)
    team2 = db.Column(db.String(100), nullable=False)
    team1_score = db.Column(db.Integer, nullable=False)
    team1_wickets = db.Column(db.Integer, nullable=False)
    team1_overs = db.Column(db.Float, nullable=False)
    team2_score = db.Column(db.Integer, nullable=True)
    team2_wickets = db.Column(db.Integer, nullable=True)
    team2_overs = db.Column(db.Float, nullable=True)
    winner = db.Column(db.String(100), nullable=True)
    season = db.Column(db.Integer, nullable=False)
    
    performances = db.relationship('MatchPerformance', backref='match', lazy=True)

class MatchPerformance(db.Model):
    """Individual player performance (batting and bowling) in a historical match."""
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('historical_match.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    team = db.Column(db.String(100), nullable=False)
    
    runs_scored = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    
    overs_bowled = db.Column(db.Float, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
    wickets_taken = db.Column(db.Integer, default=0)
    maidens = db.Column(db.Integer, default=0)
    
    player = db.relationship('Player', backref='performances')
    
    @property
    def strike_rate(self):
        """Calculate batting strike rate for this match performance."""
        if self.balls_faced == 0:
            return 0.0
        return (self.runs_scored / self.balls_faced) * 100
    
    @property
    def economy(self):
        """Calculate bowling economy rate for this match performance."""
        if self.overs_bowled == 0:
            return 0.0
        return self.runs_conceded / self.overs_bowled

class VenueStats(db.Model):
    """Aggregated scoring and conditions statistics for a cricket venue."""
    id = db.Column(db.Integer, primary_key=True)
    venue = db.Column(db.String(100), nullable=False, unique=True)
    matches_played = db.Column(db.Integer, default=0)
    total_first_innings_runs = db.Column(db.Integer, default=0)
    total_second_innings_runs = db.Column(db.Integer, default=0)
    avg_first_innings_score = db.Column(db.Float, default=160)
    avg_second_innings_score = db.Column(db.Float, default=155)
    avg_wickets_per_innings = db.Column(db.Float, default=6.5)
    boundary_percentage = db.Column(db.Float, default=0.15)
    chasing_win_percentage = db.Column(db.Float, default=0.48)

class DiscoveredPlayer(db.Model):
    """Cache for players discovered from ESPNcricinfo"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    espn_id = db.Column(db.String(20), nullable=False, unique=True)
    country = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(50), nullable=True)
    batting_style = db.Column(db.String(50), nullable=True)
    bowling_style = db.Column(db.String(50), nullable=True)
    t20_matches = db.Column(db.Integer, default=0)
    t20_runs = db.Column(db.Integer, default=0)
    t20_wickets = db.Column(db.Integer, default=0)
    t20_batting_avg = db.Column(db.Float, default=0)
    t20_bowling_avg = db.Column(db.Float, default=0)
    t20_strike_rate = db.Column(db.Float, default=0)
    t20_economy = db.Column(db.Float, default=0)
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Serialize discovered player data to a dictionary for API responses."""
        return {
            "name": self.name,
            "espn_id": self.espn_id,
            "country": self.country or "Unknown",
            "role": self.role or "Player",
            "batting_style": self.batting_style or "Unknown",
            "bowling_style": self.bowling_style or "Unknown",
            "t20_stats": {
                "matches": self.t20_matches,
                "runs": self.t20_runs,
                "wickets": self.t20_wickets,
                "batting_avg": self.t20_batting_avg,
                "bowling_avg": self.t20_bowling_avg,
                "strike_rate": self.t20_strike_rate,
                "economy": self.t20_economy
            }
        }

class PredictionFeedback(db.Model):
    """Store user feedback on predictions"""
    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('prediction.id'), nullable=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    is_positive = db.Column(db.Boolean, nullable=False)  # True = thumbs up, False = thumbs down
    
    # Checkbox reasons (for negative feedback)
    reason_wrong_player = db.Column(db.Boolean, default=False)
    reason_unrealistic = db.Column(db.Boolean, default=False)
    reason_ui_confusing = db.Column(db.Boolean, default=False)
    reason_bug_error = db.Column(db.Boolean, default=False)
    
    # Optional text feedback
    feedback_text = db.Column(db.String(300), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    email_sent = db.Column(db.Boolean, default=False)
    
    # Match context for reference
    venue = db.Column(db.String(100), nullable=True)
    match_format = db.Column(db.String(20), nullable=True)
    current_score = db.Column(db.Integer, nullable=True)
    predicted_score = db.Column(db.Integer, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='feedback')
    
    def to_dict(self):
        """Serialize feedback record with computed reason labels for display."""
        reasons = []
        if self.reason_wrong_player:
            reasons.append("Player not found / wrong player")
        if self.reason_unrealistic:
            reasons.append("Prediction seems unrealistic")
        if self.reason_ui_confusing:
            reasons.append("UI confusing")
        if self.reason_bug_error:
            reasons.append("Bug / error")
        
        return {
            "id": self.id,
            "is_positive": self.is_positive,
            "feedback_type": "Positive" if self.is_positive else "Negative",
            "reasons": ", ".join(reasons) if reasons else "",
            "feedback_text": self.feedback_text or "",
            "venue": self.venue or "",
            "match_format": self.match_format or "",
            "current_score": self.current_score,
            "predicted_score": self.predicted_score,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }


class PageView(db.Model):
    """Track page views for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(200), nullable=False, index=True)
    ip_hash = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    referrer = db.Column(db.String(500), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    device_type = db.Column(db.String(20), nullable=True)
    browser = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    @classmethod
    def log_view(cls, request):
        """Log a page view from a Flask request"""
        import hashlib
        ip = request.remote_addr or 'unknown'
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
        
        user_agent = request.headers.get('User-Agent', '')[:500]
        device_type = 'mobile' if any(m in user_agent.lower() for m in ['mobile', 'android', 'iphone']) else 'desktop'
        
        browser = 'Other'
        if 'Chrome' in user_agent and 'Edg' not in user_agent:
            browser = 'Chrome'
        elif 'Firefox' in user_agent:
            browser = 'Firefox'
        elif 'Safari' in user_agent and 'Chrome' not in user_agent:
            browser = 'Safari'
        elif 'Edg' in user_agent:
            browser = 'Edge'
        
        view = cls(
            path=request.path[:200],
            ip_hash=ip_hash,
            user_agent=user_agent,
            referrer=(request.referrer or '')[:500],
            device_type=device_type,
            browser=browser
        )
        db.session.add(view)
        db.session.commit()
        return view


class PlayerStatsCache(db.Model):
    """Cache for player statistics from external APIs to reduce API calls"""
    id = db.Column(db.Integer, primary_key=True)
    player_name = db.Column(db.String(100), nullable=False, index=True)
    cache_type = db.Column(db.String(20), nullable=False)  # 'batting', 'bowling', 'search', 'player_info'
    cache_key = db.Column(db.String(200), nullable=False, unique=True)
    data = db.Column(db.Text, nullable=False)  # JSON serialized data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    hit_count = db.Column(db.Integer, default=0)
    
    @classmethod
    def get_cached(cls, cache_key):
        """Get cached data if not expired"""
        from datetime import datetime
        import json
        entry = cls.query.filter_by(cache_key=cache_key).first()
        if entry and entry.expires_at > datetime.utcnow():
            entry.hit_count += 1
            db.session.commit()
            return json.loads(entry.data)
        return None
    
    @classmethod
    def set_cached(cls, cache_key, player_name, cache_type, data, hours=24):
        """Store data in cache with expiration"""
        from datetime import datetime, timedelta
        import json
        existing = cls.query.filter_by(cache_key=cache_key).first()
        if existing:
            existing.data = json.dumps(data)
            existing.expires_at = datetime.utcnow() + timedelta(hours=hours)
            existing.created_at = datetime.utcnow()
        else:
            entry = cls(
                cache_key=cache_key,
                player_name=player_name,
                cache_type=cache_type,
                data=json.dumps(data),
                expires_at=datetime.utcnow() + timedelta(hours=hours)
            )
            db.session.add(entry)
        db.session.commit()
    
    @classmethod
    def cleanup_expired(cls):
        """Remove expired cache entries"""
        from datetime import datetime
        cls.query.filter(cls.expires_at < datetime.utcnow()).delete()
        db.session.commit()


class SupportChat(db.Model):
    """Chat message in a user support conversation, linked to a session."""
    __tablename__ = 'support_chats'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    message = db.Column(db.Text, nullable=False)
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_original_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='chat_messages')


class BugReport(db.Model):
    """User-submitted bug report or feature request with optional screenshot."""
    __tablename__ = 'bug_reports'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(30), nullable=False, default='Bug')
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    contact_email = db.Column(db.String(120), nullable=True)
    include_diagnostics = db.Column(db.Boolean, default=True)
    diagnostics_data = db.Column(db.Text, nullable=True)
    screenshot_filename = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
