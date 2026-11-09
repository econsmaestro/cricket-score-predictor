"""Opportunity-adjusted estimates; dismissal counts are NOT catching ability."""
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
import math

import numpy as np
from scipy.optimize import minimize
from scipy.special import betaln
from scipy.stats import beta


@dataclass(frozen=True)
class ProbabilityEstimate:
    mean: float | None
    lower: float | None
    upper: float | None
    successes: int
    trials: int
    method: str

    def to_dict(self):
        return asdict(self)


def estimate(successes, trials, prior=None):
    if not 0 <= successes <= trials:
        raise ValueError("Success count must be between zero and trial count")
    if trials == 0:
        return ProbabilityEstimate(None, None, None, 0, 0, "unavailable")
    # Jeffreys' reference prior is an explicit statistical convention, not
    # a hand-assigned team rating. Hierarchical priors are fitted below.
    a, b = prior if prior is not None else (0.5, 0.5)
    a, b = a + successes, b + trials - successes
    low, high = beta.ppf([0.025, 0.975], a, b)
    return ProbabilityEstimate(float(a / (a + b)), float(low), float(high),
                               successes, trials,
                               "empirical_bayes_beta" if prior else "jeffreys_beta")


def learn_prior(groups):
    """Fit beta-binomial population hyperparameters by marginal likelihood.

    Each group is one player in ONE format/gender/provider cohort. Degenerate
    cohorts do not identify between-player variation, so use reference-prior
    estimates and disclose that rather than fabricate a learned population.
    """
    groups = [(s, n) for s, n in groups if n]
    if len(groups) < 2:
        return None
    s = np.array([x[0] for x in groups], dtype=float)
    n = np.array([x[1] for x in groups], dtype=float)
    if s.sum() == 0 or s.sum() == n.sum():
        return None

    def objective(log_ab):
        a, b = np.exp(log_ab)
        return float(-np.sum(betaln(s + a, n - s + b) - betaln(a, b)))

    result = minimize(objective, np.zeros(2), bounds=[(-12, 16), (-12, 16)],
                      method="L-BFGS-B")
    if not result.success or not math.isfinite(result.fun):
        return None
    return tuple(float(v) for v in np.exp(result.x))


def eligible_trials(records, as_of, match_format, gender):
    as_of = date.fromisoformat(str(as_of))
    selected = [r for r in records if r["match_format"] == match_format and r["gender"] == gender
                and date.fromisoformat(str(r["event_date"])) < as_of
                and date.fromisoformat(str(r["available_date"])) < as_of]
    sources = {r["source"] for r in selected}
    if len(sources) > 1:
        raise ValueError("Multiple event feeds require explicit deduplication before fitting")
    return selected


def probability_model(records, *, kind, as_of, match_format, gender, person_id=None):
    """Separate opportunity occurrence and conditional conversion.

    Absence of a wicket is NOT labelled a failed catch. Only feeds explicitly
    declaring exhaustive delivery/opportunity coverage can fit these models.
    This first estimator is a cohort baseline, not a position/difficulty model.
    """
    if kind not in {"catch", "run_out"}:
        raise ValueError("Expected catch or run_out")
    rows = [r for r in eligible_trials(records, as_of, match_format, gender)
            if r["kind"] == kind and r.get("exhaustive_delivery_coverage") is True]
    exposure = [r for r in rows if r.get("opportunity") is not None]
    occurrence = estimate(sum(r["opportunity"] for r in exposure), len(exposure))
    groups = defaultdict(lambda: [0, 0])
    for row in rows:
        if row.get("opportunity") is True and row.get("success") is not None and row.get("person_id"):
            group = groups[row["person_id"]]
            group[0] += int(row["success"])
            group[1] += 1
    prior = learn_prior(groups.values())
    s, n = groups.get(person_id, (0, 0))
    conversion = estimate(s, n, prior)
    # This combines a cohort occurrence rate with a specified player's
    # conversion, conditional on that player receiving the opportunity.
    # It is NOT a whole-XI estimate without an opportunity allocation model.
    success_probability = (
        occurrence.mean * conversion.mean
        if occurrence.mean is not None and conversion.mean is not None else None)
    direct = [r for r in rows if r.get("person_id") == person_id
              and r.get("opportunity") is True
              and r.get("context", {}).get("direct_hit_attempt") is True
              and r.get("success") is not None]
    return {
        "opportunity": occurrence.to_dict(), "conversion": conversion.to_dict(),
        "successful_dismissal_probability_if_assigned": success_probability,
        "direct_hit_conversion": estimate(sum(r["success"] for r in direct), len(direct)).to_dict(),
        "observed_direct_hits": sum(r.get("direct_hit") is True for r in rows
                                    if r.get("person_id") == person_id),
        "unmodelled_context": ["opportunity_assignment", "position", "difficulty",
                              "shot", "batter", "bowler", "throw_distance"],
        "status": "component_estimate" if success_probability is not None else "insufficient_opportunity_data",
    }


def fielding_quality(records, *, person_id, as_of, match_format, gender):
    kwargs = dict(as_of=as_of, match_format=match_format, gender=gender, person_id=person_id)
    catch = probability_model(records, kind="catch", **kwargs)
    run_out = probability_model(records, kind="run_out", **kwargs)
    ground = [r for r in eligible_trials(records, as_of, match_format, gender)
              if r["kind"] == "ground" and r.get("person_id") == person_id
              and r.get("runs_saved") is not None]
    ground_values = np.array([r["runs_saved"] for r in ground], dtype=float)
    ground_interval = None
    if len(ground_values) > 1:
        from scipy.stats import t
        half_width = float(t.ppf(0.975, len(ground_values)-1)
                           * ground_values.std(ddof=1) / np.sqrt(len(ground_values)))
        ground_interval = [float(ground_values.mean()-half_width),
                           float(ground_values.mean()+half_width)]
    return {
        "person_id": person_id, "as_of": str(as_of), "format": match_format, "gender": gender,
        "catch": catch, "run_out": run_out,
        "observed_ground_events": len(ground),
        "component_confidence": {
            "catching": catch["conversion"],
            "throwing": run_out["conversion"],
            "ground_fielding": {
                "sample_size": len(ground), "mean_95_percent_interval": ground_interval,
                "method": "student_t_descriptive" if ground_interval else "insufficient_sample",
                "limitations": "Provider-labelled events; repeated-player/match clustering may invalidate independence",
            },
        },
        "mean_reported_runs_saved_per_recorded_event": (
            sum(r["runs_saved"] for r in ground) / len(ground) if ground else None),
        # Components do not share units, and no outcome-trained aggregation
        # has been validated. A 0–100 composite would imply false precision.
        "fqr": None, "status": "no_validated_composite",
        "confidence": "Report component sample sizes and 95% credible intervals; no global confidence percentage",
    }
