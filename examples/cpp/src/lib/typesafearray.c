
#include "typesafearray.h"

struct header {
  size_t element_size;
  size_t length;
};

void* typesafearray_new(size_t const element_size, size_t const length) {
  void* ptr = malloc(sizeof(struct header) + element_size * length);
  if (ptr == NULL) {
    return NULL;
  }
  struct header* header = ptr;
  header->element_size = element_size;
  header->length = length;
  return ptr + sizeof(struct header);
}

void* typesafearray_resize(void* const array, size_t const new_length) {
  if (array == NULL) {
    return NULL;
  }
  struct header* header = array - sizeof(struct header);
  void* ptr = realloc(header, sizeof(struct header) + header->element_size * new_length);
  if (ptr == NULL) {
    return NULL;
  }
  header = ptr;
  header->length = new_length;
  return ptr + sizeof(struct header);
}

size_t typesafearray_length(void* const array) {
  if (array == NULL) {
    return 0;
  }
  return ((struct header*)(array - sizeof(struct header)))->length;
}

void typesafearray_delete(void* const array) {
  if (array != NULL) {
    free(array - sizeof(struct header));
  }
}
