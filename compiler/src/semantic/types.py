from typing import Optional, Dict, List
from ..ast_nodes import (
    Program,
    BindingStmt,
    AssignmentStmt,
    ExpressionStmt,
    ReturnStmt,
    Block,
    IfStmt,
    MatchStmt,
    FunctionDecl,
    Identifier,
    Literal,
    BinaryExpr,
    CallExpr,
    TypeNode,
    PrimitiveType,
    ReferenceType,
    GenericType,
    ASTNode,
)
from ..symbol import SymbolTable, SymbolKind


class TypeChecker:
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table

    def check(self, node: ASTNode):
        """Entry point to run type checking over the AST."""
        return self._visit(node)

    def _visit(self, node: ASTNode) -> Optional[TypeNode]:
        method_name = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self._generic_visit)
        return visitor(node)

    def _generic_visit(self, node: ASTNode) -> Optional[TypeNode]:
        for _, value in vars(node).items():
            if isinstance(value, ASTNode):
                self._visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ASTNode):
                        self._visit(item)
        return None

    def _visit_Program(self, node: Program):
        for stmt in node.statements:
            self._visit(stmt)

    def _visit_Block(self, node: Block) -> Optional[TypeNode]:
        self.symbol_table.enter_scope("block")
        last_type = None
        for stmt in node.statements:
            last_type = self._visit(stmt)
        self.symbol_table.exit_scope()
        return last_type

    def _visit_FunctionDecl(self, node: FunctionDecl):
        # Register function symbol globally first if not already done
        fn_symbol_type = FunctionTypeNode_placeholder = node.return_type
        self.symbol_table.define_function(node.name, fn_symbol_type, node)

        scope = self.symbol_table.enter_scope(f"fn_{node.name}")
        for param in node.parameters:
            self.symbol_table.define_variable(
                name=param.name,
                var_type=param.param_type,
                verb=param.verb,
                node=param
            )

        body_type = self._visit(node.body)
        
        # Verify return type if specified
        if node.return_type and body_type:
            if not self._types_match(node.return_type, body_type):
                raise TypeError(
                    f"Type Error in function '{node.name}': Expected return type "
                    f"'{node.return_type}', but body evaluated to '{body_type}'."
                )

        self.symbol_table.exit_scope()

    def _visit_BindingStmt(self, node: BindingStmt):
        val_type = self._visit(node.value)
        
        # If expression type is resolved, verify it matches the explicit type annotation
        if val_type and not self._types_match(node.var_type, val_type):
            raise TypeError(
                f"Type Error for binding '{node.name}': Explicit type annotation "
                f"'{node.var_type}' does not match expression type '{val_type}'."
            )

        self.symbol_table.define_variable(
            name=node.name,
            var_type=node.var_type,
            verb=node.verb,
            node=node
        )

    def _visit_AssignmentStmt(self, node: AssignmentStmt) -> Optional[TypeNode]:
        sym = self.symbol_table.resolve(node.name)
        val_type = self._visit(node.value)
        
        if val_type and sym.type_annotation and not self._types_match(sym.type_annotation, val_type):
            raise TypeError(
                f"Type Error: Cannot assign value of type '{val_type}' to variable "
                f"'{node.name}' of type '{sym.type_annotation}'."
            )
        return val_type

    def _visit_ExpressionStmt(self, node: ExpressionStmt) -> Optional[TypeNode]:
        return self._visit(node.expr)

    def _visit_ReturnStmt(self, node: ReturnStmt) -> Optional[TypeNode]:
        if node.value:
            return self._visit(node.value)
        return PrimitiveType(name="unit")

    def _visit_IfStmt(self, node: IfStmt):
        cond_type = self._visit(node.condition)
        if cond_type and not self._types_match(PrimitiveType(name="bool"), cond_type):
            raise TypeError(f"Type Error: 'if' condition must evaluate to 'bool', found '{cond_type}'.")
        
        self._visit(node.then_block)
        if node.else_block:
            self._visit(node.else_block)

    def _visit_MatchStmt(self, node: MatchStmt):
        expr_type = self._visit(node.expr)
        for arm in node.arms:
            self.symbol_table.enter_scope("match_arm")
            pattern = arm.pattern
            if hasattr(pattern, "name") and pattern.name:
                self.symbol_table.define_variable(
                    name=pattern.name,
                    var_type=pattern.pattern_type,
                    verb=pattern.verb,
                    node=pattern
                )
            self._visit(arm.body)
            self.symbol_table.exit_scope()

    def _visit_Identifier(self, node: Identifier) -> Optional[TypeNode]:
        sym = self.symbol_table.resolve(node.name)
        return sym.type_annotation

    def _visit_Literal(self, node: Literal) -> TypeNode:
        if isinstance(node.value, int):
            return PrimitiveType(name="i32")
        elif isinstance(node.value, str):
            return PrimitiveType(name="String")
        return PrimitiveType(name="unknown")

    def _visit_BinaryExpr(self, node: BinaryExpr) -> TypeNode:
        left_type = self._visit(node.left)
        right_type = self._visit(node.right)

        if left_type and right_type and not self._types_match(left_type, right_type):
            raise TypeError(
                f"Type Error: Binary operator '{node.op}' operands have mismatched types: "
                f"'{left_type}' and '{right_type}'."
            )
        return left_type

    def _visit_CallExpr(self, node: CallExpr) -> Optional[TypeNode]:
        for arg in node.arguments:
            self._visit(arg)
        
        sym = self.symbol_table.resolve(node.callee)
        if sym.kind != SymbolKind.FUNCTION:
            raise TypeError(f"Type Error: Identifier '{node.callee}' is not a callable function.")
        return sym.type_annotation

    def _types_match(self, t1: TypeNode, t2: TypeNode) -> bool:
        """Helper to check structural equality of two types."""
        if type(t1) is not type(t2):
            return False
        if isinstance(t1, PrimitiveType) and isinstance(t2, PrimitiveType):
            return t1.name == t2.name
        if isinstance(t1, ReferenceType) and isinstance(t2, ReferenceType):
            return self._types_match(t1.inner, t2.inner)
        if isinstance(t1, GenericType) and isinstance(t2, GenericType):
            if t1.base != t2.base or len(t1.type_args) != len(t2.type_args):
                return False
            return all(self._types_match(a, b) for a, b in zip(t1.type_args, t2.type_args))
        return True
