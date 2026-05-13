"""Test the Q14 display issue."""
from latex_utils import split_latex_text

# Test the problematic text from user
text = r'设总体 $X$ 的概率密度为 $$f(x;\theta) = \left\{ \begin{array}{ll} \frac{2x}{3\theta^2}, & \theta < x < 2\theta \\ 0, & \text{其他} \end{array} \right.$$其中 $\theta$ 是未知参数，$X_1,X_2,\dots,X_n$ 为来自总体 $X$ 的简单随机样本，若 $c \sum_{i=1}^n X_i^2$ 是 $\theta^2$ 的无偏估计，则 $c=\underline{\qquad\qquad}$'
print("Original text:", repr(text))

# Test split
segments = split_latex_text(text)
print("\nSplit result:")
for seg in segments:
    print(f"  {seg}")
