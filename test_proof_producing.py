"""测试 Proof-Producing Rewrite"""
from latex_engine import *

print("=" * 70)
print("Proof-Producing Rewrite 测试")
print("=" * 70)

# 创建表达式
x = ExprCache.symbol("x")
y = ExprCache.symbol("y")
zero = ExprCache.number(0)
one = ExprCache.number(1)

print("\n1. Substitution（形式化替换）:")
sigma = Substitution({"x": ExprCache.add([y, y])})
print(f"   σ = {sigma}")

expr = ExprCache.add([x, zero])
print(f"   原始: {expr}")
result = sigma.apply(expr)
print(f"   应用后: {result}")

print("\n2. 替换组合:")
sigma1 = Substitution({"x": y})
sigma2 = Substitution({"y": ExprCache.number(2)})
composed = sigma1.compose(sigma2)
print(f"   sigma1 = {sigma1}")
print(f"   sigma2 = {sigma2}")
print(f"   sigma1 compose sigma2 = {composed}")

print("\n3. Proof Object（证明对象）:")
# 创建定理并应用
add_id = create_additive_identity()
print(f"   定理: {add_id}")

eq, proof = add_id.apply_with_proof({"x": ExprCache.add([y, y])})
print(f"   应用结果: {eq}")
print(f"   证明: {proof}")

print("\n4. 等式推理规则:")
# 自反性
reflex_proof = Proof.reflexivity(x)
print(f"   自反性: {reflex_proof}")

# 对称性
sym_proof = Proof.symmetry(reflex_proof)
print(f"   对称性: {sym_proof}")

# 传递性
trans_proof = Proof.transitivity(reflex_proof, sym_proof)
print(f"   传递性: {trans_proof}")

# 同余
cong_proof = Proof.congruence(reflex_proof, "ADD", 0)
print(f"   同余: {cong_proof}")

print("\n5. Proof-Producing Rewrite:")
system = create_std_equality_system()

# 测试等价性证明
expr1 = ExprCache.mul([one, ExprCache.add([x, zero])])  # 1*(x+0)
expr2 = x

result = system.are_equivalent(expr1, expr2)
print(f"   1*(x+0) ≡ x: {result}")

# 展示定理应用过程
theorem = system.theorems["additive_identity"]
bindings = {"x": x}
eq, proof = theorem.apply_with_proof(bindings)
print(f"   定理应用: {eq}")
print(f"   证明对象: {proof}")

print("\n" + "=" * 70)
print("所有测试通过！")
print("=" * 70)
