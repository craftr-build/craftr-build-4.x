# Qt5 (`craftr.lib.qt5`)

Configuration:

- `.dir` &ndash; Directory of the prebuilt binaries with the standard Qt5
  folder structure.
- `.link_style` &ndash; Link-style of the Qt5 prebuilt binaries. The default
  value of this option is `detect`, other available options are `static` and
  `dynamic`.

```ini
[craftr.lib.qt5]
  link_style = detect
  dir = D:\lib\qt5-5.7.0-vs2015\qt5-x64-static-release
```

Features:

- Automatic detection of Qt5 prebuilt binaries link-style.
- Adds `CRAFTRQT5_STATIC` or `CRAFTRQT5_DYNAMIC` preprocessor macro respectively

Todolist:

- Support and test platforms other than **Windows**
- Update `PATH` for testing with dynamically linked Qt5 binaries when using
  `runtarget()`
- Ability to gather a list of all dynamic dependencies

Example:

```python
cxx = load_module('craftr.lang.cxx')
qt5 = load_module('craftr.lib.qt5')

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
