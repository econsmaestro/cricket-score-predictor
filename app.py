import os
import re
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from markupsafe import Markup, escape

logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

db.init_app(app)

def markdown_links(text):
    safe_text = str(escape(text))
    safe_text = safe_text.replace('\n', '<br>')
    safe_text = re.sub(
        r'\[([^\]]+)\]\((/[^)]*)\)',
        r'<a href="\2" style="color:#2d5a87;text-decoration:underline;font-weight:500;">\1</a>',
        safe_text
    )
    return Markup(safe_text)

app.jinja_env.filters['markdown_links'] = markdown_links

with app.app_context():
    import models  # noqa: F401
    db.create_all()
