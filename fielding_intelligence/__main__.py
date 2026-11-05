"""Explicit offline operations; never imported by the live prediction route."""
import argparse
from datetime import date
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("registry", help="Download and ingest the public Cricsheet people registry")
    from .sources import ARCHIVES
    download = commands.add_parser("download", help="Download public Test/franchise archives for offline ingestion")
    download.add_argument("archives", nargs="+", choices=ARCHIVES)
    archive = commands.add_parser("ingest", help="Ingest local Cricsheet JSON ZIP archives")
    archive.add_argument("archives", nargs="+")
    archive.add_argument("--limit", type=int)
    trials = commands.add_parser("trials", help="Import licensed, provenance-labelled JSONL events")
    trials.add_argument("path")
    commands.add_parser("coverage")
    pressure = commands.add_parser("pressure", help="Analyse annotated JSON delivery records with situation controls")
    pressure.add_argument("path")
    pressure.add_argument("--split-date", required=True)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--matches", type=int, default=100)
    evaluation.add_argument("--output", default="generated-artifacts/fielding/comparison.json")
    evaluation.add_argument("--include-franchise", action="store_true",
                            help="Also replay downloaded IPL/BBL/WBBL/PSL/CPL/WPL archives")
    report = commands.add_parser("report")
    report.add_argument("--test-results", required=True)
    args = parser.parse_args()
    if getattr(args, "limit", None) is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if getattr(args, "matches", 1) < 1:
        parser.error("--matches must be positive")
    if args.command == "download":
        from .sources import download_archive
        for name in args.archives:
            print(json.dumps({"downloaded": str(download_archive(name))}), flush=True)
        return
    if args.command == "pressure":
        from .pressure import controlled_pressure
        data = json.loads(Path(args.path).read_text())
        print(json.dumps(controlled_pressure(data, split_date=args.split_date), indent=2))
        return
    if args.command == "report":
        from .reporting import build_report
        print(build_report(test_results=args.test_results))
        return

    from app import app, db
    from sqlalchemy import func, select
    from .models import FieldingAlias, FieldingIdentifier, FieldingMatch, FieldingPerson, FieldingTrial
    from .ingestion import ingest_archive, import_trials
    from .registry import ingest_registry
    from .service import observed_history

    with app.app_context():
        if args.command == "registry":
            import requests
            folder = Path("generated-artifacts/fielding/sources")
            folder.mkdir(parents=True, exist_ok=True)
            data = {}
            for name in ("people.csv", "names.csv"):
                response = requests.get(f"https://cricsheet.org/register/{name}", timeout=60)
                response.raise_for_status()
                text = response.content.decode("utf-8-sig")
                if not text.startswith("identifier,"):
                    raise ValueError("Unexpected registry response")
                (folder / name).write_text(text)
                data[name] = text
            result = ingest_registry(db.session, data["people.csv"], data["names.csv"])
            db.session.commit()
        elif args.command == "ingest":
            result = []
            for path in args.archives:
                report = ingest_archive(db.session, path, args.limit)
                db.session.commit()
                result.append({"archive": str(path), **report})
                print(json.dumps(result[-1]), flush=True)
            return
        elif args.command == "trials":
            with open(args.path) as stream:
                result = {"imported": import_trials(db.session, [json.loads(x) for x in stream if x.strip()])}
            db.session.commit()
        elif args.command == "evaluate":
            from .evaluation import compare
            result = {"generated_on": str(date.today()), "cohorts": [
                compare(db.session, f, args.matches)
                for f in ("mens_odi", "womens_odi", "mens_t20", "womens_t20")]}
            if args.include_franchise:
                result["franchise_cohorts"] = []
                for competition, filename, fmt, count in (
                    ("IPL", "ipl_json.zip", "mens_t20", 100),
                    ("BBL", "bbl_json.zip", "mens_t20", 100),
                    ("PSL", "psl_json.zip", "mens_t20", 100),
                    ("CPL", "cpl_json.zip", "mens_t20", 100),
                    ("WBBL", "wbb_json.zip", "womens_t20", 100),
                    ("WPL", "wpl_json.zip", "womens_t20", 50),
                ):
                    comparison = compare(db.session, fmt, min(count, args.matches),
                                         Path("generated-artifacts/fielding/sources") / filename)
                    comparison["competition"] = competition
                    result["franchise_cohorts"].append(comparison)
            output = Path(args.output)
            if not output.is_relative_to(Path("generated-artifacts")) or ".." in output.parts:
                raise ValueError("Evaluation outputs must stay under generated-artifacts")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2))
            result = {"report": str(output), "cohorts": [
                {k: c[k] for k in ("format", "baseline", "fielding_shadow", "activation")}
                for c in result["cohorts"]],
                "franchise_cohorts": [
                    {k: c[k] for k in ("competition", "baseline", "activation")}
                    for c in result.get("franchise_cohorts", [])]}
        else:
            cohort_counts = db.session.execute(select(
                FieldingMatch.match_format, FieldingMatch.gender, func.count(),
                func.min(FieldingMatch.start_date), func.max(FieldingMatch.end_date)
            ).group_by(FieldingMatch.match_format, FieldingMatch.gender)).all()
            history = observed_history(list(db.session.scalars(select(FieldingMatch))))
            history.pop("players")
            result = {
                "people_including_officials": db.session.scalar(select(func.count()).select_from(FieldingPerson)),
                "aliases": db.session.scalar(select(func.count()).select_from(FieldingAlias)),
                "identifiers": db.session.scalar(select(func.count()).select_from(FieldingIdentifier)),
                "labelled_trials": db.session.scalar(select(func.count()).select_from(FieldingTrial)),
                "complete_opportunity_records": db.session.scalar(select(func.count()).select_from(FieldingTrial).where(
                    FieldingTrial.kind.in_(("catch", "run_out")),
                    FieldingTrial.exhaustive_delivery_coverage.is_(True),
                    FieldingTrial.opportunity.is_not(None))),
                "cohorts": [{"format": f, "gender": g, "matches": n, "first": str(a), "last": str(b)}
                            for f, g, n, a, b in cohort_counts],
                "historical_observations": history,
                "attribution": "Data derived from Cricsheet, ODC Attribution License 1.0",
            }
        print(json.dumps(result, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
