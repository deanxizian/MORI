import unittest
from unittest.mock import patch

from air_trial import exchange_for
from attitude import Fault
from protocol import locked_query


class WriteAuditTests(unittest.TestCase):
    def test_write_fault_records_elapsed_propagates_and_never_retries(self):
        error=TimeoutError('Write timeout')
        class Port:
            t=100.;calls=0
            def reset_input_buffer(self):pass
            def write(self,packet):
                self.calls+=1;self.t+=.009;raise error
            def read(self,_):raise AssertionError('read after failed write')
        port=Port();report={'transactions':[]}
        with self.assertRaises(TimeoutError) as caught:
            exchange_for(port,0,report,now=lambda:port.t)(locked_query(0),'test')
        self.assertIs(caught.exception,error);self.assertEqual(port.calls,1)
        row=report['transactions'][0]
        self.assertEqual(row['tx_hex'],locked_query(0).hex())
        self.assertAlmostEqual(row['write_attempt_ms'],9.)
        self.assertEqual(row['write_error_type'],'TimeoutError')
        self.assertNotIn('bytes_written',row)
        self.assertNotIn('write_completed_monotonic',row)

    def test_success_and_short_write_keep_existing_semantics(self):
        for count in [20,19]:
            class Port:
                t=100.;calls=0;in_waiting=1
                def reset_input_buffer(self):pass
                def write(self,packet):
                    self.calls+=1;self.t+=.0007;return count
                def read(self,_):self.t+=.0003;return b'reply'
            class Stream:
                bad_frames=discarded_bytes=0
                def __init__(self,_):pass
                def feed(self,_):return [dict(id=0,mode=0)]
            port=Port();report={'transactions':[]};call=exchange_for(port,0,report,now=lambda:port.t)
            with patch('air_trial.FeedbackStream',Stream):
                if count==20:
                    self.assertEqual(call(locked_query(0),'test')['id'],0)
                else:
                    with self.assertRaisesRegex(Fault,'incomplete_serial_write'):
                        call(locked_query(0),'test')
            row=report['transactions'][0]
            self.assertEqual(port.calls,1);self.assertEqual(row['bytes_written'],count)
            self.assertAlmostEqual(row['write_attempt_ms'],.7)
            self.assertNotIn('write_error_type',row)


if __name__=='__main__':unittest.main()
