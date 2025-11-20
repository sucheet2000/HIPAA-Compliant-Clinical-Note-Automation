"""
Flask Web Application for Clinical Notes Review
Provides human-in-the-loop interface for clinician review and validation
"""

import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    """
    Application factory pattern
    Creates and configures the Flask application
    """
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Configuration
    app.config['ENV'] = os.getenv('FLASK_ENV', 'development')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', False) == 'True'
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JSON_SORT_KEYS'] = False

    # Enable CORS for API
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    from routes.api import api_bp
    from routes.web import web_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)

    # Health check endpoint
    @app.route('/health')
    def health():
        """Health check for deployment monitoring"""
        return jsonify({'status': 'healthy', 'service': 'clinical-notes-ui'}), 200

    print("✅ Flask application initialized")
    return app


def register_error_handlers(app):
    """Register error handlers for common HTTP errors"""

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found"""
        return jsonify({'error': 'Not found', 'message': str(error)}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        print(f"❌ Internal server error: {error}")
        return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400


if __name__ == '__main__':
    app = create_app()

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))

    print(f"\n{'='*60}")
    print(f"Starting Clinical Notes Review Application")
    print(f"{'='*60}")
    print(f"Server: http://{host}:{port}")
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Debug: {os.getenv('FLASK_DEBUG', False)}")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=app.config['DEBUG'])
