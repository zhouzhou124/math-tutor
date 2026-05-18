"""测试等式系统与重写策略的集成"""
from latex_engine import *
from latex_engine.parselet import parse_with_pratt

print("=" * 70)
print("Equational Kernel 与 Rewrite Strategy 集成测试")
print("=" * 70)

# 创建等式系统
system = create_std_equality_system()

print("\n1. 可用定理:")
for name, theorem in system.theorems.items():
    print(f"   {name}: {theorem.equality}")

print("\n2. 等价性查询:")
x = ExprCache.symbol("x")
zero = ExprCache.number(0)
one = ExprCache.number(1)

# 测试各种等价关系
test_cases = [
    (ExprCache.add([x, zero]), x, "x+0 ≡ x"),
    (ExprCache.mul([x, one]), x, "x*1 ≡ x"),
    (ExprCache.add([x, zero]), ExprCache.add([zero, x]), "x+0 ≡ 0+x"),
    (ExprCache.mul([x, one]), ExprCache.mul([one, x]), "x*1 ≡ 1*x"),
]

for expr1, expr2, desc in test_cases:
    result = system.are_equivalent(expr1, expr2)
    status = "[成立]" if result else "[不成立]"
    print(f"   {desc}: {status}")

print("\n3. 从定理创建重写规则:")
# 获取加法单位元定理
add_id = system.theorems["additive_identity"]
print(f"   定理: {add_id}")

# 展示如何将等式定向化为重写规则
lhs_cost = DefaultCostModel().cost(add_id.equality.lhs)
rhs_cost = DefaultCostModel().cost(add_id.equality.rhs)
print(f"   LHS代价: {lhs_cost}, RHS代价: {rhs_cost}")
direction = "lhs -> rhs" if lhs_cost > rhs_cost else "rhs -> lhs"
print(f"   定向: {direction}")

print("\n4. 完整重写流程:")
# 解析表达式
ast = parse_with_pratt("(x+0)*1")
expr = from_ast(ast)
print(f"   输入: {expr}")

# 使用重写策略
rules = RuleSet()
rules.add(create_rule(
    'Additive Identity',
    Pattern(op=Op.ADD, args=[Pattern.var('x'), Pattern.lit(0)]),
    Pattern.var('x')
))
rules.add(create_rule(
    'Multiplicative Identity',
    Pattern(op=Op.MUL, args=[Pattern.var('x'), Pattern.lit(1)]),
    Pattern.var('x')
))

context = create_proof_context()
strategy = RepeatStrategy(BottomUpStrategy(rules))
result = strategy.apply(expr, context)
print(f"   输出: {result.expr}")

# 验证等价性
# 注意：需要使用 ExprCache 创建相同结构的表达式进行比较
expr_simplified = ExprCache.mul([ExprCache.add([x, zero]), one])
result_expr = result.expr
print(f"   等价性验证: {system.are_equivalent(expr_simplified, result_expr)}")

print("\n5. 证明生成:")
if context.trace:
    print(context.trace.to_latex())

print("\n" + "=" * 70)
print("集成测试完成！")
print("=" * 70)
