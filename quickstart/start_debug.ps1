param(
    [int]$ApiPort = 8000,
    [int]$StreamlitPort = 8501
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Python = "python"
$ApiUrl = "http://127.0.0.1:$ApiPort"
$FrontendUrl = "http://127.0.0.1:$StreamlitPort"
$LogDir = Join-Path $ProjectRoot ".run_logs"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-HttpOk {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    }
    catch {
        return $false
    }
}

function Test-PortListening {
    param([int]$Port)
    $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Start-HuhuProcess {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [string]$StdoutName,
        [string]$StderrName
    )

    $stdout = Join-Path $LogDir $StdoutName
    $stderr = Join-Path $LogDir $StderrName
    $process = Start-Process `
        -FilePath $Python `
        -ArgumentList $Arguments `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
    Write-Host "$Name started. PID=$($process.Id)"
}

function Wait-Http {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk -Url $Url) {
            Write-Host "$Name is ready: $Url"
            return $true
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "$Name did not respond within $TimeoutSeconds seconds: $Url"
    return $false
}

Write-Host "Project: $ProjectRoot"

if (-not (Test-HttpOk -Url "$ApiUrl/docs")) {
    if (Test-PortListening -Port $ApiPort) {
        Write-Host "Port $ApiPort is already in use. API may be running at $ApiUrl"
    }
    else {
        Start-HuhuProcess `
            -Name "API" `
            -Arguments @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort") `
            -StdoutName "api.out.log" `
            -StderrName "api.err.log"
    }
}
else {
    Write-Host "API is already ready: $ApiUrl"
}

if (-not (Test-HttpOk -Url $FrontendUrl)) {
    if (Test-PortListening -Port $StreamlitPort) {
        Write-Host "Port $StreamlitPort is already in use. Streamlit may be running at $FrontendUrl"
    }
    else {
        Start-HuhuProcess `
            -Name "Streamlit" `
            -Arguments @("-m", "streamlit", "run", "streamlit_app.py", "--server.address", "127.0.0.1", "--server.port", "$StreamlitPort", "--server.headless", "true") `
            -StdoutName "streamlit.out.log" `
            -StderrName "streamlit.err.log"
    }
}
else {
    Write-Host "Streamlit is already ready: $FrontendUrl"
}

$apiReady = Wait-Http -Name "API" -Url "$ApiUrl/docs" -TimeoutSeconds 45
$frontendReady = Wait-Http -Name "Streamlit" -Url $FrontendUrl -TimeoutSeconds 60

if ($frontendReady) {
    Start-Process $FrontendUrl
}
elseif ($apiReady) {
    Start-Process "$ApiUrl/docs"
}

Write-Host ""
Write-Host "Frontend: $FrontendUrl"
Write-Host "Swagger:  $ApiUrl/docs"
Write-Host "Logs:     $LogDir"

