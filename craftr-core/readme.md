# craftr-core

The `craftr-core` package provides the core functionality for the Craftr build system, such as
an abstraction for units of work (actions) and the dependencies between that work (tasks).
A property system allows for the lazy evaluation of configuration values while keeping track
of the data lineage in order to compute task dependencies.

To use the `craftr-core` package from a plain Python script, you need to manually instantiate at
`Context` and `Project`.

__Example__

```python
import sys
from craftr.core import Context
from craftr.core.actions import WriteFileAction, CommandAction

ctx = Context()
project = ctx.project()

write_task = project.task('writeFile', WriteFileAction.as_task)
write_task.text = 'print("Hello, World!")\n'
write_task.file_path = project.build_directory / 'out.py'

run_task = project.task('runFile', CommandAction.as_task)
run_task.commands = [[sys.executable, write_task.file_path]]
run_task.default = False
run_task.always_outdated = True

assert write_task in run_task.get_dependencies()

ctx.execute(sys.argv[1:] or None)
```

Run with

```
$ python build.py :runFile
> Task craftr-core:writeFile
> Task craftr-core:runFile
Hello, World!
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
