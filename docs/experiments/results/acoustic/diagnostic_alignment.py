from pathlib import Path
import numpy as np
from scipy import signal,optimize
from scipy.io import wavfile
from lab.modem import reference_frame
payload=Path('fixtures/messages/declaration-opening.txt').read_bytes().rstrip(b'\n')
truth=np.unpackbits(np.frombuffer(reference_frame(payload,'fsk4'),np.uint8)).reshape(-1,2)@np.array([2,1])
for label in ['received-declaration','received-declaration-low-volume']:
 sr,x=wavfile.read('artifacts/radio/'+label+'-stereo.wav');x=x.mean(axis=1).astype(float)
 t=np.arange(len(x)); es=[]
 for f in [900,1500,2100,2700]:
  z=x*np.exp(-2j*np.pi*f*t/sr);c=np.r_[0,np.cumsum(z)];es.append(abs(c[80:]-c[:-80])**2)
 e=np.array(es).T
 # Normalize each window's total energy. Correlate against known transmitted symbols.
 p=e/(e.sum(axis=1,keepdims=True)+1e-20)
 scores=0
 for k in range(4):
  template=np.zeros((len(truth)-1)*20+1);template[::20]=(truth==k)
  scores=scores+signal.correlate(p[::4,k],template,mode='valid',method='fft')
 start=np.argmax(scores)*4
 n=np.arange(len(truth))
 def score(v):
  idx=np.rint(v[0]+n*v[1]).astype(int)
  if idx.min()<0 or idx.max()>=len(p):return 1e6
  return -p[idx,truth].mean()
 fit=optimize.differential_evolution(score,[(start-160,start+160),(79.75,80.25)],seed=42,tol=1e-8)
 start,period=fit.x;idx=np.rint(start+n*period).astype(int);pred=e[idx].argmax(axis=1)
 conf=np.zeros((4,4),int);np.add.at(conf,(truth,pred),1)
 print(label,'start',start/sr,'period',period,'ppm',(period/80-1)*1e6,'correct',np.mean(pred==truth),'sync errors',sum(pred[64:80]!=truth[64:80]),flush=True)
 print(conf,flush=True)
 print('header expected',reference_frame(payload,'fsk4')[20:28].hex(),'predicted',np.packbits(np.column_stack((pred>>1,pred&1)).ravel())[20:28].tobytes().hex(),flush=True)
 np.savez('artifacts/radio/'+label+'-aligned.npz',energies=e[idx],truth=truth,indices=idx,start=start,period=period)
