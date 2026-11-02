"""Bounded synthetic-data connectivity probe; never reads local documents."""
import argparse, hashlib, http.server, ipaddress, json, os, socket, threading, time, urllib.request
from pathlib import Path
SIZE=1024*1024
DATA=bytes(range(256))*4096
DIGEST=hashlib.sha256(DATA).hexdigest()
def emit(value): print(json.dumps(value,sort_keys=True),flush=True)
def endpoint(value):
    addr=ipaddress.ip_address(value)
    if addr.version!=4 or not (addr in ipaddress.ip_network('100.64.0.0/10') or addr.is_loopback):
        raise ValueError('Expected a tailnet IPv4 address')
    return str(addr)
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def setup(self):
        super().setup(); self.connection.settimeout(8)
    def permitted(self):
        if self.headers.get('Authorization')!='Bearer '+os.environ['PROBE_TOKEN']:
            self.send_error(403);return False
        return True
    def do_GET(self):
        if not self.permitted():return
        if self.path=='/health':body=b'cross-border-probe-ok'
        elif self.path=='/download':body=DATA
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if not self.permitted():return
        if self.path!='/upload' or self.headers.get('Content-Length')!=str(SIZE):self.send_error(400);return
        body=self.rfile.read(SIZE)
        valid=len(body)==SIZE and hashlib.sha256(body).hexdigest()==DIGEST
        self.send_response(200 if valid else 400);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'OK' if valid else b'NO')
class Server(http.server.ThreadingHTTPServer):
    def handle_error(self,request,address):emit({"server_error":"request_failed"})
def serve(args):
    server=Server((endpoint(args.bind),args.port),Handler)
    timer=threading.Timer(args.seconds,server.shutdown);timer.daemon=True;timer.start()
    emit({'server':'ready','port':args.port,'lifetime_seconds':args.seconds})
    try:server.serve_forever(poll_interval=.2)
    finally:server.server_close();timer.cancel()
def measure(args):
    target=endpoint(args.target);opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
    for count in range(args.rounds):
        row={'round':count+1,'direction':args.label}
        for name,path,payload in [('health','/health',None),('download','/download',None),('upload','/upload',DATA)]:
            begin=time.monotonic()
            try:
                request=urllib.request.Request(f'http://{target}:{args.port}{path}',data=payload,headers={'Authorization':'Bearer '+os.environ['PROBE_TOKEN']})
                with opener.open(request,timeout=15) as response:body=response.read(SIZE+1)
                good=(body==b'cross-border-probe-ok' if name=='health' else hashlib.sha256(body).hexdigest()==DIGEST if name=='download' else body==b'OK')
                seconds=time.monotonic()-begin
                row[name]={'passed':good,'seconds':round(seconds,4)}
                if name!='health':row[name]['mbps']=round(SIZE*8/seconds/1e6,3)
            except Exception as exc:row[name]={'passed':False,'error_type':type(exc).__name__}
        if args.ssh_banner:
            try:
                with socket.create_connection((target,22),timeout=8) as connection:banner=connection.recv(256)
                row['ssh_banner']={'passed':banner.startswith(b'SSH-')}
            except Exception as exc:row['ssh_banner']={'passed':False,'error_type':type(exc).__name__}
        rows.append(row);emit(row)
        if count+1<args.rounds:time.sleep(args.delay)
    good=all(check.get('passed') is True for row in rows for key,check in row.items() if isinstance(check,dict))
    if args.output:Path(args.output).write_text(json.dumps({'passed':good,'rounds':rows},indent=2)+'\n')
    return 0 if good else 1
if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True)
    server=sub.add_parser('serve');server.add_argument('--bind',required=True);server.add_argument('--port',type=int,default=42070);server.add_argument('--seconds',type=int,default=900)
    client=sub.add_parser('measure');client.add_argument('--target',required=True);client.add_argument('--port',type=int,default=42070);client.add_argument('--rounds',type=int,default=3);client.add_argument('--delay',type=float,default=10);client.add_argument('--label',default='outbound');client.add_argument('--ssh-banner',action='store_true');client.add_argument('--output')
    args=parser.parse_args()
    if not os.environ.get('PROBE_TOKEN'):raise SystemExit('Missing probe token')
    if args.mode=='serve':serve(args)
    else:raise SystemExit(measure(args))
