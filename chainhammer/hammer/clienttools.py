#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import time

from hammer.clienttype import clientType
from hammer.config import FILE_PASSPHRASE

# globals for node/client info
NODENAME = "???"
NODETYPE = "???"
NODEVERSION = "???"
CONSENSUS = "???"
NETWORKID = -1
CHAINNAME = "???"
CHAINID = -1


################################################################################
# printing dependency versions (must never crash chainhammer)

def printVersions():
    """Print dependency versions without crashing (informational only)."""
    import subprocess

    # web3
    try:
        from web3 import __version__ as web3version
    except Exception:
        web3version = "not-installed"

    # py-solc (pip name: py-solc; import name: solc)
    pysolcversion = "not-installed"
    try:
        import pkg_resources  # comes with setuptools
        try:
            pysolcversion = pkg_resources.get_distribution("py-solc").version
        except Exception:
            pysolcversion = "not-installed"
    except Exception:
        pysolcversion = "unknown"

    # eth-testrpc (pip name: eth-testrpc; import name: testrpc)
    try:
        from testrpc import __version__ as ethtestrpcversion
    except Exception:
        ethtestrpcversion = "not-installed"

    # solc binary version (tolerate solc printing to stderr)
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


################################################################################
# web3 connection + node metadata

def start_web3connection(RPCaddress, account=None):
    from web3 import Web3, HTTPProvider

    w3 = Web3(HTTPProvider(RPCaddress))

    if not w3.isConnected():
        raise RuntimeError("Cannot connect to RPC at %s" % RPCaddress)

    # web3 v4 compatible node version string:
    node_ver = getattr(getattr(w3, "version", None), "node", None) or "unknown"

    print(
        "web3 connection established, blockNumber = %s, node version string = %s"
        % (w3.eth.blockNumber, node_ver)
    )

    accountname = "chosen"

    if not account:
        # Many remote RPC nodes return eth_accounts=[]
        try:
            accounts = w3.eth.accounts
        except Exception:
            accounts = []

        if accounts and len(accounts) > 0:
            w3.eth.defaultAccount = accounts[0]
            accountname = "first"
        else:
            ch_from = os.getenv("CH_FROM")
            if ch_from:
                w3.eth.defaultAccount = ch_from
                accountname = "CH_FROM"
                print("No RPC accounts; using CH_FROM =", ch_from)
            else:
                raise RuntimeError(
                    "RPC returned no accounts (eth_accounts=[]). "
                    "Set CH_FROM (and usually CH_PRIVKEY for signing) or use a node that exposes/unlocks accounts."
                )

    return w3


def setGlobalVariables_clientType(w3):
    global NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID

    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = clientType(w3)

    formatter = (
        "nodeName: %s, nodeType: %s, nodeVersion: %s, consensus: %s, network: %s, chainName: %s, chainId: %s"
    )
    print(formatter % (NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID))

    return NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID


def if_poa_then_bugfix(w3, CONSENSUS):
    """POA middleware for geth/parity POA chains."""
    if CONSENSUS != "poa":
        return
    try:
        from web3.middleware import geth_poa_middleware
        w3.middleware_stack.inject(geth_poa_middleware, layer=0)
    except Exception:
        pass


def web3connection(RPCaddress, account=None):
    """Create web3 connection and detect node type."""
    printVersions()

    w3 = start_web3connection(RPCaddress=RPCaddress, account=account)
    chainInfos = setGlobalVariables_clientType(w3)
    if_poa_then_bugfix(w3, chainInfos[3])  # CONSENSUS

    return w3, chainInfos


################################################################################
# block helpers (needed by tps.py)

def getBlockTransactionCount(w3, block_identifier):
    """Return number of tx in a block (compatible across nodes/web3 versions)."""
    try:
        # web3 v4 has eth.getBlockTransactionCount
        return int(w3.eth.getBlockTransactionCount(block_identifier))
    except Exception:
        try:
            blk = w3.eth.getBlock(block_identifier)
            return len(blk["transactions"]) if isinstance(blk, dict) else len(blk.transactions)
        except Exception:
            return 0


################################################################################
# account tools (deploy.py expects unlockAccount() to be callable easily)

def _read_passphrase():
    """Try env CH_PASSWORD then FILE_PASSPHRASE (if exists)."""
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
    """
    Best-effort unlock. Must never crash chainhammer.

    - If node doesn't support personal API: returns False.
    - If CH_PRIVKEY signing is used: unlocking may not be required (returns False/True depending).
    """
    try:
        if w3 is None:
            # deploy.py previously called unlockAccount() with no args.
            # We keep it safe: do nothing, don't crash.
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
            # no password available -> can't unlock via personal API
            return False

        # Try geth namespace first
        try:
            w3.geth.personal.unlock_account(accountAddress, password)
            return True
        except Exception:
            pass

        # Try parity/openethereum style (some nodes expose w3.personal)
        try:
            w3.personal.unlockAccount(accountAddress, password)
            return True
        except Exception:
            pass

        return False
    except Exception:
        return False


################################################################################
# simple helpers

def waitForTransactionReceipt(w3, tx_hash, timeout=120):
    """Wait for tx receipt, return it when mined."""
    start = time.time()
    while True:
        receipt = w3.eth.getTransactionReceipt(tx_hash)
        if receipt:
            return receipt
        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for receipt: %s" % str(tx_hash))
        time.sleep(1)