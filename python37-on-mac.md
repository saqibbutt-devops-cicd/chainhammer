# ✅ Recommended (cleanest): use `pyenv`

Even if you already downloaded the tarball, using `pyenv` is much cleaner and won’t mess up system Python.

### 1️⃣ Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

### 2️⃣ Install pyenv

```bash
brew install pyenv
```

Add to your shell:

```bash
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc
```

---

### 3️⃣ Install Python 3.7.17

```bash
pyenv install 3.7.17
pyenv global 3.7.17
```

Check:

```bash
python --version
```

You should see:

```
Python 3.7.17
```

---

### 4️⃣ Use it in IntelliJ (PyCharm or IntelliJ Ultimate)

Go to:

```
Settings → Project → Python Interpreter
```

Click:

```
Add Interpreter → Existing Interpreter
```

Then browse to:

```
~/.pyenv/versions/3.7.17/bin/python
```

Done.

---

# 🛠 If you really want to install from python-3.7.17.tar.xz manually

If you want to compile it yourself:

---

### 1️⃣ Extract

```bash
tar -xf python-3.7.17.tar.xz
cd Python-3.7.17
```

---

### 2️⃣ Install required build deps (important on mac)

```bash
brew install openssl readline sqlite3 xz zlib
```

---

### 3️⃣ Configure build

On macOS (especially M1/M2), you need to point to Homebrew libraries:

```bash
./configure \
  --prefix=/usr/local/python-3.7.17 \
  --with-openssl=$(brew --prefix openssl@1.1)
```

---

### 4️⃣ Build + install

```bash
make
make install
```

This installs it to:

```
/usr/local/python-3.7.17/bin/python3
```

Check:

```bash
/usr/local/python-3.7.17/bin/python3 --version
```

---

### 5️⃣ Add to PATH (optional)

```bash
echo 'export PATH="/usr/local/python-3.7.17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

# 🎯 Use it inside IntelliJ

In IntelliJ:

```
Settings → Python Interpreter → Add Interpreter → System Interpreter
```

Browse to:

```
/usr/local/python-3.7.17/bin/python3
```

---

# ⚠️ Important Note (very important)

Python 3.7 is:

- End-of-life
- Old SSL support
- Old pip support
- May break with modern packages

If you're using it **only for Chainhammer compatibility**, that’s fine.

But don’t use it for new production development.

---

# 🔥 My honest recommendation for you

Since you’re doing Docker work already:

You don’t actually need to install 3.7 system-wide.

You can:

- Let Docker use 3.7
- Develop inside IntelliJ using Docker interpreter
- Avoid polluting your Mac

If you want, I can show you how to use **Docker as Python interpreter inside IntelliJ**, which is actually cleaner for this project.

---

Tell me:

- Are you on Intel Mac or Apple Silicon?
- Are you using IntelliJ Ultimate or PyCharm?

And I’ll give you the cleanest setup path for your environment.