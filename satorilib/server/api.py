'''
this file contains data structures for communication between the server and
Satroi Neurons
'''

from marshmallow import Schema, fields, validate


class ProposalSchema(Schema):
    id = fields.String(
        required=True, description='The unique identifier for the proposal')
    title = fields.String(
        required=True, description='The title of the proposal')
    description = fields.String(
        required=True, description='A detailed description of the proposal')
    proposal_date = fields.DateTime(
        required=True, description='The date when the proposal was submitted')
    complete_date = fields.DateTime(
        description='The date when the proposal was completed or closed')
    value = fields.Float(
        required=True, description='The monetary value or cost associated with the proposal')
    image_url = fields.String(
        description='URL to an image related to the proposal')
    yes_votes = fields.Integer(
        description='The number of yes votes for this proposal')
    no_votes = fields.Integer(
        description='The number of no votes for this proposal')


class VoteSchema(Schema):
    proposal_id = fields.String(
        required=True, description='The unique identifier of the proposal being voted on')
    user_id = fields.String(
        required=True, description='The unique identifier of the user casting the vote')
    vote = fields.Boolean(
        required=True, description='The vote: True for Yes, False for No')

# api version 1.0:


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
        self.wallet: dict = raw.get('wallet')
        self.key: str = raw.get('key')
        self.oracleKey: str = raw.get('oracleKey')
        self.idKey: str = raw.get('idKey')
        self.subscriptionKeys: list[str] = raw.get('subscriptionKeys')
        self.publicationKeys: list[str] = raw.get('publicationKeys')
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
