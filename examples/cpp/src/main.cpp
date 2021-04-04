
#include <iostream>

extern "C" {
#include <cstring>
#include <array.h>
#include <typesafearray.h>
}

int main() {
  std::cout << "\n\narray example\n\n";

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

  std::cout << "\n\ntypesafearray example\n\n";
  int* numbers = (int*) typesafearray_new(sizeof(int), 2);
  std::cout << typesafearray_length(numbers) << "\n";
  numbers[0] = 42;
  numbers[1] = 90;
  numbers = (int*) typesafearray_resize(numbers, 3);
  std::cout << typesafearray_length(numbers) << "\n";
  typesafearray_delete(numbers);
}
