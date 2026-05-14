"""
batch_grader_yuge.py — 26宇哥八套卷批量AI批改

按题目类型（选择题/填空题/解答题）对26宇哥八套卷进行AI批改

用法:
    python batch_grader_yuge.py                          # 预览要批改的题目
    python batch_grader_yuge.py --grade                  # 执行批量批改
    python batch_grader_yuge.py --grade --type 选择题     # 只批改选择题
    python batch_grader_yuge.py --grade --volume 卷一     # 只批改指定卷
"""

import sys
import os
import json
import argparse
import time
from pathlib import Path
from collections import defaultdict

_ROOT = os.path.dirname(os.path.realpath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, STORAGE_DIR

# 题目类型映射
QUESTION_TYPE_MAP = {
    "选择题": "single_choice",
    "填空题": "fill_blank",
    "解答题": "solution",
    "证明题": "proof",
}


def load_yuge_questions(volume: str = None, question_type: str = None) -> list:
    """加载26宇哥八套卷题目"""
    questions = []
    simul_dir = Path(STORAGE_DIR) / "questions" / "simulations"

    if not simul_dir.exists():
        print(f"[错误] 目录不存在: {simul_dir}")
        return []

    # 遍历所有JSON文件
    for fname in sorted(simul_dir.glob("26宇哥八套卷-*.json")):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 按卷过滤
            if volume:
                vol = data.get("volume", "")
                if vol != volume:
                    continue

            # 按题型过滤
            if question_type:
                qtype = data.get("question_type", "")
                if qtype != question_type:
                    continue

            questions.append(data)
        except Exception as e:
            print(f"[跳过] {fname}: {e}")

    return questions


def get_student_answer(question: dict) -> str:
    """模拟获取学生答案（实际应从作答记录获取）
    这里用标准答案作为"学生答案"来演示批改流程
    """
    qtype = question.get("question_type", "")

    if qtype == "选择题":
        return question.get("correct_option", "A")

    if qtype == "填空题":
        return question.get("standard_answer", "")

    if qtype in ("解答题", "证明题"):
        steps = question.get("solution_steps", [])
        if steps:
            return "\n".join(steps)
        return question.get("standard_answer", "")

    return ""


def group_by_type(questions: list) -> dict:
    """按题目类型分组"""
    groups = defaultdict(list)
    for q in questions:
        qtype = q.get("question_type", "未知")
        groups[qtype].append(q)
    return dict(groups)


def print_summary(questions: list):
    """打印题目汇总信息"""
    print("\n" + "=" * 60)
    print("26宇哥八套卷题目汇总")
    print("=" * 60)

    groups = group_by_type(questions)
    total = len(questions)

    for qtype in ["选择题", "填空题", "解答题", "证明题"]:
        qlist = groups.get(qtype, [])
        if qlist:
            print(f"\n【{qtype}】共 {len(qlist)} 道")

            # 按卷分组
            by_volume = defaultdict(list)
            for q in qlist:
                vol = q.get("volume", "未知")
                by_volume[vol].append(q)

            for vol in sorted(by_volume.keys()):
                vlist = by_volume[vol]
                print(f"  {vol}: {len(vlist)} 道")

                # 显示前3道题目
                for q in vlist[:3]:
                    qid = q.get("question_id", "?")
                    kp = q.get("knowledge_points", ["未知"])[:1]
                    kp_str = kp[0] if kp else "未知"
                    print(f"    - {qid}: {kp_str}")

                if len(vlist) > 3:
                    print(f"    ... 还有 {len(vlist) - 3} 道")

    print(f"\n总计: {total} 道题目")


def grade_single_choice(question: dict, student_answer: str) -> dict:
    """批改选择题"""
    qid = question.get("question_id", "?")
    correct = question.get("correct_option", "").strip().upper()
    stu = student_answer.strip().upper()

    is_correct = stu == correct

    return {
        "question_id": qid,
        "question_type": "选择题",
        "is_correct": is_correct,
        "score": 5.0 if is_correct else 0.0,
        "max_score": 5.0,
        "student_answer": student_answer,
        "correct_answer": correct,
        "comment": f"{'正确' if is_correct else f'错误，正确答案是 {correct}'}"
    }


def grade_fill_blank(question: dict, student_answer: str) -> dict:
    """批改填空题"""
    qid = question.get("question_id", "?")
    std_answer = question.get("standard_answer", "")
    total_score = float(question.get("score", 5))

    from symbolic_executor import quick_compare

    result = quick_compare(student_answer, std_answer)
    is_correct = result.get("equivalent", False)

    return {
        "question_id": qid,
        "question_type": "填空题",
        "is_correct": is_correct,
        "score": total_score if is_correct else 0.0,
        "max_score": total_score,
        "student_answer": student_answer,
        "correct_answer": std_answer,
        "comment": f"{'正确' if is_correct else f'答案不等价'}"
    }


def grade_solution_question(question: dict, student_answer: str, grader) -> dict:
    """批改解答题（使用AI）"""
    qid = question.get("question_id", "?")
    qtext = question.get("question", "")
    std_answer = question.get("standard_answer", "")
    total_score = float(question.get("score", 10))
    kps = question.get("knowledge_points", [])
    kp_str = ", ".join(kps[:2]) if kps else "未指定"
    difficulty = question.get("difficulty", "中等")

    try:
        result = grader.grade(
            question=qtext,
            standard_answer=std_answer,
            student_answer=student_answer,
            total_score=total_score,
            knowledge_points=kp_str,
            difficulty=difficulty,
        )
        return {
            "question_id": qid,
            "question_type": "解答题",
            "is_correct": result.get("total", 0) >= total_score * 0.6,
            "score": result.get("total", 0),
            "max_score": total_score,
            "student_answer": student_answer[:200] + "..." if len(student_answer) > 200 else student_answer,
            "correct_answer": std_answer[:200] + "..." if len(std_answer) > 200 else std_answer,
            "comment": result.get("comment", ""),
            "step_analysis": result.get("step_analysis", []),
            "success": True
        }
    except Exception as e:
        return {
            "question_id": qid,
            "question_type": "解答题",
            "is_correct": False,
            "score": 0,
            "max_score": total_score,
            "success": False,
            "error": str(e)
        }


def batch_grade(questions: list, question_type: str = None, dry_run: bool = False):
    """批量批改"""
    from agents import GradingAgent
    from llm_client import create_client

    print("\n" + "=" * 60)
    print("开始批量AI批改")
    print("=" * 60)

    # 构建LLM客户端
    if not LLM_API_KEY:
        print("[错误] 未配置 LLM_API_KEY")
        return

    protocol = "openai"
    try:
        from credential_store import get_active_profile
        profile = get_active_profile()
        if profile:
            protocol = profile.get("protocol", "openai")
    except Exception:
        pass

    client = create_client(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        protocol=protocol,
    )

    if not client:
        print("[错误] LLM 客户端初始化失败")
        return

    grader = GradingAgent(client, model=LLM_MODEL or "deepseek-chat")

    # 按类型分组
    groups = group_by_type(questions)

    all_results = []
    stats = {"total": 0, "correct": 0, "by_type": {}}

    for qtype in ["选择题", "填空题", "解答题", "证明题"]:
        if question_type and question_type != qtype:
            continue

        qlist = groups.get(qtype, [])
        if not qlist:
            continue

        print(f"\n处理 {qtype} ({len(qlist)} 道)...")

        type_stats = {"total": len(qlist), "correct": 0, "graded": 0, "failed": 0}
        stats["by_type"][qtype] = type_stats

        for i, q in enumerate(qlist):
            qid = q.get("question_id", "?")
            student_answer = get_student_answer(q)

            print(f"  [{i+1}/{len(qlist)}] {qid}...", end=" ", flush=True)

            if dry_run:
                print("跳过（dry_run）")
                continue

            # 关键修复：选择题和填空题走快速路径，解答题和证明题始终走AI路径
            if qtype == "选择题":
                result = grade_single_choice(q, student_answer)
            elif qtype == "填空题":
                result = grade_fill_blank(q, student_answer)
            elif qtype in ("解答题", "证明题"):
                # 解答题和证明题始终调用AI批改，即使有standard_answer
                result = grade_solution_question(q, student_answer, grader)
            else:
                result = {"question_id": qid, "question_type": qtype, "is_correct": False, "score": 0}

            all_results.append(result)
            stats["total"] += 1

            if result.get("is_correct"):
                type_stats["correct"] += 1
                stats["correct"] += 1

            if result.get("success", True):
                type_stats["graded"] += 1
                print(f"得分: {result.get('score', 0)}/{result.get('max_score', 0)} - {result.get('comment', '')[:30]}")
            else:
                type_stats["failed"] += 1
                print(f"失败: {result.get('error', '未知错误')}")

            time.sleep(0.5)  # 避免请求过快

    # 打印统计
    print("\n" + "=" * 60)
    print("批改完成 - 统计汇总")
    print("=" * 60)

    for qtype, type_stats in stats["by_type"].items():
        total = type_stats["total"]
        correct = type_stats["correct"]
        rate = correct / total * 100 if total > 0 else 0
        print(f"\n【{qtype}】")
        print(f"  总题数: {total}")
        print(f"  正确数: {correct}")
        print(f"  正确率: {rate:.1f}%")

    total = stats["total"]
    correct = stats["correct"]
    rate = correct / total * 100 if total > 0 else 0
    print(f"\n【总计】")
    print(f"  总题数: {total}")
    print(f"  正确数: {correct}")
    print(f"  正确率: {rate:.1f}%")

    # 保存结果
    if not dry_run and all_results:
        output_path = Path(STORAGE_DIR) / "grading_results_yuge.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "stats": stats,
                "results": all_results
            }, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="26宇哥八套卷批量AI批改")
    parser.add_argument("--grade", action="store_true", help="执行批量批改")
    parser.add_argument("--type", choices=["选择题", "填空题", "解答题", "证明题"],
                        help="只批改指定题型")
    parser.add_argument("--volume", help="只批改指定卷（如：卷一）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不执行批改")

    args = parser.parse_args()

    print("加载题目...")
    questions = load_yuge_questions(volume=args.volume, question_type=args.type)
    print(f"找到 {len(questions)} 道题目")

    if not questions:
        print("未找到任何题目")
        return

    print_summary(questions)

    if args.grade or args.dry_run:
        batch_grade(questions, question_type=args.type, dry_run=args.dry_run)


if __name__ == "__main__":
    main()