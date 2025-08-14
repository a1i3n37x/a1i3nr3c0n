# AlienRecon Setup Guide for Fresh Ubuntu Install

## Quick Setup (2 Commands)

1. **Run system setup (requires sudo):**
   ```bash
   sudo ~/setup_alienrecon.sh
   ```

2. **Run user setup (no sudo):**
   ```bash
   ./setup_user.sh
   ```

## Manual Step: Configure OpenAI API Key

Edit the `.env` file and add your OpenAI API key:
```bash
nano .env
# Replace 'your-api-key-here' with your actual OpenAI API key
```

## Verify Installation

1. **Activate Poetry environment:**
   ```bash
   poetry shell
   ```

2. **Run doctor command:**
   ```bash
   alienrecon doctor
   ```

## What Gets Installed

### System Tools (via apt):
- Python 3.12+ (already installed)
- nmap - Network scanner
- hydra - Password brute-forcer
- smbclient - SMB client tools
- openssl - SSL/TLS tools
- Build dependencies

### Tools from GitHub:
- nikto - Web vulnerability scanner
- enum4linux-ng - SMB enumeration
- ffuf - Web fuzzer
- searchsploit - Exploit database search

### Python Tools:
- Poetry - Dependency management
- All Python dependencies via poetry.lock

## Common Issues

### Issue: Poetry not found after installation
**Solution:** Run `source ~/.bashrc` or open a new terminal

### Issue: Permission denied running tools
**Solution:** Make sure you ran the system setup with sudo

### Issue: OpenAI API errors
**Solution:** Verify your API key is correctly set in .env file

### Issue: Tool not found errors
**Solution:** Some tools require PATH updates. Try:
```bash
export PATH="/usr/local/bin:$PATH"
```

## Usage Examples

After setup, you can use AlienRecon:

```bash
# AI-guided reconnaissance
alienrecon recon --target 10.10.10.1

# Quick automated scan
alienrecon quick-recon --target 10.10.10.1

# Manual tool execution
alienrecon manual nmap --target 10.10.10.1
alienrecon manual nikto --target http://10.10.10.1

# Session management
alienrecon status
alienrecon save
alienrecon clear
```

## Docker Alternative

If you prefer Docker, you can use the included Docker setup:
```bash
./alienrecon-docker.sh build
./alienrecon-docker.sh run recon --target 10.10.10.1
```