import java.nio.channels.Selector;
public class LoopbackCheck {
    public static void main(String[] args) throws Exception {
        System.out.println("java=" + System.getProperty("java.version"));
        System.out.println("tmp=" + System.getProperty("java.io.tmpdir"));
        try (Selector selector = Selector.open()) { System.out.println("Selector.open: OK"); }
    }
}
