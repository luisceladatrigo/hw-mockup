Param(
  [switch]$Watch
)

Write-Host "Running unit tests..." -ForegroundColor Cyan
python -m unittest discover -s tests -p "test_*.py" -v

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Watch) {
  Write-Host "--watch not implemented yet" -ForegroundColor Yellow
}
