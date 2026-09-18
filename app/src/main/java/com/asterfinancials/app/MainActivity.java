package com.asterfinancials.app;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private WebView web;
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Runnable marketLoop = new Runnable() {
        @Override public void run() {
            requestMarkets();
            main.postDelayed(this, 5000);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(8, 9, 11));
        getWindow().setNavigationBarColor(Color.rgb(8, 9, 11));

        web = new WebView(this);
        web.setBackgroundColor(Color.rgb(8, 9, 11));
        web.setWebViewClient(new WebViewClient());

        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setTextZoom(100);

        web.addJavascriptInterface(new NativeBridge(), "asterNative");
        web.setClickable(true);
        web.setFocusable(true);
        web.setFocusableInTouchMode(true);
        web.setOnTouchListener((v, event) -> {
            if (event.getAction() == android.view.MotionEvent.ACTION_UP && web.getHeight() > 0 && event.getY() >= web.getHeight() - 105) {
                int slot = (int) (event.getX() / Math.max(1f, web.getWidth() / 5f));
                if (slot < 0) slot = 0;
                if (slot > 4) slot = 4;
                final String[] tabs = {"home", "autoinvest", "markets", "wallet", "profile"};
                web.evaluateJavascript("window.nav && window.nav('" + tabs[slot] + "')", null);
                return true;
            }
            return false;
        });
        setContentView(web);
        web.loadUrl("file:///android_asset/index.html");
    }

    @Override protected void onResume() {
        super.onResume();
        main.removeCallbacks(marketLoop);
        main.post(marketLoop);
    }

    @Override protected void onPause() {
        main.removeCallbacks(marketLoop);
        super.onPause();
    }

    private void requestMarkets() {
        network.execute(() -> {
            try {
                URL url = new URL("https://api.binance.com/api/v3/ticker/24hr?symbols=%5B%22BTCUSDT%22,%22ETHUSDT%22,%22SOLUSDT%22,%22BNBUSDT%22,%22XRPUSDT%22,%22DOGEUSDT%22%5D");
                HttpURLConnection c = (HttpURLConnection) url.openConnection();
                c.setRequestMethod("GET");
                c.setConnectTimeout(7000);
                c.setReadTimeout(7000);
                c.setUseCaches(false);

                int code = c.getResponseCode();
                if (code != HttpURLConnection.HTTP_OK) {
                    c.disconnect();
                    return;
                }

                BufferedReader reader = new BufferedReader(new InputStreamReader(c.getInputStream()));
                StringBuilder body = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) body.append(line);
                reader.close();
                c.disconnect();

                JSONArray rows = new JSONArray(body.toString());
                JSONObject out = new JSONObject();

                for (int i = 0; i < rows.length(); i++) {
                    JSONObject row = rows.getJSONObject(i);
                    JSONObject item = new JSONObject();
                    item.put("price", row.getString("lastPrice"));
                    item.put("change", row.getString("priceChangePercent"));
                    out.put(row.getString("symbol"), item);
                }

                final String js = "window.applyMarketData(" + out.toString() + ")";
                main.post(() -> {
                    if (web != null) web.evaluateJavascript(js, null);
                });
            } catch (Exception ignored) {
                // Keep values unavailable. Never invent market data.
            }
        });
    }

    public class NativeBridge {
        @JavascriptInterface
        public void requestMarkets() {
            MainActivity.this.requestMarkets();
        }
    }

    @Override public void onBackPressed() {
        if (web != null) {
            web.evaluateJavascript("(function(){var v=document.querySelector('.view.active');return v?v.id:'home'})()", value -> {
                String id = value == null ? "home" : value.replace("\"", "");
                if (!"home".equals(id)) {
                    web.evaluateJavascript("if(window.nav)nav('home');", null);
                } else {
                    super.onBackPressed();
                }
            });
        } else {
            super.onBackPressed();
        }
    }

    @Override protected void onDestroy() {
        main.removeCallbacksAndMessages(null);
        network.shutdownNow();
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
