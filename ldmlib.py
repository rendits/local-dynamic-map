'''Shared class definitions.


'''

import math
import struct
import datetime

datetime_2004 = datetime.datetime(year=2004, month=1, day=1)
def timestampits_now():
    '''return the current ITS timestamp, i.e., the number of milliseconds
    since the beginning of 2004.

    '''
    return round(
        (datetime.datetime.now() - datetime_2004).total_seconds() * 1000
    )

def gdt_now(timestampits):
    '''convert an ITS timestamp into generation delta time.'''
    return timestampits_now() % 65536

def timestampits_from_gdt(gdt):
    '''convert generation delta time into an ITS timestamp. Assumes that
    less than 65536 ms has passed since gdt was generated.

    '''

    # round down to closest multiple of 65536 ms
    ts = timestampits_now()
    ts -= ts % 65536

    # add the specified number of ms and return
    ts += gdt
    return ts

class CAM(object):
    '''ETSI ITS-G5 Cooperative awareness message (CAM).

    Allows converting byte arrays formatted according to the Rendits
    simple message set spec. to/from CAM message objects.

    See ETSI EN 302 637-2 for an explanation of what the fields represent.
    https://www.etsi.org/deliver/etsi_en/302600_302699/30263702/01.03.01_30/en_30263702v010301v.pdf

    Any non-required (as indicated by the __attrs__ list) field may be
    safely omitted. Omitted fields are replaced with a special value
    indicating that the field is unavailable.

    '''

    # CAM message fields.
    __attrs__ = [
        'message_id', # has to be 2
        'station_id', # required
        'gen_delta_time_millis', # required
        'container_mask',
        'station_type',
        'latitude',
        'longitude',
        'semi_major_axis_confidence',
        'semi_minor_axis_confidence',
        'semi_major_orientation',
        'altitude',
        'heading',
        'heading_confidence',
        'speed',
        'speed_confidence',
        'vehicle_length',
        'vehicle_width',
        'longitudinal_acceleration',
        'longitudinal_acceleration_confidence',
        'yaw_rate',
        'yaw_rate_confidence',
        'vehicle_role'
    ]

    # values indicating the field is unavailable
    unavailable_indicators = {
        'container_mask': 0,
        'station_type': 0,
        'latitude': 900000001,
        'longitude': 1800000001,
        'semi_major_axis_confidence': 4095,
        'semi_minor_axis_confidence': 4095,
        'semi_major_orientation': 3601,
        'altitude': 800001,
        'heading': 3601,
        'heading_confidence': 127,
        'speed': 16383,
        'speed_confidence': 127,
        'vehicle_length': 1023,
        'vehicle_width': 62,
        'longitudinal_acceleration': 161,
        'longitudinal_acceleration_confidence': 102,
        'yaw_rate': 32767,
        'yaw_rate_confidence': 8,
        'vehicle_role': 0,
    }

    # packed bytes representation of a CAM message
    bytes_format = '!biibiiiiiiiiiiiiiiiiii'

    def __init__(self, **kwargs):
        '''create a new CAM message.

        '''
        self.__dict__.update(self.unavailable_indicators)
        self.__dict__.update(kwargs)
        if not 'message_id' in kwargs:
            kwargs['message_id'] = 2
        if not kwargs['message_id'] == 2:
            raise ValueError('message_id must be 2, but is {}'.format(kwargs['message_id']))
        if 'station_id' not in kwargs:
            raise ValueError('station_id is required, but was not given')
        if 'gen_delta_time_millis' not in kwargs:
            raise ValueError('gen_delta_time_millis is required, but was not given')

        # store the absolute time
        self.__dict__['timestampits'] = timestampits_from_gdt(
            kwargs['gen_delta_time_millis'],
        )
        return

    @classmethod
    def from_bytes(cls, b):
        '''create a CAM object from a byte array b formatted according to the
        simple message set spec.

        '''
        if not isinstance(b, bytes):
            raise TypeError('b must be of type bytes, but is {}'.format(type(b)))
        values = struct.unpack(cls.bytes_format, b)
        return cls(
            **{field: value for field, value in zip(
                cls.__attrs__,
                values,
            )}
        )

    def as_bytes(self):
        '''return the bytes representation of the message.'''
        return struct.pack(
            self.bytes_format,
            *[self.__dict__[field] for field in self.__attrs__],
        )

    def as_dict(self):
        '''return the message as a dict.'''
        return {field: self.__dict__[field] for field in self.__attrs__}

    def age(self, timestampits=None):
        '''return the age of the message in milliseconds.'''
        if timestampits is None:
            timestampits = timestampits_now()
        return timestampits - self['timestampits']

    def __getitem__(self, field):
        '''dict-like access to message fields.'''
        return self.__dict__[field]

    def __repr__(self):
        return 'CAM' + str(self.as_dict())

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        for field in self.__attrs__:
            if self.__dict__[field] != other.__dict__[field]:
                return False
        return True

    def __hash__(self):
        return hash(frozenset(self.as_dict().items()))

class LDM(object):
    '''Local dynamic map. Associates CAM messages with the transmitting
    vehicle and allows iterating over the latest CAM received by
    vehicles.

    '''

    def __init__(self):
        '''create a new LMD. just initializes an empty dict.'''
        self.cams = dict()

    def __getitem__(self, station_id):
        '''dict-like access to the latest CAM received with given
        station_id.

        '''
        return self.cams[station_id]

    def __setitem__(self, station_id, cam):
        '''associate a CAM message with a station_id'''
        self.cams[station_id] = cam

    def __repr__(self):
        return 'LDM{{nvehicles={}}}'.format(len(self.cams))

    def iter_cams(self, position=None, max_distance=None, max_age=None):
        '''return an iterator over the latest CAM received by vehicles from
        each vehicle. allows filtering by distance and how long age
        the message was received.

        args:

        position: a tuple of length 2 (longitude, latitude).  optional
        but must be given is max_distance is given.

        max_distance: only return CAMs received from vehicles at most
        this distance from position. given as a floating point number
        representing distance in meters.

        max_age: only return CAMs at most this number of milliseconds
        old.

        '''
        if max_distance is None:
            max_distance = math.inf
        elif position is None:
            raise ValueError('position must be given if max_distance is.')
        if position is None:
            position = (0.0, 0.0)
            max_distance = math.inf
        if max_age is None:
            max_age = math.inf
        timestampits = timestampits_now()
        longitude, latitude = position
        for station_id, cam in self.cams.items():
            if cam.age(timestampits=timestampits) > max_age:
                continue
            distance = math.sqrt(
                pow(cam['longitude']-longitude, 2) + pow(cam['latitude'] - latitude, 2)
            )
            if distance > max_distance:
                continue
            yield cam
        return
