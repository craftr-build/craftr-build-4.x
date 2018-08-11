
#include <stdio.h>
#include <Windows.h>
#include "resource.h"
#pragma comment(lib, "user32.lib")

int main() {
  char buffer[512];
  LoadString(NULL, IDS_HELLO, buffer, 512);
  printf("%s\n", buffer);
  return 0;
}
