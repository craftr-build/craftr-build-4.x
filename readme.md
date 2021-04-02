# craftr

Craftr is a Gradle-like build-system implemented in Python.

## Quickstart (DSL)

```py
apply_plugin('cxx')
apply_plugin('gitversion')

cpp_application {
  sources glob('src/**/*.cpp')
  executable_name f'main-{gitversion()}'
}
```

## Quickstart (Python)

```py
project.apply_plugin('cxx')
project.apply_plugin('gitversion')

app = project.cpp_application()
app.sources(project.glob('src/**/*.cpp'))
app.executable_name(f'main-{gitversion()}')
```

## Development

Craftr is composed of three main components:

* `craftr-core` &ndash; The pure Python API for describing and executing builds.
* `craftr-dsl` &ndash; Craftr DSL parser and transpiler.
* `craftr-stdlib` &ndash; Standard library of Craftr plugins.

---

<p align="center">Copyright &copy; 2021 &ndash; Niklas Rosenstein</p>
