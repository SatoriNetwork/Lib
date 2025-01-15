import requests
from satorilib import logging


def requestPermission() -> bool:
    ''' sends a satori partial transaction to the server '''
    return True # mock
    response = requests.get('http://ofac.burnbridge.io/validate')
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error("unauth'ed server err:", response.text, e, color='red')
    if response.status_code == 200:
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False

def reportTxid(txid) -> bool:
    ''' Function to set the worker mining mode '''
    return True # mock
    response = requests.get(f'http://ofac.burnbridge.io/validate/{txid}')
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error("unauth'ed server err:", response.text, e, color='red')
    if response.status_code == 200:
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False
