/* Copyright (c) 2016  Niklas Rosenstein
 * All rights reserved. */

#include <QtWidgets/QApplication>
#include "MainWindow.h"

#ifdef CRAFTRQT5_STATIC
  #include <QtCore/QtPlugin>
  Q_IMPORT_PLUGIN(QWindowsIntegrationPlugin);
#endif

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  MainWindow wnd;
  wnd.show();
  return app.exec();
}
