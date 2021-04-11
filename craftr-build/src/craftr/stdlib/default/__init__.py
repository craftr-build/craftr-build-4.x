
"""
Provides the extensions that are always available in a project.
"""

from craftr.core.project import Project

from .run import RunTask


def apply(project: Project) -> None:
  project.add_task_extension('run', RunTask)
