# Tips & Trick

## Using Git submodules to manage dependencies

Git submodules can be useful to keep track of a projects dependencies.
For example, consider your project requires a library from GitHub that
comes with a Craftr build script:

    git submodule add https://github.com/mycompany/somelibrary.git vendor/mycompany/somelibrary

If the module provides a `nodepy.json`, you could use the Node.py package
manager to link the module into the build system.

    nodepy-pm install -e vendor/mycompany/somelibrary

If the project however only contains a `build.craftr` script, you can use
the `craftr --link` command, which essentially does the same and derives
the Node.py module name from the project name defined in the build script.

    craftr --link vendor/mycompany/somelibrary

The cleanest way however would be to use the `link_module` statement provided
by the Craftr DSL. It basically does the same as the `craftr --link` command,
but it will do the linking step in a temporary directory every time that you
configure the build. Also, if multiple modules try to link other modules with
the same name, the order matters and the first one to link a module takes
precedence.

```python
project "myproject"
link_module "./vendor/mycompany/somelibrary"

target "main":
  requires "mycompany/somelibrary"
  # ...
```
