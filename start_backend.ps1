$ErrorActionPreference = 'Stop'

Write-Host '========================================' -ForegroundColor Cyan
Write-Host '   RAGMind Backend Server (PowerShell)' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

function Invoke-NativeChecked {
    param([Parameter(Mandatory = $true)][scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

function Test-CommandExists {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Wait-PostgresReady {
    param(
        [int]$MaxAttempts = 30,
        [int]$SleepSeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $postgresContainerId = Get-PostgresContainerId
            $health = docker inspect --format='{{.State.Health.Status}}' $postgresContainerId 2>$null
            if ($LASTEXITCODE -eq 0 -and $health -eq 'healthy') {
                Write-Host '[✓] PostgreSQL container is healthy' -ForegroundColor Green
                return
            }
        } catch {
            # ignore and retry
        }

        Write-Host "[INFO] Waiting for PostgreSQL readiness ($attempt/$MaxAttempts)..." -ForegroundColor Yellow
        Start-Sleep -Seconds $SleepSeconds
    }

    throw 'PostgreSQL container did not become healthy in time.'
}

function Wait-PostgresHostPort {
    param(
        [int]$Port,
        [int]$MaxAttempts = 30,
        [int]$SleepSeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $ok = Test-NetConnection -ComputerName '127.0.0.1' -Port $Port -WarningAction SilentlyContinue
            if ($ok.TcpTestSucceeded) {
                Write-Host "[OK] PostgreSQL host port 127.0.0.1:$Port is reachable" -ForegroundColor Green
                return
            }
        } catch {
            # ignore and retry
        }

        Write-Host "[INFO] Waiting for host port 127.0.0.1:$Port ($attempt/$MaxAttempts)..." -ForegroundColor Yellow
        Start-Sleep -Seconds $SleepSeconds
    }

    throw "PostgreSQL host port 127.0.0.1:$Port is not reachable."
}

function Ensure-PostgresPortBinding {
    param([int]$ExpectedHostPort)

    $postgresContainerId = Get-PostgresContainerId
    $portsJson = docker inspect $postgresContainerId --format='{{json .NetworkSettings.Ports}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($portsJson)) {
        throw 'Could not inspect postgres container network settings.'
    }

    $ports = $portsJson | ConvertFrom-Json
    $boundEntries = $ports.'5432/tcp'
    $hasExpectedBinding = $false

    if ($boundEntries) {
        foreach ($entry in $boundEntries) {
            if ($entry.HostPort -eq "$ExpectedHostPort") {
                $hasExpectedBinding = $true
                break
            }
        }
    }

    if (-not $hasExpectedBinding) {
        Write-Host "[WARN] postgres service is missing host port binding on $ExpectedHostPort. Recreating postgres service..." -ForegroundColor Yellow
        Invoke-NativeChecked { docker compose up -d --force-recreate --no-deps postgres }
    }
}

function Get-PostgresContainerId {
    $composeRaw = docker compose ps -q postgres 2>$null | Select-Object -First 1
    $containerId = if ($null -eq $composeRaw) { '' } else { "$composeRaw".Trim() }
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($containerId)) {
        return $containerId
    }

    $fallbackRaw = docker ps --filter "name=ragmind-postgres" --format "{{.ID}}" 2>$null | Select-Object -First 1
    $containerId = if ($null -eq $fallbackRaw) { '' } else { "$fallbackRaw".Trim() }
    if (-not [string]::IsNullOrWhiteSpace($containerId)) {
        return $containerId
    }

    throw 'Could not resolve postgres container ID from docker compose.'
}

function Get-DatabaseHostPort {
    $databaseUrl = $env:DATABASE_URL

    if ([string]::IsNullOrWhiteSpace($databaseUrl) -and (Test-Path '.env')) {
        $line = Get-Content '.env' | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1
        if ($line) {
            $databaseUrl = ($line -split '=', 2)[1].Trim()
        }
    }

    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        return 5555
    }

    if ($databaseUrl -match '@[^:]+:(\d+)/') {
        return [int]$Matches[1]
    }

    return 5432
}

function Test-LocalPortAvailable {
    param([int]$Port)

    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Get-AvailablePort {
    param([int[]]$Candidates)

    foreach ($candidate in $Candidates) {
        if (Test-LocalPortAvailable -Port $candidate) {
            return $candidate
        }
    }

    throw 'No available PostgreSQL host port found in candidate list.'
}

function Set-DatabaseUrlPort {
    param(
        [string]$DatabaseUrl,
        [int]$Port
    )

    if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
        $dbUser = if ([string]::IsNullOrWhiteSpace($env:POSTGRES_USER)) { 'ragmind' } else { $env:POSTGRES_USER }
        $dbPass = if ([string]::IsNullOrWhiteSpace($env:POSTGRES_PASSWORD)) { '' } else { $env:POSTGRES_PASSWORD }
        $auth = if ([string]::IsNullOrWhiteSpace($dbPass)) { $dbUser } else { "{0}:{1}" -f $dbUser, $dbPass }
        return "postgresql+asyncpg://$auth@localhost:$Port/ragmind"
    }

    if ($DatabaseUrl -match '@([^/:]+):(\d+)/(.*)$') {
        $dbHost = $Matches[1]
        $replacement = "@{0}:{1}/" -f $dbHost, $Port
        return ($DatabaseUrl -replace '@[^/]+/', $replacement)
    }

    return $DatabaseUrl
}

function Get-DatabaseUrlRaw {
    $databaseUrl = $env:DATABASE_URL
    if (-not [string]::IsNullOrWhiteSpace($databaseUrl)) {
        return $databaseUrl
    }

    if (Test-Path '.env') {
        $line = Get-Content '.env' | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1
        if ($line) {
            return ($line -split '=', 2)[1].Trim()
        }
    }

    return ''
}

if (-not (Test-CommandExists -Name 'docker')) {
    throw 'Docker is not installed. Please install Docker Desktop first.'
}

try {
    docker info | Out-Null
} catch {
    throw 'Docker Desktop is not running. Start Docker Desktop and retry.'
}

Write-Host '[INFO] Resolving PostgreSQL host port...' -ForegroundColor Yellow
$databaseUrlRaw = Get-DatabaseUrlRaw
$requestedDbPort = Get-DatabaseHostPort
$fallbackPorts = @(5544, 5545, 5546, 5547, 5550) + (5700..5720)
$dbPort = Get-AvailablePort -Candidates (@($requestedDbPort) + $fallbackPorts)
if ($dbPort -ne $requestedDbPort) {
    Write-Host "[WARN] Requested PostgreSQL host port $requestedDbPort is not available. Using $dbPort instead." -ForegroundColor Yellow
}

$env:POSTGRES_HOST_PORT = "$dbPort"
$env:DATABASE_URL = Set-DatabaseUrlPort -DatabaseUrl $databaseUrlRaw -Port $dbPort

Write-Host '[INFO] Ensuring Docker services are running...' -ForegroundColor Yellow
Invoke-NativeChecked { docker compose up -d }

Ensure-PostgresPortBinding -ExpectedHostPort $dbPort
Wait-PostgresReady
Wait-PostgresHostPort -Port $dbPort
Write-Host ''

if (-not (Test-CommandExists -Name 'uv')) {
    throw 'uv is not installed. Install from https://docs.astral.sh/uv/getting-started/installation/'
}

if (-not (Test-Path -Path 'venv')) {
    Write-Host '[INFO] Creating virtual environment...' -ForegroundColor Yellow
    Invoke-NativeChecked { uv venv venv }
}

Write-Host '[INFO] Activating virtual environment...' -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

Write-Host '[INFO] Installing/updating backend dependencies...' -ForegroundColor Yellow
Invoke-NativeChecked { uv pip install -r .\backend\requirements.txt }

Write-Host '[INFO] Initializing database schema...' -ForegroundColor Yellow
Invoke-NativeChecked { python .\backend\init_database.py }

Write-Host '[INFO] Cleaning old listeners on ports 8500 and 3000...' -ForegroundColor Yellow
$ports = @(8500, 3000)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        try {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        } catch {
            # ignore failures for already terminated processes
        }
    }
}

Write-Host '[INFO] Starting frontend static server on http://localhost:3000' -ForegroundColor Yellow
$frontendPath = Join-Path $PSScriptRoot 'frontend'
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location -LiteralPath '$frontendPath'; python -m http.server 3000"
Start-Process 'http://localhost:3000'

Write-Host ''
Write-Host 'Starting FastAPI server on http://127.0.0.1:8500' -ForegroundColor Green
Write-Host 'Docs: http://127.0.0.1:8500/docs' -ForegroundColor Green
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8500
