"""Self-contained, table-based evidence report; no chart/runtime dependencies."""
from datetime import datetime
from html import escape
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


def table(headers, rows):
    heading = "".join(f"<th scope='col'>{escape(str(h))}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>" for row in rows)
    return f"<div class='scroll'><table><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>"


def build_report(root=Path("generated-artifacts/fielding"), test_results=None):
    root = Path(root)
    coverage = json.loads((root / "coverage.json").read_text())
    comparison = json.loads((root / "comparison.json").read_text())
    tests = {"passed": None, "failed": None, "skipped": None, "fielding": None}
    if test_results:
        cases = ET.parse(test_results).getroot().findall(".//testcase")
        tests["failed"] = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
        tests["skipped"] = sum(c.find("skipped") is not None for c in cases)
        tests["passed"] = len(cases) - tests["failed"] - tests["skipped"]
        tests["fielding"] = sum("test_fielding_intelligence" in c.get("classname", "")
                               and c.find("failure") is None and c.find("error") is None
                               and c.find("skipped") is None for c in cases)
    missing = ["Dropped catches and complete catch opportunities", "Catch difficulty and fielding position",
               "Complete run-out opportunities and throw-attempt denominators",
               "Direct-hit versus assisted-run-out roles",
               "Misfields, boundary saves and runs saved",
               "Precise substitute/on-field exposure time",
               "Event-labelled pressure data and attacking-shot annotations"]
    stages = [
        ("1. Audit", "Completed", "Existing engine, data pipelines, identities, licences and evidence gaps documented."),
        ("2. Registry and ingestion", "Implemented; partial world coverage",
         f"{coverage['people_including_officials']:,} people including officials; "
         f"{coverage['historical_observations']['matches']:,} fixtures. Not every professional or competition worldwide."),
        ("3. Statistics and FQR", "Component estimators implemented; FQR unavailable",
         "Observed dismissal counts are not ability. Separate catching/throwing credible intervals and ground-fielding sample uncertainty."),
        ("4. Catch / run-out models", "Opportunity/conversion estimators implemented; unvalidated",
         "No complete labelled opportunity trials in the imported real data. Context-sensitive conversion and XI opportunity allocation remain unvalidated."),
        ("5. Fielding pressure", "Controlled research code implemented; inactive",
         "Controls for score/innings, wickets lost, over, required run rate and prior scoring/wickets. No real annotated-event evidence."),
        ("6. Prediction integration", "Shadow adapter only",
         "Existing prediction.py is byte-for-byte unchanged. No new fielding adjustment, extra wicket, altered score interval or win multiplier."),
        ("7. Comparison", "Compatibility evaluated; improvement not demonstrated",
         "Identical baseline/shadow observations. Four international cohorts, plus available franchise cohorts. No replacement activated."),
    ]
    performance = []
    for c in comparison["cohorts"]:
        m = c["baseline"]
        performance.append([
            c["format"], m["matches"], m["predictions"], f"{m['score_mae']:.2f}",
            f"{m['score_bias']:+.2f}", f"{m['wicket_mae']:.2f}", f"{m['wicket_bias']:+.2f}",
            f"{100*m['exact_wicket_accuracy']:.1f}%", f"{100*m['interval_coverage']:.1f}%",
            f"{c['delta_score_mae']:+.2f}", f"{c['delta_wicket_mae']:+.2f}",
        ])
    components = [
        ("Catching ability", "Unavailable", "No observed failed-chance denominator; successful catches do not identify conversion skill."),
        ("Throwing / run-out ability", "Unavailable", "No complete run-out/throw opportunities; one named participant does not prove a direct hit."),
        ("Ground fielding", "Unavailable", "No runs-saved or misfield event labels."),
        ("Overall FQR", "Not generated", "Missing components and no independently validated learned aggregation."),
        ("Fielding Pressure Index", "Not generated", "Dot-ball sequences alone do not identify exceptional fielding or psychology."),
        ("Win-probability effect", "Not evaluated", "First-innings replay does not test chase win calibration."),
        ("Shadow integration", "Compatible; no improvement", "Numerical predictions are identical by design; compatibility is not an enhanced-model performance claim."),
    ]
    observations = coverage["historical_observations"]["observed"]
    total_matches = sum(c["baseline"]["matches"] for c in comparison["cohorts"])
    total_predictions = sum(c["baseline"]["predictions"] for c in comparison["cohorts"])
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CricPredict — Fielding intelligence evidence report</title>
<style>
body{{font-family:system-ui,sans-serif;color:#172b40;background:#f5f8fb;margin:0;line-height:1.6}}
main{{max-width:1080px;margin:auto;padding:30px 20px 70px}}h1,h2{{line-height:1.2;color:#153e68}}
h1{{font-size:2rem}}h2{{margin-top:42px}}.notice{{background:#fff5d6;border-left:5px solid #bd7c00;padding:18px}}
.scroll{{overflow-x:auto;background:white;border:1px solid #d6e0e8}}table{{border-collapse:collapse;width:100%;font-size:.92rem}}
th,td{{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #e2e8ed}}th{{background:#eaf0f6}}
small,.muted{{color:#4d6175}}a{{color:#145f9c}}code{{overflow-wrap:anywhere}}li{{margin-bottom:7px}}
@media(max-width:600px){{main{{padding:18px 14px 45px}}h1{{font-size:1.65rem}}th,td{{padding:9px}}}}
</style><main>
<p class="muted">CricPredict · Research snapshot · {escape(datetime.now(ZoneInfo("Asia/Singapore")).isoformat(timespec="seconds"))}</p>
<h1>Fielding intelligence: infrastructure established, improvement not demonstrated</h1>
<div class="notice"><strong>No enhanced predictor has been activated.</strong>
The available data describes successful fielding dismissals, but does not identify
opportunity-adjusted catching, throwing or ground-fielding ability. Existing hardcoded
ratings and live predictions remain unchanged. No deployment or production data change was performed.</div>
<h2>Stage-by-stage status</h2>{table(["Stage", "Status", "Evidence / limitation"], stages)}
<h2>Actual imported coverage</h2>
<p>{coverage['people_including_officials']:,} people including officials;
{coverage['aliases']:,} aliases; {coverage['identifiers']:,} provider identifiers.
There are <strong>{coverage['complete_opportunity_records']} complete delivery-opportunity records</strong>
and {coverage['labelled_trials']} imported event records.
Registry presence is not proof of professional-player or detailed event coverage.</p>
{table(["Format", "Gender", "Fixtures", "First start", "Last completion"],
       [[c["format"], c["gender"], c["matches"], c["first"], c["last"]] for c in coverage["cohorts"]])}
<p>Archives imported: men's/women's ODI and international T20, men's/women's Tests,
IPL, BBL, WBBL, PSL, CPL and WPL. These are cached source snapshots with different
last-covered dates, not a promise of a complete or current worldwide feed.</p>
{table(["Observed record", "Count"], [
    ("Fixtures", coverage["historical_observations"]["matches"]),
    ("Deliveries, including illegal deliveries", observations["deliveries"]),
    ("Catch dismissals", observations["catch_dismissals"]),
    ("Run-out dismissals", observations["run_out_dismissals"]),
    ("Stumpings", observations["stumpings"]),
    ("Unresolved fielder name entries", observations.get("unresolved_fielder_events", 0)),
])}
<p>Counts are observations, not ability ratings. Multiple run-out participants are
retained as involvement, without inventing direct-hit/assist roles. Individual
on-field delivery exposure is unknown because XI membership does not track substitutions.</p>
<h2>Missing information prevents ability claims</h2><ul>
{"".join("<li>"+escape(s)+"</li>" for s in missing)}</ul>
<h2>Component evidence and prediction contribution</h2>
{table(["Component", "Empirical status", "Reason"], components)}
<h2>Four-cohort historical comparison</h2>
<p>The four cohorts contain {total_matches:,} distinct fixtures in total; each cohort's
count is shown below. ODI uses four checkpoints and T20 five, yielding
{total_predictions:,} international checkpoint predictions. Bias is prediction minus
actual; negative means undershoot. Accuracy/coverage values below are baseline
and shadow values alike. Deltas are shadow minus baseline.</p>
{table(["Cohort", "Matches", "Checkpoints", "Score MAE", "Score bias", "Wicket MAE",
        "Wicket bias", "Exact wickets", "Interval coverage", "Δ score MAE", "Δ wicket MAE"], performance)}
<p><strong>Existing wicket underprediction is substantial.</strong> The new shadow
system does not fix it. Equal metrics demonstrate compatibility only, not a
statistical fielding enhancement. Score interval coverage is measured, not
certified as a calibrated confidence level.</p>
<h2>Franchise replay coverage</h2>
{table(["Competition", "Matches", "Checkpoints", "Score MAE", "Wicket MAE", "Interval coverage"],
       [[c["competition"], c["baseline"]["matches"], c["baseline"]["predictions"],
         f'{c["baseline"]["score_mae"]:.2f}', f'{c["baseline"]["wicket_mae"]:.2f}',
         f'{100*c["baseline"]["interval_coverage"]:.1f}%']
        for c in comparison.get("franchise_cohorts", [])])}
<p>Franchise shadow predictions are also identical to baseline. WPL uses 50
eligible fixtures rather than claiming a 100-match cohort. Test data is ingested,
but the existing baseline has no Test prediction engine; Test forecast performance
is not evaluated.</p>
<h2>Historical timing and leakage safeguards</h2><ul>
<li>Opportunity models use only records whose event and known-availability dates
are strictly earlier than the requested prediction date. Whole-day cutoffs are
conservative: no same-day evidence is used.</li>
<li>Cricsheet history excludes the evaluation fixture, later completions and
source files created on/after the cutoff; multi-day matches must have ended.</li>
<li>Cricsheet corrected revisions do not carry a reliable historical publication
timestamp. These snapshots do not establish revision-level historical availability.</li>
<li>Residual-learning features must precede their fixture; outcomes must be
available before training cutoff. Cross-validation splits whole dates and fits
scaling within each fold.</li>
<li>The untouched baseline may already incorporate later historical priors, and
these latest-match cohorts have been used in earlier calibration. This is
<strong>not clean out-of-time validation of the entire engine</strong>.</li>
<li>Pressure research separates earlier/later fixtures and excludes the event
delivery from subsequent outcomes. Associations remain confounded; no causal,
psychological or significance claim is made.</li></ul>
<h2>Tests and operational scope</h2>
<p>Recorded test run: <strong>{tests['passed']} passed, {tests['failed']} failed,
{tests['skipped']} skipped</strong>; {tests['fielding']} are fielding-specific cases.
Synthetic event tests verify software behaviour, not accuracy on real fielding
opportunity data. Read-only research API endpoints are separate from prediction routes.</p>
<p>Six additive tables were created and populated in development where applicable.
No existing tables or records were replaced. Database migration to production and
any live integration require separate approval; production remains untouched.</p>
<h2>Provider accessibility, licence and costs</h2><ul>
<li><a href="https://cricsheet.org/">Cricsheet</a>: public downloads; JSON and
registry use <a href="https://cricsheet.org/licensing/">ODC Attribution 1.0</a>.
Coverage has gaps, including withheld Afghanistan matches. No paid subscription used.</li>
<li><a href="https://developer.sportradar.com/cricket/reference/cricket-faq">Sportradar</a>:
public documentation describes richer fielding-level coverage for selected ICC
events and CPL. Exact event schema, historical depth, commercial/model-training
rights and costs require confirmation; no universally priced feed assumed.</li>
<li><a href="https://www.statsperform.com/team-performance/performance-solutions-for-cricket/">Opta</a>:
advertises detailed cricket data and fielding metrics. Licensing is
<a href="https://www.statsperform.com/faqs/stats-perform-faqs-pricing-licensing/">custom quoted</a>;
desired opportunity, difficulty and runs-saved fields need a licensed sample.
No provider purchase, account or credentials were created.</li></ul>
<p class="muted">Data derived from Cricsheet, Open Data Commons Attribution License 1.0.
No commentary archive was assumed or introduced. This self-contained report makes
no live data queries and includes no private player/customer account information.</p>
</main></html>"""
    output = root / "report.html"
    if len(html.encode()) > 5_242_880:
        raise ValueError("Report exceeds delivery size budget")
    output.write_text(html)
    return output
