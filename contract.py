OntCversion = '2.0.0'

'''
OEP4 Example Contract

Written: July 21st, 2019
Author: Wyatt Mufson <wyatt@towerbuilders.org>

Copyright (C) 2019 TowerBuilders
Available free of charge under the MIT license
'''

from ontology.interop.Ontology.Runtime import Base58ToAddress
from ontology.interop.System.Action import RegisterAction
from ontology.interop.System.Runtime import Log, CheckWitness
from ontology.interop.System.Storage import GetContext, Get, Put, Delete
ctx = GetContext()

TransferEvent = RegisterAction("transfer", "from", "to", "amount")
ApprovalEvent = RegisterAction("approval", "owner", "spender", "amount")

OWNER = Base58ToAddress("AQf4Mzu1YJrhz9f3aRkkwSm9n3qhXGSh4p")

NAME = 'OEP4 Token'
SYMBOL = 'OEP4'
DECIMALS = 8
TOTAL_AMOUNT = 100000000 # 100 million
DECIMAL_MULTIPLIER = 100000000 # 10^{DECIMALS} = 10^8

BALANCE_PREFIX = b'\x01'
APPROVE_PREFIX = b'\x02'
SUPPLY_KEY = 'TotalSupply'


def Main(operation, args):
    if operation == 'name':
        Require(len(args) == 0)
        return name()
    elif operation == 'symbol':
        Require(len(args) == 0)
        return symbol()
    elif operation == 'decimals':
        Require(len(args) == 0)
        return decimals()
    elif operation == 'totalSupply':
        Require(len(args) == 0)
        return totalSupply()
    elif operation == 'balanceOf':
        Require(len(args) == 1)
        address = args[0]
        return balanceOf(address)
    elif operation == 'transfer':
        Require(len(args) == 3)
        from_address = args[0]
        to_address = args[1]
        amount = args[2]
        return transfer(from_address, to_address, amount)
    elif operation == 'transferMulti':
        Require(len(args) > 0)
        return transferMulti(args)
    elif operation == 'approve':
        Require(len(args) == 3)
        owner = args[0]
        spender = args[1]
        amount = args[2]
        return approve(owner, spender, amount)
    elif operation == 'transferFrom':
        Require(len(args) == 4)
        spender = args[0]
        from_address = args[1]
        to_address = args[2]
        amount = args[3]
        return transferFrom(spender, from_address, to_address, amount)
    elif operation == 'allowance':
        Require(len(args) == 2)
        owner = args[0]
        spender = args[1]
        return allowance(owner, spender)
    # Admin Methods
    elif operation == 'init':
        return init()
    return False


def name():
    """
    Returns the name of the token
    """
    return NAME


def symbol():
    """
    Returns the symbol of the token
    """
    return SYMBOL


def decimals():
    """
    Returns the amount of decimals of the token
    """
    return DECIMALS + 0


def totalSupply():
    """
    Returns the total supply of the token
    """
    return Get(ctx, SUPPLY_KEY) + 0


def balanceOf(address):
    """
    Returns the balance for the given address

    :param address: The address to check
    """
    RequireIsAddress(address)
    key = getBalanceKey(address)
    return Get(ctx, key) + 0


def transfer(from_address, to_address, amount):
    """
    Transfers an amount of tokens from from_acct to to_acct

    :param from_address: The address sending the tokens
    :param to_address: The address receiving the tokens
    :param amount: The amount being transferred
    Returns True on success, otherwise raises an exception
    """
    RequireIsAddress(from_address)
    RequireIsAddress(to_address)
    RequireWitness(from_address)
    Require(amount >= 0)

    fromKey = getBalanceKey(from_address)
    fromBalance = Get(ctx, fromKey)
    Require(fromBalance >= amount)
    if amount == fromBalance:
        Delete(ctx, fromKey)
    else:
        Put(ctx, fromKey, fromBalance - amount)

    toKey = getBalanceKey(to_address)
    toBalance = Get(ctx, toKey)
    Put(ctx, toKey, toBalance + amount)

    TransferEvent(from_address, to_address, amount)
    return True


def transferMulti(args):
    """
    Allows the transferring of tokens from multiple addresses to multiple other addresses with multiple amounts of tokens

    :param args: An array of arrays in the format of  [[from, to, amount] ... [from_n, to_n, amount_n]]
    Returns True on success, otherwise raises an exception
    """
    for p in args:
        Require(len(p) == 3)
        Require(transfer(p[0], p[1], p[2]))
    return True


def approve(owner, spender, amount):
    """
    Allows the spender to transfer tokens on behalf of the owner

    :param owner: The address granting permissions
    :param spender: The address that will be able to transfer the owner's tokens
    :param amount: The amount of tokens being enabled for transfer
    Returns True on success, otherwise raises an exception
    """
    RequireIsAddress(owner)
    RequireIsAddress(spender)
    RequireWitness(owner)
    Require(amount >= 0)
    Require(amount <= balanceOf(owner))

    key = getApprovalKey(owner, spender)
    Put(ctx, key, amount)

    ApprovalEvent(owner, spender, amount)
    return True


def transferFrom(spender, from_address, to_address, amount):
    """
    The spender address sends amount of tokens from the from_address to the to_address

    :param spender: The address sending the funds
    :param from_address: The address whose funds are being sent
    :param to_address: The receiving address
    :param amount: The amounts of tokens being transferred
    Returns True on success, otherwise raises an exception
    """
    RequireIsAddress(spender)
    RequireIsAddress(from_address)
    RequireIsAddress(to_address)
    RequireWitness(spender)
    Require(amount >= 0)

    fromKey = getBalanceKey(from_address)
    fromBalance = Get(ctx, fromKey)
    Require(amount <= fromBalance)

    approveKey = getApprovalKey(from_address, spender)
    approvedAmount = Get(ctx, approveKey)
    Require(amount <= approvedAmount)

    if amount == approvedAmount:
        Delete(ctx, approveKey)
    else:
        Put(ctx, approveKey, approvedAmount - amount)

    if amount == fromBalance:
        Delete(ctx, fromKey)
    else:
        Put(ctx, fromKey, fromBalance - amount)

    toKey = getBalanceKey(to_address)
    toBalance = Get(ctx, toKey)
    Put(ctx, toKey, toBalance + amount)

    TransferEvent(from_address, to_address, amount)
    return True


def allowance(owner, spender):
    """
    Gets the amount of tokens that the spender is allowed to spend on behalf of the owner
    :param owner: The owner address
    :param spender:  The spender address
    """
    key = getApprovalKey(owner, spender)
    return Get(ctx, key) + 0

# Helpers

def getBalanceKey(address):
    '''
    Gets the storage key for looking up a balance

    :param address: The address to get the balance key for
    '''
    key = concat(BALANCE_PREFIX, address) # pylint: disable=E0602
    return key


def getApprovalKey(owner, spender):
    '''
    Gets the storage key for looking up an approval

    :param owner: The owner address for the approval
    :param spender: The spender address for the approval
    '''
    key = concat(concat(APPROVE_PREFIX, owner), spender) # pylint: disable=E0602
    return key

# Admin Methods

def init():
    """
    Initializes the contract
    """

    RequireIsAddress(OWNER)
    RequireWitness(OWNER)
    Require(totalSupply() == 0)

    total = TOTAL_AMOUNT * DECIMAL_MULTIPLIER
    Put(ctx, SUPPLY_KEY, total)

    key = getBalanceKey(OWNER)
    Put(ctx, key, total)

    TransferEvent(None, OWNER, total)
    return True

# Require Module

def RequireIsAddress(address):
    '''
    Raises an exception if the given address is not the correct length.

    :param address: The address to check.
    '''
    Require(len(address) == 20, "Address has invalid length")


def RequireWitness(address):
    '''
    Raises an exception if the given address is not a witness.

    :param address: The address to check.
    '''
    Require(CheckWitness(address), "Address is not witness")


def Require(expr, message="There was an error"):
    '''
    Raises an exception if the given expression is false.

    :param expr: The expression to evaluate.
    :param message: The error message to log.
    '''
    if not expr:
        Log(message)
        raise Exception(message)
