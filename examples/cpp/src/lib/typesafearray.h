
#include <stdlib.h>

void* typesafearray_new(size_t const element_size, size_t const length);

void* typesafearray_resize(void* const array, size_t const new_length);

size_t typesafearray_length(void* const array);

void typesafearray_delete(void* const array);
