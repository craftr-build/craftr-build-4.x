This file documents some features of Craftr that should not be left
undocumented.

Goto:

- [Package documentation](package.md)
- [Built-ins documentation](builtins.md)
- [Config documentation](config.md)
- [Transition from Craftr 1](transition.md)
- [Writing Target generators](generators.md)


# FAQ

## How to use an alternative Ninja command?

You can set the `craftr.ninja` option or use the `NINJA` environment variable.

    $ craftr -d craftr.ninja=ninja-1.7.2 build

## Is there a way to create a Python function that is called from Ninja?

Currently not. Craftr 1 used to have this feature called *RTS*. Including
this feature into Craftr 2 is definitely on the plan.

## How can I include a configuration file from another configuration file?

You can use the `[include "path/to/config" if-exists]` section directive. Note
that the `if-exists` part is optional.

## How can I set a global option in a configuration file?

You can add the options under the `[__global__]` section.
