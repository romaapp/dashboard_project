# monitor_dashboard.ps1
$projectPath = "C:\dashboard_project"
$logFile = "$projectPath\logs\monitor.log"
$pythonExe = "$projectPath\venv\Scripts\python.exe"

# Функция для записи в лог
function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -FilePath $logFile -Append
}

# Создаем папку для логов если её нет
if (!(Test-Path "$projectPath\logs")) {
    New-Item -ItemType Directory -Path "$projectPath\logs" -Force
}

# Проверяем, запущен ли процесс python с run_server.py
$processes = Get-Process -Name python -ErrorAction SilentlyContinue
$isRunning = $false

foreach ($proc in $processes) {
    try {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
        if ($cmdLine -like "*run_server.py*") {
            $isRunning = $true
            Write-Log "Dashboard is running (PID: $($proc.Id))"
            break
        }
    } catch {
        # Ignore errors
    }
}

if (-not $isRunning) {
    Write-Log "Dashboard is not running! Starting..."
    
    try {
        # Запускаем дашборд в фоновом режиме
        Start-Process -FilePath "powershell.exe" -ArgumentList "-ExecutionPolicy Bypass -File `"$projectPath\start_dashboard.ps1`"" -WindowStyle Hidden
        Write-Log "Dashboard started successfully!"
    } catch {
        Write-Log "Error starting dashboard: $($_.Exception.Message)"
    }
}