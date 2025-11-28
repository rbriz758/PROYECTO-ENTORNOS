@echo off
echo ========================================
echo SISTEMA DE CONTROL DIGITAL TWIN
echo Motor de Fisica Centralizado
echo ========================================
echo.

echo Iniciando servidores OPC UA...
echo.

REM Iniciar cada servidor en una ventana separada
start "Servidor Nivel" cmd /k "cd /d %~dp0\src && python server_nivel.py"
timeout /t 2 /nobreak >nul

start "Servidor Temperatura" cmd /k "cd /d %~dp0\src && python server_temp.py"
timeout /t 2 /nobreak >nul

start "Servidor Entrada" cmd /k "cd /d %~dp0\src && python server_entrada.py"
timeout /t 2 /nobreak >nul

start "Servidor Salida" cmd /k "cd /d %~dp0\src && python server_salida.py"
timeout /t 2 /nobreak >nul

echo Esperando a que los servidores se inicien...
timeout /t 3 /nobreak >nul

start "Middleware - Motor de Fisica" cmd /k "cd /d %~dp0\src && python middleware.py"
timeout /t 3 /nobreak >nul

start "Web SCADA" cmd /k "cd /d %~dp0\src && python web_app.py"
timeout /t 2 /nobreak >nul

start "Visor de Datos" cmd /k "cd /d %~dp0\src && python ver_datos.py"

echo.
echo ========================================
echo Todos los componentes iniciados
echo.
echo Web SCADA: http://localhost:5000
echo ========================================
echo.
echo Abriendo navegador...
timeout /t 8 /nobreak >nul
start http://localhost:5000
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
