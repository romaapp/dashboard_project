#!/usr/bin/env python3
"""
Скрипт для запуска дашборда на Streamlit
"""
import subprocess
import sys
import os

def run_dashboard():
    """Запускает Streamlit приложение"""
    print("🚀 Запуск дашборда...")
    print(f"📊 Открывайте в браузере: http://localhost:8501")
    
    try:
        # Запускаем Streamlit
        subprocess.run([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            "app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"  # Доступно для всех в сети
        ])
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    run_dashboard()