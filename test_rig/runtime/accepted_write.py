"""Independent POSIX candidate: stop waiting once all bytes were accepted.

Acceptance is not physical delivery. Original response/health/stop guards
remain essential. No device opening, packets, enable or retry API here.
"""
import errno
from contextlib import contextmanager
import os
import select
import time


def write_accepted(port,data,*,write=os.write,wait=select.select,clock=time.monotonic,read=os.read,audit=None):
    from serial import SerialTimeoutException,SerialException,PortNotOpenError
    if not port.is_open:raise PortNotOpenError()
    if type(data) is not bytes or len(data)!=20:raise ValueError('exact_20_byte_packet_required')
    if port.write_timeout!=.008:raise ValueError('exact_8ms_write_deadline_required')
    end=clock()+.008;sent=0
    for _ in range(64):
        before=clock()
        if before>=end:raise SerialTimeoutException('Write timeout')
        if audit is not None:audit['os_write_calls']+=1
        try:n=write(port.fd,data[sent:])
        except OSError as exc:
            if exc.errno not in (errno.EAGAIN,errno.EWOULDBLOCK,errno.EINTR):
                raise SerialException('write failed: '+str(exc)) from exc
            n=0
        after=clock()
        if audit is not None:
            audit['max_os_write_ms']=max(audit['max_os_write_ms'],1000*(after-before))
            audit['full_first_acceptances']+=int(sent==0 and n==len(data))
        if type(n) is not int or not 0<=n<=len(data)-sent:raise SerialException('invalid_os_write_count')
        sent+=n
        # Check elapsed even after full acceptance; never enlarge the budget.
        if after>=end:raise SerialTimeoutException('Write timeout')
        if sent==len(data):return sent
        # Only unsent bytes wait/retry. An accepted prefix is never replayed.
        remaining=end-clock()
        if remaining<=0:raise SerialTimeoutException('Write timeout')
        if audit is not None:audit['wait_calls']+=1
        abort,ready,_=wait([port.pipe_abort_write_r],[port.fd],[],remaining)
        if abort:read(port.pipe_abort_write_r,1000);return sent
        if not ready:raise SerialTimeoutException('Write timeout')
    raise SerialTimeoutException('Write attempt budget')


class AcceptedWriter:
    def __init__(self):
        self.port=None;self.calls=0;self.errors=0;self.max_ms=0.
        self.acceptance=dict(os_write_calls=0,full_first_acceptances=0,wait_calls=0,max_os_write_ms=0.)
    def install(self,port):
        if self.port is port:return
        if self.port is not None:raise ValueError('one_port_only')
        if os.get_blocking(port.fd):raise ValueError('nonblocking_fd_required')
        self.port=port;self.old=port.write;self.local=port.__dict__.get('write');self.had_local='write' in port.__dict__
        def write(data):
            begin=time.monotonic();self.calls+=1
            try:return write_accepted(port,data,audit=self.acceptance)
            except BaseException:self.errors+=1;raise
            finally:self.max_ms=max(self.max_ms,1000*(time.monotonic()-begin))
        port.write=write
    def restore(self):
        if self.port is not None:
            if self.had_local:self.port.write=self.local
            else:del self.port.write
    def audit(self):
        return dict(calls=self.calls,errors=self.errors,max_wall_ms=self.max_ms,**self.acceptance,
            write_deadline_s=.008,scope='all bytes accepted != physically delivered; original feedback deadline must remain8ms')


class AcceptedPortOpener:
    """Install only while the original port context owns the device."""
    def __init__(self,original):
        import serial
        if serial.VERSION!='3.5':raise ValueError('reviewed_pyserial35_required')
        self.original=original;self.writer=None
    @contextmanager
    def open(self,*args,**kwargs):
        with self.original(*args,**kwargs) as port:
            self.writer=AcceptedWriter();self.writer.install(port)
            try:yield port
            finally:self.writer.restore()
    def audit(self):
        return self.writer.audit() if self.writer is not None else dict(calls=0,port_opened=False)
