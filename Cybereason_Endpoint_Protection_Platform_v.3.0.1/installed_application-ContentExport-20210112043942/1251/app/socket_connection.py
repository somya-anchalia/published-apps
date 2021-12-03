import socket, os
from qpylib import qpylib

class TimeoutError(Exception):
    """
    Exception to be raised on connection timeout
    """
    pass

class SocketConnection:
    """
    Send the event text to socket specified by an IP and port number

    ...

    Attributes
    ----------
    host : str
        Destination IP address to send the event string 
    port : str
        family name of the person

    Methods
    -------
    send(event):
        Sends event to the destination host
    """

    def __init__(self, host, port):
        """
        Constructs all the necessary attributes for the SocketConnection.

        Parameters
        ----------
            host : str
                Destination IP address to send the event string 
            port : str
                family name of the person
        """
        self.host = host
        self.port = port
        self.count = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def send(self, data):
        """
        Send data to the host on specified port through socket connection.

        Parameters
        ----------
            data : str
                String data to be sent to host
        """

        try:
            self.count = self.count + 1
            self.sock.sendall(data.encode('utf-8'))
        except TimeoutError:
            qpylib.log("Timeout reached while sending the data to %s:%s" % (self.host, self.port))