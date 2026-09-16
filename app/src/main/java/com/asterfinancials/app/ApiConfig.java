package com.asterfinancials.app;

/** Development API configuration. Replace with the deployed HTTPS API before release. */
public final class ApiConfig {
    private ApiConfig() {}

    public static String baseUrl() {
        String configured = System.getProperty("aster.api.baseUrl");
        if (configured != null && !configured.isBlank()) return configured;
        return "https://api.example.invalid";
    }
}
