@echo off
rem Lanzador de rama para PowerShell y CMD en Windows (Q161): corre el ejecutable de esta arquitectura que esta en
rem esta carpeta, rama-windows-<arch>.exe, con los argumentos tal cual. Sin ejecutable para la arquitectura, sale
rem con 3. Un proceso de 32 bits ve x86 en PROCESSOR_ARCHITECTURE y la del sistema en PROCESSOR_ARCHITEW6432.
setlocal DisableDelayedExpansion
set "rama_arch=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "rama_arch=%PROCESSOR_ARCHITEW6432%"
set "rama_exe="
if /i "%rama_arch%"=="AMD64" set "rama_exe=%~dp0rama-windows-amd64.exe"
if /i "%rama_arch%"=="ARM64" set "rama_exe=%~dp0rama-windows-arm64.exe"
if not defined rama_exe goto sin_ejecutable
if not exist "%rama_exe%" goto sin_ejecutable
"%rama_exe%" %*
exit /b %ERRORLEVEL%

:sin_ejecutable
>&2 echo rama: no hay ejecutable para esta plataforma (Windows "%rama_arch%"): falta "%~dp0rama-windows-%rama_arch%.exe". Hay para windows en amd64 y arm64.
exit /b 3
