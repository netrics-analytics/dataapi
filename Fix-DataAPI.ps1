<#
.SYNOPSIS
    Diagnostic and fix script for dataapi Flask application on IIS

.DESCRIPTION
    This script diagnoses and fixes common issues with the Flask/FastCGI application
    that serves the MarketStorm conversion data API.

.NOTES
    Run this script as Administrator on the Windows IIS server
#>

[CmdletBinding()]
param(
    [switch]$DiagnoseOnly,
    [switch]$AutoFix
)

$ErrorActionPreference = "Continue"
$AppPath = "C:\inetpub\wwwroot\dataapi"
$LogFile = "$AppPath\diagnostic_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check if running as Administrator
if (-not (Test-Administrator)) {
    Write-Error "This script must be run as Administrator!"
    exit 1
}

Write-Log "=== DataAPI Diagnostic Script Started ===" "INFO"
Write-Log "Log file: $LogFile"

# 1. Check if dataapi directory exists
Write-Log "Checking application directory: $AppPath"
if (-not (Test-Path $AppPath)) {
    Write-Log "ERROR: Application directory not found!" "ERROR"
    exit 1
} else {
    Write-Log "Application directory exists" "SUCCESS"
}

# 2. Check Python virtual environment
Write-Log "Checking Python virtual environment..."
$pythonExe = "$AppPath\FlaskWebVenv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Log "ERROR: Python executable not found at $pythonExe" "ERROR"
} else {
    Write-Log "Python executable found" "SUCCESS"
    try {
        $pythonVersion = & $pythonExe --version 2>&1
        Write-Log "Python version: $pythonVersion" "INFO"
    } catch {
        Write-Log "ERROR: Cannot execute Python: $_" "ERROR"
    }
}

# 3. Check main Flask application file
Write-Log "Checking Flask application file..."
$flaskApp = "$AppPath\flaskIIS.py"
if (-not (Test-Path $flaskApp)) {
    Write-Log "ERROR: Flask application file not found!" "ERROR"
} else {
    Write-Log "Flask application file exists" "SUCCESS"
}

# 4. Check web.config
Write-Log "Checking web.config..."
$webConfig = "$AppPath\web.config"
if (-not (Test-Path $webConfig)) {
    Write-Log "ERROR: web.config not found!" "ERROR"
} else {
    Write-Log "web.config exists" "SUCCESS"
    $configContent = Get-Content $webConfig -Raw
    Write-Log "web.config content preview:" "INFO"
    Write-Log $configContent.Substring(0, [Math]::Min(500, $configContent.Length)) "INFO"
}

# 5. Check IIS Application Pool
Write-Log "Checking IIS Application Pool..."
try {
    Import-Module WebAdministration -ErrorAction Stop

    # Find the app pool for this application
    $site = Get-Website | Where-Object { $_.PhysicalPath -like "*dataapi*" }

    if ($site) {
        Write-Log "Found IIS site: $($site.Name)" "SUCCESS"
        $appPool = $site.ApplicationPool
        Write-Log "Application Pool: $appPool" "INFO"

        $appPoolObj = Get-Item "IIS:\AppPools\$appPool" -ErrorAction SilentlyContinue
        if ($appPoolObj) {
            Write-Log "App Pool State: $($appPoolObj.State)" "INFO"
            Write-Log "App Pool Identity: $($appPoolObj.ProcessModel.IdentityType)" "INFO"

            if ($appPoolObj.State -ne "Started") {
                Write-Log "WARNING: Application Pool is not running!" "WARN"
                if ($AutoFix) {
                    Write-Log "Attempting to start Application Pool..." "INFO"
                    Start-WebAppPool -Name $appPool
                    Start-Sleep -Seconds 3
                    Write-Log "Application Pool started" "SUCCESS"
                }
            }
        }
    } else {
        Write-Log "WARNING: Could not find IIS site for dataapi" "WARN"

        # List all sites
        Write-Log "Available IIS sites:" "INFO"
        Get-Website | ForEach-Object {
            Write-Log "  - $($_.Name): $($_.PhysicalPath)" "INFO"
        }
    }
} catch {
    Write-Log "ERROR checking IIS: $_" "ERROR"
}

# 6. Check FastCGI Configuration
Write-Log "Checking FastCGI configuration..."
try {
    $fastCgiConfig = & "$env:windir\system32\inetsrv\appcmd.exe" list config -section:system.webServer/fastCgi
    if ($fastCgiConfig -match "python.exe") {
        Write-Log "FastCGI Python handler found" "SUCCESS"
    } else {
        Write-Log "WARNING: No Python FastCGI handler found in configuration" "WARN"
    }
} catch {
    Write-Log "ERROR checking FastCGI: $_" "ERROR"
}

# 7. Check file permissions
Write-Log "Checking file permissions..."
try {
    $acl = Get-Acl $AppPath
    $hasIISPermissions = $acl.Access | Where-Object {
        $_.IdentityReference -like "*IIS_IUSRS*" -or
        $_.IdentityReference -like "*IUSR*" -or
        $_.IdentityReference -like "*IIS APPPOOL*"
    }

    if ($hasIISPermissions) {
        Write-Log "IIS user permissions found" "SUCCESS"
        $hasIISPermissions | ForEach-Object {
            Write-Log "  - $($_.IdentityReference): $($_.FileSystemRights)" "INFO"
        }
    } else {
        Write-Log "WARNING: No IIS user permissions found!" "WARN"
        if ($AutoFix) {
            Write-Log "Attempting to fix permissions..." "INFO"
            icacls $AppPath /grant "IIS_IUSRS:(OI)(CI)F" /T
            Write-Log "Permissions updated" "SUCCESS"
        }
    }
} catch {
    Write-Log "ERROR checking permissions: $_" "ERROR"
}

# 8. Check Event Logs for recent errors
Write-Log "Checking recent Event Log errors..."
try {
    $startDate = (Get-Date).AddDays(-7)

    # Check Application log
    $appErrors = Get-EventLog -LogName Application -After $startDate -EntryType Error |
        Where-Object { $_.Source -like "*FastCGI*" -or $_.Source -like "*IIS*" -or $_.Message -like "*python*" } |
        Select-Object -First 10

    if ($appErrors) {
        Write-Log "Recent Application errors found:" "WARN"
        $appErrors | ForEach-Object {
            Write-Log "  [$($_.TimeGenerated)] $($_.Source): $($_.Message.Substring(0, [Math]::Min(200, $_.Message.Length)))" "WARN"
        }
    } else {
        Write-Log "No recent FastCGI/IIS/Python errors in Application log" "INFO"
    }
} catch {
    Write-Log "Could not read Event Log: $_" "WARN"
}

# 9. Test Python application manually
Write-Log "Testing Flask application directly..."
if (Test-Path $pythonExe) {
    try {
        # Try to import the application
        $testScript = @"
import sys
sys.path.insert(0, r'$AppPath')
try:
    import flaskIIS
    print('SUCCESS: Flask application imports successfully')
except Exception as e:
    print(f'ERROR: Failed to import Flask application: {e}')
"@

        $testScriptPath = "$AppPath\test_import.py"
        $testScript | Out-File -FilePath $testScriptPath -Encoding UTF8

        $output = & $pythonExe $testScriptPath 2>&1
        Write-Log "Python import test: $output" "INFO"

        Remove-Item $testScriptPath -ErrorAction SilentlyContinue
    } catch {
        Write-Log "ERROR testing Python: $_" "ERROR"
    }
}

# 10. Check Python dependencies
Write-Log "Checking Python dependencies..."
if (Test-Path $pythonExe) {
    try {
        $pipList = & $pythonExe -m pip list 2>&1
        Write-Log "Installed packages:" "INFO"
        Write-Log $pipList "INFO"
    } catch {
        Write-Log "ERROR checking pip packages: $_" "ERROR"
    }
}

# 11. IIS Reset if AutoFix enabled
if ($AutoFix) {
    Write-Log "Performing IIS Reset..." "INFO"
    try {
        iisreset /restart
        Start-Sleep -Seconds 5
        Write-Log "IIS restarted successfully" "SUCCESS"
    } catch {
        Write-Log "ERROR during IIS reset: $_" "ERROR"
    }
}

# 12. Final connectivity test
Write-Log "Testing API endpoint connectivity..."
try {
    $testUrl = "http://localhost/iMarketSolutions/conversionJourney?startDate=2025-01-01&endDate=2025-01-02"
    $credentials = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("iMarketSolutions:4uN9GI8rphDT6mK"))

    $response = Invoke-WebRequest -Uri $testUrl -Headers @{Authorization = "Basic $credentials"} -UseBasicParsing -ErrorAction Stop

    if ($response.StatusCode -eq 200) {
        Write-Log "API endpoint test: SUCCESS (Status 200)" "SUCCESS"
    } else {
        Write-Log "API endpoint test: Unexpected status $($response.StatusCode)" "WARN"
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    Write-Log "API endpoint test FAILED: HTTP $statusCode" "ERROR"
    Write-Log "Error details: $($_.Exception.Message)" "ERROR"
}

Write-Log "=== Diagnostic Complete ===" "INFO"
Write-Log "Log saved to: $LogFile"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SUMMARY & NEXT STEPS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Log file: $LogFile" -ForegroundColor Yellow
Write-Host ""

if (-not $AutoFix) {
    Write-Host "Run with -AutoFix to automatically attempt repairs:" -ForegroundColor Yellow
    Write-Host "  .\Fix-DataAPI.ps1 -AutoFix" -ForegroundColor White
    Write-Host ""
    Write-Host "Manual fixes to try:" -ForegroundColor Yellow
    Write-Host "  1. Restart IIS: iisreset /restart" -ForegroundColor White
    Write-Host "  2. Fix permissions: icacls C:\inetpub\wwwroot\dataapi /grant 'IIS_IUSRS:(OI)(CI)F' /T" -ForegroundColor White
    Write-Host "  3. Check web.config FastCGI handler configuration" -ForegroundColor White
    Write-Host "  4. Review Event Viewer > Windows Logs > Application" -ForegroundColor White
}

Write-Host ""
