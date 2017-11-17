
#pragma once

#if defined(HELLOLIB_SHARED) && defined(_WIN32)
  #if defined(HELLOLIB_EXPORTS)
    #define HELLOLIB_API __declspec(dllexport)
  #else
    #define HELLOLIB_API __declspec(dllimport)
  #endif
#else
  #define HELLOLIB_API
#endif

HELLOLIB_API void say_hello();
