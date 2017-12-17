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

#include "argument_parser.hpp"

std::string argument_parser::_format_option_name(option_info_t const& opt) const {
  std::string res;
  if (!opt.short_name.empty()) {
    res += _settings.short_option_prefix + opt.short_name;
    if (!opt.long_name.empty()) {
      res += ", ";
    }
  }
  if (!opt.long_name.empty()) {
    res += _settings.long_option_prefix + opt.long_name;
  }
  return res;
}

void argument_parser::operator () (int argc, char** argv) {
  // Consumes an argument and returns true on success, false on failure,
  // that is, when there are no arguments left to be consumed.
  auto consume = [&](std::string* result) -> bool {
    if (argc <= 0) return false;
    argc--; *result = *argv++;
    return true;
  };

  // True if options are still accepted. When the long_option_prefix is
  // parsed on its own, options are no longer accepted and only positional
  // arguments are expected.
  bool accept_options = true;

  // Iterator for the current argument that is being consumed into when an
  // argument does not actually represent an option, plus the number of
  // arguments already consumed for this argument definition.
  auto arg_it = _args.begin();
  int args_consumed = 0;

  // The current option that is being handled and the number of arguments
  // that have already been consumed for the option.
  option_info_t* current_option = nullptr;
  int option_args_consumed = 0;

  // Checks if the current option is satisfied, then switches to a new
  // (or no) option.
  auto next_option = [&](option_info_t* new_option) -> void {
    if (current_option && option_args_consumed != current_option->argc) {
      std::string name = (current_option->long_name.empty() ?
        _settings.short_option_prefix + current_option->short_name :
        _settings.long_option_prefix + current_option->long_name);
      throw parse_error("option \"" + name + "\" requires " +
        std::to_string(current_option->argc) + " arguments, but received " +
        std::to_string(option_args_consumed));
    }
    current_option = new_option;
    option_args_consumed = 0;
  };

  std::string current;
  while (consume(&current)) {
    if (accept_options) {
      // Skip options after the long_option_prefix was parsed alone.
      if (current == _settings.long_option_prefix) {
        accept_options = false;
        continue;
      }
      // Check whether this is a short or long option name.
      char option_type = 0;
      std::string unprefixed_name;
      if (startswith(current, _settings.long_option_prefix)) {
        option_type = 2;
        unprefixed_name = current.substr(_settings.long_option_prefix.size());
      }
      else if (startswith(current, _settings.short_option_prefix)) {
        option_type = 1;
        unprefixed_name = current.substr(_settings.short_option_prefix.size());
      }
      if (option_type != 0) {
        // Find the option information matching this option name.
        bool option_found = false;
        for (auto& opt : _options) {
          if ((option_type == 1 && opt.short_name == unprefixed_name) ||
              (option_type == 2 && opt.long_name == unprefixed_name)) {
            next_option(&opt);
            option_found = true;
            break;
          }
        }
        if (!option_found) {
          throw parse_error("unknown option \"" + current + "\"");
        }
        if (current_option->argc == 0) {
          // Create the entry.
          _parsed_args[current_option->map_key()];
          next_option(nullptr);
        }
        continue;
      }
    }

    if (current_option && option_args_consumed < current_option->argc) {
      option_args_consumed++;
      _parsed_args[current_option->map_key()].push_back(current);
      continue;
    }

    if (arg_it == _args.end()) {
      throw parse_error("positional argument could not be consumed: " + current);
    }

    _parsed_args[arg_it->name].push_back(current);
    args_consumed++;
    if (arg_it->argc > 0 && args_consumed >= arg_it->argc) {
      arg_it++;
      args_consumed = 0;
    }
  }

  next_option(nullptr);

  for (auto& opt : _options) {
    if (opt.required && !has(opt.map_key())) {
      throw parse_error("required option \"" + _format_option_name(opt) +
        "\" is not specified.");
    }
  }

  if (arg_it != _args.end() && arg_it->argc > 0) {
    throw parse_error("missing required argument(s): " + arg_it->name);
  }
}

void argument_parser::print_help() const {
  std::cout << "usage: " << _name << " [OPTIONS]";
  for (auto& arg : _args) {
    std::cout << " ";
    if (!arg.required) std::cout << "[";
    std::cout << toupper(arg.name);
    if (!arg.required) std::cout << "]";
  }
  std::cout << "\n\n";
  if (!_args.empty()) {
    std::cout << "positional arguments:\n";
    for (auto& arg : _args) {
      std::cout << "  " << arg.name << "\n";
    }
    std::cout << "  " << _settings.long_option_prefix << "\n";
    std::cout << "\n";
  }
  if (!_options.empty()) {
    std::cout << "options:\n";
  }
  for (auto& opt : _options) {
    std::cout << "  " << _format_option_name(opt) << "\n";
  }
}
