#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import time

from hammer.clienttype import clientType
from hammer.config import FILE_PASSPHRASE


# -------------------------------------------------------------------
# Globals
# -------------------------------------------------------------------
NODENAME = "???"
NODETYPE = "???"
NODEVERSION = "???"
CONSENSUS = "???"
NETWORKID = -1
CHAINNAME = "???"
CHAINID = -1


# -------------------------------------------------------------------
# Versions (must not crash)
# -------------------------------------------------------------------
def printVersions():
    import subprocess

    try:
        from web3 import __version__ as web3version
    except Exception:
        web3version = "not-installed"

    pysolcversion = "not-installed"
    try:
        import pkg_resources
        try:
            pysolcversion = pkg_resources.get_distribution("py-solc").version
        except Exception:
            pysolcversion = "not-installed"
    except Exception:
        pysolcversion = "unknown"

    try:
        from testrpc import __version__ as ethtestrpcversion
    except Exception:
        ethtestrpcversion = "not-installed"

    def _solc_version():
        try:
            p = subprocess.run(
                ["solc", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            combined = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
            if not combined:
                return "unknown"
            for line in combined.splitlines():
                line = line.strip()
                if line:
                    return line
            return "unknown"
        except FileNotFoundError:
            return "not-found"
        except Exception:
            return "unknown"

    solcver = _solc_version()

    print(
        "versions: web3 %s, py-solc: %s, solc %s, testrpc %s, python %s"
        % (web3version, pysolcversion, solcver, ethtestrpcversion, sys.version.replace("\n", ""))
    )


# -------------------------------------------------------------------
# Web3 connect
# -------------------------------------------------------------------
def start_web3connection(RPCaddress, account=None):
    from web3 import Web3, HTTPProvider

    w3 = Web3(HTTPProvider(RPCaddress))
    if not w3.isConnected():
        raise RuntimeError("Cannot connect to RPC at %s" % RPCaddress)

    node_ver = getattr(getattr(w3, "version", None), "node", None) or "unknown"

    print(
        "web3 connection established, blockNumber = %s, node version string = %s"
        % (w3.eth.blockNumber, node_ver)
    )

    # Default account selection
    if not account:
        try:
            accounts = w3.eth.accounts
        except Exception:
            accounts = []

        if accounts and len(accounts) > 0:
            w3.eth.defaultAccount = accounts[0]
        else:
            ch_from = os.getenv("CH_FROM")
            if ch_from:
                w3.eth.defaultAccount = ch_from
                print("No RPC accounts; using CH_FROM =", ch_from)
            else:
                raise RuntimeError(
                    "RPC returned no accounts (eth_accounts=[]). Set CH_FROM or use unlocked accounts."
                )

    return w3


def setGlobalVariables_clientType(w3):
    global NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID
    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = clientType(w3)
    return NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID


def if_poa_then_bugfix(w3, consensus):
    if consensus != "poa":
        return
    try:
        from web3.middleware import geth_poa_middleware
        w3.middleware_stack.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass


# -------------------------------------------------------------------
# ✅ REQUIRED by deploy.py + tps.py
# -------------------------------------------------------------------
def web3connection(RPCaddress, account=None):
    printVersions()
    w3 = start_web3connection(RPCaddress=RPCaddress, account=account)
    chainInfos = setGlobalVariables_clientType(w3)
    consensus = chainInfos[3]
    if_poa_then_bugfix(w3, consensus)
    return w3, chainInfos


# -------------------------------------------------------------------
# Used by tps.py
# -------------------------------------------------------------------
def getBlockTransactionCount(w3, block_identifier):
    try:
        return int(w3.eth.getBlockTransactionCount(block_identifier))
    except Exception:
        try:
            blk = w3.eth.getBlock(block_identifier)
            if isinstance(blk, dict):
                return len(blk.get("transactions", []))
            return len(blk.transactions)
        except Exception:
            return 0


# -------------------------------------------------------------------
# Unlock (safe)
# -------------------------------------------------------------------
def _read_passphrase():
    pw = os.getenv("CH_PASSWORD")
    if pw:
        return pw
    try:
        if os.path.exists(FILE_PASSPHRASE):
            return open(FILE_PASSPHRASE, "r").read().strip()
    except Exception:
        pass
    return None


def unlockAccount(w3=None, accountAddress=None, password=None):
    # Do not crash if called wrongly
    if w3 is None:
        return False

    if not accountAddress:
        try:
            accountAddress = w3.eth.defaultAccount
        except Exception:
            accountAddress = None

    if not accountAddress:
        return False

    if password is None:
        password = _read_passphrase()

    if password is None:
        return False

    try:
        w3.geth.personal.unlock_account(accountAddress, password)
        return True
    except Exception:
        pass

    try:
        w3.personal.unlockAccount(accountAddress, password)
        return True
    except Exception:
        return False


# -------------------------------------------------------------------
# Receipt wait helper
# -------------------------------------------------------------------
def waitForTransactionReceipt(w3, tx_hash, timeout=120):
    start = time.time()
    while True:
        receipt = w3.eth.getTransactionReceipt(tx_hash)
        if receipt:
            return receipt
        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for receipt: %s" % str(tx_hash))
        time.sleep(1)