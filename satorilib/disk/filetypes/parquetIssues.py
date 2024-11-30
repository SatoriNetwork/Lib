'''
notice when we had the parquet situation we had to do stuff like this which 
should have been done in the disk module, but was instead done at higher levels:
'''
# def getHistoryOf(self, streamId: StreamId):

#     def tellModelsAboutNewHistory():
#         tellEm = False
#         for model in self.start.engine.models:
#             if model.variable == streamId:
#                 tellEm = True
#             else:
#                 for target in model.targets:
#                     if target == streamId:
#                         tellEm = True
#         if tellEm:
#             model.inputsUpdated.on_next(True)

#     def gatherUnknownHistory() -> list[PeerMessage]:

#         def lookThoughIncrementals(timestamp: str, value: str):
#             ''' gets a df of the incrementals and looks for the observation'''
#             df = diskApi.read(aggregate=False)
#             if timestamp in df.index:
#                 return eq(df.loc[timestamp].values[0], value)
#             return False

#         def lookThoughAggregates(timestamp: str, value: str):
#             ''' sees if the timestamp exists in the aggregate '''
#             # only checks to see if the timestamp exists, not the value
#             # if we want to check the value to we have to read in the full file
#             return diskApi.timeExistsInAggregate(timestamp)

#         msg: PeerMessage = topic.getOneObservation(time=now())
#         incrementalsChecked = False
#         msgsToSave = []
#         while msg is not None and not msg.isNoneResponse():
#             # here we have a situation. we should tell the data manager about
#             # this and let it handle it. but this stream isnt' the best way to
#             # do that because it is built for only new realtime data in mind:
#             # start.engine.data.newData.on_next(
#             #    ObservationFromPeerMessage.fromPeerMessage(msg))
#             # well. we have history datapoints that we may or may not already
#             # have, furthermore, if we do already have it, we should probably
#             # top asking... so what do we do here? technically all ipfs sync
#             # is save the entire ipfs history to disk using:
#             # diskApi.path(aggregate=None, temp=True)
#             # then combines it with what is currently known, on disk, using:
#             # diskApi.compress(includeTemp=True)
#             # but we don't want to do that because we dont' want to download the
#             # entire history. we want to stop once we start seeing data we
#             # already have. so we really need 2-way communication with the data
#             # manager of the engine... so we need to listen to a stream on which
#             # it can respond. which is pretty nasty. so we'll think about it...
#             # ok, I think I know what to do. we don't ask or notify the data
#             # manager at all. instead we look at the data, one row at a time
#             # until we find this observation or don't. if we don't find it, we
#             # we know we can stop asking, if we don't find it, we save it as an
#             # incremental, and loop until we reach the end or find one we have.
#             # then we combine the incrementals with the aggregate and compress
#             # and if we have to do that, we tell the models to update. done.
#             # we'll have to look through the incrementals first, then the
#             # aggregates. and keep a flag if we get into aggregates, so we don't
#             # hit incrementals each time we loop.
#             if not incrementalsChecked:
#                 incrementalsChecked = True  # only on the first loop
#                 if lookThoughIncrementals(msg.observationTime, msg.data):
#                     break
#                 else:
#                     found = lookThoughAggregates(
#                         msg.observationTime, msg.data)
#                     if found:
#                         break
#                     else:
#                         msgsToSave.append(msg)
#             msg = topic.getOneObservation(
#                 time=timestampToDatetime(msg.observationTime))
#         return msgsToSave

#     def findTopic():
#         return self.peer.topicFor(streamId)
#         # if topic is None: return False  # error?

#     topic = findTopic()
#     if topic:
#         diskApi = disk.Disk(id=streamId)
#         msgs = gatherUnknownHistory()
#         if len(msgs) > 0:
#             # save
#             diskApi.append(msgsToDataframe(msgs))
#             tellModelsAboutNewHistory()


# def compress():
#                 '''
#                 compress if the number of incrementals is high
#                 could make this responsive to /get/stream/cadence if we wanted.
#                 don't compress if we're currently busy with downloading the ipfs
#                 compress on multiples of 100, that way everyone might compress
#                 at the same time and has the same ipfs.
#                 '''
#                 disk = Disk(id=observation.key)
#                 if len(disk.incrementals()) % 3 == 0:
#                     try:
#                         disk.compress()
#                     except Exception as e:
#                         logging.error('ERROR: unable to compress:', e)
