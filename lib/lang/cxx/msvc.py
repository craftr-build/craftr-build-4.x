
import string
import craftr from 'craftr'
import cxx from '.'
import {log, macro, path} from 'craftr/utils'
import _msvc from 'craftr/lang/msvc'
import _base from './base'


class MsvcCompiler(_base.Compiler):

  def __init__(self, toolkit=None):
    self.toolkit = toolkit or _msvc.MsvcToolkit.from_config()

  def init_macro_context(self, target, ctx):
    data = target.data
    if data.type == 'binary':
      ctx.define('ext', '.exe')
    elif data.preferred_linkage == 'static':
      ctx.define('ext', '.lib')
    elif data.preferred_linkage == 'shared':
      ctx.define('ext', '.dll')
    else: assert False, (data.type, data.preferred_linkage)

  def create_session(self):
    return MsvcCompilerSession(self)


class MsvcCompilerSession(_base.CompilerSession):

  def __init__(self, compiler):
    super().__init__(compiler)
    self.objs = []
    self.obj_actions = []

  def compile_c(self, srcs):
    # XXX Source files in different folders could have the same basename!
    for src in srcs:
      obj_file = path.join(self.obj_dir, path.rmvsuffix(path.base(src)) + '.obj')
      command = ['cl', src, '/Fo' + obj_file, '/nologo', '/c']
      action = craftr.actions.System.new(
        self.target,
        name = path.base(src),
        deps = [self.obj_dir_action, ...],
        commands = [command],
        input_files = [src],
        output_files = [obj_file],
        environ = self.compiler.toolkit.environ
      )
      self.objs.append(obj_file)
      self.obj_actions.append(action)

  def link(self, outfile):
    libs = []
    for data in self.target.deps().attr('data'):
      if isinstance(data, cxx.CxxBuild) and data.type == 'library':
        assert data.outname_full, data.target
        libs.append(data.outname_full)
      elif isinstance(data, cxx.CxxPrebuilt):
        # XXX
        pass

    if self.data.type == 'library' and self.data.preferred_linkage == 'static':
      command = [self.compiler.toolkit.cl_info.lib_program, '/OUT:' + outfile] + self.objs + libs
    else:
      command = [self.compiler.toolkit.cl_info.link_program, '/OUT:' + outfile] + self.objs + libs
      if self.data.preferred_linkage == 'shared':
        command += ['/dynamic']  # XXX
    command += ['/nologo']
    craftr.actions.System.new(
      self.target,
      name = 'link',
      deps = self.obj_actions,
      commands = [command],
      input_files = self.objs,
      output_files = [outfile],
      environ = self.compiler.toolkit.environ
    )


def get_compiler(fragment):
  if fragment:
    log.warn('craftr/lang/cxx/msvc: Fragment not supported. (fragment = {!r})'
      .format(fragment))
  return MsvcCompiler()
