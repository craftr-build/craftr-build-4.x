
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

  def finalize_target(self, target, data):
    if not data.srcs:
      return
    data.objfiles = [path.setsuffix(x, '.o') for x in data.srcs]
    target.outputs().add(data.objfiles, ['cpp.obj'])

  def translate_target(self, target, data):
    command = ['gcc', '-c', '-o', '$out', '$in']
    action = target.add_action('cpp.compile')
    for infile, outfile in zip(data.srcs, data.objfiles):
      build = action.add_buildset()
      build.files.add(infile, ['in'])
      build.files.add(outfile, ['out'])
    # etc ...

project.register_target_handler(CxxTargetHandler)
```
