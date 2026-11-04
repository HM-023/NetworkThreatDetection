"""Loopback-only workspace server and transactional local document storage."""
import argparse
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

MAX_BODY=4*1024*1024

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def text(value, name='Text', limit=2000):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f'{name} is required')
    value=value.strip()
    if len(value)>limit: raise ValueError(f'{name} exceeds {limit} characters')
    return value

def integer(value, name, low=1, high=65534):
    if isinstance(value,bool): raise ValueError(f'{name} must be an integer')
    try:
        n=int(value)
    except (TypeError,ValueError):
        raise ValueError(f'{name} must be an integer') from None
    if str(n)!=str(value).strip(): raise ValueError(f'{name} must be an integer')
    if not low<=n<=high: raise ValueError(f'{name} must be between {low} and {high}')
    return n

class Store:
    def __init__(self,directory):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/'workspace.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL)')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15)
        db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
        return db
    def all(self,kind):
        with self.connect() as db:
            rows=db.execute('SELECT payload FROM documents WHERE kind=? ORDER BY created DESC,id DESC',(kind,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def get(self,kind,identifier):
        with self.connect() as db:
            row=db.execute('SELECT payload FROM documents WHERE id=? AND kind=?',(str(identifier),kind)).fetchone()
        if not row: raise ValueError('Record not found')
        return json.loads(row[0])
    def save(self,kind,payload):
        with self.connect() as db:
            db.execute('INSERT INTO documents VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                       (payload['id'],kind,json.dumps(payload,allow_nan=False),payload.get('created',now())))
        return payload
    def delete(self,kind,identifier):
        with self.connect() as db:
            n=db.execute('DELETE FROM documents WHERE id=? AND kind=?',(str(identifier),kind)).rowcount
        if not n: raise ValueError('Record not found')

class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,app):
        self.app=app;self.token=secrets.token_urlsafe(32);self.operation_lock=threading.Lock()
        super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    server_version='LocalWorkspace/1.0'
    def log_message(self,*args):
        pass  # Request bodies and local data are never logged.
    def reply(self,status,data,mime='application/json'):
        raw=json.dumps(data,allow_nan=False).encode() if mime=='application/json' else data
        self.send_response(status);self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers();self.wfile.write(raw)
    def trusted_host(self):
        port=self.server.server_port
        return self.headers.get('Host') in {f'127.0.0.1:{port}',f'localhost:{port}'}
    def authorized(self):
        port=self.server.server_port
        origin=self.headers.get('Origin')
        return (self.trusted_host() and secrets.compare_digest(self.headers.get('X-Workspace-Token',''),self.server.token)
                and (origin is None or origin in {f'http://127.0.0.1:{port}',f'http://localhost:{port}'}))
    def do_GET(self):
        if not self.trusted_host(): return self.reply(403,{'error':'Unrecognized host'})
        path=urlsplit(self.path).path
        if path=='/api/state':
            if not self.authorized(): return self.reply(403,{'error':'Session token required'})
            try: return self.reply(200,self.server.app.state())
            except Exception: return self.reply(500,{'error':'Workspace unavailable; check local storage permissions'})
        files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if path not in files: return self.reply(404,{'error':'Not found'})
        filename,mime=files[path];raw=(Path(__file__).parent/'static'/filename).read_bytes()
        if filename=='index.html': raw=raw.replace(b'__SESSION_TOKEN__',self.server.token.encode())
        self.reply(200,raw,mime)
    def do_POST(self):
        if not self.authorized(): return self.reply(403,{'error':'Invalid local session or origin'})
        if urlsplit(self.path).path!='/api/action': return self.reply(404,{'error':'Not found'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            return self.reply(415,{'error':'JSON is required'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=MAX_BODY: return self.reply(413,{'error':'Request must be between 1 byte and 4 MiB'})
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError('Expected a JSON object')
            if not self.server.operation_lock.acquire(blocking=False): return self.reply(409,{'error':'An operation is running; try again after it finishes'})
            try: result=self.server.app.action(body)
            finally: self.server.operation_lock.release()
            self.reply(200,result)
        except (ValueError,TypeError,KeyError,sqlite3.IntegrityError) as exc:
            self.reply(400,{'error':str(exc) or 'Invalid input'})
        except Exception:
            self.reply(500,{'error':'Operation failed; no detailed local data is returned in error messages'})

def serve(factory,default_port):
    parser=argparse.ArgumentParser(description='Run this private local workspace on loopback')
    parser.add_argument('--port',type=int,default=default_port)
    parser.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[1]/'data')
    args=parser.parse_args()
    if not 1<=args.port<=65535: parser.error('port must be between 1 and 65535')
    server=LocalServer(('127.0.0.1',args.port),factory(args.data_dir))
    print(f'Open http://127.0.0.1:{server.server_port} | Ctrl+C to stop',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
