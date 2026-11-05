"""Safe engine integration: shadow-only until replacements earn activation."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ShadowPrediction:
    baseline: object
    candidate: object
    diagnostics: dict


def attach_shadow(result, diagnostics):
    """Never add catches/run-outs to the engine's existing wicket projection."""
    if diagnostics.get("applied"):
        raise ValueError("Shadow diagnostics cannot authorise prediction adjustments")
    return ShadowPrediction(result, replace(result), dict(diagnostics))


def predict_with_fielding(state, session, *, as_of, xi_ids=()):
    """Use the existing engine exactly once, then attach evidence diagnostics.

    Explicit historical cutoff is required. No live source calls, no anonymous
    identity guesses, and no route from unsupported statistics to multipliers.
    """
    from prediction import predict_score
    from .service import shadow_evidence
    if state.match_format not in {"mens_t20", "womens_t20", "mens_odi", "womens_odi"}:
        raise ValueError("Existing baseline supports ODI/T20 only; Test replay is not implemented")
    raw_format = "ODI" if state.is_odi else "T20"
    gender = "female" if state.match_format.startswith("womens_") else "male"
    baseline = predict_score(state)
    evidence = shadow_evidence(session, as_of, raw_format, gender, list(xi_ids))
    return attach_shadow(baseline, evidence)
