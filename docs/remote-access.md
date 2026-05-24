# Remote Access Guide

By default, Hermes WebUI binds to `127.0.0.1:8787` (loopback only). This page describes how to access it from another device without exposing it to the public internet.

---

## Option 1 — Tailscale (recommended)

[Tailscale](https://tailscale.com) creates an encrypted overlay network between your devices. Only authenticated Tailscale peers can reach your machine's Tailscale IP (`100.x.x.x`).

```bash
# Install Tailscale, authenticate once, then:
./start-remote.sh
# Output: [start-remote] Starting on http://100.x.x.x:8787
```

`start-remote.sh` auto-detects your Tailscale IP and binds to it. Open `http://100.x.x.x:8787` on any device in your Tailscale network.

**Set a password** before sharing your Tailscale IP with others:

```bash
HERMES_WEBUI_PASSWORD=yourpassword ./start-remote.sh
# or add to .env:
echo "HERMES_WEBUI_PASSWORD=yourpassword" >> .env
```

---

## Option 2 — SSH tunnel (zero extra setup)

Forward a port from a remote machine over an existing SSH connection. No server-side config changes needed — keep the WebUI on `127.0.0.1`.

```bash
# On the remote/client machine:
ssh -L 8787:127.0.0.1:8787 user@your-server

# Then open http://localhost:8787 in the remote browser.
```

Add `-N -f` to run the tunnel in the background:

```bash
ssh -N -f -L 8787:127.0.0.1:8787 user@your-server
```

The tunnel inherits SSH's authentication — no WebUI password needed, but you should still set one for defense-in-depth.

---

## Option 3 — Explicit LAN/Tailscale IP

If Tailscale is not installed but you know the interface IP you want:

```bash
HERMES_REMOTE_BIND_HOST=192.168.1.42 ./start-remote.sh
```

Use your machine's static LAN IP so the address doesn't change between reboots. Restrict access with a firewall rule allowing only specific source IPs.

---

## Option 4 — Bind all interfaces (0.0.0.0)

Use only on a trusted LAN or behind a firewall that blocks external access to port 8787.

```bash
HERMES_WEBUI_PASSWORD=yourpassword ./start-remote.sh --all-interfaces
# Binds to 0.0.0.0:8787 — reachable on every local interface.
```

Without a password, anyone on the same network can read your sessions and invoke your agent.

---

## TLS / HTTPS (optional)

For HTTPS, generate a self-signed cert or use `mkcert`:

```bash
mkcert 100.x.x.x   # or your hostname
# Produces: 100.x.x.x.pem  100.x.x.x-key.pem

HERMES_WEBUI_TLS_CERT=100.x.x.x.pem \
HERMES_WEBUI_TLS_KEY=100.x.x.x-key.pem \
HERMES_REMOTE_BIND_HOST=100.x.x.x \
./start-remote.sh
# URL: https://100.x.x.x:8787
```

---

## Environment variables reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `HERMES_WEBUI_HOST` | `127.0.0.1` | Bind address (set automatically by `start-remote.sh`) |
| `HERMES_WEBUI_PORT` | `8787` | Port |
| `HERMES_WEBUI_PASSWORD` | _(unset)_ | Enable auth; required for non-loopback exposure |
| `HERMES_REMOTE_BIND_HOST` | _(unset)_ | Override the IP `start-remote.sh` binds to |
| `HERMES_WEBUI_TLS_CERT` | _(unset)_ | Path to TLS certificate (enables HTTPS) |
| `HERMES_WEBUI_TLS_KEY` | _(unset)_ | Path to TLS private key |

All variables can be placed in `.env` in the repo root (sourced automatically by `start.sh` and `start-remote.sh`).

---

## Firewall note

On macOS, the system firewall does **not** block LAN traffic by default when a process is already bound. If you bind to `0.0.0.0`, consider restricting access at the router level or using Tailscale ACLs instead of relying on the OS firewall alone.
