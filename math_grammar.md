# Mathematical Grammar Specification

## Version: 1.0
## Date: 2026-05-17
## Status: Draft

---

## 1. Token Specification

### 1.1 Token Categories

| Category | Description | Examples |
|----------|-------------|----------|
| **IDENTIFIER** | 标识符（变量名、函数名） | `x`, `y`, `sin`, `cos`, `f` |
| **NUMBER** | 数字（整数、小数） | `2`, `3.14`, `-5`, `1/2` |
| **COMMAND** | LaTeX 命令 | `\sin`, `\cos`, `\sqrt`, `\frac` |
| **OPERATOR** | 运算符 | `+`, `-`, `*`, `/`, `^`, `=`, `<`, `>` |
| **PAREN** | 括号 | `(`, `)`, `[`, `]`, `{`, `}` |
| **PUNCTUATION** | 标点 | `,`, `;`, `:` |
| **WHITESPACE** | 空白（忽略） | 空格、换行、制表符 |

### 1.2 EBNF Definitions

```ebnf
IDENTIFIER := [a-zA-Z_][a-zA-Z0-9_]*
NUMBER := INTEGER | DECIMAL | FRACTION
INTEGER := ["-"] [0-9]+
DECIMAL := ["-"] [0-9]+ "." [0-9]+
FRACTION := INTEGER "/" INTEGER
COMMAND := "\" IDENTIFIER
OPERATOR := "+" | "-" | "*" | "/" | "^" | "=" | "<" | ">" | "<=" | ">=" | "!="
PAREN_OPEN := "(" | "[" | "{"
PAREN_CLOSE := ")" | "]" | "}"
```

### 1.3 Reserved Identifiers

| Identifier | Type | Description |
|------------|------|-------------|
| `pi` | CONSTANT | 圆周率 |
| `e` | CONSTANT | 自然对数底数 |
| `i` | CONSTANT | 虚数单位 |
| `sin` | FUNCTION | 正弦函数 |
| `cos` | FUNCTION | 余弦函数 |
| `tan` | FUNCTION | 正切函数 |
| `sinh` | FUNCTION | 双曲正弦 |
| `cosh` | FUNCTION | 双曲余弦 |
| `exp` | FUNCTION | 指数函数 |
| `log` | FUNCTION | 对数函数 |
| `ln` | FUNCTION | 自然对数 |
| `sqrt` | FUNCTION | 平方根 |
| `abs` | FUNCTION | 绝对值 |
| `lim` | FUNCTION | 极限 |
| `sum` | FUNCTION | 求和 |
| `prod` | FUNCTION | 求积 |
| `int` | FUNCTION | 积分 |
| `det` | FUNCTION | 行列式 |
| `trace` | FUNCTION | 迹 |
| `rank` | FUNCTION | 秩 |

---

## 2. Expression Grammar

### 2.1 Grammar Hierarchy (by precedence)

```
Level 1: Equality (lowest precedence)
Level 2: Comparison
Level 3: Additive
Level 4: Multiplicative
Level 5: Power
Level 6: Unary
Level 7: Primary (highest precedence)
```

### 2.2 EBNF Definition

```ebnf
expression         ::= equality

equality           ::= comparison (("=" | "!=") comparison)*

comparison         ::= additive (("<" | ">" | "<=" | ">=") additive)*

additive           ::= multiplicative (("+" | "-") multiplicative)*

multiplicative     ::= power (("*" | "/" | "\cdot") power)*

power              ::= unary ("^" unary)*

unary              ::= ("-" | "+") unary
                     | primary

primary            ::= NUMBER
                     | IDENTIFIER
                     | function_call
                     | group
                     | set
                     | matrix
                     | fraction
                     | sqrt
                     | subscript
                     | superscript
```

---

## 3. Function Call Grammar

### 3.1 EBNF Definition

```ebnf
function_call      ::= IDENTIFIER "(" expr_list? ")"
                     | COMMAND "(" expr_list? ")"

expr_list          ::= expression ("," expression)*
```

### 3.2 Function Call vs Implicit Multiplication

| Pattern | Interpretation | Example |
|---------|----------------|---------|
| `IDENTIFIER "("` | Function Call | `sin(x)`, `f(x)` |
| `NUMBER IDENTIFIER` | Implicit Multiplication | `2x`, `3y` |
| `IDENTIFIER IDENTIFIER` | Implicit Multiplication | `xy`, `ab` |
| `IDENTIFIER "(" expr ` | Function Call | `sin(x+y)` |
| `IDENTIFIER "(" IDENTIFIER` | Function Call | `f(x)` |
| `IDENTIFIER "(" NUMBER` | Function Call | `round(3.14)` |

### 3.3 Special Functions

```ebnf
sqrt               ::= "sqrt" "(" expression ")"
                     | "\sqrt" ["[" expression "]"] "{" expression "}"

fraction           ::= "\frac" "{" expression "}" "{" expression "}"
                     | expression "/" expression
```

---

## 4. Grouping and Scope

```ebnf
group              ::= "(" expression ")"
                     | "[" expression "]"
                     | "{" expression "}"
```

### 4.1 Group Types

| Delimiter | Semantic Meaning | Example |
|-----------|------------------|---------|
| `()` | Parentheses - grouping | `(x+y)` |
| `[]` | Square brackets - vector/index | `x[i]`, `[1,2,3]` |
| `{}` | Curly braces - set/sequence | `{1,2,3}`, `{x | x>0}` |

---

## 5. Implicit Multiplication Rules

### 5.1 Rules

1. **NUMBER followed by IDENTIFIER**: `2x` → `Multiply(2, x)`
2. **IDENTIFIER followed by IDENTIFIER**: `xy` → `Multiply(x, y)`
3. **IDENTIFIER followed by "("**: `x(y+1)` → `Multiply(x, (y+1))`
4. **")" followed by IDENTIFIER**: `(x+1)y` → `Multiply((x+1), y)`
5. **")" followed by "("**: `(x+1)(y+1)` → `Multiply((x+1), (y+1))`
6. **NUMBER followed by "("**: `2(x+1)` → `Multiply(2, (x+1))`

### 5.2 Exceptions

| Pattern | Exception Rule |
|---------|----------------|
| `sin(x)` | Function call (reserved identifiers) |
| `log(x)` | Function call (reserved identifiers) |
| `sqrt(x)` | Function call (reserved identifiers) |

---

## 6. Subscript and Superscript

```ebnf
subscript          ::= IDENTIFIER "_" ("{" expression "}" | [a-zA-Z0-9])

superscript        ::= expression "^" ("{" expression "}" | [a-zA-Z0-9])
```

---

## 7. Set Notation

```ebnf
set                ::= "{" expr_list "}"
                     | "{" expression "|" expression "}"
```

---

## 8. Matrix Notation

```ebnf
matrix             ::= "\begin{matrix}" row_list "\end{matrix}"

row_list           ::= row ("\\") row*

row                ::= expression ("&" expression)*
```

---

## 9. AST Node Types

### 9.1 Expression Nodes

| Node Type | Description | Children |
|-----------|-------------|----------|
| `NumberNode` | 数字 | value |
| `SymbolNode` | 符号 | name |
| `AddNode` | 加法 | left, right |
| `SubtractNode` | 减法 | left, right |
| `MultiplyNode` | 乘法 | left, right |
| `DivideNode` | 除法 | numerator, denominator |
| `PowerNode` | 幂运算 | base, exponent |
| `NegateNode` | 取反 | operand |
| `FunctionNode` | 函数调用 | name, arguments |

### 9.2 Structural Nodes

| Node Type | Description | Children |
|-----------|-------------|----------|
| `GroupNode` | 分组 | content |
| `SetNode` | 集合 | elements |
| `MatrixNode` | 矩阵 | rows |
| `FractionNode` | 分数 | numerator, denominator |
| `SqrtNode` | 根号 | radicand, degree |
| `SubscriptNode` | 下标 | base, subscript |
| `SuperscriptNode` | 上标 | base, superscript |

### 9.3 Logical Nodes

| Node Type | Description | Children |
|-----------|-------------|----------|
| `EquationNode` | 等式 | left, right |
| `ComparisonNode` | 比较 | left, right, operator |

---

## 10. Type System Integration

### 10.1 Type Inference Rules

| Operation | Left Type | Right Type | Result Type |
|-----------|-----------|------------|-------------|
| `+` | REAL | REAL | REAL |
| `+` | INTEGER | INTEGER | INTEGER |
| `+` | MATRIX | MATRIX | MATRIX |
| `*` | REAL | REAL | REAL |
| `*` | MATRIX | MATRIX | MATRIX |
| `*` | MATRIX | VECTOR | VECTOR |
| `/` | REAL | REAL | REAL |
| `/` | INTEGER | INTEGER | RATIONAL |
| `^` | REAL | INTEGER | REAL |

---

## 11. Precedence Table

| Precedence | Operators | Associativity |
|------------|-----------|---------------|
| 1 | `=`, `!=`, `<`, `>`, `<=`, `>=` | Left |
| 2 | `+`, `-` (binary) | Left |
| 3 | `*`, `/`, `\cdot` | Left |
| 4 | `^` | Right |
| 5 | `-`, `+` (unary) | Right |

---

## 12. Error Handling

### 12.1 Syntax Errors

| Error Type | Description | Example |
|------------|-------------|---------|
| `UnexpectedToken` | 遇到意外 token | `x++y` |
| `MismatchedParentheses` | 括号不匹配 | `(x+y` |
| `EmptyExpression` | 空表达式 | `()` |
| `UndefinedFunction` | 未定义函数 | `unknown(x)` |

### 12.2 Semantic Errors

| Error Type | Description | Example |
|------------|-------------|---------|
| `TypeError` | 类型不兼容 | `A + x` (A:MATRIX, x:REAL) |
| `UndefinedVariable` | 未定义变量 | `unknown_var` |
| `DivisionByZero` | 除零错误 | `x / 0` |

---

## Appendix A: Grammar Summary

```ebnf
expression         ::= equality
equality           ::= comparison (("=" | "!=") comparison)*
comparison         ::= additive (("<" | ">" | "<=" | ">=") additive)*
additive           ::= multiplicative (("+" | "-") multiplicative)*
multiplicative     ::= power (("*" | "/" | "\cdot") power)*
power              ::= unary ("^" unary)*
unary              ::= ("-" | "+") unary | primary
primary            ::= NUMBER | IDENTIFIER | function_call | group | set
function_call      ::= IDENTIFIER "(" expr_list? ")"
group              ::= "(" expression ")"
expr_list          ::= expression ("," expression)*
```

---

## Appendix B: Lexer State Machine

### B.1 State Transitions

```
Start -> [a-zA-Z_] -> IdentifierState -> [a-zA-Z0-9_]* -> IDENTIFIER
      -> [0-9] -> NumberState -> [0-9]* ( "." [0-9]+ )? -> NUMBER
      -> "\\" -> CommandState -> [a-zA-Z_][a-zA-Z0-9_]* -> COMMAND
      -> "+" | "-" | "*" | "/" | "^" -> OPERATOR
      -> "(" | "[" | "{" -> PAREN_OPEN
      -> ")" | "]" | "}" -> PAREN_CLOSE
      -> "," | ";" | ":" -> PUNCTUATION
      -> [ \t\n\r] -> Skip -> Start
```