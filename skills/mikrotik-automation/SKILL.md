---
name: mikrotik-automation
description: Automate MikroTik RouterOS network monitoring, diagnostics, troubleshooting, and configuration via Hermes Agent.
version: 1.0.0
author: PTI MikroTik AI Team
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [networking, mikrotik, routeros, automation, diagnostics, telegram]
    category: devops
    requires_toolsets: [terminal]
environments:
  - cli
  - telegram
---

# MikroTik Automation Skill for Hermes Agent

This skill equips Hermes Agent to monitor, diagnose, troubleshoot, and safely configure MikroTik RouterOS devices across the network using natural language.

## When to Use

Use this skill when:
- The user requests router health, CPU, memory, uptime, or interface traffic checks.
- The user asks why the internet connection is slow ("Internet lambat", "Koneksi lemot").
- The user asks who is currently using the network (DHCP leases, ARP, active hotspot users).
- The user asks to create or delete hotspot users or toggle interface states.
- The user requests connectivity tests (ping to Google DNS, gateway, etc.).

## Command Tools

Use `terminal` tool to run the CLI tool:

```bash
# General query with natural language reasoning
python "skills/mikrotik-automation/scripts/mikrotik_cli.py" query "<user message>"

# Check system resources
python "skills/mikrotik-automation/scripts/mikrotik_cli.py" resource --device "Kantor Utama"

# Check interfaces and traffic
python "skills/mikrotik-automation/scripts/mikrotik_cli.py" interface --device "Kantor Utama"

# Ping test
python "skills/mikrotik-automation/scripts/mikrotik_cli.py" ping 8.8.8.8 --device "Kantor Utama"

# Hotspot active sessions
python "skills/mikrotik-automation/scripts/mikrotik_cli.py" hotspot --device "Kantor Utama" --type active

# Create hotspot user (requires user confirmation before committing)
python "skills/mikrotik-automation/scripts/mikrotik_cli.py" create-hotspot-user <name> --limit-uptime 1d

# Discover routers on subnet
python "skills/mikrotik-automation/scripts/mikrotik_cli.py" discover --subnet "10.20.33.0/24"
```

## Safety Rules

1. **Dangerous Operation Protection**:
   Never execute factory reset, reset-configuration, reboot, disk format, or wipe commands.
2. **Confirmation**:
   Always prompt the user for confirmation when executing configuration changes (adding/removing users, modifying interfaces).
3. **Credentials**:
   Never expose router passwords or sensitive tokens in the final user response.
