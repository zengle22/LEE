[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$url = "https://github.com/farion1231/cc-switch/releases/download/v3.10.1/CC-Switch-v3.10.1-Windows.msi"
$output = "$env:TEMP\CC-Switch-Windows.msi"

Write-Host "Downloading cc-switch v3.10.1..."
Write-Host "From: $url"
Write-Host "To: $output"

try {
    Invoke-WebRequest -Uri $url -OutFile $output -UseBasicParsing
    $fileInfo = Get-Item $output
    Write-Host "`nDownload successful!"
    Write-Host "File: $($fileInfo.Name)"
    Write-Host "Size: $($fileInfo.Length) bytes"
    Write-Host "Path: $($fileInfo.FullName)"
    Write-Host "`nTo install, run: msiexec /i `"$($fileInfo.FullName)`""
    exit 0
} catch {
    Write-Host "`nDownload failed: $_" -ForegroundColor Red
    exit 1
}
