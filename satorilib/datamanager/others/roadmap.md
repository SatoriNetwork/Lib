'''

---
refactor and test
---
create endpoint for the DataManager's DataClient to notify the DataManager's DataServer that it is it's special DataClient and needs to know what to subscribe to when it's ( Done )
---
create rendevous endpoint - Jordan
---
create DataManager startup process - it's a separate process, starts up before the Neuron
- subscriptionsinside start.sh data.py should run as a background process
- create DataServer object and listen for instructions forever (data.py) ( Done )
--- 
integrate with neuron-dataClient
- get DataServer Ip ( Done )
  - dsIp = config.get().get('peer ip', '0.0.0.0') ( Done )
  - if that doesn't work... dsIp = start.server.getPublicIp().text.split()[-1] # /ip ( Done )
- put a DataClient singleton object in the neuron ( Done )
  - during the startup process in init.py (StartupDag singleton) instanteate a DataClient ( Done )
- connect to our DataServer on startup ( Done )
- stay connected/reconnect on disconnect to our own DataServer  ( Done )
- tell DataServer the streams of our subscriptions and publications (that we got from checkin) ( Done )
- tell DataServer the peers of our subscriptions (who publishes, and who subscribes to the data we want) (we get this from "rendezvous" call) ( Done )
  - payload: {table_uuid: [publisher ip, subscirber ip, subscirber ip, ...]} ( Done )
- subscribe to our own list of subscriptions and publications for UI ( )
- (implement later) ask for any data necessary on demand

integrate with engine-dataClient
- get DataServer Ip ( Done )
  - dsIp = (from satorineuron import config) config.get().get('peer ip', '0.0.0.0') ( Done )
  - if that doesn't work... dsIp = start.server.getPublicIp().text.split()[-1] # /ip ( Done )
- put a DataClient singleton object in the engine ( Done )
- connect to our DataServer on startup ( Done )
- ask DataServer for streams along with peer information (must somehow know how to contact our data server) ( Done )
  - payload: {table_uuid: [publisher ip, subscirber ip, subscirber ip, ...]} ( Done )
- ask DataServer for our current known data of our streams (from disk, full df) ( Done )

choose peer to connect to
- handle subscriber list
    - filter our own ip out of the subscriber list
    - randomize subscriber list (shuffle payload[table_uuid][1:])
  - connect to a peer for a stream
    - attempt connection to the source first (publisher)
      - if able to connect, make sure they have the stream we're looking for available for subscribing to
        - if not, keep looking for a valid peer
    - go down the subscriber list until you find one...

- engine data client asks external data servers for subscriptions
  
  - and sync (for now just ask for their entire dataset every time)
    - if it's different than the df we got from our own dataserver, then tell dataserver to save this instead
  - and subscribe to the stream so we get the information
    - whenever we get an observation on this stream, pass to the DataServer
- continually generate predictions for prediction publication streams and pass that to DataServer ( Done )



---
subsume all logic currently used in engine for managing data on disk
---
make sure it's all working together
---
p2p - get histories (just request history of data)
p2p - replace pubsub servers (start using subscriptions)
---
relay if necessary?
- requires mesh network
---
datastreams are immutable, they don't change, so if there's anything that does change 
(like the target changes because the api became different) then we have to build a new
stream, for optimization purposes we may want to be able to link back to the old stream
and we still want to be able to do that in a decentralized manner, so the new stream 
could have an optional .prior attribute which is the UUID of the old stream. this way
we could automatically deploy new streams associated with the correct histories.
---

'''