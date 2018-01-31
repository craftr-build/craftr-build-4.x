
import craftr


class JavaTargetHandler(craftr.TargetHandler):

  def setup_target(self, target):
    target.define_property('java.srcs', 'StringList')
    target.define_property('java.srcRoots', 'StringList')
    target.define_property('java.classDir', 'String')
    target.define_property('java.compilerFlags', 'StringList')
    target.define_property('java.jarName', 'String')
    target.define_property('java.mainClass', 'String')
    target.define_property('java.distType', 'String')  # The distribution type for applications, can be `none`, `onejar` or `merge`.
    target.define_property('java.binaryJars', 'StringList')
    target.define_property('java.artifacts', 'StringList')

  def setup_dependency(self, target):
    # Whether to embedd the library when combining JARs. Defaults
    # to True for applicaton JARs, False to library JARs.
    target.define_property('java.embed', 'Bool')


module.register_target_handler(JavaTargetHandler())
