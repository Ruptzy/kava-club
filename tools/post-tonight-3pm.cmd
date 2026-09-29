@echo off
REM Nudges the Tonight on Discord workflow at 3pm Bradenton time, from this PC.
REM GitHub's own scheduler only executes a handful of the runs it is asked for, and
REM never at a predictable minute, so a Windows scheduled task does the timing instead.
REM No secrets live here: it uses the GitHub CLI login already on this machine, and the
REM Discord webhook stays a GitHub secret. The workflow still applies its own rules, so
REM nothing is posted twice and nothing is posted on a night with nothing on.
REM
REM It also starts the weekly email workflow, which hands the email to Brevo; Brevo sends
REM it at 6pm on Monday. The Brevo key stays a GitHub secret.
REM
REM Each job is tried up to six times, a minute apart, because a PC that has just woken
REM up may not have its network back yet. What happened is written to the log below.
setlocal enabledelayedexpansion
set GH="%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe"
set LOGDIR=%LOCALAPPDATA%\KavaSocialTask
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set LOG=%LOGDIR%\3pm-task.log
set FAILED=0
echo ==== %DATE% %TIME% >> "%LOG%"

REM The GitHub CLI was signed in from inside an app that keeps its own private copy of
REM this folder, so Windows itself never had the file that says which account to use.
REM It holds the account name only. The token is in Windows Credential Manager.
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

call :start tonight.yml
call :start weekly-email.yml
echo ---- finished, failed=%FAILED% >> "%LOG%"
exit /b %FAILED%

:start
for /L %%i in (1,1,6) do (
  %GH% workflow run %1 --repo Ruptzy/kava-club -f mode=auto >> "%LOG%" 2>&1
  if !ERRORLEVEL! EQU 0 (
    echo %1 started on try %%i >> "%LOG%"
    exit /b 0
  )
  echo %1 try %%i failed with !ERRORLEVEL! >> "%LOG%"
  timeout /t 60 /nobreak > nul
)
set FAILED=1
exit /b 1
