"""Observable post-event research summaries, never a psychological multiplier."""
from statistics import mean


def investigate_pressure(deliveries, window=6):
    """Accept explicitly annotated delivery records, not commentary guesses.

    Input must be one innings in chronological order. `fielding_event` is
    provider annotation, e.g. boundary_save/dropped_catch/misfield; ordinary
    dot balls are not automatically labelled exceptional fielding.
    """
    if window < 1:
        raise ValueError("Window must be positive")
    events = []
    for i, delivery in enumerate(deliveries):
        annotation = delivery.get("fielding_event")
        if annotation in (None, "none"):
            continue
        if not delivery.get("fielding_source"):
            raise ValueError("Fielding annotations need a provenance source")
        before, after = deliveries[max(0, i-window):i], deliveries[i+1:i+1+window]
        if len(before) != window or len(after) != window:
            continue
        events.append({
            "event": annotation, "immediate_runs_saved": delivery.get("runs_saved"),
            "pre_runs_per_delivery": mean(d["runs"] for d in before),
            "post_runs_per_delivery": mean(d["runs"] for d in after),
            "post_dot_fraction": mean(d["runs"] == 0 for d in after),
            "post_wicket_fraction": mean(bool(d.get("team_wicket")) for d in after),
            "attacking_shot_frequency": (
                mean(d["attacking_shot"] for d in after)
                if all(type(d.get("attacking_shot")) is bool for d in after) else None),
        })
    return {
        "annotated_windows": len(events), "windows": events, "window_deliveries": window,
        "status": "descriptive_only" if events else "insufficient_annotated_fielding_data",
        "fpi": None, "applied_multiplier": None,
        "limitations": [
            "Before/after association is not a causal or psychological effect",
            "Match situation, batter and bowler changes confound this comparison",
            "Overlapping windows are not independent observations",
            "Immediate runs saved are separate from subsequent scoring; do not add both twice",
            "A pressure effect requires chronological, controlled validation before use",
        ],
    }


def controlled_pressure(deliveries, *, split_date, window=6):
    """Held-out associations after controlling for pre-event match situation.

    Fits the same controls-only and controls-plus-event models on earlier
    fixtures; compares them on later fixtures. No fitted term is used live.
    Requires provider event annotations and complete situation variables.
    """
    from collections import defaultdict
    from datetime import date
    import numpy as np
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.metrics import mean_absolute_error, brier_score_loss

    cutoff = date.fromisoformat(str(split_date))
    if window < 1:
        raise ValueError("Window must be positive")
    grouped = defaultdict(list)
    for row in deliveries:
        if "match_id" not in row or "innings" not in row:
            raise ValueError("Pressure research needs fixture and innings identifiers")
        grouped[(row["match_id"], row["innings"])].append(row)
    samples, missing_controls, annotations = [], 0, 0
    required = ("date", "over", "wickets_before", "score_before", "required_run_rate_before")
    for (match_id, innings), sequence in grouped.items():
        for i in range(window, len(sequence)-window):
            row = sequence[i]
            if row.get("fielding_event") not in (None, "none"):
                annotations += 1
                if not row.get("fielding_source"):
                    raise ValueError("Observed fielding events need a source")
            if any(key not in row for key in required):
                missing_controls += 1
                continue
            if row.get("fielding_coverage_complete") is not True:
                missing_controls += 1
                continue
            # In a chase, a missing RRR is missing evidence, not a zero target.
            if innings == 2 and row["required_run_rate_before"] is None:
                missing_controls += 1
                continue
            before, after = sequence[i-window:i], sequence[i+1:i+1+window]
            if any("runs" not in d or "team_wicket" not in d for d in before+after):
                missing_controls += 1
                continue
            prior_rate = mean(d["runs"] for d in before)
            controls = {
                "over": float(row["over"]), "wickets_lost": row["wickets_before"],
                "score": row["score_before"], "is_chase": float(innings == 2),
                "required_run_rate": row["required_run_rate_before"] if innings == 2 else 0.0,
                "prior_runs_per_delivery": prior_rate,
                "prior_wickets_in_window": sum(bool(d["team_wicket"]) for d in before),
            }
            samples.append({
                "date": str(row["date"]), "match_id": match_id, "controls": controls,
                "event": row.get("fielding_event", "none"),
                "score_change": mean(d["runs"] for d in after)-prior_rate,
                "subsequent_wicket": int(any(d["team_wicket"] for d in after)),
            })
    result = {
        "fpi": None, "applied_multiplier": None, "split_date": str(cutoff),
        "window_deliveries": window, "observed_annotations": annotations,
        "usable_windows": len(samples), "windows_missing_controls": missing_controls,
        "controls": ["score/match situation", "innings/chase", "wickets lost", "over number",
                     "required run rate", "preceding scoring rate", "preceding wickets"],
        "status": "insufficient_annotated_fielding_data",
        "limitations": [
            "Conditional association, not causation or a measure of psychology",
            "Immediate runs saved are excluded from the subsequent outcome window",
            "Overlapping windows need fixture-clustered inference; no significance claim made",
            "Batter/bowler/shot and unobserved conditions remain possible confounders",
            "Same-day training and evaluation are not mixed",
        ],
    }
    if not annotations:
        return result
    train = [r for r in samples if date.fromisoformat(r["date"]) < cutoff]
    test = [r for r in samples if date.fromisoformat(r["date"]) >= cutoff]
    if {r["match_id"] for r in train} & {r["match_id"] for r in test}:
        raise ValueError("A fixture cannot cross pressure training/test partitions")
    if not train or not test or not any(r["event"] != "none" for r in train):
        result["status"] = "insufficient_chronological_event_coverage"
        return result
    outcome = {}
    for enhanced in (False, True):
        def features(row):
            f = dict(row["controls"])
            if enhanced:
                f["fielding_event"] = str(row["event"])
            return f
        vectorizer = DictVectorizer(sparse=False)
        x_train = vectorizer.fit_transform([features(r) for r in train])
        x_test = vectorizer.transform([features(r) for r in test])
        scorer = LinearRegression().fit(x_train, [r["score_change"] for r in train])
        probability = None
        if len({r["subsequent_wicket"] for r in train}) == 2:
            wicket_model = LogisticRegression(max_iter=2000).fit(
                x_train, [r["subsequent_wicket"] for r in train])
            probability = float(brier_score_loss(
                [r["subsequent_wicket"] for r in test], wicket_model.predict_proba(x_test)[:, 1]))
        outcome["with_fielding_events" if enhanced else "controls_only"] = {
            "score_change_mae": float(mean_absolute_error(
                [r["score_change"] for r in test], scorer.predict(x_test))),
            "subsequent_wicket_brier": probability,
        }
    result.update({
        "status": "heldout_conditional_association_only",
        "training_matches": len({r["match_id"] for r in train}),
        "test_matches": len({r["match_id"] for r in test}), **outcome,
        "score_change_mae_delta": outcome["with_fielding_events"]["score_change_mae"]
                                  - outcome["controls_only"]["score_change_mae"],
        "subsequent_wicket_brier_delta": (
            outcome["with_fielding_events"]["subsequent_wicket_brier"]
            - outcome["controls_only"]["subsequent_wicket_brier"]
            if all(v["subsequent_wicket_brier"] is not None for v in outcome.values()) else None),
    })
    return result
