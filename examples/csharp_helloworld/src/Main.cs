
using Newtonsoft.Json.Linq;

public class MainClass {
  public static void Main(string[] args) {
    System.Console.WriteLine("Hello, world!");

    JArray array = new JArray();
    array.Add("Manual text");
    array.Add(new System.DateTime(2000, 5, 23));

    JObject o = new JObject();
    o["MyArray"] = array;

    string json = o.ToString();
    System.Console.WriteLine(o.ToString());
  }
}
