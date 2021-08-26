# craftr-dsl

The Craftr DSL is a transpiler for the Python language that introduces the concept of **closures** an 
**function calls without parentheses** into the language.

## Getting started

### Installation 

From Pip:

    $ pip install craftr-dsl

Latest from GitHub:

    $ pip install git+https://github.com/craftr-build/craftr-dsl

Requirements: Python 3.6 or newer

### Hello, World!

A convoluted Hello, World! example in Craftr DSL might look like this:

```py
# hello.craftr
world = { self('World!') }
world { print('Hello,', self) }
```

This is transpiled to

```py
# $ python -m craftr.dsl hello.craftr -E | grep -v -e '^$'
def _closure_1(self):
    self('World!')
world = _closure_1
def _closure_2(self):
    print('Hello,', self)
world(_closure_2)
```

Abnd evaluates to

```py
# $ python -m craftr.dsl hello.craftr
Hello, World!
```

## Language features

### Closures

Closures can define a parameter list and can also have a single expression as their body. Only closures without
a parameter list will receive `self` as a default argument.

<table><tr><th>Craftr DSL</th><th>Python</th></tr>

<tr><td>

```py
filter({ self % 2 }, range(5))
```
</td><td>

```py
def _closure_1(self):
    self % 2
filter(_closure_1, range(5))
```
</td></tr>


<tr><td>

```py
filter(x -> x % 2, range(5))
```
</td><td>

```py
def _closure_1(x):
    return x % 2
filter(_closure_1, range(5))
```
</td></tr>


<tr><td>

```py
reduce((a, b) -> {
  a.append(b * 2)
  return a
}, [1, 2, 3], [])
```
</td><td>

```py
def _closure_1(a, b):
    a.append(b * 2)
    return a
reduce(_closure_1, [1, 2, 3], [])
```
</td></tr>

</table>


### Function calls without parentheses

Such function calls are only supported at the statement level. A function can be called without parentheses by
simply omitting them. Variadic and keyword arguments are supported as expected. Applying a closure on an object
is basically the same as calling that object with the function, and arguments following the closure are still
supported.


<table><tr><th>Craftr DSL</th><th>Python</th></tr>

<tr><td>

```py
print 'Hello, World!', file=sys.stderr
```
</td><td>

```py
print('Hello, World!', file=sys.stderr)
```
</td></tr>


<tr><td>

```py
map {
  print('Hello,', self)
}, ['John', 'World']
```
</td><td>

```py
def _closure_1(self):
    print('Hello,', self)
map(_closure_1, ['John', 'World'])
```
</td></tr>


<tr><td>

```py
list(map {  # Not allowed inside an expression
  print('Hello,', self)
}, ['John', 'World'])
```
</td><td>

```py
craftr.dsl.rewrite.SyntaxError: 
  in <stdin> at line 1: expected ) but got TokenProxy(Token(type=<Token.Control: 8>, value='{', pos=Cursor(offset=9, line=1, column=9)))
  |list(map {
  |~~~~~~~~~^
```
</td></tr>


</table>



### Limitations

Craftr DSL is intended to behave as a complete syntactic superset of standard Python. However there are currently
some limitations, namely:

* Literal sets cannot be expressed due to the grammar conflict with parameter-less closures
* Type annotations are not currently supported
* The walrus operator is not currently supported

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
