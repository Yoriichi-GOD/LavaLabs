"""Start only LavaLabs-owned local services. Ctrl+C stops both children."""
from pathlib import Path
import os
import socket
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
from scripts.bootstrap_demo import bootstrap
bootstrap()
PORT=int(os.environ.get('LAVALABS_PORT','8780'))
FLOOD_PORT=int(os.environ.get('LAVALABS_FLOOD_PORT','8781'))
if PORT==FLOOD_PORT:raise SystemExit('Choose different LavaLabs and flood-service ports.')
for port in (PORT,FLOOD_PORT):
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',port))==0:
            raise SystemExit(f'Port {port} is in use. Choose another LavaLabs port; existing services will not be replaced.')
logs=ROOT/'.runtime/lava';logs.mkdir(parents=True,exist_ok=True)
environment=dict(os.environ,LAVALABS_FLOOD_UPSTREAM=f'http://127.0.0.1:{FLOOD_PORT}',LAVALABS_PORT=str(PORT))
processes=[];handles=[]
try:
    for name, module, cwd, port, factory in [
        ('flood','floodlab.server:app',ROOT/'components/floodlab',FLOOD_PORT,False),
        ('lava','lavalabs.server:create_app',ROOT,PORT,True),
    ]:
        handle=(logs/(name+'.log')).open('ab',buffering=0);handles.append(handle)
        command=[sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port)]
        if factory:command.append('--factory')
        processes.append(subprocess.Popen(command,cwd=cwd,env=environment,stdout=handle,stderr=subprocess.STDOUT))
    print(f'LavaLabs: http://127.0.0.1:{PORT}/#terrain',flush=True)
    print('Only LavaLabs services are started. Ctrl+C stops both.',flush=True)
    while all(process.poll() is None for process in processes):time.sleep(.5)
    raise SystemExit('A LavaLabs service stopped. Inspect .runtime/lava/*.log.')
except KeyboardInterrupt:pass
finally:
    for process in processes:
        if process.poll() is None:process.terminate()
    for process in processes:
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    for handle in handles:handle.close()
