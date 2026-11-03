@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
cd /d "C:\Users\marcos.castilho\testes-gemini\clipping"
echo ============================================================ > ultimo_log_agendador.txt
echo Execucao automatica iniciada em: %DATE% %TIME% >> ultimo_log_agendador.txt
echo ============================================================ >> ultimo_log_agendador.txt
"C:\Users\marcos.castilho\AppData\Local\Microsoft\WindowsApps\python3.12.exe" ..\sincronizar_nuvem.py pull >> ultimo_log_agendador.txt 2>&1
"C:\Users\marcos.castilho\AppData\Local\Microsoft\WindowsApps\python3.12.exe" gerar_clipping.py --skip-if-exists --no-browser >> ultimo_log_agendador.txt 2>&1
echo Execucao concluida em: %DATE% %TIME% >> ultimo_log_agendador.txt
