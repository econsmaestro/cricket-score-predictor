                is_positive=is_positive,
                    feedback_text=feedback.feedback_text,
                    venue=feedback.venue,
                    match_format=feedback.match_format,
                    predicted_score=feedback.predicted_score
                )
                if email_sent:
                    feedback.email_sent = True
                    db.session.commit()
            except Exception as email_err:
                app.logger.error(f"Auto-reply email error: {email_err}")
        
        flash("Thank you for your feedback! It helps us improve.", "success")
        return redirect(url_for("index"))
    except Exception as e:
        app.logger.error(f"Feedback submission error: {str(e)}")
        flash("There was an error submitting your feedback. Please try again.", "error")
        return redirect(url_for("index"))


@app.route("/feedback/export", methods=["GET"])
def export_feedback():
    """Export all feedback to Excel file"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        feedback_list = PredictionFeedback.query.order_by(PredictionFeedback.created_at.desc()).all()
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Prediction Feedback"
        
        headers = ["ID", "Date/Time", "Feedback Type", "Reasons", "Comments", "Venue", "Format", "Current Score", "Predicted Score"]
        header_fill = PatternFill(start_color="1a365d", end_color="1a365d", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        
        for row_num, feedback in enumerate(feedback_list, 2):
            data = feedback.to_dict()
            ws.cell(row=row_num, column=1, value=data['id']).border = thin_border
            ws.cell(row=row_num, column=2, value=data['created_at']).border = thin_border
            ws.cell(row=row_num, column=3, value=data['feedback_type']).border = thin_border
            ws.cell(row=row_num, column=4, value=data['reasons']).border = thin_border
            ws.cell(row=row_num, column=5, value=data['feedback_text']).border = thin_border
            ws.cell(row=row_num, column=6, value=data['venue']).border = thin_border
            ws.cell(row=row_num, column=7, value=data['match_format']).border = thin_border
            ws.cell(row=row_num, column=8, value=data['current_score']).border = thin_border
            ws.cell(row=row_num, column=9, value=data['predicted_score']).border = thin_border
        
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 40
        ws.column_dimensions['E'].width = 50
        ws.column_dimensions['F'].width = 25
        ws.column_dimensions['G'].width = 15
        ws.column_dimensions['H'].width = 15
        ws.column_dimensions['I'].width = 15
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='prediction_feedback.xlsx'
        )
    except Exception as e:
        app.logger.error(f"Excel export error: {str(e)}")
        flash(f"Error exporting feedback: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/feedback", methods=["GET"])
def view_feedback():
    """View all feedback in a simple dashboard"""
    feedback_list = PredictionFeedback.query.order_by(PredictionFeedback.created_at.desc()).limit(100).all()
    total_feedback = PredictionFeedback.query.count()
    positive_count = PredictionFeedback.query.filter_by(is_positive=True).count()
    negative_count = PredictionFeedback.query.filter_by(is_positive=False).count()
    
    return render_template(
        "feedback_dashboard.html",
        feedback_list=feedback_list,
        total_feedback=total_feedback,
        positive_count=positive_count,
        negative_count=negative_count
    )


@app.before_request
def track_page_view():
    """Track page views for analytics"""
    excluded_paths = ['/static/', '/api/', '/analytics', '/favicon']
    if any(request.path.startswith(p) for p in excluded_paths):
        return
    if request.method != 'GET':
        return
    try:
        PageView.log_view(request)
    except Exception as e:
        app.logger.error(f"Error logging page view: {e}")


def _is_admin():
    """Return True only for the designated developer/admin account."""
    import os
    admin_id = os.environ.get('ADMIN_USER_ID', '')
    return current_user.is_authenticated and str(current_user.id) == admin_id


@app.route("/accuracy", methods=["GET"])
def accuracy_dashboard():
    """Prediction accuracy stats — admin only."""
    if not current_user.is_authenticated:
        return redirect(url_for('login_and_redirect', next='/accuracy'))
    if not _is_admin():
        abort(404)
    from learning_engine import get_accuracy_stats, run_learning_cycle
    force_learn = request.args.get('relearn') == '1'
    if force_learn:
        run_learning_cycle()
        flash("Learning cycle complete.", "success")
        return redirect(url_for('accuracy_dashboard'))
    stats = get_accuracy_stats()
    return render_template(
        "accuracy_dashboard.html",
        stats=stats,
        venues=EXTENDED_VENUES,
        formats=[
            ("mens_t20", "Men's T20"),
            ("womens_t20", "Women's T20"),
            ("mens_odi", "Men's ODI"),
            ("womens_odi", "Women's ODI"),
        ],
        is_admin=True,
    )


@app.route("/accuracy/override", methods=["POST"])
def accuracy_override():
    """Admin: manually record or correct a match outcome."""
    if not _is_admin():
        abort(404)
    try:
        from learning_engine import record_match_outcome
        from models import MatchOutcome
        match_id = request.form.get("match_id", "").strip()
        venue = request.form.get("venue", "").strip()
        match_format = request.form.get("match_format", "mens_t20")
        final_score = request.form.get("final_score", "").strip()
        wickets = request.form.get("wickets", "").strip()

        if not match_id or not venue or not final_score:
            flash("Match ID, venue, and final score are all required.", "error")
            return redirect(url_for('accuracy_dashboard'))

        final_score = int(final_score)
        wickets = int(wickets) if wickets else 10

        # If an outcome already exists for this match_id, update it
        existing = MatchOutcome.query.filter_by(match_id=match_id).first()
        if existing:
            existing.venue = venue
            existing.match_format = match_format
            existing.final_score = final_score
            existing.wickets = wickets
            existing.source = 'manual'
            existing.confirmed_at = datetime.utcnow()
            # Backfill predictions too
            from models import Prediction
            preds = Prediction.query.filter_by(match_id=match_id).all()
            for p in preds:
                p.actual_final_score = final_score
                p.actual_wickets = wickets
            db.session.commit()
            flash(f"Outcome for '{match_id}' updated ({final_score}/{wickets} at {venue}).", "success")
        else:
            record_match_outcome(match_id, venue, match_format, final_score, wickets, source='manual')
            flash(f"Outcome recorded for '{match_id}' ({final_score}/{wickets} at {venue}).", "success")
    except ValueError:
        flash("Invalid score or wickets value — must be whole numbers.", "error")
    except Exception as e:
        flash(f"Error saving override: {e}", "error")
    return redirect(url_for('accuracy_dashboard'))


@app.route("/accuracy/outcome/<int:outcome_id>/delete", methods=["POST"])
def accuracy_delete_outcome(outcome_id):
    """Admin: delete a recorded match outcome."""
    if not _is_admin():
        flash("You must be logged in to delete outcomes.", "error")
        return redirect(url_for('accuracy_dashboard'))
    try:
        from models import MatchOutcome, Prediction
        outcome = MatchOutcome.query.get_or_404(outcome_id)
        match_id = outcome.match_id
        # Clear backfilled actuals on linked predictions
        preds = Prediction.query.filter_by(match_id=match_id).all()
        for p in preds:
            p.actual_final_score = None
            p.actual_wickets = None
        db.session.delete(outcome)
        db.session.commit()
        flash(f"Outcome for '{match_id}' deleted.", "success")
    except Exception as e:
        flash(f"Error deleting outcome: {e}", "error")
    return redirect(url_for('accuracy_dashboard'))


@app.route("/analytics", methods=["GET"])
def analytics_dashboard():
    """View traffic analytics dashboard"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, distinct
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    total_views = PageView.query.count()
    total_unique = db.session.query(func.count(distinct(PageView.ip_hash))).scalar() or 0
    
    today_views = PageView.query.filter(PageView.created_at >= today_start).count()
    today_unique = db.session.query(func.count(distinct(PageView.ip_hash))).filter(PageView.created_at >= today_start).scalar() or 0
    
    week_views = PageView.query.filter(PageView.created_at >= week_ago).count()
    week_unique = db.session.query(func.count(distinct(PageView.ip_hash))).filter(PageView.created_at >= week_ago).scalar() or 0
    
    month_views = PageView.query.filter(PageView.created_at >= month_ago).count()
    
    top_pages = db.session.query(
        PageView.path,
        func.count(PageView.id).label('views')
    ).group_by(PageView.path).order_by(func.count(PageView.id).desc()).limit(10).all()
    
    browser_stats = db.session.query(
        PageView.browser,
        func.count(PageView.id).label('count')
    ).group_by(PageView.browser).order_by(func.count(PageView.id).desc()).all()
    
    device_stats = db.session.query(
        PageView.device_type,
        func.count(PageView.id).label('count')
    ).group_by(PageView.device_type).order_by(func.count(PageView.id).desc()).all()
    
    daily_views = db.session.query(
        func.date(PageView.created_at).label('date'),
        func.count(PageView.id).label('views'),
        func.count(distinct(PageView.ip_hash)).label('unique')
    ).filter(PageView.created_at >= week_ago).group_by(func.date(PageView.created_at)).order_by(func.date(PageView.created_at)).all()
    
    recent_views = PageView.query.order_by(PageView.created_at.desc()).limit(20).all()
    
    return render_template(
        "analytics_dashboard.html",
        total_views=total_views,
        total_unique=total_unique,
        today_views=today_views,
        today_unique=today_unique,
        week_views=week_views,
        week_unique=week_unique,
        month_views=month_views,
        top_pages=top_pages,
        browser_stats=browser_stats,
        device_stats=device_stats,
        daily_views=daily_views,
        recent_views=recent_views
    )


@app.route("/api/venue-timezone")
def api_venue_timezone():
    """Return the IANA timezone string for a given venue name."""
    venue = request.args.get("venue", "")
    tz = get_venue_timezone(venue)
    return jsonify({"timezone": tz, "venue": venue})

@app.route("/prematch", methods=["GET", "POST"])
def prematch():
    """Render pre-match analysis page with venue conditions, par scores, and toss advice."""
    venues_by_country = get_venues_by_country()

    if request.method == "GET":
        return render_template("prematch.html",
                               venues=ALL_VENUES,
                               venues_by_country=venues_by_country,
                               analysis=None)

    venue = request.form.get("venue", "")
    match_format = request.form.get("match_format", "mens_t20")
    match_time = request.form.get("match_time", "")
    team1 = request.form.get("team1", "").strip()
    team2 = request.form.get("team2", "").strip()

    if match_format not in FORMAT_CONFIG:
        match_format = "mens_t20"

    if not venue or venue not in ALL_VENUES:
        flash("Please select a valid venue", "error")
        return redirect(url_for("prematch"))

    analysis = build_prematch_analysis(
        venue=venue,
        match_format=match_format,
        match_time=match_time if match_time else None,
        team1=team1 if team1 else None,
        team2=team2 if team2 else None
    )

    return render_template("prematch.html",
                           venues=ALL_VENUES,
                           venues_by_country=venues_by_country,
                           analysis=analysis)


@app.route("/insights", methods=["GET", "POST"])
def insights():
    """Render dismissal insights page predicting how batsmen may get out."""
    all_players = get_all_players_including_discovered()
    venues_by_country = get_venues_by_country()

    if request.method == "GET":
        return render_template("insights.html",
                               venues=ALL_VENUES,
                               venues_by_country=venues_by_country,
                               all_players=all_players,
                               insights_data=None)

    venue = request.form.get("venue", "")
    current_score = int(request.form.get("current_score", 0))
    wickets = int(request.form.get("wickets_fallen", 0))
    overs = float(request.form.get("overs_completed", 0))
    next_bowler = request.form.get("next_over_bowler", "")
    innings = int(request.form.get("innings", 1))
    target = int(request.form.get("target", 0)) if request.form.get("target") else 0
    match_format = request.form.get("match_format", "mens_t20")

    if match_format not in FORMAT_CONFIG:
        match_format = "mens_t20"

    format_config = FORMAT_CONFIG[match_format]
    max_overs = format_config['max_overs']

    if current_score < 0:
        flash("Current score cannot be negative", "error")
        return redirect(url_for("insights"))
    if wickets < 0 or wickets >= 10:
        flash("Wickets must be between 0 and 9", "error")
        return redirect(url_for("insights"))
    if overs < 0 or overs >= max_overs:
        flash(f"Overs must be between 0 and {max_overs - 1}.5", "error")
        return redirect(url_for("insights"))
    overs_decimal = overs - int(overs)
    if overs_decimal >= 0.6:
        flash(f"Invalid overs format: {overs}. Valid decimals are .0 to .5", "error")
        return redirect(url_for("insights"))
    if innings == 2 and target > 0 and current_score >= target:
        flash("Score already exceeds target", "error")
        return redirect(url_for("insights"))

    batsmen_list = []
    for i in range(1, 3):
        name = request.form.get(f"batsman{i}_name", "")
        runs = int(request.form.get(f"batsman{i}_runs", 0) or 0)
        balls = int(request.form.get(f"batsman{i}_balls", 0) or 0)
        if name:
            batsmen_list.append({'name': name, 'runs': runs, 'balls_faced': balls})

    if not batsmen_list:
        flash("Please select at least one batsman for insights", "error")
        return redirect(url_for("insights"))

    if not next_bowler:
        flash("Please select the current bowler", "error")
        return redirect(url_for("insights"))

    if not venue or venue not in ALL_VENUES:
        flash("Please select a valid venue", "error")
        return redirect(url_for("insights"))

    insights_data = build_match_insights(
        batsmen=batsmen_list,
        bowler_name=next_bowler,
        venue=venue,
        overs=overs,
        wickets=wickets,
        current_score=current_score,
        target=target,
        innings=innings,
        match_format=match_format
    )

    from prediction import get_venue_conditions
    from ipl_stats import get_venue_weather, get_pitch_tempo
    venue_conditions = get_venue_conditions(venue)
    weather_data = get_venue_weather(venue)
    pitch_tempo = get_pitch_tempo(venue)

    format_labels = {
        'mens_t20': "Men's T20",
        'womens_t20': "Women's T20",
        'mens_odi': "Men's ODI",
        'womens_odi': "Women's ODI"
    }

    return render_template("insights.html",
                           venues=ALL_VENUES,
                           venues_by_country=venues_by_country,
                           all_players=all_players,
                           insights_data=insights_data,
                           venue=venue,
                           venue_conditions=venue_conditions,
                           current_score=current_score,
                           wickets=wickets,
                           overs=overs,
                           next_bowler=next_bowler,
                           innings=innings,
                           target=target,
                           match_format=match_format,
                           format_label=format_labels.get(match_format, "T20"),
                           weather_data=weather_data,
                           pitch_tempo=pitch_tempo,
                           form_data=dict(request.form))


@app.route("/bug-report", methods=["GET", "POST"])
def bug_report():
    """Handle bug report submission with optional screenshot and email notification."""
    if request.method == "GET":
        return render_template("bug_report.html")

    import os
    import json
    import uuid

    category = request.form.get("category", "Bug")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    contact_email = request.form.get("contact_email", "").strip() or None
    
    if contact_email:
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]*[a-zA-Z][a-zA-Z0-9.-]*\.[a-zA-Z]{2,6}$', contact_email):
            is_ajax_check = (request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                       or request.accept_mimetypes.best == 'application/json'
                       or request.headers.get('Sec-Fetch-Mode') in ('cors', 'no-cors')
                       or 'fetch' in request.headers.get('Sec-Fetch-Dest', ''))
            if is_ajax_check:
                return jsonify({"success": False, "error": "The email address you entered doesn't look right. Please check it and try again."}), 400
            flash("The email address you entered doesn't look right. Please check it and try again.", "warning")
            return redirect(url_for('bug_report'))
    
    include_diagnostics = "include_diagnostics" in request.form

    is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest'
               or request.accept_mimetypes.best == 'application/json'
               or request.headers.get('Sec-Fetch-Mode') in ('cors', 'no-cors')
               or 'fetch' in request.headers.get('Sec-Fetch-Dest', ''))

    if not title or not description:
        if is_ajax:
            return jsonify({"success": False, "error": "Title and description are required."}), 400
        flash("Title and description are required.", "error")
        return redirect(url_for('bug_report'))

    diagnostics_data = None
    if include_diagnostics:
        diagnostics_data = json.dumps({
            "url": request.form.get("diagnostics_url", ""),
            "user_agent": request.form.get("diagnostics_ua", ""),
            "screen": request.form.get("diagnostics_screen", ""),
            "timestamp": request.form.get("diagnostics_time", "")
        })

    screenshot_filename = None
    screenshot = request.files.get("screenshot")
    if screenshot and screenshot.filename:
        from werkzeug.utils import secure_filename as wz_secure
        ext = wz_secure(screenshot.filename).rsplit(".", 1)[-1].lower()
        if ext in ("png", "jpg", "jpeg", "webp"):
            screenshot.seek(0, 2)
            file_size = screenshot.tell()
            screenshot.seek(0)
            if file_size <= 5 * 1024 * 1024:
                upload_dir = os.path.join(app.root_path, "static", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                screenshot_filename = f"{uuid.uuid4().hex[:12]}.{ext}"
                screenshot.save(os.path.join(upload_dir, screenshot_filename))

    username = None
    if current_user.is_authenticated:
        username = current_user.display_name

    report = BugReport(
        category=category,
        title=title[:80],
        description=description[:4000],
        contact_email=contact_email,
        include_diagnostics=include_diagnostics,
        diagnostics_data=diagnostics_data,
        screenshot_filename=screenshot_filename,
        username=username
    )
    db.session.add(report)
    db.session.commit()

    if is_ajax:
        response = jsonify({"success": True})
    else:
        flash("Feedback submitted successfully! Thank you.", "success")
        response = redirect(url_for('bug_report'))

    if contact_email:
        try:
            from email_responder import send_bug_report_reply
            send_bug_report_reply(
                to_email=contact_email,
                category=category,
                title=title,
                description=description
            )
        except Exception as email_err:
            app.logger.error(f"Bug report auto-reply email error: {email_err}")

    return response


@app.route("/login-redirect")
def login_and_redirect():
    """Redirect authenticated users to next_url or initiate Replit OAuth login."""
    next_url = request.args.get("next", "/")
    if current_user.is_authenticated:
        return redirect(next_url)
    session["next_url"] = request.url_root.rstrip("/") + next_url
    return redirect(url_for('replit_auth.login'))


@app.route("/support-chat")
def support_chat():
    """Render the AI-powered support chat page with session and CSRF management."""
    import uuid
    from datetime import datetime, timedelta

    if not current_user.is_authenticated:
        return render_template("support_chat.html", login_required=True,
                               login_url=url_for('login_and_redirect', next='/support-chat'))

    chat_session_id = session.get('chat_session_id')
    if not chat_session_id:
        chat_session_id = uuid.uuid4().hex
        session['chat_session_id'] = chat_session_id

    if 'chat_csrf' not in session:
        session['chat_csrf'] = uuid.uuid4().hex

    history = SupportChat.query.filter_by(session_id=chat_session_id).order_by(SupportChat.created_at.asc()).all()

    WEEKLY_LIMIT = 50
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)
    if current_user.is_authenticated:
        used = SupportChat.query.filter(
            SupportChat.user_id == current_user.id,
            SupportChat.role == 'user',
            SupportChat.created_at >= week_start
        ).count()
    else:
        used = SupportChat.query.filter(
            SupportChat.session_id == chat_session_id,
            SupportChat.role == 'user',
            SupportChat.created_at >= week_start
        ).count()

    remaining = max(0, WEEKLY_LIMIT - used)

    oldest_msg = None
    if used > 0:
        if current_user.is_authenticated:
            oldest_msg = SupportChat.query.filter(
                SupportChat.user_id == current_user.id,
                SupportChat.role == 'user',
                SupportChat.created_at >= week_start
            ).order_by(SupportChat.created_at.asc()).first()
        else:
            oldest_msg = SupportChat.query.filter(
                SupportChat.session_id == chat_session_id,
                SupportChat.role == 'user',
                SupportChat.created_at >= week_start
            ).order_by(SupportChat.created_at.asc()).first()

    renews_at = None
    if oldest_msg:
        renews_at = (oldest_msg.created_at + timedelta(days=7)).isoformat() + "Z"

    return render_template("support_chat.html", history=history, csrf_token=session['chat_csrf'],
                           remaining=remaining, weekly_limit=WEEKLY_LIMIT, renews_at=renews_at,
                           login_required=False)


@app.route("/api/support-chat", methods=["POST"])
def api_support_chat():
    """Process a user chat message and return an AI-generated support response."""
    import uuid
    import os
    from datetime import datetime, timedelta
    from email_responder import generate_chat_reply
    from werkzeug.utils import secure_filename

    if not current_user.is_authenticated:
        return jsonify({"error": "login_required",
                        "message": "Please sign in to use the support chat."}), 401

    if request.content_type and 'multipart/form-data' in request.content_type:
        token = request.form.get("csrf_token", "")
        user_message = (request.form.get("message") or "").strip()
        attachment = request.files.get("attachment")
    else:
        data = request.get_json(silent=True) or {}
        token = data.get("csrf_token", "")
        user_message = (data.get("message") or "").strip()
        attachment = None

    if not token or token != session.get('chat_csrf'):
        return jsonify({"error": "Invalid request."}), 403

    if not user_message and not attachment:
        return jsonify({"error": "Please provide a message or attachment."}), 400
    if len(user_message) > 1000:
        return jsonify({"error": "Message too long (max 1000 characters)."}), 400

    MAX_FILE_SIZE = 10 * 1024 * 1024
    saved_filename = None
    original_name = None
    if attachment and attachment.filename:
        original_name = attachment.filename
        file_data = attachment.read()
        if len(file_data) > MAX_FILE_SIZE:
            return jsonify({"error": "File too large. Maximum size is 10 MB."}), 400
        attachment.seek(0)
        ext = os.path.splitext(secure_filename(original_name))[1].lower()
        saved_filename = uuid.uuid4().hex + ext
        upload_path = os.path.join("static", "chat_uploads", saved_filename)
        attachment.save(upload_path)

    chat_session_id = session.get('chat_session_id')
    if not chat_session_id:
        chat_session_id = uuid.uuid4().hex
        session['chat_session_id'] = chat_session_id

    username = None
    user_id = None
    if current_user.is_authenticated:
        username = current_user.display_name
        user_id = current_user.id

    WEEKLY_LIMIT = 50
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)
    if current_user.is_authenticated:
        used = SupportChat.query.filter(
            SupportChat.user_id == current_user.id,
            SupportChat.role == 'user',
            SupportChat.created_at >= week_start
        ).count()
    else:
        used = SupportChat.query.filter(
            SupportChat.session_id == chat_session_id,
            SupportChat.role == 'user',
            SupportChat.created_at >= week_start
        ).count()

    if used >= WEEKLY_LIMIT:
        if saved_filename:
            try:
                os.remove(os.path.join("static", "chat_uploads", saved_filename))
            except OSError:
                pass
        oldest_msg = None
        if current_user.is_authenticated:
            oldest_msg = SupportChat.query.filter(
                SupportChat.user_id == current_user.id,
                SupportChat.role == 'user',
                SupportChat.created_at >= week_start
            ).order_by(SupportChat.created_at.asc()).first()
        else:
            oldest_msg = SupportChat.query.filter(
                SupportChat.session_id == chat_session_id,
                SupportChat.role == 'user',
                SupportChat.created_at >= week_start
            ).order_by(SupportChat.created_at.asc()).first()

        renews_at = None
        if oldest_msg:
            renews_at = (oldest_msg.created_at + timedelta(days=7)).isoformat() + "Z"

        return jsonify({"error": "You've reached the weekly limit of 50 messages. Your quota renews soon — check back later!",
                        "quota_exceeded": True, "remaining": 0, "renews_at": renews_at}), 429

    display_message = user_message if user_message else ""
    if saved_filename and not user_message:
        display_message = f"[Attached: {original_name}]"

    user_entry = SupportChat(
        session_id=chat_session_id,
        user_id=user_id,
        username=username,
        role="user",
        message=display_message,
        attachment_filename=saved_filename,
        attachment_original_name=original_name
    )
    db.session.add(user_entry)
    db.session.commit()

    history = SupportChat.query.filter_by(session_id=chat_session_id).order_by(SupportChat.created_at.asc()).all()
    conv = []
    for h in history:
        entry = {"role": h.role, "message": h.message}
        if h.attachment_filename and h.role == 'user':
            entry["attachment"] = {
                "path": os.path.join("static", "chat_uploads", h.attachment_filename),
                "original_name": h.attachment_original_name or h.attachment_filename,
                "filename": h.attachment_filename
            }
        conv.append(entry)

    ai_reply = generate_chat_reply(conv, user_name=username)
    if not ai_reply:
        ai_reply = "Sorry, I'm having trouble responding right now. Please try again in a moment!"

    ai_entry = SupportChat(
        session_id=chat_session_id,
        user_id=user_id,
        username="CricPredictor AI",
        role="assistant",
        message=ai_reply
    )
    db.session.add(ai_entry)
    db.session.commit()

    new_remaining = max(0, WEEKLY_LIMIT - (used + 1))
    renews_at = None
    oldest_msg = None
    if current_user.is_authenticated:
        oldest_msg = SupportChat.query.filter(
            SupportChat.user_id == current_user.id,
            SupportChat.role == 'user',
            SupportChat.created_at >= week_start
        ).order_by(SupportChat.created_at.asc()).first()
    else:
        oldest_msg = SupportChat.query.filter(
            SupportChat.session_id == chat_session_id,
            SupportChat.role == 'user',
            SupportChat.created_at >= week_start
        ).order_by(SupportChat.created_at.asc()).first()
    if oldest_msg:
        renews_at = (oldest_msg.created_at + timedelta(days=7)).isoformat() + "Z"

    attachment_info = None
    if saved_filename:
        attachment_info = {
            "url": "/static/chat_uploads/" + saved_filename,
            "name": original_name,
            "is_image": ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
        }

    return jsonify({"reply": ai_reply, "remaining": new_remaining, "renews_at": renews_at, "attachment": attachment_info})


@app.route("/api/support-chat/clear", methods=["POST"])
def api_support_chat_clear():
    """Reset the chat session by generating a new session ID."""
    import uuid
    data = request.get_json(silent=True) or {}
    token = data.get("csrf_token", "")
    if not token or token != session.get('chat_csrf'):
        return jsonify({"error": "Invalid request."}), 403
    session['chat_session_id'] = uuid.uuid4().hex
    return jsonify({"success": True})


HUB_PAGES = {
    "ipl-predictions": {
        "meta_title": "IPL Score Predictions 2025 – AI Cricket Match Predictor",
        "meta_desc": "Get AI-powered IPL score predictions for every match. Predict final scores, wickets, and win probability for RCB, CSK, MI, KKR and all IPL teams.",
        "title": "IPL Score Predictions",
        "subtitle": "AI-powered final score forecasts for every Indian Premier League match — powered by live data and a 705+ player database.",
        "intro": "The Indian Premier League is the highest-scoring T20 competition in the world, with flat pitches, short boundaries, and the best T20 specialists in one place. Use Cricket Match Intelligence to predict final scores for any IPL match in real time.",
        "cta_url": "/?format=mens_t20",
        "cta_text": "Predict an IPL Match",
        "related": [
            {"url": "/rcb-vs-csk", "label": "RCB vs CSK Prediction"},
            {"url": "/t20-predictions", "label": "T20 Score Predictor"},
            {"url": "/india-vs-australia-prediction", "label": "India vs Australia"},
        ],
        "sections": [
            {
                "icon": "bi-trophy-fill",
                "heading": "Why IPL Scoring is Different",
                "bullets": [
                    "Average T20 score in IPL is 163–170, significantly higher than international T20s (155–162).",
                    "Wankhede, Chinnaswamy, and Eden Gardens are historically the highest-scoring grounds.",
                    "Death-over specialists like Bumrah, Boult, and Chahal have specific economy profiles built into the engine.",
                    "The model applies IPL-specific venue multipliers for 12 IPL stadiums.",
                ]
            },
            {
                "icon": "bi-bar-chart-fill",
                "heading": "How IPL Predictions Work",
                "body": "Enter the current score, overs bowled, wickets fallen, and active bowlers. The AI engine reads the current run rate, momentum, pitch conditions, and wickets in hand to project the final total. For chases, it also calculates win probability based on the required run rate curve."
            },
            {
                "icon": "bi-star-fill",
                "heading": "Popular IPL Matchups",
                "cards": [
                    {"badge": "CSK vs MI", "badge_color": "#f5a623", "title": "Chennai vs Mumbai", "body": "Two most successful IPL franchises. Wankhede pitches favour batsmen; Chepauk favours spin."},
                    {"badge": "RCB vs KKR", "badge_color": "#c0392b", "title": "Bangalore vs Kolkata", "body": "Chinnaswamy's short boundaries regularly produce 190+ totals. Eden Gardens favours pace."},
                    {"badge": "MI vs DC", "badge_color": "#1a6b3a", "title": "Mumbai vs Delhi", "body": "Wankhede vs Kotla — two very different pitch profiles producing contrasting scores."},
                ],
                "card_cols": "4"
            }
        ]
    },
    "rcb-vs-csk": {
        "meta_title": "RCB vs CSK Score Prediction – IPL Match AI Predictor",
        "meta_desc": "Predict RCB vs CSK IPL match scores with AI. Get final score forecasts, wicket predictions, and win probability for Royal Challengers vs Chennai Super Kings.",
        "title": "RCB vs CSK Score Prediction",
        "subtitle": "Royal Challengers Bengaluru vs Chennai Super Kings — one of cricket's greatest rivalries. Predict the score with AI.",
        "intro": "RCB vs CSK is consistently one of the most-watched IPL fixtures. Chinnaswamy Stadium's short square boundaries and Chepauk's spin-friendly surface make these two grounds produce contrasting match dynamics. The Cricket Match Intelligence engine accounts for both venue profiles when generating predictions.",
        "cta_url": "/?format=mens_t20",
        "cta_text": "Predict RCB vs CSK Now",
        "related": [
            {"url": "/ipl-predictions", "label": "All IPL Predictions"},
            {"url": "/t20-predictions", "label": "T20 Score Predictor"},
            {"url": "/india-vs-australia-prediction", "label": "India vs Australia"},
        ],
        "sections": [
            {
                "icon": "bi-geo-alt-fill",
                "heading": "Venue Impact on Scores",
                "cards": [
                    {"badge": "M. Chinnaswamy", "badge_color": "#c0392b", "title": "RCB Home Ground", "body": "One of the smallest grounds in IPL. Short boundaries and flat pitches regularly produce 200+ scores. Favours big-hitting batsmen."},
                    {"badge": "MA Chidambaram", "badge_color": "#f5a623", "title": "CSK Home Ground", "body": "Slower, spin-friendly surface. Scores typically 150–170. Off-spinners and leg-spinners extract significant turn."},
                ],
                "card_cols": "6"
            },
            {
                "icon": "bi-cpu",
                "heading": "What the Predictor Considers",
                "bullets": [
                    "Current score, overs bowled, and wickets fallen",
                    "Active batsmen's strike rates and balls faced (set batsman boost applied after 15 balls)",
                    "Bowler economy rates and overs remaining in spell",
                    "Venue-specific scoring multiplier (Chinnaswamy: flat/high-scoring; Chepauk: spin/moderate)",
                    "Wickets-in-hand acceleration for death overs when 0–3 wickets lost",
                ]
            }
        ]
    },
    "t20-predictions": {
        "meta_title": "T20 Score Predictor – AI Cricket Match Score Forecast",
        "meta_desc": "Predict T20 match scores instantly with AI. Supports Men's and Women's T20 internationals across 290+ venues. Get final score, wickets, and win probability.",
        "title": "T20 Score Predictor",
        "subtitle": "AI-powered score forecasting for Men's and Women's T20 internationals. Enter the match state — get a prediction in seconds.",
        "intro": "T20 cricket is the fastest-evolving format in the game. Scores, tactics, and player roles change rapidly. Cricket Match Intelligence uses a multi-phase statistical model to predict T20 final scores, wickets, and next-over performance based on the current match state.",
        "cta_url": "/?format=mens_t20",
        "cta_text": "Predict a T20 Match",
        "related": [
            {"url": "/ipl-predictions", "label": "IPL Score Predictions"},
            {"url": "/t20-world-cup-predictions", "label": "T20 World Cup Predictions"},
            {"url": "/rcb-vs-csk", "label": "RCB vs CSK Prediction"},
        ],
        "sections": [
            {
                "icon": "bi-bar-chart-steps",
                "heading": "T20 Phases & Scoring Patterns",
                "cards": [
                    {"badge": "Powerplay (0–6)", "badge_color": "#1565c0", "title": "High Variance Phase", "body": "Fielding restrictions allow aggressive batting. Top-order batsmen set the tone. Average: 7–9 RPO."},
                    {"badge": "Middle (7–15)", "badge_color": "#6a1f6e", "title": "Build or Accelerate", "body": "Depends on wickets in hand. Teams with 7+ wickets accelerate; those with 4–5 consolidate. Average: 7–8 RPO."},
                    {"badge": "Death (16–20)", "badge_color": "#b71c1c", "title": "Maximum Acceleration", "body": "Set batsmen and low wicket count can produce 12–15 RPO. Tail collapses modelled separately. Average: 9–12 RPO."},
                ],
                "card_cols": "4"
            },
            {
                "icon": "bi-globe",
                "heading": "Supported T20 Formats",
                "bullets": [
                    "Men's T20 Internationals — all ICC member nations",
                    "Women's T20 Internationals — 87 nations in database",
                    "IPL, BBL, and other franchise leagues (manual input)",
                    "T20 World Cup matches across all group stages and knockouts",
                ]
            }
        ]
    },
    "t20-world-cup-predictions": {
        "meta_title": "T20 World Cup Score Predictions – AI Match Predictor",
        "meta_desc": "Predict T20 World Cup match scores with AI. Get final score forecasts, wicket predictions, and win probability for all T20 WC fixtures.",
        "title": "T20 World Cup Score Predictions",
        "subtitle": "AI-powered match predictions for the ICC Men's and Women's T20 World Cup — every fixture, every venue.",
        "intro": "The ICC T20 World Cup brings together the world's best T20 sides across multiple venues with vastly different conditions. From low-scoring spinner's paradises to high-octane batting feasts, Cricket Match Intelligence accounts for every venue's unique profile when generating predictions.",
        "cta_url": "/?format=mens_t20",
        "cta_text": "Predict a World Cup Match",
        "related": [
            {"url": "/t20-predictions", "label": "T20 Score Predictor"},
            {"url": "/india-vs-australia-prediction", "label": "India vs Australia"},
            {"url": "/ipl-predictions", "label": "IPL Score Predictions"},
        ],
        "sections": [
            {
                "icon": "bi-geo-alt-fill",
                "heading": "Venue Profiles Matter Most at World Cups",
                "body": "World Cups are often decided by conditions as much as talent. The engine profiles each venue — pitch type, ground dimensions, average first-innings score, and historical batting/bowling balance — to generate venue-calibrated predictions rather than generic run-rate extrapolations."
            },
            {
                "icon": "bi-trophy-fill",
                "heading": "Key World Cup Matchups to Predict",
                "cards": [
                    {"badge": "IND vs PAK", "badge_color": "#1a6b3a", "title": "India vs Pakistan", "body": "The most-watched match in cricket. High-pressure dynamics, spin-friendly surfaces, and chasing teams historically struggle."},
                    {"badge": "AUS vs ENG", "badge_color": "#c0392b", "title": "Australia vs England", "body": "Ashes rivalry in T20 format. Both sides play aggressive cricket; high-scoring affairs are common."},
                    {"badge": "SA vs NZ", "badge_color": "#2980b9", "title": "South Africa vs New Zealand", "body": "Two consistent but unpredictable sides. Seam and pace-friendly conditions in most venues suit both attacks."},
                ],
                "card_cols": "4"
            }
        ]
    },
    "india-vs-australia-prediction": {
        "meta_title": "India vs Australia Score Prediction – AI Cricket Predictor",
        "meta_desc": "Predict India vs Australia cricket match scores with AI. Supports T20 and ODI formats across all venues. Get final score, wickets, and win probability.",
        "title": "India vs Australia Score Prediction",
        "subtitle": "One of cricket's premier rivalries — predict any India vs Australia match across T20 and ODI formats.",
        "intro": "India vs Australia is one of the most contested rivalries in international cricket, producing memorable matches across all formats. The Cricket Match Intelligence engine has detailed player profiles for all current Indian and Australian cricketers, with venue-specific data for their most common grounds.",
        "cta_url": "/",
        "cta_text": "Predict India vs Australia",
        "related": [
            {"url": "/t20-predictions", "label": "T20 Score Predictor"},
            {"url": "/t20-world-cup-predictions", "label": "T20 World Cup Predictions"},
            {"url": "/ipl-predictions", "label": "IPL Score Predictions"},
        ],
        "sections": [
            {
                "icon": "bi-bar-chart-fill",
                "heading": "Typical Scoring Patterns",
                "cards": [
                    {"badge": "T20 in India", "badge_color": "#1a6b3a", "title": "High-Scoring Affairs", "body": "Flat pitches at Wankhede, Eden Gardens, and Chinnaswamy regularly produce 180–200 totals. Australia's pace attack and India's batting depth make these contests high-variance."},
                    {"badge": "T20 in Australia", "badge_color": "#f5a623", "title": "Pace-Friendly Conditions", "body": "MCG, SCG, and Gabba have larger outfields. Scores typically 155–175. Australian fast bowlers thrive in home conditions."},
                    {"badge": "ODI Matches", "badge_color": "#2980b9", "title": "300+ Par Scores", "body": "Both sides are capable of posting 300+ in ODIs. Chases are common — the win probability model is particularly useful for ODI second innings."},
                ],
                "card_cols": "4"
            },
            {
                "icon": "bi-cpu",
                "heading": "Player Profiles in the Database",
                "bullets": [
                    "Indian batsmen: Rohit Sharma, Virat Kohli, Shubman Gill, KL Rahul, Hardik Pandya and 40+ more",
                    "Indian bowlers: Jasprit Bumrah, Mohammed Shami, Axar Patel, Kuldeep Yadav and more",
                    "Australian batsmen: David Warner, Travis Head, Steve Smith, Glenn Maxwell and more",
                    "Australian bowlers: Pat Cummins, Josh Hazlewood, Mitchell Starc, Adam Zampa and more",
                ]
            }
        ]
    }
}


@app.route("/ipl-predictions")
def hub_ipl():
    return render_template("hub_page.html", hub=HUB_PAGES["ipl-predictions"])


@app.route("/rcb-vs-csk")
def hub_rcb_csk():
    return render_template("hub_page.html", hub=HUB_PAGES["rcb-vs-csk"])


@app.route("/t20-predictions")
def hub_t20():
    return render_template("hub_page.html", hub=HUB_PAGES["t20-predictions"])


@app.route("/t20-world-cup-predictions")
def hub_t20_wc():
    return render_template("hub_page.html", hub=HUB_PAGES["t20-world-cup-predictions"])


@app.route("/india-vs-australia-prediction")
def hub_ind_aus():
    return render_template("hub_page.html", hub=HUB_PAGES["india-vs-australia-prediction"])


@app.route("/favicon.ico")
def favicon():
    """Serve favicon for browsers and Google search results."""
    return send_file("static/cricket_logo.svg", mimetype="image/svg+xml")


@app.route("/about")
def about():
    """About page with app description and creator info."""
    return render_template("about.html")


@app.route("/privacy-policy")
def privacy_policy():
    """Privacy policy page."""
    return render_template("privacy.html")


@app.route("/robots.txt")
def robots_txt():
    """Serve robots.txt for search engine crawlers."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        "Disallow: /auth/\n"
        "\n"
        "Sitemap: https://cricket-score-predictor.com/sitemap.xml\n"
    )
    from flask import Response
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Serve sitemap.xml listing all public pages for search engines."""
    base = "https://cricket-score-predictor.com"
    pages = [
        ("", "1.0", "daily"),
        ("/ipl-predictions", "0.95", "daily"),
        ("/t20-predictions", "0.95", "daily"),
        ("/t20-world-cup-predictions", "0.9", "weekly"),
        ("/india-vs-australia-prediction", "0.9", "weekly"),
        ("/rcb-vs-csk", "0.9", "weekly"),
        ("/demo", "0.85", "weekly"),
        ("/prematch", "0.8", "weekly"),
        ("/insights", "0.8", "weekly"),
        ("/about", "0.7", "monthly"),
        ("/privacy-policy", "0.5", "monthly"),
        ("/support-chat", "0.6", "monthly"),
    ]
    from flask import Response
    from datetime import date
    today = date.today().isoformat()
    urls = ""
    for path, priority, freq in pages:
        urls += (
            f"  <url>\n"
            f"    <loc>{base}{path}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>\n"
        )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}</urlset>"""
    return Response(xml, mimetype="application/xml")


# ===========================================================================
# MONETIZATION — Matchday Pro (Stripe subscriptions, event tracking, Pro features)
# ===========================================================================

from functools import wraps
import json as _json

def require_pro(f):
    """Decorator: redirect non-Pro users to the pricing page."""
    @wraps(f)
    def _inner(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = request.url
            return redirect(url_for('replit_auth.login'))
        if not current_user.is_pro:
            flash("This feature is part of Matchday Pro. Upgrade to unlock it.", "warning")
            _track_event("upgrade_clicked", {"source": request.path})
            return redirect(url_for('pricing'))
        return f(*args, **kwargs)
    return _inner


def _track_event(event_type: str, metadata: dict = None):
    """Persist a conversion event. Silently ignores DB errors."""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        ev = ConversionEvent(
            event_type=event_type,
            user_id=user_id,
            session_id=session.get("chat_session_id") or session.get("_id", ""),
            metadata=_json.dumps(metadata or {}),
        )
        db.session.add(ev)
        db.session.commit()
    except Exception:
        db.session.rollback()


# ---------------------------------------------------------------------------
# Public event tracking API (called from JS)
# ---------------------------------------------------------------------------

@app.route("/api/events/track", methods=["POST"])
def api_track_event():
    """Record a client-side funnel event.

    Body JSON: {"event_type": "prediction_completed", "metadata": {...}}
    """
    data = request.get_json(silent=True) or {}
    event_type = str(data.get("event_type", ""))[:60]
    metadata = data.get("metadata", {})
    if not event_type:
        return jsonify({"error": "event_type required"}), 400
    _track_event(event_type, metadata)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Pricing page
# ---------------------------------------------------------------------------

@app.route("/pricing")
def pricing():
    """Public pricing / upgrade page."""
    _track_event("pricing_viewed")
    from stripe_helper import PUBLISHABLE_KEY, is_configured
    return render_template(
        "pricing.html",
        stripe_publishable_key=PUBLISHABLE_KEY,
        stripe_configured=is_configured(),
    )


# ---------------------------------------------------------------------------
# Stripe checkout
# ---------------------------------------------------------------------------

@app.route("/subscribe", methods=["POST"])
def subscribe():
    """Create a Stripe Checkout session and redirect the user to it."""
    from replit_auth import require_login as _rl
    if not current_user.is_authenticated:
        session["next_url"] = url_for('pricing')
        return redirect(url_for('replit_auth.login'))

    from stripe_helper import create_checkout_session, is_configured
    if not is_configured():
        flash("Payment system is not configured yet. Please check back soon.", "warning")
        return redirect(url_for('pricing'))

    _track_event("upgrade_clicked", {"source": "subscribe_button"})

    success_url = url_for('subscription_success', _external=True) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = url_for('subscription_cancel', _external=True)

    try:
        checkout = create_checkout_session(current_user, success_url, cancel_url)
        return redirect(checkout.url, code=303)
    except Exception as e:
        flash(f"Could not start checkout: {e}", "danger")
        return redirect(url_for('pricing'))


@app.route("/subscription/success")
def subscription_success():
    """Post-checkout landing page. Stripe redirects here after payment."""
    _track_event("purchase_completed", {"session_id": request.args.get("session_id", "")})
    return render_template("subscription_success.html")


@app.route("/subscription/cancel")
def subscription_cancel():
    """Shown when user clicks 'back' on the Stripe checkout page."""
    return render_template("subscription_cancel.html")


@app.route("/subscription/portal", methods=["POST"])
def subscription_portal():
    """Redirect Pro user to Stripe Customer Portal to manage/cancel."""
    if not current_user.is_authenticated or not current_user.stripe_customer_id:
        return redirect(url_for('pricing'))

    from stripe_helper import create_portal_session
    portal = create_portal_session(
        current_user.stripe_customer_id,
        return_url=url_for('pricing', _external=True),
    )
    return redirect(portal.url, code=303)


# ---------------------------------------------------------------------------
# Stripe webhook (must NOT require login; uses raw body)
# ---------------------------------------------------------------------------

@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events to keep subscription status in sync."""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    from stripe_helper import handle_webhook, sync_subscription_to_user
    try:
        event = handle_webhook(payload, sig_header)
    except Exception as e:
        app.logger.warning("Stripe webhook error: %s", e)
        return jsonify({"error": str(e)}), 400

    obj = event["data"]["object"]

    if event["type"] in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        customer_id = obj.get("customer")
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            import stripe as _stripe
            sub = _stripe.Subscription.retrieve(obj["id"])
            sync_subscription_to_user(user, sub)

    elif event["type"] == "invoice.payment_succeeded":
        customer_id = obj.get("customer")
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user and not user.is_pro:
            user.is_pro = True
            db.session.commit()

    elif event["type"] == "invoice.payment_failed":
        customer_id = obj.get("customer")
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.subscription_status = "past_due"
            user.is_pro = False
            db.session.commit()

    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Pro: Saved Predictions
# ---------------------------------------------------------------------------

@app.route("/pro/predictions")
@require_pro
def pro_predictions():
    """Pro user saved-predictions history page."""
    saves = (SavedPrediction.query
             .filter_by(user_id=current_user.id)
             .order_by(SavedPrediction.created_at.desc())
             .limit(50)
             .all())
    return render_template("pro_predictions.html", saves=saves)


@app.route("/pro/predictions/save", methods=["POST"])
@require_pro
def pro_save_prediction():
    """Save the current prediction result for later review."""
    data = request.get_json(silent=True) or {}
    save = SavedPrediction(
        user_id=current_user.id,
        prediction_id=data.get("prediction_id"),
        venue=data.get("venue", "")[:100],
        match_format=data.get("match_format", "")[:20],
        predicted_score=data.get("predicted_score"),
        notes=data.get("notes", "")[:500],
        snapshot_json=_json.dumps(data.get("snapshot", {})),
    )
    db.session.add(save)
    db.session.commit()
    _track_event("prediction_saved", {"venue": save.venue})
    return jsonify({"ok": True, "id": save.id})


@app.route("/pro/predictions/<int:save_id>/actual", methods=["POST"])
@require_pro
def pro_update_actual(save_id):
    """Update a saved prediction with the real final score."""
    save = SavedPrediction.query.filter_by(id=save_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    save.actual_score = data.get("actual_score")
    save.notes = data.get("notes", save.notes or "")[:500]
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Pro: Match Alerts
# ---------------------------------------------------------------------------

@app.route("/pro/alerts", methods=["GET"])
@require_pro
def pro_alerts():
    """Pro user match-alert management page."""
    alerts = MatchAlert.query.filter_by(user_id=current_user.id).order_by(MatchAlert.created_at.desc()).all()
    from prediction import ALL_VENUES, FIELDING_TEAMS
    return render_template(
        "pro_alerts.html",
        alerts=alerts,
        all_venues=ALL_VENUES,
        all_teams=FIELDING_TEAMS,
        user_email=current_user.email or "",
    )


@app.route("/pro/alerts", methods=["POST"])
@require_pro
def pro_create_alert():
    """Create or update a match alert for the current Pro user."""
    data = request.form
    alert_email = data.get("alert_email", current_user.email or "").strip()
    teams = ",".join(request.form.getlist("teams"))
    venues = ",".join(request.form.getlist("venues"))
    formats = ",".join(request.form.getlist("formats"))

    if not alert_email:
        flash("Please provide an email address for alerts.", "warning")
        return redirect(url_for('pro_alerts'))

    alert = MatchAlert(
        user_id=current_user.id,
        alert_email=alert_email,
        teams=teams,
        venues=venues,
        formats=formats,
        is_active=True,
    )
    db.session.add(alert)
    db.session.commit()
    _track_event("alert_created", {"teams": teams, "venues": venues})
    flash("Match alert created! You'll receive emails before relevant matches.", "success")
    return redirect(url_for('pro_alerts'))


@app.route("/pro/alerts/<int:alert_id>/delete", methods=["POST"])
@require_pro
def pro_delete_alert(alert_id):
    """Delete a match alert."""
    alert = MatchAlert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    db.session.delete(alert)
    db.session.commit()
    flash("Alert deleted.", "info")
    return redirect(url_for('pro_alerts'))


# ---------------------------------------------------------------------------
# Conversion funnel in analytics dashboard (extend existing analytics route)
# ---------------------------------------------------------------------------

@app.route("/api/funnel")
def api_funnel():
    """Return conversion funnel counts for the analytics dashboard."""
    from sqlalchemy import func
    from datetime import timedelta, datetime
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    rows = (db.session.query(ConversionEvent.event_type, func.count(ConversionEvent.id))
            .filter(ConversionEvent.created_at >= thirty_days_ago)
            .group_by(ConversionEvent.event_type)
            .all())
    funnel = {r[0]: r[1] for r in rows}

    pro_count = User.query.filter_by(is_pro=True).count()
    total_users = User.query.count()

    return jsonify({
        "funnel_30d": funnel,
        "pro_subscribers": pro_count,
        "total_registered": total_users,
    })


# ---------------------------------------------------------------------------
# Backtest routes
# ---------------------------------------------------------------------------

_backtest_cache = {}


@app.route("/backtest")
def backtest_page():
    return render_template("backtest.html")


@app.route("/backtest/status")
def backtest_status():
    from backtest_data import get_data_info
    return jsonify(get_data_info())


@app.route("/backtest/run", methods=["POST"])
def backtest_run():
    from backtest import run_backtest, compute_metrics, generate_summary
    data = request.get_json(silent=True) or {}
    max_matches = min(int(data.get("max_matches", 100)), 2000)
    try:
        results = run_backtest(max_matches=max_matches)
        metrics = compute_metrics(results)
        summary = generate_summary(metrics)
        _backtest_cache["last"] = results
        return jsonify({"results": results, "metrics": metrics, "summary": summary})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/backtest/export.csv")
def backtest_export():
    import csv
    results = _backtest_cache.get("last", [])
    if not results:
        return "No backtest results cached. Run a backtest first.", 404
    output = io.StringIO()
    fields = [
        "match_id", "date", "venue", "batting_team", "checkpoint",
        "score_at_cp", "wickets_at_cp", "predicted", "pred_low", "pred_high",
        "actual", "error", "abs_error", "in_range", "range_width",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(results)
    output.seek(0)
    return send_file(
        io.BytesIO(output.read().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="backtest_results.csv",
    )
