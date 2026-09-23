param(
    [Parameter(Mandatory = $true)][string]$ModelDirectory,
    [Parameter(Mandatory = $true)][string]$ClassMap
)
$ErrorActionPreference = 'Stop'
$modelSource = (Resolve-Path -LiteralPath $ModelDirectory).Path
$mappingSource = (Resolve-Path -LiteralPath $ClassMap).Path
if (-not (Test-Path -LiteralPath (Join-Path $modelSource 'MLmodel'))) {
    throw 'ModelDirectory must contain an exported MLflow MLmodel file.'
}
function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker failed with exit code $LASTEXITCODE" }
}
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    Invoke-Docker compose up -d --build --wait mlflow
    $containerId = (& docker compose ps -q mlflow).Trim()
    if (-not $containerId) { throw 'MLflow container is missing.' }
    Invoke-Docker cp $modelSource "${containerId}:/tmp/lab4-source-model"
    Invoke-Docker cp $mappingSource "${containerId}:/tmp/lab4-class-map.json"
    Invoke-Docker cp scripts/seed_lab4.py "${containerId}:/tmp/seed_lab4.py"
    Invoke-Docker compose exec -T mlflow python /tmp/seed_lab4.py --tracking-uri http://mlflow:5000 --model-dir /tmp/lab4-source-model --class-map /tmp/lab4-class-map.json --output /tmp/lab4-seed.json
    New-Item -ItemType Directory -Force reports/lab4 | Out-Null
    Invoke-Docker cp "${containerId}:/tmp/lab4-seed.json" reports/lab4/seed.json
    Invoke-Docker compose up -d --build --wait
    Write-Output 'Food-11: http://127.0.0.1:8501 | MLflow: http://127.0.0.1:5500'
}
finally {
    Pop-Location
}
