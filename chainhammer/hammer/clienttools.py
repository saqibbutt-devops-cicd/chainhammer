#!/usr/bin/env python3
"""
@summary: tools to talk to an Ethereum client node 

@version: v58 (12/April/2019)
@since:   19/June/2018
@organization: 
@author:  https://github.com/drandreaskrueger
@see: https://github.com/drandreaskrueger/chainhammer for updates
"""


################
## Dependencies:

import os
from pprint import pprint

try:
    from web3 import Web3, HTTPProvider # pip3 install web3
except:
    print ("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend sys.path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPCaddress
from hammer.config import FILE_PASSPHRASE, PARITY_UNLOCK_EACH_TRANSACTION, PARITY_ALREADY_UNLOCKED
from hammer.clienttype import clientType

################
## Tools:


def printVersions():
    """Print dependency versions without crashing.

    Chainhammer historically ran inside a virtualenv and would exit early when optional
    dependencies were missing. In Docker (or other packaged environments) we want to
    keep going even if we can't read some version strings (e.g., solc-js prints version
    to stderr which confuses py-solc).
    """
    import sys
    import subprocess

    # web3
    try:
        from web3 import __version__ as web3version
    except Exception:
        web3version = "not-installed"

    # py-solc (legacy)
    try:
        from solc import __version__ as pysolcversion  # pip package: py-solc
    except Exception:
        pysolcversion = "not-installed"

    # eth-testrpc (optional; only used for version printing)
    try:
        from testrpc import __version__ as ethtestrpcversion  # pip package: eth-testrpc
    except Exception:
        ethtestrpcversion = "not-installed"

    # solc binary version: be tolerant about stdout/stderr formats
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
            # Return the first non-empty line (works for solc, solc-js, wrappers)
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
    print("web3 connection established, blockNumber = %s, node version string = %s"
      % (w3.eth.blockNumber, node_ver))

    accountname = "chosen"

    if not account:
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

    formatter="nodeName: %s, nodeType: %s, nodeVersion: %s, consensus: %s, network: %s, chainName: %s, chainId: %s"
    print (formatter % (NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID))

    return NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID # for when imported into other modules


def if_poa_then_bugfix(w3, NODENAME, CHAINNAME, CONSENSUS):
    """
    bugfix for quorum web3.py problem, see
    https://github.com/ethereum/web3.py/issues/898#issuecomment-396701172
    and
    https://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority
    
    actually also appeared when using dockerized standard geth nodes with PoA   
    https://github.com/javahippie/geth-dev (net_version='500')
    """
    if NODENAME == "Quorum" or CHAINNAME=='500' or CONSENSUS=='clique':
        from web3.middleware import geth_poa_middleware
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_stack.inject(geth_poa_middleware, layer=0)


# def web3connection(RPCaddress=RPCaddress, account=None):
def web3connection(RPCaddress=None, account=None):
    """
    prints dependency versions, starts web3 connection, identifies client node type, if quorum then bugfix
    """

    printVersions()

    w3 = start_web3connection(RPCaddress=RPCaddress, account=account)

    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = setGlobalVariables_clientType(w3)

    if_poa_then_bugfix(w3, NODENAME, CHAINNAME, CONSENSUS)

    chainInfos = NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID

    return w3, chainInfos


################################################################################
# generally useful tools


def getBlockTransactionCount(w3, blockNumber):
    """
    testRPC does not provide this endpoint yet, so replicate its functionality:
    """
    block=w3.eth.getBlock(blockNumber)
    # pprint (block)
    return len(block["transactions"])


def correctPath(file):
    """
    This is a semi-dirty hack for FILE_PASSPHRASE (="account-passphrase.txt")
    to repair the FileNotFound problem which only appears when running the tests 
    because then the currentWorkDir is "chainhammer" not "chainhammer/hammer" 
    P.S.: If ever consistent solution, then also fix for the two
          "contract-{abi,address}.json" which tests put into the root folder
    """
    # print ("os.getcwd():", os.getcwd())

    if os.getcwd().split("/")[-1] != "hammer":
        return os.path.join("hammer", file)
    else:
        return file


def unlockAccount(duration=3600, account=None):
    """
    unlock once, then leave open, to later not loose time for unlocking
    """

    if ("TestRPC" in w3.version.node) or (PARITY_ALREADY_UNLOCKED and ("Parity" in w3.version.node)):
        return True # TestRPC does not need unlocking; or parity can be CLI-switch unlocked when starting

    if NODENAME=="Quorum":
        if NETWORKID==1337:
            passphrase="1234" # Azure Quorum testnet 1337 jtessera
        else:
            passphrase="" # Any other Quorum
    else:
        # print ("os.getcwd():", os.getcwd())
        with open(correctPath(FILE_PASSPHRASE), "r") as f:
            passphrase=f.read().strip()

    if NODENAME=="Geth" and CONSENSUS=="clique" and NETWORKID==500:
        passphrase="pass" # hardcoded in geth-dev/docker-compose.yml

    # print ("passphrase:", passphrase)

    if not account:
        account = w3.eth.defaultAccount
        # print (account)

    if PARITY_UNLOCK_EACH_TRANSACTION:
        answer = w3.personal.unlockAccount(account=account,
                                           passphrase=passphrase)
    else:
        if NODETYPE=="Parity":
            duration = w3.toHex(duration)
        answer = w3.personal.unlockAccount(account=account,
                                           passphrase=passphrase,
                                           duration=duration)
    print ("unlocked:", answer)
    return answer



if __name__ == '__main__':

    # example how to call this:
    # answer = web3connection()
    answer = web3connection(RPCaddress=RPCaddress, account=None)

    w3, chainInfos  = answer

    global NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID
    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = chainInfos

    # print (type(NETWORKID), NETWORKID)


