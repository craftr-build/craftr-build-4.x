
#include "argument_parser.hpp"
#include <cstdint>
#include <iostream>
#include <string>

extern "C" unsigned char BUILDSCRIPT[];
extern "C" std::size_t BUILDSCRIPT_size;

int main(int argc, char** argv) {
  argument_parser parser("craftr-examples-cxx");
  parser.add_option("", "help", 0);
  parser.add_option("", "hex");
  try {
    parser(argc-1, argv+1);
  }
  catch (argument_parser::parse_error& exc) {
    std::cout << "error: " << exc.what() << "\n";
    return 1;
  }

  if (parser.has("hex")) {
    long value = std::stol(parser["hex"][0]);
    std::cout << std::hex << value << std::endl;
    return 0;
  }

  std::cout << "Build Script used to compile this program:\n\n";
  std::cout << std::string((char*)BUILDSCRIPT, BUILDSCRIPT_size) << std::endl;
  return 0;
}
