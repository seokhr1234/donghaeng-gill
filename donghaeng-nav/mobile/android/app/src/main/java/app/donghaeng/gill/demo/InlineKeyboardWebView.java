package app.donghaeng.gill.demo;

import android.content.Context;
import android.util.AttributeSet;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import com.getcapacitor.CapacitorWebView;

public class InlineKeyboardWebView extends CapacitorWebView {
    public InlineKeyboardWebView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    @Override
    public InputConnection onCreateInputConnection(EditorInfo editorInfo) {
        InputConnection connection = super.onCreateInputConnection(editorInfo);
        if (connection != null) {
            editorInfo.imeOptions |= EditorInfo.IME_FLAG_NO_FULLSCREEN | EditorInfo.IME_FLAG_NO_EXTRACT_UI;
        }
        return connection;
    }
}
