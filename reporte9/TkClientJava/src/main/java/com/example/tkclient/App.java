
package com.example.tkclient;

import com.fasterxml.jackson.databind.JsonNode;
import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

public class App extends JFrame {
    private final Config cfg = new Config();
    private final JTextArea logArea = new JTextArea(10, 80);
    private ApiClient api;

    // Top config
    private final JTextField authBaseField = new JTextField(40);
    private final JTextField booksBaseField = new JTextField(40);
    private final SemaphoreIndicator semAuth = new SemaphoreIndicator();
    private final SemaphoreIndicator semBooks = new SemaphoreIndicator();

    // Auth tab components
    private final JLabel statusLabel = new JLabel("Desconectado");
    private final JTextField loginUser = new JTextField(24);
    private final JPasswordField loginPass = new JPasswordField(24);

    private final JTextField regEmail = new JTextField(24);
    private final JTextField regUser = new JTextField(18);
    private final JPasswordField regPass = new JPasswordField(18);

    private final JTextArea accessTokenArea = new JTextArea(4, 60);
    private final JTextArea refreshTokenArea = new JTextArea(3, 60);
    private final JTextField accessExpField = new JTextField(40);

    // Protected tab
    private final JTextArea profileArea = new JTextArea(20, 80);
    private final JLabel protectedStatus = new JLabel("Estado: –");

    // Books tab
    private final DefaultTableModel booksModel = new DefaultTableModel(new Object[]{"isbn","titulo","autor","anio","genero","precio","stock","formato"}, 0);

    public App() {
        super("TkClient Java – Auth + Libros");
        this.api = new ApiClient(cfg.getAuthBase(), cfg.getBooksBase(), this::log);
        initUI();
        updateStatus();
    }

    private void initUI() {
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        setSize(1200, 800);
        setLocationRelativeTo(null);

        JPanel root = new JPanel(new BorderLayout());
        root.add(buildTopBar(), BorderLayout.NORTH);
        root.add(buildTabs(), BorderLayout.CENTER);
        root.add(buildLogPane(), BorderLayout.SOUTH);
        setContentPane(root);
    }

    private JPanel buildTopBar() {
        JPanel p = new JPanel();
        authBaseField.setText(cfg.getAuthBase());
        booksBaseField.setText(cfg.getBooksBase());

        JButton apply = new JButton("Aplicar y Guardar");
        apply.addActionListener(e -> {
            cfg.setAuthBase(authBaseField.getText().trim());
            cfg.setBooksBase(booksBaseField.getText().trim());
            cfg.save();
            api.setBases(cfg.getAuthBase(), cfg.getBooksBase());
            log("Nuevas bases (guardadas): AUTH=" + cfg.getAuthBase() + " BOOKS=" + cfg.getBooksBase());
        });

        JButton health = new JButton("Probar salud");
        health.addActionListener(this::checkHealth);

        p.add(new JLabel("AUTH_BASE:"));
        p.add(authBaseField);
        p.add(new JLabel("BOOKS_BASE:"));
        p.add(booksBaseField);
        p.add(apply);
        p.add(health);
        p.add(new JLabel("AUTH")); p.add(semAuth);
        p.add(new JLabel("BOOKS")); p.add(semBooks);
        semAuth.setState("gray"); semBooks.setState("gray");
        return p;
    }

    private JTabbedPane buildTabs() {
        JTabbedPane tabs = new JTabbedPane();
        tabs.addTab("Auth: Login/Registro/Token", buildAuthTab());
        tabs.addTab("Protegido (/api/profile)", buildProtectedTab());
        tabs.addTab("Libros (XML)", buildBooksTab());
        return tabs;
    }

    private JPanel buildLogPane() {
        JPanel p = new JPanel(new BorderLayout());
        p.add(new JLabel("Peticiones y Respuestas (incluye JWT)"), BorderLayout.NORTH);
        logArea.setEditable(false);
        p.add(new JScrollPane(logArea), BorderLayout.CENTER);
        return p;
    }

    private JPanel buildAuthTab() {
        JPanel panel = new JPanel();
        panel.setLayout(new BoxLayout(panel, BoxLayout.Y_AXIS));

        // Estado
        JPanel state = new JPanel(new FlowLayout(FlowLayout.LEFT));
        state.add(statusLabel);
        panel.add(state);

        // Login
        JPanel login = new JPanel(new FlowLayout(FlowLayout.LEFT));
        login.setBorder(BorderFactory.createTitledBorder("Login"));
        login.add(new JLabel("Email o Usuario"));
        login.add(loginUser);
        login.add(new JLabel("Password"));
        login.add(loginPass);
        JButton btnLogin = new JButton("Login");
        btnLogin.addActionListener(this::doLogin);
        login.add(btnLogin);
        panel.add(login);

        // Registro
        JPanel reg = new JPanel(new FlowLayout(FlowLayout.LEFT));
        reg.setBorder(BorderFactory.createTitledBorder("Registro"));
        reg.add(new JLabel("Email")); reg.add(regEmail);
        reg.add(new JLabel("Usuario")); reg.add(regUser);
        reg.add(new JLabel("Password")); reg.add(regPass);
        JButton btnReg = new JButton("Registrar");
        btnReg.addActionListener(this::doRegister);
        reg.add(btnReg);
        panel.add(reg);

        // Tokens
        JPanel toks = new JPanel();
        toks.setLayout(new GridBagLayout());
        toks.setBorder(BorderFactory.createTitledBorder("Tokens JWT"));
        GridBagConstraints c = new GridBagConstraints();
        c.insets = new Insets(4,4,4,4); c.anchor = GridBagConstraints.WEST;

        c.gridx=0; c.gridy=0; toks.add(new JLabel("Access token"), c);
        c.gridx=1; c.gridy=0; c.weightx=1; c.fill=GridBagConstraints.HORIZONTAL;
        toks.add(new JScrollPane(accessTokenArea), c);

        c.gridx=0; c.gridy=1; c.weightx=0; c.fill=GridBagConstraints.NONE;
        toks.add(new JLabel("Refresh token"), c);
        c.gridx=1; c.gridy=1; c.weightx=1; c.fill=GridBagConstraints.HORIZONTAL;
        toks.add(new JScrollPane(refreshTokenArea), c);

        c.gridx=0; c.gridy=2; c.weightx=0; c.fill=GridBagConstraints.NONE;
        toks.add(new JLabel("Access exp (UTC)"), c);
        c.gridx=1; c.gridy=2; c.weightx=1; c.fill=GridBagConstraints.HORIZONTAL;
        toks.add(accessExpField, c);

        JButton btnRefresh = new JButton("Refresh access token");
        btnRefresh.addActionListener(this::doRefresh);
        c.gridx=2; c.gridy=2; c.weightx=0; c.fill=GridBagConstraints.NONE;
        toks.add(btnRefresh, c);

        panel.add(toks);

        return panel;
    }

    private JPanel buildProtectedTab() {
        JPanel panel = new JPanel(new BorderLayout());
        JPanel top = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton btn = new JButton("Cargar Perfil");
        btn.addActionListener(this::loadProfile);
        top.add(btn);
        top.add(protectedStatus);
        panel.add(top, BorderLayout.NORTH);
        profileArea.setEditable(false);
        panel.add(new JScrollPane(profileArea), BorderLayout.CENTER);
        return panel;
    }

    private JPanel buildBooksTab() {
        JPanel panel = new JPanel(new BorderLayout());
        JPanel filt = new JPanel(new FlowLayout(FlowLayout.LEFT));
        JButton all = new JButton("Todos");
        all.addActionListener(this::loadAllBooks);
        filt.add(all);
        panel.add(filt, BorderLayout.NORTH);

        JTable table = new JTable(booksModel);
        panel.add(new JScrollPane(table), BorderLayout.CENTER);
        return panel;
    }

    // Actions
    private void doRegister(ActionEvent e) {
        runBg(() -> {
            try {
                JsonNode res = api.register(regEmail.getText().trim(), regUser.getText().trim(), new String(regPass.getPassword()));
                log("Registro ok.");
                updateStatus();
                JOptionPane.showMessageDialog(this, "Usuario creado y autenticado.");
            } catch (Exception ex) {
                error("Registro: " + ex.getMessage());
            }
        });
    }

    private void doLogin(ActionEvent e) {
        runBg(() -> {
            try {
                JsonNode res = api.login(loginUser.getText().trim(), new String(loginPass.getPassword()));
                log("Login ok.");
                updateStatus();
                JOptionPane.showMessageDialog(this, "Autenticado.");
            } catch (Exception ex) {
                error("Login: " + ex.getMessage());
            }
        });
    }

    private void doRefresh(ActionEvent e) {
        runBg(() -> {
            try {
                JsonNode res = api.refresh();
                log("Access token renovado.");
                updateStatus();
            } catch (Exception ex) {
                error("Refresh: " + ex.getMessage());
            }
        });
    }

    private void loadProfile(ActionEvent e) {
        runBg(() -> {
            try {
                protectedStatus.setText("Estado: solicitando…");
                JsonNode res = api.profile();
                profileArea.setText(res.toPrettyString());
                protectedStatus.setText("Estado: 200 OK");
                log("Perfil cargado.");
            } catch (Exception ex) {
                protectedStatus.setText("Estado: error");
                error("Perfil: " + ex.getMessage());
            }
        });
    }

    private void loadAllBooks(ActionEvent e) {
        runBg(() -> {
            try {
                String xml = api.booksAllXml();
                SwingUtilities.invokeLater(() -> renderBooksXml(xml));
            } catch (Exception ex) {
                error("Books all: " + ex.getMessage());
            }
        });
    }

    private void renderBooksXml(String xml) {
        try {
            booksModel.setRowCount(0);
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(false);
            DocumentBuilder builder = factory.newDocumentBuilder();
            Document doc = builder.parse(new ByteArrayInputStream(xml.getBytes(StandardCharsets.UTF_8)));
            NodeList books = doc.getElementsByTagName("book");
            for (int i = 0; i < books.getLength(); i++) {
                Node b = books.item(i);
                String isbn = b.getAttributes().getNamedItem("isbn") != null ? b.getAttributes().getNamedItem("isbn").getNodeValue() : "";
                String title = textOf(b, "title");
                String author = textOf(b, "author");
                String year = textOf(b, "year");
                String genre = textOf(b, "genre");
                String price = textOf(b, "price");
                String stock = textOf(b, "stock");
                String format = textOf(b, "format");
                booksModel.addRow(new Object[]{isbn, title, author, year, genre, price, stock, format});
            }
            log("Libros mostrados: " + books.getLength());
        } catch (Exception ex) {
            error("XML inválido: " + ex.getMessage());
            log(xml);
        }
    }

    private String textOf(Node parent, String tag) {
        NodeList list = ((org.w3c.dom.Element) parent).getElementsByTagName(tag);
        if (list.getLength() == 0) return "";
        Node n = list.item(0);
        return n.getTextContent();
    }

    private void updateStatus() {
        statusLabel.setText(api.getAccessToken().isPresent() ? ("Autenticado • exp " + api.getAccessExp().orElse("?")) : "Desconectado");
        accessTokenArea.setText(api.getAccessToken().orElse(""));
        refreshTokenArea.setText(api.getRefreshToken().orElse(""));
        accessExpField.setText(api.getAccessExp().orElse(""));
    }

    private void checkHealth(ActionEvent e) {
        runBg(() -> {
            semAuth.setState("orange");
            semBooks.setState("orange");
            boolean a = api.healthAuth();
            semAuth.setState(a ? "green" : "red");
            boolean b = api.healthBooks();
            semBooks.setState(b ? "green" : "red");
            log("Health AUTH=" + a + " BOOKS=" + b);
        });
    }

    private void runBg(Runnable r) {
        new Thread(() -> {
            try { r.run(); } catch (Exception ignored) {}
        }, "bg").start();
    }

    private void log(String msg) {
        SwingUtilities.invokeLater(() -> {
            logArea.append("[" + java.time.LocalTime.now().withNano(0) + "] " + msg + "\n");
            logArea.setCaretPosition(logArea.getDocument().getLength());
        });
    }

    private void error(String msg) {
        log("ERROR: " + msg);
        Toolkit.getDefaultToolkit().beep();
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new App().setVisible(true));
    }
}
