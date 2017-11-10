
import com.google.common.base.Optional;

public class Main {
  public static void main(String[] args) {
    Optional<String> name = args.length == 0 ? Optional.absent() : Optional.of(args[0]);
    System.out.println("Hello, " + name + "!");
  }
}
