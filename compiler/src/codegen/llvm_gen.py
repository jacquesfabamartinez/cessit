from llvmlite import ir, binding
from typing import Dict, Optional
from ..ast_nodes import (
    Program,
    BindingStmt,
    AssignmentStmt,
    ExpressionStmt,
    ReturnStmt,
    Block,
    IfStmt,
    FunctionDecl,
    Identifier,
    Literal,
    BinaryExpr,
    CallExpr,
    PrimitiveType,
    ASTNode,
)

class LLVMCodeGenerator:
    def __init__(self, module_name: str = "cessit_module"):
        # Initialize LLVM binding
        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()

        self.module = ir.Module(name=module_name)
        self.builder: Optional[ir.IRBuilder] = None
        self.named_values: Dict[str, ir.AllocaInstr] = {}
        self.current_function: Optional[ir.Function] = None

        self._setup_types()

    def _setup_types(self):
        # Map Cessit primitive types to LLVM types
        self.llvm_types = {
            "i32": ir.IntType(32),
            "bool": ir.IntType(1),
            "unit": ir.VoidType(),
        }

    def _get_llvm_type(self, type_node: Optional[ASTNode]) -> ir.Type:
        if isinstance(type_node, PrimitiveType):
            return self.llvm_types.get(type_node.name, ir.IntType(32))
        return ir.IntType(32) # Default fallback for stage 0

    def generate(self, node: Program) -> str:
        self._visit(node)
        return str(self.module)

    def _visit(self, node: ASTNode):
        method_name = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self._generic_visit)
        return visitor(node)

    def _generic_visit(self, node: ASTNode):
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

    def _visit_FunctionDecl(self, node: FunctionDecl):
        # Map parameter types
        param_types = [self._get_llvm_type(p.param_type) for p in node.parameters]
        return_type = self._get_llvm_type(node.return_type)
        
        fn_type = ir.FunctionType(return_type, param_types)
        fn = ir.Function(self.module, fn_type, name=node.name)
        self.current_function = fn

        # Create entry block
        block = fn.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        # Clear scope values for new function
        self.named_values.clear()

        # Allocate and store parameters
        for i, p in enumerate(node.parameters):
            arg = fn.args[i]
            arg.name = p.name
            alloca = self._create_entry_block_alloca(fn, p.name, arg.type)
            self.builder.store(arg, alloca)
            self.named_values[p.name] = alloca

        # Visit function body statements
        for stmt in node.body.statements:
            self._visit(stmt)

        # Ensure terminal instruction if missing
        if not self.builder.block.is_terminated:
            if isinstance(return_type, ir.VoidType):
                self.builder.ret_void()
            else:
                self.builder.ret(ir.Constant(return_type, 0))

        self.current_function = None

    def _visit_BindingStmt(self, node: BindingStmt):
        val = self._visit(node.value)
        llvm_type = self._get_llvm_type(node.var_type)
        
        # Allocate stack slot for local variable binding
        alloca = self._create_entry_block_alloca(self.current_function, node.name, llvm_type)
        self.builder.store(val, alloca)
        self.named_values[node.name] = alloca

    def _visit_AssignmentStmt(self, node: AssignmentStmt):
        val = self._visit(node.value)
        ptr = self.named_values.get(node.name)
        if not ptr:
            raise NameError(f"Codegen Error: Undefined variable '{node.name}'")
        self.builder.store(val, ptr)

    def _visit_ExpressionStmt(self, node: ExpressionStmt):
        return self._visit(node.expr)

    def _visit_ReturnStmt(self, node: ReturnStmt):
        if node.value:
            val = self._visit(node.value)
            self.builder.ret(val)
        else:
            self.builder.ret_void()

    def _visit_Identifier(self, node: Identifier) -> ir.Value:
        ptr = self.named_values.get(node.name)
        if not ptr:
            raise NameError(f"Codegen Error: Undefined variable '{node.name}'")
        return self.builder.load(ptr, name=node.name)

    def _visit_Literal(self, node: Literal) -> ir.Constant:
        if isinstance(node.value, int):
            return ir.Constant(ir.IntType(32), node.value)
        elif isinstance(node.value, str):
            # String constants handled as global strings or pointers
            return ir.Constant(ir.IntType(8), 0)
        return ir.Constant(ir.IntType(32), 0)

    def _visit_BinaryExpr(self, node: BinaryExpr) -> ir.Value:
        lhs = self._visit(node.left)
        rhs = self._visit(node.right)

        if node.op == "+":
            return self.builder.add(lhs, rhs, name="addtmp")
        elif node.op == "-":
            return self.builder.sub(lhs, rhs, name="subtmp")
        elif node.op == "*":
            return self.builder.mul(lhs, rhs, name="multmp")
        elif node.op == "<":
            return self.builder.icmp_signed("<", lhs, rhs, name="lttmp")
        elif node.op == "==":
            return self.builder.icmp_signed("==", lhs, rhs, name="eqtmp")
        
        raise NotImplementedError(f"Binary operator '{node.op}' not implemented in codegen.")

    def _create_entry_block_alloca(self, fn: ir.Function, var_name: str, ty: ir.Type) -> ir.AllocaInstr:
        """Helper to create an alloca instruction in the entry block of a function."""
        with self.builder.goto_entry_block():
            builder = ir.IRBuilder(self.builder.block)
            # Position builder right before the first instruction or at the end of entry
            if self.builder.block.instructions:
                builder.position_before(self.builder.block.instructions[0])
            return builder.alloca(ty, size=None, name=var_name)
