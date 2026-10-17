import queue
import os
import pty
import select
import termios
import time
import unittest
from unittest import mock

from cam_indicator import CamConsole,CamIndicator,IndicatorError,SOUND_GAP_S


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.master,self.slave=pty.openpty()
        self.path=os.ttyname(self.slave)

    def tearDown(self):
        os.close(self.master);os.close(self.slave)

    def test_roundtrip_is_raw_and_close_does_not_request_hangup(self):
        port=CamConsole(self.path)
        try:
            self.assertFalse(termios.tcgetattr(port.fd)[2]&termios.HUPCL)
            self.assertEqual(port.read(1024),b'')
            self.assertEqual(port.write(b'C'),1)
            self.assertTrue(select.select([self.master],[],[],.1)[0])
            self.assertEqual(os.read(self.master,16),b'C')
            os.write(self.master,b'MORI_MOTION_ACK 1 0\n')
            self.assertEqual(port.read(1024),b'MORI_MOTION_ACK 1 0\n')
        finally:port.close()
        port.close()

    def test_second_owner_cannot_open_the_console(self):
        port=CamConsole(self.path)
        try:
            with self.assertRaises(BlockingIOError):CamConsole(self.path)
        finally:port.close()

    def test_write_timeout_is_an_indicator_fault(self):
        port=CamConsole(self.path)
        try:
            with mock.patch('select.select',return_value=([],[],[])):
                with self.assertRaisesRegex(IndicatorError,'write_timeout'):port.write(b'M')
        finally:port.close()

    def test_disconnection_is_not_silent_empty_input(self):
        port=CamConsole(self.path)
        try:
            with mock.patch('select.select',return_value=([port.fd],[],[])),mock.patch('os.read',return_value=b''):
                with self.assertRaisesRegex(IndicatorError,'disconnected'):port.read(1024)
        finally:port.close()


class Port:
    def __init__(self):self.q=queue.Queue();self.writes=[];self.closed=False;self.silent=False;self.n=100
    def reset_input_buffer(self):pass
    def write(self,data):
        self.writes.append(data)
        self.n+=1
        if not self.silent:
            if data==b'C':self.q.put(b'MORI_MOTION_READY v=1 ttl_ms=350\n')
            elif data in (b'M',b'm'):self.q.put(('MORI_MOTION_ACK %d %d\n'%(self.n+(0x80000000 if data==b'M' else 0),data==b'M')).encode())
        return len(data)
    def read(self,n):
        try:return self.q.get(timeout=.01)
        except queue.Empty:return b''
    def close(self):self.closed=True


class IndicatorTests(unittest.TestCase):
    def test_handshake_active_ack_and_explicit_final_off(self):
        p=Port();r={}
        with CamIndicator(r,port=p) as cue:
            end=time.monotonic()+.2
            while time.monotonic()<end:cue.tick();time.sleep(.01)
            self.assertTrue(cue.ack_visible)
        self.assertTrue(r['final_off_frame_acknowledged']);self.assertTrue(p.closed)
        self.assertIn('red_frame_ack',[x['event'] for x in r['events']])
        self.assertEqual(p.writes[-1],b'm')
        self.assertEqual(p.writes.count(b'b'),3)
        tones=[x for x in r['events'] if x['event']=='sound_command_sent']
        self.assertEqual([(x['edge'],x['number']) for x in tones],[('start',1),('stop',1),('stop',2)])
        self.assertGreaterEqual(tones[2]['t']-tones[1]['t'],SOUND_GAP_S-.03)
        self.assertEqual(r['sound']['pending_at_close'],0)

    def test_frozen_controller_stops_host_heartbeat(self):
        p=Port();r={}
        with CamIndicator(r,port=p) as cue:
            cue.tick();time.sleep(.23)
            with self.assertRaisesRegex(IndicatorError,'control_heartbeat_expired'):cue.check()
            self.assertEqual([x for x in p.writes if x in (b'M',b'm')][-1],b'm')
        self.assertEqual(p.writes.count(b'b'),3)

    def test_off_preflight_and_repeated_off_frames_are_silent(self):
        p=Port();r={}
        with CamIndicator(r,port=p):time.sleep(.12)
        self.assertEqual(p.writes.count(b'b'),0)

    def test_no_start_sound_before_frame_ack_and_no_repeat_per_heartbeat(self):
        clock=[10.];p=Port();cue=CamIndicator({},port=p,now=lambda:clock[0])
        cue._line(b'MORI_MOTION_ACK 99 0')
        cue.tick();cue._sound_tick();self.assertNotIn(b'b',p.writes)
        for token in (100,101,102):
            cue._line(('MORI_MOTION_ACK %d 1'%token).encode());cue._sound_tick()
        self.assertEqual(p.writes.count(b'b'),1)
        cue.deactivate()
        cue._line(b'MORI_MOTION_ACK 102 0');cue._sound_tick()
        clock[0]+=SOUND_GAP_S;cue._sound_tick()
        self.assertEqual(p.writes.count(b'b'),3)

    def test_buffered_active_ack_after_deactivate_cannot_announce_start(self):
        clock=[10.];p=Port();cue=CamIndicator({},port=p,now=lambda:clock[0])
        cue._line(b'MORI_MOTION_ACK 99 0')
        cue.tick();cue.deactivate()
        cue._line(b'MORI_MOTION_ACK 100 1');cue._sound_tick()
        cue._line(b'MORI_MOTION_ACK 101 0');cue._sound_tick()
        self.assertNotIn(b'b',p.writes)

    def test_new_active_frame_cancels_delayed_stop_tone(self):
        clock=[10.];p=Port();cue=CamIndicator({},port=p,now=lambda:clock[0])
        cue._line(b'MORI_MOTION_ACK 99 0')
        cue.tick();cue._line(b'MORI_MOTION_ACK 100 1');cue._sound_tick()
        cue.deactivate();cue._line(b'MORI_MOTION_ACK 101 0');cue._sound_tick()
        cue.tick();cue._line(b'MORI_MOTION_ACK 102 1');cue._sound_tick()
        clock[0]+=SOUND_GAP_S;cue._sound_tick()
        self.assertEqual([x['edge'] for x in cue.report['events'] if x['event']=='sound_command_sent'],
                         ['start','stop','start'])

    def test_missing_render_acks_faults_even_while_control_ticks(self):
        p=Port();r={}
        with CamIndicator(r,port=p) as cue:
            p.silent=True
            with self.assertRaisesRegex(IndicatorError,'ack_stale'):
                end=time.monotonic()+1.
                while time.monotonic()<end:cue.tick();time.sleep(.01)

    def test_duplicate_ack_cannot_refresh_liveness(self):
        clock=[10.];cue=CamIndicator({},port=Port(),now=lambda:clock[0])
        cue._line(b'MORI_MOTION_ACK 123 0');self.assertEqual(cue.ack_at,10.)
        clock[0]=20.;cue._line(b'MORI_MOTION_ACK 123 0')
        self.assertEqual(cue.ack_at,10.)


if __name__=='__main__':unittest.main()
