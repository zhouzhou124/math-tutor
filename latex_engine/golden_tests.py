"""Golden Test Suite - 黄金测试套件

用于验证解析器行为的回归测试集合。
"""

import unittest
from typing import List, Dict, Any, Optional, Tuple

from latex_engine.lexer import LaTeXLexer, Token, TokenType
from latex_engine.parser import parse_latex
from latex_engine.parselet import parse_with_pratt
from latex_engine.ast import *
from latex_engine.validator import validate_ast
from latex_engine.printer import pp_ast, ast_to_string


# ═══════════════════════════════════════════════
# 测试用例定义
# ═══════════════════════════════════════════════

class TestCase:
    """测试用例"""
    
    def __init__(self, 
                 name: str,
                 input_expr: str,
                 expected_type: Optional[str] = None,
                 expected_ast: Optional[str] = None,
                 valid: bool = True,
                 description: str = ""):
        self.name = name
        self.input_expr = input_expr
        self.expected_type = expected_type
        self.expected_ast = expected_ast
        self.valid = valid
        self.description = description
    
    def __repr__(self):
        return f"TestCase({self.name}, '{self.input_expr}')"


# ═══════════════════════════════════════════════
# 黄金测试用例集合
# ═══════════════════════════════════════════════

GOLDEN_TEST_CASES = [
    # ════════════════════════════════════════════
    # 基础表达式
    # ════════════════════════════════════════════
    TestCase(
        name="simple_symbol",
        input_expr="x",
        expected_type="SymbolNode",
        description="简单符号"
    ),
    TestCase(
        name="integer",
        input_expr="2",
        expected_type="NumberNode",
        description="整数"
    ),
    TestCase(
        name="decimal",
        input_expr="3.14",
        expected_type="NumberNode",
        description="小数"
    ),
    
    # ════════════════════════════════════════════
    # 二元运算
    # ════════════════════════════════════════════
    TestCase(
        name="addition",
        input_expr="x+y",
        expected_type="AddNode",
        description="加法"
    ),
    TestCase(
        name="subtraction",
        input_expr="x-y",
        expected_type="SubtractNode",
        description="减法"
    ),
    TestCase(
        name="multiplication",
        input_expr="x*y",
        expected_type="MultiplyNode",
        description="乘法"
    ),
    TestCase(
        name="division",
        input_expr="x/y",
        expected_type="DivideNode",
        description="除法"
    ),
    TestCase(
        name="power",
        input_expr="x^2",
        expected_type="PowerNode",
        description="幂运算"
    ),
    
    # ════════════════════════════════════════════
    # 运算符优先级
    # ════════════════════════════════════════════
    TestCase(
        name="precedence_add_mult",
        input_expr="x+y*z",
        expected_type="AddNode",
        description="加法和乘法优先级"
    ),
    TestCase(
        name="precedence_mult_power",
        input_expr="x*y^2",
        expected_type="MultiplyNode",
        description="乘法和幂运算优先级"
    ),
    TestCase(
        name="precedence_power_right",
        input_expr="x^y^z",
        expected_type="PowerNode",
        description="幂运算右结合"
    ),
    
    # ════════════════════════════════════════════
    # 一元运算
    # ════════════════════════════════════════════
    TestCase(
        name="unary_negation",
        input_expr="-x",
        expected_type="NegateNode",
        description="一元负号"
    ),
    TestCase(
        name="unary_positive",
        input_expr="+x",
        expected_type="SymbolNode",
        description="一元正号"
    ),
    TestCase(
        name="double_negation",
        input_expr="--x",
        expected_type="NegateNode",
        description="双重否定"
    ),
    
    # ════════════════════════════════════════════
    # 函数调用
    # ════════════════════════════════════════════
    TestCase(
        name="function_sin",
        input_expr="sin(x)",
        expected_type="FunctionNode",
        description="正弦函数"
    ),
    TestCase(
        name="function_cos",
        input_expr="cos(x)",
        expected_type="FunctionNode",
        description="余弦函数"
    ),
    TestCase(
        name="function_sqrt",
        input_expr="sqrt(x)",
        expected_type="FunctionNode",
        description="平方根函数"
    ),
    TestCase(
        name="function_exp",
        input_expr="exp(x)",
        expected_type="FunctionNode",
        description="指数函数"
    ),
    TestCase(
        name="function_log",
        input_expr="log(x)",
        expected_type="FunctionNode",
        description="对数函数"
    ),
    
    # ════════════════════════════════════════════
    # 隐式乘法
    # ════════════════════════════════════════════
    TestCase(
        name="implicit_mult_number_symbol",
        input_expr="2x",
        expected_type="MultiplyNode",
        description="数字和符号隐式乘法"
    ),
    TestCase(
        name="implicit_mult_symbol_symbol",
        input_expr="xy",
        expected_type="MultiplyNode",
        description="符号和符号隐式乘法"
    ),
    TestCase(
        name="implicit_mult_symbol_paren",
        input_expr="x(y+1)",
        expected_type="MultiplyNode",
        description="符号和括号隐式乘法"
    ),
    
    # ════════════════════════════════════════════
    # 分组
    # ════════════════════════════════════════════
    TestCase(
        name="group_parentheses",
        input_expr="(x+y)",
        expected_type="GroupNode",
        description="圆括号分组"
    ),
    TestCase(
        name="group_nested",
        input_expr="(x+(y*z))",
        expected_type="GroupNode",
        description="嵌套分组"
    ),
    
    # ════════════════════════════════════════════
    # 复杂表达式
    # ════════════════════════════════════════════
    TestCase(
        name="complex_expr_1",
        input_expr="x+y*z/w",
        expected_type="AddNode",
        description="复杂表达式1"
    ),
    TestCase(
        name="complex_expr_2",
        input_expr="(x+y)/(z+1)",
        expected_type="DivideNode",
        description="复杂表达式2"
    ),
    TestCase(
        name="complex_expr_3",
        input_expr="x^2+y^2",
        expected_type="AddNode",
        description="复杂表达式3"
    ),
    
    # ════════════════════════════════════════════
    # 等式和不等式
    # ════════════════════════════════════════════
    TestCase(
        name="equation",
        input_expr="x=y",
        expected_type="EquationNode",
        description="等式"
    ),
    TestCase(
        name="inequality_less",
        input_expr="x<y",
        expected_type="EquationNode",
        description="小于"
    ),
    TestCase(
        name="inequality_greater",
        input_expr="x>y",
        expected_type="EquationNode",
        description="大于"
    ),
    
    # ════════════════════════════════════════════
    # 三角函数组合
    # ════════════════════════════════════════════
    TestCase(
        name="sin_squared",
        input_expr="sin(x)^2",
        expected_type="PowerNode",
        description="正弦平方"
    ),
    TestCase(
        name="sin_plus_cos",
        input_expr="sin(x)+cos(x)",
        expected_type="AddNode",
        description="正弦加余弦"
    ),
]


# ═══════════════════════════════════════════════
# 测试执行器
# ═══════════════════════════════════════════════

class TestResult:
    """测试结果"""
    
    def __init__(self, test_case: TestCase):
        self.test_case = test_case
        self.success = False
        self.error = None
        self.ast = None
        self.node_type = None
        self.validation_errors = []
    
    def __repr__(self):
        status = "PASS" if self.success else "FAIL"
        return f"TestResult({self.test_case.name}, {status})"


def run_test_case(test_case: TestCase, use_pratt: bool = False) -> TestResult:
    """运行单个测试用例"""
    result = TestResult(test_case)
    
    try:
        # 解析表达式
        if use_pratt:
            ast = parse_with_pratt(test_case.input_expr)
        else:
            ast = parse_latex(test_case.input_expr)
        
        result.ast = ast
        result.node_type = type(ast).__name__
        
        # 验证 AST
        validator = validate_ast(ast)
        if not validator:
            # 获取验证错误
            pass
        
        # 检查预期类型
        if test_case.expected_type:
            if result.node_type == test_case.expected_type:
                result.success = True
            else:
                result.error = f"Expected type '{test_case.expected_type}', got '{result.node_type}'"
        else:
            result.success = True
        
    except Exception as e:
        result.error = str(e)
    
    return result


def run_all_tests(use_pratt: bool = False) -> Tuple[List[TestResult], int, int]:
    """运行所有测试用例"""
    results = []
    passed = 0
    failed = 0
    
    for test_case in GOLDEN_TEST_CASES:
        result = run_test_case(test_case, use_pratt)
        results.append(result)
        
        if result.success:
            passed += 1
        else:
            failed += 1
    
    return results, passed, failed


def print_test_results(results: List[TestResult]):
    """打印测试结果"""
    print("=" * 70)
    print("Golden Test Suite Results")
    print("=" * 70)
    
    for result in results:
        status = "[PASS]" if result.success else "[FAIL]"
        print(f"{status} {result.test_case.name}: {result.test_case.input_expr}")
        
        if not result.success:
            print(f"      Error: {result.error}")
            if result.ast:
                print(f"      Got AST: {result.node_type}")
    
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    
    print("\n" + "=" * 70)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 70)


# ═══════════════════════════════════════════════
# 单元测试类
# ═══════════════════════════════════════════════

class GoldenTests(unittest.TestCase):
    """黄金测试单元测试类"""
    
    def test_all_cases(self):
        """运行所有黄金测试用例"""
        results, passed, failed = run_all_tests()
        self.assertEqual(failed, 0, f"{failed} tests failed")


# ═══════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    # 运行测试
    results, passed, failed = run_all_tests(use_pratt=True)
    print_test_results(results)
    
    # 对于失败的测试，打印 AST 结构
    print("\n--- Failed Tests AST Details ---")
    for result in results:
        if not result.success and result.ast:
            print(f"\nTest: {result.test_case.name}")
            print(f"Input: {result.test_case.input_expr}")
            print("AST:")
            pp_ast(result.ast)