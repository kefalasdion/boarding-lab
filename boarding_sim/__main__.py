"""Run the local simulator UI and API."""

from __future__ import annotations

import argparse

from .server import make_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Passenger Boarding System Simulator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    host, port = server.server_address[:2]
    print(f"Passenger Boarding Simulator: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
