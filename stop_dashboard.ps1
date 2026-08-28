# stop_simple.ps1
Write-Host "Останавливаю дашборд..." -ForegroundColor Yellow

# Находим все python процессы
$procs = Get-Process -Name python -ErrorAction SilentlyContinue

if ($procs) {
    foreach ($p in $procs) {
        try {
            # Проверяем командную строку
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($p.Id)").CommandLine
            if ($cmd -like "*run_server.py*") {
                Write-Host "Останавливаю PID: $($p.Id)" -ForegroundColor Green
                Stop-Process -Id $p.Id -Force
            }
        } catch {
            Write-Host "Ошибка: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "Процессов python не найдено" -ForegroundColor Yellow
}

# Проверяем порт 8501
$portCheck = netstat -ano | findstr :8501
if ($portCheck) {
    Write-Host "Порт 8501 все еще занят. Проверьте вручную." -ForegroundColor Red
} else {
    Write-Host "Дашборд остановлен!" -ForegroundColor Green
}