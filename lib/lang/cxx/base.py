
import craftr from 'craftr'
import {macro} from 'craftr/utils'


class Compiler:
  """
  Base class that implements the behaviour of the Cxx targets.
  """

  def get_output_filename(self, target):
    """
    This method is supposed to render the `target.outname` macro string
    with the appropriate substitutions for the standard `$(lib)`, `$(name)`
    and `$(ext)` macros. A safe-subsitution is supposed to be performed,
    ridding all macros that are not defined from the string.
    """

    ctx = macro.Context()
    ctx.define('name', target.name)
    self.init_macro_context(target, ctx)
    return macro.parse(target.data.outname).eval(ctx)

  def init_macro_context(self, target, ctx):
    raise NotImplementedError

  def create_session(self):
    """
    Create a new #CompilerSession instance.
    """

    raise NotImplementedError


class CompilerSession:

  def __init__(self, compiler):
    self.compiler = compiler

  def init_session(self, target, obj_dir):
    self.target = target
    self.obj_dir = obj_dir
    self.obj_dir_action = craftr.actions.Mkdir.new(target, directory=obj_dir)

  @property
  def data(self):
    return self.target.data

  def compile_c(self, srcs):
    raise NotImplementedError

  def compile_cpp(self, srcs):
    raise NotImplementedError

  def link(self, outfile):
    raise NotImplementedError
