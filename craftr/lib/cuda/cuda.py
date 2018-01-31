
import craftr


class CudaTargetHandler(craftr.TargetHandler):

  def setup_target(self, target):
    target.define_property('cuda.srcs', 'StringList')


module.register_handler(CudaTargetHandler())
