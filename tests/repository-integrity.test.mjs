import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync,existsSync} from "node:fs";
import {resolve,dirname,relative} from "node:path";
import {fileURLToPath} from "node:url";
const root=resolve(dirname(fileURLToPath(import.meta.url)),"..");
const pages=["index.html","lab.html","model.html","methods.html","monitor.html","business.html"];
function assets(html){
 const result=[];
 const re=/<(?:a|img|link|script)\b[^>]*?\b(?:href|src)\s*=\s*["']([^"']+)["']/gi;
 for(const match of html.matchAll(re)){
  const ref=match[1].trim();
  if(!ref||/^(?:https?:|mailto:|tel:|data:|javascript:|#|\/\/)/i.test(ref))continue;
  const clean=decodeURIComponent(ref.split("#")[0].split("?")[0]);
  if(clean)result.push(clean);
 }
 return result;
}
test("every shipped local HTML/CSS/JS/link asset exists, with no traversal",()=>{
 for(const name of pages){
  const path=resolve(root,name);
  assert.ok(existsSync(path),name+" missing");
  const html=readFileSync(path,"utf8");
  for(const ref of assets(html)){
   const pathname=resolve(dirname(path),ref);
   assert.ok(!relative(root,pathname).startsWith(".."),name+" unsafe relative link "+ref);
   assert.ok(existsSync(pathname),name+" references a missing asset: "+ref);
  }
 }
});
test("real-observation route is not silently misrepresented as synthetic dashboard",()=>{
 const page=readFileSync(resolve(root,"monitor.html"),"utf8");
 assert.match(page,/تصنيف فضائي غير محقق ميدانيًا/);
 assert.match(page,/monitor-real\.mjs/);
 const record=JSON.parse(readFileSync(resolve(root,"data/hawizeh-actual-observations.json"),"utf8"));
 assert.equal(record.official_wetland_boundary,false);
 assert.equal(record.label,"UNVERIFIED SATELLITE PROXY");
 assert.equal(record.rows.length,36);
});
test("commercial workspace is linked and caveats are explicit",()=>{
 const index=readFileSync(resolve(root,"index.html"),"utf8");
 assert.match(index,/href="\\.\\/business\\.html"/);
 const html=readFileSync(resolve(root,"business.html"),"utf8");
 assert.match(html,/غير محقق ميدانيًا/);
 assert.match(html,/business\\.mjs/);
});
test("scientific monitoring and forecast disclaimers remain visible",()=>{
 const source=readFileSync(resolve(root,"ml/verify_experiment.py"),"utf8");
 assert.match(source,/ready_for_operational_or_ecological_decisions/);
 const methods=readFileSync(resolve(root,"methods.html"),"utf8");
 assert.match(methods,/الهيدرولوجيا/);
});
