@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
cd /d "C:\Users\marcos.castilho\testes-gemini\clipping"
echo ============================================================ > ultimo_log_agendador.txt
echo Execucao automatica (Despertador Nuvem) iniciada em: %DATE% %TIME% >> ultimo_log_agendador.txt
echo ============================================================ >> ultimo_log_agendador.txt
echo [PULL] Baixando arquivos atualizados da nuvem... >> ultimo_log_agendador.txt
"C:\Users\marcos.castilho\AppData\Local\Microsoft\WindowsApps\python3.12.exe" ..\sincronizar_nuvem.py pull >> ultimo_log_agendador.txt 2>&1
echo [DISPARO] Acionando workflow do Clipping & Radar na nuvem via GitHub CLI... >> ultimo_log_agendador.txt
"%LOCALAPPDATA%\Microsoft\WinGet\Links\gh.exe" workflow run clipping_diario_nuvem.yml --repo mdagavea/inteligencia-regulatoria >> ultimo_log_agendador.txt 2>&1
echo [SUCESSO] Disparo solicitado na nuvem em: %DATE% %TIME% >> ultimo_log_agendador.txt

