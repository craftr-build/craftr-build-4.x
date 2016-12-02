/**
 * Copyright (C) 2016  Niklas Rosenstein
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
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */


#include <iostream>
#include <sstream>
#include <tinyxml2.h>

#if __CYGWIN__
  // Missing include from curl/multi.h on Cygwin.
  #include <sys/select.h>
#endif
#include <curlpp/cURLpp.hpp>
#include <curlpp/Easy.hpp>
#include <curlpp/Options.hpp>

#if !defined(DLIB_ISO_CPP_ONLY) && !defined(DLIB_NO_GUI_SUPPORT)
  #include <dlib/gui_core.h>
  #include <dlib/gui_widgets.h>
  #define HAVE_DLIB_GUI
#endif
#include <dlib/config_reader.h>

#ifdef HAVE_QT5
  #include <QtWidgets/QMainWindow>
  #include <QtWidgets/QApplication>
  #include <QtWidgets/QLabel>
  #include <QtWidgets/QBoxLayout>
#endif // HAVE_QT5


std::string read_url(std::string const& fn) {
  try {
    dlib::config_reader cfg(fn);
    return cfg.block("example")["url"];
  }
  catch (std::exception& e) {
    std::cerr << "error: could not read config file: " << e.what() << std::endl;
    return "";
  }
}


void dump_xml(std::ostream& out, tinyxml2::XMLNode* node) {
  auto* elem = node->ToElement();
  if (elem) {
    out << "  " << elem->Name() << std::endl;
  }
  for (auto* child = node->FirstChild(); child; child = child->NextSibling()) {
    dump_xml(out, child);
  }
}


int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: main <config-file>" << std::endl;
    return 1;
  }

  std::string url = read_url(argv[1]);
  if (!url.size()) {
    std::cerr << "error: none or empty url" << std::endl;
    return 1;
  }

  std::cout << "retrieving XML from \"" << url << "\" ..." << std::endl;
  std::ostringstream data;
  try {
    curlpp::Cleanup cleanup;
    curlpp::Easy request;
    request.setOpt<curlpp::options::WriteStream>(&data);
    request.setOpt<curlpp::options::Url>(url);
    request.perform();
  }
  catch (std::exception& e) {
    std::cerr << e.what() << std::endl;
    return 1;
  }

  std::cout << "parsing XML document ..." << std::endl << std::endl;
  tinyxml2::XMLDocument doc;
  tinyxml2::XMLError error = doc.Parse(data.str().c_str());
  if (error != tinyxml2::XML_SUCCESS) {
    std::cerr << "tinyxml2 error: " << error << std::endl;
    return 1;
  }

  data << "\n\nTags:\n\n";
  dump_xml(data, doc.RootElement());

  #if defined(HAVE_QT5)
  {
    QApplication app(argc, argv);
    QWidget window;

    QHBoxLayout layout(&window);
    window.setLayout(&layout);

    QLabel label(data.str().c_str());
    layout.addWidget(&label);

    window.show();
    return app.exec();
  }
  #elif defined(HAVE_DLIB_GUI)
  {
    class window : public dlib::drawable_window {
    public:
      window() { show(); }
      ~window() { close_window(); }
    };
    window win;
    win.set_size(400, 300);
    win.set_title("dlib window");
    dlib::label label(win);
    label.set_text(data.str());
    win.wait_until_closed();
    return 0;
  }
  #else
  {
    std::cerr << "note: no GUI available (could be Qt5/dlib)" << std::endl;
    std::cout << data.str() << std::endl;
    return 0;
  }
  #endif
}
