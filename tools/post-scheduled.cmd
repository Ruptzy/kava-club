@echo off
REM Nudges the Scheduled posts workflow at the minute a scheduled Lenny message is due
REM (scheduled-posts.json). A Windows scheduled task runs this; the workflow itself decides
REM what is due and never posts anything twice. No secrets here: the Discord webhooks stay
REM GitHub secrets and the GitHub CLI login is the one already on this PC.
setlocal enabledelayedexpansion
set GH="%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe"
set LOGDIR=%LOCALAPPDATA%\KavaSocialTask
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set LOG=%LOGDIR%\scheduled-post.log
echo ==== %DATE% %TIME% >> "%LOG%"
if not exist "%APPDATA%\GitHub CLI\hosts.yml" (
  if not exist "%APPDATA%\GitHub CLI" mkdir "%APPDATA%\GitHub CLI"
  (
    echo github.com:
    echo     git_protocol: https
    echo     users:
    echo         Ruptzy:
    echo     user: Ruptzy
  ) > "%APPDATA%\GitHub CLI\hosts.yml"
  echo wrote the GitHub CLI account file >> "%LOG%"
)
for /L %%i in (1,1,6) do (
  %GH% workflow run scheduled-posts.yml --repo Ruptzy/kava-club >> "%LOG%" 2>&1
  if !ERRORLEVEL! EQU 0 (
    echo started on try %%i >> "%LOG%"
    exit /b 0
  )
  echo try %%i failed with !ERRORLEVEL! >> "%LOG%"
  timeout /t 60 /nobreak > nul
)
exit /b 1
