"""Loopback development only. Cloud deployment uses the separate HTTPS proxy."""
import os,uvicorn
if __name__=='__main__':
 print('MORI SIMULATED gateway; one-use pairing code is in .state/pairing.txt (0600).')
 uvicorn.run('backend.mori.app:create_app',factory=True,host='127.0.0.1',port=int(os.environ.get('PORT','8765')),ws_max_size=4096,log_level='warning')
