"""Loopback-only UI fixture. RAM settings only; no Pi, GPS or credential access."""
import json
import sys
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
sys.path.insert(0, str(Path(__file__).parents[1]/'backend'))
from models import Settings
ROOT=Path(__file__).parents[1]/'frontend'
state=Settings().model_dump(mode='json')
test_place=None
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
    def log_message(self,*a):pass
    def reply(self,data,code=200):
        body=json.dumps(data).encode();self.send_response(code)
        self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/settings':return self.reply(state)
        if path=='/api/test-observation':return self.reply({'place_name':test_place})
        if path=='/api/arrival/status':return self.reply({'loading':False,'message':'Testdaten: Ort übernommen'})
        if path=='/api/calendar/status':return self.reply({'state':'disabled','vacations':[]})
        if path=='/api/traccar/settings':return self.reply({'api_url':'http://example.invalid/api','token_saved':False,'device_id':None})
        if path.startswith('/api/'):return self.reply({'detail':'Not enabled in UI fixture'},404)
        if path=='/settings':self.path='/settings.html'
        super().do_GET()
    def do_PUT(self):
        global state
        if self.path!='/api/settings':return self.reply({'detail':'Fixture only'},403)
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if data.get('gpsd_host')=='simulate-save-error':return self.reply({'detail':'Test: Speichern fehlgeschlagen'},500)
        state=Settings.model_validate(data).model_dump(mode='json');self.reply(state)
    def do_POST(self):
        global test_place
        if self.path!='/api/arrival/test':return self.reply({'detail':'Fixture only'},403)
        from models import ArrivalTestRequest
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        test_place=ArrivalTestRequest.model_validate(data).place_name
        self.reply({'ok':True,'message':'Testdaten: Ort übernommen'},202)
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8768),Handler).serve_forever()
