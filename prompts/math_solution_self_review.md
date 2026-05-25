# 标准解答自检

对生成的标准解答进行 JSON 自检。只输出 JSON，不要解释。

```json
{
  "complete": true,
  "latex_ok": true,
  "has_final_conclusion": true,
  "covers_all_requirements": true,
  "missing_parts": [],
  "broken_latex_patterns": [],
  "should_regenerate": false,
  "brief_reason": ""
}
```

## 自检规则

1. **完整性**：证明题覆盖必要性/充分性；选择题解释正确选项和错误选项；填空题有完整计算和最终答案；解答题有完整推导链和最终结论。
2. **LaTeX**：检查 `\frac{}`、`\frac{分子}` 无分母、孤立 `}`、孤立 `}{`、`$$` 是否配对。
3. **结论**：是否包含明确结论语句（"综上/故/因此/即证/得证/证毕/故选/答案为"）。
4. **重生成判断**：如果 `complete=false` 或 `latex_ok=false` 或 `has_final_conclusion=false`，则 `should_regenerate=true`。
5. **只输出 JSON，不要解释**。
