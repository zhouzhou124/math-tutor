from services.grading_adapter import (
    repair_derivation_text_block,
    repair_ai_grading_math_artifacts,
    normalize_math_delimiters_in_text,
    normalize_cases_spacing,
    normalize_differential_tokens,
)

body = (
    "中间公式为：\n\n$$\nf_x=2x(2+y^2)\n$$\n\n"
    "因此本步得到结论：\n\n$$\nf_y=2x^2y+\\ln y+1\n$$"
)
s = body
for name, fn in [
    ("derivation", repair_derivation_text_block),
    ("ai", repair_ai_grading_math_artifacts),
    ("delim", normalize_math_delimiters_in_text),
    ("cases", normalize_cases_spacing),
    ("diff", normalize_differential_tokens),
]:
    s2 = fn(s)
    print(name, "count $$", s2.count("$$"), repr(s2[:70]))
    s = s2