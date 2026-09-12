package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;

/** Probe-only delayed result Activity; never opens the system document picker. */
public final class WorkspaceProbePicker extends Activity {
    static int launches;
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        if(saved==null)launches++;
        TextView label=new TextView(this);
        label.setText("Probe destination selection pending");
        setContentView(label);
    }
    void deliver(int code,Intent result){setResult(code,result);finish();}
}
