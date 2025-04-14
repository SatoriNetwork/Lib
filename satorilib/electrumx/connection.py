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
    ):
        self.host = host
        self.port = port
        self.ssl = port == 50002 or ssl
        self.timeout = timeout
        self.isConnected = False
        self.connection: socket.socket = None
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

    def connect(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.settimeout(self.timeout)
        if self.ssl:
            # # Create a SSL context with a specific protocol
            # # context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            # # Optionally, set up more specific SSL options if needed
            # # context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Example to disable TLSv1 and TLSv1.1
            # # Wrap the socket with the SSL context
            # # self.connection = context.wrap_socket(self.connection, server_hostname=self.host)
            # self.connection = ssl.wrap_socket(self.connection)
            #
            # Create an SSL context that does not verify certificates
            # context = ssl.create_default_context()
            # This ignores certificate verification
            context = ssl._create_unverified_context()
            # context.check_hostname = True
            # context.verify_mode = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.CERT_NONE | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3 | ssl.CERT_OPTIONAL | ssl.OP_NO_COMPRESSION | ssl.OP_NO_TICKET | ssl.CERT_REQUIRED
            # context.verify_mode = ssl.CERT_OPTIONAL
            #
            # Wrap the socket with the SSL context
            self.connection = context.wrap_socket(
                self.connection, server_hostname=self.host)
        try:
            self.connection.connect((self.host, self.port))
            self.isConnected = True
        except Exception as e:
            logging.error(
                f'error connecting to {self.host}:{str(self.port)} {e}')
            raise e

    def disconnect(self):
        try:
            self.isConnected = False
            self.connection.close()
        except Exception as _:
            pass
