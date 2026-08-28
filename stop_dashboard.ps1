# stop_dashboard.ps1
Write-Host "=== STOP DASHBOARD ===" -ForegroundColor Cyan
Write-Host ""

# Способ 1: Найти процесс на порту 8501 через netstat
Write-Host "Method 1: Finding process by port 8501..." -ForegroundColor Yellow
$portInfo = netstat -ano | findstr :8501 | findstr LISTENING

if ($portInfo) {
    Write-Host "Found:" -ForegroundColor Green
    Write-Host $portInfo -ForegroundColor Gray
    
    # Извлекаем PID (последнее число в строке)
    $parts = $portInfo -split '\s+'
    $processId = $parts[-1]
    
    if ($processId -match '^\d+$') {
        Write-Host "Stopping PID: $processId" -ForegroundColor Yellow
        taskkill /PID $processId /F
        Write-Host "Process killed!" -ForegroundColor Green
    }
} else {
    Write-Host "No process found listening on port 8501" -ForegroundColor Yellow
}

# Способ 2: Найти все python процессы с run_server.py
Write-Host ""
Write-Host "Method 2: Finding python processes with run_server.py..." -ForegroundColor Yellow

# Получаем список всех python процессов
$pythonProcesses = Get-WmiObject Win32_Process | Where-Object { $_.Name -eq "python.exe" }

if ($pythonProcesses) {
    $found = $false
    foreach ($proc in $pythonProcesses) {
        if ($proc.CommandLine -like "*run_server.py*") {
            Write-Host "Found python process with run_server.py" -ForegroundColor Green
            Write-Host "  PID: $($proc.ProcessId)" -ForegroundColor Gray
            Write-Host "  Command: $($proc.CommandLine)" -ForegroundColor Gray
            Write-Host "Stopping..." -ForegroundColor Yellow
            Stop-Process -Id $proc.ProcessId -Force
            Write-Host "Process stopped!" -ForegroundColor Green
            $found = $true
        }
    }
    if (-not $found) {
        Write-Host "No python processes with run_server.py found" -ForegroundColor Yellow
    }
} else {
    Write-Host "No python processes found" -ForegroundColor Yellow
}

# Способ 3: Найти все процессы на порту 8501 (включая ESTABLISHED)
Write-Host ""
Write-Host "Method 3: Killing all processes on port 8501..." -ForegroundColor Yellow
$allPortInfo = netstat -ano | findstr :8501

if ($allPortInfo) {
    $pids = $allPortInfo | ForEach-Object {
        $parts = $_ -split '\s+'
        $pid = $parts[-1]
        if ($pid -match '^\d+$') {
            $pid
        }
    } | Select-Object -Unique
    
    foreach ($pid in $pids) {
        if ($pid -ne "0") {
            Write-Host "Killing PID: $pid" -ForegroundColor Yellow
            taskkill /PID $pid /F 2>$null
        }
    }
    Write-Host "All processes on port 8501 killed!" -ForegroundColor Green
} else {
    Write-Host "No processes found on port 8501" -ForegroundColor Yellow
}

# Проверка результата
Write-Host ""
Write-Host "Checking result..." -ForegroundColor Yellow
$checkPort = netstat -ano | findstr :8501
if ($checkPort) {
    Write-Host "Port 8501 is still busy!" -ForegroundColor Red
    Write-Host $checkPort -ForegroundColor Gray
} else {
    Write-Host "Port 8501 is FREE!" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== DONE ===" -ForegroundColor Cyan
Read-Host "Press Enter to exit"