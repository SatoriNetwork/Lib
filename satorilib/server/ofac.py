from typing import Union
import requests
import logging


class OfacServer():
    @staticmethod
    def call(
        fn: callable,
        endpoint: str,
        json: Union[dict, None] = None,
        expectedResponse: Union[str, None] = None
    ) -> bool:
        try:
            response = fn(f'http://195.26.255.217/{endpoint}', json=json)
            try:
                response.raise_for_status()
            except Exception as e:
                logging.error(
                    f"err: {e} server returned status code {response.status_code}: {response.text}")
                return False
            if (
                200 <= response.status_code <= 399 and (
                    expectedResponse is None or
                    response.text.lower() == expectedResponse.lower())
            ):
                return True
            logging.error(
                f"Server returned status code {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"unable to reach OFAC server: {e}")
        return False

    @staticmethod
    def acceptTerms() -> bool:
        return OfacServer.call(
            fn=requests.post,
            endpoint='accept-tos')

    @staticmethod
    def requestPermission() -> bool:
        return OfacServer.call(
            fn=requests.get,
            endpoint='validate-ip',
            expectedResponse='true')

    @staticmethod
    def reportTxid(txid) -> bool:
        return OfacServer.call(
            fn=requests.post,
            endpoint='validate-ip-txid',
            expectedResponse='true',
            json={'txid': txid})

    @staticmethod
    def verifyTxid(txid) -> bool:
        return OfacServer.call(
            fn=requests.get,
            endpoint='validate-txid',
            expectedResponse='true',
            json={'txid': txid})
