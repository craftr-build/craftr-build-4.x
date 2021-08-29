
import typing as t
from pathlib import Path

import typing_extensions as te

from craftr.build.lib import ExecutableInfo
from craftr.core.actions import Action, CreateDirectoryAction, CommandAction
from craftr.core import Namespace, Project, Property, Task


class ProcessorTask(Task):
  inputs: te.Annotated[Property[t.List[Path]], Task.Input]
  outputs: te.Annotated[Property[t.List[Path]], Task.Output]
  additional_vars: te.Annotated[Property[t.Dict[str, t.List[str]]], Task.Input]
  executable: Property[ExecutableInfo]
  args: Property[t.List[str]]
  batch: Property[bool]

  def _render_command(self, executable: ExecutableInfo, template_vars: t.Dict[str, t.List[str]]) -> CommandAction:
    args: t.List[str] = list(executable.invokation_layout or [executable.filename])
    for arg in self.args.or_else([]):
      if arg.startswith('$'):
        varname = arg[1:]
        args.extend(map(str, template_vars[varname]))
      else:
        args.append(arg)
    return CommandAction(args)

  # Task
  def get_actions(self):
    executable = self.executable.get()
    inputs = self.inputs.get()
    outputs = self.outputs.get()
    actions: t.List[Action] = [CreateDirectoryAction(d) for d in set(p.parent for p in outputs)]
    additional_vars: t.Dict[str, t.List[str]] = self.additional_vars.or_else({})
    if self.batch.or_else(True):
      if len(inputs) != len(outputs):
        raise ValueError('inputs must be same length as outputs')
      for key, value in additional_vars.items():
        if len(value) != len(inputs):
          raise ValueError(f'additional_vars[{key!r}] must have same length as inputs')
      for index, (infile, outfile) in enumerate(zip(inputs, outputs)):
        template_vars = {k: [v[index]] for k, v in additional_vars.items()}
        template_vars['in'] = [str(infile)]
        template_vars['out'] = [str(outfile)]
        actions.append(self._render_command(executable, template_vars))
    else:
      template_vars = {k: v for k, v in additional_vars.items()}
      template_vars['in'] = list(map(str, inputs))
      template_vars['out'] = list(map(str, outputs))
      actions.append(self._render_command(executable, template_vars))
    return actions


def apply(project: Project, namespace: Namespace) -> None:
  namespace.add('ProcessorTask', ProcessorTask)
  namespace.add_task_factory('processor', ProcessorTask)
