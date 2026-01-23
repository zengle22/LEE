$msiPath = "C:\Users\shado\AppData\Local\Temp\CC-Switch-Windows.msi"

Write-Host "Installing cc-switch v3.10.1..."
Write-Host "This will open an installation window."
Write-Host ""

# Check if file exists
if (-Not (Test-Path $msiPath)) {
    Write-Host "ERROR: Installer file not found at $msiPath" -ForegroundColor Red
    exit 1
}

try {
    # Start installation - this will open the GUI installer
    $process = Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`"" -PassThru

    Write-Host "Installation process started (PID: $($process.Id))"
    Write-Host ""
    Write-Host "If you don't see the installation window:"
    Write-Host "1. Check your taskbar for a new installer window"
    Write-Host "2. Look for 'Windows Installer' in Task Manager"
    Write-Host "3. Try running this command manually in an elevated PowerShell:"
    Write-Host "   msiexec /i `"$msiPath`""
    Write-Host ""
    Write-Host "Waiting for installation to complete..."

    # Wait for up to 2 minutes
    $process.WaitForExit(120000)

    if ($process.HasExited) {
        Write-Host ""
        Write-Host "Installation exit code: $($process.ExitCode)"
        if ($process.ExitCode -eq 0) {
            Write-Host "Installation completed successfully!" -ForegroundColor Green
        } else {
            Write-Host "Installation may have had issues (exit code: $($process.ExitCode))" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Installation is still running in GUI mode."
        Write-Host "Please complete the installation in the popup window."
    }

} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
}
