from routes.upload_routes import upload_bp
from routes.chat_routes import chat_bp


def register_routes(app):
    app.register_blueprint(upload_bp)
    app.register_blueprint(chat_bp)