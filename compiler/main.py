import sys
from pathlib import Path

from src.parser import parse_code
from src.symbol import SymbolTable
from src.semantic.ownership import OwnershipVerifier
from src.semantic.types import TypeChecker
from src.codegen.llvm_gen import LLVMCodeGenerator


def compile_file(file_path: Path):
    if not file_path.exists():
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    source_code = file_path.read_text(encoding="utf-8")
    print(f"[*] Compiling '{file_path}'...")

    try:
        # 1. Parse AST
        ast = parse_code(source_code)
        print("  ✓ Parse successful (AST generated)")

        # 2. Ownership & Borrow Verification
        ownership_verifier = OwnershipVerifier(SymbolTable())
        ownership_verifier.verify(ast)
        print("  ✓ Ownership verification passed")

        # 3. Type Checking
        type_checker = TypeChecker(SymbolTable())
        type_checker.check(ast)
        print("  ✓ Type checking passed")

        # 4. LLVM Code Generation
        codegen = LLVMCodeGenerator(module_name=file_path.stem)
        llvm_ir = codegen.generate(ast)
        print("  ✓ LLVM IR generated successfully")

        # 5. Output .ll file
        output_path = file_path.with_suffix(".ll")
        output_path.write_text(llvm_ir, encoding="utf-8")
        print(f"[*] LLVM IR dumped to: {output_path.resolve()}")

    except Exception as e:
        print(f"\n[!] Compilation Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path-to-cessit-file>")
        sys.exit(1)

    target_file = Path(sys.argv[1])
    compile_file(target_file)


if __name__ == "__main__":
    main()
