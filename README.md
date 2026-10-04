# Cessit

Cessit is a statically typed systems programming language designed to provide strict, explicit control over memory access, lifetime relationships, and effect management without hidden magic or implicit syntax overhead.

## 1. Core Principles & Philosophy

* Separation of Binding and Type: Cessit permanently decouples how a binding accesses a value (take, read, mut) from the value's type itself (where reference-ness is explicitly represented by &T).

* No Function-Coloring: I/O, generators, and concurrency are unified using lexically scoped deep effect handlers and single-shot continuations rather than colored async/await keywords.

* Statically Checked Capabilities: Privileged operations require explicit capabilities (e.g., can IO, Timer), checked statically at compile time.

* Predictable Continuation Storage: Escaping continuations require programmer-supplied bounded storage (such as a task pool or arena); the compiler never silently falls back to an unbounded heap allocation.

## 2. Lexical & Binding Semantics

Every variable binding in Cessit must explicitly declare its access mode. There is no implicit move or copy.

| Binding Keyword | Semantics | Ownership Impact |
| take | Takes ownership of the value. | Moves the value; source becomes uninitialized. |
| read | Borrows the value immutably. | Multiple active readers allowed; source cannot be mutated. |
| mut | Borrows the value mutably. | Exclusive access; source cannot be read or borrowed elsewhere. |

Example: Explicit Binding

```cessit
fn process_data(take raw: String) -> String {
    return raw; // raw ownership is moved into the function scope
}
```

## 3. Types and References

Reference types are explicitly marked with `&T` and carry optional lifetime parameters to verify safety across scopes.

```cessit
// Function accepting an immutable reference with an explicit lifetime 'r
fn get_length(read s: &String from r) -> Int {
    return s.len();
}
```

## 4. Effect System & Concurrency

Cessit replaces traditional async runtimes with algebraic effect handlers. Effects are declared, handled lexically, and tracked via function capability bounds (`can EffectName`).

### Effect Declaration & Handling

```cessit
effect IO {
    http_get(take url: String) -> String;
}

handler TestIO for IO {
    fn http_get(take url: String) -> String {
        return "mocked_response";
    }
}

fn fetch_item(take url: String) -> String can IO {
    return IO.http_get(url);
}

fn main() -> () can IO {
    take target: String = "https://example.com";
    
    handle IO with TestIO.new() {
        take res: String = fetch_item(target);
        println(res);
    }
}
```

## 5. Grammar & Syntax Reference

* Statements: Terminated by semicolons (`;`).

* Blocks: Enclosed in curly braces (`{ ... }`).

* Functions: Declared with `fn name(parameters) -> ReturnType [can Capabilities]`.

## Project Architecture

* `spec/`: Formal language grammar and syntax specifications.
* `examples/`: Idiomatic `.ces` source files demonstrating core language mechanics.
