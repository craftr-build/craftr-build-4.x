# craftr-dsl

This package provides a transpiler for the Craftr domain-specific-language. The language is
a full syntactic superset of Python (with some exceptions\*) and a sprinkle of Groovy-style
closures and unparenthesised function calls.

__Requirements__

* Python 3.6 or newer

<small>_\*exceptions_

* set literals
* type annotations
* walrus operator

> These syntactical features could be supported in theory but are not prioritised.
</small>



## Introduction

Variables are looked up through the context's current closure (a `craftr.core.closure.Closure`
object) with the special name `__closure__`. Unless previously explicitly declared, a variable
always refers to a member of an object resolved from the current context. On the global level,
and in the context of a Craftr build script, the closure delegates to a Craftr `Project` object.

The following statements are equal:

```py
print(name)
print(project.name)
print(__closure__.delegate.name)
```

And such are the following assignments:

```py
name = 'my-project-name'
project.name = 'my-project-name'
__closure__.delegate.name = 'my-project-name'
```

In order to define a local variable that is not looked up through the closure, it must be prefixed
with the `def` keyword.

```py
def name = 'local variable called name'
assert project.name != name
```

Function calls at the root of the statement do not need to be parenthesised, but it may be needed
to disambiguate certain syntactical constructors.

```py
print 'Hello, World', file=sys.stderr
print *args  # Multiply print by args?
print(*args) # Ah yes, that's it
print *args, file=sys.stderr  # Actually a syntax error
```

A new closure can be defined by using the `() -> { ... } ` or just `{ ... }` syntax. It is a common
pattern in Craftr build scripts to pass a closure to a function in order to allow that function to
invoke it with a new delegate (for example a `Task` object).

```py
task('sayHello') {
  assert __closure__.delegate is project.tasks.sayHello
  do_last {
    print 'Hello, World!'
  }
}

# Error: Unable to resolve 'do_last' in Project context
do_last {
  print 'Not happening'
}
```

Closures can also accept arguments. With an argument list provided, a closure definition may also omit
the curly braces and contain exactly one expression.

```py
print list(filter(k -> k % 2, range(10)))  # 1, 3, 5, 7, 9

promise.then((status, value) -> {
  if status is not None:
    raise Exception(status)
  return do_something(value)
})
```


---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
