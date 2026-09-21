from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request

from app import meta
from app.config import Config
from app.extensions import db, login_manager
from app.models import User
from app.seed import seed_all
from app.utils import (
    ACTION_LABELS,
    MODE_LABELS,
    ROLE_LABELS,
    STATUS_LABELS,
    VISIBILITY_LABELS,
    format_dt,
    label_of,
)


def create_app(config_class=Config):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.config["APP_NAME"] = meta.APP_NAME
    app.config["APP_VERSION"] = meta.APP_VERSION

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.template_filter("dt")
    def dt_filter(value):
        return format_dt(value)

    @app.template_filter("vis_label")
    def vis_label_filter(value):
        return label_of(VISIBILITY_LABELS, value)

    @app.template_filter("status_label")
    def status_label_filter(value):
        return label_of(STATUS_LABELS, value)

    @app.template_filter("role_label")
    def role_label_filter(value):
        return label_of(ROLE_LABELS, value)

    @app.template_filter("mode_label")
    def mode_label_filter(value):
        return label_of(MODE_LABELS, value)

    @app.template_filter("action_label")
    def action_label_filter(value):
        return label_of(ACTION_LABELS, value)

    @app.context_processor
    def inject_globals():
        return {
            "APP_NAME": meta.APP_NAME,
            "APP_VERSION": meta.APP_VERSION,
            "COURSE_NAME": meta.COURSE_NAME,
            "current_endpoint": request.endpoint,
        }

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.knowledge import bp as knowledge_bp
    from app.blueprints.qa import bp as qa_bp
    from app.blueprints.graph import bp as graph_bp
    from app.blueprints.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        seed_all(app)

    return app
