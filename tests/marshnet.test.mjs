import test from "node:test";
import assert from "node:assert/strict";
import {demoData,parseCSV,scenario,train} from "../src/engine.mjs";
import {fitMarshNet,validateMarshNet,predictMarshNet,forecastMarshNet} from "../src/marshnet.mjs";
const ds=demoData();
test("MarshNet trains reproducibly with a chronological holdout",async()=>{
  const first=await fitMarshNet(ds,{epochs:5,seed:17});
  const second=await fitMarshNet(ds,{epochs:5,seed:17});
  assert.ok(validateMarshNet(first));
  assert.deepEqual(first.weights,second.weights);
  assert.ok(first.training.holdoutStart>first.training.validationEnd);
  assert.ok(first.training.validationEnd>=first.training.trainingEnd);
  assert.equal(first.provenance.sourceVerified,false);
  assert.equal(first.provenance.origin,"synthetic");
  assert.ok(Number.isFinite(first.evaluation.model.brier));
  assert.ok(Number.isFinite(first.evaluation.persistence.brier));
  assert.ok(first.training.holdoutSamples>0);
});
test("MarshNet probabilities and scenario adaptor are bounded",async()=>{
 const model=await fitMarshNet(ds,{epochs:3,seed:5});
 const probs=forecastMarshNet(model,ds);
 assert.equal(probs.probabilities.length,ds.width*ds.height);
 assert.ok(probs.probabilities.every(p=>p>=0&&p<=1));
 const baseline=train(ds,{epochs:5});
 const s=scenario(ds,baseline,{stress:35,budget:3,predictor:(d,t,i)=>predictMarshNet(model,d,t,i)});
 assert.ok(s.selected.length<=3);
 assert.ok(s.after.largest>=s.before.largest);
});
test("invalid model weights are rejected",async()=>{
 const model=await fitMarshNet(ds,{epochs:1});
 model.weights.W1[0]=NaN;
 assert.throws(()=>validateMarshNet(model),/Malformed model weights/);
});
