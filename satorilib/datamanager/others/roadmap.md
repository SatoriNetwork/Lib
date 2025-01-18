'''

---
refactor and test
---
create endpoint for the DataManager's DataClient to notify the DataManager's DataServer that it is it's special DataClient and needs to know what to subscribe to when it's ( Done )
---
create rendevous endpoint - Jordan
---
create DataManager startup process - it's a separate process, starts up before the Neuron
- run DataManager app in the background before neuron starts                  # TODO : inside start.sh data.py should run as a background process
- create DataServer object and listen for instructions forever (data.py)
--- 
integrate with neuron-dataClient
- put a DataClient singleton object in the neuron
  - during the startup process in init.py (StartupDag singleton) instanteate a DataClient
- connect to our DataServer on startup
- stay connected/reconnect on disconnect to our own DataServer        # TODO : reconnect stuff
- tell DataServer the streams of our subscriptions and publications (that we got from checkin)
- tell DataServer the peers of our subscriptions (who publishes, and who subscribes to the data we want) (we get this from "rendezvous" call) 
  - payload: {table_uuid: [publisher ip, random subscirber ip, random subscirber ip, ...]}
- subscribe to our own list of subscriptions and publications for UI 
- (implement later) ask for any data necessary on demand

integrate with engine-dataClient
- put a DataClient singleton object in the engine
- connect to our DataServer on startup
- ask DataServer for streams along with peer information (must somehow know how to contact our data server)
  - payload: {table_uuid: [publisher ip, random subscirber ip, random subscirber ip, ...]}
- ask DataServer for our current known data of our streams (from disk, full df)
- engine data client asks external data servers for subscriptions
  - connect to a peer for a stream 
    - attempt connection to the source first
      - if able to connect, make sure they have the stream we're looking for available for subscribing to
        - if not, keep looking for a valid peer
    - go down the list of othe subscribers until you find one...
  - and sync (for now just ask for their entire dataset every time)
    - if it's different than the df we got from our own dataserver, then tell dataserver to save this instead
  - and subscribe to the stream so we get the information
- continually generate predictions for prediction publication streams and pass that to DataServer

---
subsume all logic currently used in engine for managing data on disk
---
make sure it's all working together
---
p2p - get histories (just request history of data)
p2p - replace pubsub servers (start using subscriptions)
---
relay if necessary?
---

'''