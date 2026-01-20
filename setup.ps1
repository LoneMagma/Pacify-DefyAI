# setup.ps1 - Windows Installation Script for Pacify & Defy
# Usage: Right-click and "Run with PowerShell" OR execute: .\setup.ps1

# Requires PowerShell 5.0+
#Requires -Version 5.0

# Enable strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Failure { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Cyan }
function Write-Warn { Write-Host "⚠ $args" -ForegroundColor Yellow }

# ASCII Art Banner
function Show-Banner {
    Write-Host ""
    Write-Host "    ____             _ ____         ___      ____       ____       " -ForegroundColor Cyan
    Write-Host "   / __ \____ ______(_)___/   __   ( _ )    / __ \___  / __/_  __" -ForegroundColor Cyan
    Write-Host "  / /_/ / __ \`/ ___/ //   / / /  / __ |   / / / / _ \/ /_/ / / /" -ForegroundColor Cyan
    Write-Host " / ____/ /_/ / /__/ / __/ /_/ /  / /_/  | / /_/ /  __/ __/ /_/ / " -ForegroundColor Cyan
    Write-Host "/_/    \__,_/\___/_/_/  \__, /   \____/|_/_____/\___/_/  \__, /  " -ForegroundColor Cyan
    Write-Host "                       /____/                           /____/   " -ForegroundColor Cyan
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Blue
    Write-Host "              Dual-Mode Conversational AI System" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Blue
    Write-Host ""
}

# Check if running as Administrator
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($user)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check Python installation
function Test-Python {
    Write-Info "Checking Python installation..."
    
    $pythonCmd = $null
    
    # Try python3 first, then python
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    }
    
    if (-not $pythonCmd) {
        Write-Failure "Python not found!"
        Write-Host ""
        Write-Host "Please install Python 3.8 or higher from:" -ForegroundColor Yellow
        Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Make sure to check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
        exit 1
    }
    
    $version = & $pythonCmd --version 2>&1
    Write-Success "Python found: $version"
    
    return $pythonCmd
}

# Check pip installation
function Test-Pip {
    param($PythonCmd)
    
    Write-Info "Checking pip installation..."
    
    $pipCmd = $null
    
    if (Get-Command pip3 -ErrorAction SilentlyContinue) {
        $pipCmd = "pip3"
    } elseif (Get-Command pip -ErrorAction SilentlyContinue) {
        $pipCmd = "pip"
    } else {
        Write-Warn "pip not found, installing..."
        & $PythonCmd -m ensurepip --upgrade
        $pipCmd = "$PythonCmd -m pip"
    }
    
    Write-Success "pip found"
    return $pipCmd
}

# Create virtual environment
function New-VirtualEnvironment {
    param($PythonCmd)
    
    Write-Info "Creating virtual environment..."
    
    if (Test-Path "venv") {
        Write-Warn "Virtual environment already exists"
    } else {
        & $PythonCmd -m venv venv
        Write-Success "Virtual environment created"
    }
    
    # Activate virtual environment
    $activateScript = "venv\Scripts\Activate.ps1"
    
    if (Test-Path $activateScript) {
        & $activateScript
        Write-Success "Virtual environment activated"
    } else {
        Write-Failure "Could not find activation script"
        exit 1
    }
}

# Install dependencies
function Install-Dependencies {
    Write-Info "Installing dependencies..."
    
    if (-not (Test-Path "requirements.txt")) {
        Write-Failure "requirements.txt not found!"
        exit 1
    }
    
    # Upgrade pip first
    python -m pip install --upgrade pip | Out-Null
    
    # Install requirements
    pip install -r requirements.txt
    
    Write-Success "All dependencies installed"
}

# Create directory structure
function New-DirectoryStructure {
    Write-Info "Creating directory structure..."
    
    $directories = @("data", "logs", "exports", "personas\pacify", "personas\defy")
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    # Create .gitkeep files
    @("data\.gitkeep", "logs\.gitkeep", "exports\.gitkeep") | ForEach-Object {
        New-Item -ItemType File -Path $_ -Force | Out-Null
    }
    
    Write-Success "Directory structure created"
}

# Configure Groq API
function Set-ApiConfiguration {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════=" -ForegroundColor Cyan
    Write-Host "                  API CONFIGURATION" -ForegroundColor Yellow
    Write-Host "═══════════════════════════════════════════════════════════=" -ForegroundColor Cyan
    Write-Host ""
    
    if (Test-Path ".env") {
        Write-Warn ".env file already exists"
        $response = Read-Host "Overwrite existing configuration? [y/N]"
        
        if ($response -notmatch '^[Yy]$') {
            Write-Info "Keeping existing configuration"
            return
        }
    }
    
    Write-Host "You need a Groq API key to use this system." -ForegroundColor Blue
    Write-Host "Get your free API key at: " -ForegroundColor Blue -NoNewline
    Write-Host "https://console.groq.com/keys" -ForegroundColor Cyan
    Write-Host ""
    
    do {
        $groqKey = Read-Host "Enter your Groq API key"
        
        if ([string]::IsNullOrWhiteSpace($groqKey)) {
            Write-Failure "API key cannot be empty!"
            continue
        }
        
        # Basic validation
        if (-not $groqKey.StartsWith("gsk_")) {
            Write-Warn "This doesn't look like a valid Groq API key (should start with 'gsk_')"
            $response = Read-Host "Use it anyway? [y/N]"
            
            if ($response -notmatch '^[Yy]$') {
                continue
            }
        }
        
        break
    } while ($true)
    
    # Create .env file
    @"
# Groq API Configuration
GROQ_API_KEY=$groqKey

# Optional: Enable debug mode
# PACIFY_DEBUG=false
"@ | Out-File -FilePath ".env" -Encoding UTF8
    
    Write-Success "API key configured successfully"
}

# Create launcher script
function New-LauncherScript {
    Write-Info "Creating launcher script..."
    
    $installDir = Get-Location
    
    # Create PowerShell launcher
    @"
# Pacify & Defy Launcher
Set-Location "$installDir"
& "$installDir\venv\Scripts\Activate.ps1"
python -m cli
deactivate
"@ | Out-File -FilePath "pacify-defy.ps1" -Encoding UTF8
    
    # Create batch launcher for compatibility
    @"
@echo off
cd /d "$installDir"
call venv\Scripts\activate.bat
python -m cli
call deactivate
"@ | Out-File -FilePath "pacify-defy.bat" -Encoding ASCII
    
    Write-Success "Launcher scripts created"
}

# Setup PowerShell alias
function Set-PowerShellAlias {
    Write-Info "Setting up global PowerShell alias..."
    
    $installDir = Get-Location
    $profilePath = $PROFILE.CurrentUserAllHosts
    
    # Create profile directory if it doesn't exist
    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    
    # Create profile if it doesn't exist
    if (-not (Test-Path $profilePath)) {
        New-Item -ItemType File -Path $profilePath -Force | Out-Null
    }
    
    # Check if alias already exists
    $aliasExists = Select-String -Path $profilePath -Pattern "pacify-defy" -Quiet 2>$null
    
    if ($aliasExists) {
        Write-Warn "Alias already exists in PowerShell profile"
        return
    }
    
    # Add alias to profile
    @"

# Pacify & Defy - Global Command
function pacify-defy {
    & "$installDir\pacify-defy.ps1"
}
"@ | Add-Content -Path $profilePath
    
    Write-Success "Alias added to PowerShell profile: $profilePath"
}

# Add to PATH (optional)
function Add-ToPath {
    Write-Info "Adding to system PATH..."
    
    $installDir = Get-Location
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    
    if ($currentPath -like "*$installDir*") {
        Write-Warn "Already in PATH"
        return
    }
    
    $response = Read-Host "Add to User PATH for 'pacify-defy.bat' command? [Y/n]"
    
    if ($response -match '^[Nn]$') {
        Write-Info "Skipping PATH addition"
        return
    }
    
    $newPath = "$currentPath;$installDir"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    
    Write-Success "Added to User PATH"
    Write-Warn "You may need to restart your terminal for PATH changes to take effect"
}

# Verify installation
function Test-Installation {
    Write-Info "Verifying installation..."
    
    $requiredFiles = @(".env", "venv", "core", "personas", "requirements.txt")
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "$file exists"
        } else {
            Write-Failure "$file missing!"
            return $false
        }
    }
    
    # Check Python imports
    & venv\Scripts\Activate.ps1
    $imports = python -c "import requests, rich, pyfiglet" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "All Python packages installed correctly"
    } else {
        Write-Failure "Some Python packages are missing!"
        return $false
    }
    
    Write-Success "Installation verified successfully"
    return $true
}

# Show completion message
function Show-Completion {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "             ✓ INSTALLATION COMPLETE!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start using Pacify & Defy:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Reload PowerShell profile:" -ForegroundColor Yellow
    Write-Host "     " -NoNewline
    Write-Host ". `$PROFILE" -ForegroundColor Blue
    Write-Host ""
    Write-Host "  2. Run from anywhere:" -ForegroundColor Yellow
    Write-Host "     " -NoNewline
    Write-Host "pacify-defy" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Alternative methods:" -ForegroundColor Cyan
    Write-Host "  • PowerShell: " -NoNewline
    Write-Host ".\pacify-defy.ps1" -ForegroundColor Blue
    Write-Host "  • Command Prompt: " -NoNewline
    Write-Host "pacify-defy.bat" -ForegroundColor Blue
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor Cyan
    Write-Host "  • Type " -NoNewline
    Write-Host "/help" -ForegroundColor Yellow -NoNewline
    Write-Host " to see all commands"
    Write-Host "  • Type " -NoNewline
    Write-Host "/setmode defy" -ForegroundColor Yellow -NoNewline
    Write-Host " to switch to uncensored mode"
    Write-Host "  • Type " -NoNewline
    Write-Host "/persona sage" -ForegroundColor Yellow -NoNewline
    Write-Host " for task-oriented coding"
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
}

# Main installation flow
function Main {
    try {
        Show-Banner
        
        # Check for admin rights (optional warning)
        if (-not (Test-Administrator)) {
            Write-Warn "Not running as Administrator (this is usually fine)"
            Write-Warn "If installation fails, try running as Administrator"
            Write-Host ""
        }
        
        $pythonCmd = Test-Python
        $pipCmd = Test-Pip -PythonCmd $pythonCmd
        
        New-VirtualEnvironment -PythonCmd $pythonCmd
        Install-Dependencies
        New-DirectoryStructure
        Set-ApiConfiguration
        New-LauncherScript
        Set-PowerShellAlias
        Add-ToPath
        
        if (Test-Installation) {
            Show-Completion
        } else {
            Write-Failure "Installation verification failed!"
            exit 1
        }
    }
    catch {
        Write-Failure "Installation failed: $_"
        Write-Host $_.ScriptStackTrace -ForegroundColor Red
        exit 1
    }
}

# Run main function
Main
