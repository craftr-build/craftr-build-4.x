
import craftr


class ThriftTargetHandler(craftr.TargetHandler):

  def setup_target(self, target):
    target.define_property('thrift.srcs', 'StringList')
    target.define_property('thrift.strict', 'Bool')
    target.define_property('thrift.gen', 'StringList')


module.register_target_handler(ThriftTargetHandler())
