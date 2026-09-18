$ErrorActionPreference = "Stop"

function Assert-HttpOk {
    param([string]$Url)
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing
    if ($response.StatusCode -ne 200) { throw "Resposta inesperada: $($response.StatusCode)" }
}

docker compose up --build -d
try {
    Start-Sleep -Seconds 8
    Assert-HttpOk "http://localhost:8080/health"

    docker compose stop api-1
    Start-Sleep -Seconds 2
    Assert-HttpOk "http://localhost:8080/health"

    Write-Host "PASSOU: o gateway continuou respondendo após a parada da api-1."
}
finally {
    docker compose down
}
