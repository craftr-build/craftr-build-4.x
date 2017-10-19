"""
Actions are generated from build targets and represent concrete
implementations of tasks on a more detailed level.
"""

import io
import locale
import sumtypes
import _target from './target'
import ts from './utils/ts'


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
    data.mounted(self)

  def __repr__(self):
    return '<Action {!r}>'.format(self.long_name)

  @property
  def long_name(self):
    return '{}#{}'.format(self.name)

  def execute(self):
    """
    Exeuctes the action. #Action.progress must be set before this method is
    called. Returns the #ActionProgress.code. Catches any exceptions and
    prints them to the #ActionProgress.buffer.
    """

    if self.progress is None:
      raise RuntimeError('Action.progress must be set before executing')
    if self.progress.executed:
      raise RuntimeError('Action already executed.')
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
      progress.notify()
    return code


class ActionData:

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

  def __init__(self, encoding=None):
    self.executed = False
    self.encoding = encoding or locale.getpreferredencoding()
    self.buffer = io.BytesIO()
    self.code = None

  def update(self, percent=None, message=None):
    """
    Called from #ActionData.execute() to update progress information. If
    *percent* is #None, the action is unable to estimate the current progress.
    The default implementation does nothing.
    """

    pass

  def print(self, *objects, sep=' ', end='\n'):
    """
    Prints to the #ActionData.buffer.
    """

    message = (sep.join(map(str, objects)) + end).encode(self.encoding)
    with ts.condition(self):
      self.buffer.write(message)
