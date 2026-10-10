from flask import render_template, request, abort, flash, g, redirect, url_for

from app.admin import admin_bp
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import Player

from app.admin.services import (
    block_player,
    delete_player,
    restore_player,
    set_role,
    unblock_player,
)
PER_PAGE = 30


@admin_bp.route("/")
@admin_required
def index():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", default=1, type=int)

    query = Player.query

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Player.nickname.ilike(pattern),
                Player.email.ilike(pattern),
            )
        )

    query = query.order_by(Player.nickname)

    total_count = query.count()
    total_pages = max(1, (total_count + PER_PAGE - 1) // PER_PAGE)

    if page < 1:
        page = 1

    if page > total_pages:
        page = total_pages

    players = (
        query
        .limit(PER_PAGE)
        .offset((page - 1) * PER_PAGE)
        .all()
    )

    from flask import g

    rows = []

    for player in players:
        rows.append({
            "player": player,
            "is_self": player.id == g.current_user.id,
            "is_admin": player.role == "ADMIN",
        })

    return render_template(
        "admin/index.html",
        players=rows,
        q=q,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
    )


@admin_bp.route("/player/<int:player_id>/role", methods=["POST"])
@admin_required
def change_role(player_id):
    player = db.session.get(Player, player_id)

    if player is None:
        abort(404)

    if player.id == g.current_user.id:
        flash("Нельзя изменить свою роль.")
        return redirect(url_for("admin.index"))

    if player.role == "ADMIN":
        flash("Нельзя изменить роль администратора.")
        return redirect(url_for("admin.index"))

    role = request.form.get("role", "").strip()

    if role not in ("USER", "MODERATOR"):
        flash("Некорректная роль.")
        return redirect(url_for("admin.index"))

    set_role(player, role)
    db.session.commit()

    flash(f"Роль игрока {player.nickname} изменена.")

    return redirect(url_for("admin.index"))


@admin_bp.route("/player/<int:player_id>/block", methods=["POST"])
@admin_required
def block_player_view(player_id):
    player = db.session.get(Player, player_id)

    if player is None:
        abort(404)

    if player.id == g.current_user.id:
        flash("Нельзя заблокировать себя.")
        return redirect(url_for("admin.index"))

    if player.role == "ADMIN":
        flash("Нельзя заблокировать администратора.")
        return redirect(url_for("admin.index"))

    block_player(player)
    db.session.commit()

    flash(f"Игрок {player.nickname} заблокирован.")

    return redirect(url_for("admin.index"))


@admin_bp.route("/player/<int:player_id>/unblock", methods=["POST"])
@admin_required
def unblock_player_view(player_id):
    player = db.session.get(Player, player_id)

    if player is None:
        abort(404)

    unblock_player(player)
    db.session.commit()

    flash(f"Игрок {player.nickname} разблокирован.")

    return redirect(url_for("admin.index"))


@admin_bp.route("/player/<int:player_id>/delete", methods=["POST"])
@admin_required
def delete_player_view(player_id):
    player = db.session.get(Player, player_id)

    if player is None:
        abort(404)

    if player.id == g.current_user.id:
        flash("Нельзя удалить себя.")
        return redirect(url_for("admin.index"))

    if player.role == "ADMIN":
        flash("Нельзя удалить администратора.")
        return redirect(url_for("admin.index"))

    if player.is_deleted:
        flash("Игрок уже удалён.")
        return redirect(url_for("admin.index"))

    delete_player(player)
    db.session.commit()

    flash(f"Игрок {player.nickname} удалён.")

    return redirect(url_for("admin.index"))


@admin_bp.route("/player/<int:player_id>/restore", methods=["POST"])
@admin_required
def restore_player_view(player_id):
    player = db.session.get(Player, player_id)

    if player is None:
        abort(404)

    if not player.is_deleted:
        flash("Игрок не удалён.")
        return redirect(url_for("admin.index"))

    restore_player(player)
    db.session.commit()

    flash(f"Игрок {player.nickname} восстановлен.")

    return redirect(url_for("admin.index"))