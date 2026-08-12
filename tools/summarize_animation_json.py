#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'uasset_json')
files = sorted(root.glob('*.json'))
print(f'JSON files: {len(files)}')

needles = (
    'AnimationSequencerDataModel', 'DataModel', 'MovieScene', 'ControlRig',
    'Track', 'Channel', 'Key', 'Frame', 'Time', 'Value', 'Transform',
    'Translation', 'Rotation', 'Scale', 'Bone', 'Skeleton'
)

def walk(x, path='$', out=None, depth=0):
    if out is None: out=[]
    if depth > 18: return out
    if isinstance(x, dict):
        for k,v in x.items():
            p=f'{path}.{k}'
            if any(n.lower() in str(k).lower() for n in needles):
                desc=type(v).__name__
                if isinstance(v,(str,int,float,bool)) or v is None:
                    s=repr(v)
                    if len(s)>180: s=s[:177]+'...'
                    desc += f'={s}'
                elif isinstance(v,(list,dict)):
                    desc += f' len={len(v)}'
                out.append((p,desc))
            walk(v,p,out,depth+1)
    elif isinstance(x,list):
        for i,v in enumerate(x[:2000]):
            walk(v,f'{path}[{i}]',out,depth+1)
    return out

for f in files:
    print('\n' + '='*100)
    print(f.name)
    try:
        data=json.loads(f.read_text(encoding='utf-8-sig'))
    except Exception as e:
        print('JSON READ ERROR:',e)
        continue
    hits=walk(data)
    # de-duplicate identical path/desc pairs while retaining order
    seen=set(); uniq=[]
    for h in hits:
        if h in seen: continue
        seen.add(h); uniq.append(h)
    print(f'interested paths: {len(uniq)}')
    for p,d in uniq[:500]:
        print(f'{p}: {d}')
    if len(uniq)>500:
        print(f'... {len(uniq)-500} more paths omitted')
