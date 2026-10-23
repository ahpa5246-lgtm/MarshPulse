import test from "node:test";
import assert from "node:assert/strict";
import {patternGeometry,taperedRibbon,initOrganicPattern} from "../src/organic-pattern.mjs";
import {prepareSectionMotion} from "../src/section-motion.mjs";

test("open tapered ribbons originate from true deterministic D3 isolines",()=>{
 const first=patternGeometry("hero");
 assert.ok(first.paths.length>=10);
 assert.deepEqual(first,patternGeometry("hero"));
 assert.notDeepEqual(first,patternGeometry("cards"));
 assert.ok(first.paths.every(x=>x.d.startsWith("M")&&x.d.endsWith(" Z")));
 assert.ok(first.paths.every(x=>!x.d.includes("NaN")&&!x.d.includes("Infinity")));
 assert.ok(first.paths.some(x=>x.d.length>1800),"long landscape-following paths required");
 assert.ok(first.dots.length>40);
});
test("all pattern zones provide nonidentical geometry",()=>{
 const zones=["hero","light","cards","bottom","intro","analysis"];
 const seeds=zones.map(x=>patternGeometry(x).seed);
 assert.equal(new Set(seeds).size,zones.length);
 for(const z of zones)assert.ok(patternGeometry(z).paths.length>=6,z);
 assert.throws(()=>patternGeometry("nonexistent"),/Unknown pattern/);
});
test("tapered ribbon is a closed organic shape with long axis",()=>{
 const points=Array.from({length:50},(_,i)=>[i*8,95+Math.sin(i/7)*35]);
 const path=taperedRibbon(points,3);
 assert.match(path,/^M/);
 assert.match(path,/ Z$/);
 assert.ok(path.includes(" Q"));
 assert.ok(path.length>800);
 assert.equal(taperedRibbon([]),"");
});
test("motion defaults remain progressive-enhancement safe",()=>{
 assert.equal(initOrganicPattern({querySelectorAll:()=>[]}),0);
 assert.equal(initOrganicPattern(null),0);
 assert.equal(prepareSectionMotion({querySelectorAll:()=>[]},true),0);
 assert.equal(prepareSectionMotion(null),0);
});
