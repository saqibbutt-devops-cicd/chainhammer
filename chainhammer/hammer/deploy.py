#!/usr/bin/env python3
"""
@summary: deploy contract

@version: v46 (03/January/2019)
@since:   2/May/2018
@author:  https://github.com/drandreaskrueger
"""

import sys, time, json
from pprint import pprint

import requests

try:
    from web3 import Web3, HTTPProvider
    from solc import compile_source
except:
    print("Dependencies unavailable. Start virtualenv first!")
    exit()

# extend path for imports:
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from hammer.config import RPCaddress, TIMEOUT_DEPLOY, PARITY_UNLOCK_EACH_TRANSACTION
from hammer.config import FILE_CONTRACT_SOURCE, FILE_CONTRACT_ABI, FILE_CONTRACT_ADDRESS
from hammer.config import GAS_FOR_SET_CALL

from hammer.clienttools import web3connection, unlockAccount


def compileContract(contract_source_file):
    with open(contract_source_file, "r") as f:
        contract_source_code = f.read()
    compiled_sol = compile_source(contract_source_code)
    assert(len(compiled_sol) == 1)

    contractName = list(compiled_sol.keys())[0]
    contract_interface = compiled_sol[contractName]
    return contractName.replace("<stdin>:", ""), contract_interface


def deployContract(contract_interface, ifPrint=True, timeout=TIMEOUT_DEPLOY):
    before = time.time()
    myContract = w3.eth.contract(abi=contract_interface['abi'],
                                 bytecode=contract_interface['bin'])

    tx_hash = w3.toHex(myContract.constructor().transact())
    print("tx_hash = ", tx_hash, "--> waiting for receipt (timeout=%d) ..." % timeout)
    sys.stdout.flush()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=timeout)
    print("Receipt arrived. Took %.1f seconds." % (time.time() - before))

    contractAddress = tx_receipt["contractAddress"]
    if ifPrint:
        line = "Deployed. gasUsed={gasUsed} contractAddress={contractAddress}"
        print(line.format(**tx_receipt))
    return contractAddress


def contractObject(contractAddress, abi):
    myContract = w3.eth.contract(address=contractAddress, abi=abi)
    return myContract


def saveToDisk(contractAddress, abi):
    json.dump({"address": contractAddress}, open(FILE_CONTRACT_ADDRESS, 'w'))
    json.dump(abi, open(FILE_CONTRACT_ABI, 'w'))


def loadFromDisk():
    contractAddress = json.load(open(FILE_CONTRACT_ADDRESS, 'r'))
    abi = json.load(open(FILE_CONTRACT_ABI, 'r'))
    return contractAddress["address"], abi


def contract_CompileDeploySave(contract_source_file):
    contractName, contract_interface = compileContract(contract_source_file)

    # ✅ FIX: unlockAccount must receive w3 (deploy.py used to call unlockAccount() with no args)
    print("unlock:", unlockAccount(w3))

    contractAddress = deployContract(contract_interface)
    saveToDisk(contractAddress, abi=contract_interface["abi"])
    return contractName, contract_interface, contractAddress


def trySmartContractMethods(myContract, gasForSetCall=GAS_FOR_SET_CALL):
    answer1 = myContract.functions.get().call()
    print('.get(): {}'.format(answer1))

    if PARITY_UNLOCK_EACH_TRANSACTION:
        print("unlockAccount:", unlockAccount(w3))

    print('.set()')
    txParameters = {'from': w3.eth.defaultAccount,
                    'gas': gasForSetCall}
    tx = myContract.functions.set(answer1 + 1).transact(txParameters)
    tx_hash = w3.toHex(tx)
    print("transaction", tx_hash, "... "); sys.stdout.flush()
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
    print("... mined. Receipt --> gasUsed={gasUsed}".format(**tx_receipt))

    answer2 = myContract.functions.get().call()
    print('.get(): {}'.format(answer2))

    return answer1, tx_receipt, answer2


if __name__ == '__main__':
    global w3, NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID

    w3, chainInfos = web3connection(RPCaddress=RPCaddress, account=None)
    NODENAME, NODETYPE, NODEVERSION, CONSENSUS, NETWORKID, CHAINNAME, CHAINID = chainInfos

    contract_CompileDeploySave(contract_source_file=FILE_CONTRACT_SOURCE)

    if len(sys.argv) > 1 and sys.argv[1] == "andtests":
        contractAddress, abi = loadFromDisk()
        myContract = contractObject(contractAddress, abi)
        trySmartContractMethods(myContract)