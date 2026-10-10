from functools import wraps

from flask import abort, g, redirect, request, url_for


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.get("current_user") is None:
            return redirect(
                url_for("auth.login", next=request.full_path)
            )

        return view(*args, **kwargs)

    return wrapped_view



def moderator_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.get("current_user") is None:
            return redirect(
                url_for("auth.login", next=request.full_path)
            )

        if g.current_user.role not in ("MODERATOR", "ADMIN"):
            abort(403)

        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.get("current_user") is None:
            return redirect(
                url_for("auth.login", next=request.full_path)
            )

        if g.current_user.role != "ADMIN":
            abort(403)

        return view(*args, **kwargs)

    return wrapped_view