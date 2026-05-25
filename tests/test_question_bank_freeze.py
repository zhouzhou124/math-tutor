"""P20: Regression test — question bank rendering format is frozen."""

import inspect


def test_question_bank_keeps_full_question_rendering():
    """真题库必须继续直接渲染完整题目，不能降级为纯文本 preview。"""
    import views.question_bank_page as page
    src = inspect.getsource(page.render_question_bank_page)
    assert "render_question(" in src
    # 不应用 show_preview=True（那是纯文本预览模式）
    assert "show_preview=True" not in src


def test_question_bank_imports_theme_components():
    """主题组件已就绪但题库页不强制依赖。"""
    from views.ui.theme import (
        inject_app_theme,
        render_page_header,
        render_flow_steps,
        render_question_list_card,
        render_mistake_card,
    )
    assert callable(inject_app_theme)
    assert callable(render_page_header)
    assert callable(render_flow_steps)
    assert callable(render_question_list_card)
    assert callable(render_mistake_card)
