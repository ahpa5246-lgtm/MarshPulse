import test from "node:test";
import assert from "node:assert/strict";
import {demoData,parseCSV,connectivity,articulation,train,forecast,scenario,report,nextMonth,MODEL_VERSION} from "../src/engine.mjs";
const ds=demoData();
function csv(data, months=12, size=3){
  const lines=["date,row,col,water"];
  for(let t=0;t<months;t++)for(let r=0;r<size;r++)for(let c=0;c<size;c++)
    lines.push(data.dates[t]+","+r+","+c+","+(data.frames[t][(r+4)*data.width+c+6]>=0.5?1:0));
  return lines.join("\n");
}
test("synthetic demonstration is explicitly labelled and reproducible",()=>{
  assert.equal(ds.origin,"synthetic");
  assert.match(ds.description,/ليست رصدًا/);
  assert.equal(ds.frames.length,60);
  assert.equal(ds.frames[0].length,ds.width*ds.height);
  assert.deepEqual(ds.frames[0],demoData().frames[0]);
});
test("month handling handles year boundary",()=>{
  assert.equal(nextMonth("2024-12"),"2025-01");
});
test("CSV parses complete monthly grids and preserves unverified provenance",()=>{
  const parsed=parseCSV(csv(ds));
  assert.equal(parsed.origin,"imported_unverified");
  assert.equal(parsed.width,3);assert.equal(parsed.height,3);
  assert.equal(parsed.dates.length,12);
});
test("CSV handles quoted cells and BOM header",()=>{
  const valid=csv(ds).replace("date,row,col,water","\uFEFF\"date\",row,col,water");
  assert.equal(parseCSV(valid).dates.length,12);
});
test("CSV rejects missing months, incomplete data and duplicate cells",()=>{
  const valid=csv(ds,14);
  assert.throws(()=>parseCSV(valid.replace(/^2020-02.*\n/gm,"")),/Missing month/);
  assert.throws(()=>parseCSV(valid.split("\n").filter(line=>!line.startsWith("2020-03,1,1,")).join("\n")),/Missing cells/);
  assert.throws(()=>parseCSV(valid+"\n"+valid.split("\n")[1]),/Duplicate/);
});
test("CSV rejects malicious / malformed grid cells",()=>{
  const valid=csv(ds);
  assert.throws(()=>parseCSV(valid.replace(",0,0,",",0,-1,")),/Invalid row/);
  assert.throws(()=>parseCSV(valid.replace(/,0,0,[0-9.]+/,",0,0,2")),/Water must/);
  assert.throws(()=>parseCSV("row,col,water\n0,0,1"),/Missing CSV column/);
});
test("connectivity recognizes separate regions",()=>{
  const mask=[1,1,0,0,0,0,1,1,0];
  const r=connectivity(mask,3,3);
  assert.equal(r.components,2);
  assert.equal(r.largest,2);
  assert.equal(r.wet,4);
  assert.equal(r.share,0.5);
});
test("articulation identifies a one-cell bridge",()=>{
  const mask=[0,1,0,1,1,1,0,1,0];
  const bridges=articulation(mask,3,3);
  assert.ok(bridges.has(4));
  assert.equal(bridges.size,1);
  assert.equal(articulation([1,1,1,1],2,2).size,0);
});
test("chronological holdout training produces finite scientific metrics",()=>{
  const model=train(ds,{epochs:35});
  assert.ok(model.holdoutStart>model.trainingEnd);
  assert.ok(model.holdoutSamples>0);
  for(const m of [model.metrics,model.baseline]){
    for(const key of ["brier","f1","accuracy","precision","recall"])assert.ok(m[key]>=0&&m[key]<=1,key);
  }
  assert.equal(model.weights.length,6);
});
test("forecast is future-dated and probabilistic",()=>{
  const model=train(ds,{epochs:20}),f=forecast(ds,model);
  assert.equal(f.date,nextMonth(ds.dates.at(-1)));
  assert.equal(f.probabilities.length,ds.width*ds.height);
  assert.ok(f.probabilities.every(p=>p>=0&&p<=1));
});
test("optimizer never converts predicted water into dry pixels",()=>{
  const model=train(ds,{epochs:40});
  for(const budget of [0,3,8,12]){
    const sc=scenario(ds,model,{stress:50,budget});
    assert.ok(sc.selected.length<=budget);
    assert.ok(sc.after.wet>=sc.before.wet);
    assert.ok(sc.after.largest>=sc.before.largest);
    assert.ok(sc.selected.every(x=>!sc.baseline[x.index]&&sc.protected[x.index]));
    if(budget===0)assert.equal(sc.selected.length,0);
  }
});
test("report distinguishes modeled evidence from real wetland interventions",()=>{
  const model=train(ds,{epochs:15}),sc=scenario(ds,model,{stress:65,budget:5});
  const result=report(ds,model,sc);
  assert.equal(result.version,MODEL_VERSION);
  assert.equal(result.dataset.verified,false);
  assert.equal(result.dataset.origin,"synthetic");
  assert.match(result.disclaimer,/not a physically calibrated/);
  assert.ok(result.scenario.assumptions.length>=2);
});

test("policy baselines are deterministic, equal-credit and included in export",()=>{
  const model=train(ds,{epochs:30});
  const one=scenario(ds,model,{stress:65,budget:7});
  const two=scenario(ds,model,{stress:65,budget:7});
  assert.deepEqual(one.policyComparison,two.policyComparison);
  assert.equal(one.policyComparison.creditsSpent,one.selected.length);
  assert.equal(one.policyComparison.optimizedLargest,one.after.largest);
  assert.ok(Number.isFinite(one.policyComparison.randomMeanLargest));
  const evidence=report(ds,model,one);
  assert.deepEqual(evidence.scenario.policyComparison,one.policyComparison);
});
