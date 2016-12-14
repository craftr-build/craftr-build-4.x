/* The Craftr build system
 * Copyright (C) <year>  <name of author>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>. */

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
