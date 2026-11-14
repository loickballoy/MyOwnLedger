package com.lballoy.ledger.acceptance.api;


import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

import static org.assertj.core.api.Assertions.*;



public class Level0Test {
    static String uri;
    static HttpClient client = HttpClient.newHttpClient();
    static final ObjectMapper mapper = new ObjectMapper();

    @BeforeAll
    static void setup(){
        uri = System.getenv("LEDGER_BASE_URL");
        client = HttpClient.newHttpClient();
    }

    @Test
    public void h1_isHealthy() throws Exception{
        HttpRequest request = HttpRequest.newBuilder(new URI(uri + "/health")).GET().build();
        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        JsonNode actual = mapper.readTree(response.body());

        String txtBlock = """
                {"status": "UP"}
        """;

        JsonNode awaited = mapper.readTree(txtBlock);

        assertThat(response.statusCode()).isEqualTo(200);
        assertThat(awaited).isEqualTo(actual);
    }    
}
