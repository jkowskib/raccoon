import sys
import uuid
import socket
import threading
from datetime import datetime, timezone, timedelta

import net
from net.templates import render_template
from net.utility import send_response, set_cookie, parse_cookies, tuple_netstring

from config import STATIC_FOLDER, BUFFER_SIZE, Configuration

from memory import KeyStore

config = Configuration("racoon.toml")
sessions = KeyStore()


def make_session_token() -> str:
    uuid_token = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc) + timedelta(minutes=config.get_value(
        "racoon", "cookie_expire_time_minutes"))
    sessions.set(uuid_token, timestamp.timestamp())
    return uuid_token


def send_challenge(client: socket.socket) -> None:
    send_response(client,
    "HTTP/1.1", 200, "OK", render_template(
        f"{STATIC_FOLDER}/challenge.html",
                challenge_time=str(config.get_value("racoon", "challenge_time_ms") + 500)
            ),
            config.get_value("racoon", "max_body_size_bytes"),
            BUFFER_SIZE,
            {
                      "Set-Cookie": set_cookie(
                          config.get_value("racoon", "cookie_name"),
                          make_session_token()
                      ),
            }
    )


def connection_thread(
        client: socket.socket,
        client_addr: tuple[str, int],
        forward_addresses: dict[str, str]
) -> None:
    server: socket.socket | None = None

    max_body_size = config.get_value("racoon", "max_body_size_bytes")
    max_header_size = config.get_value("racoon", "max_header_size_bytes")
    session_token_name = config.get_value("racoon", "cookie_name")

    try:
        client_message = net.Request.read_header(
            client,
            max_body_size,
            BUFFER_SIZE
        )

        print(
            f"{client_addr[0]}:{client_addr[1]} -",
            client_message.Method.value,
            client_message.Path,
            client_message.Version
        )

        client_cookies = parse_cookies(client_message.Headers.get("Cookie"))

        if session_token_name not in client_cookies:
            send_challenge(client)
            return

        session_token = client_cookies.get(session_token_name)
        expire_offset: bytes = sessions.get(session_token)

        if not expire_offset:
            send_challenge(client)
            return
        elif float(expire_offset) < datetime.now(timezone.utc).timestamp():
            sessions.delete(session_token)
            send_challenge(client)
            return

        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            host_header = (client_message.Headers.get("Host")
                           .replace(".", "_"))
            if host_header and host_header in forward_addresses:
                # Forward to specific host defined in host header
                server.connect(tuple_netstring(forward_addresses.get(host_header)))
            else:
                # The Host was either not found or the header was not included
                server.connect(tuple_netstring(forward_addresses.get("default")))
        except Exception as e:
            print("Failed to reach forward location:", e)
            send_response(client, "HTTP/1.1", 502, "Bad Gateway", render_template(
                f"{STATIC_FOLDER}/intercept.html",
                errorcode="502",
                errormessage="Bad Gateway",
                message="Internal service could not be reached. Try again later."
            ), max_body_size=max_body_size, buffer_size=BUFFER_SIZE)
            return

        client_message.Headers["X-Forwarded-For"] = client_addr[0]
        client_message.make(client, server, max_body_size, BUFFER_SIZE)

        server_response = net.Response.read_header(server, max_header_size, BUFFER_SIZE)

        server_response.make(server, client, max_body_size, BUFFER_SIZE)
    finally:
        client.close()
        server and server.close()


def main(args: list[str]) -> int:
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.bind((
        config.get_value("racoon", "host_ip"),
        config.get_value("racoon", "host_port")
    ))
    soc.listen()

    print("Raccoon is listening on {ip}:{port}".format(
        ip=config.get_value("racoon", "host_ip"),
        port=config.get_value("racoon", "host_port")
    ))

    for route, forward in config.get_config("routes").items():
        print("  {route} -> {forward}".format(
            route=route,
            forward=forward
        ))

    try:
        while True:
            conn, addr = soc.accept()
            threading.Thread(
                target=connection_thread,
                args=(conn, addr, config.get_config("routes"))
            ).start()
    except KeyboardInterrupt:
        soc.close()
        print("Shutdown requested")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
