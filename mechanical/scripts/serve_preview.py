"""Loopback-only static review server, including byte ranges for video seeking."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
from pathlib import Path
import argparse,os,re

class PreviewHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.byte_range=None
        raw=self.headers.get('Range')
        path=Path(self.translate_path(self.path))
        if not raw or not path.is_file():return super().send_head()
        try:
            stream=path.open('rb');stat=os.fstat(stream.fileno());size=stat.st_size
        except OSError:return self.send_error(404,'File not found')
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',raw.strip())
        if not match or not any(match.groups()):
            stream.close();return self.unsatisfied(size)
        a,b=match.groups()
        if a:
            start=int(a);end=min(int(b),size-1) if b else size-1
        else:
            start=max(0,size-int(b));end=size-1
        if start<0 or start>=size or end<start:
            stream.close();return self.unsatisfied(size)
        self.byte_range=(start,end-start+1);stream.seek(start)
        self.send_response(206)
        self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Last-Modified',self.date_time_string(stat.st_mtime))
        self.end_headers();return stream

    def unsatisfied(self,size):
        self.send_response(416);self.send_header('Content-Range',f'bytes */{size}')
        self.send_header('Content-Length','0');self.end_headers();return None

    def end_headers(self):
        self.send_header('Accept-Ranges','bytes')
        super().end_headers()

    def copyfile(self,source,output):
        try:
            if self.byte_range is None:return super().copyfile(source,output)
            left=self.byte_range[1]
            while left:
                data=source.read(min(left,1024*1024))
                if not data:break
                output.write(data);left-=len(data)
        except (BrokenPipeError,ConnectionResetError):
            pass # Browsers cancel pending media reads when seeking.

class PreviewServer(ThreadingHTTPServer):
    request_queue_size=64

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=58201)
    parser.add_argument('--directory',type=Path,default=Path(__file__).resolve().parents[2])
    args=parser.parse_args()
    server=PreviewServer(('127.0.0.1',args.port),partial(PreviewHandler,directory=str(args.directory)))
    print(f'MORI preview http://127.0.0.1:{args.port}/mechanical/',flush=True)
    server.serve_forever()
