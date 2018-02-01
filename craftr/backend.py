
class BuildBackend:

  def __init__(self, context, module, args):
    self.context = context
    self.module = module
    self.args = args

  def export(self):
    raise NotImplementedError

  def clean(self):
    raise NotImplementedError

  def build(self):
    raise NotImplementedError
