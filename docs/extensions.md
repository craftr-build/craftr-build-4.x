
### Implementing a target handler

If a module that implements a target handler is added as a dependency to a
target, that handler is also automatically added to that target. Usually,
target handlers require a fair amount of code for their implementation, thus
it is usually inconvenient to implement them inside an `eval` block.  
Instead, use `load` statement to load a Python file that implements a target
handler.

```python
project "cxx" v1.0.0
load "./cxx-handler.py"
```

A target handler can be implemented using the `craftr.TargetHandler` class
and must be registered to the project with `project.register_target_handler()`.

```python
import craftr

class CxxTargetHandler(craftr.TargetHandler):

  def setup_target(self, target):
    target.define_property('cpp.srcs', list)
    target.define_property('cpp.includePaths', list)
    target.define_property('cpp.defines', list)
    target.define_property('cpp.compilerId', str, 'msvc', readonly=True)
  
  def setup_requires(self, requires):
    requires.define_property('cpp.link', bool, True)

  def translate_target(self, target):
    srcs = target.get_property('cpp.srcs')
    for dep in target.requires():
      if dep.get_property('cpp.link'):
        for file in dep.output_files():
          if file.tag in ('c', 'cpp'):
            srcs.append(file.name)
    # TODO ..

project.register_target_handler(CxxTargetHandler)
```
