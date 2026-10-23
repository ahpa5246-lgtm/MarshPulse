// MarshPulse scientific analysis core. No external runtime dependencies.
// Synthetic demo is explicitly labelled; imported data is never presented as validated.
export const MODEL_VERSION = "0.2.0";
const clamp = (x, a=0, b=1) => Math.max(a,Math.min(b,x));
const sigmoid = x => 1/(1+Math.exp(-clamp(x,-30,30)));
const water = v => v >= 0.5;
export function nextMonth(s) {
  const d=new Date(s.slice(0,7)+"-01T00:00:00Z");
  if(Number.isNaN(d.getTime())) throw Error("Invalid month "+s);
  d.setUTCMonth(d.getUTCMonth()+1);
  return d.toISOString().slice(0,7);
}
function rng(seed) {let s=seed>>>0;return ()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296;};}
export function demoData() {
  const width=32,height=20,n=60,start="2020-01",dates=[],frames=[],r=rng(20261023);
  for(let t=0;t<n;t++){
    const date=t===0?start:nextMonth(dates[t-1]);dates.push(date);
    const month=t%12, seasonal=Math.sin(2*Math.PI*(month+1)/12);
    const scarcity=0.0029*t + (t>=38?0.035:0);
    const frame=[];
    for(let y=0;y<height;y++)for(let x=0;x<width;x++){
      const channel=0.61*Math.exp(-Math.pow((y-(9.5+3*Math.sin(x/5)))/1.7,2));
      const north=0.82*Math.exp(-Math.pow((x-10)/7,2)-Math.pow((y-6)/4.2,2));
      const south=0.85*Math.exp(-Math.pow((x-22)/7,2)-Math.pow((y-13)/4.8,2));
      const season=0.085*seasonal+0.04*Math.sin(t/8);
      const terrain=0.048*Math.sin(x*1.8+y*0.7)+0.03*Math.cos(y*1.23-x*0.71);
      const noise=(r()-0.5)*0.035;
      frame.push(clamp((Math.max(channel,north,south)+season+terrain+noise-scarcity-0.26)*2.4));
    }
    frames.push(frame);
  }
  return {name:"بيانات توضيحية مولّدة رياضيًا",origin:"synthetic",width,height,dates,frames,description:"محاكاة تركيبية وليست رصدًا لأهوار العراق",threshold:0.5};
}
function csvRows(text) {
  const lines=[];let row=[],field="",quotes=false;
  const input=String(text).replace(/^\uFEFF/,"");
  for(let i=0;i<input.length;i++) {
    const ch=input[i];
    if(ch==='"'){if(quotes&&input[i+1]==='"'){field+='"';i++;}else quotes=!quotes;}
    else if(ch===","&&!quotes){row.push(field);field="";}
    else if((ch==="\n"||ch==="\r")&&!quotes){
      if(ch==="\r"&&input[i+1]==="\n")i++;
      row.push(field);if(row.some(v=>v.trim()!==""))lines.push(row);
      row=[];field="";
    } else field+=ch;
  }
  if(quotes)throw Error("Malformed CSV: unclosed quote");
  row.push(field);if(row.some(v=>v.trim()!==""))lines.push(row);
  return lines;
}
export function parseCSV(text) {
  const rows=csvRows(text);
  if(rows.length<2)throw Error("CSV is empty");
  const headers=rows.shift().map(v=>v.trim().toLowerCase());
  for(const req of ["date","row","col","water"]) if(!headers.includes(req))throw Error("Missing CSV column: "+req);
  const idx=Object.fromEntries(headers.map((k,i)=>[k,i]));
  const observations=new Map();let maxRow=-1,maxCol=-1;
  for(const fields of rows){
    const date=String(fields[idx.date]??"").trim().slice(0,7);
    if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(date))throw Error("Expected ISO month YYYY-MM");
    if(String(fields[idx.row]??"").trim()===""||String(fields[idx.col]??"").trim()==="")throw Error("Missing row/col");
    const rr=Number(fields[idx.row]),cc=Number(fields[idx.col]),v=Number(fields[idx.water]);
    if(!Number.isInteger(rr)||!Number.isInteger(cc)||rr<0||cc<0||rr>99||cc>99)throw Error("Invalid row/col");
    if(String(fields[idx.water]??"").trim()===""||!Number.isFinite(v)||v<0||v>1)throw Error("Water must be in [0,1]");
    const key=date+"|"+rr+"|"+cc;
    if(observations.has(key))throw Error("Duplicate measurement "+key);
    observations.set(key,v);maxRow=Math.max(rr,maxRow);maxCol=Math.max(cc);
    if(observations.size>350000)throw Error("Dataset exceeds supported size");
  }
  const height=maxRow+1,width=maxCol+1,dates=[...new Set([...observations.keys()].map(k=>k.split("|")[0]))].sort();
  if(width<3||height<3||width*height>4900)throw Error("Grid must be at least 3x3 and at most 4900 cells");
  if(dates.length<12||dates.length>72)throw Error("12 to 72 monthly snapshots required");
  for(let i=1;i<dates.length;i++)if(nextMonth(dates[i-1])!==dates[i])throw Error("Missing month between "+dates[i-1]+" and "+dates[i]);
  if(observations.size!==width*height*dates.length)throw Error("Missing cells: every month requires a complete rectangular grid");
  const frames=dates.map(date=>Array.from({length:width*height},(_,i)=>observations.get(date+"|"+Math.floor(i/width)+"|"+(i%width))));
  if(frames.some(f=>f.some(v=>v===undefined)))throw Error("Incomplete raster grid");
  return {name:"ملف CSV مستورد",origin:"imported_unverified",width,height,dates,frames,description:"قياسات مقدمة من المستخدم؛ مصدرها ودقتها لم يتحققا تلقائيًا",threshold:0.5};
}
export function neighbors(i,w,h) {
  const x=i%w,y=Math.floor(i/w),a=[];
  if(x>0)a.push(i-1);if(x<w-1)a.push(i+1);
  if(y>0)a.push(i-w);if(y<h-1)a.push(i+w);
  return a;
}
export function connectivity(mask,w,h) {
  const n=w*h;
  if(mask.length!==n)throw Error("Grid dimensions mismatch");
  const visited=new Uint8Array(n),components=[],componentOf=new Int32Array(n).fill(-1);
  for(let i=0;i<n;i++)if(mask[i]&&!visited[i]){
    const q=[i];visited[i]=1;let ptr=0;
    while(ptr<q.length){
      const u=q[ptr++];componentOf[u]=components.length;
      for(const v of neighbors(u,w,h))if(mask[v]&&!visited[v]){visited[v]=1;q.push(v);}
    }
    components.push(q);
  }
  const wet=mask.reduce((a,b)=>a+(b?1:0),0);
  const largest=components.reduce((m,c)=>Math.max(m,c.length),0);
  return {wet,components:components.length,largest,share:wet?largest/wet:0,componentOf,componentSizes:components.map(c=>c.length)};
}
export function articulation(mask,w,h) {
  const n=w*h,disc=new Int32Array(n).fill(-1),low=new Int32Array(n),parent=new Int32Array(n).fill(-1),result=new Set();let clock=0;
  // Iterative DFS avoids stack overflow on user-supplied grids.
  for(let root=0;root<n;root++){
    if(!mask[root]||disc[root]>=0)continue;
    const stack=[{u:root,ns:neighbors(root,w,h),next:0,children:0}];
    disc[root]=low[root]=clock++;
    while(stack.length){
      const f=stack[stack.length-1];
      if(f.next<f.ns.length){
        const v=f.ns[f.next++];if(!mask[v])continue;
        if(disc[v]<0){parent[v]=f.u;f.children++;disc[v]=low[v]=clock++;stack.push({u:v,ns:neighbors(v,w,h),next:0,children:0});}
        else if(v!==parent[f.u])low[f.u]=Math.min(low[f.u],disc[v]);
      } else {
        stack.pop();
        if(parent[f.u]===-1){if(f.children>1)result.add(f.u);}
        else {const p=parent[f.u];low[p]=Math.min(low[p],low[f.u]);if(parent[p]!==-1&&low[f.u]>=disc[p])result.add(p);}
      }
    }
  }
  return result;
}
function features(ds,t,i){
  const w=ds.width,h=ds.height,v=ds.frames[t],prev=ds.frames[t-1];
  const neighborhood=neighbors(i,w,h);
  const m=Number(ds.dates[t].slice(5,7));
  return [1,v[i],prev[i],neighborhood.reduce((s,k)=>s+v[k],0)/neighborhood.length,Math.sin(2*Math.PI*m/12),Math.cos(2*Math.PI*m/12)];
}
function predict(weights,feature) {let z=0;for(let k=0;k<weights.length;k++)z+=weights[k]*feature[k];return sigmoid(z);}
function targets(ds,t){return ds.frames[t+1];}
export function train(ds,{epochs=72,learningRate=0.38,regularization=0.004}={}){
  const n=ds.dates.length;if(n<12)throw Error("Need at least 12 months");
  const split=Math.max(8,Math.floor(n*0.75)),rows=[];
  for(let t=1;t<split-1;t++)for(let i=0;i<ds.width*ds.height;i++)
    rows.push([features(ds,t,i),water(targets(ds,t)[i])?1:0]);
  if(!rows.length)throw Error("No training observations");
  const weights=[0,0,0,0,0,0];
  for(let epoch=0;epoch<epochs;epoch++){
    const grad=new Float64Array(weights.length);
    for(const [x,y] of rows){const error=predict(weights,x)-y;for(let k=0;k<grad.length;k++)grad[k]+=error*x[k];}
    for(let k=0;k<weights.length;k++)weights[k]-=learningRate*(grad[k]/rows.length+(k?regularization*weights[k]:0));
  }
  const points=[],step=Math.max(1,Math.ceil((n-split)*ds.width*ds.height/60000));
  for(let t=split-1;t<n-1;t++)for(let i=0;i<ds.width*ds.height;i+=step) {
    const truth=water(targets(ds,t)[i])?1:0;
    const prob=predict(weights,features(ds,t,i));
    const persistence=water(ds.frames[t][i])?1:0;
    points.push({truth,prob,persistence});
  }
  const evaluate=key=>{
    const vals=points.map(p=>key==="model"?p.prob:p.persistence);
    let brier=0,tp=0,fp=0,fn=0,correct=0;
    vals.forEach((p,i)=>{const y=points[i].truth,hat=p>=0.5?1:0;brier+=(p-y)**2;tp+=hat&&y?1:0;fp+=hat&&!y?1:0;fn+=!hat&&y?1:0;correct+=hat===y?1:0;});
    return {brier:brier/points.length,f1:2*tp+fp+fn?2*tp/(2*tp+fp+fn):1,accuracy:correct/points.length,precision:tp+fp?tp/(tp+fp):0,recall:tp+fn?tp/(tp+fn):0};
  };
  return {weights,trainingEnd:ds.dates[split-1],holdoutStart:ds.dates[split],holdoutEnd:ds.dates[n-1],trainSamples:rows.length,holdoutSamples:points.length,metrics:evaluate("model"),baseline:evaluate("baseline"),params:{epochs,learningRate,regularization,split:"chronological",baseline:"persistence"}};
}
export function forecast(ds,model){
  const t=ds.frames.length-1,probabilities=ds.frames[t].map((_,i)=>predict(model.weights,features(ds,t,i)));
  return {date:nextMonth(ds.dates[t]),probabilities};
}
export function scenario(ds,model,{stress=25,budget=6}={}){
  const recent=ds.frames.at(-1),current=recent.map(water),raw=forecast(ds,model);
  const probabilities=raw.probabilities.map(p=>clamp(p-stress*0.005));
  const baseMask=probabilities.map(water);
  const base=connectivity(baseMask,ds.width,ds.height);
  const corridor=articulation(current,ds.width,ds.height);
  const candidates=[];
  for(let i=0;i<current.length;i++)if(current[i]&&!baseMask[i]) {
    const near=neighbors(i,ds.width,ds.height).filter(j=>baseMask[j]).length;
    candidates.push({index:i,rank:(corridor.has(i)?6:0)+near*1.7+probabilities[i]});
  }
  candidates.sort((a,b)=>b.rank-a.rank);
  const pool=candidates.slice(0,Math.min(110,candidates.length));
  const selected=[],mask=baseMask.slice(),limit=Math.min(12,Math.max(0,Math.floor(budget)));
  function utility(c) {return 4*c.largest+0.35*c.wet-1.5*c.components;}
  for(let k=0;k<limit&&pool.length;k++){
    let best=-1,bestGain=-Infinity,bestMetrics=null;
    const currentMetrics=connectivity(mask,ds.width,ds.height);
    for(let j=0;j<pool.length;j++){
      mask[pool[j].index]=true;
      const m=connectivity(mask,ds.width,ds.height);
      mask[pool[j].index]=false;
      const gain=utility(m)-utility(currentMetrics);
      if(gain>bestGain+1e-9){best=j;bestGain=gain;bestMetrics=m;}
    }
    if(best<0||bestGain<=0)break;
    const chosen=pool.splice(best,1)[0];mask[chosen.index]=true;
    selected.push({row:Math.floor(chosen.index/ds.width),col:chosen.index%ds.width,index:chosen.index,wasCritical:corridor.has(chosen.index),marginalUtility:bestGain});
  }
  // Equal-credit decision baselines expose whether topology-aware selection adds value.
  const eligible=candidates.map(c=>c.index);
  const spent=selected.length;
  const trial=indices=>{
    const testMask=baseMask.slice();
    for(const i of indices.slice(0,spent))testMask[i]=true;
    return connectivity(testMask,ds.width,ds.height);
  };
  const mostAtRisk=trial(eligible.slice().sort((a,b)=>probabilities[a]-probabilities[b]));
  const random=rng(140277+Math.floor(stress)*31+Math.floor(budget)*7);
  const randomTrials=[];
  for(let run=0;run<20;run++){
    const sampled=eligible.slice();
    for(let k=sampled.length-1;k>0;k--){const j=Math.floor(random()*(k+1));[sampled[k],sampled[j]]=[sampled[j],sampled[k]];}
    randomTrials.push(trial(sampled).largest);
  }
  const after=connectivity(mask,ds.width,ds.height);
  const policyComparison={
    creditsSpent:spent,optimizedLargest:after.largest,
    riskFirstLargest:mostAtRisk.largest,
    randomMeanLargest:randomTrials.reduce((a,b)=>a+b,0)/randomTrials.length,
    randomTrials:randomTrials.length,
    warning:"Graph-metric comparisons on the same modeled scenario; not environmental field outcomes."
  };
  return {date:raw.date,stress,budget,probabilities,current,baseline:baseMask,protected:mask,corridor:[...corridor],before:base,after,selected,policyComparison,
    assumptions:["Scenario stress applies a hypothetical penalty to predicted water probability.","One credit preserves one forecast-dry cell in this graph only.","No hydrological flow, actual water volumes, biodiversity response or field outcomes are simulated."]};
}
export function report(ds,model,sc){
  return {project:"MarshPulse",version:MODEL_VERSION,generatedAt:new Date().toISOString(),dataset:{name:ds.name,origin:ds.origin,dates:[ds.dates[0],ds.dates.at(-1)],grid:[ds.width,ds.height],pixels:ds.width*ds.height,threshold:ds.threshold,verified:false},
    training:{protocol:"chronological held-out months; no shuffled splits",...model},scenario:{date:sc.date,stress:sc.stress,budget:sc.budget,baseline:{wet:sc.before.wet,largest:sc.before.largest,components:sc.before.components},after:{wet:sc.after.wet,largest:sc.after.largest,components:sc.after.components},interventions:sc.selected,policyComparison:sc.policyComparison,assumptions:sc.assumptions},disclaimer:"Graph-based hypothetical study only; not a physically calibrated allocation or reliable forecast of actual Iraqi marshes."};
}
