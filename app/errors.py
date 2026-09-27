"""
Error handlers registered with the Flask app.
"""
from flask import render_template


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("errors/400.html", error=str(e)), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", error=str(e)), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html", error=str(e)), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html", error=str(e)), 413

    @app.errorhandler(500)
    def internal_error(e):
        from app.extensions import db
        db.session.rollback()
        return render_template("errors/500.html", error=str(e)), 500
