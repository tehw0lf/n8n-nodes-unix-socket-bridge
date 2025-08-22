# Security Guide for Unix Socket Bridge

This document provides comprehensive security guidance for using the Unix Socket Bridge system securely in production environments.

## 🔐 Authentication Security

The Unix Socket Bridge supports secure token-based authentication with multiple layers of protection:

### 1. **Secure Token Hashing (Recommended)**

The system uses SHA-256 hashing to ensure tokens are never transmitted in plain text over Unix sockets.

**How it works:**
- Client (n8n node) hashes the token before sending
- Server stores and compares hashed tokens only
- Plain text tokens are never logged or stored on server

### 2. **Environment Variable Storage**

Store authentication tokens securely using environment variables:

```bash
# Secure approach - store hashed token on server (REQUIRED)
export AUTH_TOKEN_HASH="your-sha256-hash-here"
```

⚠️ **Plain text token support has been REMOVED for security reasons. Only hashed tokens are supported.**

### 3. **Token Generation and Management**

Use the provided utility to generate secure tokens:

```bash
# Generate a random secure token and its hash
python3 server/generate-token-hash.py --random

# Hash an existing token
python3 server/generate-token-hash.py "your-existing-token"

# Interactive mode (token won't appear in shell history)
python3 server/generate-token-hash.py --interactive
```

## 🛡️ Authentication Setup Guide

### Step 1: Generate Secure Token

```bash
cd server
python3 generate-token-hash.py --random
```

This outputs:
- **Token**: Use in n8n credentials (keep secret!)
- **SHA-256 Hash**: Use in server environment variable

### Step 2: Configure Server

**Option A: Configuration File with Environment Variable (Recommended)**
```json
{
  "auth_enabled": true,
  "commands": { ... }
}
```
```bash
export AUTH_TOKEN_HASH="d3ba8af26682896ea7a3305e4bc76b2c1ad1a2778d5569e66859113d5ccf7926"
python3 /usr/local/bin/unix-socket-server config.json
```

**Option B: Configuration File Only**
```json
{
  "auth_enabled": true,
  "auth_token_hash": "d3ba8af26682896ea7a3305e4bc76b2c1ad1a2778d5569e66859113d5ccf7926",
  "commands": { ... }
}
```

**Option C: No Authentication (Development/Testing)**
```json
{
  "auth_enabled": false,
  "commands": { ... }
}
```

### Step 3: Configure n8n Node

**Option A: Credentials (Recommended)**
1. Create "HTTP Header Auth" credential in n8n
2. Set "Value" field to your plain text token
3. Select this credential in the Unix Socket Bridge node

~~**Option B: Direct Token Field (REMOVED)**~~
❌ **Direct token fields have been removed for security. Use credentials only.**

## 🚨 Security Features

### Rate Limiting
- **Failed Authentication Attempts**: Default 5 attempts per 60 seconds
- **Request Rate Limiting**: Default 30 requests per 60 seconds
- **Configurable Limits**: Environment variables or config file

```bash
export AUTH_MAX_ATTEMPTS=5
export AUTH_WINDOW_SECONDS=60
export AUTH_BLOCK_DURATION=60
```

### Input Validation
- **Command Allowlisting**: Only predefined commands can be executed
- **Parameter Validation**: Regex patterns validate all parameters
- **Path Restrictions**: Executable paths must be in allowed directories (`allowed_executable_dirs`)
- **Size Limits**: Request and response size limits prevent DoS
- **Security Requirement**: All configurations must include `allowed_executable_dirs` field

### Logging and Monitoring
- **Authentication Events**: All auth attempts are logged
- **Rate Limiting Events**: Blocked clients are logged
- **Command Execution**: All executed commands are logged
- **Security Events**: Failed validations and attacks are logged

## 🔒 Security Best Practices

### Token Management
- ✅ **Use environment variables** for token storage
- ✅ **Generate cryptographically random tokens** (32+ characters)
- ✅ **Rotate tokens regularly** (monthly/quarterly)
- ✅ **Use different tokens** for different environments
- ❌ **Never commit tokens** to version control
- ❌ **Never log tokens** in plain text
- ❌ **Never share tokens** between systems

### Server Configuration
- ✅ **Enable authentication** in production (`AUTH_ENABLED=true`)
- ✅ **Use restrictive file permissions** for socket files
- ✅ **Limit executable directories** (`allowed_executable_dirs` - REQUIRED field)
- ✅ **Set appropriate timeouts** to prevent hanging processes
- ✅ **Enable rate limiting** to prevent abuse
- ✅ **Run with minimal privileges** (non-root user)
- ✅ **Include all required fields** in configuration (name, socket_path, allowed_executable_dirs, commands)

### Network Security
- ✅ **Use Unix domain sockets** (more secure than TCP)
- ✅ **Set restrictive socket permissions** (e.g., 0600)
- ✅ **Place socket files** in secure directories
- ✅ **Monitor socket file access** with system tools
- ❌ **Never expose sockets** over network filesystems

### Command Security
- ✅ **Use command allowlisting** (predefined commands only)
- ✅ **Validate all parameters** with regex patterns
- ✅ **Use absolute paths** for executables
- ✅ **Set command timeouts** to prevent hanging
- ✅ **Sanitize command arguments** to prevent injection
- ❌ **Never allow arbitrary command execution**

## 🏭 Production Deployment

### Environment Setup
```bash
# Authentication (choose one)
export AUTH_ENABLED=true
export AUTH_TOKEN_HASH="your-secure-hash"

# Rate limiting
export AUTH_MAX_ATTEMPTS=3
export AUTH_WINDOW_SECONDS=60
export AUTH_BLOCK_DURATION=300

# Server limits
export MAX_REQUEST_SIZE=1048576    # 1MB
export MAX_OUTPUT_SIZE=100000      # 100KB

# Logging
export LOG_LEVEL=WARNING           # Reduce log verbosity
```

### Service Configuration

#### User Services (Recommended)

For user-specific services with access to user sessions:

```bash
# Install the user service template
sudo cp systemd/socket-bridge-user@.service /etc/systemd/user/
sudo systemctl daemon-reload

# Create user configuration directory
mkdir -p ~/.config/socket-bridge

# Copy your secure configuration
cp examples/playerctl-secure.json ~/.config/socket-bridge/

# Set authentication token hash
echo "AUTH_TOKEN_HASH=your-secure-hash" > ~/.config/socket-bridge/.env

# Enable and start the service
systemctl --user enable socket-bridge-user@playerctl-secure.service
systemctl --user start socket-bridge-user@playerctl-secure.service
```

#### System Services (Alternative)

For system-wide services:

```bash
# Create systemd service
sudo cp server/socket-server.py /usr/local/bin/unix-socket-server
sudo chmod +x /usr/local/bin/unix-socket-server

# Create service file
sudo tee /etc/systemd/system/unix-socket-bridge.service << EOF
[Unit]
Description=Unix Socket Bridge Server
After=network.target

[Service]
Type=simple
User=your-username
Group=your-group
WorkingDirectory=/opt/unix-socket-bridge
ExecStart=/usr/local/bin/unix-socket-server /opt/unix-socket-bridge/config.json
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

# Environment variables for DBUS access (if needed)
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
EnvironmentFile=/opt/unix-socket-bridge/.env

[Install]
WantedBy=multi-user.target
EOF
```

### Monitoring and Alerting
```bash
# Monitor authentication failures (user service)
journalctl --user -u socket-bridge-user@yourconfig.service -f | grep "Failed authentication"

# Monitor rate limiting events (user service)
journalctl --user -u socket-bridge-user@yourconfig.service -f | grep "rate_limited"

# Monitor authentication failures (system service)
journalctl -u unix-socket-bridge.service -f | grep "Failed authentication"

# Monitor socket file permissions
ls -la /tmp/socket-bridge/*.sock
```

## 🚩 Security Incident Response

### Suspicious Activity Detection
1. **Multiple Authentication Failures**: Check logs for repeated failed attempts
2. **Rate Limiting Triggers**: Investigate blocked clients
3. **Unusual Command Patterns**: Review executed commands
4. **Socket File Access**: Monitor file system access logs

### Incident Response Steps
1. **Immediate**: Rotate authentication tokens
2. **Analysis**: Review server logs for attack patterns
3. **Mitigation**: Block malicious clients at firewall level
4. **Recovery**: Restart services with new tokens
5. **Prevention**: Update rate limiting and validation rules

## 📋 Security Checklist

### Pre-Production
- [ ] Authentication enabled with secure tokens
- [ ] Tokens stored in environment variables (not config files)
- [ ] Rate limiting configured appropriately
- [ ] Command allowlisting validated
- [ ] Parameter validation regex tested
- [ ] Socket file permissions set correctly
- [ ] Service runs with minimal privileges
- [ ] Logging configured for security events
- [ ] All configurations include `allowed_executable_dirs` field
- [ ] User systemd services configured (recommended)
- [ ] CLI client testing completed

### Production Monitoring
- [ ] Authentication failure alerts configured
- [ ] Rate limiting events monitored
- [ ] Token rotation schedule established
- [ ] Backup authentication tokens prepared
- [ ] Incident response procedures documented
- [ ] Security logs reviewed regularly

## 🔗 Related Documentation

- [Main README](README.md) - Setup and basic usage
- [Server Configuration](server/README.md) - Advanced server configuration
- [n8n Node Documentation](n8n-node/README.md) - Node-specific configuration
- [Examples](examples/) - Configuration examples

## 🚨 Vulnerability Reporting

If you discover security vulnerabilities, please report them responsibly:
- **Do not** create public issues for security bugs
- Contact the maintainers privately
- Allow reasonable time for fixes before disclosure