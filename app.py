import os
from flask import Flask, render_template, jsonify
from database.db import init_db
from routes.workspace_routes import workspace_bp
from routes.upload_routes import upload_bp
from routes.chat_routes import chat_bp
from services.cleanup_service import start_cleanup_scheduler
from config.settings import settings
from utils.logger import logger

app = Flask(__name__, 
            static_folder="static", 
            template_folder="templates")

# Register API routing blueprints
app.register_blueprint(workspace_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(chat_bp)

@app.route("/")
def index():
    """Render the SPA dashboard template."""
    return render_template("index.html")

@app.route("/health", methods=["GET"])
def health():
    """Application health probe endpoint."""
    return jsonify({"status": "healthy"}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Internal server error"}), 500

# Initialize SQLite database and periodic sweeps scheduler on application startup
with app.app_context():
    try:
        init_db()
    except Exception as db_err:
        logger.error(f"Startup - Failed to initialize database: {str(db_err)}")
        
    try:
        # Launch background sweeper thread running every hour (3600 seconds)
        start_cleanup_scheduler(interval_seconds=3600)
        logger.info("Startup - Sweeper thread started successfully.")
    except Exception as sched_err:
        logger.error(f"Startup - Failed to start sweeper thread: {str(sched_err)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    logger.info(f"Starting Flask server on port: {port}")
    app.run(host="0.0.0.0", port=port, debug=(settings.FLASK_ENV == "development"))
