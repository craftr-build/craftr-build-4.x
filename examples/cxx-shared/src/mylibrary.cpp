
#include "mylibrary.hpp"
#include <iostream>

HelloSayer::HelloSayer(std::string const& name) : _name(name) {}

void HelloSayer::say_hello() {
  std::cout << "Hello, " << _name << "\n";
}
