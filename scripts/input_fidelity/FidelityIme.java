// SPDX-License-Identifier: AGPL-3.0-only
package io.github.styayur.lgxt_input_ime;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.inputmethodservice.InputMethodService;
import android.util.Base64;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.TextView;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/** Disposable CI keyboard; no network permission and no credential logging. */
public final class FidelityIme extends InputMethodService {
    private static FidelityIme active;
    private View inputView;
    private static final String TARGET = "io.github.styayur.lgxt_input_fidelity";

    @Override public void onCreate() { super.onCreate(); active = this; }
    @Override public void onDestroy() { active = null; super.onDestroy(); }
    @Override public View onCreateInputView() {
        TextView label = new TextView(this);
        label.setText("LGXT TEST IME — synthetic inputs only");
        label.setTextSize(18);
        label.setPadding(8, 12, 8, 12);
        inputView = label;
        return label;
    }

    public static final class Bridge extends BroadcastReceiver {
        @Override public void onReceive(Context context, Intent intent) {
            JSONObject result = new JSONObject();
            try {
                FidelityIme ime = active;
                if (ime == null) throw new IllegalStateException("Test IME not active");
                EditorInfo info = ime.getCurrentInputEditorInfo();
                InputConnection input = ime.getCurrentInputConnection();
                if (info == null || input == null || !TARGET.equals(info.packageName)) {
                    throw new IllegalStateException("Refusing non-fixture editor");
                }
                String mode = intent.getStringExtra("mode");
                String encoded = intent.getStringExtra("text64");
                String text = encoded == null ? "" : new String(
                    Base64.decode(encoded, Base64.NO_WRAP), StandardCharsets.UTF_8);
                // Public dummy text only; no arbitrary credential argument API.
                if (!text.isEmpty() && !text.matches("fixture-[A-Za-z0-9-]{1,48}")) {
                    throw new IllegalArgumentException("Refusing non-synthetic text");
                }
                boolean accepted;
                if ("probe".equals(mode)) {
                    accepted = true;
                } else if ("commit".equals(mode)) {
                    accepted = input.commitText(text, 1);
                } else if ("fast".equals(mode)) {
                    accepted = true;
                    for (int i = 0; i < text.length(); i++) {
                        accepted = input.commitText(text.substring(i, i + 1), 1) && accepted;
                    }
                } else if ("compose".equals(mode)) {
                    accepted = true;
                    for (int i = 1; i <= text.length(); i++) {
                        accepted = input.setComposingText(text.substring(0, i), 1) && accepted;
                    }
                    accepted = input.finishComposingText() && accepted;
                } else if ("clipboard".equals(mode) || "paste".equals(mode)) {
                    ClipboardManager clipboard = (ClipboardManager)
                        context.getSystemService(Context.CLIPBOARD_SERVICE);
                    clipboard.setPrimaryClip(ClipData.newPlainText("LGXT synthetic fixture", text));
                    accepted = !"paste".equals(mode) ||
                        input.performContextMenuAction(android.R.id.paste);
                } else if ("single".equals(mode)) {
                    // Individual requests are keyed by a public synthetic full text
                    // plus an index, so this bridge never accepts arbitrary chars.
                    int index = intent.getIntExtra("index", -1);
                    if (index < 0 || index >= text.length()) {
                        throw new IllegalArgumentException("Invalid synthetic character index");
                    }
                    accepted = input.commitText(text.substring(index, index + 1), 1);
                } else {
                    throw new IllegalArgumentException("Unknown test input route");
                }
                result.put("ok", accepted);
                result.put("mode", mode);
                result.put("inputType", info.inputType);
                result.put("imeOptions", info.imeOptions);
                result.put("package", info.packageName);
                result.put("requestedCodeUnits", text.length());
                result.put("inputViewRequested", ime.isInputViewShown());
                result.put("inputViewAttached", ime.inputView != null && ime.inputView.isAttachedToWindow());
                result.put("inputViewVisible", ime.inputView != null && ime.inputView.isShown()
                    && ime.inputView.getWindowVisibility() == View.VISIBLE);
                setResultCode(Activity.RESULT_OK);
            } catch (Exception error) {
                try {
                    result.put("ok", false);
                    result.put("errorType", error.getClass().getSimpleName());
                } catch (Exception ignored) { /* fixed JSON fields only */ }
                setResultCode(Activity.RESULT_CANCELED);
            }
            setResultData(result.toString());
        }
    }
}
