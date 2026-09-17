from functools import wraps

from flask import g, redirect, request, url_for


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.get("current_user") is None:
            return redirect(
                url_for("auth.login", next=request.full_path)
            )

        return view(*args, **kwargs)

    return wrapped_view