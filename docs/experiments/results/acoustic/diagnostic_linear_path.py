import numpy as np
from scipy import signal,linalg
from scipy.io import wavfile
from pathlib import Path
from lab.modem import encode
import json
payload=Path('fixtures/messages/declaration-opening.txt').read_bytes().rstrip(b'\n');tx=encode(payload,'fsk4').astype(float)
results=[]
for label in ['received-declaration','received-declaration-low-volume']:
 sr,x=wavfile.read('artifacts/radio/'+label+'-stereo.wav');rx=x.mean(axis=1).astype(float)
 c=signal.correlate(rx,tx,mode='valid',method='fft');origin=int(np.argmax(abs(c)))
 print(label,'raw waveform lag',origin/sr,'correlation',c[origin]/np.linalg.norm(tx)/np.linalg.norm(rx[origin:origin+len(tx)]),flush=True)
 # Start 128 samples before strongest correlation; allow delayed and ringing energy.
 start=origin-128;y=rx[start:start+len(tx)]
 n=len(tx)//2;length=2048
 auto=signal.correlate(tx[:n],tx[:n],mode='full',method='fft')[n-1:n-1+length]
 cross=signal.correlate(y[:n],tx[:n],mode='full',method='fft')[n-1:n-1+length]
 auto[0]+=auto[0]*1e-4
 h=linalg.solve_toeplitz(auto,cross)
 yp=signal.fftconvolve(tx,h)[:len(y)]
 hold=slice(n+length,None)
 r=dict(recording=label,alignment_seconds=start/sr,fit_seconds=n/sr,filter_taps=length,validation_r2=float(1-np.sum((y[hold]-yp[hold])**2)/np.sum(y[hold]**2)),strongest_taps=[dict(delay_ms=float(k*1000/sr),value=float(h[k])) for k in np.argsort(abs(h))[-8:]])
 print(json.dumps(r),flush=True);results.append(r)
 np.savez('artifacts/radio/'+label+'-path-fit.npz',h=h,observed=y,predicted=yp,origin=start)
Path('artifacts/radio/path-fit-summary.json').write_text(json.dumps(results,indent=2)+'\n')
