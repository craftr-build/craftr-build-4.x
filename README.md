<p align="center"><img src=".assets/craftr-logo.png"></p>
<h1 align="center">Craftr</h1>
<p align="center">
  An extensible language-independent build system written in Python.
</p>

*Version 3.0.0-dev*

## Installation

Craftr is built with Python, but not exactly standard Python. You will need
to install [Node.py 2](https://nodepy.org/) or higher beforehand. Craftr is
installed on a per-project basis so you always have the same build system
version.

> Note that currently Craftr 3 is in development and there are no tags for
> it, yet. Thus, installing from the `develop` branch will obviously not
> always give you the same version.

    $ pip install --user nodepy-runtime
    $ nodepy-pm install git+https://github.com/craftr-build/craftr@develop

If you want to keep track of Craftr as a dependency, or may want to install
additional packages that can work with Craftr, you should add a `nodepy.json`
package manifest. It is relatively similar to Node.js package manifests.

```json
{
  "name": "myproject",
  "version": "1.0.0",
  "dependencies": {
    "craftr-build": "git+https://github.com/craftr-build/craftr@develop"
  }
}
```

## Build scripts

Craftr build scripts are called `Craftrfile.py` and Craftr runs them to create
the target build graph. Craftr currently has built-in support for building
projects of the following programming languages (to be extended in the future):

* C# *(low-grade)*
* Java *(middle-grade)*

Example Java build script:

```python
import craftr from 'craftr'
import java from 'craftr/lang/java'

# Downloads Guava 23.4 from Maven Central.
java.prebuilt(name = 'guava', artifact = 'com.google.guava:guava:23.4-jre')

java.binary(
  name = 'main',
  deps = [':guava'],
  srcs = craftr.glob('src/**.java'),
  main_class = 'Main'
)

java.run(':main')
```

This will use [OneJar](http://one-jar.sourceforge.net/) to include all
dependencies in the output Jar. You can invoke the `run()` target by
specifiying the `:main_run` on the command-line. Additional arguments
can be specified using an `=` character.

    $ craftr -bbuild :main_run="arg1 arg2 'argument number 3'"

## Todolist

* The default build backend sometimes runs into a deadlock when interrupting
  the build process with CTRL+C
* Trigger rebuild if the input variables (eg. system command that is being
  executed) changed since the last time the action was executed
