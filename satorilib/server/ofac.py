import requests
from satorilib import logging


def requestPermission() -> bool:
    return True
    response = requests.get('http://195.26.255.217:3005/validate-ip')
    try:
        response.raise_for_status()
    except Exception as e:
        logging.error(f"err: {e} server returned status code {response.status_code}: {response.text}")
        return False
    if 200 <= response.status_code <= 399 and response.text.lower() == 'true':
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False


def reportTxid(txid) -> bool:
    return True
    response = requests.post('http://195.26.255.217:3005/register-txid', json={'txid': txid})
    try:
        response.raise_for_status()
    except Exception as e:
        logging.error(f"err: {e} server returned status code {response.status_code}: {response.text}")
        return False
    if 200 <= response.status_code <= 399 and response.text.lower() == 'true':
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False


def verifyTxid(txid) -> bool:
    return True
    response = requests.post('http://195.26.255.217:3005/verify-txid', json={'txid': txid})
    try:
        response.raise_for_status()
    except Exception as e:
        logging.error(f"err: {e} server returned status code {response.status_code}: {response.text}")
        return False
    if 200 <= response.status_code <= 399 and response.text.lower() == 'true':
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False
