import test from "node:test";
import assert from "node:assert/strict";
import {syntheticWetlandField,contourPaths,initLivingGrid} from "../src/living-grid.mjs";

test("wetland scalar field is deterministic and has non-flat dynamic range",()=>{
 const f=syntheticWetlandField(72,40,27);
 assert.equal(f.length,2880);
 assert.deepEqual(f,syntheticWetlandField(72,40,27));
 assert.notDeepEqual(f,syntheticWetlandField(72,40,28));
 assert.ok(Math.max(...f)-Math.min(...f)>0.75,"isolines need interesting spatial variation");
});
test("vendored ISC D3 marching squares produces nonempty closed SVG geometry",()=>{
 const layers=contourPaths(80,48,31,[-.49,-.18,.12,.4,.67]);
 assert.equal(layers.length,5);
 assert.ok(layers.some(l=>l.paths.length>=2));
 const d=layers.flatMap(l=>l.paths);
 assert.ok(d.length>8);
 assert.ok(d.every(p=>p.startsWith("M")&&p.endsWith("Z")));
 assert.ok(d.every(p=>!p.includes("NaN")&&!p.includes("Infinity")));
});
test("mount operation degrades gracefully without browser DOM",()=>{
 assert.equal(initLivingGrid({querySelectorAll:()=>[]}),0);
 assert.equal(initLivingGrid(null),0);
 assert.throws(()=>syntheticWetlandField(1,20),/Invalid decorative grid/);
});
