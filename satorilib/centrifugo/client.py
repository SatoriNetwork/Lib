import asyncio
import logging
from centrifuge import Client, SubscriptionEventHandler, ClientEventHandler
from centrifuge import PublicationContext, ConnectedContext, DisconnectedContext
from typing import Optional, Callable, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CentrifugoClientEvents(ClientEventHandler):
    def __init__(self, 
                 on_connected_callback: Optional[Callable[[ConnectedContext], Any]] = None,
                 on_disconnected_callback: Optional[Callable[[DisconnectedContext], Any]] = None):
        """
        Initialize with optional callback functions for connection events.
        
        Args:
            on_connected_callback: Function to call when connected (takes ConnectedContext)
            on_disconnected_callback: Function to call when disconnected (takes DisconnectedContext)
        """
        self.on_connected_callback = on_connected_callback
        self.on_disconnected_callback = on_disconnected_callback
    
    async def on_connected(self, ctx: ConnectedContext):
        logger.info(f"Centrifugo Connected! Client ID: {ctx.client}")
        if self.on_connected_callback:
            try:
                if asyncio.iscoroutinefunction(self.on_connected_callback):
                    await self.on_connected_callback(ctx)
                else:
                    self.on_connected_callback(ctx)
            except Exception as e:
                logger.error(f"Error in on_connected callback: {e}")
        
    async def on_disconnected(self, ctx: DisconnectedContext):
        logger.info(f"Centrifugo Disconnected: {ctx.reason}")
        if self.on_disconnected_callback:
            try:
                if asyncio.iscoroutinefunction(self.on_disconnected_callback):
                    await self.on_disconnected_callback(ctx)
                else:
                    self.on_disconnected_callback(ctx)
            except Exception as e:
                logger.error(f"Error in on_disconnected callback: {e}")


class CentrifugoSubscriptionEventHandler(SubscriptionEventHandler):
    def __init__(self, 
                 on_publication_callback: Optional[Callable[[PublicationContext], Any]] = None,
                 stream_id: Optional[str] = None,
                 value_callback: Optional[Callable[[Any, dict], Any]] = None):
        """
        Initialize with optional callback functions for publication events.
        
        Args:
            on_publication_callback: Function to call when publication received (takes PublicationContext)
            stream_id: Optional identifier for the stream (for logging purposes)
            value_callback: Function to call with extracted value and data (takes value, data)
        """
        self.on_publication_callback = on_publication_callback
        self.stream_id = stream_id
        self.value_callback = value_callback
    
    async def on_publication(self, ctx: PublicationContext):
        data = ctx.pub.data
        
        # Log with stream ID if provided
        if self.stream_id:
            logger.info(f"Stream {self.stream_id} received: {data}")
        else:
            logger.info(f"Centrifugo Publication: {data}")
        
        # Call external callback if provided
        if self.on_publication_callback:
            try:
                if asyncio.iscoroutinefunction(self.on_publication_callback):
                    await self.on_publication_callback(ctx)
                else:
                    self.on_publication_callback(ctx)
            except Exception as e:
                logger.error(f"Error in on_publication callback: {e}")
        
        # Handle value extraction and callback (DataStreamHandler functionality)
        if self.value_callback and ('value' in data or 'input' in data):
            value = data.get('value') or data.get('input')
            logger.info(f"Processing value: {value}")
            
            try:
                if asyncio.iscoroutinefunction(self.value_callback):
                    await self.value_callback(value, data)
                else:
                    self.value_callback(value, data)
            except Exception as e:
                logger.error(f"Error in value_callback: {e}")


async def create_centrifugo_client(ws_url: str, token: str, 
                                 on_connected_callback: Optional[Callable[[ConnectedContext], Any]] = None,
                                 on_disconnected_callback: Optional[Callable[[DisconnectedContext], Any]] = None) -> Client:
    """Create and return a configured Centrifugo client
    
    Args:
        ws_url: WebSocket URL for Centrifugo
        token: Authentication token
        on_connected_callback: Optional callback function for connection events
        on_disconnected_callback: Optional callback function for disconnection events
    """
    
    async def get_token():
        return token

    return Client(
        ws_url,
        events=CentrifugoClientEvents(
            on_connected_callback=on_connected_callback,
            on_disconnected_callback=on_disconnected_callback),
        get_token=get_token)


def create_subscription_handler(on_publication_callback: Optional[Callable[[PublicationContext], Any]] = None,
                              stream_id: Optional[str] = None,
                              value_callback: Optional[Callable[[Any, dict], Any]] = None) -> CentrifugoSubscriptionEventHandler:
    """Create and return a configured subscription event handler
    
    Args:
        on_publication_callback: Optional callback function for publication events
        stream_id: Optional identifier for the stream (for logging purposes)
        value_callback: Function to call with extracted value and data (takes value, data)
    """
    return CentrifugoSubscriptionEventHandler(
        on_publication_callback=on_publication_callback,
        stream_id=stream_id,
        value_callback=value_callback
    )


async def subscribe_to_stream(client: Client, stream_id: str, 
                            events: CentrifugoSubscriptionEventHandler) -> Any:
    """Subscribe to a stream using the client
    
    Args:
        client: The Centrifugo client
        stream_id: The stream ID to subscribe to
        events: The subscription event handler
        
    Returns:
        The subscription object
    """
    channel = f"streams:{stream_id}"
    subscription = client.new_subscription(channel, events=events)
    await subscription.subscribe()
    return subscription


def publish_to_stream_rest(stream_uuid: str, data: dict, token: str):
    import requests
    response = requests.post(
        'https://gatekeeper.satorinet.io/api/publish',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'channel': f'streams:{stream_uuid}',
            'data': data
        }
    )
    return response