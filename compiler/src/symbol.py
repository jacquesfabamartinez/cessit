from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from enum import Enum, auto

from .ast_nodes import TypeNode, ASTNode


class SymbolKind(Enum):
    VARIABLE = auto()
    FUNCTION = auto()
    GENERIC_PARAM = auto()


class BindingState(Enum):
    LIVE = auto()
    MOVED = auto()
    BORROWED_READ = auto()
    BORROWED_MUT = auto()


@dataclass
class Symbol:
    name: str
    kind: SymbolKind
    type_annotation: Optional[TypeNode]
    verb: Optional[str] = None  # "take", "read", or "mut"
    state: BindingState = BindingState.LIVE
    node_decl: Optional[ASTNode] = None


class Scope:
    def __init__(self, parent: Optional["Scope"] = None, scope_name: str = "block"):
        self.parent: Optional[Scope] = parent
        self.scope_name: str = scope_name
        self.symbols: Dict[str, Symbol] = {}

    def define(self, symbol: Symbol) -> bool:
        """Defines a symbol in the current scope. Returns False if already defined in local scope."""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol lexically up the scope chain."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up a symbol strictly in the current local scope."""
        return self.symbols.get(name)


class SymbolTable:
    def __init__(self):
        self.global_scope = Scope(scope_name="global")
        self.current_scope = self.global_scope

    def enter_scope(self, name: str = "block") -> Scope:
        """Pushes a new child scope onto the scope stack."""
        new_scope = Scope(parent=self.current_scope, scope_name=name)
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self) -> Scope:
        """Pops the current scope, returning to parent."""
        if self.current_scope.parent is None:
            raise RuntimeError("Cannot exit root global scope.")
        popped = self.current_scope
        self.current_scope = self.current_scope.parent
        return popped

    def define_variable(
        self,
        name: str,
        var_type: TypeNode,
        verb: str,
        node: Optional[ASTNode] = None
    ) -> Symbol:
        sym = Symbol(
            name=name,
            kind=SymbolKind.VARIABLE,
            type_annotation=var_type,
            verb=verb,
            state=BindingState.LIVE,
            node_decl=node
        )
        if not self.current_scope.define(sym):
            raise NameError(f"Redeclaration of symbol '{name}' in scope '{self.current_scope.scope_name}'")
        return sym

    def define_function(self, name: str, fn_type: TypeNode, node: Optional[ASTNode] = None) -> Symbol:
        sym = Symbol(
            name=name,
            kind=SymbolKind.FUNCTION,
            type_annotation=fn_type,
            node_decl=node
        )
        # Functions are always registered in the global or outer scope
        if not self.global_scope.define(sym):
            raise NameError(f"Redeclaration of function '{name}' in global scope")
        return sym

    def resolve(self, name: str) -> Symbol:
        sym = self.current_scope.lookup(name)
        if sym is None:
            raise NameError(f"Undeclared identifier '{name}' referenced")
        return sym
