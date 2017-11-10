
public class Main {
  public static void main(String[] args) {
    hello.Hello.say();
    for (String s : args) {
      System.out.println("> " + s);
    }
  }
}
