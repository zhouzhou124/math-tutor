"""测试 Repository 和 Service 层"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from repository import (
    UserRepository,
    ProfileRepository,
    ProfileStatsRepository,
    ErrorRecordRepository,
    ErrorIndexRepository,
    User,
    UserProfile,
    ErrorRecord,
)

from services import (
    AuthService,
    DashboardService,
    MemoryService,
    GradingService,
)

def test_repository_layer():
    """测试 Repository 层"""
    print("=" * 60)
    print("测试 Repository 层")
    print("=" * 60)
    
    # 创建临时存储目录
    storage_dir = Path("storage/test_repo")
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = storage_dir / "test.db"
    data_dir = storage_dir / "data"
    
    # 1. 测试 UserRepository
    print("\n1. 测试 UserRepository")
    user_repo = UserRepository(db_path, data_dir)
    
    # 创建用户
    user_id = user_repo.create_user("test_user", "password123", "test@example.com")
    print(f"   创建用户: {user_id}")
    
    # 获取用户
    user = user_repo.get_user(user_id)
    print(f"   获取用户: {user.username}")
    
    # 认证
    auth_result = user_repo.authenticate("test_user", "password123")
    print(f"   认证结果: {auth_result}")
    
    # 2. 测试 ProfileRepository
    print("\n2. 测试 ProfileRepository")
    profile_repo = ProfileRepository(db_path, data_dir)
    
    # 获取/创建画像
    profile = profile_repo.get_profile(user_id)
    print(f"   获取画像: level={profile.level}")
    
    # 更新画像
    profile.level = "冲刺阶段"
    profile.total_questions = 50
    profile_repo.save_profile(profile)
    
    # 重新获取
    profile = profile_repo.get_profile(user_id)
    print(f"   更新后画像: level={profile.level}, total_questions={profile.total_questions}")
    
    # 3. 测试 ProfileStatsRepository
    print("\n3. 测试 ProfileStatsRepository")
    stats_repo = ProfileStatsRepository(db_path, data_dir)
    
    stats_repo.update_stats(user_id, {
        "total_questions": 100,
        "total_errors": 20,
        "overall_accuracy": 0.8,
        "current_level": "冲刺阶段",
        "streak_days": 7,
        "last_study_date": "2024-01-15",
    })
    
    stats = stats_repo.get_stats(user_id)
    print(f"   获取统计: total_questions={stats['total_questions']}, accuracy={stats['overall_accuracy']:.1%}")
    
    # 4. 测试 ErrorRecordRepository
    print("\n4. 测试 ErrorRecordRepository")
    error_repo = ErrorRecordRepository(db_path, data_dir)
    
    record_id = error_repo.add_record(user_id, {
        "question_id": "2024-数一-001",
        "question_type": "选择题",
        "knowledge_point": "高等数学 - 极限",
        "error_type": "概念错误",
        "difficulty": "中等",
        "student_answer": "A",
        "correct_answer": "B",
        "score": 0,
        "max_score": 4,
    })
    print(f"   添加错题: {record_id}")
    
    records = error_repo.get_records(user_id, limit=5)
    print(f"   获取错题数: {len(records)}")
    
    error_stats = error_repo.get_stats(user_id)
    print(f"   错题统计: total_errors={error_stats.total_errors}")
    
    # 5. 测试 ErrorIndexRepository
    print("\n5. 测试 ErrorIndexRepository")
    error_index_repo = ErrorIndexRepository(db_path, data_dir)
    
    # 搜索
    results = error_index_repo.search_by_knowledge_point(user_id, "极限", limit=5)
    print(f"   搜索结果数: {len(results)}")
    
    type_dist = error_index_repo.get_error_count_by_type(user_id)
    print(f"   错误类型分布: {type_dist}")
    
    print("\n[OK] Repository 层测试通过!")

def test_service_layer():
    """测试 Service 层"""
    print("\n" + "=" * 60)
    print("测试 Service 层")
    print("=" * 60)
    
    storage_dir = Path("storage/test_repo")
    db_path = storage_dir / "test.db"
    data_dir = storage_dir / "data"
    
    # 1. 测试 AuthService
    print("\n1. 测试 AuthService")
    auth_service = AuthService(db_path, data_dir)
    
    # 注册新用户
    new_user_id = auth_service.register("service_test", "pass123", "service@test.com")
    print(f"   注册用户: {new_user_id}")
    
    # 登录
    login_result = auth_service.login("service_test", "pass123")
    print(f"   登录结果: {login_result}")
    
    # 2. 测试 DashboardService
    print("\n2. 测试 DashboardService")
    dashboard_service = DashboardService(db_path, data_dir)
    
    # 获取仪表盘数据
    dashboard = dashboard_service.get_dashboard_data(new_user_id)
    print(f"   仪表盘数据: total_questions={dashboard.total_questions}, level={dashboard.current_level}")
    
    # 更新连续打卡
    dashboard_service.update_streak(new_user_id)
    dashboard = dashboard_service.get_dashboard_data(new_user_id)
    print(f"   更新后连续打卡: {dashboard.streak_days}天")
    
    # 获取掌握度
    mastery = dashboard_service.calculate_mastery(new_user_id)
    print(f"   掌握度: {mastery}")
    
    # 3. 测试 MemoryService
    print("\n3. 测试 MemoryService")
    memory_service = MemoryService(db_path, data_dir)
    
    # 添加错题记录
    record_id = memory_service.add_error_record(new_user_id, {
        "question_id": "2024-数一-002",
        "question_type": "解答题",
        "knowledge_point": "线性代数 - 矩阵",
        "error_type": "计算错误",
        "difficulty": "较难",
        "student_answer": "计算错误",
        "score": 5,
        "max_score": 10,
    })
    print(f"   添加错题记录: {record_id}")
    
    # 获取画像
    profile = memory_service.get_profile(new_user_id)
    print(f"   获取画像: weak_points={profile.weak_points}")
    
    # 获取建议
    recommendations = memory_service.get_recommendations(new_user_id)
    print(f"   获取建议: {recommendations}")
    
    # 4. 测试 GradingService
    print("\n4. 测试 GradingService")
    grading_service = GradingService(db_path, data_dir)
    
    # 批改答案
    result = grading_service.grade_answer(new_user_id, "2024-数一-003", "我的答案", max_score=10)
    print(f"   批改结果: score={result.score}/{result.max_score}, correct={result.is_correct}")
    
    # 诊断错误
    diagnosis = grading_service.diagnose_error(new_user_id, "2024-数一-003", "错误答案")
    print(f"   诊断结果: error_type={diagnosis.error_type}")
    
    print("\n[OK] Service 层测试通过!")

if __name__ == "__main__":
    test_repository_layer()
    test_service_layer()
    
    print("\n" + "=" * 60)
    print("[OK] 所有测试通过!")
    print("=" * 60)
