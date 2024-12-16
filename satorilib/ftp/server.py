# apt-get install curl -y
# curl ifconfig.me
# pip install pyftpdlib
from pyftpdlib import servers, handlers


class FTPServer:
    def __init__(self, host="0.0.0.0", port=21,  nat_address=None):
        # Use 0.0.0.0 for all available network interfaces
        self.address = (host, port)
        self.server = servers.FTPServer(self.address, handlers.FTPHandler)
        # Set a custom banner message
        self.server.banner = "Welcome to My SatoriNeuron FTP Server"
        # Set the username and password with read-only access
        self.handler = self.server.handler
        self.handler.authorizer.add_user(
            "username", "password", ".", perm="elr")
        # Specify the NAT address
        self.handler.masquerade_address = nat_address
        # Configure passive mode and specify the passive port range
        # Set your desired passive port range
        self.handler.passive_ports = range(60000, 60100)
        # set a limit for connections
        self.server.max_cons = 256
        self.server.max_cons_per_ip = 5

    def run(self):
        # Start the server
        self.server.serve_forever()


FTPServer(host="0.0.0.0", port=22, nat_address='97.117.28.178').run()
# handler.authorizer.add_anonymous(".", perm="elr")
