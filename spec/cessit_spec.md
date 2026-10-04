# Cessit Programming Language Specification

# 1. Language model

Cessit is a statically typed systems language with deliberately separate concepts:

1. **Binding mode** — how a binding obtains or accesses a value: ownership, shared access, or exclusive access.
2. **Type** — the structure of the value. Reference-ness is part of the type.
3. **Mutability** — whether a local owned binding may be reassigned or its value mutated.
4. **Lifetime** — how long a reference remains valid.
5. **Capability** — permission to perform a class of operations.
6. **Effect** — a named set of operations whose semantics are supplied by a handler.

The core rule is:

> A binding verb describes how a binding accesses a value. The type describes the value itself. Reference-ness is represented by `&T`; access mode is represented by `take`, `read`, or `mut`.

Examples:

```cessit
take value: Item = make_item();
read value_view: Item = value;
mut owned: Item = make_item();
take reference: &Item = make_item_reference();
```

`&Item` is a type. It does not mean that the referent is owned by the binding containing the reference.

---

# 2. Quick syntax overview

The most common Cessit declarations look like this:

```cessit
struct Point {
    x: Int;
    y: Int;
}

fn distance(take p: Point) -> Float {
    ...
}

fn load(take path: Path) -> String can IO {
    ...
}

effect IO {
    fn read_line() -> String;
}

trait Printable {
    fn print(read self: &This) -> ();
}
```

The visual distinctions are deliberate:

- `:` introduces a type annotation.
- `->` introduces a function's return type.
- `can` introduces the capabilities required when a function is called.
- `[]` supplies generic type or function arguments.
- `{}` delimit blocks and declaration bodies.
- `;` terminates statements and declaration members.

# 3. Core terminology

## 3.1 Binding

A binding associates a name with an owned value or with access to an existing value.

## 3.2 Owned value

An owned value has exactly one owning binding at a time. Ownership can be transferred explicitly.

## 3.3 Shared access

Shared access permits reading an existing value without transferring ownership. Multiple shared accesses may coexist.

## 3.4 Exclusive access

Exclusive ordinary access permits mutation of an existing value and excludes conflicting shared or exclusive ordinary accesses for its lifetime.

## 3.5 Reference

A reference is a non-owning value of type `&T` that designates a value of type `T`. References may be nested: `&T`, `&&T`, `&&&T`, and so on.

## 3.6 POD value

A POD value is a value whose complete representation can be duplicated without executing user-defined behavior, allocation, reference-count updates, or destructor logic. The compiler determines which types satisfy the `Copy` requirements.

## 3.7 Lifetime

A lifetime is a compile-time validity interval for a reference. It has no runtime representation.

## 3.8 Capability

A capability is a statically checked permission to perform a class of operations, such as I/O, task spawning, or acquiring storage for escaping continuations.

## 3.9 Effect

An effect is a named interface of operations. An effect operation suspends the current computation until a handler supplies its semantics.

## 3.10 Handler

A handler supplies implementations for effect operations and governs the computation in its lexical handling scope.

## 3.11 Continuation

A continuation is the suspended computation after an effect operation. Each continuation instance is **single-shot**: it may be resumed at most once.

A generator may suspend and resume repeatedly because every suspension creates a new continuation instance.

---
# 4. Lexical and layout rules

Cessit uses braces for blocks, struct bodies, enum bodies, trait bodies, effect declarations, handlers, and other multi-statement constructs. Statements are terminated with semicolons.

Whitespace is otherwise insignificant except where required to separate tokens.

## 4.1 Statements

A statement ends with `;`.

```cessit
take x: Int = 10;
take y: Int = 20;
take sum: Int = x + y;
println(sum);
```

A declaration whose body is a block does not require a second semicolon after the closing `}`.

## 4.2 Blocks

A block is delimited by `{` and `}`.

```cessit
if condition {
    println("true");
} else {
    println("false");
}
```

Braces are purely syntactic delimiters. They do not change ownership or lifetime semantics.

## 4.3 Comments

Single-line comments begin with `//`.

```cessit
take x: Int = 10; // comment
```

## 4.4 Delimiters

Parentheses group expressions and function signatures. Square brackets parameterize generic types and functions. Braces delimit blocks and declaration bodies. Semicolons delimit statements and declaration members.

---

# 5. Binding modes

Every ordinary binding has exactly one binding mode.

## 5.1 `take`

`take` creates an immutable owned binding.

```cessit
take x: Int = 5;
```

Properties:

- the binding owns its value;
- the binding cannot be reassigned;
- using the value in a `take` position transfers ownership;
- copying requires an explicit `copy()` operation;
- cloning requires an explicit `clone()` operation.

## 5.2 `read`

`read` creates shared access to an existing value.

```cessit
read item: Item = source;
```

Properties:

- ownership remains with the source;
- the binding provides shared ordinary access;
- ordinary mutation through this binding is forbidden;
- the binding cannot be reassigned;
- the binding's validity is limited by the borrowed value.

The declared type is the type being accessed, not a hidden reference type:

```cessit
read items: Vec[Int] = collection;
```

When the reference value itself must be represented as part of a type, `&T` is written explicitly:

```cessit
take item_ref: &Item = make_item_reference();
```

## 5.3 `mut`

`mut` creates a mutable owned local binding:

```cessit
mut total: Int = 0;
total = total + 1;
```

A mutable owned local may be reassigned and mutated.

For function parameters and method receivers, `mut` instead means exclusive ordinary access to an existing caller-owned value:

```cessit
fn edit(mut value: String) -> () {
    value.clear();
}
```

The parameter does not acquire ownership of the `String`; it acquires exclusive access to it.

## 5.4 Binding syntax

The canonical binding form is:

```text
verb name: Type = expression;
```

A type is mandatory. There is no implicit local declaration form.

## 5.5 Binding modes by context

| Context | `take` | `read` | `mut` |
| --- | --- | --- | --- |
| Local | owns immutable value | shared access | owns mutable value |
| Parameter | takes ownership | shared borrow | exclusive borrow |
| Receiver | takes ownership | shared borrow | exclusive borrow |
| Closure capture | owns capture | shared access to capture | exclusive access to capture |

The type does not change because of the binding mode.

---

# 6. Mutability and reassignment

Mutability is a property of a binding, not a property of the type itself.

## 6.1 Reassignment

Only `mut` local bindings may be reassigned.

```cessit
mut result: Int = 10;
result = 20;
result = result + 5;
```

These are invalid:

```cessit
take result: Int = 10;
result = 20;
```

```cessit
read result: Int = source;
result = 20;
```

`take` and `read` bindings are never reassigned.

## 6.2 Mutation

A mutable owned binding may mutate its contained value:

```cessit
mut items: Vec[Int] = Vec[Int].new();
items.push(1);
items.push(2);
```

Exclusive parameter access also permits mutation:

```cessit
fn push_one(mut items: Vec[Int]) -> () {
    items.push(1);
}
```

Interior mutability is separate: a type may expose operations that mutate internal state through shared access. See section 8.5.

## 6.3 No shadowing

A binding may not shadow another binding visible at its declaration site.

```cessit
take x: Int = 5;
if condition {
    take x: Int = 10; // ERROR
}
```

A different name must be used.

---

# 7. Ownership operations

Ownership transfer is explicit.

## 7.1 Moving

A value used in an owning position is moved.

```cessit
take source: String = "hello";
take destination: String = source;
```

After the move, `source` is no longer usable.

## 7.2 Borrowing

A value may be borrowed at a binding boundary:

```cessit
read view: String = source;
mut view: String = source;
```

The first creates shared ordinary access. The second creates exclusive ordinary access.

An explicit reference value uses `&T`:

```cessit
take reference: &String = make_reference(source);
```

A reference is non-owning even when the binding containing the reference is `take`.

## 7.3 Function argument passing

At a call site, the parameter binding mode determines what happens:

- `take` parameter: ownership is transferred;
- `read` parameter: shared access is created;
- `mut` parameter: exclusive access is created.

No implicit copy or clone is inserted.

```cessit
fn consume(take value: String) -> () {
    process(value);
}

fn inspect(read value: String) -> Int {
    return value.length();
}

fn edit(mut value: String) -> () {
    value.clear();
}
```

## 7.4 Copying

A copy is never inserted implicitly.

```cessit
take x: Int = 5;
take y: Int = x.copy();
```

See section 18.

## 7.5 Cloning

Non-POD duplication is never inserted implicitly.

```cessit
take x: String = "hello";
take y: String = x.clone();
```

See section 19.

---

# 8. Type system

Every expression has a statically known type.

The initial compiler performs **no type inference**.

Therefore:

- every binding has an explicit type;
- every function parameter has an explicit type;
- every function return type is explicit;
- generic type arguments at generic call sites are explicit;
- pattern-bound variables have explicit types where the grammar requires a binding declaration.

The compiler may perform type checking, normalization, overload resolution where explicitly specified, and lifetime inference, but it does not invent missing type annotations.

A future language revision may introduce carefully bounded type inference after the compiler architecture has matured.

---

# 9. Reference types

Reference-ness is part of the type. Access mode is a separate property of a binding.

## 9.1 Reference type

```text
&T
```

`&T` is a non-owning reference to a value of type `T`.

There is no separate mutable-reference type such as `$T`. Exclusive ordinary access is represented by `mut` at the binding or parameter boundary.

Example:

```cessit
take value: Item = make_item();
take reference: &Item = make_item_reference(value);
```

The `reference` binding owns the reference value as a value, but it does not own the `Item` referred to by it.

## 9.2 Nested references

Reference types compose normally:

```text
&T
&&T
&&&T
```

`&&T` is a reference to a value whose type is `&T`. It is not automatically collapsed to `&T`.

## 9.3 Binding mode versus reference type

These are independent:

```cessit
take x: T = make_value();
read y: T = x;
mut z: T = x;
take r: &T = make_reference(x);
```

`x` owns `T`; `y` has shared access to `T`; `z` has exclusive ordinary access to `T`; `r` owns a non-owning reference value.

## 9.4 Match ergonomics

Reference-ness remains visible in the type system so pattern matching does not need implicit mirroring or dereferencing transformations.

For example:

```text
Option[T]
Option[&T]
Option[&&T]
```

are distinct types.

A pattern therefore knows structurally whether it is handling a `T`, `&T`, or `&&T` without relying on hidden reference transformations.

## 9.5 Interior mutability

`read` prevents ordinary exclusive access through that binding. It does not prohibit a type from exposing operations that mutate internal state through shared access.

Interior mutability is a property of the type's API and invariants, not a special reference type.

Examples include runtime-checked cells, mutexes, atomics, and reference-counted types. Their operations may accept `read` access while internally providing dynamic exclusivity, synchronization, or atomicity.

The compiler does not inspect an abstract type's implementation to infer ordinary field mutation through its public API.

---

# 10. Function parameters and returns

Functions use the same declaration model as other named values.

## 10.1 Function declaration

```text
fn name[TypeParameters](parameters) -> ReturnType can Capability1, Capability2 {
    body
}
```

The `-> ReturnType` clause and `can CapabilityExpression` clause are optional when the function has no explicit return value or capabilities.

Example:

```cessit
fn add(take x: Int, take y: Int) -> Int {
    return x + y;
}
```

## 10.2 Parameter binding modes

For function parameters:

- `take parameter: T` moves ownership of `T` into the function;
- `read parameter: T` creates shared borrowed access to an existing `T`;
- `mut parameter: T` creates exclusive mutable borrowed access to an existing `T`.

The parameter's type may itself be a reference type.

```cessit
fn consume(take value: String) -> () {
    process(value);
}

fn length(read value: String) -> Int {
    return value.length();
}

fn clear(mut value: String) -> () {
    value.clear();
}
```

## 10.3 Return types

Return types are written directly after `->`. Return ownership is determined by the function's return type and the expression being returned; there is no separate return type syntax.

```cessit
fn make_value() -> Int {
    return 42;
}

fn first(read items: Vec[Int]) -> &Int {
    return items.at(0);
}

fn first_mut(mut items: Vec[Int]) -> &Int {
    return items.at_mut(0);
}

## 10.4 Method receivers

Methods are ordinary functions with a receiver parameter.

```cessit
fn length(read self: Vec[Int]) -> Int {
    ...
}

fn push(mut self: Vec[Int], take value: Int) -> () {
    ...
}

fn into_iter(take self: Vec[Int]) -> Iterator[Int, Vec[Int]] {
    ...
}
```

---

# 11. Function types

Function types use the same arrow syntax as function declarations.

```text
(take Int) -> Int
(take Int, take Int) -> Int
(read String) -> Int
(read Vec[Int], read (take Int) -> Int) -> Vec[Int]
```

Capabilities may be attached:

```text
(take String) -> String can IO
```

The capability expression is optional. Multiple capabilities are separated by commas:

```text
(take String) -> String can IO, Timer
```

---

# 12. Function values and calls

A named function is a value.

```cessit
fn double(take x: Int) -> Int {
    return x * 2;
}

take f: (take Int) -> Int = double;
```

Generic arguments are explicit:

```cessit
take x: Int = identity[Int](5);
```

No generic type argument is inferred from the arguments.

Method calls use `.`:

```cessit
take size: Int = items.length();
```

There is no Rust-style `::` syntax. Type-qualified operations use the same member notation:

```cessit
take values: Vec[Int] = Vec[Int].new();
```

---

# 13. Lifetimes and borrow provenance

Cessit uses compiler-managed lifetimes. A lifetime is not a runtime value and is not represented by a user-declared lifetime struct.

## 13.1 Lifetime annotations

A reference may specify its validity relation with:

```text
from name
```

Example:

```text
&T from outer
```

The name after `from` is a lifetime relationship label. `static` denotes a lifetime valid for the entire program.

```text
&T from static
```

## 13.2 Lifetime relationship placeholders

A lifetime label such as `r` is a compiler-level relationship variable, not a runtime parameter.

Example:

```cessit
fn pick[T](take condition: Bool, read a: &T from r, read b: &T from r) -> &T from r {
    if condition {
        return a;
    } else {
        return b;
    }
}
```

Repeated `r` means that the references participate in one lifetime relationship. At a call site the compiler computes the result lifetime as the meet of the participating source lifetimes.

```cessit
read chosen: &Item = pick[Item](true, foo from outer, bar from static);
```

The result is valid for the shorter common validity interval: `outer` in this example.

## 13.3 Lifetime inference and elision

Explicit lifetime annotations are required only when the compiler cannot uniquely determine the relationship.

The compiler may infer lifetimes from:

- a returned reference originating from one borrowed parameter;
- receiver provenance;
- nested reference structure;
- a single unambiguous source;
- lexical scope containment.

Iterators and other values that carry references use the same inference rules. A lifetime is written explicitly only when inference is ambiguous.

## 13.4 Lifetime safety

A reference may not outlive its referent. A borrowed result must therefore derive from storage whose lifetime dominates the result.

The compiler must reject:

- references to locals escaping their valid scope;
- borrowed fields whose target may expire first;
- generators, closures, or tasks that retain references beyond the referent's lifetime;
- conflicting accesses whose lifetimes overlap.

---

# 14. Closures

**Provisional:** The exact distinction between named functions and closure values is intentionally left open for a later language-design pass. The capture ownership and lifetime rules below are fixed.

Closures may explicitly declare captures.

## 14.1 Closure syntax

```text
fn(parameters) -> ReturnType can Capability1, Capability2 |capture list| {
    body
}
```

Example:

```cessit
take scale: Int = 2;

take scale_int: (take Int) -> Int =
    fn(take x: Int) -> Int |take scale: Int| {
        return x * scale;
    };
```

An empty capability set is omitted. An empty capture list may be written `||`:

```cessit
take double: (take Int) -> Int = fn(take x: Int) -> Int || {
    return x * 2;
};
```

## 14.2 Capture modes

A capture has the form `verb name: Type`:

- `take` — the closure owns the captured value;
- `read` — the closure holds shared access to the captured value;
- `mut` — the closure holds exclusive access to the captured value.

```cessit
read template: String = "Hello";
mut counter: Int = 0;

take greet: (take String) -> String =
    fn(take name: String) -> String
    |read template: String, mut counter: Int| {
        counter = counter + 1;
        return format(template, name);
    };
```

## 14.3 Hidden closure environments

A closure consists conceptually of:

1. callable code;
2. a hidden environment containing its captures.

The hidden environment has a concrete compiler-known type. Its ownership and lifetime rules are checked exactly like an ordinary struct.

## 14.4 Closure lifetimes

A closure containing `read` or `mut` captures may not outlive the borrowed values. A closure containing `take` captures owns those values.

## 14.5 Callable access modes

When a closure is received as a function parameter, the parameter binding mode determines whether the closure value is owned, shared, or exclusively accessed.

The concrete rules for coercing closure values to first-class function values remain **Provisional**.

---

# 15. Structs

Struct declarations contain fields without binding verbs.

```cessit
struct Node[T] {
    value: T;
    next: Box[Node[T]];
}

struct Pair[K, V] {
    key: &K;
    value: V;
}
```

Fields describe stored representation. A field may itself have a reference type.

## 15.1 Field mutation

Mutation is determined by the access mode through which the struct is used:

```cessit
mut node: Node[Int] = make_node();
node.value = 10;
```

A shared binding cannot mutate fields:

```cessit
read node: Node[Int] = source;
node.value = 10; // ERROR
```

## 15.2 Reference fields

A reference field stores a reference value, and the reference lifetime must be valid for the lifetime of the containing value.

```cessit
struct NameView {
    text: &String;
}
```

---

# 16. Enums and pattern matching

Enum variants contain fields without binding verbs.

```cessit
enum Result[T, E] {
    Ok(value: T);
    Err(error: E);
}

enum Option[T] {
    Some(value: T);
    None;
}
```

Pattern bindings use ordinary binding syntax:

```cessit
match divide[Int, String](10, 2 {
    Ok(take result: Int) => println(result);
    Err(take e: String) => println(e);
}
```

The exact match-arm separator is `=>`. The arm body may be an expression or a block.

Pattern matching does not implicitly add or remove reference layers.

---

# 17. Generics

Generic parameters use square brackets.

## 17.1 Generic types

```cessit
struct Vec[T] {
    ...
}
```

## 17.2 Generic functions

```cessit
fn process[T](take value: T) -> T {
    return value;
}

fn zip[A, B](take left: Vec[A], take right: Vec[B]) -> Vec[(A, B)] {
    ...
}
```

## 17.3 Generic calls

```cessit
take value: Int = process[Int](42);
```

No generic type argument is inferred.

---

# 18. Traits

Traits define named sets of operations.

```cessit
trait Indexable[T] {
    unsafe fn at(read self: &This, take index: usize) -> &T;
    fn get(read self: &This, take index: usize) -> Result[&T, IndexError];
}
```

Trait implementations use an explicit implementation declaration:

```cessit
implementation Indexable[Int] for Array[Int; 10] {
    ...
}
```

Traits may be used for method dispatch, generic constraints, compiler-recognized capabilities such as `Copy`, and ordinary library abstractions.

Static dispatch is the default.

---

# 19. Copy

`Copy` is a special compiler-recognized trait. User code may not implement, override, or provide an alternative implementation of `Copy`.

The compiler determines whether a type is `Copy` according to the language's structural rules.

A `Copy` operation duplicates the complete POD representation without user-defined behavior, allocation, reference-count updates, or destructor execution.

Example:

```cessit
take x: Int = 5;
take y: Int = x.copy();
```

Typical `Copy` types include primitive scalar types such as `Int`, `Float`, `Bool`, and `Byte`.

---

# 20. Clone

`Clone` is an ordinary trait for explicit duplication of a non-POD value.

```cessit
trait Clone {
    fn clone(read self: &This) -> This;
}
```

`Clone` means whatever operation is necessary to produce an independent logical value according to the type's semantics. It is not restricted to deep memory copying.

For example, an `Rc[T]`-like type may implement `clone()` by incrementing a reference count. Another type may allocate and recursively duplicate its contents.

A cloning implementation that allocates requires the relevant allocation capability.

---

# 21. Control flow

## 21.1 Blocks as expressions

The final expression of a block is its value when the surrounding construct expects a value.

```cessit
fn double(take x: Int) -> Int {
    x * 2
}
```

## 21.2 Explicit return

`return` performs an early return.

```cessit
fn divide(take a: Int, take b: Int) -> Result[Int, String] {
    if b == 0 {
        return Err[Int, String]("division by zero");
    }

    return Ok[Int, String](a / b);
}
```

## 21.3 Definite assignment

The compiler verifies that a value is initialized before it is read across branches, loops, matches, early returns, and recursive scopes.

## 21.4 Unreachable code

Unreachable statements after a non-branching exit are compiler errors.

---

# 22. Error handling

`Result[T, E]` and `Option[T]` are ordinary enums. There is no implicit exception propagation operator.


Library-level alias constructor helpers may provide ergonomic names for enum constructors without special compiler syntax:

```cessit
fn Ok[T, E](take value: T) -> Result[T, E] {
    return Result[T, E].Ok(value);
}
```

```cessit
fn divide(take a: Int, take b: Int) -> Result[Int, String] {
    if b == 0 {
        return Err[Int, String]("division by zero");
    }

    return Ok[Int, String](a / b);
}
```

A caller handles the result explicitly:

```cessit
fn main() {
    match divide(10, 2) {
        Ok(take result: Int) => println(result);
        Err(take e: String) => println(e);
    }
}
```

`Never` represents an impossible value. It may be used in ordinary generic types such as `Result[T, Never]`.

---

# 23. Program entry point

`main` is the program entry point and uses the same ordinary function declaration syntax as every other function.

The entry point has no caller-visible return value. Its body may require capabilities in the same way as any other function.

Example:

```cessit
fn main() -> () can IO {
    println(IO.read_line());
}
```

# 24. Capabilities

Capabilities describe permission to perform external or otherwise privileged operations.

A function may declare:

```text
can Capability1, Capability2
```

The clause is optional. No `can` clause means that the function requires no capabilities.

## 24.1 Capability checking

A function may invoke an operation only when every capability required by that operation is available to the caller:

```text
required(callee) ⊆ available(caller)
```

Example:

```cessit
fn fetch(take url: String) -> String can IO {
    IO.http_get(url)
}
```

A caller without `IO` cannot call `fetch`.

## 24.2 Allocation and bounded storage

`Alloc` is reserved for operations that may obtain dynamically managed memory from an allocation facility.

It is **not** automatically required for every escaping continuation. Cessit's concurrency model can instead use an explicitly supplied bounded task-storage capability.

The exact capability name for that storage mechanism remains **Provisional**; see section 29.

# 25. Effects

Effects are named interfaces of operations.

```cessit
effect IO {
    http_get(take url: String) -> String;
}

effect Timer {
    sleep(take millis: Int) -> ();
}
```

An effect declaration defines operations but does not hardcode their runtime behavior.

An effect operation transfers control to the nearest lexically governing handler for that effect. The suspended computation is represented by a single-shot continuation.

Capabilities and effects are related but distinct:

- an **effect** declares what operations exist;
- a **capability** grants permission to perform those operations.

The core language does not hardcode generators, timers, channels, or schedulers as special compiler features. They are expressed using the same effect/handler machinery.

---

# 26. Effect handlers

Handlers are defined separately from effect declarations.

```cessit
handler BlockingIOHandler for IO {
    http_get(take url: String) -> String {
        ...
    }
}
```

Another handler can provide different semantics for the same effect:

```cessit
handler TestIO for IO {
    fn http_get(take url: String) -> String {
        return fake_response(url);
    }
}
```

## 26.1 Lexical handler scope

Handlers are **lexically scoped**. A handler applies only to effect operations executed within its handling construct.

```cessit
handle IO with TestIO.new() {
    take response: String = load("example");
    println(response);
}
```

An effect performed outside that construct is not handled by `TestIO` merely because the same function was called earlier.

## 26.2 Deep handlers

Cessit uses **deep handlers**.

When a handler resumes a continuation, the resumed computation remains under that handler until the lexical handling scope is exited.

Conceptually:

```text
handle E with H {
    computation;
}

E.operation()
    -> H handles operation
    -> H resumes continuation
    -> continuation remains under H
```

This is important for generators and other repeated resumptions: the handler remains available for subsequent effect operations performed by the resumed computation.

Deep handling does not make a handler dynamically scoped. The handler must still belong to the lexical handling scope enclosing the computation.

## 26.3 Handler state

A handler may have explicit state. Handler state that must survive a suspension is part of the handler/continuation state and is subject to the same ownership, lifetime, and storage rules as other live state.

A continuation may not resume into a handler state that has already been destroyed.

## 26.4 Handler dispatch

When a handler is statically known, the compiler may specialize or directly dispatch to it without a dynamic vtable.

If handler selection is genuinely dynamic, an indirect dispatch representation may be required. The language does not require every possible handler dispatch to be statically monomorphized.

---

# 27. Continuations

A continuation represents the suspended computation after an effect operation.

## 27.1 Single-shot rule

Each continuation instance may be resumed at most once.

This is a linear ownership rule. A continuation cannot be copied, cloned, or resumed twice.

A computation may suspend many times. Every suspension creates a fresh continuation instance.

## 27.2 Continuation state

A continuation may contain:

- the program state required to resume execution;
- values live across the suspension point;
- owned captures;
- references that remain valid across suspension;
- handler state required by deep handling;
- the control-state discriminant.

Only state live across the suspension point is retained.

## 27.3 State-machine lowering

A compiler may lower a suspended computation to a concrete state-machine representation:

```text
StateStruct =
    discriminant
    + live values
    + required handler state
    + required continuation metadata
```

The compiler computes the exact size and alignment of this representation.

This representation is statically sized when the continuation's live state is statically bounded.

## 27.4 Escaping continuations

A continuation that does not outlive its creating activation may be stored in compiler-controlled activation storage.

A continuation that escapes its creating activation cannot remain in the dead caller's stack frame.

Cessit therefore does **not** silently extend an ordinary stack frame and does **not** silently fall back to `malloc`.

Instead, an escaping continuation must be placed into storage supplied by the program, such as a pre-allocated task pool or arena.

The compiler computes the continuation's required storage size and verifies that the selected storage facility can accommodate it.

If the required storage is unavailable, the storage operation fails according to the storage facility's declared API; the compiler must not silently introduce hidden heap allocation.

---

# 28. Generators

Generators are expressed as effects and handlers rather than as a dedicated `async` function category.

A generator-like effect may be declared as:

```cessit
effect Generator[T] {
    yield(take value: T) -> ();
}
```

A computation can perform the effect:

```cessit
fn count_to(take n: Int) -> () can Generator[Int] {
    mut i: Int = 0;
    while i < n {
        Generator[Int].yield(i);
        i = i + 1;
    }
}
```

A handler can interpret the effect as printing, collecting, streaming, or exposing a resumable generator interface.

## 28.1 Generator state

The compiler-generated suspended state contains only values live across suspension points.

Explicit captures are represented as ordinary state-machine fields with the same ownership modes as closure captures:

```text
|take x: T|  -> state owns x
|read x: T|  -> state retains shared access to x
|mut x: T|   -> state retains exclusive access to x
```

A generator is therefore not semantically a special runtime object. It is a conventional use of effects, handlers, continuations, and generated state.

## 28.2 Repeated suspension

A generator may execute:

```text
yield -> resume -> yield -> resume -> ...
```

Each `yield` produces a new single-shot continuation. The generator itself is not subject to the single-shot restriction.

---

# 29. Concurrency

Concurrency is built from effects, handlers, continuations, and explicit task storage.

The language does not define one mandatory scheduler. A runtime or library may implement cooperative tasks, event loops, thread pools, interrupt-driven systems, or other execution models using the same effect mechanism.

Typical concurrency effects can include:

```cessit
effect Channel[T] {
    fn send(take value: T) -> ();
    fn receive() -> T;
}

effect Spawn[T] {
    fn spawn(take task: fn() -> T) -> Task[T];
}
```

These are ordinary effect declarations. Their handlers define scheduling and communication semantics.

## 29.1 Concurrency does not imply heap allocation

A concurrency operation may allocate task state, but the allocation strategy is explicit.

An implementation that uses a pre-allocated task pool can provide deterministic bounded memory use.

An implementation that uses dynamic allocation must require the relevant allocation capability.

## 29.2 Cross-task ownership

Sending an owned value to another task transfers ownership unless the value is explicitly shared through a type whose semantics permit concurrent access.

A borrowed reference may not be sent to a task whose lifetime can exceed the referent.

The compiler must verify these conditions statically.

## 29.3 Exclusive access across suspension

An exclusive access that survives suspension remains exclusive for the entire interval in which the suspended computation can resume using it.

Another conflicting shared or exclusive access is therefore rejected until the original access is no longer live.

This is a static property even if the scheduler itself is dynamic.

---

# 30. Task storage and bounded allocation

**Provisional name:** The capability for programmer-supplied continuation storage may later receive a more specific name than `Alloc`.

The semantic requirement is fixed:

> An escaping continuation must have storage that outlives its creating activation. Cessit must not obtain that storage through an implicit heap allocation.

A task pool or arena can supply bounded storage:

```cessit
struct TaskPool[TaskState] {
    ...
}

fn worker() -> Stream {
    ...
}

take pool: TaskPool[Stream] = TaskPool[Stream].new_static();
take task: Task[Stream] = pool.spawn(worker);
```

The compiler knows the concrete storage requirements of `worker`'s suspended states and checks compatibility with the pool's slot requirements.

The precise API for heterogeneous pools, variable-size state machines, exhaustion behavior, and pool capabilities remains provisional.

The core invariant is that **the compiler never silently converts an escaping continuation into an unbounded heap allocation merely to make the program compile**.

---

# 31. Unsafe code

Unsafe operations are explicitly marked at declaration and call sites.

## 31.1 Unsafe declarations

The `unsafe` modifier appears before the function declaration:

```cessit
trait Indexable[T] {
    unsafe fn at(read self: &This, take index: usize) -> &T;
}

unsafe fn raw_read(take pointer: RawPtr[Int]) -> Int {
    ...
}
```

## 31.2 Unsafe calls

Calling an unsafe function requires an `unsafe` expression:

```cessit
read element: &Int = unsafe array.at(5);
```

There are no implicit unsafe regions.

## 31.3 Auditability

Unsafe declarations identify operations that require unsafe use, and every unsafe call site is syntactically visible.

---

# 32. Indexing and slicing

Indexing is expressed by traits rather than compiler-special-case methods.

## 32.1 Range

```cessit
struct Range {
    start: usize;
    end: usize;
}
```

## 32.2 Single-element access

```cessit
trait Indexable[T] {
    unsafe fn at(read self: &This, take index: usize) -> &T;
    fn get(read self: &This, take index: usize) -> Result[&T, IndexError];
}
```

Example:

```cessit
take array: Array[Int; 10] = Array[Int; 10].new();
read element: &Int = unsafe array.at(5);

match array.get(5 {
    Ok(read element: &Int) => println(element);
    Err(take error: IndexError) => println("index out of bounds");
}
```

## 32.3 Range access

```cessit
trait RangeIndexable[T] {
    unsafe fn at(read self: &This, take range: Range) -> &Slice[T];
    fn get(read self: &This, take range: Range) -> Result[&Slice[T], RangeError];
}
```

---

# 33. Iterators

Iterators use explicit ownership and borrowing. If an iterator carries references whose lifetimes cannot be inferred, the same `from` annotations used elsewhere are written explicitly.

## 33.1 Owning iterator

An owning iterator can store owned state:

```cessit
struct Iterator[T, S] {
    state: S;
    next_fn: fn(mut S) -> Option[T];
}
```

## 33.2 Read iteration

A read iterator borrows a collection:

```cessit
trait ReadIterable[T] {
    fn read_iter(read self: &This) -> Iterator[T, ReadState[This]];
}
```

The resulting iterator may not outlive the collection it references. If that relationship cannot be inferred, it is expressed with `from`.

## 33.3 Take iteration

A take iterator consumes a collection:

```cessit
trait TakeIterable[T] {
    fn take_iter(take self: This) -> Iterator[T, This];
}
```

The iterator owns the collection and may outlive the original binding.

## 33.4 Mutable iteration

A mutable iterator exclusively borrows a collection:

```cessit
trait MutIterable[T] {
    fn mut_iter(mut self: &This) -> Iterator[T, MutState[This]];
}
```

The iterator remains tied to the lifetime of the exclusive borrow.

---

# 34. Smart pointers

Allocation strategies are represented by distinct nominal types.

```cessit
struct BoxNode[T] {
    inner: Box[Node[T]];
}

struct RcNode[T] {
    inner: Rc[Node[T]];
}

struct ArcNode[T] {
    inner: Arc[Node[T]];
}
```

Their ownership, allocation, reference-counting, and concurrency semantics are defined by their library implementations.

---

# 35. Expression safety rules

The compiler rejects safe code that would violate any of the following:

1. use of a moved value;
2. mutation through shared ordinary access;
3. simultaneous conflicting exclusive and shared ordinary accesses;
4. references that outlive their sources;
5. reassignment of `take` or `read` bindings;
6. use of uninitialized storage;
7. calls requiring unavailable capabilities;
8. calls to unsafe functions outside an `unsafe` expression;
9. reads before definite initialization;
10. shadowing a visible binding;
11. resuming a continuation more than once;
12. resuming a continuation after its required state or handler environment has been destroyed;
13. moving a reference-bearing suspended state into a context where its references become invalid;
14. creating an escaping continuation without compatible supplied storage.

Unsafe code may explicitly bypass guarantees assigned to the unsafe operation, but the operation remains syntactically marked.

---

# 36. Compiler model

A conforming compiler should conceptually process a program through the following stages.

## 36.1 Parsing

Build the syntax tree using Cessit's brace-delimited blocks and semicolon-terminated statements.

## 36.2 Name resolution

Resolve every binding reference and reject unknown names, duplicate bindings, and forbidden shadowing.

## 36.3 Type checking

Verify explicit type annotations, generic arguments, function calls, trait requirements, expression types, and return types. No ordinary type inference is performed.

## 36.4 Ownership and borrow checking

Track ownership transfers, shared accesses, exclusive accesses, moved-from values, closure environments, continuation state, and reference lifetimes.

## 38.5 Lifetime checking

Verify explicit and inferred `from` relationships and compute the meet of lifetimes associated with a shared relationship placeholder.

## 36.6 Capability checking

Verify that every required capability is available at the call site.

## 36.7 Effect and handler checking

Verify that every performed effect is permitted by the function's declared capabilities and that every effect operation has a valid handler in the required execution context.

## 36.8 Unsafe checking

Require every unsafe operation to appear inside an explicitly marked unsafe expression.

## 36.9 Definite initialization

Reject reads from values that may not yet have been initialized.

## 36.10 Continuation lowering

Lower effect operations and handlers into a representation that preserves:

- single-shot continuation semantics;
- lexical handler scope;
- deep handler resumption;
- ownership and lifetime rules;
- live state across suspension.

## 36.11 Storage verification

For every continuation that may escape its creating activation, compute its required storage and verify that the supplied task-storage mechanism can accommodate it. The compiler must not silently introduce heap allocation to satisfy this requirement.

## 36.12 Code generation

Only after all static checks succeed may executable code be generated.

---

# 37. Testing

Testing is designed around Cessit's existing ownership, capability, trait, and lexical-effect systems rather than a hidden mocking or dependency-injection framework.

## 37.1 Effect-based testing

Because effects use lexically scoped handlers, production behavior such as I/O or database access can be replaced by a test handler within a bounded lexical scope. Tests therefore depend on stable effect interfaces rather than concrete implementations.

```cessit
handle IO with TestIO.new() {
    // code under test
}
```

## 37.2 Access modes in tests

The separation of `take`, `read`, and `mut`, together with explicit `&T` reference types, lets tests inspect state through shared access without implicitly cloning or moving values.

## 37.3 Trait-based contract testing

Tests may target trait interfaces rather than concrete private implementations. Replacing an implementation behind the same trait contract therefore need not invalidate tests that depend only on the contract.

## 37.4 Result-returning tests

Tests may return explicit `Result[T, E]` values. Test execution can therefore propagate failures without hidden exception or panic-based unwrapping.

## 37.5 Effect-driven property testing

Native generators can provide streams of generated test data through the same effect, handler, and single-shot continuation machinery used elsewhere in the language.

## 37.6 Capability restrictions

Test functions and test blocks may declare capabilities. A test that does not require `IO`, allocation, or another capability can be checked by the compiler so that accidental use of those operations is rejected.

## 37.7 Test declarations

The language may provide dedicated top-level test declarations parsed directly by the compiler, avoiding macro-based test registration and module boilerplate. The exact test declaration syntax and runner interface remain subject to the testing design pass.

---

# 38. Canonical examples

## 38.1 Immutable pipeline

```cessit
take input: Int = 5;
take plus_one: Int = input + 1;
take doubled: Int = plus_one * 2;
println(doubled);
```

## 38.2 Mutable state

```cessit
mut state: State = initial_state();
state = process_step_one(state);
state = process_step_two(state);
state = process_step_three(state);
```

## 38.3 Generic transformation

```cessit
fn process[T](take value: T) -> T {
    return value;
}

take number: Int = process[Int](42);
```

## 38.4 Shared borrowing

```cessit
take name: String = "hello";
read view: String = name;
take length: Int = view.length();
```

## 38.5 Exclusive borrowing

```cessit
mut values: Vec[Int] = Vec[Int].new();
values.push(1);
values.push(2);

fn normalize(mut values: Vec[Int]) -> () {
    values.sort();
}
```

## 38.6 Lifetime selection

```cessit
fn pick[T](take condition: Bool, read a: &T from r, read b: &T from r) -> &T from r {
    if condition {
        return a;
    } else {
        return b;
    }
}

read result: &Item = pick[Item](true, foo from outer, bar from static);
```

## 38.7 Closure with owned state

```cessit
take multiplier: Int = 5;

take multiply: (take Int) -> Int =
    fn(take x: Int) -> Int |take multiplier: Int| {
        return x * multiplier;
    };
```

## 38.8 Effectful function

```cessit
fn load(take url: String) -> String can IO {
    return IO.http_get(url);
}
```

## 38.9 Effect handling

```cessit
handler TestIO for IO {
    fn http_get(take url: String) -> String {
        return fake_response(url);
    }
}

handle IO with TestIO.new() {
    take response: String = load("example");
    println(response);
}
```

## 38.10 Unsafe indexing

```cessit
read value: &Int = unsafe array.at(5);
```

## 38.11 Bounded task storage

```cessit
take pool: TaskPool[WorkerState] = TaskPool[WorkerState].new_static();
take task: Task[WorkerState] = pool.spawn(worker);
```

The compiler computes the required suspended-state size for `worker` and verifies that the pool can store it.

---

# 41. Design invariants

The following are core invariants of Cessit:

1. **Ownership is explicit.**
2. **Reference-ness is explicit in the type.**
3. **`mut` is required for local reassignment.**
4. **Struct and enum fields do not repeat binding verbs.**
5. **Copies and clones are explicit operations.**
6. **`Copy` is compiler-controlled and non-overridable.**
7. **Borrow provenance is represented by lifetimes, with inference for unambiguous cases.**
8. **A repeated lifetime relationship combines participating source lifetimes through their shorter common validity interval.**
9. **Ordinary values are never implicitly uninitialized.**
10. **Unsafe declarations and unsafe call sites are both explicit.**
11. **Capabilities are checked statically.**
12. **Effect declarations are separate from handlers.**
13. **Handlers are lexically scoped and deep.**
14. **Every continuation instance is single-shot.**
15. **Escaping continuations use programmer-supplied bounded storage or an explicitly authorized allocation facility; no hidden heap fallback occurs.**
16. **Generators are an effect/handler/continuation pattern, not a privileged function category.**
17. **No ordinary type inference is performed in the initial compiler.**
18. **Bindings may not shadow visible names.**
19. **Recursive binding groups use `rec`.**
20. **Blocks and declaration bodies use `{}` and statements use `;`.**
