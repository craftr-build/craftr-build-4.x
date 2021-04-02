# kahmi-core

The kahmi-core package provides the core functionality for the Kahmi build system, such as
an abstraction for units of work (actions) and the dependencies between that work (tasks).
A property system allows for the lazy evaluation of configuration values while keeping track
of the data lineage in order to compute task dependencies.

__Example__

```python
import sys
from kahmi.core import Context
from kahmi.core.actions import WriteFileAction, CommandAction

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
> Task kahmi-core:writeFile
> Task kahmi-core:runFile
Hello, World!
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
