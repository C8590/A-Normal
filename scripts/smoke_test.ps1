param(
    [switch]$Full,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$argsList = @("scripts/smoke_test.py")
if ($Full) {
    $argsList += "--full"
}
if ($Json) {
    $argsList += "--format"
    $argsList += "json"
}

py -3.12 @argsList
