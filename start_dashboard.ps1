# start_dashboard.ps1
# Путь к проекту
$projectPath = "C:\dashboard_project"

# Переходим в папку проекта
Set-Location $projectPath

# Активируем виртуальное окружение и запускаем run_server.py
& ".\venv\Scripts\python.exe" run_server.py