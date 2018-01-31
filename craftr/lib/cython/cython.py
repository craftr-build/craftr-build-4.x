
import craftr


class CythonTargetHandler(craftr.TargetHandler):

  def setup_target(self, target):
    target.define_property('cython.srcs', 'StringList')
    target.define_property('cython.mainSrcs', 'StringList')
    target.define_property('cython.pythonVersion', 'Int')
    target.define_property('cython.useCpp', 'Bool')
    target.define_property('cython.fastFail', 'Bool')
    target.define_property('cython.includes', 'StringList')
    target.define_property('cython.cythonFlags', 'StringList')


module.register_target_handler(CythonTargetHandler())
