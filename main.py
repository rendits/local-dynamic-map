'''Main module for running the LDM on a developer PC.

LICENSE:
Copyright 2019 Rendits

Licensed under the Apache License, Version 2.0 (the "License"); you
may not use this file except in compliance with the License.  You may
obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied.  See the License for the specific language governing
permissions and limitations under the License.

'''

import time
import socket
import logging
import argparse
import threading
import functools

import ldmlib

parser = argparse.ArgumentParser(description='Rendits Local Dynamic Map')
parser.add_argument(
    '--port',
    dest='port',
    default='6000',
    help='port to receive local CAMs on.',
)

def receiver(ldm, port):
    '''listen for local CAM messages and update the LDM accordingly.'''
    if not isinstance(ldm, ldmlib.LDM):
        raise TypeError('ldm must be of type LDM, but is {}'.format(type(ldm)))
    logging.info('Listening for local CAM messages on port {}.'.format(port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('localhost', port))
    while True:
        data = sock.recv(256)
        cam = ldmlib.CAM.from_bytes(data)
        ldm[cam['station_id']] = cam
        # logging.info('associated {} with {}'.format(cam, cam['station_id']))
    return

def printer(ldm):
    '''periodically print CAM messages.'''
    while True:
        time.sleep(2)
        for cam in ldm.iter_cams():
            station_id = cam['station_id']
            age = cam.age()
            logging.info('station_id={}, age={}ms : {}'.format(station_id, age, cam))

    return

def main():
    args = parser.parse_args()
    port = int(args.port)
    ldm = ldmlib.LDM()
    receiver_thread = threading.Thread(
        target=functools.partial(receiver, ldm, port),
    )
    receiver_thread.start()

    printer_thread = threading.Thread(
        target=functools.partial(printer, ldm),
    )
    printer_thread.start()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
