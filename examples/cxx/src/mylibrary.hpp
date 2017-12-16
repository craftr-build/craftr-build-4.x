
#pragma once
#include <string>

#if defined(MYLIB_SHARED) && defined(_WIN32)
  #if defined(MYLIB_SHARED_EXPORTS)
    #define MYLIB_API __declspec(dllexport)
  #else
    #define MYLIB_API __declspec(dllimport)
  #endif
#else
  #define MYLIB_API
#endif

#pragma warning(push)
#pragma warning(disable: 4251)

class MYLIB_API HelloSayer {
  std::string _name;
public:
  HelloSayer(std::string const& name);
  void say_hello();
};

#pragma warning(pop)
