import io
import socket
from enum import Enum
from dataclasses import dataclass, field

from net.utility import write_headers, parse_headers, read_socket_body, read_socket_header, write_status
from net.errors import RequestTooLarge, PrematureStreamEnd, InvalidRequestHead

class Methods(Enum):
    Connect = "CONNECT"
    Delete = "DELETE"
    Get = "GET"
    Head = "HEAD"
    Options = "OPTIONS"
    Patch = "PATCH"
    Post = "POST"
    Put = "PUT"
    Trace = "TRACE"


@dataclass
class Request:
    Method: Methods
    Path: str
    Version: str
    Headers: dict[str, str]
    Body: bytes
    __body_complete: bool = field(default=False, repr=False, compare=False)

    def set_body(self, body: bytes) -> None:
        """
        Sets the body of the request
        :param body: body to set
        :return: None
        """
        self.__body_complete = True
        self.Body = body

    def make(self, client: socket.socket, server: socket.socket, max_body_size: int, buffer_size: int) -> None:
        """
        Sends the request to a server
        :return: None
        """
        buffer = io.BytesIO()

        buffer.write(
            write_status(self.Method.value, self.Path, self.Version)
        )

        buffer.write(
            write_headers(self.Headers)
        )

        buffer.write(self.Body)
        server.sendall(buffer.getvalue())

        if not self.__body_complete:
            self.read_body(
                client, max_body_size, buffer_size,
                stream=True,
                server=server
            )

    @staticmethod
    def read_header(client: socket.socket, max_size: int, buffer_size: int) -> "Request":
        """
        Attempts to read in an HTTP header from a TCP socket and returns a request object.
        If parts of the body are read in, the incomplete body will be placed in the object body.
        :param client: tcp socket
        :param max_size: the limit where the method should stop if the header is too long
        :param buffer_size: socket buffer read size
        :return: Request object
        """
        buffer: bytearray = read_socket_header(
            buffer_size,
            client,
            max_size
        )

        header_end = buffer.find(b"\r\n\r\n")

        header_region: bytearray = buffer[:header_end]
        body_region: bytes = bytes(buffer[header_end + 4:])

        header_region: list[str] = header_region.decode("UTF-8").split("\r\n")
        status_header: list[str] = header_region[0].split(" ")

        if len(status_header) != 3:
            raise InvalidRequestHead("status header is invalid")

        http_method: Methods = Methods(status_header[0])
        http_path: str = status_header[1]
        http_version: str = status_header[2]

        http_headers = parse_headers(header_region[1:])

        return Request(http_method, http_path, http_version, http_headers, body_region)

    def read_body(
            self,
            client: socket.socket,
            max_size: int,
            buffer_size: int,
            stream: bool = False,
            server: socket.socket = None
    ) -> None:
        """
        Reads in the rest of the body into the object so it can be used.
        :param client: tcp socket
        :param max_size: the max body size
        :param buffer_size: socket buffer read size
        :param stream: True if the body should be streamed to the socket
        :param server: response socket (only needed if streaming is enabled)
        :return: None
        """

        body = read_socket_body(
            buffer_size,
            self.Body,
            self.Headers,
            client,
            max_size,
            stream,
            server
        )

        if not stream:
            self.Body = bytes(body)
            self.__body_complete = True


@dataclass
class Response:
    Version: str
    Status: int
    Message: str
    Headers: dict[str, str]
    Body: bytes
    __body_complete: bool = field(default=False, repr=False, compare=False)

    def set_body(self, body: bytes) -> None:
        """
        Sets the body of the request
        :param body: body to set
        :return: None
        """
        self.__body_complete = True
        self.Body = body

    def make(self, server: socket.socket, client: socket.socket, max_body_size: int, buffer_size: int) -> None:
        """
        Sends the response to a client
        :return: None
        """
        buffer = io.BytesIO()

        buffer.write(
            write_status(self.Version, str(self.Status), self.Message)
        )

        buffer.write(
            write_headers(self.Headers)
        )

        buffer.write(self.Body)
        client.sendall(buffer.getvalue())

        if not self.__body_complete:
            self.read_body(
                server, max_body_size, buffer_size,
                stream=True,
                client=client
            )

    @staticmethod
    def read_header(server: socket.socket, max_size: int, buffer_size: int) -> "Response":
        """
        Attempts to read in an HTTP header from a TCP socket and returns a response object.
        If parts of the body are read in, the incomplete body will be placed in the object body.
        :param server: tcp socket
        :param max_size: the limit where the method should stop if the header is too long
        :param buffer_size: socket buffer read size
        :return: Response object
        """
        buffer = read_socket_header(
            buffer_size,
            server,
            max_size
        )

        header_end = buffer.find(b"\r\n\r\n")

        header_region = buffer[:header_end]
        body_region = bytes(buffer[header_end + 4:])

        header_region = header_region.decode("UTF-8").split("\r\n")
        status_header = header_region[0].split(" ", 2)

        if len(status_header) != 3:
            raise InvalidRequestHead("status header is invalid")

        http_version = status_header[0]
        http_status = status_header[1]

        if not http_status.isnumeric():
            raise InvalidRequestHead("status code must be numeric")

        http_status = int(http_status)
        http_code = status_header[2]

        http_headers = parse_headers(header_region[1:])

        return Response(http_version, http_status, http_code, http_headers, body_region)

    def read_body(
            self,
            server: socket.socket,
            max_size: int,
            buffer_size: int,
            stream: bool = False,
            client: socket.socket = None
    ) -> None:
        """
        Reads in the rest of the body into the object so it can be used.
        :param server: tcp socket
        :param max_size: the max body size
        :param buffer_size: socket buffer read size
        :param stream: True if the body should be streamed to the socket
        :param client: client socket (only needed if streaming is enabled)
        :return: None
        """
        body = read_socket_body(
            buffer_size,
            self.Body,
            self.Headers,
            server,
            max_size,
            stream,
            client
        )

        if not stream:
            self.Body = bytes(body)
            self.__body_complete = True
