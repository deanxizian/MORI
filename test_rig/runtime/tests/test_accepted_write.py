import errno
import os
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from serial import SerialTimeoutException,SerialException,PortNotOpenError
from accepted_write import write_accepted,AcceptedWriter,AcceptedPortOpener


class AcceptedWriteTests(unittest.TestCase):
    def port(self):return SimpleNamespace(is_open=True,fd=9,write_timeout=.008,pipe_abort_write_r=10)
    def test_full_acceptance_never_waits_for_next_write_room(self):
        waits=[];writes=[]
        result=write_accepted(self.port(),b'a'*20,write=lambda fd,b:(writes.append(b) or len(b)),
            wait=lambda *args:waits.append(args),clock=lambda:0.)
        self.assertEqual(result,20);self.assertEqual(waits,[]);self.assertEqual(writes,[b'a'*20])
    def test_partial_write_waits_and_sends_only_unsent_suffix(self):
        packet=bytes(range(20));chunks=[];times=[0.]
        def write(fd,data):chunks.append(data);times[0]+=.001;return 7 if len(chunks)==1 else len(data)
        def wait(r,w,x,t):self.assertLessEqual(t,.008);return [],w,[]
        self.assertEqual(write_accepted(self.port(),packet,write=write,wait=wait,clock=lambda:times[0]),20)
        self.assertEqual(chunks,[packet,packet[7:]])
    def test_eagain_then_acceptance_and_deadline_without_delivery_retry(self):
        calls=[]
        def write(fd,data):
            calls.append(data)
            if len(calls)==1:raise BlockingIOError(errno.EAGAIN,'busy')
            return len(data)
        self.assertEqual(write_accepted(self.port(),b'a'*20,write=write,wait=lambda r,w,x,t:([],w,[]),clock=lambda:0.),20)
        calls.clear()
        with self.assertRaises(SerialTimeoutException):
            write_accepted(self.port(),b'a'*20,write=lambda f,b:0,wait=lambda *args:([],[],[]),clock=lambda:0.)
    def test_os_write_returning_after_deadline_still_fails_even_if_all_accepted(self):
        t=[0.]
        def write(fd,data):t[0]=.0081;return len(data)
        with self.assertRaises(SerialTimeoutException):write_accepted(self.port(),b'a'*20,write=write,clock=lambda:t[0])
    def test_cancel_partial_returns_short_count_for_original_stop_guard(self):
        read=[]
        n=write_accepted(self.port(),b'a'*20,write=lambda *a:5,wait=lambda r,w,x,t:(r,[],[]),
                         read=lambda fd,n:read.append(fd),clock=lambda:0.)
        self.assertEqual(n,5);self.assertEqual(read,[10])
    def test_device_error_propagates_without_retry(self):
        calls=[]
        def write(*a):calls.append(a);raise OSError(errno.ENODEV,'gone')
        with self.assertRaises(SerialException):write_accepted(self.port(),b'a'*20,write=write,clock=lambda:0.)
        self.assertEqual(len(calls),1)
    def test_closed_port_wrong_packet_or_changed_budget_refused(self):
        p=self.port();p.is_open=False
        with self.assertRaises(PortNotOpenError):write_accepted(p,b'a'*20)
        for data in (b'',b'a'*19,bytearray(20)):
            with self.assertRaises(ValueError):write_accepted(self.port(),data)
        p=self.port();p.write_timeout=.02
        with self.assertRaises(ValueError):write_accepted(p,b'a'*20)

    def test_installer_idempotent_restores_original_and_writes_only_anonymous_pipe(self):
        rx,tx=os.pipe2(os.O_NONBLOCK);arx,atx=os.pipe2(os.O_NONBLOCK)
        class Port:
            is_open=True;write_timeout=.008
            def write(self,data):return -1
        p=Port();p.fd=tx;p.pipe_abort_write_r=arx;candidate=AcceptedWriter()
        try:
            candidate.install(p);first=p.write;candidate.install(p)
            self.assertIs(p.write,first)
            self.assertEqual(p.write(b'a'*20),20);self.assertEqual(os.read(rx,20),b'a'*20)
            self.assertEqual(candidate.audit()['full_first_acceptances'],1)
            self.assertEqual(candidate.audit()['wait_calls'],0)
            candidate.restore();self.assertNotIn('write',p.__dict__);self.assertEqual(p.write(b''),-1)
        finally:
            for fd in (rx,tx,arx,atx):os.close(fd)

    def test_port_context_restores_method_and_original_cleanup_on_body_fault(self):
        rx,tx=os.pipe2(os.O_NONBLOCK);arx,atx=os.pipe2(os.O_NONBLOCK);events=[]
        class Port:
            is_open=True;write_timeout=.008
            def write(self,data):return -1
        p=Port();p.fd=tx;p.pipe_abort_write_r=arx
        @contextmanager
        def original():
            events.append('open')
            try:yield p
            finally:events.append('close')
        candidate=AcceptedPortOpener(original);fault=ValueError('original_controller_fault')
        try:
            with self.assertRaises(ValueError) as raised:
                with candidate.open() as port:
                    self.assertEqual(port.write(b'a'*20),20)
                    raise fault
            self.assertIs(raised.exception,fault);self.assertEqual(events,['open','close'])
            self.assertNotIn('write',p.__dict__);self.assertEqual(p.write(b''),-1)
            self.assertEqual(candidate.audit()['calls'],1)
        finally:
            for fd in (rx,tx,arx,atx):os.close(fd)
