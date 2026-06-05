import os

from flask import Flask, jsonify, render_template

from config.settings import Config
from routes import register_routes
from database.db import initialize_database


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["UPLOAD_FOLDER"] = Config.UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    initialize_database()
    register_routes(app)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "application": "Multi Document RAG",
            "environment": Config.FLASK_ENV
        }), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=Config.FLASK_DEBUG
    )