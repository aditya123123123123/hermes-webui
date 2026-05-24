#!/usr/bin/env bash
# start-remote.sh — Start Hermes WebUI bound to a remote-accessible interface.
#
# SAFE DEFAULT: binds to your Tailscale IP if available, so only devices on
# your Tailscale network can reach it.  Falls back to an explicit IP you set
# via HERMES_REMOTE_BIND_HOST, or 0.0.0.0 only when --all-interfaces is passed.
#
# Usage:
#   ./start-remote.sh                    # auto-detect Tailscale IP
#   ./start-remote.sh --all-interfaces   # bind 0.0.0.0 (LAN-wide, use with caution)
#   HERMES_REMOTE_BIND_HOST=192.168.1.5 ./start-remote.sh
#
# Set a password before exposing to the network:
#   HERMES_WEBUI_PASSWORD=yourpassword ./start-remote.sh
#   — or configure it in Settings after the first local startup.
#
# See docs/remote-access.md for SSH-tunnel and firewall guidance.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BIND_HOST="${HERMES_REMOTE_BIND_HOST:-}"
ALL_INTERFACES=0
PASSTHROUGH_ARGS=()

for arg in "$@"; do
  case "$arg" in
    --all-interfaces) ALL_INTERFACES=1 ;;
    *) PASSTHROUGH_ARGS+=("$arg") ;;
  esac
done

# ── Resolve bind address ─────────────────────────────────────────────────────

if [[ "$ALL_INTERFACES" -eq 1 ]]; then
  BIND_HOST="0.0.0.0"
  echo "[start-remote] WARNING: Binding to 0.0.0.0 — accessible on ALL local interfaces."
  echo "               Make sure firewall rules and/or a password protect this."
fi

if [[ -z "$BIND_HOST" ]]; then
  # Prefer Tailscale: smallest blast-radius (only TS peers can reach you).
  if command -v tailscale >/dev/null 2>&1; then
    TS_IP="$(tailscale ip -4 2>/dev/null || true)"
    if [[ -n "$TS_IP" ]]; then
      BIND_HOST="$TS_IP"
      echo "[start-remote] Detected Tailscale IP: $BIND_HOST"
    fi
  fi

  # If no Tailscale, look for the common Tailscale CGNAT range (100.64/10) in
  # ifconfig/ip output as a fallback for systems where the CLI isn't on PATH.
  if [[ -z "$BIND_HOST" ]]; then
    if command -v ip >/dev/null 2>&1; then
      TS_IP="$(ip -4 addr show 2>/dev/null \
               | grep -oE '100\.(6[4-9]|[7-9][0-9]|1[0-2][0-9])\.[0-9]+\.[0-9]+' \
               | head -1 || true)"
    elif command -v ifconfig >/dev/null 2>&1; then
      TS_IP="$(ifconfig 2>/dev/null \
               | grep -oE '100\.(6[4-9]|[7-9][0-9]|1[0-2][0-9])\.[0-9]+\.[0-9]+' \
               | head -1 || true)"
    fi
    if [[ -n "${TS_IP:-}" ]]; then
      BIND_HOST="$TS_IP"
      echo "[start-remote] Detected Tailscale CGNAT IP via interface scan: $BIND_HOST"
    fi
  fi
fi

if [[ -z "$BIND_HOST" ]]; then
  echo "[start-remote] ERROR: No Tailscale IP found and HERMES_REMOTE_BIND_HOST is unset."
  echo "  Options:"
  echo "    1. Install Tailscale (https://tailscale.com) for the safest remote access."
  echo "    2. Set HERMES_REMOTE_BIND_HOST=<your-LAN-ip> explicitly."
  echo "    3. Pass --all-interfaces to bind to 0.0.0.0 (use with a password + firewall)."
  exit 1
fi

PORT="${HERMES_WEBUI_PORT:-8787}"

# ── Password reminder ────────────────────────────────────────────────────────

if [[ -z "${HERMES_WEBUI_PASSWORD:-}" ]]; then
  echo "[start-remote] NOTICE: No HERMES_WEBUI_PASSWORD set."
  echo "               Anyone who can reach $BIND_HOST:$PORT can access your agent."
  echo "               Set it in your .env file or prefix: HERMES_WEBUI_PASSWORD=... ./start-remote.sh"
fi

echo "[start-remote] Starting on http://$BIND_HOST:$PORT"

export HERMES_WEBUI_HOST="$BIND_HOST"
export HERMES_WEBUI_PORT="$PORT"

if [[ ${#PASSTHROUGH_ARGS[@]} -gt 0 ]]; then
  exec "${REPO_ROOT}/start.sh" "${PASSTHROUGH_ARGS[@]}"
else
  exec "${REPO_ROOT}/start.sh"
fi
