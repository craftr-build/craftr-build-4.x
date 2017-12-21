/* This is free and unencumbered software released into the public domain.
 *
 * Anyone is free to copy, modify, publish, use, compile, sell, or
 * distribute this software, either in source code form or as a compiled
 * binary, for any purpose, commercial or non-commercial, and by any
 * means.
 *
 * In jurisdictions that recognize copyright laws, the author or authors
 * of this software dedicate any and all copyright interest in the
 * software to the public domain. We make this dedication for the benefit
 * of the public at large and to the detriment of our heirs and
 * successors. We intend this dedication to be an overt act of
 * relinquishment in perpetuity of all present and future rights to this
 * software under copyright law.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 * OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 *
 * For more information, please refer to <http://unlicense.org>
 */

#pragma once
#include <algorithm>
#include <cassert>
#include <cstring>
#include <iostream>
#include <unordered_map>
#include <string>
#include <vector>

/* This class implements a simple command-line argument parser. */
class argument_parser {
public:

  /* Settings for the argument parser. */
  struct settings_t {
    std::string short_option_prefix;
    std::string long_option_prefix;
    settings_t() : short_option_prefix("-"), long_option_prefix("--") {}
  };

  /* A structure that represents an option. */
  struct option_info_t {
    std::string short_name;
    std::string long_name;
    int argc;
    bool required;
    std::string const& map_key() const { return long_name.empty() ? short_name : long_name; }
  };

  /* A structure that represents a positional argument. Every positional
   * argument is stored in a #std::vector of arguments, even if the number
   * of consumed positional arguments is fixed to 1. */
  struct argument_info_t {
    std::string name;
    int argc;
    bool required;
  };

  /* Raised when the command-line settings did not fulfill all requirements. */
  struct parse_error : public std::exception {
    std::string _msg;
    parse_error(std::string const& msg) : _msg(msg) {}
    virtual char const* what() const throw() { return _msg.c_str(); }
  };

  using arglist_t = std::vector<std::string>;
  using results_t = std::unordered_map<std::string, arglist_t>;

  /* Check if a string starts with another string. */
  static inline bool startswith(std::string const& subject, std::string const& needle) {
    if (subject.size() < needle.size()) return false;
    return strncmp(subject.c_str(), needle.c_str(), needle.size()) == 0;
  }

  /* Converts a string to uppercase. */
  static inline std::string toupper(std::string str) {
    std::transform(str.begin(), str.end(), str.begin(), ::toupper);
    return str;
  }

private: // members

  std::string _name;
  results_t _parsed_args;
  std::vector<option_info_t> _options;
  std::vector<argument_info_t> _args;
  settings_t _settings;

  std::string _format_option_name(option_info_t const& opt) const;

public: // members

  inline argument_parser(std::string const& name, settings_t const& settings = {})
    : _name(name), _settings(settings) {}

  inline ~argument_parser() {}

  /* Add an option to the parser. */
  inline void add_option(
    std::string const& short_name,
    std::string const& long_name,
    int argc = 1,
    bool required = false)
  {
    _options.push_back({short_name, long_name, argc, required});
  }

  /* Add a positional argument to the parser. An argument consumes as many
   * values as possible if #argc is below 0. #argc can not be 0. */
  inline void add_argument(
    std::string const& name,
    int argc = 1,
    bool required = true)
  {
    assert(argc != 0);
    _args.push_back({name, argc, required});
  }

  /* Parse the command-line arguments. */
  void operator () (int argc, char** argv);

  /* Prints the help for this argument parser. */
  void print_help() const;

  /* Returns #true if the parser has a valid entry for the specified argument. */
  bool has(std::string const& key) const {
    return _parsed_args.find(key) != _parsed_args.end();
  }

  /* Returns the values for the specified argument. Does not fail, even if the
   * value does not exist, however it can return an empty vector. Check with #has()
   * if the argument or option was parsed. */
  arglist_t const& operator [] (std::string const& key) {
    return _parsed_args[key];
  }

};
