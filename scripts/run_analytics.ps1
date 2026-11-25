
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

$queryDir = Join-Path $root "warehouse\queries"

$queries = Get-ChildItem $queryDir -Filter "0*.sql" |
    Sort-Object Name

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "DATAFLOW NEXUS - BUSINESS ANALYTICS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

foreach ($query in $queries) {

    Write-Host "`n--- $($query.BaseName) ---" -ForegroundColor Yellow

    Get-Content $query.FullName -Raw |
        docker exec -i nexus-postgres psql `
        -U nexus_admin `
        -d dataflow_nexus `
        -v ON_ERROR_STOP=1 `
        -P pager=off

    if ($LASTEXITCODE -ne 0) {
        throw "Query failed: $($query.Name)"
    }
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "ALL ANALYTICS QUERIES COMPLETED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
