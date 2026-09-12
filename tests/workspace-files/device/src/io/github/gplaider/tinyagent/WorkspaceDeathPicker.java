package io.github.gplaider.tinyagent;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;

/** Paired-client picker stays alive while the isolated owner process is terminated. */
public final class WorkspaceDeathPicker extends Activity {
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);
        if(!"io.github.gplaider.tinyagent.workspaceprobe".equals(getCallingPackage()))throw new SecurityException("Expected paired owner");
        TextView label=new TextView(this);label.setText("Probe selection pending across owner process death");setContentView(label);
    }
    void deliver(int code,Intent data){setResult(code,data);finish();}
}
