"""verification_layer.py — 验证层 (Verification Layer)

负责验证数学的正确性，包括：
  1. Symbolic Equivalence - 符号等价判断
  2. Expression Legality - 表达式合法性检查
  3. Theorem Validity - 定理适用性验证
  4. Derivation Legality - 推导过程合法性验证

架构：
  ┌─────────────────────────────────────────────────────────────┐
  │                   Verification Layer                          │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │  │SymbolicVerify│  │ ExpressionCheck│ │ TheoremVerify │     │
  │  │   符号等价   │  │   表达式检查   │  │   定理验证   │     │
  │  └──────────────┘  └──────────────┘  └──────────────┘     │
  │                           │                                   │
  │  ┌──────────────┐  ┌──────────────┐                         │
  │  │DerivationCheck│  │ UnifiedVerifier│                        │
  │  │   推导验证   │  │    统一入口    │                        │
  │  └──────────────┘  └──────────────┘                         │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any, Callable

# 尝试导入 SymPy
try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False

from common_enums import ErrorLevel


# ═══════════════════════════════════════════════
# 错误级别定义已移至 common_enums
# ═══════════════════════════════════════════════


# ═══════════════════════════════════════════════
# 验证结果定义
# ═══════════════════════════════════════════════

@dataclass
class VerificationResult:
    """验证结果"""
    verified: bool                    # 是否通过验证
    error_level: ErrorLevel           # 错误级别
    method: str = ""                  # 验证方法
    message: str = ""                 # 验证消息
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    confidence: float = 1.0           # 验证置信度 0-1

    @property
    def is_correct(self) -> bool:
        return self.verified and self.error_level == ErrorLevel.CORRECT

    @property
    def is_warning(self) -> bool:
        return self.error_level == ErrorLevel.WARNING


@dataclass
class StepTransitionResult:
    """步骤转换验证结果"""
    from_step: str
    to_step: str
    from_output: str
    to_input: str
    verification: VerificationResult
    score: float = 1.0  # 0-1 衔接分数


@dataclass
class FullVerificationResult:
    """完整验证结果"""
    overall_verified: bool
    overall_score: float              # 总体得分 0-1
    error_level: ErrorLevel            # 最高错误级别
    step_transitions: List[StepTransitionResult] = field(default_factory=list)
    failed_steps: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    verification_log: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════
# 符号等价验证器
# ═══════════════════════════════════════════════

class SymbolicVerifier:
    """
    符号等价验证器

    使用多级策略验证两个数学表达式是否等价：
      Level 1: 字符串规范化比较
      Level 2: 数值采样（快速排除）
      Level 3: expand/factor 比较
      Level 4: simplify（最后手段）
    """

    def __init__(self):
        self._cache: Dict[Tuple[str, str], VerificationResult] = {}

    @staticmethod
    def _normalize_latex(s: str) -> str:
        """规范化 LaTeX 字符串"""
        if not s:
            return ""
        # 移除 $ 符号
        s = s.replace('$', '').replace('$$', '')
        # 规范化空格
        s = re.sub(r'\s+', '', s)
        # 小写化
        s = s.lower()
        return s

    @staticmethod
    def _convert_latex_to_sympy(s: str) -> Optional['sp.Expr']:
        """将 LaTeX 转换为 SymPy 表达式"""
        if not _HAS_SYMPY:
            return None

        s = s.strip()
        if not s:
            return None

        # 替换常见 LaTeX 命令
        replacements = {
            r'\sin': 'sin', r'\cos': 'cos', r'\tan': 'tan',
            r'\arctan': 'atan', r'\arcsin': 'asin', r'\arccos': 'acos',
            r'\ln': 'ln', r'\log': 'log', r'\exp': 'exp',
            r'\pi': 'pi', r'\infty': 'oo',
            r'\cdot': '*', r'\times': '*',
            r'\le': '<=', r'\ge': '>=', r'\ne': '!=',
            r'\alpha': 'alpha', r'\beta': 'beta', r'\gamma': 'gamma',
            r'\delta': 'delta', r'\theta': 'theta', r'\lambda': 'lambda',
            r'\sigma': 'sigma', r'\phi': 'phi', r'\omega': 'omega',
        }
        for latex, sympy in replacements.items():
            s = s.replace(latex, sympy)

        # 处理嵌套分数
        for _ in range(10):
            m = re.search(
                r'\\frac\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
                r'\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
                s
            )
            if not m:
                break
            num, den = m.group(1), m.group(2)
            s = s[:m.start()] + f'(({num})/({den}))' + s[m.end():]

        # 处理根号
        for _ in range(5):
            m = re.search(r'\\sqrt\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', s)
            if not m:
                break
            inner = m.group(1)
            s = s[:m.start()] + f'sqrt(({inner}))' + s[m.end():]

        # 清理剩余的 LaTeX 命令
        s = re.sub(r'\\[a-zA-Z]+', '', s)
        s = s.replace('{', '(').replace('}', ')')

        # 隐式乘法
        s = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', s)
        s = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', s)
        s = re.sub(r'\)\(', ')*(', s)
        s = re.sub(r'(\d)\(', r'\1*(', s)
        s = re.sub(r'\)(\d)', r')*\1', s)
        s = s.replace('e^', 'exp')

        try:
            return sp.sympify(s, evaluate=False)
        except Exception:
            return None

    def verify_equivalence(
        self,
        expr1: str,
        expr2: str,
        use_cache: bool = True
    ) -> VerificationResult:
        """
        验证两个表达式是否符号等价

        Args:
            expr1: 表达式1 (LaTeX 或普通文本)
            expr2: 表达式2
            use_cache: 是否使用缓存

        Returns:
            VerificationResult
        """
        cache_key = (expr1.strip(), expr2.strip())
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Level 1: 字符串规范化
        if self._normalize_latex(expr1) == self._normalize_latex(expr2):
            result = VerificationResult(
                verified=True,
                error_level=ErrorLevel.CORRECT,
                method="string_normalize",
                message="字符串规范化后相等"
            )
            self._cache[cache_key] = result
            return result

        # 无 SymPy 时只能做到 L1
        if not _HAS_SYMPY:
            return VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_1,
                method="string_normalize",
                message="无法解析表达式进行深度验证"
            )

        # 解析表达式
        parsed1 = self._convert_latex_to_sympy(expr1)
        parsed2 = self._convert_latex_to_sympy(expr2)

        if parsed1 is None:
            result = VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_1,
                method="parse_failed",
                message=f"无法解析表达式1: {expr1[:50]}"
            )
            self._cache[cache_key] = result
            return result

        if parsed2 is None:
            result = VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_1,
                method="parse_failed",
                message=f"无法解析表达式2: {expr2[:50]}"
            )
            self._cache[cache_key] = result
            return result

        # 计算差值
        diff = parsed1 - parsed2

        # Level 2: 数值采样
        numeric_result = self._numeric_sample(diff)
        if numeric_result is True:
            result = VerificationResult(
                verified=True,
                error_level=ErrorLevel.CORRECT,
                method="numeric_sample",
                message="数值采样验证通过"
            )
            self._cache[cache_key] = result
            return result
        elif numeric_result is False:
            result = VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_1,
                method="numeric_sample",
                message="数值采样验证失败"
            )
            self._cache[cache_key] = result
            return result

        # Level 3: expand/factor
        try:
            if sp.expand(diff) == 0:
                result = VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.CORRECT,
                    method="expand",
                    message="expand 验证通过"
                )
                self._cache[cache_key] = result
                return result
        except Exception:
            pass

        try:
            if sp.factor(diff) == 0:
                result = VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.CORRECT,
                    method="factor",
                    message="factor 验证通过"
                )
                self._cache[cache_key] = result
                return result
        except Exception:
            pass

        # Level 4: simplify
        try:
            diff_simplified = sp.simplify(diff)
            if diff_simplified == 0:
                result = VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.CORRECT,
                    method="simplify",
                    message="simplify 验证通过"
                )
                self._cache[cache_key] = result
                return result
        except Exception:
            pass

        # 不等价
        try:
            diff_str = str(sp.simplify(diff))
            message = f"差值不为零: {diff_str[:50]}"
        except Exception:
            message = "表达式不等价"

        result = VerificationResult(
            verified=False,
            error_level=ErrorLevel.LEVEL_1,
            method="simplify",
            message=message,
            details={"difference": str(diff) if diff else "unknown"}
        )
        self._cache[cache_key] = result
        return result

    @staticmethod
    def _numeric_sample(diff_expr, n_points: int = 5, radius: float = 2.0) -> Optional[bool]:
        """
        数值采样比较

        Returns:
            True: 采样范围内全部为零，认为等价
            False: 采样范围内有非零值，认为不等价
            None: 无法判断
        """
        if not _HAS_SYMPY:
            return None

        try:
            import random
            free_vars = list(diff_expr.free_symbols)
            if not free_vars:
                val = float(diff_expr.evalf())
                return abs(val) < 1e-10

            for _ in range(n_points):
                subs = {v: random.uniform(-radius, radius) for v in free_vars}
                val = float(diff_expr.subs(subs).evalf())
                if abs(val) > 1e-8:
                    return False
            return True
        except Exception:
            return None


# ═══════════════════════════════════════════════
# 表达式合法性检查器
# ═══════════════════════════════════════════════

class ExpressionChecker:
    """
    表达式合法性检查器

    检查：
      1. 表达式语法是否正确
      2. 定义域是否合法（如除零、分母为零等）
      3. 符号使用是否规范
    """

    # 常见非法模式
    ILLEGAL_PATTERNS = [
        (r'/0', "除以零"),
        (r'\/0', "除以零"),
        (r'\frac\s*\{[^}]*\}\s*\{\s*0\s*\}', "分数分母为零"),
        (r'log\s*\(\s*0\s*\)', "log(0) 无定义"),
        (r'ln\s*\(\s*0\s*\)', "ln(0) 无定义"),
        (r'\/\s*\(', "除以括号表达式"),
        (r'sqrt\s*\(\s*-', "负数开平方"),
        (r'\sqrt\s*\{[^}]*<0[^}]*\}', "根号内为负"),
    ]

    @classmethod
    def check_legality(cls, expr: str) -> VerificationResult:
        """
        检查表达式是否合法

        Args:
            expr: LaTeX 表达式

        Returns:
            VerificationResult
        """
        if not expr or not expr.strip():
            return VerificationResult(
                verified=True,
                error_level=ErrorLevel.CORRECT,
                method="empty",
                message="空表达式视为合法"
            )

        # 检查非法模式
        warnings = []
        for pattern, description in cls.ILLEGAL_PATTERNS:
            if re.search(pattern, expr):
                warnings.append(description)

        if warnings:
            return VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_1,
                method="illegal_pattern",
                message=f"发现非法模式: {', '.join(warnings)}",
                details={"warnings": warnings}
            )

        # 检查括号匹配
        if not cls._check_brackets(expr):
            return VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_1,
                method="bracket_mismatch",
                message="括号不匹配"
            )

        # 尝试解析
        if _HAS_SYMPY:
            try:
                from symbolic_executor import parse_expression
                parsed = parse_expression(expr)
                if parsed is None:
                    return VerificationResult(
                        verified=False,
                        error_level=ErrorLevel.LEVEL_1,
                        method="parse_failed",
                        message="表达式无法解析"
                    )
            except Exception:
                pass

        return VerificationResult(
            verified=True,
            error_level=ErrorLevel.CORRECT,
            method="legality_check",
            message="表达式合法"
        )

    @staticmethod
    def _check_brackets(s: str) -> bool:
        """检查括号是否匹配"""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        for c in s:
            if c in pairs:
                stack.append(c)
            elif c in pairs.values():
                if not stack:
                    return False
                if pairs.get(stack[-1]) != c:
                    return False
                stack.pop()
        return len(stack) == 0

    @classmethod
    def check_domain(cls, expr: str, assumptions: Dict[str, str] = None) -> VerificationResult:
        """
        检查定义域

        Args:
            expr: LaTeX 表达式
            assumptions: 定义域假设，如 {"x": "positive"}

        Returns:
            VerificationResult
        """
        if not _HAS_SYMPY:
            return VerificationResult(
                verified=True,
                error_level=ErrorLevel.WARNING,
                method="no_sympy",
                message="无 SymPy，无法验证定义域"
            )

        # 默认假设：所有变量为正
        if assumptions is None:
            assumptions = {}

        try:
            from symbolic_executor import parse_expression
            parsed = parse_expression(expr)
            if parsed is None:
                return VerificationResult(
                    verified=False,
                    error_level=ErrorLevel.LEVEL_1,
                    method="parse_failed",
                    message="无法解析表达式"
                )

            # 检查定义域问题
            issues = []

            # 1/x 型：x ≠ 0
            if re.search(r'\\frac\s*\{[^}]*\}\s*\{[^}]*\}', expr):
                issues.append("分母不为零")

            # sqrt(x) 型：x ≥ 0
            if '\\sqrt' in expr:
                issues.append("根号内非负")

            # log(x) 型：x > 0
            if '\\log' in expr or '\\ln' in expr:
                issues.append("对数真数大于零")

            if issues:
                return VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.WARNING,
                    method="domain_check",
                    message=f"需满足: {', '.join(issues)}",
                    details={"domain_issues": issues}
                )

            return VerificationResult(
                verified=True,
                error_level=ErrorLevel.CORRECT,
                method="domain_check",
                message="定义域检查通过"
            )

        except Exception as e:
            return VerificationResult(
                verified=False,
                error_level=ErrorLevel.WARNING,
                method="domain_check_error",
                message=f"定义域检查失败: {str(e)}"
            )


# ═══════════════════════════════════════════════
# 定理验证器
# ═══════════════════════════════════════════════

class TheoremVerifier:
    """
    定理验证器

    验证：
      1. 定理应用条件是否满足
      2. 定理使用是否正确
      3. 常见定理误用模式
    """

    # 常见定理及其适用条件
    THEOREM_CONDITIONS: Dict[str, Dict] = {
        "洛必达法则": {
            "conditions": ["0/0型", "∞/∞型", "分子分母可导"],
            "forbidden": ["非不定型", "分子分母不可导"],
            "error_patterns": [
                (r'洛必达.*0', "分子趋近于非零常数不能使用洛必达"),
            ]
        },
        "泰勒展开": {
            "conditions": ["函数无穷阶可导", "展开点选择"],
            "forbidden": ["不可导点展开"],
            "error_patterns": [
                (r'泰勒.*\^\s*\(', "高阶导数计算错误"),
            ]
        },
        "拉格朗日中值定理": {
            "conditions": ["闭区间连续", "开区间可导"],
            "forbidden": ["区间端点不连续"],
            "error_patterns": []
        },
        "牛顿-莱布尼茨公式": {
            "conditions": ["原函数存在", "积分区间有限"],
            "forbidden": ["原函数不存在"],
            "error_patterns": []
        },
    }

    @classmethod
    def verify_theorem_application(
        cls,
        theorem_name: str,
        conditions: List[str],
        context: str = ""
    ) -> VerificationResult:
        """
        验证定理应用是否正确

        Args:
            theorem_name: 定理名称
            conditions: 当前已满足的条件
            context: 应用上下文

        Returns:
            VerificationResult
        """
        theorem_info = cls.THEOREM_CONDITIONS.get(theorem_name, {})

        if not theorem_info:
            return VerificationResult(
                verified=True,
                error_level=ErrorLevel.WARNING,
                method="unknown_theorem",
                message=f"未知定理: {theorem_name}"
            )

        required = theorem_info.get("conditions", [])
        forbidden = theorem_info.get("forbidden", [])

        # 检查是否满足必要条件
        missing = [c for c in required if c not in conditions]
        if missing:
            return VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_3,
                method="theorem_condition",
                message=f"定理 {theorem_name} 的条件不满足: {', '.join(missing)}"
            )

        # 检查是否有禁忌情况
        violations = []
        for f in forbidden:
            if f in context:
                violations.append(f)

        if violations:
            return VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_3,
                method="theorem_violation",
                message=f"定理 {theorem_name} 使用禁忌: {', '.join(violations)}"
            )

        return VerificationResult(
            verified=True,
            error_level=ErrorLevel.CORRECT,
            method="theorem_check",
            message=f"定理 {theorem_name} 应用正确"
        )

    @classmethod
    def detect_theorem_errors(cls, text: str) -> List[VerificationResult]:
        """
        检测文本中的定理误用

        Args:
            text: 文本

        Returns:
            错误列表
        """
        errors = []

        for theorem_name, info in cls.THEOREM_CONDITIONS.items():
            for pattern, error_msg in info.get("error_patterns", []):
                if re.search(pattern, text):
                    errors.append(VerificationResult(
                        verified=False,
                        error_level=ErrorLevel.LEVEL_3,
                        method="theorem_error",
                        message=f"{theorem_name}: {error_msg}"
                    ))

        return errors


# ═══════════════════════════════════════════════
# 推导验证器
# ═══════════════════════════════════════════════

class DerivationVerifier:
    """
    推导验证器

    验证：
      1. 步骤之间的转换是否合理
      2. 操作应用是否正确
      3. 整体推导链是否闭合
    """

    def __init__(self):
        self.symbolic_verifier = SymbolicVerifier()
        self.expression_checker = ExpressionChecker()

    def verify_step_transition(
        self,
        from_output: str,
        to_input: str,
        operation: str = "compute"
    ) -> StepTransitionResult:
        """
        验证两步之间的转换

        Args:
            from_output: 前一步的输出
            to_input: 后一步的输入
            operation: 执行的操作

        Returns:
            StepTransitionResult
        """
        # 空状态检查
        if not from_output and not to_input:
            return StepTransitionResult(
                from_step="",
                to_step="",
                from_output=from_output,
                to_input=to_input,
                verification=VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.CORRECT,
                    method="empty",
                    message="空状态跳过验证"
                ),
                score=1.0
            )

        if not from_output:
            return StepTransitionResult(
                from_step="",
                to_step="",
                from_output=from_output,
                to_input=to_input,
                verification=VerificationResult(
                    verified=False,
                    error_level=ErrorLevel.LEVEL_2,
                    method="missing_output",
                    message="前一步输出为空"
                ),
                score=0.0
            )

        if not to_input:
            # 检查符号连续性
            score = self._check_symbol_continuity(from_output, "")
            return StepTransitionResult(
                from_step="",
                to_step="",
                from_output=from_output,
                to_input=to_input,
                verification=VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.WARNING,
                    method="missing_input",
                    message="后一步输入为空，但符号有连续性"
                ),
                score=score
            )

        # 策略1: 符号等价
        equiv_result = self.symbolic_verifier.verify_equivalence(from_output, to_input)
        if equiv_result.is_correct:
            return StepTransitionResult(
                from_step="",
                to_step="",
                from_output=from_output,
                to_input=to_input,
                verification=equiv_result,
                score=1.0
            )

        # 策略2: 符号包含（部分变换）
        score = self._check_symbol_overlap(from_output, to_input)
        if score >= 0.6:
            return StepTransitionResult(
                from_step="",
                to_step="",
                from_output=from_output,
                to_input=to_input,
                verification=VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.WARNING,
                    method="partial_transformation",
                    message="符号部分变换，转换可能合理"
                ),
                score=score
            )

        # 策略3: 操作验证
        op_result = self._verify_operation(from_output, to_input, operation)
        if op_result.is_correct:
            return StepTransitionResult(
                from_step="",
                to_step="",
                from_output=from_output,
                to_input=to_input,
                verification=op_result,
                score=0.9
            )

        return StepTransitionResult(
            from_step="",
            to_step="",
            from_output=from_output,
            to_input=to_input,
            verification=VerificationResult(
                verified=False,
                error_level=ErrorLevel.LEVEL_2,
                method="transition_failed",
                message=f"推导跳跃过大"
            ),
            score=0.2
        )

    def _check_symbol_continuity(self, from_output: str, to_input: str) -> float:
        """检查符号连续性"""
        if not from_output:
            return 0.5

        symbols1 = set(re.findall(r'[a-zA-Z]+', from_output))
        symbols2 = set(re.findall(r'[a-zA-Z]+', to_input)) if to_input else set()

        if not symbols1:
            return 0.5

        overlap = len(symbols1 & symbols2)
        total = len(symbols1 | symbols2) if symbols2 else len(symbols1)

        return overlap / total if total > 0 else 0.5

    def _check_symbol_overlap(self, expr1: str, expr2: str) -> float:
        """检查符号重叠度"""
        symbols1 = set(re.findall(r'[a-zA-Z]+', expr1))
        symbols2 = set(re.findall(r'[a-zA-Z]+', expr2))

        if not symbols1 or not symbols2:
            return 0.0

        overlap = len(symbols1 & symbols2)
        union = len(symbols1 | symbols2)

        return overlap / union if union > 0 else 0.0

    def _verify_operation(
        self,
        input_expr: str,
        output_expr: str,
        operation: str
    ) -> VerificationResult:
        """验证操作是否正确应用"""
        if not _HAS_SYMPY:
            return VerificationResult(
                verified=True,
                error_level=ErrorLevel.WARNING,
                method="no_sympy",
                message="无 SymPy，无法验证操作"
            )

        try:
            from symbolic_executor import parse_expression
            p_expr = parse_expression(input_expr)
            o_expr = parse_expression(output_expr)

            if p_expr is None or o_expr is None:
                return VerificationResult(
                    verified=True,
                    error_level=ErrorLevel.WARNING,
                    method="parse_failed",
                    message="表达式无法解析"
                )

            # 求导操作
            if operation in ("differentiate", "diff", "求导"):
                result = sp.diff(p_expr)
                if sp.simplify(result - o_expr) == 0:
                    return VerificationResult(
                        verified=True,
                        error_level=ErrorLevel.CORRECT,
                        method="derivative_check",
                        message="求导验证通过"
                    )

            # 积分操作
            elif operation in ("integrate", "积分"):
                result = sp.integrate(p_expr)
                if sp.simplify(result - o_expr) == 0:
                    return VerificationResult(
                        verified=True,
                        error_level=ErrorLevel.CORRECT,
                        method="integral_check",
                        message="积分验证通过"
                    )

        except Exception:
            pass

        return VerificationResult(
            verified=True,
            error_level=ErrorLevel.WARNING,
            method="operation_unverifiable",
            message="操作无法验证"
        )

    def verify_full_derivation(
        self,
        steps: List[Dict],
        final_answer: str = ""
    ) -> FullVerificationResult:
        """
        验证完整推导链

        Args:
            steps: 步骤列表 [{"output_state": "", "input_state": "", "operation": ""}]
            final_answer: 最终答案

        Returns:
            FullVerificationResult
        """
        if not steps:
            return FullVerificationResult(
                overall_verified=False,
                overall_score=0.0,
                error_level=ErrorLevel.LEVEL_0,
                warnings=["没有可验证的步骤"]
            )

        step_transitions = []
        failed_steps = []
        transition_scores = []
        max_error_level = ErrorLevel.CORRECT

        for i in range(1, len(steps)):
            prev = steps[i - 1]
            curr = steps[i]

            result = self.verify_step_transition(
                from_output=prev.get("output_state", ""),
                to_input=curr.get("input_state", ""),
                operation=curr.get("operation", "compute")
            )

            step_transitions.append(result)
            transition_scores.append(result.score)

            if not result.verification.is_correct:
                failed_steps.append({
                    "step": i,
                    "from_output": result.from_output,
                    "to_input": result.to_input,
                    "reason": result.verification.message
                })
                if result.verification.error_level.value > max_error_level.value:
                    max_error_level = result.verification.error_level

        # 验证最终答案
        if final_answer and steps[-1].get("output_state"):
            final_result = self.symbolic_verifier.verify_equivalence(
                steps[-1].get("output_state", ""),
                final_answer
            )
            if not final_result.is_correct:
                failed_steps.append({
                    "step": "final",
                    "from_output": steps[-1].get("output_state", ""),
                    "to_input": final_answer,
                    "reason": "最终答案不匹配"
                })
                if final_result.error_level.value > max_error_level.value:
                    max_error_level = final_result.error_level

        # 计算总体得分
        avg_score = sum(transition_scores) / len(transition_scores) if transition_scores else 0.0

        # 检查推导闭合
        has_start = bool(steps[0].get("input_state") or steps[0].get("output_state"))
        has_end = bool(steps[-1].get("output_state"))
        closure_score = 1.0 if (has_start and has_end) else 0.5

        overall_score = avg_score * 0.7 + closure_score * 0.3

        return FullVerificationResult(
            overall_verified=len(failed_steps) == 0,
            overall_score=round(overall_score, 2),
            error_level=max_error_level,
            step_transitions=step_transitions,
            failed_steps=failed_steps
        )


# ═══════════════════════════════════════════════
# 统一验证入口
# ═══════════════════════════════════════════════

class UnifiedVerifier:
    """
    统一验证入口

    整合所有验证功能，提供统一接口
    """

    def __init__(self):
        self.symbolic_verifier = SymbolicVerifier()
        self.expression_checker = ExpressionChecker()
        self.theorem_verifier = TheoremVerifier()
        self.derivation_verifier = DerivationVerifier()

    def verify_expression_equivalence(
        self,
        student_expr: str,
        standard_expr: str
    ) -> VerificationResult:
        """验证表达式等价"""
        return self.symbolic_verifier.verify_equivalence(student_expr, standard_expr)

    def verify_step_transition(
        self,
        from_output: str,
        to_input: str,
        operation: str = "compute"
    ) -> StepTransitionResult:
        """验证步骤转换"""
        return self.derivation_verifier.verify_step_transition(
            from_output, to_input, operation
        )

    def verify_full_derivation(
        self,
        steps: List[Dict],
        final_answer: str = ""
    ) -> FullVerificationResult:
        """验证完整推导"""
        return self.derivation_verifier.verify_full_derivation(steps, final_answer)

    def check_expression_legality(self, expr: str) -> VerificationResult:
        """检查表达式合法性"""
        return self.expression_checker.check_legality(expr)

    def verify_theorem(
        self,
        theorem_name: str,
        conditions: List[str],
        context: str = ""
    ) -> VerificationResult:
        """验证定理应用"""
        return self.theorem_verifier.verify_theorem_application(
            theorem_name, conditions, context
        )

    def full_verify(
        self,
        student_answer: str,
        standard_answer: str,
        steps: List[Dict] = None,
        final_answer: str = ""
    ) -> FullVerificationResult:
        """
        完整验证

        综合验证学生作答的正确性
        """
        results = FullVerificationResult(
            overall_verified=True,
            overall_score=1.0,
            error_level=ErrorLevel.CORRECT
        )

        # 1. 表达式等价验证
        if student_answer and standard_answer:
            expr_result = self.verify_expression_equivalence(student_answer, standard_answer)
            if not expr_result.is_correct:
                results.overall_verified = False
                results.error_level = expr_result.error_level
                results.failed_steps.append({
                    "type": "expression_equivalence",
                    "student": student_answer,
                    "standard": standard_answer,
                    "reason": expr_result.message
                })

        # 2. 步骤转换验证
        if steps and len(steps) >= 2:
            derivation_result = self.verify_full_derivation(steps, final_answer)
            results.step_transitions = derivation_result.step_transitions
            if not derivation_result.overall_verified:
                results.overall_verified = False
                if derivation_result.error_level.value > results.error_level.value:
                    results.error_level = derivation_result.error_level
            results.failed_steps.extend(derivation_result.failed_steps)
            results.overall_score *= derivation_result.overall_score

        return results


# ═══════════════════════════════════════════════
# 全局实例
# ═══════════════════════════════════════════════

_verifier: Optional[UnifiedVerifier] = None


def get_verifier() -> UnifiedVerifier:
    """获取验证器全局实例"""
    global _verifier
    if _verifier is None:
        _verifier = UnifiedVerifier()
    return _verifier


# ═══════════════════════════════════════════════
# 示例用法
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    verifier = get_verifier()

    print("=== 表达式等价验证 ===")
    result = verifier.verify_expression_equivalence("x^2 + 2x + 1", "(x+1)^2")
    print(f"x^2 + 2x + 1 vs (x+1)^2: {result.verified} ({result.method})")
    print(f"错误级别: {result.error_level.label}")

    result = verifier.verify_expression_equivalence("sin(x)^2 + cos(x)^2", "1")
    print(f"sin²x + cos²x vs 1: {result.verified} ({result.method})")

    print("\n=== 表达式合法性检查 ===")
    result = verifier.check_expression_legality(r"\frac{x}{0}")
    print(f"\\frac{{x}}{{0}}: {result.verified}, {result.message}")

    result = verifier.check_expression_legality(r"\frac{x^2 - 1}{x - 1}")
    print(f"\\frac{{x^2-1}}{{x-1}}: {result.verified}, {result.message}")

    print("\n=== 步骤转换验证 ===")
    result = verifier.verify_step_transition(
        from_output="x^2 - 1",
        to_input="(x+1)(x-1)",
        operation="factor"
    )
    print(f"x²-1 → (x+1)(x-1): verified={result.verification.verified}, score={result.score}")

    print("\n=== 完整推导验证 ===")
    steps = [
        {"output_state": "x^2 - 1", "input_state": "", "operation": "expand"},
        {"output_state": "(x+1)(x-1)", "input_state": "x^2 - 1", "operation": "factor"},
        {"output_state": "x = 1 或 x = -1", "input_state": "(x+1)(x-1) = 0", "operation": "solve_equation"},
    ]
    result = verifier.verify_full_derivation(steps, "x = ±1")
    print(f"总体验证: {result.overall_verified}")
    print(f"总体得分: {result.overall_score}")
    print(f"错误级别: {result.error_level.label}")
    print(f"失败步骤: {len(result.failed_steps)}")
