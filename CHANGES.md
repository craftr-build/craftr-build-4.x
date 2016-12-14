# Craftr Changelog

__v2.0.0.dev6__:

- `Target` objects can now be passed to the `frameworks = [...]` argument
  of target generators that use the `TargetBuilder` class. These input targets
  will automatically added to the implicit dependencies and their frameworks
  be added
- `Tool` objects can now be passed into the `commands = [[...]]` argument
  of targets generators
