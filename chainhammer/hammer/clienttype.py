#!/usr/bin/env python3
"""
@summary: Which client type do we have?
          quorum-raft/ibft OR energyweb OR parity OR geth OR ...

@version: v43 (16/December/2018)
@since:   29/May/2018
@author:  https://github.com/drandreaskrueger
"""

################
## Dependencies:

import json
from pprint import pprint
import requests

try:
    from web3 import Web3, HTTPProvider
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend sys.path for imports:
if __name__ == "__main__" and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPCaddress


class Error(Exception):
    pass


class MethodNotExistentError(Error):
    pass


def curl_post(method, ifPrint=False, RPCaddress=RPCaddress, params=None):
    if params is None:
        params = []
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    r = requests.post(RPCaddress, json=payload)
    if r.status_code != 200:
        raise RuntimeError("HTTP %s calling %s" % (r.status_code, method))
    answer = r.json()
    if "error" in answer:
        msg = answer["error"].get("message", "")
        if "The method" in msg and "does not exist" in msg:
            raise MethodNotExistentError(msg)
        if "Method not found" in msg:
            raise MethodNotExistentError(msg)
        # Unknown error
        raise RuntimeError("RPC error calling %s: %s" % (method, answer["error"]))
    result = answer.get("result", None)
    if ifPrint:
        print(method, "->")
        pprint(result)
    return result


def clientTypeWarnings(nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId):
    if nodeName == "Unknown":
        print("WARN: could not detect nodeName from client string.")
    if consensus == "???":
        print("WARN: consensus could not be detected.")
    if nodeName == "TestRPC":
        print("WARN: TestRPC has odd timestamp units")
    if consensus == "raft":
        print("WARN: raft consensus did not work in all cases")


def clientType(w3):
    """
    figure out which client (quorum, parity, geth...)
    which consensus algorithm (e.g. raft, istanbul, clique, ethash)
    and networkId / chainId / chainName
    """

    consensus = "???"
    chainName = "???"
    networkId = -1
    chainId = -1

    # network id
    try:
        answer = curl_post(method="net_version")
        networkId = int(answer)
    except MethodNotExistentError:
        pass

    # raft consensus?
    try:
        answer = curl_post(method="raft_role")
        if answer:
            consensus = "raft"
    except MethodNotExistentError:
        pass

    # IBFT/istanbul?
    try:
        answer = curl_post(method="admin_nodeInfo")
        if "istanbul" in answer.get("protocols", {}).keys():
            consensus = "istanbul"
    except:
        pass

    nodeString = (w3.version.node or "").strip()

    # Safe defaults
    nodeName = "Unknown"
    nodeVersion = "unknown"
    nodeType = "Unknown"

    if "/" in nodeString:
        parts = nodeString.split("/")
        nodeName = parts[0].strip() if len(parts) > 0 else "Unknown"
        known = ("Geth", "Parity", "Parity-Ethereum", "Energy Web", "TestRPC")
        if nodeName not in known:
            print("Interesting, '%s', a new node type? '%s'" % (nodeName, nodeString))

        if nodeName == "Parity-Ethereum":
            nodeName = "Parity"

        nodeVersion = parts[1].strip() if len(parts) > 1 else "unknown"
        nodeType = nodeName  # ✅ IMPORTANT: always set nodeType for '/' case

        if nodeName == "Parity" and len(parts) > 2:
            # see issue https://github.com/paritytech/parity-ethereum/issues/10215
            nodeVersion = parts[2].strip()

    else:
        # Non-standard / multi-line client strings (common in custom nodes)
        first_line = nodeString.splitlines()[0].strip() if nodeString else "Unknown"
        nodeName = first_line or "Unknown"
        nodeType = nodeName

        import re
        m = re.search(r"(go\d+\.\d+(?:\.\d+)?)", nodeString)
        nodeVersion = m.group(1) if m else first_line

        if consensus in ("raft", "istanbul"):
            nodeName = "Quorum"

        if nodeName == "Energy Web":
            nodeType = "Parity"
            consensus = "PoA"

    # Parity-specific info
    if nodeType == "Parity":
        try:
            chainName = curl_post(method="parity_chain")
            if chainName == "foundation":
                consensus = "PoW"
        except MethodNotExistentError:
            pass
        try:
            answer = curl_post(method="parity_chainId")
            if answer is not None:
                chainId = int(answer, 16) if isinstance(answer, str) else int(answer)
        except MethodNotExistentError:
            pass

    # Geth-style chainId / consensus info
    if nodeType == "Geth":
        try:
            answer = curl_post(method="admin_nodeInfo")
            answer_config = answer.get("protocols", {}).get("eth", {}).get("config", None)
            if answer_config:
                if "clique" in answer_config:
                    consensus = "clique"
                if "ethash" in answer_config:
                    consensus = "ethash"
                chainId = answer_config.get("chainId", chainId)
        except MethodNotExistentError:
            pass
        except Exception:
            pass

    clientTypeWarnings(nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId)
    return nodeName, nodeType, nodeVersion, consensus, networkId, chainName, chainId


def run_clientType(w3):
    return clientType(w3)