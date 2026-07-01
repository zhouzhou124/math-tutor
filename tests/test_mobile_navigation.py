"""Mobile navigation contracts."""


def test_mobile_nav_renders_fixed_anchor_links(monkeypatch):
    import streamlit as st
    from views import mobile

    rendered = []
    monkeypatch.setattr(st, "session_state", {"page": "grading"})
    monkeypatch.setattr(st, "markdown", lambda body, **kw: rendered.append((body, kw)))

    mobile.render_mobile_nav()

    html = rendered[-1][0]
    assert 'class="mobile-bottom-nav"' in html
    assert '?page=grading' in html
    assert '?page=settings' in html
    assert 'mobile-nav-item active' in html
    assert 'target="_self"' in html


def test_mobile_query_param_sync_changes_page(monkeypatch):
    import streamlit as st
    import views.main_page as main_page

    state = {"page": "dashboard"}
    monkeypatch.setattr(st, "session_state", state)
    monkeypatch.setattr(st, "query_params", {"page": "grading"})
    monkeypatch.setattr(main_page, "is_admin", lambda: False)

    main_page._sync_page_from_query_params()

    assert state["page"] == "grading"
    assert state["_last_page_query"] == "grading"


def test_mobile_query_param_sync_settings_page(monkeypatch):
    import streamlit as st
    import views.main_page as main_page

    state = {"page": "dashboard"}
    monkeypatch.setattr(st, "session_state", state)
    monkeypatch.setattr(st, "query_params", {"page": "settings"})
    monkeypatch.setattr(main_page, "is_admin", lambda: False)

    main_page._sync_page_from_query_params()

    assert state["page"] == "settings"


def test_mobile_topbar_includes_settings_link(monkeypatch):
    import streamlit as st
    from views import mobile

    rendered = []
    monkeypatch.setattr(
        st,
        "session_state",
        {"page": "dashboard", "auth": {"username": "demo_user"}},
    )
    monkeypatch.setattr(st, "markdown", lambda body, **kw: rendered.append((body, kw)))

    mobile.render_mobile_topbar()

    html = rendered[-1][0]
    assert 'class="user-settings"' in html
    assert '?page=settings' in html
    assert "demo_user" in html


def test_same_query_param_does_not_override_internal_navigation(monkeypatch):
    import streamlit as st
    import views.main_page as main_page

    state = {"page": "practice", "_last_page_query": "grading"}
    monkeypatch.setattr(st, "session_state", state)
    monkeypatch.setattr(st, "query_params", {"page": "grading"})
    monkeypatch.setattr(main_page, "is_admin", lambda: False)

    main_page._sync_page_from_query_params()

    assert state["page"] == "practice"
