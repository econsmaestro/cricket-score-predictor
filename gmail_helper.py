"""Gmail integration via Replit connector for sending emails."""
import os
import json
import base64
import logging
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, formataddr
import requests

logger = logging.getLogger(__name__)

_connection_settings = None


def _get_access_token():
    """Get Gmail OAuth access token from Replit connector."""
    global _connection_settings

    if (_connection_settings
            and _connection_settings.get('settings', {}).get('expires_at')
            and _is_token_valid(_connection_settings['settings']['expires_at'])):
        return _connection_settings['settings']['access_token']

    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    repl_identity = os.environ.get('REPL_IDENTITY')
    web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')

    if repl_identity:
        x_replit_token = 'repl ' + repl_identity
    elif web_repl_renewal:
        x_replit_token = 'depl ' + web_repl_renewal
    else:
        raise RuntimeError('Replit token not found')

    if not hostname:
        raise RuntimeError('REPLIT_CONNECTORS_HOSTNAME not set')

    resp = requests.get(
        f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-mail',
        headers={
            'Accept': 'application/json',
            'X_REPLIT_TOKEN': x_replit_token
        },
        timeout=10
    )
    resp.raise_for_status()
    data = resp.json()
    _connection_settings = (data.get('items') or [None])[0]

    if not _connection_settings:
        raise RuntimeError('Gmail not connected')

    settings = _connection_settings.get('settings', {})
    access_token = settings.get('access_token') or settings.get('oauth', {}).get('credentials', {}).get('access_token')

    if not access_token:
        raise RuntimeError('Gmail access token not found')

    return access_token


def _is_token_valid(expires_at):
    """Check if the token hasn't expired."""
    from datetime import datetime
    try:
        exp = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return exp.timestamp() > datetime.utcnow().timestamp()
    except Exception:
        return False


def _get_sender_email(access_token):
    """Get the authenticated user's email address from Gmail profile."""
    try:
        resp = requests.get(
            'https://gmail.googleapis.com/gmail/v1/users/me/profile',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        resp.raise_for_status()
        email = resp.json().get('emailAddress')
        if email:
            return email
    except Exception:
        pass

    try:
        resp = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        resp.raise_for_status()
        email = resp.json().get('email')
        if email:
            return email
    except Exception:
        pass

    return os.environ.get('GMAIL_SENDER_EMAIL', 'noreply@cricketintelligence.app')


def _is_valid_email(email):
    """Email format validation - requires domain with letters and TLD max 6 chars."""
    import re
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]*[a-zA-Z][a-zA-Z0-9.-]*\.[a-zA-Z]{2,6}$', email))


def send_email(to_email, subject, html_body, plain_body=None):
    """Send an email via Gmail API.
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email
        plain_body: Plain text fallback (optional)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not _is_valid_email(to_email):
        logger.warning(f"Invalid email address: {to_email}")
        return False

    try:
        access_token = _get_access_token()

        sender_email = _get_sender_email(access_token)

        msg = MIMEMultipart('alternative')
        msg['From'] = formataddr(("CricPredictor (no-reply)", sender_email))
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = f"<{uuid.uuid4()}@cricpredictor.app>"
        msg['X-Mailer'] = 'CricPredictor'
        msg['Precedence'] = 'bulk'

        if plain_body:
            msg.attach(MIMEText(plain_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

        resp = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={'raw': raw_message},
            timeout=15
        )
        resp.raise_for_status()
        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def get_unread_replies():
    """Fetch unread emails that are replies to CricPredictor messages.
    
    Returns:
        List of dicts with keys: message_id, thread_id, from_email, from_name, subject, body, snippet
    """
    try:
        access_token = _get_access_token()
        
        resp = requests.get(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages',
            headers={'Authorization': f'Bearer {access_token}'},
            params={
                'q': 'subject:CricPredictor is:unread -from:me',
                'maxResults': 10
            },
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        
        messages = data.get('messages', [])
        if not messages:
            return []
        
        results = []
        for msg_stub in messages:
            msg_id = msg_stub['id']
            thread_id = msg_stub.get('threadId', msg_id)
            
            msg_resp = requests.get(
                f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'format': 'full'},
                timeout=15
            )
            msg_resp.raise_for_status()
            msg_data = msg_resp.json()
            
            headers = {h['name'].lower(): h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
            
            from_header = headers.get('from', '')
            from_email = from_header
            from_name = ''
            if '<' in from_header and '>' in from_header:
                from_name = from_header.split('<')[0].strip().strip('"')
                from_email = from_header.split('<')[1].split('>')[0]
            
            subject = headers.get('subject', '')
            
            body = _extract_body(msg_data.get('payload', {}))
            
            results.append({
                'message_id': msg_id,
                'thread_id': thread_id,
                'from_email': from_email,
                'from_name': from_name,
                'subject': subject,
                'body': body,
                'snippet': msg_data.get('snippet', '')
            })
        
        return results
    
    except Exception as e:
        logger.error(f"Failed to fetch unread replies: {e}")
        return []


def _extract_body(payload):
    """Extract plain text body from Gmail message payload."""
    if payload.get('mimeType') == 'text/plain' and payload.get('body', {}).get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    
    for part in payload.get('parts', []):
        if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
        if part.get('parts'):
            result = _extract_body(part)
            if result:
                return result
    
    if payload.get('body', {}).get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
    
    return ''


def mark_as_read(message_id):
    """Mark a Gmail message as read."""
    try:
        access_token = _get_access_token()
        resp = requests.post(
            f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={'removeLabelIds': ['UNREAD']},
            timeout=10
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to mark message {message_id} as read: {e}")
        return False


def send_reply(to_email, subject, html_body, thread_id, message_id, plain_body=None):
    """Send a reply within an existing email thread."""
    if not _is_valid_email(to_email):
        return False
    
    try:
        access_token = _get_access_token()
        sender_email = _get_sender_email(access_token)
        
        msg = MIMEMultipart('alternative')
        msg['From'] = formataddr(("CricPredictor", sender_email))
        msg['To'] = to_email
        msg['Reply-To'] = sender_email
        msg['Subject'] = subject if subject.lower().startswith('re:') else f"Re: {subject}"
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = f"<{uuid.uuid4()}@cricpredictor.app>"
        msg['In-Reply-To'] = message_id
        msg['References'] = message_id
        msg['X-Mailer'] = 'CricPredictor'
        
        if plain_body:
            msg.attach(MIMEText(plain_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        
        resp = requests.post(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={'raw': raw_message, 'threadId': thread_id},
            timeout=15
        )
        resp.raise_for_status()
        logger.info(f"Reply sent to {to_email} in thread {thread_id}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send reply to {to_email}: {e}")
        return False
