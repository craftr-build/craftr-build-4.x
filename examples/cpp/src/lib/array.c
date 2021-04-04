
#include <string.h>
#include <stdio.h>
#include "array.h"

#define max(a, b) \
  ({ __typeof__ (a) _a = (a); \
      __typeof__ (b) _b = (b); \
    _a > _b ? _a : _b; })

int array_init(array_t* const array, const size_t min_buffer_size, const size_t min_item_count) {
  if (array == NULL) {
    return ARRAY_ENULL;
  }
  array->buffer = min_buffer_size > 0 ? malloc(min_buffer_size) : NULL;
  array->offsets = (size_t*) (min_item_count > 0 ? malloc(sizeof(size_t) * min_item_count) : NULL);
  if ((min_buffer_size > 0 && array->buffer == NULL) || (min_item_count > 0 && array->offsets == NULL)) {
    free(array->buffer);
    free(array->offsets);
    return ARRAY_ENOMEM;
  }
  array->buffer_capacity = min_buffer_size;
  array->buffer_used = 0;
  array->offsets_capacity = min_item_count;
  array->offsets_used = 0;
  return 0;
}

int array_push(array_t* const array, const void* data, const size_t size) {
  if (array == NULL) {
    return ARRAY_ENULL;
  }
  if (array->buffer_used + size > array->buffer_capacity) {
    size_t new_buffer_size = max(array->buffer_capacity * 2, array->buffer_used + size);
    void* new_buffer = realloc(array->buffer, new_buffer_size);
    if (new_buffer == NULL) {
      return ARRAY_ENOMEM;
    }
    array->buffer = new_buffer;
    array->buffer_capacity = new_buffer_size;
  }
  if (array->offsets_used + 1 > array->offsets_capacity) {
    size_t new_offsets_count = max(array->offsets_used * 2, 4);
    size_t* new_offsets = (size_t*) realloc(array->offsets, sizeof(size_t) * new_offsets_count);
    if (new_offsets == NULL) {
      return ARRAY_ENOMEM;
    }
    array->offsets = new_offsets;
    array->offsets_capacity = new_offsets_count;
  }
  memcpy(array->buffer + array->buffer_used, data, size);
  array->offsets[array->offsets_used] = array->buffer_used;
  array->buffer_used += size;
  array->offsets_used++;
  return 0;
}

void* array_get(array_t* const array, const size_t index) {
  if (array == NULL) {
    return NULL;
  }
  if (index >= array->offsets_used) {
    return NULL;
  }
  return array->buffer + array->offsets[index];
}

void array_dump_info(array_t* const array) {
  printf(
    "array_t {\n"
    "  .buffer %p\n"
    "  .offset s%p\n"
    "  .buffer_capacity %zu\n"
    "  .buffer_used %zu\n"
    "  .offsets_capacity %zu\n"
    "  .offsets_used %zu\n"
    "}\n",
    array->buffer, array->offsets, array->buffer_capacity, array->buffer_used,
    array->offsets_capacity, array->offsets_used);
}

void array_destroy(array_t* const array) {
  if (array != NULL) {
    free(array->buffer);
    free(array->offsets);
    array->buffer_capacity = 0;
    array->buffer_used = 0;
    array->offsets_capacity = 0;
    array->offsets_used = 0;
  }
}
