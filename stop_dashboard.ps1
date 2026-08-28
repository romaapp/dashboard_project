# stop_dashboard.ps1
Write-Host "=== STOP DASHBOARD ===" -ForegroundColor Cyan
Write-Host ""

# 1. Find process on port 8501
Write-Host "Checking port 8501..." -ForegroundColor Yellow
$portInfo = netstat -ano | findstr :8501

if ($portInfo) {
    Write-Host "Found process on port 8501:" -ForegroundColor Green
    Write-Host $portInfo -ForegroundColor Gray
    
    # Extract PID (используем другую переменную, не $pid)
    $pidMatch = [regex]::Match($portInfo, '(\d+)$')
    if ($pidMatch.Success) {
        $processId = $pidMatch.Groups[1].Value  # ← Используем $processId вместо $pid
        Write-Host "Stopping PID: $processId" -ForegroundColor Yellow
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Host "Process stopped!" -ForegroundColor Green
    }
} else {
    Write-Host "No process found on port 8501" -ForegroundColor Yellow
}

# 2. Also check python processes with run_server.py
Write-Host ""
Write-Host "Checking python processes..." -ForegroundColor Yellow
$procs = Get-Process -Name python -ErrorAction SilentlyContinue

if ($procs) {
    foreach ($p in $procs) {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)").CommandLine
            if ($cmd -like "*run_server.py*") {
                Write-Host "Stopping python process PID: $($p.Id)" -ForegroundColor Yellow
                Stop-Process -Id $p.Id -Force
                Write-Host "Python process stopped!" -ForegroundColor Green
            }
        } catch {
            Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "No python processes found" -ForegroundColor Yellow
}

# 3. Check result
Write-Host ""
Write-Host "Checking port 8501 again..." -ForegroundColor Yellow
$checkPort = netstat -ano | findstr :8501
if ($checkPort) {
    Write-Host "Port 8501 is still busy!" -ForegroundColor Red
    Write-Host $checkPort -ForegroundColor Gray
} else {
    Write-Host "Port 8501 is free!" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Cyan
Read-Host "Press Enter to exit"