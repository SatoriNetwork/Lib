
import os
import joblib
from satorilib import logging
from satorilib.concepts import StreamId
from satorilib.utils.hash import generatePathId
from satorilib.interfaces.model import ModelDataDiskApi, ModelDiskApi
from satorilib.disk.utils import safetify
from satorilib.disk.wallet import WalletApi


class ModelApi(ModelDiskApi):

    config = None

    @classmethod
    def setConfig(cls, config):
        cls.config = config

    @staticmethod
    def defaultModelPath(streamId: StreamId):
        return safetify(WalletApi.config.root(
            '..', 'models', generatePathId(streamId=streamId) + '.joblib'))

    @staticmethod
    def save(
        model,
        modelPath: str = None,
        streamId: StreamId = None,
        hyperParameters: list = None,
        chosenFeatures: list = None,
    ):
        ''' save to joblib file '''
        def appendAttributes(model, hyperParameters: list = None, chosenFeatures: list = None):
            if hyperParameters is not None:
                model.savedHyperParameters = hyperParameters
            if chosenFeatures is not None:
                model.savedChosenFeatures = chosenFeatures
            return model

        modelPath = modelPath or WalletApi.config.modelPath(
            generatePathId(streamId=streamId))
        safetify(modelPath)
        model = appendAttributes(model, hyperParameters, chosenFeatures)
        joblib.dump(model, modelPath)

    @staticmethod
    def load(modelPath: str = None, streamId: StreamId = None):
        modelPath = modelPath or WalletApi.config.modelPath(
            generatePathId(streamId=streamId))
        if os.path.exists(modelPath):
            try:
                return joblib.load(modelPath)
            except Exception as e:
                # returning False should overwrite the problematic model
                os.remove(modelPath)
                # logging.error('model err', modelPath, streamId, e)
        return False

    @staticmethod
    def getModelRootSize(modelPath: str = None):
        total = 0
        with os.scandir(modelPath) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += ModelApi.getModelRootSize(entry.path)
        return total

    @staticmethod
    def getModelSize(modelPath: str = None):
        if os.path.isfile(modelPath):
            return os.path.getsize(modelPath)
        elif os.path.isdir(modelPath):
            return ModelApi.getModelRootSize(modelPath)
