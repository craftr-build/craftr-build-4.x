# Qt5 (`craftr.lib.qt5`)

Static prebuilt binaries of Qt5 for Windows can be found [here](http://www.npcglib.org/~stathis/blog/precompiled-qt4-qt5/).

__Configuration__:

- `.dir` &ndash; Directory of the prebuilt binaries with the standard Qt5
  folder structure.
- `.link_style` &ndash; Link-style of the Qt5 prebuilt binaries. The default
  value of this option is `detect`, other available options are `static` and
  `dynamic`.
- `.debug` &ndash; Set this option when linking against debug binaries. Also,
  keep in mind that almost all options in Craftr are inheritable from the
  global namespace, thus setting the global `debug` option to true will set
  this option to true as well unless there is an explicit override.

```ini
[__global__]
  debug = false
[craftr.lib.qt5]
  link_style = detect
  dir = D:\lib\qt5-5.7.0-vs2015\qt5-x64-static-release
```

__Features__:

- Automatic detection of Qt5 prebuilt binaries link-style.
- Adds `CRAFTRQT5_STATIC` or `CRAFTRQT5_DYNAMIC` preprocessor macro respectively

__Todolist__:

- Support and test platforms other than **Windows**
- Update `PATH` for testing with dynamically linked Qt5 binaries when using
  `runtarget()`
- Ability to gather a list of all dynamic dependencies

__Example__:

```python
cxx = load('craftr.lang.cxx')
qt5 = load('craftr.lib.qt5')

mocfiles = qt5.moc(sources = glob(['src/*.h']))
uifiles = qt5.uic(sources = glob(['ui/*.ui']))

app = cxx.binary(
  inputs = cxx.cpp_compile(
    sources = [mocfiles] + glob(['src/*.cpp']),
    frameworks = [uifiles, qt5.framework('Qt5Widgets', 'Qt5Gui')]
  ),
  output = 'installer'
)

run = runtarget(app, cwd = project_dir)
```

```cpp
#include <QtWidgets/QApplication>
#include <QtWidgets/QWidget>
#include "MainWindow.h"

#ifdef CRAFTRQT5_STATIC
  #include <QtCore/QtPlugin>
  Q_IMPORT_PLUGIN (QWindowsIntegrationPlugin);
#endif

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  MainWindow wnd;
  wnd.show();
  return app.exec();
}
```
