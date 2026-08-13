(() => {
const $=id=>document.getElementById(id),canvas=$('renderCanvas');
const engine=new BABYLON.Engine(canvas,true,{preserveDrawingBuffer:true,stencil:true});
const scene=new BABYLON.Scene(engine);scene.clearColor=new BABYLON.Color4(.025,.032,.043,1);
const camera=new BABYLON.ArcRotateCamera('cam',-Math.PI/2.15,Math.PI/2.2,2.25,new BABYLON.Vector3(0,1.45,0),scene);
camera.attachControl(canvas,true);camera.wheelPrecision=45;camera.panningSensibility=1200;camera.minZ=.001;
new BABYLON.HemisphericLight('hemi',new BABYLON.Vector3(.2,1,.3),scene).intensity=1.55;
const key=new BABYLON.DirectionalLight('key',new BABYLON.Vector3(-.3,-.5,.8),scene);key.intensity=.8;
const grid=BABYLON.MeshBuilder.CreateGround('grid',{width:8,height:8,subdivisions:32},scene);
const gm=new BABYLON.GridMaterial('gridMat',scene);gm.majorUnitFrequency=4;gm.minorUnitVisibility=.3;gm.gridRatio=.25;gm.opacity=.32;grid.material=gm;grid.position.y=.82;
let result=null,root=null,playing=false,scrubbing=false;
const defaults={p:[0,0,0],r:[0,0,0],s:1};
function log(s){$('log').textContent=(s+'\n'+$('log').textContent).slice(0,7000)}
function norm(s){return String(s).toLowerCase().replace(/[^a-z0-9]+/g,'_')}
function topRoot(r){return (r.meshes||[]).find(m=>m.name==='__root__')||(r.transformNodes||[]).find(n=>!n.parent)||(r.meshes||[]).find(m=>!m.parent)||r.meshes?.[0]}
function buildTransform(){const fields=[['px','Pos X'],['py','Pos Y'],['pz','Pos Z'],['rx','Rot X°'],['ry','Rot Y°'],['rz','Rot Z°'],['sc','Scale']];$('transformGrid').innerHTML=fields.map(([id,l])=>`<label>${l}<input id="${id}" type="number" step="${id==='sc'?'.025':id[0]==='r'?'1':'.01'}"></label>`).join('');fields.forEach(([id])=>$(id).addEventListener('input',()=>{if(!root)return;const n=parseFloat($(id).value);if(!Number.isFinite(n))return;if(id==='px')root.position.x=n;if(id==='py')root.position.y=n;if(id==='pz')root.position.z=n;if(id==='rx')root.rotation.x=BABYLON.Tools.ToRadians(n);if(id==='ry')root.rotation.y=BABYLON.Tools.ToRadians(n);if(id==='rz')root.rotation.z=BABYLON.Tools.ToRadians(n);if(id==='sc')root.scaling.setAll(n)}))}
function syncTransform(){if(!root)return;const v={px:root.position.x,py:root.position.y,pz:root.position.z,rx:BABYLON.Tools.ToDegrees(root.rotation.x),ry:BABYLON.Tools.ToDegrees(root.rotation.y),rz:BABYLON.Tools.ToDegrees(root.rotation.z),sc:root.scaling.x};for(const [k,x] of Object.entries(v))$(k).value=Number(x).toFixed(k==='sc'?3:2)}
function resetRig(){if(!root)return;root.position.set(...defaults.p);root.rotationQuaternion=null;root.rotation.set(...defaults.r.map(BABYLON.Tools.ToRadians));root.scaling.setAll(defaults.s);syncTransform()}
buildTransform();
function fillAnimations(){const sel=$('anim');sel.innerHTML='';(result.animationGroups||[]).forEach((g,i)=>{const o=document.createElement('option');o.value=i;o.textContent=g.name;sel.appendChild(o)})}
function selected(){const i=parseInt($('anim').value,10);return Number.isFinite(i)?result?.animationGroups?.[i]:null}
function stopAll(){for(const g of result?.animationGroups||[])try{g.stop()}catch{};playing=false;$('timeline').value=0;$('timeLabel').textContent='0.00s'}
function play(){const g=selected();if(!g)return;for(const x of result.animationGroups)if(x!==g)try{x.stop()}catch{};const loop=$('loop').checked,speed=parseFloat($('speed').value)||1;g.start(loop,speed,g.from,g.to,false);playing=true}
function pause(){const g=selected();if(g)g.pause();playing=false}
function duration(g){let d=0;for(const ta of g?.targetedAnimations||[]){const a=ta.animation,k=a?.getKeys?.()||[];if(k.length>1)d=Math.max(d,(k.at(-1).frame-k[0].frame)/(a.framePerSecond||60))}return d}
function best(type){const groups=result?.animationGroups||[];let top=null;for(let i=0;i<groups.length;i++){const n=norm(groups[i].name);let s=0;
 if(type==='reload'){if(n.includes('reload'))s+=50;if(n.includes('empty'))s-=45;if(n.includes('aimed'))s-=12}
 if(type==='reload_full'){if(n.includes('reload'))s+=20;if(n.includes('empty'))s+=55;if(n.includes('aimed'))s-=12}
 if(type==='fire'){if(n.includes('fire'))s+=45;if(n.includes('aimed'))s-=30}
 if(type==='fire_aimed'){if(n.includes('fire'))s+=25;if(n.includes('aimed'))s+=45}
 if(type==='equip'&&n.includes('equip'))s+=50;if(type==='holster'&&n.includes('holster'))s+=50;
 if(type==='idle'){if(n.includes('idle'))s+=40;if(n.includes('loop'))s+=10;if(n.includes('aim'))s-=25}
 if(type==='aim'){if(n.includes('aim'))s+=35;if(n.includes('loop'))s+=10;if(n.includes('fire'))s-=30}
 if(type==='walk'){if(n.includes('walk'))s+=45;if(n.includes('aimed'))s-=12}
 if(type==='run'){if(n.includes('run'))s+=45;if(n.includes('loop'))s+=10}
 if(!top||s>top.s)top={i,s};}
 return top&&top.s>0?top.i:null}
function preset(type){const i=best(type);if(i==null){log('No matching '+type+' clip');return}$('anim').value=String(i);$('loop').checked=['idle','aim','walk','run'].includes(type);play()}
function fit(){const meshes=(result?.meshes||[]).filter(m=>m.getTotalVertices?.()>0&&m.name!=='__root__');if(!meshes.length)return;let mn=new BABYLON.Vector3(Infinity,Infinity,Infinity),mx=new BABYLON.Vector3(-Infinity,-Infinity,-Infinity);for(const m of meshes){const b=m.getHierarchyBoundingVectors(true);mn=BABYLON.Vector3.Minimize(mn,b.min);mx=BABYLON.Vector3.Maximize(mx,b.max)}const c=mn.add(mx).scale(.5),size=mx.subtract(mn).length();camera.setTarget(c);camera.radius=Math.max(.75,size*1.15)}
async function load(){try{$('status').textContent='Loading actual AKS-74U pack…';result=await BABYLON.SceneLoader.ImportMeshAsync('','assets/','aks74u_ue_actual_arms_authored_magfix.glb',scene);root=topRoot(result);fillAnimations();resetRig();$('status').textContent='ACTUAL AKS-74U + AUTHORED UE ANIMS (MAG FIX)';log(`Loaded ${result.meshes.length} meshes, ${(result.skeletons||[]).length} skins/skeletons, ${(result.animationGroups||[]).length} authored animation groups.`);preset('reload');setTimeout(fit,120)}catch(e){$('status').textContent='LOAD ERROR';log(e.stack||e.message||String(e));console.error(e)}}
$('play').onclick=play;$('pause').onclick=pause;$('stop').onclick=stopAll;$('fit').onclick=fit;$('front').onclick=()=>{camera.alpha=-Math.PI/2;camera.beta=Math.PI/2;fit()};$('side').onclick=()=>{camera.alpha=0;camera.beta=Math.PI/2;fit()};$('grid').onchange=e=>grid.setEnabled(e.target.checked);$('wire').onchange=e=>scene.materials.forEach(m=>{if(m!==gm)m.wireframe=e.target.checked});$('resetRig').onclick=resetRig;
document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>preset(b.dataset.preset));$('anim').onchange=()=>{stopAll();$('timeline').value=0};
$('timeline').addEventListener('pointerdown',()=>scrubbing=true);$('timeline').addEventListener('pointerup',()=>scrubbing=false);$('timeline').addEventListener('input',()=>{const g=selected();if(!g)return;const f=+$('timeline').value/1000;try{g.goToFrame(g.from+(g.to-g.from)*f)}catch{};$('timeLabel').textContent=(duration(g)*f).toFixed(2)+'s'});
scene.onBeforeRenderObservable.add(()=>{if(!playing||scrubbing)return;const g=selected(),a=g?.animatables?.[0];if(!g||!a)return;const f=(a.masterFrame-g.from)/Math.max(1e-6,g.to-g.from);$('timeline').value=Math.max(0,Math.min(1000,f*1000));$('timeLabel').textContent=(Math.max(0,f)*duration(g)).toFixed(2)+'s'});
window.addEventListener('keydown',e=>{if(e.target.matches('input,select'))return;if(e.code==='KeyR'){preset(e.shiftKey?'reload_full':'reload');e.preventDefault()}else if(e.code==='KeyF')preset('fire');else if(e.code==='KeyE')preset('equip');else if(e.code==='KeyH')preset('holster');else if(e.code==='Space'){playing?pause():play();e.preventDefault()}});
engine.runRenderLoop(()=>scene.render());window.addEventListener('resize',()=>engine.resize());load();
})();
