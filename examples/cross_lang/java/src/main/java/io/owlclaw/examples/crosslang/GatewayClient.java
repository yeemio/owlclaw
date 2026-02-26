package io.owlclaw.examples.crosslang;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public final class GatewayClient {
    private final HttpClient client;
    private final URI baseUri;

    public GatewayClient(String baseUrl) {
        this.client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        this.baseUri = URI.create(baseUrl);
    }

    public int healthStatusCode() throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(baseUri.resolve("/health"))
                .timeout(Duration.ofSeconds(5))
                .GET()
                .build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        return response.statusCode();
    }
}
