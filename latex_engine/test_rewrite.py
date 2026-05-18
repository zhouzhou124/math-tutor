"""Rewrite Engine Tests - 重写引擎测试套件"""

import unittest
from typing import List, Tuple

from latex_engine.parselet import parse_with_pratt
from latex_engine.rewrite import (
    RewriteEngine, RewriteRule, PatternVar, PatternLiteral, PatternAdd,
    PatternMultiply, PatternPower, PatternSymbol, PatternFunction,
    create_default_rules, parse_rule, rewrite, nodes_equal
)


class TestPatternMatching(unittest.TestCase):
    """模式匹配测试"""
    
    def test_pattern_var_match(self):
        """测试模式变量匹配"""
        pattern = PatternVar("X")
        node = parse_with_pratt("x")
        
        bindings = pattern.match(node, {})
        self.assertIsNotNone(bindings)
        self.assertIn("X", bindings)
    
    def test_pattern_literal_match(self):
        """测试字面量匹配"""
        pattern = PatternLiteral(0)
        node = parse_with_pratt("0")
        
        bindings = pattern.match(node, {})
        self.assertIsNotNone(bindings)
    
    def test_pattern_add_match(self):
        """测试加法模式匹配"""
        pattern = PatternAdd(PatternVar("X"), PatternLiteral(0))
        node = parse_with_pratt("x+0")
        
        bindings = pattern.match(node, {})
        self.assertIsNotNone(bindings)
        self.assertIn("X", bindings)
    
    def test_pattern_add_commutative(self):
        """测试加法交换律匹配"""
        pattern = PatternAdd(PatternVar("X"), PatternLiteral(0))
        node = parse_with_pratt("0+x")
        
        bindings = pattern.match(node, {})
        self.assertIsNotNone(bindings)
        self.assertIn("X", bindings)


class TestRewriteRules(unittest.TestCase):
    """重写规则测试"""
    
    def test_additive_identity(self):
        """测试加法恒等元"""
        rule = parse_rule("X + 0 -> X")
        node = parse_with_pratt("x+0")
        
        result = rule.apply(node)
        self.assertIsNotNone(result)
        self.assertEqual(result.to_latex(), "x")
    
    def test_multiplicative_identity(self):
        """测试乘法恒等元"""
        rule = parse_rule("X * 1 -> X")
        node = parse_with_pratt("x*1")
        
        result = rule.apply(node)
        self.assertIsNotNone(result)
        self.assertEqual(result.to_latex(), "x")
    
    def test_combine_like_terms(self):
        """测试合并同类项"""
        rule = parse_rule("X + X -> 2 * X")
        node = parse_with_pratt("x+x")
        
        result = rule.apply(node)
        self.assertIsNotNone(result)
        self.assertEqual(result.to_latex(), "2x")


class TestRewriteEngine(unittest.TestCase):
    """重写引擎测试"""
    
    def test_chain_rewrite(self):
        """测试链式重写"""
        engine = RewriteEngine()
        engine.add_rules(create_default_rules())
        
        node = parse_with_pratt("(x+0)*1")
        result, steps = engine.rewrite(node)
        
        self.assertEqual(result.to_latex(), "x")
        self.assertGreater(len(steps), 0)
    
    def test_multiple_rules(self):
        """测试多规则应用"""
        engine = RewriteEngine()
        engine.add_rules(create_default_rules())
        
        # 测试 x+x+0 -> 2x
        node = parse_with_pratt("x+x+0")
        result, steps = engine.rewrite(node)
        
        self.assertEqual(result.to_latex(), "2x")


class TestRuleDSL(unittest.TestCase):
    """规则 DSL 测试"""
    
    def test_parse_simple_rule(self):
        """测试解析简单规则"""
        rule = parse_rule("X + 0 -> X")
        self.assertIsInstance(rule, RewriteRule)
        self.assertEqual(rule.name, "")
    
    def test_parse_rule_with_comment(self):
        """测试解析带注释的规则"""
        rule = parse_rule("X + 0 -> X /* Additive Identity */")
        self.assertEqual(rule.name, "Additive Identity")
    
    def test_parse_function_rule(self):
        """测试解析函数规则"""
        rule = parse_rule("sin(X)^2 + cos(X)^2 -> 1")
        self.assertIsInstance(rule, RewriteRule)


class TestNodesEqual(unittest.TestCase):
    """节点相等性测试"""
    
    def test_same_symbols_equal(self):
        """测试相同符号相等"""
        node1 = parse_with_pratt("x")
        node2 = parse_with_pratt("x")
        self.assertTrue(nodes_equal(node1, node2))
    
    def test_different_symbols_not_equal(self):
        """测试不同符号不相等"""
        node1 = parse_with_pratt("x")
        node2 = parse_with_pratt("y")
        self.assertFalse(nodes_equal(node1, node2))
    
    def test_same_expressions_equal(self):
        """测试相同表达式相等"""
        node1 = parse_with_pratt("x+y")
        node2 = parse_with_pratt("x+y")
        self.assertTrue(nodes_equal(node1, node2))


# ═══════════════════════════════════════════════
# 功能测试
# ═══════════════════════════════════════════════

def run_functional_tests():
    """运行功能测试"""
    print("=" * 70)
    print("Rewrite Engine - 功能测试")
    print("=" * 70)
    
    test_cases = [
        ("x+0", "x", "加法恒等元"),
        ("0+x", "x", "加法恒等元（交换）"),
        ("x*1", "x", "乘法恒等元"),
        ("1*x", "x", "乘法恒等元（交换）"),
        ("x+x", "2x", "合并同类项"),
        ("(x+0)*1", "x", "链式重写"),
    ]
    
    engine = RewriteEngine()
    engine.add_rules(create_default_rules())
    
    passed = 0
    failed = 0
    
    for input_expr, expected, description in test_cases:
        try:
            node = parse_with_pratt(input_expr)
            result, steps = engine.rewrite(node)
            actual = result.to_latex()
            
            if actual == expected:
                print("OK: %s: %s -> %s" % (description, input_expr, actual))
                passed += 1
            else:
                print("FAIL: %s: %s -> %s (期望: %s)" % (description, input_expr, actual, expected))
                failed += 1
        except Exception as e:
            print("FAIL: %s: %s -> 错误: %s" % (description, input_expr, e))
            failed += 1
    
    print("\n" + "=" * 70)
    print("通过: %d, 失败: %d" % (passed, failed))
    print("=" * 70)


if __name__ == "__main__":
    # 运行功能测试
    run_functional_tests()
    
    # 运行单元测试
    print("\n运行单元测试...")
    unittest.main(verbosity=2)