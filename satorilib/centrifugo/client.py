import asyncio
import logging
from centrifuge import Client, ClientEventType, ConnectedContext, DisconnectedContext
from centrifuge import SubscribedContext, SubscriptionEventType, PublicationContext
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SatoriCentrifugoClient:
    def __init__(self, 
                 centrifugo_ws_url: str,
                 user_id: str,
                 token: Optional[str] = None):
        """
        Initialize the Satori Centrifugo client
        
        Args:
            centrifugo_ws_url: WebSocket URL for Centrifugo
            user_id: User ID for authentication
        """
        self.centrifugo_ws_url = centrifugo_ws_url
        self.user_id = user_id
        self.token: Optional[str] = token
        self.client: Optional[Client] = None
        self.subscriptions = {}
        
    async def connect(self) -> None:
        """
        Connect to Centrifugo WebSocket server
        """
        if not self.token:
            raise ValueError("Token is required to connect to Centrifugo")
            
        # Initialize Centrifugo client
        self.client = Client(
            address=self.centrifugo_ws_url,
            token=self.token
        )
        
        # Set up event handlers
        self.client.on(ClientEventType.CONNECTED, self._on_connected)
        self.client.on(ClientEventType.DISCONNECTED, self._on_disconnected)
        self.client.on(ClientEventType.ERROR, self._on_error)
        
        # Connect to Centrifugo
        await self.client.connect()
        logger.info("Connected to Centrifugo")
        
    async def disconnect(self) -> None:
        """
        Disconnect from Centrifugo server
        """
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Centrifugo")

    async def subscribe_to_stream(self, stream_id: str, callback=None) -> None:
        """
        Subscribe to a data stream
        
        Args:
            stream_id: The stream ID to subscribe to
            callback: Optional callback function for handling publications
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
            
        channel = f"streams:{stream_id}"
        
        # Create subscription
        subscription = self.client.new_subscription(channel)
        
        # Set up subscription event handlers
        subscription.on(SubscriptionEventType.SUBSCRIBED, self._on_subscribed)
        subscription.on(SubscriptionEventType.UNSUBSCRIBED, self._on_unsubscribed)
        subscription.on(SubscriptionEventType.ERROR, self._on_subscription_error)
        
        # Set up publication handler
        if callback:
            subscription.on(SubscriptionEventType.PUBLICATION, callback)
        else:
            subscription.on(SubscriptionEventType.PUBLICATION, self._default_publication_handler)
            
        # Subscribe
        await subscription.subscribe()
        
        # Store subscription for later reference
        self.subscriptions[stream_id] = subscription
        logger.info(f"Subscribed to stream: {stream_id}")
        
    async def publish_to_stream(self, stream_id: str, data: Dict[str, Any]) -> None:
        """
        Publish data to a stream
        
        Args:
            stream_id: The stream ID to publish to
            data: Data to publish (e.g., {"input": "0.9994234"})
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
            
        channel = f"streams:{stream_id}"
        
        try:
            await self.client.publish(channel, data)
            logger.info(f"Successfully published to stream {stream_id}: {data}")
        except Exception as e:
            logger.error(f"Failed to publish to stream {stream_id}: {e}")
            raise
            
    async def unsubscribe_from_stream(self, stream_id: str) -> None:
        """
        Unsubscribe from a data stream
        
        Args:
            stream_id: The stream ID to unsubscribe from
        """
        if stream_id in self.subscriptions:
            subscription = self.subscriptions[stream_id]
            await subscription.unsubscribe()
            del self.subscriptions[stream_id]
            logger.info(f"Unsubscribed from stream: {stream_id}")
        else:
            logger.warning(f"No active subscription found for stream: {stream_id}")
            
    # Event handlers
    async def _on_connected(self, ctx: ConnectedContext) -> None:
        """Handle connection event"""
        logger.info(f"Connected to Centrifugo. Client ID: {ctx.client}")
        
    async def _on_disconnected(self, ctx: DisconnectedContext) -> None:
        """Handle disconnection event"""
        logger.info(f"Disconnected from Centrifugo. Code: {ctx.code}, Reason: {ctx.reason}")
        
    async def _on_error(self, error: Exception) -> None:
        """Handle client error"""
        logger.error(f"Centrifugo client error: {error}")
        
    async def _on_subscribed(self, ctx: SubscribedContext) -> None:
        """Handle subscription success"""
        logger.info(f"Successfully subscribed to channel")
        
    async def _on_unsubscribed(self, ctx) -> None:
        """Handle unsubscription"""
        logger.info(f"Unsubscribed from channel. Code: {ctx.code}, Reason: {ctx.reason}")
        
    async def _on_subscription_error(self, error: Exception) -> None:
        """Handle subscription error"""
        logger.error(f"Subscription error: {error}")
        
    async def _default_publication_handler(self, ctx: PublicationContext) -> None:
        """Default handler for incoming publications"""
        logger.info(f"Received publication: {ctx.data}")
        
        # Check for prediction/observation data
        if 'value' in ctx.data or 'input' in ctx.data:
            value = ctx.data.get('value') or ctx.data.get('input')
            logger.info(f"Processing data value: {value}")
            # Add your data processing logic here
            

# Example usage
async def example_usage():
    """
    Example of how to use the SatoriCentrifugoClient
    """
    
    # Initialize client
    client = SatoriCentrifugoClient(
        centrifugo_ws_url="ws://centrifugo.satorinet.io/connection/websocket",
        user_id="12345")
    
    try:
        # Connect to Centrifugo
        await client.connect()
        
        # Custom publication handler
        async def my_data_handler(ctx: PublicationContext):
            print(f"Received data: {ctx.data}")
            if 'input' in ctx.data:
                prediction_value = ctx.data['input']
                print(f"New prediction: {prediction_value}")
                # Process the prediction here
        
        # Subscribe to a stream with custom handler
        await client.subscribe_to_stream("11451866", callback=my_data_handler)
        
        # Publish some data
        await client.publish_to_stream("11451866", {"input": "0.9994234"})
        
        # Keep the connection alive
        await asyncio.sleep(30)  # Run for 30 seconds
        
        # Unsubscribe and disconnect
        await client.unsubscribe_from_stream("11451866")
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"Error in example: {e}")
        await client.disconnect()

if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())