import smtplib
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import datetime

def send_email(to, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config.get("MAIL_DEFAULT_SENDER")
    msg["To"] = to
    msg.set_content(body)

    host = current_app.config.get("MAIL_SERVER", "localhost")
    port = current_app.config.get("MAIL_PORT", 25)
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")
    use_tls = current_app.config.get("MAIL_USE_TLS", False)
    use_ssl = current_app.config.get("MAIL_USE_SSL", False)

    if use_ssl:
        smtp = smtplib.SMTP_SSL(host, port)
    else:
        smtp = smtplib.SMTP(host, port)
    if use_tls:
        smtp.starttls()
    if username:
        smtp.login(username, password)
    smtp.send_message(msg)
    smtp.quit()


def generate_token(email, salt, expires_sec=3600):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email, salt=salt)


def confirm_token(token, salt, expiration=3600):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(token, salt=salt, max_age=expiration)
    except Exception:
        return None
    return email


from sqlalchemy import func
from .extensions import db
from .models import Vote, Topic


def compute_winning_topic(debate):
    """Return the winning Topic for a debate or None."""
    if not debate or debate.voting_open or debate.second_voting_open:
        return None
    if debate.second_voting_topics:
        topic_ids = debate.second_topic_ids()
        round_num = 2
    else:
        topic_ids = [t.id for t in debate.topics]
        round_num = 1
    if not topic_ids:
        return None
    counts = (
        db.session.query(Vote.topic_id, func.count(Vote.id))
        .filter(Vote.topic_id.in_(topic_ids), Vote.round == round_num)
        .group_by(Vote.topic_id)
        .all()
    )
    if not counts:
        return None
    max_votes = max(c[1] for c in counts)
    winners = [tid for tid, c in counts if c == max_votes]
    if len(winners) == 1:
        #this is a bit of an experiment
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        debate.title = current_date + ": " + Topic.query.get(winners[0]).text
        db.session.commit()
        return Topic.query.get(winners[0])
    return None


def reset_prefer_free():
    """Reset the prefer_judging flag for all users."""
    from .models import User

    User.query.update({User.prefer_free: False}, synchronize_session=False)


def reset_prefer_judging():
    """Reset the prefer_judging flag for all users."""
    from .models import User

    User.query.update({User.prefer_judging: False}, synchronize_session=False)
