# TkClientJava – Desktop client (Swing) for your microservices

## Build & Run
Requires Java 17+ and Maven.

```bash
mvn -q -f pom.xml package
mvn -q -f pom.xml exec:java
```

## What it includes
- Login, Register, Refresh token (JWT)
- Config persistence (stored at `~/.tkclient_java_config.json`)
- Protected endpoint viewer (`/api/profile`) with `Authorization: Bearer`
- Health lights (green/orange/red) for AUTH and BOOKS
- Books XML table (/api/books)
- Live log of requests/responses and tokens
