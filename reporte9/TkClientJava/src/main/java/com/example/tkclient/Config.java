
package com.example.tkclient;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

public class Config {
    private final File file;
    private final ObjectMapper mapper = new ObjectMapper();
    private Map<String, Object> data = new HashMap<>();

    public Config() {
        String home = System.getProperty("user.home");
        this.file = new File(home, ".tkclient_java_config.json");
        data.put("auth_base", "http://127.0.0.1:5001");
        data.put("books_base", "http://127.0.0.1:5000");
        load();
    }

    public void load() {
        if (file.exists()) {
            try {
                Map m = mapper.readValue(file, Map.class);
                data.putAll(m);
            } catch (IOException ignored) {}
        }
    }

    public void save() {
        try {
            mapper.writerWithDefaultPrettyPrinter().writeValue(file, data);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public String getAuthBase() { return (String) data.get("auth_base"); }
    public String getBooksBase() { return (String) data.get("books_base"); }
    public void setAuthBase(String v) { data.put("auth_base", v); }
    public void setBooksBase(String v) { data.put("books_base", v); }
}
