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


def _generate_ai_reply(context_type, user_message, extra_context=None):
    """Generate an AI reply based on the feedback/report context."""
    system_prompt = f"""You are a friendly, professional customer support representative for {APP_NAME}, 
a cricket score prediction web application. Write a brief, warm email reply to a user who submitted feedback or a bug report.

Guidelines:
- Keep it concise (3-5 sentences max)
- Be genuinely grateful and specific about what they reported
- If it's a bug report, acknowledge the issue and assure them it will be looked into
- If it's positive feedback, thank them warmly
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
        badge_text = "Thank You!"
        subtitle = "Your feedback brightens our day"
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
    system_prompt = f"""You are a friendly, knowledgeable support assistant for {APP_NAME}, a cricket score prediction web application.

About the app:
- Predicts final scores, wickets, and next-over performance for T20 and ODI cricket matches (Men's and Women's)
- Supports 100+ international venues, 530+ players including U19 youth
- Features: live match auto-fill, pre-match insights, dismissal mode analysis, venue pitch conditions
- Has feedback/bug report forms and analytics dashboard

App Pages Directory (use these EXACT links when helping users find pages):
- Score Predictor (main page): [Score Predictor](/)
- Pre-Match Insights (venue analysis, weather, par scores): [Pre-Match Insights](/prematch)
- Match Insights (dismissal mode predictions): [Match Insights](/insights)
- Feedback Dashboard (view all feedback): [Feedback Dashboard](/feedback)
- Bug Report / Feedback Form: [Bug Report](/bug-report)
- Analytics Dashboard (traffic stats): [Analytics Dashboard](/analytics)
- Support Chat (this page): [Support Chat](/support-chat)

Guidelines:
- Be concise (2-4 sentences per reply)
- Be warm, helpful, and conversational
- Answer questions about cricket and the app features
- IMPORTANT: When a user asks how to find a page or feature, ALWAYS include a clickable markdown link from the App Pages Directory above. Use the format [Page Name](/path).
- If the user asks about a page or feature that does not exist in the directory above, clearly say you cannot find that page rather than guessing or making up a link.
- If asked about bugs or issues, acknowledge and say the team will look into it
- Never make promises about timelines or upcoming features
- If the user seems frustrated, empathize and offer to help
- You can discuss cricket in general — stats, rules, formats, players
- Keep a friendly tone like chatting with a knowledgeable cricket fan
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
