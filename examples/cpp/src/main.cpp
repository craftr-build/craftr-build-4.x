
#include <iostream>

extern "C" {
#include <cstring>
#include <array.h>
}

int main() {
  array_t array;
  array_init(&array, 16, 2);
  array_dump_info(&array);

  int val1 = 42;
  array_push(&array, &val1, sizeof(int));

  const char* val2 = "Hello, World!";
  array_push(&array, val2, strlen(val2) + 1);

  float val3 = 3.14;
  array_push(&array, &val3, sizeof(float));

  std::cout << "1. " << *(int*)array_get(&array, 0) << "\n";
  std::cout << "2. " << (const char*)array_get(&array, 1) << "\n";
  std::cout << "3. " << *(float*)array_get(&array, 2) << "\n";

  array_dump_info(&array);
  array_destroy(&array);
}
