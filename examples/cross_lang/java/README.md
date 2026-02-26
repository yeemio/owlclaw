# Cross-language Java Example

This directory provides a Java baseline project for protocol-level integration checks.

## Prerequisites

1. JDK 17
2. Maven 3.9+

## Structure

1. `pom.xml`: Java 17 baseline project configuration.
2. `src/main/java/io/owlclaw/examples/crosslang/Main.java`: entry point.
3. `src/main/java/io/owlclaw/examples/crosslang/GatewayClient.java`: simple HTTP helper.

## Quick Check

```bash
mvn -q -DskipTests package
```
