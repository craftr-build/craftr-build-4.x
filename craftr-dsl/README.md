# craftr-dsl

The Craftr DSL is an extension of the Python language with support for Groovy-like closures.

__Example:__

```python
buildscript {
  dependencies = ["craftr-git", "craftr-cxx"]
}

def cxx = load("craftr-cxx")
def git = load("craftr-git")

name = "myproject"
version = git.version()

cxx.executable {
  srcs = glob("src/*.cpp")
}
```

This code is transpiled to the following Python code:

```python
@__closure__.sub
def _closure_1(__closure__):
  __closure__['dependencies'] = ['craftr-git', 'craftr-cxx']
__closure__['buildscript'](_closure_1)

cxx = __closure__['load']('craftr-cxx')
git = __closure__['load']('craftr-git')

__closure__['name'] = 'myproject'
__closure__['version'] = git.version()

@__closure__.sub
def _closure_2(__closure__):
  __closure__['srcs'] = __closure__['glob']['src/*.cpp']
__closure__['cxx'].executable(_closure_2)
```

## Syntax & Semantics

The Craftr DSL is not a strict superset of the Python language, instead it wraps Python code and
swaps between DSL parsing and Python code parsing.

### Craftr DSL Syntax

1. **Define a local variable with the `def` Keyword**

    Local variables are defined using the `def` keyword. The variable can then be addressed in
    Python expressions or as call block targets (see below). The right hand side of the assignment
    must be a Python expression.

    ```python
    def my_variable = 42
    ```

2. **Set owner/delegate property**

    Assigning to a name that was not previously defined with the `def` keyword will attempt to
    assign the variable to a property of the closure's owner or delegate, or any of the parent
    closures.

    ```python
    name = "my-project"
    version = git.version()
    ```

3. **Parentheses-less function calls**

    Functions may be called without parentheses.

    ```python
    print "Hello, World!"  # Call without body

    buildscript {
      dependencies = ["craftr-python"]
    }

    cxx.build("main") {
      srcs = glob("src/*.cpp")
    }
    ```

4. **Closures**

    The Kamhi DSL provides a syntax for defining a `craftr.core.closure.Closure` object. It is
    essentially a multi-line lambda definition enclosed in curly braces, similar to how other
    languages define lambdas (e.g. Java, TypeScript, Groovy).

    ```python
    def get_random_number = {
      import random
      random.randint(0, 255)
    }

    print get_random_number()
    ```

    The last expression in a closure is it's return value, but the `return` keyword is of course
    also supported. Closures may accept arguments by defining the parameter list before an arrow.

    ```python
    def incrementer = n -> { n + 1 }
    def adder = (a, b) -> { a + b }
    ```

    > Note: Python 3 set syntax is not supported in Craftr. For example, `{a, b, c}` would be
    > interpreter as a closure returning a tuple of the values a, b and c instead of a set that
    > containts the three values.

5. **Macros**

    Macros are plugins that can be enabled in the Craftr DSL parser to implement custom parsing
    logic following a macro identifier. The Craftr DSL parser comes with a YAML plugin out of the
    box:

    ```python
    buildscript {
      dependencies = !yaml {
        - craftr-git
        - craftr-python
      }
    }

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
