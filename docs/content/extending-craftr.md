+++
title = "Extending Craftr"
ordering = 5
+++

A module that is imported can register a `TargetHandler` to the Craftr build
context. This TargetHandler can then register properties to the module, target
and dependency blocks and gets a chance to read the property values to turn
them into build actions.

The TargetHandler can be implemented in the build script itself or in another
Python script that you can `import`. Note that you will need to import that
Craftr build context from the build script.

<table>
<tr><th>Inline</th><th>Separate</th></tr>
<tr><td>

```python
# java/build.craftr
project "java" v1.0.0
eval:>>

import craftr from 'craftr.craftr'

class JavaTargetHandler(craftr.TargetHandler):
  # ...
```

</td><td>

```python
# java/build.craftr
project "java" v1.0.0
import "./targethandler"

# java/targethandler.py
import craftr, {context} from 'craftr.craftr'

class JavaTargetHandler(craftr.TargetHandler):
  # ...
```

</td></tr>
</table>

A target handler must be registered with `context.register_handler()`.

```python
import craftr, {context, path} from 'craftr.craftr'

class JavaTargetHandler(craftr.TargetHandler):

  def init(self, context):
    props = context.target_properties
    props.add('java.srcs', craftr.StringList)
    # ...
  
  def translate_target(self, target):
    data = target.get_props('java.', as_object=True)
    if data.srcs:
      # Generate a build action to compile the Java source files.
      data.srcs = [path.canonical(x, target.directory) for x in data.srcs]
      outputs = [path.setsuffix(x, '.class') for x in data.srcs]
      command = ['javac', '${in}']
      action = target.add_action('java.javac', commands=[command])
      buildset = action.add_buildset()
      buildset.files.add(data.srcs, ['in'])
      buildset.files.add(outputs, ['out', 'java.class'])

context.register_handler(JavaTargetHandler())
```

Make sure you tag the output files of an action appropriately, as other
targets can use it to access these files and create further build actions
with them.
