$ErrorActionPreference = 'Stop'
$projectPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$classesPath = Join-Path $projectPath '.checks/policy'
New-Item -ItemType Directory -Path $classesPath -Force | Out-Null
$policySource = Join-Path $projectPath 'app/src/main/java/io/github/gplaider/tinyagent/LocalPolicy.java'
$checkSource = Join-Path $projectPath 'app/src/test/java/io/github/gplaider/tinyagent/LocalPolicyCheck.java'
& javac -encoding UTF-8 -d $classesPath $policySource $checkSource
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& java -cp $classesPath io.github.gplaider.tinyagent.LocalPolicyCheck
exit $LASTEXITCODE
