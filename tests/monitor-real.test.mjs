import test from "node:test";
import assert from "node:assert/strict";
import {validateMonitor,chartPoints} from "../src/monitor-real.mjs";
function sample(){
 return {format:"marshpulse-observed-water-v1",
 label:"UNVERIFIED SATELLITE PROXY",official_wetland_boundary:false,
 rows:Array.from({length:36},(_,i)=>[
  String(2023+Math.floor((i+9)/12))+"-"+String((i+9)%12+1).padStart(2,"0"),
  i%6===0?3:0, i%4===0?.65:1,i===0?null:0])};
}
test("accept chronological actual-source schema",()=>{
 const r=sample();assert.equal(validateMonitor(r),true);
 assert.equal(chartPoints(r.rows).points.length,36);
 assert.equal(chartPoints(r.rows).points[0][0],0);
});
test("fail closed if source becomes synthetic, classes invalid, or timestamps duplicate",()=>{
 const x=sample();x.label="SYNTHETIC";assert.equal(validateMonitor(x),false);
 const y=sample();y.rows[1][0]=y.rows[0][0];assert.equal(validateMonitor(y),false);
 const z=sample();z.rows[1][2]=1.2;assert.equal(validateMonitor(z),false);
 const w=sample();w.official_wetland_boundary=true;assert.equal(validateMonitor(w),false);
});
test("plot y decreases as observed water increases",()=>{
 const x=sample();const v=chartPoints(x.rows);
 assert.ok(v.points[0][1]<v.points[1][1]);
 assert.equal(v.ceiling,10);
});
