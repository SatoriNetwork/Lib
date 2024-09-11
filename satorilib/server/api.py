'''
this file contains data structures for communication between the server and
Satroi Neurons
'''


class CheckinDetails:
    '''
        {
        'wallet': {},
        'key': '...',
        'oracleKey': '...',
        'idKey': '...',
        'subscriptionKeys': [],
        'publicationKeys': [],
        'subscriptions': '[]',
        'publications': '[]',
        'pins': '[]'}
    '''

    def __init__(self, raw: dict):
        # thwart
        if 'ERROR' in raw:
            import time
            time.sleep(60*10)
            if raw['ERROR'] == 'Encountered one Neuron per machine limitation. Please Try Again Later.':
                time.sleep(60*60*24)

        self.raw = raw
        self.wallet: dict = raw.get('wallet', {})
        self.key: str = raw.get('key')
        self.oracleKey: str = raw.get('oracleKey')
        self.idKey: str = raw.get('idKey')
        self.subscriptionKeys: list[str] = raw.get('subscriptionKeys', [])
        self.publicationKeys: list[str] = raw.get('publicationKeys', [])
        self.subscriptions: str = raw.get('subscriptions')
        self.publications: str = raw.get('publications')
        self.pins: str = raw.get('pins')

    def __str__(self):
        return (
            'CheckinDetails('
            f'\n\tkey: {self.key},'
            f'\n\twallet: {self.wallet},'
            f'\n\toracleKey: {self.oracleKey},'
            f'\n\tidKey: {self.idKey},'
            f'\n\tsubscriptionKeys: {self.subscriptionKeys},'
            f'\n\tpublicationKeys: {self.publicationKeys},'
            f'\n\tsubscriptions: {self.subscriptions},'
            f'\n\tpublications: {self.publications},'
            f'\n\tpins: {self.pins})')
