
class BuildBackend:

  def __init__(self, context, args):
    self.context = context
    self.args = args

  def export(self):
    raise NotImplementedError

  def clean(self, recursive):
    raise NotImplementedError

  def build(self):
    raise NotImplementedError
