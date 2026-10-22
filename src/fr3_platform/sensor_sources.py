"""Explicit synthetic/replay sources. No RealSense or FlexiTac hardware reader."""
from typing import Protocol
import struct
from .contracts import VERSION
from .data import DatasetReader

class CameraSource(Protocol):
    def frames(self, stamp:dict, sequence:int): ...

class TactileSource(Protocol):
    def frames(self, stamp:dict, sequence:int): ...


def envelope(kind,stream,stamp,sequence,payload):
    return {'schema':VERSION,'id':f'{stream}-{sequence}','kind':kind,'stream':stream,'source':'synthetic','stamp':{**stamp,'sequence':sequence},'payload':payload}

class SyntheticCamera:
    def __init__(self,identity,color_offset=0):self.identity=identity;self.offset=color_offset
    def frames(self,stamp,sequence):
        meta={'camera_id':self.identity,'pair_id':f'{self.identity}-{sequence}','valid':True,'quality_flags':['SYNTHETIC'],
              'intrinsics':{'fx':8.,'fy':8.,'cx':3.5,'cy':3.5,'source':'synthetic'},'extrinsics':'SYNTHETIC_NOT_PHYSICAL','calibration_version':'synthetic-camera-v1'}
        rgb=bytes([(self.offset+sequence)%255,40,80]*64)
        depth=struct.pack('<64H',*([100+sequence]*64))
        return [(envelope('rgb',self.identity+'.rgb',stamp,sequence,{**meta,'shape':[8,8,3],'dtype':'uint8','encoding':'rgb8'}),rgb),
                (envelope('depth',self.identity+'.depth',stamp,sequence,{**meta,'shape':[8,8],'dtype':'uint16_le','depth_scale_m':.001,'invalid_values':[0]}),depth)]

class SyntheticTactile:
    def __init__(self,identity='synthetic-tactile'):self.identity=identity
    def frames(self,stamp,sequence):
        p={'sensor_id':self.identity,'shape':[2],'dtype':'uint16_le','quantity':'raw_reading','calibration_version':'UNCONFIGURED','calibrated':None,'valid':True,'quality_flags':['SYNTHETIC'],'protocol':'NOT_A_HARDWARE_PROTOCOL'}
        return [(envelope('tactile','tactile',stamp,sequence,p),struct.pack('<2H',sequence,sequence+1))]

class ReplaySensorSource:
    def __init__(self,episode,streams):self.reader=DatasetReader(episode);self.streams=set(streams)
    def __iter__(self):
        for e in self.reader:
            if e['stream'] in self.streams:yield e,self.reader.blob(e)
