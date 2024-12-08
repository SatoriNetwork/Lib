import os
from ftplib import FTP


class FTPClient:
    def __init__(self, host, port=21):
        self.host = host
        self.port = port

    def _connect(self):
        self.ftp = FTP()
        self.ftp.connect(self.host, self.port)
        # self.ftp.port = self.port
        self.ftp.set_pasv(True)
        self.ftp.login('username', 'password')

    def _disconnect(self):
        ''' Disconnect from the FTP server '''
        self.ftp.quit()

    @staticmethod
    def manageConnection(func):
        def wrapper(self, *args, **kwargs):
            self._connect()
            result = func(self, *args, **kwargs)
            self._disconnect()
            return result
        return wrapper

    @manageConnection
    def pull(self, filename: str, path: str = None, local: str = '.') -> bool:
        if path is not None:
            self.ftp.cwd(path)
        if filename in self.ftp.nlst():
            # Specify the desired folder or path here
            local_path = os.path.join(local, filename)
            with open(local_path, 'wb') as file:
                self.ftp.retrbinary('RETR ' + filename, file.write)
            return True
        return False

    @manageConnection
    def view(self, path: str = None) -> bool:
        if path is not None:
            self.ftp.cwd(path)
        for file in self.ftp.nlst():
            print(file)
        return False


f = FTPClient('127.0.0.1', 22)
f.view()
f.pull('utils.py')
f = FTPClient('172.17.0.2', 22)
f.view()
f.pull('utils.py')
f = FTPClient('97.117.28.178', 22)
f.view()
f.pull('utils.py')
#
#
# import pyftpdlib
#
# client = pyftpdlib.FTPClient()
# client.connect("localhost", 21)
#
# # Use the PASV command to request a passive connection.
# client.pasv()
#
# # Get the passive IP address and port number.
# passive_ip_address, passive_port = client.getpassive()
#
# # Open a file on the remote server.
# with open("remote_file", "wb") as f:
#     # Read data from the remote file and write it to the local file.
#     f.write(client.retrbinary("RETR remote_file"))
#
# # Close the file.
# f.close()
#
# # Disconnect from the server.
# client.quit()
