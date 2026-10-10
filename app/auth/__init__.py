from urllib.parse import urlparse

from flask import (
    Blueprint,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from app.extensions import db
from app.models import Player, Wargame, Faction, PlayerFaction
from app.auth.password import hash_password, check_password
from app.auth.session import login_user, logout_user
from app.auth.decorators import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next_url(target: str | None) -> str | None:
    """
    Разрешаем редирект только на относительные пути
    внутри нашего приложения.
    """
    if not target:
        return None

    parsed = urlparse(target)

    if parsed.scheme or parsed.netloc:
        return None

    if not target.startswith("/"):
        return None

    return target


def _render_register(error=None):
    wargames = Wargame.query.order_by(Wargame.name).all()
    factions = (
        Faction.query
        .order_by(Faction.wargame_id, Faction.faction_name)
        .all()
    )

    return render_template(
        "auth/register.html",
        wargames=wargames,
        factions=factions,
        error=error,
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.current_user is not None:
        return redirect(url_for("auth.test"))

    if request.method == "GET":
        return _render_register()

    nickname = request.form.get("nickname", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    faction_ids = request.form.getlist("faction_ids")

    if not nickname or not email or not password:
        return _render_register(
            "Nickname, email and password are required."
        )

    if len(nickname) > 100:
        return _render_register("Nickname is too long.")

    if len(email) > 255:
        return _render_register("Email is too long.")

    if Player.query.filter_by(nickname=nickname).first():
        return _render_register(
            "This nickname is already registered."
        )

    if Player.query.filter_by(email=email).first():
        return _render_register(
            "This email is already registered."
        )

    try:
        selected_faction_ids = {
            int(faction_id)
            for faction_id in faction_ids
        }
    except ValueError:
        return _render_register("Invalid faction selection.")

    selected_factions = (
        Faction.query
        .filter(Faction.id.in_(selected_faction_ids))
        .all()
        if selected_faction_ids
        else []
    )

    if len(selected_factions) != len(selected_faction_ids):
        return _render_register(
            "One or more selected factions do not exist."
        )

    player = Player(
        nickname=nickname,
        email=email,
        hash_password=hash_password(password),
        role="USER",  # роль не берётся из формы
    )

    try:
        db.session.add(player)
        db.session.flush()

        for faction in selected_factions:
            db.session.add(
                PlayerFaction(
                    player_id=player.id,
                    faction_id=faction.id,
                )
            )

        db.session.commit()
    except Exception:
        db.session.rollback()
        return _render_register(
            "Registration failed. Please try again."
        )

    # Сразу логиним — иначе пользователь после регистрации
    # попадёт на /auth/login из-за @login_required.
    login_user(player.id)

    return redirect(url_for("auth.test"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.current_user is not None:
        return redirect(url_for("auth.test"))

    next_url = _safe_next_url(request.args.get("next"))

    if request.method == "GET":
        return render_template(
            "auth/login.html",
            error=None,
            next=next_url,
        )

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    player = Player.query.filter_by(email=email).first()

    if player is None or not check_password(password, player.hash_password):
        return render_template(
            "auth/login.html",
            error="Invalid email or password.",
            next=next_url,
        )

    if player.is_deleted:
        return render_template(
            "auth/login.html",
            error="Аккаунт удалён.",
            next=next_url,
        )

    login_user(player.id)

    if next_url:
        return redirect(next_url)

    return redirect(url_for("auth.test"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/test")
@login_required
def test():
    current_user = g.current_user

    return (
        f"ID: {current_user.id}<br>"
        f"Nickname: {current_user.nickname}<br>"
        f"Email: {current_user.email}<br>"
        f"Role: {current_user.role}"
    )