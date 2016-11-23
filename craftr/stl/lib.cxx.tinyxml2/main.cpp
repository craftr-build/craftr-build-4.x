
#include <iostream>
#include <tinyxml2.h>

int main() {
  tinyxml2::XMLPrinter printer(stdout);
  printer.OpenElement("foo");
  printer.PushAttribute("spam", "bar");
  printer.CloseElement();
  return 0;
}
