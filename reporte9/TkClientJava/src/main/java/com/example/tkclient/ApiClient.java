
package com.example.tkclient;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Optional;

public class ApiClient {
    private String authBase;
    private String booksBase;
    private String accessToken;
    private String refreshToken;
    private String accessExp;
    private final ObjectMapper mapper = new ObjectMapper();
    private final HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(8))
            .build();
    private final Logger logger;

    public interface Logger {
        void log(String msg);
    }

    public ApiClient(String authBase, String booksBase, Logger logger) {
        this.authBase = authBase;
        this.booksBase = booksBase;
        this.logger = logger;
    }

    public void setBases(String authBase, String booksBase) {
        this.authBase = authBase;
        this.booksBase = booksBase;
    }

    public Optional<String> getAccessToken() { return Optional.ofNullable(accessToken); }
    public Optional<String> getRefreshToken() { return Optional.ofNullable(refreshToken); }
    public Optional<String> getAccessExp() { return Optional.ofNullable(accessExp); }

    private void logReq(String label, String method, String url, String body) {
        if (logger != null) {
            logger.log("[" + label + "] " + method + " " + url);
            if (body != null) logger.log("  payload=" + body);
        }
    }

    private void logResp(String label, HttpResponse<String> resp) {
        if (logger != null) {
            logger.log("  => " + resp.statusCode() + " content-type=" + resp.headers().firstValue("Content-Type").orElse(""));
            String text = resp.body();
            if (text != null) {
                if (text.length() > 2000) text = text.substring(0, 2000) + "…";
                logger.log("  body=" + text);
            }
        }
    }

    private HttpRequest.Builder baseReq(String url) {
        HttpRequest.Builder b = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(12));
        return b;
    }

    private void throwIfError(String label, String url, HttpResponse<String> resp) throws IOException {
        if (resp.statusCode() >= 400) {
            logResp(label, resp);
            throw new IOException(resp.statusCode() + " error " + url + "\nBody: " + resp.body());
        }
    }

    // ---- Auth ----
    public JsonNode register(String email, String username, String password) throws Exception {
        String url = authBase + "/auth/register";
        String body = "{\"email\":\"" + email + "\",\"username\":\"" + username + "\",\"password\":\"" + password + "\"}";
        logReq("register", "POST", url, body);
        HttpRequest req = baseReq(url).header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(body)).build();
        HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
        logResp("register", resp);
        throwIfError("register", url, resp);
        JsonNode json = mapper.readTree(resp.body());
        storeTokensFrom(json);
        return json;
    }

    public JsonNode login(String who, String password) throws Exception {
        String url = authBase + "/auth/login";
        String body = "{\"email\":\"" + who + "\",\"username\":\"" + who + "\",\"password\":\"" + password + "\"}";
        logReq("login", "POST", url, body);
        HttpRequest req = baseReq(url).header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(body)).build();
        HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
        logResp("login", resp);
        throwIfError("login", url, resp);
        JsonNode json = mapper.readTree(resp.body());
        storeTokensFrom(json);
        return json;
    }

    private void storeTokensFrom(JsonNode json) {
        JsonNode toks = json.path("tokens");
        if (!toks.isMissingNode()) {
            accessToken = toks.path("access_token").asText(null);
            refreshToken = toks.path("refresh_token").asText(null);
            accessExp = toks.path("access_expires_at_utc").asText(null);
        }
    }

    public JsonNode refresh() throws Exception {
        if (refreshToken == null) throw new IllegalStateException("No hay refresh_token cargado.");
        String url = authBase + "/auth/refresh";
        String body = "{\"refresh_token\":\"" + refreshToken + "\"}";
        logReq("refresh", "POST", url, body);
        HttpRequest req = baseReq(url).header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(body)).build();
        HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
        logResp("refresh", resp);
        throwIfError("refresh", url, resp);
        JsonNode json = mapper.readTree(resp.body());
        accessToken = json.path("access_token").asText(null);
        accessExp = json.path("access_expires_at_utc").asText(null);
        return json;
    }

    public JsonNode profile() throws Exception {
        String url = authBase + "/api/profile";
        HttpRequest.Builder b = baseReq(url).GET();
        if (accessToken != null) b.header("Authorization", "Bearer " + accessToken);
        logReq("profile", "GET", url, null);
        HttpResponse<String> resp = client.send(b.build(), HttpResponse.BodyHandlers.ofString());
        logResp("profile", resp);
        throwIfError("profile", url, resp);
        return mapper.readTree(resp.body());
    }

    public boolean healthAuth() {
        String url = authBase + "/health";
        try {
            HttpRequest req = baseReq(url).GET().build();
            HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
            logResp("health_auth", resp);
            return resp.statusCode() == 200;
        } catch (Exception e) {
            if (logger != null) logger.log("health_auth error: " + e.getMessage());
            return false;
        }
    }

    // ---- Books ----
    public String booksAllXml() throws Exception {
        String url = booksBase + "/api/books";
        logReq("books_all", "GET", url, null);
        HttpRequest req = baseReq(url).header("Accept","application/xml").GET().build();
        HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
        logResp("books_all", resp);
        throwIfError("books_all", url, resp);
        return resp.body();
    }

    public boolean healthBooks() {
        try {
            return booksAllXml() != null;
        } catch (Exception e) {
            return false;
        }
    }
}
