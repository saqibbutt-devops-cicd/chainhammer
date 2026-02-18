# 🟢 Level 1 — Clean This Project Only (Safe)

If you only want to reset **chainhammer** or your EVM lab:

### Stop and remove containers
```bash
docker compose down --volumes --remove-orphans 2>/dev/null || true
docker rm -f chainhammer 2>/dev/null || true
```

### Remove specific image
```bash
docker rmi -f chainhammer:local 2>/dev/null || true
```

### Rebuild fresh
```bash
docker build --platform linux/amd64 --no-cache -t chainhammer:local .
```

---

# 🟡 Level 2 — Remove All Unused Docker Stuff (Safe-ish)

This removes dangling images, stopped containers, unused networks.

```bash
docker system prune -a -f
```

If you also want to remove volumes:

```bash
docker system prune -a --volumes -f
```

⚠️ This deletes:
- all stopped containers
- all unused images
- all unused networks
- optionally all unused volumes

---

# 🔴 Level 3 — Hard Reset Everything (Full Nuke)

This deletes **ALL containers, images, volumes, networks**.

### Stop everything
```bash
docker stop $(docker ps -aq) 2>/dev/null || true
```

### Remove all containers
```bash
docker rm -f $(docker ps -aq) 2>/dev/null || true
```

### Remove all images
```bash
docker rmi -f $(docker images -aq) 2>/dev/null || true
```

### Remove all volumes
```bash
docker volume rm $(docker volume ls -q) 2>/dev/null || true
```

### Remove all networks (except default)
```bash
docker network rm $(docker network ls -q | grep -v "bridge\|host\|none") 2>/dev/null || true
```

---

# ☢️ Absolute Nuclear One-Liner

If you truly want to wipe Docker clean:

```bash
docker system prune -a --volumes -f
```

That’s usually enough.

---

# 💣 If Docker Is Still Acting Weird

On Linux:

```bash
sudo systemctl restart docker
```

On Docker Desktop:

- Restart Docker Desktop
- Or reset from settings

---

# 🧠 Pro Tip (Blockchain Infra)

When working with:
- Validators
- Full nodes
- Archive nodes

Be careful with volumes — they contain:
```
/data
/datadir
/geth
/cometbft
priv_validator_key.json
```

If you nuke volumes, you wipe:
- chain state
- validator keys
- node identity

Which might be fine in dev… but catastrophic in prod.

---

If you want, I can also give you:

- 🔥 “Reset only EVM lab cleanly”
- 🧹 “Reset only Chainhammer cleanly”
- 🏗 “Clean rebuild script for your whole infra”

Just tell me how aggressive you want to go 😄