from flask import g, redirect, render_template, url_for

from app.main import main_bp


@main_bp.route("/")
def index():
    if g.current_user is not None:
        return redirect(
            url_for(
                "profile.view",
                nickname=g.current_user.nickname,
            )
        )

    return render_template("main/index.html")