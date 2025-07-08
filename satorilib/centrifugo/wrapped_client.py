''' old code
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from centrifuge import (
    Client,
    ClientEventHandler,
    SubscriptionEventHandler,
    ConnectedContext,
    DisconnectedContext,
    PublicationContext,
    SubscribedContext,
    UnsubscribedContext,
    ErrorContext,
    CentrifugeError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SatoriCentrifugoClient:
    """
    Satori Centrifugo WebSocket client wrapper
    Maintains the same interface as your original implementation
    """
    
    def __init__(self, 
                 centrifugo_ws_url: str,
                 user_id: str,
                 token: Optional[str] = None):
        """
        Initialize the Satori Centrifugo client
        
        Args:
            centrifugo_ws_url: WebSocket URL for Centrifugo
            user_id: User ID for authentication
            token: JWT token for authentication
        """
        self.centrifugo_ws_url = centrifugo_ws_url
        self.user_id = user_id
        self.token = token
        self.client: Optional[Client] = None
        self.subscriptions = {}
        
        # Create event handlers
        self._client_events = self._create_client_event_handler()
        
    def _create_client_event_handler(self):
        """Create client event handler with proper method bindings"""
        class ClientEvents(ClientEventHandler):
            def __init__(self, parent):
                self.parent = parent
                
            async def on_connected(self, ctx: ConnectedContext) -> None:
                await self.parent._on_connected(ctx)
                
            async def on_disconnected(self, ctx: DisconnectedContext) -> None:
                await self.parent._on_disconnected(ctx)
                
            async def on_error(self, ctx: ErrorContext) -> None:
                await self.parent._on_error(ctx.error)
                
        return ClientEvents(self)
    
    def _create_subscription_event_handler(self, callback=None):
        """Create subscription event handler with optional callback"""
        parent = self
        
        class SubscriptionEvents(SubscriptionEventHandler):
            async def on_publication(self, ctx: PublicationContext) -> None:
                if callback:
                    await callback(ctx)
                else:
                    await parent._default_publication_handler(ctx)
                    
            async def on_subscribed(self, ctx: SubscribedContext) -> None:
                await parent._on_subscribed(ctx)
                
            async def on_unsubscribed(self, ctx: UnsubscribedContext) -> None:
                await parent._on_unsubscribed(ctx)
                
            async def on_error(self, ctx: ErrorContext) -> None:
                await parent._on_subscription_error(ctx.error)
                
        return SubscriptionEvents()
        
    async def get_token(self) -> str:
        """Token getter for centrifuge-python client"""
        if not self.token:
            raise ValueError("Token is required to connect to Centrifugo")
        return self.token
        
    async def connect(self) -> None:
        """
        Connect to Centrifugo WebSocket server
        """
        if not self.token:
            raise ValueError("Token is required to connect to Centrifugo")
            
        # Initialize Centrifugo client with the new library syntax
        self.client = Client(
            self.centrifugo_ws_url,
            events=self._client_events,
            get_token=self.get_token,
        )
        
        # Connect to Centrifugo
        await self.client.connect()
        
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
        
        # Create subscription with event handler
        subscription = self.client.new_subscription(
            channel,
            events=self._create_subscription_event_handler(callback)
        )
        
        # Subscribe
        await subscription.subscribe()
        
        # Store subscription for later reference
        self.subscriptions[stream_id] = subscription
        
    async def publish_to_stream(self, stream_id: str, data: Dict[str, Any]) -> None:
        """
        Publish data to a stream
        
        Args:
            stream_id: The stream ID to publish to
            data: Data to publish (e.g., {"input": "0.9994234"})
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")
            
        if stream_id in self.subscriptions:
            # Use the subscription's publish method
            subscription = self.subscriptions[stream_id]
            try:
                await subscription.publish(data)
                logger.info(f"Successfully published to stream {stream_id}: {data}")
            except Exception as e:
                logger.error(f"Failed to publish to stream {stream_id}: {e}")
                raise
        else:
            logger.warning(f"Not subscribed to stream {stream_id}. Subscribe first for better reliability.")
            # You might want to subscribe first or handle this differently
            raise RuntimeError(f"Not subscribed to stream {stream_id}")
            
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
            
    # Event handlers - keeping your original interface
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
        logger.info(f"Successfully subscribed to channel: {ctx.channel}")
        
    async def _on_unsubscribed(self, ctx: UnsubscribedContext) -> None:
        """Handle unsubscription"""
        logger.info(f"Unsubscribed from channel: {ctx.channel}. Code: {ctx.code}, Reason: {ctx.reason}")
        
    async def _on_subscription_error(self, error: Exception) -> None:
        """Handle subscription error"""
        logger.error(f"Subscription error: {error}")
        
    async def _default_publication_handler(self, ctx: PublicationContext) -> None:
        """Default handler for incoming publications"""
        logger.info(f"Received publication: {ctx.pub.data}")
        
        # Check for prediction/observation data - keeping your logic
        if 'value' in ctx.pub.data or 'input' in ctx.pub.data:
            value = ctx.pub.data.get('value') or ctx.pub.data.get('input')
            logger.info(f"Processing data value: {value}")
            # Add your data processing logic here


# Example usage - keeping your original example structure
async def example_usage():
    """
    Example of how to use the SatoriCentrifugoClient
    """
    
    # Initialize client - exactly as you were doing
    client = SatoriCentrifugoClient(
        centrifugo_ws_url="ws://centrifugo.satorinet.io/connection/websocket",
        user_id="12345",
        token="your_jwt_token_here"  # Pass token at initialization
    )
    
    try:
        # Connect to Centrifugo
        await client.connect()
        
        # Custom publication handler - keeping your pattern
        async def my_data_handler(ctx: PublicationContext):
            print(f"Received data: {ctx.pub.data}")
            if 'input' in ctx.pub.data:
                prediction_value = ctx.pub.data['input']
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
        if client.client:
            await client.disconnect()


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())
'''