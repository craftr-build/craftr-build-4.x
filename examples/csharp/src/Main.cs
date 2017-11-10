
public class MainClass {
  public static void Main(string[] args) {
    string name = args.Length == 0 ? "World" : args[0];
    HelloSayer.SayHello(name);
  }
}
