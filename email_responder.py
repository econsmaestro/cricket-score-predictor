"""AI-powered email responder for user feedback and bug reports."""
import os
import logging
from openai import OpenAI
from gmail_helper import send_email, get_unread_replies, mark_as_read, send_reply

logger = logging.getLogger(__name__)

client = OpenAI(
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"),
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
)

APP_NAME = "Cricket Match Intelligence"

EMAIL_STYLE = ""

# Minimum character count before a submission is considered meaningful
_SPAM_MIN_LENGTH = 8
# If more than this fraction of characters are consonants with no spaces, likely gibberish
_SPAM_CONSONANT_RATIO = 0.75


def _is_spam(text):
    """Return True if text looks like nonsense/spam and should not trigger an email reply."""
    if not text:
        return True
    text = text.strip()
    if len(text) < _SPAM_MIN_LENGTH:
        return True
    # Single word (no spaces) with very high consonant ratio = likely gibberish
    if ' ' not in text:
        consonants = sum(1 for c in text.lower() if c in 'bcdfghjklmnpqrstvwxyz')
        if len(text) > 0 and consonants / len(text) >= _SPAM_CONSONANT_RATIO:
            return True
    # All the same character repeated
    if len(set(text.lower())) <= 2 and len(text) > 4:
        return True
    return False


def _generate_ai_reply(context_type, user_message, extra_context=None):
    """Generate an AI reply based on the feedback/report context."""
    if context_type == "positive_feedback":
        system_prompt = f"""You are writing a warm, genuine thank-you message on behalf of {APP_NAME}, a cricket score prediction app built by a 19-year-old developer.

Guidelines:
- This is purely a thank-you note — focus entirely on expressing gratitude
- Make it feel personal and heartfelt, not corporate
- 2-3 sentences max — short and sincere
- Mention that feedback like theirs keeps the project going
- Do NOT mention bugs, improvements, or ask for anything
- Do NOT include a subject line, greeting, or sign-off — the email template handles those
- Casual, warm tone — like a real person saying thank you"""
    else:
        system_prompt = f"""You are a friendly, professional customer support representative for {APP_NAME}, 
a cricket score prediction web application. Write a brief, warm email reply to a user who submitted feedback or a bug report.

Guidelines:
- Keep it concise (3-5 sentences max)
- Be genuinely grateful and specific about what they reported
- If it's a bug report, acknowledge the issue and assure them it will be looked into
- If it's negative feedback, empathize and explain that the feedback helps improve predictions
- Never make promises about specific timelines
- Do NOT include a subject line, greeting, or sign-off — the email template adds those automatically
- Write in a casual but professional tone"""

    user_prompt = f"Type: {context_type}\n"
    if extra_context:
        user_prompt += f"Context: {extra_context}\n"
    user_prompt += f"User's message: {user_message}"

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            timeout=15,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI email generation failed: {e}")
        return None


def _wrap_in_template(body_html, context_type):
    """Wrap the AI-generated text in a styled HTML email template."""
    if context_type == "bug_report":
        badge_text = "Bug Report Received"
        subtitle = "We've received your report and will look into it"
    elif context_type == "positive_feedback":
        badge_text = "Thank You! 🙏"
        subtitle = "It means a lot to hear from you"
    elif context_type == "conversation_reply":
        badge_text = "CricPredictor Support"
        subtitle = "Thanks for getting back to us"
    else:
        badge_text = "Feedback Received"
        subtitle = "Your input helps us improve our predictions"

    paragraphs = body_html.split('\n')
    formatted_body = ''.join(f'<p style="margin:0 0 12px;color:#333;font-size:15px;line-height:1.6;">{p.strip()}</p>' for p in paragraphs if p.strip())

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;margin:0;padding:20px;background:#ffffff;">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;">
    <tr>
        <td style="padding:20px 0;border-bottom:2px solid #1a365d;">
            <strong style="font-size:18px;color:#1a365d;">CricPredictor</strong>
            <br><span style="font-size:13px;color:#666;">{subtitle}</span>
        </td>
    </tr>
    <tr>
        <td style="padding:20px 0;">
            {formatted_body}
            <p style="margin-top:18px;color:#888;font-size:13px;">
                Best regards,<br>The CricPredictor Team
            </p>
        </td>
    </tr>
    <tr>
        <td style="padding:14px 0;border-top:1px solid #eee;text-align:center;font-size:11px;color:#999;">
            This is an automated response — please do not reply to this email.<br>
            For further help, use the Feedback form on our website.
        </td>
    </tr>
</table>
</body>
</html>"""


def send_feedback_reply(to_email, is_positive, feedback_text, venue=None, match_format=None, predicted_score=None):
    """Send an AI-generated reply to a user who submitted prediction feedback."""
    if not to_email:
        return False
    if _is_spam(feedback_text):
        logger.info(f"Skipping feedback reply — spam/nonsense detected: {repr(feedback_text)}")
        return False

    context_type = "positive_feedback" if is_positive else "negative_feedback"

    extra_parts = []
    if venue:
        extra_parts.append(f"Venue: {venue}")
    if match_format:
        extra_parts.append(f"Format: {match_format}")
    if predicted_score:
        extra_parts.append(f"Predicted score: {predicted_score}")
    extra_context = ", ".join(extra_parts) if extra_parts else None

    user_message = feedback_text or ("Thumbs up - great prediction!" if is_positive else "Thumbs down - prediction was off")

    ai_body = _generate_ai_reply(context_type, user_message, extra_context)
    if not ai_body:
        return False

    subject = "CricPredictor Feedback"
    html_body = _wrap_in_template(ai_body, context_type)

    return send_email(to_email, subject, html_body, plain_body=ai_body)


def send_bug_report_reply(to_email, category, title, description):
    """Send an AI-generated reply to a user who submitted a bug report."""
    if not to_email:
        return False
    if _is_spam(title) and _is_spam(description):
        logger.info(f"Skipping bug report reply — spam/nonsense detected: title={repr(title)}, desc={repr(description)}")
        return False

    extra_context = f"Category: {category}, Title: {title}"
    ai_body = _generate_ai_reply("bug_report", description, extra_context)
    if not ai_body:
        return False

    subject = "CricPredictor Feedback"
    html_body = _wrap_in_template(ai_body, "bug_report")

    return send_email(to_email, subject, html_body, plain_body=ai_body)


def _generate_conversation_reply(user_message, user_name=None):
    """Generate an AI reply for a user who replied to a CricPredictor email."""
    system_prompt = f"""You are a friendly, professional customer support representative for {APP_NAME}, 
a cricket score prediction web application. A user has replied to an automated email from your system.

Guidelines:
- Keep it concise (2-4 sentences max)
- Be helpful and conversational
- If they say thanks or acknowledge, respond warmly and briefly
- If they ask a question about the app, answer helpfully based on what you know (cricket prediction app with T20/ODI support)
- If they report another issue, acknowledge it and say the team will look into it
- If the message is very short (like "ok", "thanks", "will do"), keep your reply very brief (1-2 sentences)
- Never make promises about specific timelines or features
- Do NOT include a subject line, greeting, or sign-off — the email template adds those automatically
- Write in a casual but professional tone"""

    name_part = f" (from {user_name})" if user_name else ""
    user_prompt = f"User's reply{name_part}: {user_message}"

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            timeout=15,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"AI conversation reply generation failed: {e}")
        return None


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
TEXT_EXTENSIONS = {'.txt', '.csv', '.json', '.xml', '.html', '.css', '.js', '.py',
                   '.md', '.log', '.yaml', '.yml', '.ini', '.cfg', '.toml', '.sql',
                   '.sh', '.bat', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h',
                   '.rb', '.php', '.go', '.rs', '.swift', '.kt'}


def _read_file_content(file_path):
    """Read text content from a file for AI analysis."""
    try:
        with open(file_path, 'r', errors='replace') as f:
            content = f.read(10000)
        if len(content) >= 10000:
            content += "\n... [file truncated at 10,000 characters]"
        return content
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None


def _encode_image_base64(file_path):
    """Encode an image file to base64 data URI."""
    import base64
    import mimetypes
    try:
        mime_type = mimetypes.guess_type(file_path)[0] or 'image/png'
        with open(file_path, 'rb') as f:
            data = f.read()
        b64 = base64.b64encode(data).decode('utf-8')
        return f"data:{mime_type};base64,{b64}"
    except Exception as e:
        logger.error(f"Failed to encode image {file_path}: {e}")
        return None


def generate_chat_reply(conversation_history, user_name=None):
    """Generate an AI reply for the support chat widget.
    
    Args:
        conversation_history: list of dicts with 'role', 'message', and optional 'attachment' keys
            attachment dict: {'path': str, 'original_name': str, 'filename': str}
        user_name: optional display name
    
    Returns:
        AI response string or None on error
    """
    system_prompt = f"""You are Third Umpire AI — a knowledgeable, passionate cricket expert and support assistant built into {APP_NAME}, a cricket score prediction web application.

You have two equally important roles:
1. CRICKET COMPANION: Discuss anything cricket — players, matches, stats, history, tactics, formats, controversies, records, fantasy tips, IPL, international cricket, GOAT debates. Be like a knowledgeable friend who loves the game.
2. APP SUPPORT: Help users get the most out of {APP_NAME} — explain features, guide them to the right page, and handle bug reports.

About the app:
- Predicts final scores, wickets, and next-over performance for T20 and ODI cricket matches (Men's and Women's)
- Supports 100+ international venues, 530+ players including U19 youth
- Features: live match auto-fill, pre-match insights, dismissal mode analysis, venue pitch conditions

App Pages Directory — use these EXACT markdown links whenever relevant:
- Score Predictor (predict live/upcoming matches): [Score Predictor](/)
- Pre-Match Insights (venue, weather, par scores, surface analysis): [Pre-Match Insights](/prematch)
- Match Insights (dismissal mode predictions, player analysis): [Match Insights](/insights)
- Feedback Dashboard (view community feedback): [Feedback Dashboard](/feedback)
- Bug Report / Feedback Form: [Bug Report](/bug-report)
- Support Chat (this page): [Support Chat](/support-chat)

Guidelines:
- Be enthusiastic and conversational — warm, direct, like a knowledgeable fan
- CRITICAL: You do NOT have internet access. Never offer to "pull", "fetch", or "check" live data — you cannot do this and it misleads users. Answer directly using your training knowledge.
- CRITICAL: Always give a direct, substantive answer immediately. Never say "Want me to...?" or "Shall I...?" — just answer. If they want a shortlist, give it now. If they want a prediction, give it now.
- If your data may be outdated (e.g. live standings), briefly acknowledge it then give your best analysis anyway: "My data may not reflect the latest results, but based on form..."
- PROACTIVE APP LINKING: Whenever a cricket topic is relevant to an app feature, naturally mention it with a link. Examples:
  • Discussing a venue → "You can check pitch conditions and par scores at [Pre-Match Insights](/prematch)"
  • Discussing a match outcome → "Try simulating it yourself on the [Score Predictor](/)"
  • Discussing a player's dismissal pattern → "The [Match Insights](/insights) page analyses likely dismissal modes"
  • Discussing team tactics → "Run different scenarios on the [Score Predictor](/)"
- Keep replies focused — 3-6 sentences for simple questions, longer for deep dives when asked
- When asked about bugs or issues, acknowledge warmly and direct them to [Bug Report](/bug-report)
- Never make promises about timelines or upcoming features
- When users attach images, you CAN see and analyze them — describe what you see and respond helpfully
- When users attach text files, you CAN read the contents — analyze and respond to the content
- For other file types you cannot read, acknowledge the file by name and ask the user to describe it"""

    messages = [{"role": "system", "content": system_prompt}]
    use_vision = False

    for entry in conversation_history[-10:]:
        role = "user" if entry["role"] == "user" else "assistant"
        attachment = entry.get("attachment")

        if role == "user" and attachment:
            original_name = attachment.get("original_name", "")
            file_path = attachment.get("path", "")
            ext = os.path.splitext(original_name)[1].lower()

            content_parts = []
            if entry.get("message"):
                content_parts.append({"type": "text", "text": entry["message"]})

            if ext in IMAGE_EXTENSIONS and file_path:
                data_uri = _encode_image_base64(file_path)
                if data_uri:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": data_uri}
                    })
                    use_vision = True
                else:
                    content_parts.append({"type": "text", "text": f"[User attached image: {original_name} — could not load]"})
            elif ext in TEXT_EXTENSIONS and file_path:
                file_content = _read_file_content(file_path)
                if file_content:
                    content_parts.append({"type": "text", "text": f"[Attached file: {original_name}]\n```\n{file_content}\n```"})
                else:
                    content_parts.append({"type": "text", "text": f"[User attached file: {original_name} — could not read]"})
            else:
                content_parts.append({"type": "text", "text": f"[User attached file: {original_name}]"})

            if not content_parts:
                content_parts.append({"type": "text", "text": f"[User attached: {original_name}]"})

            messages.append({"role": role, "content": content_parts})
        else:
            messages.append({"role": role, "content": entry.get("message", "")})

    try:
        model = "gpt-4o-mini" if use_vision else "gpt-5-nano"
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=30,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Chat reply generation failed: {e}")
        return None


def process_incoming_replies():
    """Check for unread replies to CricPredictor emails and auto-respond.
    
    Returns:
        Number of replies processed
    """
    try:
        unread = get_unread_replies()
        if not unread:
            return 0
        
        processed = 0
        for msg in unread:
            try:
                body = msg['body'].strip()
                if not body:
                    body = msg['snippet']
                
                body_clean = body.split('\n')[0].strip() if body else ''
                if len(body_clean) > 500:
                    body_clean = body_clean[:500]
                
                ai_body = _generate_conversation_reply(body_clean, msg.get('from_name'))
                if not ai_body:
                    mark_as_read(msg['message_id'])
                    continue
                
                html_body = _wrap_in_template(ai_body, "conversation_reply")
                
                sent = send_reply(
                    to_email=msg['from_email'],
                    subject=msg['subject'],
                    html_body=html_body,
                    thread_id=msg['thread_id'],
                    message_id=msg['message_id'],
                    plain_body=ai_body
                )
                
                mark_as_read(msg['message_id'])
                
                if sent:
                    processed += 1
                    logger.info(f"Auto-replied to {msg['from_email']}")
                    
            except Exception as e:
                logger.error(f"Error processing reply from {msg.get('from_email')}: {e}")
                mark_as_read(msg['message_id'])
        
        return processed
    
    except Exception as e:
        logger.error(f"Error in process_incoming_replies: {e}")
        return 0
