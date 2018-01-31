
import craftr


class ValaTargetHandler(craftr.TargetHandler):

  def setup_target(self, target):
    target.define_property('vala.srcs', 'StringList')


module.register_target_handler(ValaTargetHandler())
