import { describe,it,expect } from 'vitest'
import { writeFileSync,readFileSync,mkdirSync } from 'node:fs'
import { Eyes,moods } from '../src/eyes/engine'
import { blinkScale,liveliness } from '../src/eyes/reference-face'
import { LeaseGuard } from '../src/lease'
import { validate,SPEC } from '../../../contracts/protocol'
describe('eyes independent clock',()=>{
 it('deterministic finite frames, blink and interruption continuity',()=>{
  const a=new Eyes(),b=new Eyes(),frames=[]
  for(let i=0;i<300;i++){
   const t=i*.071
   if(i%9===0){const before=a.sample(t,.2);a.setState(moods[(i/9)%moods.length|0],t,.2);expect(a.sample(t,.2)).toEqual(before);b.setState(moods[(i/9)%moods.length|0],t,.2)}
   const frame=a.sample(t,.2);expect(frame).toEqual(b.sample(t,.2));for(const e of frame)for(const n of Object.values(e))expect(Number.isFinite(n)).toBe(true)
   frames.push({t,state:a.state,change:i%9===0,rms:.2,frame})
  }
  mkdirSync('reports/v1/tests',{recursive:true});writeFileSync('reports/v1/tests/eyes_ts_frames.json',JSON.stringify(frames))
  expect(()=>a.sample(NaN)).toThrow();expect(()=>a.setState('bad' as never,1)).toThrow()
  const lids=Array.from({length:2000},(_,i)=>blinkScale(liveliness(i*.01,{wander:.35,blink:true,float:false}).lid));expect(Math.min(...lids)).toBeLessThan(.1);expect(Math.max(...lids)).toBeGreaterThan(.9)
 })
})
it('foreground pointer/blur/hidden/disconnect release prevents replay',()=>{
 let stops=0;const guard=new LeaseGuard(()=>stops++);expect(guard.heartbeat(true,true,true)).toBe(false);guard.claim();expect(guard.heartbeat(true,true,true)).toBe(true);guard.release();expect(guard.active).toBe(false)
 for(const args of [[false,true,true],[true,false,true],[true,true,false]]){guard.claim();expect(guard.heartbeat(...args as [boolean,boolean,boolean])).toBe(false)}
 expect(stops).toBe(4);expect(guard.heartbeat(true,true,true)).toBe(false)
})
it('shared cross-language valid and invalid corpus',()=>{
 const cases=JSON.parse(readFileSync('contracts/test_vectors.json','utf8'))
 for(const c of cases){let accepted=true;try{validate(c.command)}catch{accepted=false}expect(accepted,c.name).toBe(c.valid)}
 for(const value of [NaN,Infinity,-Infinity]){const c=structuredClone(cases[0].command);c.params.v_m_s=value;expect(()=>validate(c)).toThrow()}
 expect(Object.keys(SPEC.commands).length).toBeGreaterThan(30)
})
it('MORI repeats the reference blink schedule beyond 15 minutes',()=>{const e=new Eyes();expect(Math.abs(e.sample(906.481)[0].d)).toBeLessThan(.1)})
