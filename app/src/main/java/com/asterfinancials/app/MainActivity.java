package com.asterfinancials.app;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(Color.rgb(8,9,11));
        getWindow().setNavigationBarColor(Color.rgb(8,9,11));
        WebView w = new WebView(this);
        w.setBackgroundColor(Color.rgb(8,9,11));
        w.setWebViewClient(new WebViewClient());
        WebSettings s = w.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        w.loadUrl("file:///android_asset/index.html");
        setContentView(w);
    }
}