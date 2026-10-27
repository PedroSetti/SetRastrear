"""Servidor HTTPS local de desenvolvimento: frontend compilado e proxy API."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import ssl,sys
root=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(root/'web/dist'),**kw)
 def do_GET(self):
  if self.path.startswith(('/api/','/docs','/openapi.json')):return self.proxy()
  return super().do_GET()
 def do_POST(self):self.proxy()
 def do_PATCH(self):self.proxy()
 def do_DELETE(self):self.proxy()
 def log_message(self,format,*args):
  pass # Evita registrar tokens de redefinicao presentes em query strings
 def proxy(self):
  headers={k:v for k,v in self.headers.items() if k.lower() not in ('host','connection','content-length')}
  body=self.rfile.read(int(self.headers.get('Content-Length','0'))) or None
  req=Request('http://127.0.0.1:8000'+self.path,data=body,headers=headers,method=self.command)
  try:r=urlopen(req,timeout=30)
  except HTTPError as e:r=e
  self.send_response(r.code)
  for k,v in r.headers.items():
   if k.lower() not in ('connection','transfer-encoding','server','date'):self.send_header(k,v)
  self.end_headers();self.wfile.write(r.read())
if '--http' in sys.argv:
 server=ThreadingHTTPServer(('127.0.0.1',8080),Handler)
 print('Origem privada do Cloudflare Tunnel: http://127.0.0.1:8080')
else:
 ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.minimum_version=ssl.TLSVersion.TLSv1_2
 ctx.load_cert_chain(root/'certs-dev/server.pem',root/'certs-dev/server-key.pem')
 server=ThreadingHTTPServer(('0.0.0.0',8443),Handler);server.socket=ctx.wrap_socket(server.socket,server_side=True)
 print('https://localhost:8443 — somente desenvolvimento')
server.serve_forever()
