"""
Provides the base class for build backends.
"""

class BuildBackend:

  def init_backend(self, session):
    """
    Called after the backend has been created.
    """

  def get_action_hash(self, session, action_long_name):
    """
    This method is used to retrieve the hash of the action identified by
    *action_long_name*. If there is no hash for the action, #None is returned.
    The hash will be used to determine if any of the action's inputs have
    changed (eg. input files, command-line, etc.).
    """

    raise NotImplementedError

  def build_parser(self, session, parser):
    """
    Extend the #argparse.ArgumentParser of the Craftr command-line. Once the
    parser has been extended, the arguments will be re-parsed to identify the
    rest of the command-line, besides the standard minimal argument set.
    """

    raise NotImplementedError

  def run(self, session, module, args):
    """
    Run the build backend.
    """

    raise NotImplementedError
