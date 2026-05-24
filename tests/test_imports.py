"""Import smoke tests — catch circular/redundant imports before refactoring."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_grading_page_imports():
    import views.grading_page


def test_grading_adapter_imports():
    import services.grading_adapter


def test_latex_utils_imports():
    import latex_utils


def test_latex_normalizer_imports():
    import latex_normalizer


def test_mistakes_page_imports():
    import views.mistakes_page


def test_question_bank_page_imports():
    import views.question_bank_page


def test_main_page_imports():
    import views.main_page


def test_practice_page_imports():
    import views.practice_page


def test_grading_result_imports():
    import renderers.components.grading_result


def test_solution_service_imports():
    import services.solution_service


def test_grading_progress_imports():
    import views.components.grading_progress


def test_grading_task_runner_imports():
    import services.grading_task_runner


def test_grading_orchestrator_imports():
    import services.grading_orchestrator


def test_semantic_output_imports():
    import semantic_output


def test_error_repository_imports():
    import repository.error_repository


def test_memory_service_imports():
    import services.memory_service


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
