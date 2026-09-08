$ErrorActionPreference = 'Stop'
$taskCandidates = @(
  'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\solid-js',
  'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\typescript',
  'C:\Users\Administrator\.local\bin\bun.exe',
  'C:\Users\Administrator\.bun\bin\bun.exe',
  'C:\Program Files\Bun\bun.exe'
)
foreach ($taskPath in $taskCandidates) {
  [pscustomobject]@{ Path = $taskPath; Exists = Test-Path -LiteralPath $taskPath } | ConvertTo-Json -Compress
}
