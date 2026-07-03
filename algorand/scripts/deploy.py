#!/usr/bin/env python3
"""
Deploy ZK Passport smart contract to Algorand

SPEC REF: zk_kyc_platform_spec.md §EP-08 — Chain-Agnostic Passport Adapter
CHAIN: Algorand (AVM)
SCRIPT: deploy.py — PyTeal compilation + Algorand deployment

SPEC: EP-08 F-08.6.1 — Contract deployment
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'contracts'))

import pyteal as pt
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk.transaction import ApplicationCreateTxn, StateSchema
from algosdk.logic import compileTeal
from passport import approval_program, clear_state_program

# Configuration
ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")
DEPLOYER_MNEMONIC = os.getenv("DEPLOYER_MNEMONIC", "")

def deploy():
    """Deploy PyTeal contract to Algorand testnet"""
    if not DEPLOYER_MNEMONIC:
        print("ERROR: DEPLOYER_MNEMONIC not set")
        return

    # Connect to Algorand node
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)

    # Compile PyTeal to TEAL
    approval_teal = compileTeal(
        client=client,
        approval_program=approval_program(),
        mode=pt.Mode.Application,
        version=6
    )
    clear_teal = compileTeal(
        client=client,
        approval_program=clear_state_program(),
        mode=pt.Mode.Application,
        version=6
    )

    # Compile TEAL to bytecode
    approval_compiled = client.compile(approval_teal)["result"]
    clear_compiled = client.compile(clear_teal)["result"]

    # Get deployer account
    private_key = mnemonic.to_private_key(DEPLOYER_MNEMONIC)
    address = account.address_from_private_key(private_key)

    # Get suggested params
    params = client.suggested_params()

    # Create application
    txn = ApplicationCreateTxn(
        sender=address,
        sp=params,
        on_complete=pt.OnComplete.NoOp,
        approval_program=bytes.fromhex(approval_compiled),
        clear_program=bytes.fromhex(clear_compiled),
        global_schema=StateSchema(num_uints=10, num_byte_slices=10),
        local_schema=StateSchema(num_uints=10, num_byte_slices=10),
    )

    # Sign and send
    signed = txn.sign(private_key)
    txid = client.send_transaction(signed)

    # Wait for confirmation
    from algosdk.transaction import wait_for_confirmation
    confirmed = wait_for_confirmation(client, txid, 4)

    app_id = confirmed["application-index"]
    print(f"Deployed ZK Passport to Algorand testnet")
    print(f"Application ID: {app_id}")
    print(f"Transaction ID: {txid}")

    return app_id

if __name__ == "__main__":
    deploy()
