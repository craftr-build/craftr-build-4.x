
import craftr
from nr import path

if OS.type == 'nt':
  exe_suffix = '.exe'
else:
  exe_suffix = ''


class ValaTargetHandler(craftr.TargetHandler):

  def init(self, context):
    props = context.target_properties
    props.add('vala.srcs', craftr.StringList)
    props.add('vala.productName', craftr.String)
    props.add('vala.compilerFlags', craftr.StringList)
    props.add('vala.linkerFlags', craftr.StringList)

  def translate_target(self, target):
    src_dir = target.directory
    build_dir = path.join(context.build_directory, target.module.name)
    data = target.get_props('vala.', as_object=True)
    data.compilerFlags = target.get_prop_join('vala.compilerFlags')
    data.linkerFlags = target.get_prop_join('vala.linkerFlags')

    if not data.productName:
      data.productName = target.name() + '-' + target.module.version
    if data.srcs:
      data.srcs = [path.canonical(x, src_dir) for x in data.srcs]
      data.productFilename = path.join(build_dir, data.productName + exe_suffix)

    if data.srcs:
      command = ['valac', '-o', '$out', '$in']
      command += data.compilerFlags
      for flag in data.linkerFlags:
        command += ['-X', flag]
      action = target.add_action('vala.compile', commands=[command])
      build = action.add_buildset()
      build.files.add(data.srcs, ['in'])
      build.files.add(data.productFilename, ['out', 'exe'])

      command = [data.productFilename]
      action = target.add_action('vala.run', commands=[command],
        explicit=True, syncio=True, output=False)
      action.add_buildset()


context.register_handler(ValaTargetHandler())
