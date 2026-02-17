# ✅ how to build + use it

## 1) Build the image (from project root)
```bash
docker build -t chainhammer:local .
```

If your Dockerfile isn’t named `Dockerfile`, then:
```bash
docker build -t chainhammer:local -f Dockerfile .
```

---

## 2) Basic sanity test (JSON-RPC only)
### Linux easiest: `--network host`
Validator RPC (example):
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  chainhammer:local quick
```

Fullnode:
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:9545" \
  chainhammer:local quick
```

Archive:
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:10545" \
  chainhammer:local quick
```

Expected output includes `eth_chainId` and `eth_blockNumber`.

---

## 3) Wait until node is up (Chainhammer’s own check)
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  chainhammer:local is_up
```

---

## 4) Load test (deploy + send)
This will send transactions, so the chain must accept txs.

### Sequential run (safe starter)
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=1000 \
  -e CH_THREADING="sequential" \
  chainhammer:local hammer_only
```

### Concurrent run
```bash
docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=10000 \
  -e CH_THREADING="threaded2 20" \
  chainhammer:local hammer_only
```

---

## 5) Full run with reports (reader + diagrams/pages)
Mount outputs so you keep results on your host:

```bash
mkdir -p ./ch-output

docker run --rm --network host \
  -e CH_RPC="http://127.0.0.1:8545" \
  -e CH_TXS=5000 \
  -e CH_THREADING="threaded2 20" \
  -v "$PWD/ch-output:/opt/chainhammer/results" \
  chainhammer:local run "evm-demo-validator"
```

---

# ⚠️ Important: Chainhammer may require an account/key setup
Chainhammer typically deploys a contract and sends txs, so it often needs:
- a funded sender address
- sometimes an unlocked account / personal API (depends on its config + client type)

If your node rejects tx submission, the container setup is fine — the **RPC node policy** or **account configuration** is the blocker.

If you paste your `chainhammer/hammer/config.py` (especially the sender/keys section), I’ll tell you exactly what it expects and how to run it cleanly against your Cosmos-EVM (evmd) nodes.

---

## Quick answer to your question
✅ Your Dockerfile and entrypoint are correct for your folder structure.  
🔧 Only fix needed is the **`sed` pattern** to handle spaces / quotes in `config.py`.  
✅ After that, you can build once and run load tests anywhere.

If you want, I can also give you a **“read-only RPC load test mode”** (no contract deploy, just spamming `eth_call`, `eth_getBlockByNumber`, `eth_getLogs`, etc.) — that’s super useful for production RPC benchmarking without touching chain state.