"""Run the prepared offline demo: python -m concretecalc_web."""
import argparse
import socket
from pathlib import Path
import uvicorn
from .api import create_app


def main() -> None:
    parser=argparse.ArgumentParser(description='Concrete Research Studio — local demo')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--api-only',action='store_true',help='Development API without built frontend')
    args=parser.parse_args()
    if not args.api_only and not (Path(__file__).parent/'static/index.html').is_file():
        parser.exit(1,'Frontend is not built. Run: cd web; npm ci; npm run build\n')
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1',args.port))
        except OSError:
            parser.exit(1,f'Port {args.port} is in use. Stop the previous server or use --port {args.port+1}.\n')
    print(f'Concrete Research Studio: http://127.0.0.1:{args.port} (offline/local only)')
    uvicorn.run(create_app(),host='127.0.0.1',port=args.port,log_level='warning')


if __name__=='__main__':
    main()
