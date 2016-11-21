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
#include <curlpp/cURLpp.hpp>
#include <curlpp/Easy.hpp>
#include <curlpp/Options.hpp>
#include <tinyxml2.h>

void DumpXML(tinyxml2::XMLNode* node) {
  auto* elem = node->ToElement();
  if (elem) {
    std::cout << elem->Name() << std::endl;
  }
  for (auto* child = node->FirstChild(); child; child = child->NextSibling()) {
    DumpXML(child);
  }
}

int main() {
  std::ostringstream data;
  try {
    curlpp::Cleanup cleanup;
    curlpp::Easy request;
    request.setOpt<curlpp::options::WriteStream>(&data);
    request.setOpt<curlpp::options::Url>("http://www.w3schools.com/xml/note.xml");
    request.perform();
  }
  catch (std::exception& e) {
    std::cerr << e.what() << std::endl;
    return 1;
  }

  tinyxml2::XMLDocument doc;
  tinyxml2::XMLError error = doc.Parse(data.str().c_str());
  if (error != tinyxml2::XML_SUCCESS) {
    std::cerr << "tinyxml2 error: " << error << std::endl;
    return 1;
  }

  DumpXML(doc.RootElement());
  return 0;
}
