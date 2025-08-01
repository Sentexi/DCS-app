# app/__init__.py
from datetime import datetime, timedelta
from flask import Flask, request, redirect, url_for
from config import Config
from .extensions import db, login_manager, migrate
from .models import Debate, Topic, Vote, User
from flask_login import current_user
from datetime import datetime
from flask_socketio import SocketIO

socketio = SocketIO()  # Create the SocketIO object globally

def create_app(config_file=None):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)
    if config_file:
        app.config.from_pyfile(config_file)

    # Initialize SocketIO with CORS options
    socketio.init_app(app, cors_allowed_origins=app.config['CORS_ALLOWED_ORIGINS'])

    # Enable a 'startswith' test in our Jinja templates
    app.jinja_env.tests['startswith'] = lambda val, prefix: (
        isinstance(val, str) and val.startswith(prefix)
    )

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints (to be implemented in the next steps)
    from .auth import auth_bp
    from .main import main_bp
    from .admin import admin_bp
    from .debate import debate_bp
    from .profile import profile_bp
    from .analytics import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(debate_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(analytics_bp)
    
    print(app.url_map)
    
    @app.before_request
    def require_login():
        # These endpoints do NOT require login:
        open_routes = ['auth.login', 'auth.register', 'auth.forgot_password', 'auth.reset_password', 'auth.confirm_email', 'main.privacy', 'static']
        # If the user is NOT authenticated and is not on a public page
        if (not current_user.is_authenticated
            and request.endpoint not in open_routes
            and not (request.endpoint or '').startswith('static')):
            return redirect(url_for('auth.login'))
    
    @app.before_request
    def update_last_seen():
        # Only for authenticated users, and not for static/assets
        if current_user.is_authenticated and not request.path.startswith('/static'):
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
            
            # --- WebSocket live update for active debates ---
            open_debates = Debate.query.filter_by(active=True).all()
            now = datetime.utcnow()
            ten_minutes_ago = now - timedelta(minutes=10)

            active_user_ids = set(
                u.id for u in User.query.filter(User.last_seen >= ten_minutes_ago).all()
            )
            for debate in open_debates:
                voted_user_ids = set(
                    row[0]
                    for row in db.session.query(Vote.user_id)
                    .join(Topic)
                    .filter(Topic.debate_id == debate.id)
                    .distinct()
                    .all()
                )
                eligible_user_ids = active_user_ids.union(voted_user_ids)
                total_users = len(eligible_user_ids)
                voted_users = len(voted_user_ids)

                socketio.emit('vote_update', {
                    'debate_id': debate.id,
                    'vote_data': {
                        'total_users': total_users,
                        'voted_users': voted_users
                    }
                })
            # --- End live update ---

    return app
