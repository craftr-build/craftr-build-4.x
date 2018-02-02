
import craftr
from craftr import path

if OS.name == 'nt':
  exe_suffix = '.exe'
else:
  exe_suffix = ''


class OcamlTargetHandler(craftr.TargetHandler):

  def get_common_property_scope(self):
    return 'ocaml'

  def setup_target(self, target):
    target.define_property('ocaml.srcs', 'StringList', inheritable=False)
    target.define_property('ocaml.standalone', 'Bool')
    target.define_property('ocaml.productName', 'String')
    target.define_property('ocaml.compilerFlags', 'StringList')

  def finalize_target(self, target, data):
    src_dir = target.directory()
    build_dir = path.join(context.build_directory, target.module().name())
    if not data.productName:
      data.productName = target.name() + '-' + target.module().version()
    if data.srcs:
      data.srcs = [path.canonical(x, src_dir) for x in data.srcs]
      data.productFilename = path.join(build_dir, data.productName)
      if data.standalone:
        data.productFilename += exe_suffix
      else:
        data.productFilename += '.cma'
      target.outputs().add(data.productFilename, ['exe'])

  def translate_target(self, target, data):
    if data.srcs:
      # Action to compile an executable.
      command = ['ocamlopt' if data.standalone else 'ocamlc']
      command += ['-o', '$out', '$in']
      action = target.add_action('ocaml.compile', commands=[command])
      build = action.add_buildset()
      build.files.add(data.srcs, ['in'])
      build.files.add(data.productFilename, ['out'])

      # Action to run the executable.
      command = [data.productFilename]
      action = target.add_action('ocaml.run', commands=[command],
        explicit=True, syncio=True, output=False)
      action.add_buildset()


module.register_target_handler(OcamlTargetHandler())
