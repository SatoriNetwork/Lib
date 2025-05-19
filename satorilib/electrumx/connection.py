import ssl
import socket
import logging

logging.basicConfig(level=logging.INFO)


class ElectrumxConnection:
    def __init__(
        self,
        host: str,
        port: int,
        ssl: bool = False,
        timeout: int = 60*10,
        initializeConnection: bool = True,
    ):
        self.host = host
        self.port = port
        self.ssl = port == 50002 or ssl
        self.timeout = timeout
        self.isConnected = False
        self.connection: socket.socket = None
        self.createConnectionObject()
        if initializeConnection:
            self.connect()

    def connected(self) -> bool:
        if self.connection is None:
            self.isConnected = False
            return False
        if self.closed():
            self.isConnected = False
            return False
        return True

    def closed(self) -> bool:
        ''' we closed the connection '''
        return self.connection._closed

    def reconnect(self) -> bool:
        try:
            self.disconnect()
            self.connect()
            return True
        except Exception as e:
            logging.debug(
                f'error reconnecting to {self.host}:{str(self.port)} {e}')
            return False

    def createConnectionObject(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.settimeout(self.timeout)
        if self.ssl:
            # Create a more robust SSL context
            context = ssl._create_unverified_context()
            # Set SSL options to be more permissive and resilient
            context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3  # Disable insecure SSL versions
            context.verify_mode = ssl.CERT_NONE  # Don't verify certificate
            
            # Explicitly handle different TLS versions if needed
            try:
                # Wrap the socket with the SSL context
                self.connection = context.wrap_socket(
                    self.connection, server_hostname=self.host)
            except ssl.SSLError as e:
                logging.warning(f"SSL error creating context: {str(e)}, trying fallback")
                # Try a more permissive fallback
                fallback_context = ssl._create_unverified_context()
                fallback_context.check_hostname = False
                fallback_context.verify_mode = ssl.CERT_NONE
                self.connection = fallback_context.wrap_socket(
                    self.connection, server_hostname=self.host)

    def connect(self):
        self.createConnectionObject()
        try:
            self.connection.connect((self.host, self.port))
            self.isConnected = True
        except (socket.error, ssl.SSLError) as e:
            logging.error(
                f'error connecting to {self.host}:{str(self.port)} {e}')
            self.isConnected = False
            raise e
        except Exception as e:
            logging.error(
                f'unexpected error connecting to {self.host}:{str(self.port)} {e}')
            self.isConnected = False
            raise e

    def disconnect(self):
        try:
            self.isConnected = False
            self.connection.close()
        except Exception as _:
            pass
