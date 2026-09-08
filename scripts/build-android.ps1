param([switch]$LintOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$env:ANDROID_HOME = 'C:\Users\Administrator\AppData\Local\Android\Sdk'
$taskSocketDirectory = 'D:\TinyAgent-work\jtmp'
New-Item -ItemType Directory -Path $taskSocketDirectory -Force | Out-Null
$env:JAVA_TOOL_OPTIONS = "-Djdk.net.unixdomain.tmpdir=$taskSocketDirectory"
& java (Join-Path $PSScriptRoot 'LoopbackCheck.java')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location $taskRoot
try {
  if ($LintOnly) { & .\gradlew.bat --no-daemon :app:lintDebug }
  else { & .\gradlew.bat --no-daemon --stacktrace :app:assembleDebug :app:lintDebug }
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  if (-not $LintOnly) {
    & 'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -I -S -X utf8 (Join-Path $PSScriptRoot 'check-packaged-runtime.py')
  }
  exit $LASTEXITCODE
} finally { Pop-Location }
