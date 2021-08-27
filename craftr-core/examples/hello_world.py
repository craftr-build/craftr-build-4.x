
import sys
from craftr.core import Context, Project
from craftr.core.actions import WriteFileAction, CommandAction

ctx = Context()
project = Project(ctx)

write_task = project.task('writeFile', WriteFileAction.as_task)
write_task.text = 'print("Hello, World!")\n'
write_task.file_path = project.build_directory / 'out.py'

run_task = project.task('runFile', CommandAction.as_task)
run_task.commands = [[sys.executable, write_task.file_path]]
run_task.default = True
run_task.always_outdated = True

assert write_task in run_task.get_dependencies()

ctx.execute(sys.argv[1:] or None)
