Below is a **complete “scenario pack”** you can copy/paste to test *everything* (RPC reachability, node-up checks, deploy+send hammering, reports, and the common failure modes).

---

## 0) Host prep (always do this once per machine)

```bash
cd ~/Downloads/projects/chainhammer
mkdir -p logs ch-output
```

### Where things live
- **Container workdir:** `/opt/chainhammer`
- **Logs inside container:** `/opt/chainhammer/logs`
- **Logs on host (bind mount):** `./logs`
- **Results inside container:** `/opt/chainhammer/results`
- **Results on host (bind mount):** `./ch-output`
- **Chainhammer “infofile” produced:** `hammer/last-experiment.json` (inside container; if you don’t mount the whole repo, you won’t persist it)

---

## 1) Build / rebuild

```bash
docker build --no-cache -t chainhammer:local .
```

(If you just changed Python files, you can skip `--no-cache` sometimes, but for debugging it’s fine.)

---

## 2) Connectivity-only tests (no txs)

### 2.1 Sanity: can the host reach RPC?
```bash
curl -s -X POST http://127.0.0.1:8545 \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### 2.2 Check whether the node exposes accounts (this is your current blocker)
```bash
curl -s -X POST http://127.0.0.1:8545 \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","method":"eth_accounts","params":[],"id":1}'
```

- If `"result":[]` → node exposes **no accounts**. You must use `CH_FROM` (and likely `CH_PRIVKEY`) or change node config.

---

## 3) Run modes and what they do

### Required env vars for most modes
Your entrypoint requires:

- `CH_TXS`
- `CH_THREADING`

And you always want:

- `CH_RPC`

---

## 4) Scenario A — “Quick” run (the one you’re using)

### A1) Linux host networking style (what you’re using)
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=100 \
  -e CH_THREADING=sequential \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local quick
```

### What to check on host
```bash
ls -lah logs
tail -n 200 logs/deploy.py.log
tail -n 200 logs/send.py.log
tail -n 200 logs/tps.py.log
```

---

## 5) Scenario B — only “is_up” (wait for node to answer)

```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=1 \
  -e CH_THREADING=sequential \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local is_up
```

(Your entrypoint wants `CH_TXS` and `CH_THREADING`, so we satisfy it even though this mode doesn’t really use them.)

---

## 6) Scenario C — hammer only (deploy + send, no reports)

### C1) Sequential (safe starter)
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=1000 \
  -e CH_THREADING="sequential" \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local hammer_only
```

### C2) Concurrent (more load)
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=10000 \
  -e CH_THREADING="threaded2 20" \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local hammer_only
```

---

## 7) Scenario D — full run with reports

```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=5000 \
  -e CH_THREADING="threaded2 20" \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  -v "$PWD/ch-output:/opt/chainhammer/results" \
  chainhammer:local run "evm-demo-validator"
```

Host results:
```bash
find ch-output -maxdepth 3 -type f | sort
```

---

## 8) Scenario E — your current “no accounts” case (most important)

If your node returns `eth_accounts: []`, Chainhammer will crash unless you provide a funded sender.

### E1) Provide a funded sender address
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=1000 \
  -e CH_THREADING="sequential" \
  -e CH_FROM="0xYOUR_FUNDED_ADDRESS" \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local hammer_only
```

### E2) If the node does NOT support unlocked accounts, you will also need a private key
(Only do this in a controlled environment.)

```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=1000 \
  -e CH_THREADING="sequential" \
  -e CH_FROM="0xYOUR_FUNDED_ADDRESS" \
  -e CH_PRIVKEY="0xYOUR_PRIVATE_KEY_HEX" \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local hammer_only
```

If your `send.py` doesn’t yet sign locally, you’ll see errors like:
- “authentication needed: password or unlock”
- “the method personal_sendTransaction does not exist”
- “sender account not recognized”
- “insufficient funds”

Those are **node policy / signing** issues (not Docker).

---

## 9) Scenario F — Mac-friendly networking (if `--network host` acts weird)
On macOS Docker Desktop, `--network host` isn’t always what you think. Use:

```bash
docker run --rm -it \
  -e CH_RPC="http://host.docker.internal:8545" \
  -e CH_TXS=100 \
  -e CH_THREADING=sequential \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local quick
```

---

## 10) Scenario G — live-editing code on host (only if you really need it)
If you bind-mount only `hammer/`, you risk missing scripts like `is_up.py`. Best is mount the whole repo:

```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=100 \
  -e CH_THREADING=sequential \
  -v "$PWD:/opt/chainhammer" \
  -v "$PWD/logs:/opt/chainhammer/logs" \
  chainhammer:local quick
```

---

## 11) Troubleshooting map (fast)

### Logs to inspect
```bash
tail -n 200 logs/tps.py.log
tail -n 200 logs/deploy.py.log
tail -n 200 logs/send.py.log
```

### Most common errors and what they mean
- `eth_accounts=[]` → supply `CH_FROM` (and likely signing)
- `IndexError w3.eth.accounts[0]` → same as above
- `personal_* method not found` → node doesn’t expose personal API; must sign locally
- `insufficient funds` → fund the `CH_FROM` address
- `replacement transaction underpriced / nonce too low` → concurrency/nonce handling; reduce threading or fix nonce logic

---

If you want, I can also generate you a **single bash script** (e.g. `run-scenarios.sh`) that runs these scenarios in order, prints PASS/FAIL, and tails the relevant log on failure—so testing becomes one command.