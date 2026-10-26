@echo off
setlocal
cd /d "%~dp0"
set "SZERO_LAN_NATIVE_TRACE=1"
echo Native session capture only - this does not redirect Online to the LAN server.
echo Run Set up / update game, then Launch game. Use Battle - Online, not F5.
call "%~dp0Start-Client.cmd"
endlocal
