"""Forced-command synthetic data provider for an ephemeral test SSH server."""
import hashlib,os,sys
DATA=bytes(range(256))*4096
mode=os.environ.get('SSH_ORIGINAL_COMMAND','')
if mode=='health':sys.stdout.buffer.write(b'cross-border-ssh-ok')
elif mode=='download':sys.stdout.buffer.write(DATA)
elif mode=='upload':
 data=sys.stdin.buffer.read(len(DATA)+1)
 sys.stdout.buffer.write(b'OK' if len(data)==len(DATA) and hashlib.sha256(data).digest()==hashlib.sha256(DATA).digest() else b'NO')
else:raise SystemExit(2)
