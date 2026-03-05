"""
Flask Web Application for Clinical Notes Review
Provides human-in-the-loop interface for clinician review and validation
"""

import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def create_app():
    """
    Application factory pattern.
    Creates and configures the Flask application.
    """
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.config['JSON_SORT_KEYS'] = False

    # SECRET_KEY — must be a strong random value set in the environment.
    # No insecure fallback is permitted in production.
    secret_key = os.getenv('SECRET_KEY', '')
    _placeholder_keys = {
        '',
        'your_secret_key_change_me_in_production',
        'CHANGE_ME_GENERATE_SECURE_RANDOM_KEY',
        'dev-secret-key-change-in-production',
    }
    if secret_key in _placeholder_keys:
        if app.config['ENV'] == 'production':
            raise RuntimeError(
                'SECRET_KEY is not set or uses a placeholder value. '
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        # Allow a deterministic dev key only in non-production
        secret_key = 'dev-only-insecure-key-do-not-use-in-production'
        logger.warning(
            'Using insecure dev SECRET_KEY — set SECRET_KEY in .env before deploying.'
        )
    app.config['SECRET_KEY'] = secret_key

    # ------------------------------------------------------------------
    # CSRF Protection
    # ------------------------------------------------------------------
    csrf = CSRFProtect()
    csrf.init_app(app)

    # ------------------------------------------------------------------
    # Rate Limiting
    # ------------------------------------------------------------------
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=['200 per hour', '60 per minute'],
        storage_uri='memory://',
    )

    # ------------------------------------------------------------------
    # Flask-Login
    # ------------------------------------------------------------------
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    from models.user import User  # noqa: PLC0415

    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database by ID."""
        try:
            return User.get_user_by_id(int(user_id))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # CORS — restrict to explicitly configured origins only
    # ------------------------------------------------------------------
    allowed_origins_raw = os.getenv('CORS_ALLOWED_ORIGINS', '')
    allowed_origins = [o.strip() for o in allowed_origins_raw.split(',') if o.strip()]
    # If no origins are configured, the API is same-origin only
    CORS(
        app,
        resources={r'/api/*': {'origins': allowed_origins or []}},
        supports_credentials=True,
    )

    # ------------------------------------------------------------------
    # Security headers on every response
    # ------------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )
        # Allow Bootstrap & Bootstrap-Icons from CDN
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    from routes.api import api_bp    # noqa: PLC0415
    from routes.web import web_bp    # noqa: PLC0415
    from routes.auth import auth_bp  # noqa: PLC0415

    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)

    # Tighter rate limit on auth routes to deter brute-force
    limiter.limit('10 per minute')(auth_bp)

    # ------------------------------------------------------------------
    # Error handlers
    # ------------------------------------------------------------------
    register_error_handlers(app)

    # ------------------------------------------------------------------
    # Health check (unauthenticated — for Docker / load-balancer probes)
    # ------------------------------------------------------------------
    @app.route('/health')
    def health():
        return jsonify({'status': 'healthy', 'service': 'clinical-notes-ui'}), 200

    logger.info('Flask application initialised successfully.')
    return app


def register_error_handlers(app):
    """Register error handlers for common HTTP errors."""

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        # Log full traceback server-side; never expose details to the client
        logger.error('Internal server error: %s', error, exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request'}), 400

    @app.errorhandler(429)
    def rate_limited(error):
        return jsonify({'error': 'Too many requests — please slow down'}), 429

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403


if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
    application = create_app()

    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', 5000))

    logger.info('Starting on %s:%s', host, port)
    application.run(host=host, port=port, debug=application.config['DEBUG'])
