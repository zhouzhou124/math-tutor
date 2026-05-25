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


def test_same_query_param_does_not_override_internal_navigation(monkeypatch):
    import streamlit as st
    import views.main_page as main_page

    state = {"page": "practice", "_last_page_query": "grading"}
    monkeypatch.setattr(st, "session_state", state)
    monkeypatch.setattr(st, "query_params", {"page": "grading"})
    monkeypatch.setattr(main_page, "is_admin", lambda: False)

    main_page._sync_page_from_query_params()

    assert state["page"] == "practice"
