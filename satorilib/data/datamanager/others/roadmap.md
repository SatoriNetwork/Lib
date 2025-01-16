'''

---
refactor and test
---
create endpoint for the DataManager's DataClient to notify the DataManager's DataServer that it is it's special DataClient and needs to know what to subscribe to when it's ( Done )
---
create a server - rendezvous server
---
create DataManager startup process - it's a separate process, starts up before the Neuron
- run DataManager app in the background before neuron starts
- create DataServer object and listen for instructions forever (data.py)
--- 
integrate with neuron-dataClient
- put a DataClient singleton object in the neuron
  - during the startup process in init.py (StartupDag singleton) instanteate a DataClient
- connect to our DataServer on startup
- stay connected/reconnect on disconnect to our own DataServer
- tell DataServer the streams of our subscriptions and publications (that we got from checkin)
- tell DataServer the peers of our subscriptions (who publishes, and who subscribes to the data we want) (we get this from "rendezvous" call)
- ask DataServer to subscribe to the streams we want to hear about and stay current on them
  - connect to a peer for a stream 
    - attempt connection to the source first
    - go down the list of othe subscribers until you find one...
  - and sync
    - see if we're already up to date
    - if not get the data we're missing
  - and subscribe to the stream so we get the information
- continually get updates on the real-world publication streams and pass that to DataServer

integrate with engine-dataClient
- put a DataClient singleton object in the engine
- connect to our DataServer on startup
- ask DataServer for streams (must know my neuron id or something)
- ask DataServer for our current known data of our streams (from disk)
- subscribes to streams 
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