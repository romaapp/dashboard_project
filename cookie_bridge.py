import streamlit as st
import streamlit.components.v1 as components


COOKIE_NAME = "dashboard_user_id"


def set_auth_cookie(user_id):
    """
    Устанавливает cookie непосредственно в браузере
    и после этого перезагружает страницу.
    """

    components.html(
        f"""
        <script>
            document.cookie =
                "{COOKIE_NAME}={user_id}; path=/; max-age=2592000";

            setTimeout(function() {{
                window.parent.location.reload();
            }}, 300);
        </script>
        """,
        height=0,
    )


def delete_auth_cookie():
    """
    Удаляет cookie непосредственно из браузера
    и после этого перезагружает страницу.
    """

    components.html(
        f"""
        <script>
            document.cookie =
                "{COOKIE_NAME}=; path=/; max-age=0";

            setTimeout(function() {{
                window.parent.location.reload();
            }}, 300);
        </script>
        """,
        height=0,
    )