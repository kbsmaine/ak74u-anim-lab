#!/usr/bin/env python3
"""Retarget CUE4Parse PSA exports onto the already-working browser GLBs.

Why this exists:
UE5.5 loose *editor* USkeletalMesh assets in this Marketplace pack do not expose
cooked RenderData LODs to CUE4Parse, so PSK mesh export fails even though the
animation sequences can be decoded. We do not need those meshes: the repository
already contains the user's visible Mixamo FP arms and split AR-15 GLBs.

This script:
  * reads the real CUE4Parse ActorX .psa animations
  * retargets UE5 Mannequin arm/finger world-rotation deltas onto the Mixamo rig
  * applies weapon/root + magazine motion to the split AR-15
  * writes two browser-ready GLBs containing ONLY the real extracted clips
"""
from __future__ import annotations
import argparse, json, math, re, struct
from dataclasses import dataclass
from pathlib import Path
import numpy as np

# Unreal -> glTF-ish world basis: UE X forward, Y right, Z up
# becomes glTF -Z forward, +X right, +Y up. UE "left" (-Y) becomes +X,
# matching the supplied Mixamo GLB where the left arm extends toward +X.
C_UE_TO_GLTF = np.array([[0.,-1.,0.],[0.,0.,1.],[-1.,0.,0.]], dtype=np.float64)
CM_TO_M = 0.01


def cstr(b: bytes) -> str:
    return b.split(b'\0',1)[0].decode('utf-8','replace')


def read_chunks(path: Path):
    data=path.read_bytes(); off=0; out={}
    while off+32 <= len(data):
        cid,typeflag,size,count=struct.unpack_from('<20siii',data,off); off+=32
        name=cstr(cid); n=size*count
        if n<0 or off+n>len(data): raise ValueError(f'{path}: invalid {name} chunk')
        out[name]={'size':size,'count':count,'data':memoryview(data)[off:off+n]}; off+=n
    return out

@dataclass
class Bone:
    name:str; parent:int; q:np.ndarray; t:np.ndarray
@dataclass
class AnimInfo:
    name:str; total_bones:int; track_time:float; rate:float; first_raw_frame:int; frames:int
@dataclass
class Psa:
    bones:list[Bone]; infos:list[AnimInfo]; keys:np.ndarray


def parse_bones(chunk)->list[Bone]:
    d=chunk['data']; sz=chunk['size']; out=[]
    if sz<120: raise ValueError(f'Unexpected BONENAMES record size {sz}')
    for i in range(chunk['count']):
        r=d[i*sz:(i+1)*sz]
        name,flags,nchild,parent=struct.unpack_from('<64sIii',r,0)
        q=np.array(struct.unpack_from('<4f',r,76),float)
        t=np.array(struct.unpack_from('<3f',r,92),float)
        out.append(Bone(cstr(name),int(parent),q,t))
    return out


def parse_psa(path:Path)->Psa:
    c=read_chunks(path); bc=c.get('BONENAMES'); ac=c.get('ANIMINFO'); kc=c.get('ANIMKEYS')
    if not all((bc,ac,kc)): raise ValueError(f'{path}: missing PSA chunks {list(c)}')
    bones=parse_bones(bc); infos=[]
    for i in range(ac['count']):
        r=ac['data'][i*ac['size']:(i+1)*ac['size']]
        vals=struct.unpack_from('<64s64siiiifffiii',r,0)
        infos.append(AnimInfo(cstr(vals[0]),int(vals[2]),float(vals[7]),float(vals[8]),int(vals[10]),int(vals[11])))
    keys=[]
    for i in range(kc['count']):
        r=kc['data'][i*kc['size']:(i+1)*kc['size']]
        p=struct.unpack_from('<3f',r,0); q=struct.unpack_from('<4f',r,12); tm=struct.unpack_from('<f',r,28)[0]
        keys.append((*p,*q,tm))
    return Psa(bones,infos,np.asarray(keys,dtype=np.float64))


def qnorm(q):
    q=np.asarray(q,float); n=np.linalg.norm(q); return q/n if n else np.array([0.,0.,0.,1.])

def qmat(q):
    x,y,z,w=qnorm(q); xx=x*x;yy=y*y;zz=z*z;xy=x*y;xz=x*z;yz=y*z;wx=w*x;wy=w*y;wz=w*z
    return np.array([[1-2*(yy+zz),2*(xy-wz),2*(xz+wy)],
                     [2*(xy+wz),1-2*(xx+zz),2*(yz-wx)],
                     [2*(xz-wy),2*(yz+wx),1-2*(xx+yy)]],float)

def matq(m):
    m=np.asarray(m,float); tr=float(np.trace(m))
    if tr>0:
        s=math.sqrt(tr+1.0)*2; w=.25*s; x=(m[2,1]-m[1,2])/s; y=(m[0,2]-m[2,0])/s; z=(m[1,0]-m[0,1])/s
    elif m[0,0]>m[1,1] and m[0,0]>m[2,2]:
        s=math.sqrt(max(1e-12,1+m[0,0]-m[1,1]-m[2,2]))*2; w=(m[2,1]-m[1,2])/s; x=.25*s; y=(m[0,1]+m[1,0])/s; z=(m[0,2]+m[2,0])/s
    elif m[1,1]>m[2,2]:
        s=math.sqrt(max(1e-12,1+m[1,1]-m[0,0]-m[2,2]))*2; w=(m[0,2]-m[2,0])/s; x=(m[0,1]+m[1,0])/s; y=.25*s; z=(m[1,2]+m[2,1])/s
    else:
        s=math.sqrt(max(1e-12,1+m[2,2]-m[0,0]-m[1,1]))*2; w=(m[1,0]-m[0,1])/s; x=(m[0,2]+m[2,0])/s; y=(m[1,2]+m[2,1])/s; z=.25*s
    return qnorm([x,y,z,w])

def rot_only(m):
    u,_,vh=np.linalg.svd(np.asarray(m,float)[:3,:3]); r=u@vh
    if np.linalg.det(r)<0: u[:,-1]*=-1; r=u@vh
    return r

def make4(r,t):
    m=np.eye(4); m[:3,:3]=r; m[:3,3]=t; return m

def actorx_key_to_unreal(key,bone_index):
    # ActorXAnim writer mirrors key Y and flips root W on export.
    p=np.array([key[0],-key[1],key[2]],float)
    q=np.array([key[3],-key[4],key[5],-key[6] if bone_index==0 else key[6]],float)
    return p,qnorm(q)

def source_rest_globals(bones:list[Bone]):
    out=[None]*len(bones)
    def go(i):
        if out[i] is not None:return out[i]
        b=bones[i]; lm=make4(qmat(b.q),b.t); p=b.parent
        out[i]=lm if i==0 or p<0 or p==i or p>=len(bones) else go(p)@lm
        return out[i]
    for i in range(len(bones)):go(i)
    return out

def source_anim_globals(psa:Psa,info:AnimInfo,frame:int):
    n=info.total_bones; out=[None]*n
    # CUE4Parse writes PSA ANIMKEYS frame-major: frame -> bone.
    base=(info.first_raw_frame+frame)*n
    def go(i):
        if out[i] is not None:return out[i]
        p,q=actorx_key_to_unreal(psa.keys[base+i],i); lm=make4(qmat(q),p); par=psa.bones[i].parent
        out[i]=lm if i==0 or par<0 or par==i or par>=n else go(par)@lm
        return out[i]
    for i in range(n):go(i)
    return out

# ----- GLB editing -----
def read_glb(path:Path):
    data=path.read_bytes(); magic,ver,total=struct.unpack_from('<4sII',data,0)
    if magic!=b'glTF' or ver!=2: raise ValueError(f'{path}: not GLB2')
    off=12; doc=None; blob=b''
    while off<total:
        ln,typ=struct.unpack_from('<II',data,off);off+=8;chunk=data[off:off+ln];off+=ln
        if typ==0x4E4F534A:doc=json.loads(chunk.decode('utf-8').rstrip('\x00 '))
        elif typ==0x004E4942:blob=chunk
    return doc,bytearray(blob)

def write_glb(path:Path,doc,blob:bytearray):
    doc.setdefault('buffers',[{}])[0]['byteLength']=len(blob)
    js=json.dumps(doc,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
    bb=bytes(blob);bb+=b'\0'*((-len(bb))%4)
    total=12+8+len(js)+8+len(bb);out=bytearray(struct.pack('<4sII',b'glTF',2,total))
    out+=struct.pack('<II',len(js),0x4E4F534A)+js;out+=struct.pack('<II',len(bb),0x004E4942)+bb
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(out)

def append_accessor(doc,blob,arr,typ,minmax=False):
    arr=np.asarray(arr,dtype='<f4');
    while len(blob)%4:blob.append(0)
    off=len(blob);raw=arr.tobytes();blob.extend(raw)
    doc.setdefault('bufferViews',[]).append({'buffer':0,'byteOffset':off,'byteLength':len(raw)})
    ac={'bufferView':len(doc['bufferViews'])-1,'byteOffset':0,'componentType':5126,'count':int(arr.shape[0]),'type':typ}
    if minmax:
        a=arr.reshape(arr.shape[0],-1);ac['min']=[float(x) for x in a.min(0)];ac['max']=[float(x) for x in a.max(0)]
    doc.setdefault('accessors',[]).append(ac);return len(doc['accessors'])-1

def node_local(node):
    if 'matrix' in node:return np.array(node['matrix'],float).reshape(4,4).T
    r=qmat(node.get('rotation',[0,0,0,1]));s=np.asarray(node.get('scale',[1,1,1]),float);m=np.eye(4);m[:3,:3]=r@np.diag(s);m[:3,3]=node.get('translation',[0,0,0]);return m

def target_rest(doc):
    parents={}
    for pi,n in enumerate(doc['nodes']):
        for c in n.get('children',[]):parents[c]=pi
    L=[node_local(n) for n in doc['nodes']]; G=[None]*len(L)
    def go(i):
        if G[i] is not None:return G[i]
        G[i]=go(parents[i])@L[i] if i in parents else L[i];return G[i]
    for i in range(len(L)):go(i)
    return parents,L,G

def nrm(s):return re.sub(r'[^a-z0-9]+','_',s.lower()).strip('_')

TARGET_ARM_MAP={
 'pelvis':'mixamorig:Hips','hips':'mixamorig:Hips',
 'spine_01':'mixamorig:Spine','spine1':'mixamorig:Spine',
 'spine_02':'mixamorig:Spine1','spine2':'mixamorig:Spine1',
 'spine_03':'mixamorig:Spine2','spine3':'mixamorig:Spine2',
 'clavicle_l':'mixamorig:LeftShoulder','upperarm_l':'mixamorig:LeftArm','lowerarm_l':'mixamorig:LeftForeArm','hand_l':'mixamorig:LeftHand',
 'clavicle_r':'mixamorig:RightShoulder','upperarm_r':'mixamorig:RightArm','lowerarm_r':'mixamorig:RightForeArm','hand_r':'mixamorig:RightHand',
}
for side,Side in [('l','Left'),('r','Right')]:
    for digit,Cap in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('pinky','Pinky')]:
        for j in (1,2,3):
            TARGET_ARM_MAP[f'{digit}_{j:02d}_{side}']=f'mixamorig:{Side}Hand{Cap}{j}'
            TARGET_ARM_MAP[f'{digit}_{j}_{side}']=f'mixamorig:{Side}Hand{Cap}{j}'


def source_to_target_map(psa:Psa,doc):
    target_names={n.get('name',''):i for i,n in enumerate(doc['nodes'])}
    out={}
    for si,b in enumerate(psa.bones):
        key=nrm(b.name)
        tn=TARGET_ARM_MAP.get(key)
        if tn in target_names: out[si]=target_names[tn]
    return out


def converted_source_rot(M):
    r=rot_only(M); return C_UE_TO_GLTF@r@C_UE_TO_GLTF.T

def continuous(qs):
    out=[]
    for q in qs:
        q=qnorm(q)
        if out and np.dot(out[-1],q)<0:q=-q
        out.append(q)
    return np.asarray(out,np.float32)


def add_arm_psa(doc,blob,psa:Psa,info:AnimInfo,clip_name:str):
    mapping=source_to_target_map(psa,doc)
    if len(mapping)<10:
        print(f'WARN {clip_name}: only {len(mapping)} arm bones mapped: {[psa.bones[i].name for i in mapping]}')
    parents,Lt,Gt=target_rest(doc); Rs_rest=source_rest_globals(psa.bones)
    tgt_rest_r=[rot_only(g) for g in Gt]
    times=np.arange(info.frames,dtype=np.float32)/(info.rate if info.rate>1e-6 else 30.0)
    rot_keys={ti:[] for ti in mapping.values()}; hips_t=[]; hips_ti=None
    # source pelvis index if mapped to Hips
    for si,ti in mapping.items():
        if doc['nodes'][ti].get('name')=='mixamorig:Hips': hips_ti=(si,ti)
    # depth order for target global propagation
    depth={}
    def dep(i):
        if i in depth:return depth[i]
        depth[i]=0 if i not in parents else dep(parents[i])+1;return depth[i]
    order=sorted(range(len(doc['nodes'])),key=dep)
    invmap={ti:si for si,ti in mapping.items()}
    for f in range(info.frames):
        Sa=source_anim_globals(psa,info,f)
        desired={}
        for si,ti in mapping.items():
            rr=converted_source_rot(Rs_rest[si]); ra=converted_source_rot(Sa[si])
            delta=ra@rr.T; desired[ti]=delta@tgt_rest_r[ti]
        anim_global={}
        local_out={}
        for ti in order:
            pr=parents.get(ti)
            parentR=np.eye(3) if pr is None else anim_global[pr]
            if ti in desired:
                gr=desired[ti]; lr=parentR.T@gr; local_out[ti]=lr; anim_global[ti]=gr
            else:
                lr=rot_only(Lt[ti]); anim_global[ti]=parentR@lr
        for ti in rot_keys: rot_keys[ti].append(matq(local_out[ti]))
        if hips_ti:
            si,ti=hips_ti
            ds=C_UE_TO_GLTF@(Sa[si][:3,3]-Rs_rest[si][:3,3])*CM_TO_M
            hips_t.append(np.asarray(doc['nodes'][ti].get('translation',[0,0,0]),float)+ds)
    tacc=append_accessor(doc,blob,times.reshape(-1,1),'SCALAR',True); sam=[];ch=[]
    for ti,qs in rot_keys.items():
        qacc=append_accessor(doc,blob,continuous(qs),'VEC4'); sidx=len(sam);sam.append({'input':tacc,'output':qacc,'interpolation':'LINEAR'});ch.append({'sampler':sidx,'target':{'node':ti,'path':'rotation'}})
    if hips_ti and hips_t:
        ti=hips_ti[1]; a=append_accessor(doc,blob,np.asarray(hips_t,np.float32),'VEC3'); sidx=len(sam);sam.append({'input':tacc,'output':a,'interpolation':'LINEAR'});ch.append({'sampler':sidx,'target':{'node':ti,'path':'translation'}})
    if ch: doc.setdefault('animations',[]).append({'name':clip_name,'samplers':sam,'channels':ch,'extras':{'source':'UE5.5 Marketplace PSA','retargeted':True}})
    return len(ch)


def pick_weapon_base(psa:Psa,info:AnimInfo,rest):
    # Prefer a weapon/root-ish bone with actual motion; exclude obvious moving parts.
    names=[nrm(b.name) for b in psa.bones]; candidates=[]
    for i,n in enumerate(names[:info.total_bones]):
        if any(x in n for x in ('mag','bolt','trigger','sight','muzzle','shell','casing','bullet')):continue
        bonus=8 if any(x in n for x in ('weapon','gun','rifle','m4a1','aks74u','ak74u','ak')) else 5 if n=='root' or n.endswith('_root') else 0
        # sample beginning/middle/end global delta
        score=0.0
        for f in sorted(set([0,max(0,info.frames//2),max(0,info.frames-1)])):
            g=source_anim_globals(psa,info,f)[i]
            rr=rot_only(rest[i]); ra=rot_only(g); ang=math.acos(float(np.clip((np.trace(ra@rr.T)-1)/2,-1,1)))
            score=max(score,ang+np.linalg.norm(g[:3,3]-rest[i][:3,3])*0.01)
        candidates.append((bonus+score,i,n))
    return max(candidates,default=(0,0,'root'))[1]


def add_weapon_psa(doc,blob,psa:Psa,info:AnimInfo,clip_name:str,animroot_idx:int,mag_target_idx:int|None):
    rest=source_rest_globals(psa.bones); base=pick_weapon_base(psa,info,rest)
    mag=None
    for i,b in enumerate(psa.bones[:info.total_bones]):
        nn=nrm(b.name)
        if 'magazine' in nn or re.search(r'(^|_)mag($|_)',nn): mag=i;break
    times=np.arange(info.frames,dtype=np.float32)/(info.rate if info.rate>1e-6 else 30.0)
    root_q=[];root_t=[];mag_q=[];mag_t=[]
    Rbr=converted_source_rot(rest[base]); pbr=C_UE_TO_GLTF@rest[base][:3,3]
    if mag is not None:
        rel_rest=np.linalg.inv(rest[base])@rest[mag]
        Rmr=rot_only(rel_rest); pmr=rel_rest[:3,3]
    for f in range(info.frames):
        A=source_anim_globals(psa,info,f); Rba=converted_source_rot(A[base]); pba=C_UE_TO_GLTF@A[base][:3,3]
        root_q.append(matq(Rba@Rbr.T)); root_t.append((pba-pbr)*CM_TO_M)
        if mag is not None and mag_target_idx is not None:
            rel=np.linalg.inv(A[base])@A[mag]; dr=rot_only(rel)@Rmr.T; dp=rel[:3,3]-pmr
            mag_q.append(matq(C_UE_TO_GLTF@dr@C_UE_TO_GLTF.T));mag_t.append((C_UE_TO_GLTF@dp)*CM_TO_M)
    tacc=append_accessor(doc,blob,times.reshape(-1,1),'SCALAR',True);sam=[];ch=[]
    for vals,path in [(continuous(root_q),'rotation'),(np.asarray(root_t,np.float32),'translation')]:
        a=append_accessor(doc,blob,vals,'VEC4' if path=='rotation' else 'VEC3');si=len(sam);sam.append({'input':tacc,'output':a,'interpolation':'LINEAR'});ch.append({'sampler':si,'target':{'node':animroot_idx,'path':path}})
    if mag_q and mag_target_idx is not None:
        for vals,path in [(continuous(mag_q),'rotation'),(np.asarray(mag_t,np.float32),'translation')]:
            a=append_accessor(doc,blob,vals,'VEC4' if path=='rotation' else 'VEC3');si=len(sam);sam.append({'input':tacc,'output':a,'interpolation':'LINEAR'});ch.append({'sampler':si,'target':{'node':mag_target_idx,'path':path}})
    doc.setdefault('animations',[]).append({'name':clip_name,'samplers':sam,'channels':ch,'extras':{'source':'UE5.5 Marketplace weapon PSA','baseBone':psa.bones[base].name,'magBone':psa.bones[mag].name if mag is not None else None}})
    print(f'  weapon {clip_name}: base={psa.bones[base].name} mag={psa.bones[mag].name if mag is not None else "-"}')


def unique_clip_name(info:AnimInfo,path:Path,existing:set[str]):
    name=info.name or path.stem
    if name in existing:name=path.stem
    if name in existing:
        n=2;base=name
        while f'{base}_{n}' in existing:n+=1
        name=f'{base}_{n}'
    existing.add(name);return name


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--exports',required=True);ap.add_argument('--site',required=True)
    a=ap.parse_args();exports=Path(a.exports);site=Path(a.site);site.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[1]
    arms_in=repo/'site/assets/fallback/player_ch15_fp_arms_reload.glb'
    wep_in=repo/'site/assets/fallback/ar15_split_reload.glb'
    psas=sorted(exports.rglob('*.psa'))
    if not psas:raise SystemExit('No PSA files found in exports')
    arms_psas=[];wep_psas=[]
    for p in psas:
        if 'WEP' in p.stem.upper() or 'WBP' in p.stem.upper():
            wep_psas.append(p)
        else:
            arms_psas.append(p)
    print(f'PSA files: arms={len(arms_psas)} weapon={len(wep_psas)}')

    # Arms: same visible supplied mesh, but strip our procedural clips and replace
    # them with the real authored UE5.5 sequences.
    adoc,ablob=read_glb(arms_in);adoc['animations']=[];arms_names=[];seen=set()
    for p in arms_psas:
        psa=parse_psa(p)
        for info in psa.infos:
            if info.frames<=0:continue
            name=unique_clip_name(info,p,seen); channels=add_arm_psa(adoc,ablob,psa,info,name)
            if channels:arms_names.append(name);print(f'  arms {name}: frames={info.frames} fps={info.rate:.3f} channels={channels}')
    arms_out=site/'aks74u_fp_arms.glb';write_glb(arms_out,adoc,ablob)

    # Weapon: insert an animation root BELOW AR15_Root so the viewer's user-set
    # transform remains untouched while the authored weapon motion plays.
    wdoc,wblob=read_glb(wep_in);wdoc['animations']=[]
    names={n.get('name',''):i for i,n in enumerate(wdoc['nodes'])}; root_idx=names.get('AR15_Root',0);mag_idx=names.get('AR15_Magazine')
    old_children=list(wdoc['nodes'][root_idx].get('children',[])); animroot=len(wdoc['nodes']);wdoc['nodes'].append({'name':'AR15_AnimRoot','children':old_children});wdoc['nodes'][root_idx]['children']=[animroot]
    weapon_names=[];seen=set()
    for p in wep_psas:
        psa=parse_psa(p)
        for info in psa.infos:
            if info.frames<=0:continue
            name=unique_clip_name(info,p,seen);add_weapon_psa(wdoc,wblob,psa,info,name,animroot,mag_idx);weapon_names.append(name)
    wep_out=site/'aks74u_weapon.glb';write_glb(wep_out,wdoc,wblob)

    manifest={'ready':bool(arms_names),'generatedBy':'CUE4Parse PSA + UE5->Mixamo retarget + supplied AR15 GLB',
              'arms':'assets/extracted/aks74u_fp_arms.glb','weapon':'assets/extracted/aks74u_weapon.glb',
              'armsAnimations':arms_names,'weaponAnimations':weapon_names,
              'note':'UE5.5 editor meshes have no CUE4Parse cooked LOD; real authored animations are retargeted onto the supplied browser GLBs.'}
    manifest_path=repo/'site/extracted-manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2))
    print('WROTE',arms_out,arms_out.stat().st_size,'bytes')
    print('WROTE',wep_out,wep_out.stat().st_size,'bytes')
    print('WROTE',manifest_path)
    print(f'RETARGET READY arms={len(arms_names)} weapon={len(weapon_names)}')

if __name__=='__main__':main()
