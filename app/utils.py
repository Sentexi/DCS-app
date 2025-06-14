import smtplib
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer
from flask import current_app


def send_email(to, subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = current_app.config.get('MAIL_DEFAULT_SENDER')
    msg['To'] = to
    msg.set_content(body)

    host = current_app.config.get('MAIL_SERVER', 'localhost')
    port = current_app.config.get('MAIL_PORT', 25)
    username = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')
    use_tls = current_app.config.get('MAIL_USE_TLS', False)
    use_ssl = current_app.config.get('MAIL_USE_SSL', False)

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
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt=salt)


def confirm_token(token, salt, expiration=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt=salt, max_age=expiration)
    except Exception:
        return None
    return email
