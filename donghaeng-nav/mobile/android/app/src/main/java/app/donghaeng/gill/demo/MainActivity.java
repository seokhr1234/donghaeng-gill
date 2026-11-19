package app.donghaeng.gill.demo;

import android.os.Bundle;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(DonghaengPlugin.class);
        super.onCreate(savedInstanceState);
        if (getBridge() == null) return;

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                getBridge().getWebView().evaluateJavascript(
                    "(function () { const dialog = document.querySelector('dialog[open]');"
                        + " if (!dialog) return false; dialog.close(); return true; })()",
                    handled -> {
                        if ("true".equals(handled) || isFinishing() || isDestroyed()) return;
                        setEnabled(false);
                        getOnBackPressedDispatcher().onBackPressed();
                        setEnabled(true);
                    }
                );
            }
        });
    }
}
