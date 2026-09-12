"""Compile the production exit-history selector against a minimal Android API double."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'app/src/main/java/io/github/gplaider/tinyagent/RuntimeSetupService.java').read_text(encoding='utf-8')
method = re.search(r'    static String previousExit\(.*?\n    \}', source, re.S).group()
check = '''
import java.util.List;
public class ExitReportCheck {
  static class ApplicationExitInfo {
    static final int REASON_LOW_MEMORY=3, REASON_CRASH=4, REASON_CRASH_NATIVE=5, REASON_ANR=6;
    final String name; final int reason; final long time;
    ApplicationExitInfo(String n,int r,long t) { name=n; reason=r; time=t; }
    String getProcessName() { return name; }
    int getReason() { return reason; }
    long getTimestamp() { return time; }
  }
  static class ActivityManager {
    final List<ApplicationExitInfo> rows;
    ActivityManager(ApplicationExitInfo... r) { rows=List.of(r); }
    List<ApplicationExitInfo> getHistoricalProcessExitReasons(String pkg,int pid,int limit) {
      if(!pkg.equals("app") || pid!=0 || limit!=16) throw new AssertionError("Wrong history scope");
      return rows;
    }
  }
  static ApplicationExitInfo row(String p,int r,long t) { return new ApplicationExitInfo(p,r,t); }
  static void require(boolean value) { if(!value) throw new AssertionError(); }
  public static void main(String[] args) {
    java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"));
    require(previousExit(new ActivityManager(),"app").isEmpty());
    require(previousExit(new ActivityManager(row("webview",3,900000),row("app",16,800000),row("app",10,700000)),"app").isEmpty());
    String memory=previousExit(new ActivityManager(row("app",3,120000),row("app",4,60000),row("webview",6,900000),row("app",16,800000)),"app");
    require(memory.contains("Android 메모리 부족") && memory.contains("1970-01-01 00:02"));
    require(previousExit(new ActivityManager(row("app",3,0),row("app",6,60000)),"app").contains("ANR"));
    require(previousExit(new ActivityManager(row("app",5,0)),"app").contains("네이티브"));
    require(previousExit(new ActivityManager(row("app",4,0)),"app").contains("앱 오류"));
    require(previousExit(null,"app").contains("읽지 못했습니다"));
    System.out.println("Exit history: scoped latest failure, normal exits, renderer exclusion and unavailable history passed");
  }
'''
with tempfile.TemporaryDirectory(prefix='tinyagent-exit-report-') as directory:
    temp = Path(directory)
    (temp / 'ExitReportCheck.java').write_text(check + method + '\n}', encoding='utf-8')
    subprocess.run(['javac', '-encoding', 'UTF-8', str(temp / 'ExitReportCheck.java')], check=True)
    subprocess.run(['java', '-cp', directory, 'ExitReportCheck'], check=True)
