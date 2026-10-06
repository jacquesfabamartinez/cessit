from dataclasses import dataclass, field
from typing import List, Optional, Union, Any

# ==============================================================================
# Base Node Marker
# ==============================================================================
class ASTNode:
    """Base class for all Cessit AST nodes."""
    pass

@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)

# ==============================================================================
# Types
# ==============================================================================
class TypeNode(ASTNode):
    """Base class for Cessit type annotations."""
    pass

@dataclass
class PrimitiveType(TypeNode):
    name: str  # e.g., "i32", "bool"

@dataclass
class ReferenceType(TypeNode):
    inner: TypeNode  # e.g., &T

@dataclass
class GenericType(TypeNode):
    base: str  # e.g., "Option"
    type_args: List[TypeNode]  # e.g., [T]

@dataclass
class FunctionType(TypeNode):
    param_types: List[TypeNode]
    return_type: Optional[TypeNode] = None
    capabilities: List[str] = field(default_factory=list)

# ==============================================================================
# Statements & Bindings
# ==============================================================================
class StatementNode(ASTNode):
    """Base class for statements."""
    pass

@dataclass
class BindingStmt(StatementNode):
    verb: str          # "take" | "read" | "mut"
    name: str          # Identifier
    var_type: TypeNode
    value: ASTNode     # Expression

@dataclass
class AssignmentStmt(StatementNode):
    name: str
    value: ASTNode

@dataclass
class ExpressionStmt(StatementNode):
    expr: ASTNode

@dataclass
class ReturnStmt(StatementNode):
    value: Optional[ASTNode] = None

@dataclass
class Block(StatementNode):
    statements: List[StatementNode] = field(default_factory=list)

@dataclass
class IfStmt(StatementNode):
    condition: ASTNode
    then_block: Block
    else_block: Optional[Block] = None

# ==============================================================================
# Match Expressions & Patterns
# ==============================================================================
class PatternNode(ASTNode):
    """Base class for pattern matching."""
    pass

@dataclass
class VariantPattern(PatternNode):
    variant: str       # e.g., "Some"
    verb: str          # "take" | "read" | "mut"
    name: str          # Captured variable name
    pattern_type: TypeNode  # Explicit type requirement

@dataclass
class WildcardPattern(PatternNode):
    pass

@dataclass
class MatchArm(ASTNode):
    pattern: PatternNode
    body: Union[ASTNode, Block]

@dataclass
class MatchStmt(StatementNode):
    expr: ASTNode
    arms: List[MatchArm] = field(default_factory=list)

# ==============================================================================
# Functions & Closures
# ==============================================================================
@dataclass
class Parameter(ASTNode):
    verb: str
    name: str
    param_type: TypeNode

@dataclass
class FunctionDecl(StatementNode):
    name: str
    generics: List[str] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[TypeNode] = None
    capabilities: List[str] = field(default_factory=list)
    body: Block = field(default_factory=Block)

# ==============================================================================
# Expressions & Terms
# ==============================================================================
class ExpressionNode(ASTNode):
    """Base class for expressions."""
    pass

@dataclass
class Identifier(ExpressionNode):
    name: str

@dataclass
class Literal(ExpressionNode):
    value: Union[int, str]

@dataclass
class BinaryExpr(ExpressionNode):
    left: ASTNode
    op: str
    right: ASTNode

@dataclass
class CallExpr(ExpressionNode):
    callee: str
    type_args: List[TypeNode] = field(default_factory=list)
    arguments: List[ASTNode] = field(default_factory=list)
