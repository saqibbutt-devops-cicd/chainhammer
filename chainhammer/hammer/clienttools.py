#!/usr/bin/env python3
# coding: utf-8

import sys
import time

from hammer.clienttype import clientType

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
    """Print dependency versions without crashing.

    This is informational. It must never stop chainhammer from running.
    """
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
# get a connection, and find out as much as possible

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

    accountname = "chosen"

    if not account:
        # Some RPC nodes return no accounts (eth_accounts=[]). In that case, allow specifying a funded
        # sender address via CH_FROM. If neither exists, fail with a clear message.
        try:
            accounts = w3.eth.accounts
        except Exception:
            accounts = []

        if accounts and len(accounts) > 0:
            w3.eth.defaultAccount = accounts[0]
            accountname = "first"
        else:
            import os
            ch_from = os.getenv("CH_FROM")
            if ch_from:
                w3.eth.defaultAccount = ch_from
                accountname = "CH_FROM"
                print("No RPC accounts; using CH_FROM =", ch_from)
            else:
                raise RuntimeError(
                    "RPC returned no accounts (eth_accounts=[]). "
                    "Set CH_FROM (and CH_PRIVKEY if needed) "
                    "or use a node that exposes/unlocks accounts."
                )

    return w3


def setGlobalVariables_clientType(w3):
    """
    Set global variables.
    """
    global NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID

    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = clientType(w3)

    formatter = "nodeName: %s, nodeType: %s, nodeVersion: %s, consensus: %s, network: %s, chainName: %s, chainId: %s"
    print(formatter % (NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID))

    return NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID


def if_poa_then_bugfix(w3, NODENAME, CHAINNAME, CONSENSUS):
    """
    bugfix for quorum web3.py problem, see
    https://github.com/ethereum/web3.py/issues/898#issuecomment-396701172
    and
    https://github.com/ethereum/web3.py/issues/898
    """
    if CONSENSUS != "poa":
        return

    from web3.middleware import geth_poa_middleware
    w3.middleware_stack.inject(geth_poa_middleware, layer=0)


def web3connection(RPCaddress, account=None):
    """
    create web3 connection and find out as much as possible about client.
    also set bugfixes when needed.
    """

    printVersions()

    w3 = start_web3connection(RPCaddress=RPCaddress, account=account)

    # set globals
    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = setGlobalVariables_clientType(w3)

    # fix if needed
    if_poa_then_bugfix(w3, NODENAME, CHAINNAME, CONSENSUS)

    return w3, (NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID)


################################################################################
# account tools

def unlockAccount(w3, accountAddress, password):
    """
    unlock an account on the RPC node (if supported).
    """
    if not accountAddress:
        return

    # some nodes don't support personal_* methods
    try:
        w3.geth.personal.unlock_account(accountAddress, password)
        print("Unlocked account:", accountAddress)
    except Exception as e:
        print("Could not unlock account via RPC personal API:", str(e))


################################################################################
# simple helpers

def waitForTransactionReceipt(w3, tx_hash, timeout=120):
    """
    wait for tx receipt, return it when mined.
    """
    start = time.time()
    while True:
        receipt = w3.eth.getTransactionReceipt(tx_hash)
        if receipt:
            return receipt
        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for receipt: %s" % tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash))
        time.sleep(1)