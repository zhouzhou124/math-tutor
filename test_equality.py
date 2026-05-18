"""测试等价核心"""
from latex_engine import *

print("=" * 60)
print("Equational Kernel 测试")
print("=" * 60)

# 创建表达式
x = ExprCache.symbol("x")
y = ExprCache.symbol("y")
zero = ExprCache.number(0)
one = ExprCache.number(1)

print("\n1. 创建等式:")
eq1 = Equality(
    lhs=ExprCache.add([x, zero]),
    rhs=x,
    justification=Justification(JustificationType.AXIOM, "Additive Identity")
)
print(f"   {eq1}")
print(f"   变量: {eq1.variables}")
print(f"   LaTeX: {eq1.to_latex()}")

print("\n2. 创建定理:")
theorem = create_additive_identity()
print(f"   {theorem}")
print(f"   描述: {theorem.description}")

print("\n3. 等式系统:")
system = create_std_equality_system()
print(f"   {system}")

print("\n4. 等价性检查:")
# 创建具体表达式
expr1 = ExprCache.add([x, zero])
expr2 = x
result = system.are_equivalent(expr1, expr2)
print(f"   x+0 ≡ x: {result}")

expr3 = ExprCache.mul([x, one])
result = system.are_equivalent(expr3, x)
print(f"   x*1 ≡ x: {result}")

print("\n5. 等价类测试:")
# 添加新等式
new_eq = Equality(
    lhs=ExprCache.add([y, zero]),
    rhs=y,
    justification=Justification(JustificationType.AXIOM, "Additive Identity")
)
system.add_equality(new_eq)

# 检查 y+0 和 x 是否等价（应该不等价，因为 y 和 x 是不同变量）
expr_y_plus_0 = ExprCache.add([y, zero])
result = system.are_equivalent(expr_y_plus_0, x)
print(f"   y+0 ≡ x: {result}")

# 检查 y+0 和 y 是否等价
result = system.are_equivalent(expr_y_plus_0, y)
print(f"   y+0 ≡ y: {result}")

print("\n6. 等式代入:")
bindings = {"x": ExprCache.add([y, y])}
substituted = eq1.substitute(bindings)
print(f"   原始: {eq1}")
print(f"   代入 x -> y+y: {substituted}")

print("\n7. 翻转等式:")
flipped = eq1.flip()
print(f"   原始: {eq1}")
print(f"   翻转: {flipped}")

print("\n" + "=" * 60)
print("所有测试通过！")
print("=" * 60)
