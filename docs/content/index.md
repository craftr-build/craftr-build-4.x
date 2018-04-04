+++
title = "Home"
renderTitle = false
ordering = 0
+++

# Welcome to the Craftr documentation!

Craftr is a modular software build system written in Python that has native
support for C/C++, C#, Cython, Java and other languages. Craftr uses [Ninja]
as its build backbone.

  [Ninja]: https://github.com/ninja-build/ninja

### How to Install  Craftr

  [Node.py]: https://github.com/nodepy/nodepy

Craftr builds on the [Node.py] runtime and must be installed via its package
manager `nodepy-pm`.

    $ pip install nodepy-runtime
    $ nodepy https://nodepy.org/install-pm.py
    $ nodepy-pm install git+https://github.com/craftr-build/craftr.git

---

### Examples

<table>
<tr><th>C</th><th>C++</th></tr>
<tr>
<td>

```python
project "examples.c"
target "main":
  requires "craftr/lang/cxx"
  cxx.srcs = ['main.c']
```

Run as `craftr -cb main:cxx.run`
</td>
<td>

```python
project "examples.cpp"
target "main":
  requires "craftr/lang/cxx"
  cxx.srcs = ['main.cpp']
```

Run as `craftr -cb main:cxx.run`
</td>
  </tr>
  <tr><th>C#</th><th>Java</th></tr>
  <tr>
    <td>

```python
project "examples.csharp"
target "main":
  requires "craftr/lang/csharp"
  csharp.srcs = glob('src/*.cs')
  csharp.packages = ['Newtonsoft.JSON:10.0.3']
  csharp.bundle = True
```

Run as `craftr -cb main:csharp.runBundle`
</td>
    <td>

```python
project "examples.java"
target "main":
  requires "craftr/lang/java"
  java.srcs = glob('src/**/*.java')
  java.artifacts = [
      'org.tensorflow:tensorflow:1.4.0'
    ]
  java.mainClass = 'Main'
  java.bundleType = 'merge'  # Or 'onejar'
```

Run as `craftr -cb main:java.runBundle`
</td>
  </tr>
  <tr><th>Haskell</th><th>OCaml</th></tr>
  <tr>
    <td>

```python
project "examples.haskell"
target "main":
  requires "craftr/lang/haskell"
  haskell.srcs = ['src/Main.hs']
```

Run as `craftr -cb main:haskell.run`
</td>
    <td>

```python
project "examples.ocaml"
target "main":
  requires "craftr/lang/ocaml"
  ocaml.srcs = ['src/Main.ml']
  # False to produce an OCaml bytecode file
  ocaml.standalone = True
```

Run as `craftr -cb main:ocaml.run`
</td>
  </tr>
  <tr><th>Vala</th><th>Cython</th></tr>
  <tr>
    <td>

```python
project "examples.vala"
target "main":
  requires "craftr/lang/vala"
  vala.srcs = ['src/Main.vala']
```

Run as `craftr -cb main:vala.run`
</td>
    <td>

```python
project "example.cython"
target "main":
  requires "craftr/lang/cython"
  cython.srcs = ['src/Primes.pyx']
  cython.main = ['src/Main.pyx']
```

Run as `craftr -cb main/Main:cxx.run`
</td>
  </tr>
</table>
