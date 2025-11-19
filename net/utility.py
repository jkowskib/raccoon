import io
import socket

import net
from net.errors import InvalidRequestHead, RequestTooLarge, PrematureStreamEnd


def set_cookie(name: str, value: str) -> str:
    """
    Builds a Set-Cookie header and returns a tuple with the content
    :param name: cookies name
    :param value: cookies value
    :return: cookie header
    """
    return f"{name}={value}"


def tuple_netstring(string: str) -> tuple[str, int] | None:
    """
    Takes an IP:PORT string and turns it into a tuple
    :param string: IP:PORT string
    :return: tuple or None
    """
    if ":" not in string:
        return None
    ip, port = string.split(":")
    return ip, int(port)


def parse_cookies(cookie_string: str) -> dict[str, str]:
    """
    Parses a cookie string
    :param cookie_string: header cookie string
    :return: dictionary of cookie values
    """
    cookies = {}

    if cookie_string is None or len(cookie_string) == 0:
        return cookies

    for part in cookie_string.split(";"):
        part = part.strip()

        if "=" not in part:
            continue

        key, value = part.split("=", 1)
        cookies[key] = value

    return cookies


def send_response(
        client: socket.socket,
        version: str,
        status: int,
        message: str,
        body: bytes,
        max_body_size: int,
        buffer_size: int,
        headers: dict[str, str] = None
) -> None:
    """
    Sends a response with a given body to a client socket
    :param version: HTTP version
    :param status: HTTP status code
    :param message: HTTP status code message
    :param client: client
    :param body: bytes body
    :param max_body_size: max body size in bytes
    :param buffer_size: max buffer size
    :param headers: headers to include
    :return: None
    """
    intercept = net.Response(version, status, message, {}, bytes())

    if headers is not None:
        for head, value in headers.items():
            intercept.Headers[head] = value

    intercept.Headers["Content-Length"] = str(len(body))

    intercept.set_body(body)
    intercept.make(client, client, max_body_size, buffer_size)


def write_status(a: str, b: str, c: str) -> bytes:
    """
    Creates HTTP status header
    :param a: pos 1
    :param b: pos 2
    :param c: pos 3
    :return: bytes
    """
    buffer = io.BytesIO()

    buffer.write(a.encode("UTF-8"))
    buffer.write(b" ")
    buffer.write(b.encode("UTF-8"))
    buffer.write(b" ")
    buffer.write(c.encode("UTF-8"))
    buffer.write(b"\r\n")

    return buffer.getvalue()


def write_headers(headers: dict[str, str]) -> bytes:
    """
    Creates HTTP headers bytes buffer from a dictionary
    :param headers: headers dictionary
    :return: bytes
    """
    buffer = io.BytesIO()

    for name, value in headers.items():
        buffer.write(name.encode("UTF-8"))
        buffer.write(b": ")
        buffer.write(value.encode("UTF-8"))
        buffer.write(b"\r\n")

    buffer.write(b"\r\n")

    return buffer.getvalue()


def parse_headers(headers: list[str]) -> dict[str, str]:
    """
    Takes a list of header strings and turns them into a dictionary
    :param headers: header line strings
    :return: dict[str, str]
    """
    http_headers = {}

    for header in headers:
        header_parts = header.split(": ", 1)

        if len(header_parts) != 2:
            raise InvalidRequestHead("header entry is invalid")

        http_headers[header_parts[0]] = header_parts[1]

    return http_headers


def read_socket_header(
        buffer_size: int,
        client: socket.socket,
        max_size: int,
) -> bytearray:
    """
    Reads until buffer contains full header
    :param buffer_size: the buffer size
    :param client: client socket
    :param max_size: max header size
    :return: bytearray buffer
    """
    buffer: bytearray = bytearray()
    read_in: int = 0

    while True:
        chunk = client.recv(buffer_size)
        read_in += len(chunk)

        if not chunk:
            raise PrematureStreamEnd("socket closed before the net header ended")

        if read_in > max_size:
            raise RequestTooLarge(f"request is too large {read_in} > {max_size}")

        buffer.extend(chunk)

        if b"\r\n\r\n" in buffer:
            break

    return buffer


def read_socket_body(
        buffer_size: int,
        part_body: bytes,
        headers: dict[str, str],
        socket_from: socket.socket,
        max_size: int,
        stream: bool = False,
        socket_to: socket.socket = None,
) -> bytes | None:
    """
    Reads in the rest of the body into the object so it can be used.
    :param buffer_size: the buffer size
    :param part_body: part if any of the body
    :param headers: net headers
    :param socket_from: tcp socket read from
    :param max_size: the max body size
    :param stream: True if the body should be streamed to the socket
    :param socket_to: response socket (only needed if streaming is enabled)
    :return: new body if stream is false
    """
    body = bytearray(part_body)
    read_in = len(body)

    if headers.get("Transfer-Encoding") and headers.get("Transfer-Encoding").lower() == "chunked":
        raise NotImplementedError("chunked transfers are not supported")
    elif headers.get("Content-Length"):
        length = headers.get("Content-Length")
        if not length.isnumeric():
            raise InvalidRequestHead("Content-Length must be numeric")

        length = int(length)

        if length > max_size:
            raise RequestTooLarge("the message body is too large")

        while read_in < length:
            chunk = socket_from.recv(buffer_size)
            read_in += len(chunk)

            if not chunk:
                raise PrematureStreamEnd("socket closed before the net body ended")

            if stream:
                socket_to.sendall(chunk)
            else:
                body.extend(chunk)
    else:
        # No Content-Length, likely no body to read
        return None

    if not stream:
        return bytes(body)

    return None
