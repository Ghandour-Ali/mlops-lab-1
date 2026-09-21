# Run from any directory; this server shares the existing lab database.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\.venv\Scripts\mlflow.exe server --host 0.0.0.0 --port 5002 --workers 1 `
    --backend-store-uri sqlite:///mlflow.db --serve-artifacts `
    --artifacts-destination ./mlartifacts --default-artifact-root mlflow-artifacts:/ `
    --allowed-hosts 'localhost:*,127.0.0.1:*,host.docker.internal:*'
exit $LASTEXITCODE
