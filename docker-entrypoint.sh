#!/usr/bin/env bash
set -euo pipefail

print_help() {
  cat <<'EOF'
Usage:
  docker run --rm --network host \
    -e CH_RPC="http://127.0.0.1:8545" \
    -e CH_TXS=50 \
    -e CH_THREADING=sequential \
    chainhammer:local quick

Modes:
  help         Show this help
  quick        Run load test with defaults if CH_TXS/CH_THREADING missing
  run          Run load test requiring CH_TXS + CH_THREADING
  healthcheck  Checks RPC eth_chainId (requires CH_RPC)
  shell        Start a shell inside the container (bash)

Env:
  CH_RPC        JSON-RPC endpoint (e.g. http://127.0.0.1:8545)
  CH_TXS        number of tx to send
  CH_THREADING  concurrency algo (e.g. sequential, "threaded2 20")
  CH_ANALYZE    0/1 (default: 0). If 1, attempts reader + diagrams (needs extra deps)
EOF
}

MODE="${1:-help}"

# Ensure the paths exist (prevents tee/log failures)
mkdir -p /opt/chainhammer/logs /opt/chainhammer/hammer

# Update config.py RPC values if present (best-effort)
if [[ -n "${CH_RPC:-}" && -f /opt/chainhammer/hammer/config.py ]]; then
  sed -i -E "s|^RPCaddress[[:space:]]*=.*|RPCaddress='${CH_RPC}'|g" /opt/chainhammer/hammer/config.py || true
  sed -i -E "s|^RPCaddress2[[:space:]]*=.*|RPCaddress2='${CH_RPC}'|g" /opt/chainhammer/hammer/config.py || true

  echo "== Chainhammer config RPC values =="
  grep -nE "^(RPCaddress|RPCaddress2)[[:space:]]*=" /opt/chainhammer/hammer/config.py || true
  echo "=================================="
fi

case "$MODE" in
  help|-h|--help)
    print_help
    exit 0
    ;;
  shell)
    exec bash
    ;;
  healthcheck)
    if [[ -z "${CH_RPC:-}" ]]; then
      echo "ERROR: CH_RPC is required for healthcheck"
      exit 2
    fi
    curl -sS -m 3 -H 'content-type: application/json' \
      --data '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' \
      "${CH_RPC}" | jq -e '.result' >/dev/null
    echo "OK: eth_chainId reachable at ${CH_RPC}"
    exit 0
    ;;
  quick)
    # Provide friendly defaults
    : "${CH_TXS:=50}"
    : "${CH_THREADING:=sequential}"
    : "${CH_ANALYZE:=0}"
    ;;
  run)
    # Require user-provided values
    if [[ -z "${CH_TXS:-}" || -z "${CH_THREADING:-}" ]]; then
      echo "ERROR: You must set CH_TXS and CH_THREADING for mode=run"
      exit 2
    fi
    : "${CH_ANALYZE:=0}"
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo
    print_help
    exit 2
    ;;
esac

# Run the chainhammer workflow
cd /opt/chainhammer
exec ./run.sh "${MODE}"