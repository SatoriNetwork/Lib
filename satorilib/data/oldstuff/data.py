'''
the DataService uses zeroMQ to communicate, manages the data on disk,
providing it to neuron or engine on demand. uses the satorilib.disk api

api basics:
    - accept StreamId objects and returns their data

refactor steps:
    neuron start.py creates self.caches disctionary,
        that needs to live in the engine.
    when creating the caches object in the engine
        we should use the data service to fill the cache
    we have to build out the data service to get the needed data
    we have to build out the data service to supply the needed data via zeromq
        (df -> zeromq messages -> df reassembled on the other side)

stretch:
    we should think about writing a SqliteManager module next to the CSVManager
        at the disk api level, allowing the DataService to use that
    this would require that data always be saved in the sqlite database instead.
'''

# from satorilib.disk import something


class DataService(object):
    def __init__(
        self,
        *args, **kwargs
    ):

        # self.listen()
        pass
