import argparse

from src.api import service
from src.api.server import FRONTEND_DIST, create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only JSON API over the precomputed risk signals and stress results.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    for name in service.available_datasets():
        service.summary(name)
        service.events(name)
    service.sentiment_model()
    server = create_server(args.host, args.port)
    print(f"Risk Engine API listening on http://{args.host}:{args.port}/api/health")
    if FRONTEND_DIST.is_dir():
        print(f"Serving the React build from {FRONTEND_DIST} at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
