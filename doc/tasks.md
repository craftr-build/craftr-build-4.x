# Tasks

Craftr allows you to embed actual Python functions into the build process. We
call this concept "tasks". Tasks end up being plain rules and build instructions
in the Ninja manifest. They will then be invoked using the `craftr run` command.
Note that for each task that is executed, your build-script is also executed
another time.

You can build functions that create tasks, so you can create multiple instances
of the same task with different inputs, or you just create a task once from a
single function.

__A simple example__

```python
git = load('craftr.utils.git').Git(project_dir)  # Git repository helper for this project

@task(outputs = [buildlocal('include/gitversion.h')])
def gitversion(inputs, outputs):
    with open(outputs[0], 'w') as fp:
      fp.write('#pragma once\n'
              '#define GITVERSION "{}"\n'
        .format(git.describe()))
```

We can then compile a C-program that includes the generated `gitversion.h`
file, but we must ensure that the task is executed *before* the C-program
is compiled.

```python
cxx = load('craftr.lang.cxx')
app = cxx.binary(
  output = 'main',
  inputs = cxx.c_compile(
    sources = glob(['src/*.c']),
    include = [buildlocal('include')]
  ) << gitversion
)
```

__Task generators__

We can generalise the `gitversion` task so it can be used multiple times.

```python
Git = load('craftr.utils.git').Git  # Git repository helper for this project

def write_gitversion(project_dir = None):
  if not project_dir:
    project_dir = session.module.project_dir
  git = Git(project_dir)

  def worker(inputs, outputs):
    with open(outputs[0], 'w') as fp:
      fp.write('#pragma once\n'
              '#define GITVERSION "{}"\n'
        .format(git.describe()))

  outputs = [buildlocal('include/gitversion.h')]
  return gentask(worker, outputs = outputs, name = gtn())

gitversion = write_gitversion()
```
