import test from "node:test";
import assert from "node:assert/strict";
import {FLOAT_PAGES,FLOAT_CHAPTERS,pageFromPath,readingProgress,initFloatingNavigation} from "../src/floating-nav.mjs";
test("floating page routing handles home and all three research pages",()=>{
 assert.equal(pageFromPath("/"),"index.html");
 assert.equal(pageFromPath("/MarshPulse/"),"index.html");
 assert.equal(pageFromPath("/MarshPulse/lab.html"),"lab.html");
 assert.equal(pageFromPath("/model.html?tab=training"),"model.html");
 assert.equal(pageFromPath("/methods.html#methods-process"),"methods.html");
 assert.equal(pageFromPath("/unknown.html"),"index.html");
 assert.equal(FLOAT_PAGES.length,4);
});
test("each route has distinct anchored chapters for MIT Gumshoe",()=>{
 for(const [route,chapters] of Object.entries(FLOAT_CHAPTERS)){
  assert.ok(chapters.length>=3,route);
  assert.equal(new Set(chapters.map(x=>x.id)).size,chapters.length);
  assert.ok(chapters.every(x=>x.selector&&x.label&&x.id));
 }
});
test("reading progress is bounded and robust on short pages",()=>{
 assert.equal(readingProgress(0,2000,1000),0);
 assert.equal(readingProgress(500,2000,1000),50);
 assert.equal(readingProgress(1000,2000,1000),100);
 assert.equal(readingProgress(9000,2000,1000),100);
 assert.equal(readingProgress(-50,2000,1000),0);
 assert.equal(readingProgress(100,700,800),0);
});
test("floating nav is an unobtrusive progressive enhancement",()=>{
 assert.equal(initFloatingNavigation(null,{}),null);
 assert.equal(initFloatingNavigation({body:null},{}),null);
});
