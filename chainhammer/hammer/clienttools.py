#!/usr/bin/env python3
"""
@summary: Which client type do we have?
          quorum-raft/ibft OR energyweb OR parity OR geth OR ...

@version: v43 (16/December/2018)
@since:   29/May/2018
@organization:
@author:  https://github.com/drandreaskrueger
@see:     https://github.com/drandreaskrueger/chainhammer for updates
"""

################
## Dependencies:

import json
from pprint import pprint
import requests  # pip3 install requests

try:
    from web3 import Web3, HTTPProvider  # pip3 install web3
except Exception:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPCaddress


############################################################
## the main function:

def clientType(w3, ifPrint=True):
    """
    @summary:
      Determine what sort of node/client we talk to:
      quorum-raft / quorum-istanbul / parity / geth / etc.
    @return:
      nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId
    """

    consensus = "???"
    chainName = "???"
    chainId = -1

    # ----------------------------------------------------------------------
    # consensus detection (best-effort)
    # ----------------------------------------------------------------------

    # Quorum raft / istanbul (older heuristics)
    try:
        answer = w3.manager.request_blocking("admin_nodeInfo", [])
        # quorum returns protocols / raft / istanbul sometimes
        try:
            if 'raft' in answer.get('protocols', {}).keys():
                consensus = "raft"
            if 'istanbul' in answer.get('protocols', {}).keys():
                consensus = "istanbul"
        except Exception:
            pass
    except Exception:
        pass

    # ----------------------------------------------------------------------
    # client identification
    # ----------------------------------------------------------------------

    # Geth / Parity / Energy Web (and custom nodes):
    try:
        nodeString = w3.version.node
    except Exception:
        nodeString = "unknown"

    # Some clients return a geth-style string like:
    #   Geth/v1.10.26-stable-.../linux-amd64/go1.20.5
    # but some custom nodes return multi-line strings without slashes, e.g.:
    #   Version dev ()
    #   Compiled at  using Go go1.23.8 (amd64)
    nodeString = (nodeString or "").strip()

    # default values
    nodeName = "Unknown"
    nodeVersion = "unknown"

    if "/" in nodeString:
        parts = nodeString.split("/")
        nodeName = parts[0].strip() if len(parts) > 0 else "Unknown"

        # geth: name/version/...
        if len(parts) > 1:
            nodeVersion = parts[1].strip()

        # Parity: sometimes version is at index 2 (see upstream issue)
        if nodeName in ("Parity", "Parity-Ethereum") and len(parts) > 2:
            nodeVersion = parts[2].strip()

        if nodeName == "Parity-Ethereum":
            nodeName = "Parity"
    else:
        # Fallback for non-standard / multi-line version strings
        first_line = nodeString.splitlines()[0].strip() if nodeString else "Unknown"
        nodeName = first_line or "Unknown"

        # try to extract a go toolchain version like "go1.23.8" if present
        import re as _re
        m_go = _re.search(r"(go\d+\.\d+(?:\.\d+)?)", nodeString)
        if m_go:
            nodeVersion = m_go.group(1)
        else:
            nodeVersion = first_line

    known = ("Geth", "Parity", "Energy Web", "TestRPC")
    if nodeName not in known:
        print("Interesting, '%s', a new node type? '%s'" % (nodeName, nodeString))

    # Quorum pretends to be Geth - so how to distinguish vanillaGeth from QuorumGeth?
    #  - see https://github.com/jpmorganchase/quorum/issues/507
    nodeType = nodeName

    if consensus in ('raft', 'istanbul'):
        nodeName = "Quorum"

    if nodeName == "Energy Web":
        nodeType = "Parity"
        consensus = "PoA"  # assumption

    # ----------------------------------------------------------------------
    # network + chain id
    # ----------------------------------------------------------------------

    # network id
    try:
        networkId = w3.net.version
        try:
            networkId = int(networkId)
        except Exception:
            pass
    except Exception:
        networkId = -1

    # chain id (may not exist on old clients)
    try:
        chainId = int(w3.eth.chainId)
    except Exception:
        chainId = -1

    if ifPrint:
        print("nodeName:", nodeName, "nodeType:", nodeType, "nodeVersion:", nodeVersion,
              "consensus:", consensus, "network:", networkId,
              "chainName:", chainName, "chainId:", chainId)

    return nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId


############################################################
## little test runner below (unchanged behaviour)

def simple_web3connection(RPCaddress):
    w3 = Web3(HTTPProvider(RPCaddress))
    print("connected:", w3.isConnected(), "blockNumber =", w3.eth.blockNumber, end=", ")
    print("node version string = ", w3.version.node)
    return w3


def run_clientType(w3):
    nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId = clientType(w3)
    return nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId


def justTryingOutDifferentThings(ifPrint=True):
    # placeholder / debug
    pass


if __name__ == '__main__':
    w3 = simple_web3connection(RPCaddress=RPCaddress)
    run_clientType(w3)
    print()
    justTryingOutDifferentThings()