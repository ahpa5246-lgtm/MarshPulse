import test from "node:test";
import assert from "node:assert/strict";
import {shouldAnimateDepth,initBotanicalDepth,botanicalScenePreset} from "../src/botanical-depth.mjs";

const env=(hover,reduced=false,data=false)=>({
 matchMedia:q=>({matches:q.includes("hover:hover")?hover:q.includes("reduced-motion")?reduced:q.includes("reduced-data")?data:false})
});
test("botanical 3D depth requires fine hover and respects reduced motion/data",()=>{
 assert.equal(shouldAnimateDepth(env(true)),true);
 assert.equal(shouldAnimateDepth(env(false)),false);
 assert.equal(shouldAnimateDepth(env(true,true)),false);
 assert.equal(shouldAnimateDepth(env(true,false,true)),false);
 assert.equal(shouldAnimateDepth({}),false);
});
test("interactive tilt is gentle enough for reading",()=>{
 assert.ok(botanicalScenePreset.hero.rotateXMax<=8);
 assert.ok(botanicalScenePreset.story.rotateYMax<=8);
 assert.equal(botanicalScenePreset.hero.rotateTouch,false);
 assert.equal(botanicalScenePreset.hero.highlight,false);
});
test("degrades safely without DOM",()=>{
 assert.deepEqual(initBotanicalDepth(null,env(true)),[]);
 assert.deepEqual(initBotanicalDepth({querySelectorAll:()=>[]},env(true,true)),[]);
});
