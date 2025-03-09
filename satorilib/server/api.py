'''
this file contains data structures for communication between the server and
Satroi Neurons
'''

# from marshmallow import Schema, fields, validate
# from marshmallow import ValidationError

# class ProposalSchema(Schema):
# id = fields.Integer(
# required=False,
# allow_none=True,
# description='The unique identifier for the proposal')
# wallet_id = fields.Integer(
# required=False,
# allow_none=True,
# description='proposer')
# title = fields.String(
# required=True,
# allow_none=True,
# description='The title of the proposal')
# description = fields.String(
# required=True,
# allow_none=True,
# description='A detailed description of the proposal')
# proposal_date = fields.DateTime(
# required=False,
# allow_none=True,
# description='The date when the proposal was submitted')
# complete_date = fields.DateTime(
# required=False,
# allow_none=True,
# description='when the proposed work will be finished')
# expires = fields.DateTime(
# required=False,
# allow_none=True,
# description='voting is closed')
# image_url = fields.String(
# required=False,
# allow_none=True,
# description='URL to an image related to the proposal')
# cost = fields.Float(
# required=True,
# allow_none=True,
# description='The monetary value or cost associated with the proposal')
# options = fields.String(
# required=False,
# allow_none=True,
# description='json list of strings')
# ts = fields.DateTime(
# required=False,
# allow_none=True,
# description='The date when the proposal was submitted')
# deleted = fields.DateTime(
# required=False,
# allow_none=True,
# description='deleted')
#
#
# class VoteSchema(Schema):
# proposal_id = fields.Integer(
# required=True,
# allow_none=True,
# description='The unique identifier of the proposal being voted on')
# wallet_id = fields.Integer(
# required=False,
# allow_none=True,
# description='The unique identifier of the user casting the vote')
# satori = fields.Float(
# required=False,
# allow_none=True,
# description='weight')
# vote = fields.String(
# required=True,
# allow_none=True,
# description='The vote: True for Yes, False for No')
# ts = fields.DateTime(
# required=False,
# allow_none=True,
# description='The date when the proposal was submitted')
# deleted = fields.DateTime(
# required=False,
# allow_none=True,
# description='deleted')


import datetime as dt


class ProposalSchema():
    id: int
    wallet_id: int
    title: str
    description: str
    proposal_date: dt.datetime
    complete_date: dt.datetime
    expires: dt.datetime
    image_url: str
    cost: float
    options: str
    ts: dt.datetime
    deleted: dt.datetime


class VoteSchema():
    proposal_id: int
    wallet_id: int
    satori: float
    vote: str
    ts: dt.datetime
    deleted: dt.datetime


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

    def get(self, key: str):
        return self.raw.get(key, self.wallet.get(key))
