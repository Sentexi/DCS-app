import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///debate_app.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv(
        "SQLALCHEMY_TRACK_MODIFICATIONS", "True"
    ).lower() in ("true", "1")
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    PORT = int(os.getenv("PORT", 5000))
    SERVER_NAME = os.getenv("SERVER_NAME", "example.com")
    PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "http")

    # Email configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "False").lower() in ("true", "1")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")
