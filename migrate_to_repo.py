"""数据迁移脚本 - 从旧版 JSON 格式迁移到 Repository Layer"""

import os
import sys

def main():
    # 添加项目路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from repository import Repository
    from config import ERROR_NOTEBOOK_PATH, STUDENT_PROFILE_PATH
    
    print("开始数据迁移...")
    
    # 创建 Repository 实例（会自动创建数据库）
    repo = Repository()
    
    # 执行迁移
    repo.migrate_from_legacy(ERROR_NOTEBOOK_PATH, STUDENT_PROFILE_PATH)
    
    print("数据迁移完成！")
    
    # 验证迁移结果
    dashboard = repo.get_dashboard_data("user_default")
    print(f"迁移后的用户统计：")
    print(f"  - 总题目数: {dashboard.total_questions}")
    print(f"  - 总错题数: {dashboard.total_errors}")
    print(f"  - 正确率: {dashboard.overall_accuracy:.2%}")
    print(f"  - 当前阶段: {dashboard.current_level}")

if __name__ == "__main__":
    main()
