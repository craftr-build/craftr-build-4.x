
#include <stdlib.h>

#define ARRAY_ENULL 1
#define ARRAY_ENOMEM 2

typedef struct array {
  void* buffer;
  size_t* offsets;
  size_t buffer_capacity;
  size_t buffer_used;
  size_t offsets_capacity;
  size_t offsets_used;
} array_t;

int array_init(array_t* const array, const size_t min_buffer_size, const size_t min_item_count);

int array_push(array_t* const array, const void* data, const size_t size);

void* array_get(array_t* const array, const size_t index);

void array_dump_info(array_t* const array);

void array_destroy(array_t* const array);
