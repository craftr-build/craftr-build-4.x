
extern void say_hello(char const* name, char const* weather);

int main(int argc, char** argv) {
  if (argc != 3) {
    printf("error: usage: %s name weather\n");
    return 0;
  }
  say_hello(argv[1], argv[2]);
  return 0;
}
