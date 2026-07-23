@echo off
REM Instala multiagentes para uso global com Claude Code

echo ============================================
echo Instalando Multiagentes Globalmente
echo ============================================
echo.

REM 1. Instalar pacote
echo [1/3] Instalando pacote...
cd /d "%~dp0"
pip install -e .
if %errorlevel% neq 0 (
    echo ERRO: Falha na instalacao
    pause
    exit /b 1
)
echo OK
echo.

REM 2. Copiar skills para diretorio global Claude
echo [2/3] Configurando skills do Claude Code...
set CLAUDE_SKILLS=%USERPROFILE%\.claude\skills
if not exist "%CLAUDE_SKILLS%" mkdir "%CLAUDE_SKILLS%"

REM Copiar arquivo de configuracao
copy /Y ".claude\config.json" "%CLAUDE_SKILLS%\multiagentes.json" >nul
echo OK
echo.

REM 3. Verificar instalacao
echo [3/3] Verificando instalacao...
pip show multiagentes
echo.

echo ============================================
echo INSTALACAO CONCLUIDA!
echo ============================================
echo.
echo Como usar em qualquer projeto:
echo.
echo 1. Abra seu projeto:
echo    cd C:\Users\emanu\Documents\Projetos\PostSpark\ 3
echo    claude
echo.
echo 2. No chat do Claude Code:
echo    /plano Criar sistema de autenticacao
echo    /auditoria src/ --dimensoes bugs,security
echo    /implementar --plano ^<dados^>
echo.
echo 3. Ou via terminal:
echo    python -m multiagentes plano
echo    python -m multiagentes auditoria src/
echo.
echo ============================================
pause
