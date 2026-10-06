from typing import Dict, Set
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
    BinaryExpr,
    CallExpr,
    ASTNode,
)
from ..symbol import SymbolTable, BindingState


class OwnershipVerifier:
    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table

    def verify(self, node: ASTNode):
        """Entry point to run the ownership verification pass over the AST."""
        self._visit(node)

    def _visit(self, node: ASTNode):
        method_name = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self._generic_visit)
        return visitor(node)

    def _generic_visit(self, node: ASTNode):
        # Fallback for nodes that don't require specialized ownership tracking yet
        for _, value in vars(node).items():
            if isinstance(value, ASTNode):
                self._visit(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ASTNode):
                        self._visit(item)

    def _visit_Program(self, node: Program):
        for stmt in node.statements:
            self._visit(stmt)

    def _visit_Block(self, node: Block):
        self.symbol_table.enter_scope("block")
        for stmt in node.statements:
            self._visit(stmt)
        self.symbol_table.exit_scope()

    def _visit_FunctionDecl(self, node: FunctionDecl):
        # Define function parameters in the new function scope
        scope = self.symbol_table.enter_scope(f"fn_{node.name}")
        
        for param in node.parameters:
            # Parameters bring values into scope according to their explicit verb
            self.symbol_table.define_variable(
                name=param.name,
                var_type=param.param_type,
                verb=param.verb,
                node=param
            )

        self._visit(node.body)
        self.symbol_table.exit_scope()

    def _visit_BindingStmt(self, node: BindingStmt):
        # 1. Visit the expression being assigned to check for moved/invalid values
        self._visit(node.value)

        # 2. If the value is a direct identifier being 'taken', mark it as MOVED in the symbol table
        if node.verb == "take" and isinstance(node.value, Identifier):
            sym = self.symbol_table.resolve(node.value.name)
            if sym.state == BindingState.MOVED:
                raise RuntimeError(f"Ownership Error: Use of moved value '{node.value.name}'")
            sym.state = BindingState.MOVED

        # 3. Define the new variable in the current scope
        self.symbol_table.define_variable(
            name=node.name,
            var_type=node.var_type,
            verb=node.verb,
            node=node
        )

    def _visit_Identifier(self, node: Identifier):
        sym = self.symbol_table.resolve(node.name)
        if sym.state == BindingState.MOVED:
            raise RuntimeError(f"Ownership Error: Variable '{node.name}' has been moved and is no longer valid.")

    def _visit_AssignmentStmt(self, node: AssignmentStmt):
        self._visit(node.value)
        sym = self.symbol_table.resolve(node.name)
        if sym.verb == "read":
            raise RuntimeError(f"Ownership Error: Cannot assign to read-only binding '{node.name}' (bound with 'read').")

    def _visit_ExpressionStmt(self, node: ExpressionStmt):
        self._visit(node.expr)

    def _visit_ReturnStmt(self, node: ReturnStmt):
        if node.value:
            self._visit(node.value)

    def _visit_IfStmt(self, node: IfStmt):
        self._visit(node.condition)
        self._visit(node.then_block)
        if node.else_block:
            self._visit(node.else_block)

    def _visit_MatchStmt(self, node: MatchStmt):
        self._visit(node.expr)
        for arm in node.arms:
            # Each match arm gets its own scope for pattern bindings
            self.symbol_table.enter_scope("match_arm")
            
            # If it's a variant pattern binding (e.g., Some(read item: T))
            pattern = arm.pattern
            if hasattr(pattern, "name") and pattern.name:
                self.symbol_table.define_variable(
                    name=pattern.name,
                    var_type=pattern.pattern_type,
                    verb=pattern.verb,
                    node=pattern
                )
            
            if isinstance(arm.body, list):
                for stmt in arm.body:
                    self._visit(stmt)
            elif isinstance(arm.body, ASTNode):
                self._visit(arm.body)
                
            self.symbol_table.exit_scope()

    def _visit_BinaryExpr(self, node: BinaryExpr):
        self._visit(node.left)
        self._visit(node.right)

    def _visit_CallExpr(self, node: CallExpr):
        for arg in node.arguments:
            self._visit(arg)
