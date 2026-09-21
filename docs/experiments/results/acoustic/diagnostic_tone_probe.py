import numpy as np,zlib,json
from pathlib import Path
from scipy.io import wavfile

def parse(pred):
 sync=np.array([3,1,0,3,2,1,0,1,3,0,1,1,2,2,1,3]) # replaced from actual bytes below
 bits=np.unpackbits(np.frombuffer(bytes.fromhex('d391c5a7'),np.uint8)).reshape(-1,2);sync=bits@np.array([2,1])
 match=np.ones(len(pred)-15,dtype=bool)
 for i,k in enumerate(sync):match&=pred[i:len(pred)-15+i]==k
 for start in np.flatnonzero(match):
  p=pred[start+16:];b=np.packbits(np.column_stack((p>>1,p&1)).ravel()).tobytes()
  if len(b)<12 or b[:2]!=b'\x00\x02' or zlib.crc32(b[:4]).to_bytes(4,'big')!=b[4:8]:continue
  n=int.from_bytes(b[2:4],'big')
  if n>1024 or len(b)<12+n:continue
  if zlib.crc32(b[:4]+b[8:8+n]).to_bytes(4,'big')==b[8+n:12+n]:return b[8:8+n]
 return None

for label,bounds in [('received-declaration-low-volume',(9.2,12.6)),('received-declaration',(10.6,14.1))]:
 sr,x=wavfile.read('artifacts/radio/'+label+'-stereo.wav');x=x.mean(axis=1)[int(bounds[0]*sr):int(bounds[1]*sr)].astype(float)
 t=np.arange(len(x));zs=[np.r_[0,np.cumsum(x*np.exp(-2j*np.pi*f*t/sr))] for f in [900,1500,2100,2700]]
 for win in [80,64,48,32,96,112]:
  e=np.array([abs(z[win:]-z[:-win])**2 for z in zs]).T
  for quantile in [None,75,90,95,99]:
   scale=np.ones(4) if quantile is None else np.percentile(e,quantile,axis=0)
   pred=(e/scale).argmax(axis=1)
   for phase in range(80):
    p=parse(pred[phase::80])
    if p is not None:
     print('SUCCESS',label,win,quantile,phase,len(p),flush=True);Path('artifacts/radio/'+label+'-probe-recovered.txt').write_bytes(p)
  print(label,win,'done',flush=True)
