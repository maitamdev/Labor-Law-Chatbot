"""Exercise the real Streamlit entry point without a Supabase project or model."""

from concurrent.futures import Future
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py")


@pytest.fixture(autouse=True)
def fresh_component_registration():
    from ui.components.account_portal import get_portal_surface
    from ui.components.approved_layout import get_surface

    get_surface.cache_clear()
    get_portal_surface.cache_clear()
    yield
    get_surface.cache_clear()
    get_portal_surface.cache_clear()


def test_guest_boots_without_supabase_and_keeps_ai_first(monkeypatch):
    import app.warmup

    monkeypatch.setattr(app.warmup, "start_background_warmup", lambda: None)
    app = AppTest.from_file(APP_PATH, default_timeout=15).run()
    assert not app.exception
    assert app.session_state["ui_view"] == "home" if "ui_view" in app.session_state else True
    assert app.session_state["guest_history_manager"] is not None
    assert not app.session_state["_accounts_client"].session


@pytest.mark.parametrize("busy", [False, True])
def test_navigation_is_applied_before_render_and_survives_reruns(monkeypatch, busy):
    import app.warmup
    import ui.components.approved_layout as layout

    monkeypatch.setattr(app.warmup, "start_background_warmup", lambda: None)
    rendered_views = []
    monkeypatch.setattr(
        layout,
        "render_approved_layout",
        lambda **kwargs: rendered_views.append(kwargs["view"]) or {},
    )
    app = AppTest.from_file(APP_PATH, default_timeout=15).run()
    key = f"approved_surface::{app.session_state['guest_session_id']}"
    if busy:
        future = Future()
        app.session_state["pending_query"] = "Điều kiện hưởng trợ cấp thôi việc?"
        app.session_state["pending_chat_future"] = future
    for index, view in enumerate(["documents", "topics", "templates", "situations", "faq", "news", "graph", "home"]):
        action = {"type": "navigate", "view": view, "action_id": f"navigation-{index}"}
        app.session_state[key] = {"action": action}
        app.run()
        assert not app.exception
        assert rendered_views[-1] == view
        assert app.session_state["ui_view"] == view
        assert app.session_state["_last_navigation_action_id"] == action['action_id']
        # Component triggers expire; an unrelated rerun must retain the page.
        app.session_state[key] = {"action": None}
        app.run()
        assert not app.exception
        assert rendered_views[-1] == view
    if busy:
        future.set_result((None, {"answer": "Test response"}))
        app.run()
        assert not app.exception
        assert "pending_query" not in app.session_state
        assert rendered_views[-1] == "home"


def test_navigation_rejects_unknown_views(monkeypatch):
    import app.warmup
    import ui.components.approved_layout as layout

    monkeypatch.setattr(app.warmup, "start_background_warmup", lambda: None)
    monkeypatch.setattr(layout, "render_approved_layout", lambda **kwargs: {})
    app = AppTest.from_file(APP_PATH, default_timeout=15).run()
    app.session_state["ui_view"] = "faq"
    key = f"approved_surface::{app.session_state['guest_session_id']}"
    app.session_state[key] = {"action": {"type": "navigate", "view": "admin-users", "action_id": "invalid-nav"}}
    app.run()
    assert not app.exception
    assert app.session_state["ui_view"] == "faq"


def test_reruns_do_not_patch_asyncio_transport(monkeypatch):
    import sys

    if sys.platform != "win32":
        pytest.skip("Windows Proactor transport")
    from asyncio.proactor_events import _ProactorBasePipeTransport

    original = _ProactorBasePipeTransport._call_connection_lost
    app = AppTest.from_file(APP_PATH, default_timeout=15)
    for _ in range(3):
        app.run()
        assert not app.exception
        assert _ProactorBasePipeTransport._call_connection_lost is original


def test_attachment_metadata_is_saved_once(monkeypatch):
    import ui.utils.document_reader

    monkeypatch.setattr(
        ui.utils.document_reader,
        "extract_attachment_text",
        lambda attachment: ("", "contract.txt", "1 KB"),
    )
    app = AppTest.from_file(APP_PATH, default_timeout=15).run()
    app.session_state["submitted_query"] = "Xin chào"
    app.session_state["submitted_attachment"] = {"name": "contract.txt"}
    app.run()
    assert not app.exception
    manager = app.session_state["guest_history_manager"]
    conversation = manager.get_conversation(app.session_state["active_conv_id"])
    users = [message for message in conversation["messages"] if message["role"] == "user"]
    assert len(users) == 1
    assert users[0]["attachment"]["name"] == "contract.txt"


def test_forged_admin_route_renders_denial_without_loading_admin_data(monkeypatch):
    import app.warmup

    monkeypatch.setattr(app.warmup, "start_background_warmup", lambda: None)
    app = AppTest.from_file(APP_PATH, default_timeout=15)
    app.session_state["portal_view"] = "admin-users"
    app.run()
    assert not app.exception
    assert "guest_history_manager" not in app.session_state


def test_recovery_route_without_one_time_link_is_not_password_form(monkeypatch):
    import app.warmup

    monkeypatch.setattr(app.warmup, "start_background_warmup", lambda: None)
    app = AppTest.from_file(APP_PATH, default_timeout=15)
    app.session_state["portal_view"] = "account-recovery"
    app.run()
    assert not app.exception
    assert "_recovery_client" not in app.session_state
