import unittest
import ldmlib

class Tests(unittest.TestCase):

    def test_to_from_bytes(self):
        '''test equality after converting to bytes and back.'''
        dct = {field: i for i, field in enumerate(ldmlib.CAM.__attrs__)}
        dct['message_id'] = 2
        m_from_dct = ldmlib.CAM(**dct)
        b = m_from_dct.as_bytes()
        m_from_bytes = ldmlib.CAM.from_bytes(b)
        self.assertEqual(m_from_dct, m_from_bytes)
        self.assertEqual(b, m_from_bytes.as_bytes())
        return
