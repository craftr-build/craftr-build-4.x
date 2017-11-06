"""
Actions are generated from build targets and represent concrete
implementations of tasks on a more detailed level.
"""

import errno
import io
import locale
import os
import subprocess
import sumtypes
import sys
import traceback
import _target from './target'
import env from '../utils/env'
import sh from '../utils/sh'
import ts from '../utils/ts'


@sumtypes.sumtype
class HashComponent:
  Data = sumtypes.constructor('bytes')
  File = sumtypes.constructor('path')


class Action:

  def __init__(self, target, name, deps, data):
    if not isinstance(target, _target.Target):
      raise TypeError('target must be Target instance')
    if any(not isinstance(x, Action) for x in deps):
      raise TypeError('deps must be a list of Action instances')
    if not isinstance(data, ActionData):
      raise TypeError('data must be an ActionData instance')
    self.target = target
    self.name = name
    self.deps = deps
    self.data = data
    self.progress = None
    self.skipped = False
    data.mounted(self)

  def __repr__(self):
    return '<Action {!r}>'.format(self.long_name)

  @property
  def long_name(self):
    return '{}#{}'.format(self.target.long_name, self.name)

  def check_skip(self):
    """
    Checks if the action can be skipped.
    """

    if self.skipped:
      return True
    if self.progress is not None:
      return False
    if self.data.check_skip(self):
      self.skipped = True
      return True
    return False

  def get_display(self):
    return self.data.get_display(self)

  def is_executed(self):
    if self.skipped:
      return True
    if self.progress is None:
      return False
    with ts.condition(self.progress):
      return self.progress.executed

  def execute(self):
    """
    Exeuctes the action. #Action.progress must be set before this method is
    called. Returns the #ActionProgress.code. Catches any exceptions and
    prints them to the #ActionProgress.buffer.
    """

    for other in self.deps:
      if not other.is_executed():
        raise RuntimeError('"{}" -> "{}" (dependent action not executed)'
          .format(self.long_name, other.long_name))

    if self.progress is None:
      raise RuntimeError('{!r}.progress must be set before execute()'.format(self))
    if self.progress.executed:
      raise RuntimeError('{!r} already executed'.format(self))
    progress = self.progress
    progress.executed = True
    try:
      code = self.data.execute(self, progress)
    except SystemExit as exc:
      code = exc.code
    except BaseException as exc:
      progress.print(traceback.format_exc())
      code = 127
    else:
      if code is None:
        code = 0
    with ts.condition(progress):
      progress.code = code
      progress.executed = True
      progress.update(1.0)
      ts.notify(progress)
    return code

  def execute_with(self, progress):
    if self.progress is not None:
      raise RuntimeError('{!r}.progress is already set'.format(self))
    self.progress = progress
    return self.execute()


class ActionData:

  @classmethod
  def new(cls, target, *, name=None, deps=(), **kwargs):
    """
    Creates a new #Action and adds it to *target*.
    """

    def leaves():
      result = set()
      for dep in target.private_deps:
        result |= dep.leaf_actions()
      for dep in target.transitive_deps:
        result |= dep.leaf_actions()
      return result

    if deps == '...':
      deps = list(leaves())
    else:
      deps = list(deps)
      try:
        index = deps.index('...')
      except ValueError:
        pass
      else:
        deps[index:index+1] = list(leaves())

    data = cls(**kwargs)
    action = Action(target, name, deps, data)
    target.add_action(action)
    return action

  def __str__(self):
    attrs = []
    for key in dir(self):
      if key.startswith('_') or hasattr(type(self), key): continue
      value = getattr(self, key)
      attrs.append('{}={!r}'.format(key, value))
    return '{}({})'.format(type(self).__name__, ', '.join(attrs))

  def check_skip(self, action):
    """
    Check if the action can be skipped.
    """

    return False

  def mounted(self, action):
    """
    Called when the #ActionData is passed to the #Action constructor.
    """

    self.action = action

  def execute(self, action, progress):
    """
    Perform the action's task. Prints should be redirected to *progress*
    which is an #ActionProgress instance. The return-value must be 0 or
    #None to indicate success, any other value is considered as the action
    failed.
    """

    raise NotImplementedError

  def get_display(self, action):
    """
    Return a displayable string. This is usually used the first time the
    action is executed. If the #execute() calls #ActionProgress.progress()
    with the *message* parameter, that message is usually displayed then.
    """

    return str(self)

  def hash_components(self, action):
    """
    Yield #HashComponent values that are to be computed into the action's
    hash key. This should include any relevant data that can influence the
    outcome of the action's execution.
    """

    raise NotImplementedError


class ActionProgress(ts.object):
  """
  An instance of this class is passed to #ActionData.execute() in order to
  allow the #ActionData to report the progress of the execution.
  """

  def __init__(self, encoding=None, do_buffering=True):
    self.executed = False
    self.encoding = encoding or locale.getpreferredencoding()
    self.buffer = io.BytesIO()
    self.do_buffering = do_buffering
    self.code = None

  def buffer_has_content(self):
    return self.buffer.tell() != 0

  def print_buffer(self):
    sys.stdout.buffer.write(self.buffer.getvalue())

  def update(self, percent=None, message=None):
    """
    Called from #ActionData.execute() to update progress information. If
    *percent* is #None, the action is unable to estimate the current progress.
    The default implementation does nothing.

    This method will be called from #Action.execute() after the action has
    finished executing. The #ActionProgress.code is available at that time,
    so the call may check if the execution was successful or not for reporting
    purposes.
    """

    pass

  def print(self, *objects, sep=' ', end='\n'):
    """
    Prints to the #ActionData.buffer.
    """

    if self.do_buffering:
      message = (sep.join(map(str, objects)) + end).encode(self.encoding)
      with ts.condition(self):
        self.buffer.write(message)
    else:
      print(*objects, sep=sep, end=end)

  def system(self, argv, cwd=None, environ=None):
    """
    Creates a new subprocess and executes it in a blocking fashion. If
    #ActionProgress.do_buffering is enabled, pipes will be created for the
    process and the data is copied into the #ActionProgress.buffer.

    Note that this method is only thread-safe when *environ* is #None or
    other threads do not modify #os.environ unless the #env.lock is used
    to synchronized access to the dictionary or they use the #env functions.

    Note that this function will constantly acquire the synchronized
    state of the #ActionProgress object if #do_buffering is enabled, until
    the process is finished.
    """

    if isinstance(argv, str):
      raise TypeError('argv must be a list of arguments, not a string')
    if any(not isinstance(x, str) for x in argv):
      raise TypeError('argv[] must be only strings')

    if self.do_buffering:
      stdin = stdout = subprocess.PIPE
      stderr = subprocess.STDOUT
    else:
      stdin = stdout = stderr = None

    with env.override(environ or {}):
      proc = subprocess.Popen(argv, cwd=cwd, stdin=stdin,
        stdout=stdout, stderr=stderr, universal_newlines=False)

    if self.do_buffering:
      proc.stdin.close()
      with ts.condition(self):
        for line in proc.stdout:
          self.buffer.write(line)

    proc.wait()
    return proc.returncode


class Null(ActionData):
  """
  This action implementation simply does nothing. :^) It's important that
  targets that do not actually perform any actions still generate at least
  a single action to properly include them in the build process.

  #Target.translate() will automatically create a Null action if no actions
  have been generated during it's #TargetData.translate() method.
  """

  def check_skip(self, action):
    return True

  def execute(self, action, progress):
    return 0


class Mkdir(ActionData):
  """
  An action that ensures that a directory exists.
  """

  def __init__(self, directory):
    self.directory = directory

  def get_display(self, action):
    return 'mkdir ' + sh.quote(self.directory)

  def execute(self, action, progress):
    try:
      os.makedirs(self.directory, exist_ok=True)
    except OSError as e:
      progress.print(e)
      return e.errno
    else:
      return 0


class System(ActionData):
  """
  This action implements executing one or more system commands, usually with
  the purpose of translating a set of input files to output files. The list
  of input and output files is not required by the default build backend, but
  other backends might require it to establish correct relationships between
  actions.
  """

  def __init__(self, commands, input_files=(), output_files=(),
               environ=None, cwd=None):
    self.commands = commands
    self.input_files = list(input_files)
    self.output_files = list(output_files)
    self.environ = environ
    self.cwd = cwd

  def get_display(self, action):
    commands = (' '.join(sh.quote(x) for x in cmd) for cmd in self.commands)
    return '$ ' + ' && '.join(commands)

  def execute(self, action, progress):
    code = 0
    for command in self.commands:
      code = progress.system(command, cwd=self.cwd, environ=self.environ)
      if code != 0:
        break
    return code
