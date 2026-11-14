"""Start the complete LavaLabs workspace on a single loopback address."""
import os
import socket

import uvicorn

from scripts.bootstrap_demo import bootstrap

def main():
    port = int(os.environ.get('LAVALABS_PORT', '8780'))
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise SystemExit(f'Port {port} is in use. Stop that instance or choose a different LAVALABS_PORT.')
    bootstrap()
    print(f'LavaLabs: http://127.0.0.1:{port}/#terrain', flush=True)
    uvicorn.run('lavalabs.server:create_app', host='127.0.0.1', port=port, factory=True)


if __name__ == '__main__':
    main()
