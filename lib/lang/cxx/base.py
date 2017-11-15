
class BaseCompiler:
  """
  Base class for the compiler that implements the translation of the Cxx
  targets.
  """

  def translate(self, target):
    """
    Translates the #CxxBuild target *target*.
    """

    raise NotImplementedError
