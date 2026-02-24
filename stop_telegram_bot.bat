@echo off
setlocal

echo ========================================
echo    Stop Tawasul Telegram Bot
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -like '*telegram_bot.bot*' }; if(-not $procs){ Write-Host 'No running telegram bot process found.'; exit 0 }; $count = 0; foreach($p in $procs){ try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; $count++; Write-Host ('Stopped PID ' + $p.ProcessId) } catch { Write-Host ('Failed to stop PID ' + $p.ProcessId) } }; Write-Host ('Stopped ' + $count + ' bot process(es).')"

echo.
echo Done.
