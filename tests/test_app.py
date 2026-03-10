import pytest
from prediction import (
    calculate_run_rate,
    calculate_required_run_rate,
    classify_bowler_type,
    get_bowler_type_from_name,
    get_venue_conditions,
    get_format_config,
    get_odi_phase,
    validate_bowling_rules,
    predict_score,
    Batsman,
    Bowler,
    MatchState,
    ALL_VENUES,
    FORMAT_CONFIG,
)
from player_data import get_all_players, get_player_by_name, search_players
from insights import build_dismissal_insights
from prematch import build_prematch_analysis, get_par_score_analysis


VALID_VENUE = ALL_VENUES[0]


class TestCalculateRunRate:
    def test_normal_values(self):
        assert calculate_run_rate(60, 10) == 6.0

    def test_zero_overs(self):
        assert calculate_run_rate(0, 0) == 0.0

    def test_high_scoring(self):
        result = calculate_run_rate(200, 20)
        assert result == 10.0


class TestCalculateRequiredRunRate:
    def test_normal_values(self):
        result = calculate_required_run_rate(180, 100, 10)
        assert result == 8.0

    def test_zero_overs_remaining(self):
        result = calculate_required_run_rate(180, 100, 0)
        assert result == float("inf")

    def test_target_already_reached(self):
        result = calculate_required_run_rate(150, 160, 5)
        assert result < 0


class TestClassifyBowlerType:
    def test_pace_fast(self):
        assert classify_bowler_type("Right arm Fast") == "pace"

    def test_pace_medium(self):
        assert classify_bowler_type("Right arm Medium fast") == "pace"

    def test_pace_seam(self):
        assert classify_bowler_type("Right arm seam") == "pace"

    def test_spin_offbreak(self):
        assert classify_bowler_type("Right arm Offbreak") == "spin"

    def test_spin_orthodox(self):
        assert classify_bowler_type("Slow Left arm Orthodox") == "spin"

    def test_spin_legbreak(self):
        assert classify_bowler_type("Legbreak Googly") == "spin"

    def test_spin_chinaman(self):
        assert classify_bowler_type("Left arm Chinaman") == "spin"

    def test_unknown_empty(self):
        assert classify_bowler_type("") == "unknown"

    def test_unknown_none(self):
        assert classify_bowler_type(None) == "unknown"


class TestGetBowlerTypeFromName:
    def test_known_pace_bowler(self):
        result = get_bowler_type_from_name("Jasprit Bumrah")
        assert result == "pace"

    def test_known_spin_bowler(self):
        result = get_bowler_type_from_name("Yuzvendra Chahal")
        assert result == "spin"

    def test_unknown_player(self):
        result = get_bowler_type_from_name("Unknown Player XYZ")
        assert result == "unknown"


class TestGetVenueConditions:
    def test_returns_required_keys(self):
        result = get_venue_conditions(VALID_VENUE)
        assert "pitch_type" in result
        assert "pitch_description" in result
        assert "pace_wickets_pct" in result
        assert "spin_wickets_pct" in result
        assert "pace_effectiveness" in result
        assert "spin_effectiveness" in result
        assert "avg_score" in result

    def test_pitch_type_valid(self):
        result = get_venue_conditions(VALID_VENUE)
        assert result["pitch_type"] in [
            "pace-friendly",
            "spin-friendly",
            "batting-paradise",
            "balanced",
        ]

    def test_effectiveness_range(self):
        result = get_venue_conditions(VALID_VENUE)
        assert 0.75 <= result["pace_effectiveness"] <= 1.25
        assert 0.75 <= result["spin_effectiveness"] <= 1.25

    def test_unknown_venue_defaults(self):
        result = get_venue_conditions("Nonexistent Stadium, Nowhere")
        assert result["pitch_type"] in [
            "pace-friendly",
            "spin-friendly",
            "batting-paradise",
            "balanced",
        ]


class TestGetFormatConfig:
    def test_mens_t20(self):
        config = get_format_config("mens_t20")
        assert config["max_overs"] == 20
        assert config["max_bowler_overs"] == 4
        assert config["is_odi"] is False

    def test_womens_t20(self):
        config = get_format_config("womens_t20")
        assert config["max_overs"] == 20
        assert config["avg_score"] == 140

    def test_mens_odi(self):
        config = get_format_config("mens_odi")
        assert config["max_overs"] == 50
        assert config["max_bowler_overs"] == 10
        assert config["is_odi"] is True

    def test_womens_odi(self):
        config = get_format_config("womens_odi")
        assert config["max_overs"] == 50
        assert config["avg_score"] == 230

    def test_invalid_format_defaults_to_mens_t20(self):
        config = get_format_config("invalid_format")
        assert config == FORMAT_CONFIG["mens_t20"]


class TestGetOdiPhase:
    def test_powerplay(self):
        assert get_odi_phase(0) == "powerplay_1"
        assert get_odi_phase(5) == "powerplay_1"
        assert get_odi_phase(9.5) == "powerplay_1"

    def test_middle_1(self):
        assert get_odi_phase(10) == "middle_1"
        assert get_odi_phase(20) == "middle_1"
        assert get_odi_phase(29.5) == "middle_1"

    def test_middle_2(self):
        assert get_odi_phase(30) == "middle_2"
        assert get_odi_phase(35) == "middle_2"
        assert get_odi_phase(39.5) == "middle_2"

    def test_death(self):
        assert get_odi_phase(40) == "death"
        assert get_odi_phase(45) == "death"
        assert get_odi_phase(49) == "death"


class TestValidateBowlingRules:
    def test_no_errors_valid_state(self):
        match_state = MatchState(
            current_score=50,
            wickets_fallen=2,
            overs_completed=8,
            venue=VALID_VENUE,
            batsmen=[Batsman("Player A", 30, 20)],
            bowlers=[
                Bowler("Bowler A", 2, 15, 1, 2),
                Bowler("Bowler B", 2, 18, 0, 2),
            ],
            next_over_bowler="Bowler A",
            last_over_bowler="Bowler B",
        )
        errors = validate_bowling_rules(match_state)
        assert errors == []

    def test_consecutive_overs_error(self):
        match_state = MatchState(
            current_score=50,
            wickets_fallen=2,
            overs_completed=8,
            venue=VALID_VENUE,
            batsmen=[Batsman("Player A", 30, 20)],
            bowlers=[Bowler("Bowler A", 2, 15, 1, 2)],
            next_over_bowler="Bowler A",
            last_over_bowler="Bowler A",
        )
        errors = validate_bowling_rules(match_state)
        assert any("consecutive" in e.lower() for e in errors)

    def test_over_limit_exceeded(self):
        match_state = MatchState(
            current_score=50,
            wickets_fallen=2,
            overs_completed=8,
            venue=VALID_VENUE,
            batsmen=[Batsman("Player A", 30, 20)],
            bowlers=[Bowler("Bowler A", 5, 40, 2, 0)],
        )
        errors = validate_bowling_rules(match_state)
        assert len(errors) > 0


class TestPredictScoreT20:
    def test_basic_t20_prediction(self):
        match_state = MatchState(
            current_score=80,
            wickets_fallen=2,
            overs_completed=10,
            venue=VALID_VENUE,
            batsmen=[
                Batsman("Virat Kohli", 45, 30),
                Batsman("Rohit Sharma", 25, 18),
            ],
            bowlers=[
                Bowler("Jasprit Bumrah", 2, 12, 1, 2),
                Bowler("Yuzvendra Chahal", 2, 18, 1, 2),
            ],
            next_over_bowler="Jasprit Bumrah",
            last_over_bowler="Yuzvendra Chahal",
            match_format="mens_t20",
        )
        result = predict_score(match_state)
        assert result.predicted_final_score > 80
        assert result.predicted_final_score < 300
        assert 0 <= result.predicted_wickets <= 10
        assert result.predicted_next_over_runs >= 0
        assert result.score_range[0] <= result.predicted_final_score <= result.score_range[1]
        assert 0 <= result.wicket_probability <= 1.0
        assert result.boundary_count >= 0
        assert result.dot_ball_count >= 0
        assert result.singles_doubles_count >= 0

    def test_has_expected_fields(self):
        match_state = MatchState(
            current_score=50,
            wickets_fallen=1,
            overs_completed=6,
            venue=VALID_VENUE,
            batsmen=[Batsman("Virat Kohli", 30, 20)],
            bowlers=[Bowler("Jasprit Bumrah", 2, 10, 0, 2)],
            match_format="mens_t20",
        )
        result = predict_score(match_state)
        assert hasattr(result, "predicted_final_score")
        assert hasattr(result, "predicted_wickets")
        assert hasattr(result, "predicted_next_over_runs")
        assert hasattr(result, "score_range")
        assert hasattr(result, "wicket_probability")
        assert hasattr(result, "boundary_count")
        assert hasattr(result, "dot_ball_count")
        assert hasattr(result, "win_probability")
        assert hasattr(result, "pitch_type")
        assert hasattr(result, "bowler_type")


class TestPredictScoreODI:
    def test_odi_prediction(self):
        match_state = MatchState(
            current_score=120,
            wickets_fallen=2,
            overs_completed=20,
            venue=VALID_VENUE,
            batsmen=[
                Batsman("Virat Kohli", 60, 55),
                Batsman("Rohit Sharma", 40, 35),
            ],
            bowlers=[
                Bowler("Jasprit Bumrah", 5, 20, 1, 5),
                Bowler("Yuzvendra Chahal", 5, 25, 1, 5),
            ],
            match_format="mens_odi",
        )
        result = predict_score(match_state)
        assert result.predicted_final_score > 120
        assert result.predicted_final_score < 500
        assert 0 <= result.predicted_wickets <= 10


class TestPredictScoreChase:
    def test_chase_scenario(self):
        match_state = MatchState(
            current_score=100,
            wickets_fallen=3,
            overs_completed=12,
            venue=VALID_VENUE,
            batsmen=[
                Batsman("Virat Kohli", 50, 35),
                Batsman("Rohit Sharma", 30, 25),
            ],
            bowlers=[
                Bowler("Jasprit Bumrah", 3, 18, 1, 1),
                Bowler("Yuzvendra Chahal", 3, 22, 1, 1),
            ],
            innings=2,
            target=180,
            match_format="mens_t20",
        )
        result = predict_score(match_state)
        assert result.is_chase is True
        assert result.runs_needed > 0
        assert result.required_run_rate > 0
        assert 0 <= result.win_probability <= 100


class TestAPIEndpoints:
    def test_index_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_api_players_returns_json_list(self, client):
        response = client.get("/api/players")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_api_players_filtered(self, client):
        response = client.get("/api/players?q=virat")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert any("virat" in p["name"].lower() for p in data)

    def test_api_player_stats(self, client):
        response = client.get("/api/player/Virat Kohli")
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Virat Kohli"
        assert "batting" in data
        assert "bowling" in data

    def test_api_live_matches(self, client):
        response = client.get("/api/live-matches")
        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data

    def test_predict_valid_form(self, client):
        response = client.post(
            "/predict",
            data={
                "venue": VALID_VENUE,
                "current_score": "80",
                "wickets_fallen": "2",
                "overs_completed": "10",
                "next_over_bowler": "",
                "last_over_bowler": "",
                "innings": "1",
                "match_format": "mens_t20",
                "batsman1_name": "Virat Kohli",
                "batsman1_runs": "40",
                "batsman1_balls": "28",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_predict_negative_score_redirects(self, client):
        response = client.post(
            "/predict",
            data={
                "venue": VALID_VENUE,
                "current_score": "-10",
                "wickets_fallen": "2",
                "overs_completed": "10",
                "match_format": "mens_t20",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_predict_all_wickets_redirects(self, client):
        response = client.post(
            "/predict",
            data={
                "venue": VALID_VENUE,
                "current_score": "150",
                "wickets_fallen": "10",
                "overs_completed": "18",
                "match_format": "mens_t20",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_insights_returns_200(self, client):
        response = client.get("/insights")
        assert response.status_code == 200

    def test_prematch_returns_200(self, client):
        response = client.get("/prematch")
        assert response.status_code == 200

    def test_support_chat_returns_200(self, client):
        response = client.get("/support-chat")
        assert response.status_code == 200

    def test_bug_report_returns_200(self, client):
        response = client.get("/bug-report")
        assert response.status_code == 200


class TestPlayerData:
    def test_get_all_players_non_empty(self):
        players = get_all_players()
        assert len(players) > 0

    def test_get_player_by_name_known(self):
        player = get_player_by_name("Virat Kohli")
        assert player is not None
        assert player["name"] == "Virat Kohli"
        assert player["team"] == "RCB"

    def test_get_player_by_name_unknown(self):
        player = get_player_by_name("Nonexistent Player XYZ")
        assert player is None

    def test_search_players(self):
        results = search_players("kohli")
        assert len(results) > 0
        assert any("Kohli" in p["name"] for p in results)

    def test_all_players_have_required_fields(self):
        players = get_all_players()
        for player in players:
            assert "name" in player, f"Player missing 'name': {player}"
            assert "team" in player, f"Player missing 'team': {player}"
            assert "role" in player, f"Player missing 'role': {player}"


class TestInsightsEngine:
    def test_build_dismissal_insights_structure(self):
        result = build_dismissal_insights(
            batsman_name="Virat Kohli",
            batsman_runs=30,
            batsman_balls=20,
            bowler_name="Jasprit Bumrah",
            venue=VALID_VENUE,
            overs=10,
            wickets=2,
            current_score=80,
        )
        assert result.batsman_name == "Virat Kohli"
        assert len(result.dismissal_modes) > 0
        assert result.overall_risk in ["Low", "Medium", "High", "Very High"]
        assert result.confidence in ["Low", "Medium", "High"]
        assert result.survival_estimate > 0
        assert isinstance(result.key_insight, str)

    def test_dismissal_probabilities_sum_to_one(self):
        result = build_dismissal_insights(
            batsman_name="Virat Kohli",
            batsman_runs=30,
            batsman_balls=20,
            bowler_name="Jasprit Bumrah",
            venue=VALID_VENUE,
            overs=10,
            wickets=2,
            current_score=80,
        )
        total_prob = sum(d.probability for d in result.dismissal_modes)
        assert abs(total_prob - 1.0) < 0.05


class TestPrematch:
    def test_build_prematch_analysis_keys(self):
        result = build_prematch_analysis(VALID_VENUE, "mens_t20")
        assert "venue" in result
        assert "bat_chase" in result
        assert "surface" in result
        assert "par_score" in result
        assert "phases" in result
        assert "toss_advice" in result
        assert "weather" in result
        assert "pitch_tempo" in result

    def test_par_score_t20_vs_odi(self):
        t20_result = get_par_score_analysis(VALID_VENUE, "mens_t20")
        odi_result = get_par_score_analysis(VALID_VENUE, "mens_odi")
        assert odi_result["par_score"] > t20_result["par_score"]
        assert "par_score" in t20_result
        assert "competitive_range" in t20_result
        assert "scoring_vibe" in t20_result
