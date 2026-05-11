# Math Tutor

考研数学智能辅导系统，包含题库管理、OCR 文本修复、真题解析、离线/在线批改、错题记忆与学习画像。

## 启动

```powershell
pip install -r requirements.txt
streamlit run app.py
```

## LLM 配置

API Key 不再写入 `storage/settings.json`。需要持久化时请使用环境变量：

```powershell
$env:LLM_API_KEY="sk-..."
$env:LLM_BASE_URL="https://api.deepseek.com"
$env:LLM_MODEL="deepseek-v4-pro"
```

页面里的系统设置只保存 `base_url` 和 `model`，API Key 只存在当前会话或环境变量中。

## 验证

```powershell
python -m compileall -q .
python tests\benchmark\run_benchmark.py
python tools\question_health.py
```

## 数据口径

当前项目只以 `storage/questions/data` 里的活动题库为准。历史 756/791 题构建产物不再作为数据源。

