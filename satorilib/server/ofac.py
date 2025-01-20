import requests
import logging

def acceptTerms() -> bool:
    try:
        response = requests.post('http://195.26.255.217:3005/accept-tos')
        response.raise_for_status()
    except Exception as e:
        logging.error(f"err: {e} server returned status code {response.status_code}: {response.text}")
        return False
    if 200 <= response.status_code <= 399:
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False


def requestPermission() -> bool:
    try:
        response = requests.get('http://195.26.255.217:3005/validate-ip')
        response.raise_for_status()
    except Exception as e:
        logging.error(f"err: {e} server returned status code {response.status_code}: {response.text}")
        return False
    if 200 <= response.status_code <= 399 and response.text.lower() == 'true':
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False


def reportTxid(txid) -> bool:
    try:
        response = requests.post(
            'http://195.26.255.217:3005/validate-ip-txid',
            json={'txid': txid})
        response.raise_for_status()
    except Exception as e:
        logging.error(f"err: {e} server returned status code {response.status_code}: {response.text}")
        return False
    if 200 <= response.status_code <= 399 and response.text.lower() == 'true':
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False


def verifyTxid(txid) -> bool:
    try:
        response = requests.get(
            'http://195.26.255.217:3005/validate-txid',
            json={'txid': txid})
        response.raise_for_status()
    except Exception as e:
        logging.error(f"err: {e} server returned status code {response.status_code}: {response.text}")
        return False
    if 200 <= response.status_code <= 399 and response.text.lower() == 'true':
        return True
    logging.error(f"Server returned status code {response.status_code}: {response.text}")
    return False
