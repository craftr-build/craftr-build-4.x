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

Known issues:

- Currently only tested and supported on **Windows**

Example:

```python
cxx = load_module('craftr.lang.cxx')
qt5 = load_module('craftr.lib.qt5')

app = cxx.binary(
  inputs = cxx.cpp_compile(
    sources = glob(['src/**/*.cpp']),
    frameworks = [qt5.framework('Qt5Widgets', 'Qt5Gui')]
  ),
  output = 'myqtapp'
)
```

```cpp
#include <QtWidgets/QApplication>
#include <QtWidgets/QWidget>

#ifdef CRAFTRQT5_STATIC
  #include <QtCore/QtPlugin>
  Q_IMPORT_PLUGIN (QWindowsIntegrationPlugin);
#endif

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  QWidget wnd;
  wnd.show();
  return app.exec();
}
```
