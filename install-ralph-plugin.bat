@echo off
echo ============================================
echo Installing Ralph Wiggum Plugin
echo ============================================
echo.
echo This will open Claude Code CLI.
echo When it starts, type exactly:
echo.
echo   /plugin install ralph-loop@claude-plugins-official
echo.
echo Then press Enter and wait for installation.
echo After it's done, type: /plugin list
echo To verify it installed correctly.
echo.
echo Press any key to continue...
pause >nul

cd /d "%~dp0"
claude
