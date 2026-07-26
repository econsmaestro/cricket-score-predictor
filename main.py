from app import app
from routes import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Background scheduler — scrapes completed match results once per day
# ---------------------------------------------------------------------------
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from background_jobs import daily_match_scrape

    scheduler = BackgroundScheduler(daemon=True)
    # Run every 24 hours; also fire immediately on first startup so we
    # don't have to wait a full day for the first data point.
    scheduler.add_job(
        daily_match_scrape,
        trigger=IntervalTrigger(hours=24),
        id='daily_match_scrape',
        next_run_time=__import__('datetime').datetime.utcnow(),  # run at startup
        replace_existing=True,
    )
    scheduler.start()
    import logging
    logging.getLogger(__name__).info("APScheduler started — daily match scrape scheduled.")
except Exception as _sched_err:
    import logging
    logging.getLogger(__name__).warning(f"Scheduler could not start: {_sched_err}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
