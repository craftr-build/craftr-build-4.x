# FAQ

### How to use an alternative Ninja command?

You can set the `craftr.ninja` option or use the `NINJA` environment variable.

    $ craftr -d craftr.ninja=ninja-1.7.2 build

### Is there a way to create a Python function that is called from Ninja?

See the Documentation about [Tasks](ref/tasks).

### How can I include a configuration file from another configuration file?

You can use the `[include "path/to/config" if-exists]` section directive. Note
that the `if-exists` part is optional.

### How can I set a global option in a configuration file?

You can add the options under the `[__global__]` section.
