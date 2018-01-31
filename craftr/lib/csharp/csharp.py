
import craftr


class CsharpTargetHandler(craftr.TargetHandler):

  def setup_target(self, target):
    target.define_property('csharp.srcs', 'StringList')
    target.define_property('csharp.type', 'String')  # appcontainer, exe, library, module, winexe, winmdobj
    target.define_property('csharp.main', 'String')
    target.define_property('csharp.compilerFlags', 'StringList')
    target.define_property('csharp.dynamicLibraries', 'StringList')
    target.define_property('csharp.packages', 'StringList')
    target.define_property('csharp.mergeAssemblies', 'Bool', True)  # Allows you to disable the merging of assemblies for this target.

  def setup_dependency(self, target):
    # Whether to embedd the library when merging assemblies. Defaults
    # to True for applicaton assemblies, False otherwise.
    target.define_property('csharp.embed', 'Bool')


module.register_target_handler(CsharpTargetHandler())
