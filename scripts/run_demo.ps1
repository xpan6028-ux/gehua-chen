param(
    [ValidateSet('plan','run')][string]$Action = 'plan',
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [string]$PythonExe,
    [string]$Stata,
    [ValidateRange(1,86400)][int]$Timeout = 300
)
$ErrorActionPreference = 'Stop'
$demoSkillRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not [IO.Path]::IsPathRooted($OutputRoot)) {
    throw 'OutputRoot must be an absolute path in your chosen output location.'
}
$demoPythonCandidates = @()
if ($PythonExe) {
    if (-not [IO.Path]::IsPathRooted($PythonExe)) { throw 'PythonExe must be an absolute executable path.' }
    $demoPythonCandidates += [pscustomobject]@{ Exe=$PythonExe; Prefix=@() }
} else {
    foreach ($demoName in @('python','python3','py')) {
        $demoCommand = Get-Command $demoName -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($demoCommand) {
            $demoPrefix = @()
            if ($demoName -eq 'py') { $demoPrefix = @('-3') }
            $demoPythonCandidates += [pscustomobject]@{ Exe=$demoCommand.Source; Prefix=$demoPrefix }
        }
    }
}
$demoPythonPath = $null
foreach ($demoCandidate in $demoPythonCandidates) {
    try {
        $demoPrefixArgs = @($demoCandidate.Prefix)
        $demoProbe = & $demoCandidate.Exe @demoPrefixArgs -X utf8 -c 'import sys; assert sys.version_info >= (3,9); print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $demoProbe) {
            $demoResolved = ($demoProbe | Select-Object -Last 1).ToString().Trim()
            if ([IO.Path]::IsPathRooted($demoResolved) -and (Test-Path -LiteralPath $demoResolved -PathType Leaf)) {
                $demoPythonPath = (Resolve-Path -LiteralPath $demoResolved).Path
                break
            }
        }
    } catch { continue }
}
if (-not $demoPythonPath) {
    throw 'No usable Python 3.9+ found. Supply -PythonExe with the actual absolute executable path; nothing was installed.'
}
$demoArgs = @(
    (Join-Path $demoSkillRoot 'scripts/stata_runner.py'),
    $Action,
    (Join-Path $demoSkillRoot 'assets/fullspec_auto.json'),
    '--output-root', [IO.Path]::GetFullPath($OutputRoot),
    '--timeout', $Timeout.ToString()
)
if ($Stata) { $demoArgs += @('--stata', $Stata) }
& $demoPythonPath @demoArgs
exit $LASTEXITCODE
