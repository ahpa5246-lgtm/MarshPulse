import {extractFeatures,nextMonth} from "./engine.mjs";
export const MARSHNET_FORMAT="marshnet-v1";
const H=12,D=5;
const sig=x=>1/(1+Math.exp(-Math.max(-25,Math.min(25,x))));
function rng(seed=42){let s=seed>>>0;return ()=>{s=(Math.imul(1664525,s)+1013904223)>>>0;return s/4294967296;};}
const zero=n=>Array(n).fill(0);
function init(seed){const random=rng(seed),scale=Math.sqrt(2/(D+H));return {W1:Array.from({length:H*D},()=>((random()*2-1)*scale)),b1:zero(H),W2:Array.from({length:H},()=>((random()*2-1)*Math.sqrt(2/(H+1)))),b2:[0]};}
function flattenFeatures(ds,t,i){return extractFeatures(ds,t,i).slice(1);}
function normalizer(ds,split){
  const sum=zero(D),sumSq=zero(D),cells=ds.width*ds.height;let n=0;
  for(let t=1;t<split-1;t++)for(let i=0;i<cells;i++){const a=flattenFeatures(ds,t,i);for(let k=0;k<D;k++){sum[k]+=a[k];sumSq[k]+=a[k]*a[k];}n++;}
  const mean=sum.map(v=>v/n),std=sumSq.map((v,k)=>Math.max(0.01,Math.sqrt(Math.max(0,v/n-mean[k]*mean[k]))));
  return {mean,std};
}
function pack(ds,t,i,norm){const raw=flattenFeatures(ds,t,i);return raw.map((v,k)=>(v-norm.mean[k])/norm.std[k]);}
function forward(x,w){
  const h=zero(H);for(let j=0;j<H;j++){let z=w.b1[j];for(let k=0;k<D;k++)z+=x[k]*w.W1[j*D+k];h[j]=Math.tanh(z);}
  let z=w.b2[0];for(let j=0;j<H;j++)z+=w.W2[j]*h[j];return {h,p:sig(z)};
}
export function predictMarshNet(model,ds,t,i){
  return forward(pack(ds,t,i,model.normalization),model.weights).p;
}
function metrics(points){
  let brier=0,tp=0,fp=0,fn=0,correct=0;
  for(const {p,y} of points){brier+=(p-y)**2;const label=p>=.5?1:0;tp+=label===1&&y===1?1:0;fp+=label===1&&y===0?1:0;fn+=label===0&&y===1?1:0;correct+=label===y?1:0;}
  const n=points.length;return {brier:n?brier/n:null,f1:2*tp+fp+fn?2*tp/(2*tp+fp+fn):1,accuracy:n?correct/n:0,precision:tp+fp?tp/(tp+fp):0,recall:tp+fn?tp/(tp+fn):0,samples:n};
}
function gather(ds,start,end,norm,cap,seed){
  const cells=ds.width*ds.height,total=(end-start)*cells;
  const random=rng(seed),indices=[];
  if(total<=cap){for(let index=0;index<total;index++)indices.push(index);}
  else {
    // Deterministic sample, avoiding full allocation of a large array.
    for(let index=0;index<total;index++){
      if(index<cap)indices.push(index);
      else {const j=Math.floor(random()*(index+1));if(j<cap)indices[j]=index;}
    }
    indices.sort((a,b)=>a-b);
  }
  return indices.map(index=>{
    const t=start+Math.floor(index/cells),i=index%cells;
    return {x:pack(ds,t,i,norm),y:ds.frames[t+1][i]>=.5?1:0,baseline:ds.frames[t][i]>=.5?1:0};
  });
}
function evaluate(data,w){return metrics(data.map(row=>({p:forward(row.x,w).p,y:row.y})));}
function update(w,grads,m,v,step,lr){
  const beta1=.9,beta2=.999,eps=1e-8;
  for(const name of ["W1","b1","W2","b2"])for(let k=0;k<w[name].length;k++){
    const g=grads[name][k];m[name][k]=beta1*m[name][k]+(1-beta1)*g;v[name][k]=beta2*v[name][k]+(1-beta2)*g*g;
    const mh=m[name][k]/(1-beta1**step),vh=v[name][k]/(1-beta2**step);
    w[name][k]-=lr*mh/(Math.sqrt(vh)+eps);
  }
}
export async function fitMarshNet(ds,{epochs=32,seed=42,learningRate=.012,reportProgress=()=>{}}={}){
  if(!Number.isInteger(epochs)||epochs<1||epochs>150)throw Error("epochs must be 1–150");
  if(ds.dates.length<12||ds.frames.length!==ds.dates.length)throw Error("At least 12 complete months required");
  const count=ds.dates.length,cells=ds.width*ds.height,split=Math.max(8,Math.floor(count*.75));
  const validationStart=Math.max(4,Math.floor((split-1)*.82));
  const norm=normalizer(ds,validationStart+1);
  const training=gather(ds,1,validationStart,norm,14000,seed);
  const validation=gather(ds,validationStart,split-1,norm,3500,seed+1);
  const holdout=gather(ds,split-1,count-1,norm,7500,seed+2);
  if(!training.length||!validation.length||!holdout.length)throw Error("Dataset cannot form train/validation/holdout splits");
  const w=init(seed),m=Object.fromEntries(Object.entries(w).map(([k,a])=>[k,zero(a.length)])),v=Object.fromEntries(Object.entries(w).map(([k,a])=>[k,zero(a.length)]));
  let step=0,bestVal=Infinity,bestW=structuredClone(w),bestEpoch=0,patience=0;
  const history=[],random=rng(seed+19);
  for(let epoch=1;epoch<=epochs;epoch++){
    // Seeded Fisher-Yates shuffle of the training-only records.
    for(let i=training.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[training[i],training[j]]=[training[j],training[i]];}
    const batch=192;let loss=0;
    for(let off=0;off<training.length;off+=batch){
      const group=training.slice(off,off+batch);
      const grads=Object.fromEntries(Object.entries(w).map(([k,a])=>[k,zero(a.length)]));
      for(const row of group){
        const {p,h}=forward(row.x,w),dz=p-row.y;
        loss+=-row.y*Math.log(Math.max(1e-8,p))-(1-row.y)*Math.log(Math.max(1e-8,1-p));
        grads.b2[0]+=dz;
        for(let j=0;j<H;j++){
          grads.W2[j]+=dz*h[j];
          const dh=dz*w.W2[j]*(1-h[j]*h[j]);grads.b1[j]+=dh;
          for(let k=0;k<D;k++)grads.W1[j*D+k]+=dh*row.x[k];
        }
      }
      for(const a of Object.values(grads))for(let k=0;k<a.length;k++)a[k]/=group.length;
      step++;update(w,grads,m,v,step,learningRate);
    }
    const val=evaluate(validation,w);
    const record={epoch,trainLoss:loss/training.length,validationBrier:val.brier};history.push(record);
    if(val.brier<bestVal-0.00005){bestVal=val.brier;bestW=structuredClone(w);bestEpoch=epoch;patience=0;}else patience++;
    reportProgress(record);
    // Yield so the browser remains responsive to user interaction.
    if(epoch%3===0)await new Promise(resolve=>setTimeout(resolve,0));
    if(patience>=10)break;
  }
  const scores=evaluate(holdout,bestW);
  const baseline=metrics(holdout.map(r=>({p:r.baseline,y:r.y})));
  return {
    format:MARSHNET_FORMAT,
    architecture:{kind:"MLP",inputs:["water_t","water_tminus1","neighbor_mean_t","sin_month","cos_month"],input:D,hidden:H,output:1,activation:"tanh/sigmoid"},
    weights:bestW,normalization:norm,
    training:{seed,requestedEpochs:epochs,completedEpochs:history.length,bestEpoch,learningRate,batchSize:192,trainSamples:training.length,validationSamples:validation.length,holdoutSamples:holdout.length,trainingEnd:ds.dates[validationStart],validationEnd:ds.dates[split-1],holdoutStart:ds.dates[split],holdoutEnd:ds.dates.at(-1),split:"chronological-with-internal-validation",history},
    evaluation:{model:scores,persistence:baseline},
    provenance:{datasetName:ds.name,origin:ds.origin,sourceVerified:false,firstMonth:ds.dates[0],lastMonth:ds.dates.at(-1),grid:[ds.width,ds.height],threshold:ds.threshold??.5},
    disclaimer:"Trained network parameters do not imply independently verified Iraqi marsh forecasting, even if synthetic holdout score is high."
  };
}
export function validateMarshNet(model){
  if(!model||model.format!==MARSHNET_FORMAT)throw Error("Unsupported model format");
  if(model.architecture?.input!==D||model.architecture?.hidden!==H||model.architecture?.output!==1)throw Error("Unsupported architecture");
  for(const [key,length] of [["W1",H*D],["b1",H],["W2",H],["b2",1]])if(!Array.isArray(model.weights?.[key])||model.weights[key].length!==length||model.weights[key].some(x=>!Number.isFinite(x)))throw Error("Malformed model weights: "+key);
  for(const key of ["mean","std"])if(!Array.isArray(model.normalization?.[key])||model.normalization[key].length!==D||model.normalization[key].some(x=>!Number.isFinite(x)||(key==="std"&&x<=0)))throw Error("Malformed normalization");
  return true;
}
export function forecastMarshNet(model,ds){
  validateMarshNet(model);
  const t=ds.dates.length-1;
  return {date:nextMonth(ds.dates[t]),probabilities:ds.frames[t].map((_,i)=>predictMarshNet(model,ds,t,i))};
}
