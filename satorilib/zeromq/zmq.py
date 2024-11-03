"""
import multiprocessing
processes
core 1
|   core 2
|---|
|   |
|   |
V   V
parallel

import threading (easy)
threads (GIL)
core 1 
|   
|---engine
    |
|    
    |
|   
    |
|   
    |
V   V
concurrent

import asyncio (moderately easy) (more efficient for IO bound tasks)
threads (GIL)
core 1 
|   
|---listener
    |
|    
    |
|   
    |
|   
    |
V   V
concurrent

wireguard each need a unique ip address 65k ip addresses

A - server aip:7888

b - server bip:7888
b - client aip:7888

c - client 7888


neuron - server bip:7888
neuron - client aip:7888 - other neuron
neuron - client bip:7889 - my engine
...
data s - server bip:7890
data s - client bip:7888 - neuron
data s - client bip:7889 - my engine
...
engine - server bip:7889
engine - client bip:7888 - neuron
engine - client bip:7890 - data s
engine - client cip:7889 - other's engine



24600 -
24601 - neuron UI flask
24608 - neuron zmq server
24699 - 
246xx - 
...

can we have two servers with different ip addresses have the same port? A and b for example? Yes
can we have the server and client on the same machine point to the same port, as long as they are pointing to different ip addresses? probably yes, b example



|---listener description
    |
    blocks - until a message is received
    vs non-blocking - returns immediately if no message is received
    
    
    
                                                                                                                       ...
                                                    ... 
h -- sustainable comfort    . .... .. ... ...
a                        .
p                     .
p                   . 
i                  .
n              ...
e       . .. .. 
s    .
s  .   
   money  survival            good salary          sustainable safety                                                    multi-millionaire
"""

# minimal zmq works -
# able to accept messages from multiple peers
# able to send messages to multiple peers
# use req/rep for now for reliability
# we build a protocol on top of this

import time
import threading
import numpy as np
from numpy.typing import NDArray
import pandas as pd
from typing import Union
import tensorcom


class ZeroMQServer:
    def __init__(
        self,
        scheme: str = "zrsub",
        ip: str = "127.0.0.1",
        port: str = "7888",
        callback: callable = None,  # callable should be a function that passes the message to somehting - like a queue - it should not be a long running function
    ):
        self.url = scheme + "://" + ip + ":" + port
        self.scheme = scheme
        self.ip = ip
        self.port = port
        self.server = None
        self.callback = callback
        self.thread = None
        self.connectServer()

    def connectServer(self):
        if self.server is None:
            self.server = tensorcom.Connection(multipart=False)
        self.server.connect(self.url)

    def listen(self) -> Union[str, pd.DataFrame]:
        if self.server is not None:
            while True:
                try:
                    data = self.server.recv(  # is this a queue - test with a long running callback function
                        flags=tensorcom.zcom.zmq.NOBLOCK
                    )  # todo: shouldn't we block here?
                    print("data", data)  # test

                    messageType = self.detectMessageType(data)
                    if isinstance(messageType, str):
                        data = self.numpyToString(data[0])
                    elif isinstance(messageType, pd.DataFrame):
                        data = self.numpyArraysToDataframe(data)
                        # self.saveDataframeToCsv(df, f'output.csv')    # additional feature to save as a csv
                    print(data)
                    if callable(self.callback):
                        self.callback(data)
                    else:
                        return data
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    time.sleep(0.001)
                    continue

    def listenForever(self):
        """listen forever in a thread"""
        self.thread = threading.Thread(target=self.listen(), daemon=True)
        self.thread.start()

    @staticmethod
    def detectMessageType(arrays: NDArray[np.uint8]) -> Union[str, pd.DataFrame]:
        """
        Detect whether the received arrays represent a DataFrame or a string message

        Parameters:
        arrays (list): List of numpy arrays received from the connection

        Returns:
        str: 'dataframe' or 'string' indicating the message type
        """
        try:
            # Check if it's a string message (single array)
            if len(arrays) == 1:
                return ""
            arrays[0].tobytes().decode("utf-8").split("|")
            return pd.DataFrame()
        except Exception:
            # If decoding fails or any other error occurs, assume it's a string
            return ""

    @staticmethod
    def numpyToString(arr: NDArray[np.uint8]) -> Union[str, None]:
        """
        Convert numpy array back to string

        Parameters:
        arr (numpy.ndarray): Array containing string data

        Returns:
        str: Decoded string message
        """
        try:
            return bytes(arr.tolist()).decode("utf-8")
        except Exception as e:
            print(f"Error converting numpy array to string: {e}")
            return None

    @staticmethod
    def numpyArraysToDataframe(arrays: NDArray[np.uint8]) -> Union[pd.DataFrame, None]:
        """
        Convert received numpy arrays back to DataFrame

        Parameters:
        arrays (list): List of numpy arrays where:
            - First array contains column names
            - Second array contains dtype information
            - Remaining arrays contain column data

        Returns:
        pandas.DataFrame: Reconstructed DataFrame
        """
        try:
            colNames = arrays[0].tobytes().decode("utf-8").split("|")
            dtypeInfo = arrays[1].tobytes().decode("utf-8").split("|")
            data = {}
            for i, (colNames, dtypeStr) in enumerate(zip(colNames, dtypeInfo)):
                arr = arrays[i + 2]  # +2 because first two arrays are metadata
                if "float" in dtypeStr:
                    data[colNames] = arr
                elif "int" in dtypeStr:
                    data[colNames] = arr
                else:
                    # Assume string data
                    data[colNames] = arr.tobytes().decode("utf-8").split("|")
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error converting numpy arrays to DataFrame: {e}")
            return None

    # todo: move out?
    # @staticmethod
    # def saveDataframeToCsv(
    #    df: pd.DataFrame, filePath: str, index: bool = False, encoding: str = "utf-8"
    # ):
    #    """
    #    Save a pandas DataFrame to a CSV file
    #
    #    Parameters:
    #    df (pandas.DataFrame): DataFrame to save
    #    filepath (str): Path where the CSV file will be saved
    #    index (bool): Whether to write row names (index)
    #    encoding (str): File encoding
    #    """
    #    try:
    #        df.to_csv(filePath, index=index, encoding=encoding)
    #        print(f"DataFrame successfully saved to {filePath}")
    #    except Exception as e:
    #        print(f"Error saving DataFrame: {str(e)}")


class ZeroMQClient:
    def __init__(self, port: str = "://127.0.0.1:7888"):
        self.scheme = None
        self.port = port
        self.server = None
        self.client = None

    def connectServer(self, scheme: str = None):
        if self.server is None:
            self.server = tensorcom.Connection(multipart=False)
        self.scheme = scheme or "zrsub"
        self.server.connect(self.scheme + self.port)

    def connectClient(self, scheme: str = None):
        if self.client is None:
            self.client = tensorcom.Connection(multipart=False)
        self.scheme = scheme or "zrpub"
        self.client.connect(self.scheme + self.port)

    def listen(self) -> Union[str, pd.DataFrame]:
        if self.server is not None:
            while True:
                while True:
                    try:
                        data = self.server.recv(flags=tensorcom.zcom.zmq.NOBLOCK)
                        break
                    except:
                        time.sleep(0.001)
                        continue

                messageType = self.detectMessageType(data)
                if isinstance(messageType, str):
                    data = self.numpyToString(data[0])
                elif isinstance(messageType, pd.DataFrame):
                    data = self.numpyArraysToDataframe(data)
                    # self.saveDataframeToCsv(df, f'output.csv')    # additional feature to save as a csv

                print(data)
                return data

    def send(self, data: Union[str, pd.DataFrame]):
        print(1)
        if isinstance(data, str):
            toSend = self.stringToNumpy(data)
        elif isinstance(data, pd.DataFrame):
            toSend = self.dataframeToNumpyArrays(data)
        self.client.send(toSend)

    @staticmethod
    def detectMessageType(arrays: NDArray[np.uint8]) -> Union[str, pd.DataFrame]:
        """
        Detect whether the received arrays represent a DataFrame or a string message

        Parameters:
        arrays (list): List of numpy arrays received from the connection

        Returns:
        str: 'dataframe' or 'string' indicating the message type
        """
        try:
            # Check if it's a string message (single array)
            if len(arrays) == 1:
                return ""
            arrays[0].tobytes().decode("utf-8").split("|")
            return pd.DataFrame()
        except Exception:
            # If decoding fails or any other error occurs, assume it's a string
            return ""

    @staticmethod
    def numpyToString(arr: NDArray[np.uint8]) -> Union[str, None]:
        """
        Convert numpy array back to string

        Parameters:
        arr (numpy.ndarray): Array containing string data

        Returns:
        str: Decoded string message
        """
        try:
            return bytes(arr.tolist()).decode("utf-8")
        except Exception as e:
            print(f"Error converting numpy array to string: {e}")
            return None

    @staticmethod
    def stringToNumpy(text: str) -> NDArray[np.uint8]:
        """Convert string to numpy array with appropriate dtype"""
        # Convert to numpy array of uint8 (bytes)
        arr = np.array(list(text.encode("utf-8")), dtype=np.uint8)
        return arr

    @staticmethod
    def numpyArraysToDataframe(arrays: NDArray[np.uint8]) -> Union[pd.DataFrame, None]:
        """
        Convert received numpy arrays back to DataFrame

        Parameters:
        arrays (list): List of numpy arrays where:
            - First array contains column names
            - Second array contains dtype information
            - Remaining arrays contain column data

        Returns:
        pandas.DataFrame: Reconstructed DataFrame
        """
        try:
            colNames = arrays[0].tobytes().decode("utf-8").split("|")
            dtypeInfo = arrays[1].tobytes().decode("utf-8").split("|")
            data = {}
            for i, (colNames, dtypeStr) in enumerate(zip(colNames, dtypeInfo)):
                arr = arrays[i + 2]  # +2 because first two arrays are metadata
                if "float" in dtypeStr:
                    data[colNames] = arr
                elif "int" in dtypeStr:
                    data[colNames] = arr
                else:
                    # Assume string data
                    data[colNames] = arr.tobytes().decode("utf-8").split("|")
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error converting numpy arrays to DataFrame: {e}")
            return None

    @staticmethod
    def dataframeToNumpyArrays(df: pd.DataFrame) -> NDArray[np.uint8]:
        """
        Convert DataFrame to list of numpy arrays:
        - One array for column names
        - One array for dtypes
        - One array per column of data
        """
        arrays = []
        arrays.append(
            np.array(list("|".join(df.columns).encode("utf-8")), dtype=np.uint8)
        )
        arrays.append(
            np.array(
                list("|".join(str(dt) for dt in df.dtypes).encode("utf-8")),
                dtype=np.uint8,
            )
        )

        for col in df.columns:
            if df[col].dtype in [np.float64, np.float32]:
                arr = df[col].to_numpy(dtype=np.float32)
            elif df[col].dtype in [np.int64, np.int32, np.int16, np.int8]:
                arr = df[col].to_numpy(dtype=np.int32)
            elif df[col].dtype == "object" or df[col].dtype == "string":
                arr = np.array(
                    list("|".join(df[col].fillna("").astype(str)).encode("utf-8")),
                    dtype=np.uint8,
                )
            else:
                raise ValueError(f"Unsupported dtype: {df[col].dtype} in column {col}")
            arrays.append(arr)

        return arrays

    @staticmethod
    def saveDataframeToCsv(
        df: pd.DataFrame, filePath: str, index: bool = False, encoding: str = "utf-8"
    ):
        """
        Save a pandas DataFrame to a CSV file

        Parameters:
        df (pandas.DataFrame): DataFrame to save
        filepath (str): Path where the CSV file will be saved
        index (bool): Whether to write row names (index)
        encoding (str): File encoding
        """
        try:
            df.to_csv(filePath, index=index, encoding=encoding)
            print(f"DataFrame successfully saved to {filePath}")
        except Exception as e:
            print(f"Error saving DataFrame: {str(e)}")


if __name__ == "__main__":
    """
    option 1: ZeroMQServer and ZeroMQClient
    option 2: ZeroMQ imply that both functionalities of send and receive are present in the same class like pubsub
    """
    client = ZeroMQClient("://127.0.0.1:7889")
    client.connectClient()
    server = ZeroMQServer(
        scheme="zrsub",
        ip="127.0.0.1",
        port="7888",
        callback=client.send,  # should be short lived
    )
    server.listenForever()
