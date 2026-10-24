import {chromium} from "playwright";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {mkdir,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
const URL="http://127.0.0.1:8765";
const paths=["/","/lab.html","/model.html","/methods.html","/monitor.html"];
const tags=["wcag2a","wcag2aa","wcag21a","wcag21aa"];
const axeSource=readFileSync(resolve("node_modules/axe-core/axe.min.js"),"utf8");
const browser=await chromium.launch({channel:"chrome",headless:true,args:["--no-sandbox"]});
const results=[];
try{
 for(const route of paths){
  const page=await browser.newPage({viewport:{width:1440,height:950}});
  try{
   const r=await page.goto(URL+route,{waitUntil:"networkidle"});
   assert.equal(r?.status(),200,"Missing route "+route);
   await page.addScriptTag({content:axeSource});
   const scan=await page.evaluate(async tags=>window.axe.run(document,{runOnly:{type:"tag",values:tags}}),tags);
   results.push({route,passed:scan.passes.length,incomplete:scan.incomplete.length,
    violations:scan.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,
      nodes:v.nodes.slice(0,12).map(n=>({html:n.html,selector:n.target,reason:n.failureSummary}))}))});
  }finally{await page.close();}
 }
 await mkdir("artifacts",{recursive:true});
 await writeFile("artifacts/accessibility-audit.json",JSON.stringify({date:new Date().toISOString(),standard:"WCAG 2.1 AA automated axe-core checks",results},null,2));
 const severe=results.flatMap(x=>x.violations.filter(v=>["critical","serious"].includes(v.impact)).map(v=>({route:x.route,id:v.id,impact:v.impact,instances:v.nodes.length})));
 console.log("ACCESSIBILITY_AUDIT",JSON.stringify(results.map(x=>({route:x.route,violations:x.violations.map(v=>v.id),passed:x.passed}))));
 if(severe.length)console.error("SERIOUS_AXE_FINDINGS",JSON.stringify(severe));
 assert.equal(severe.length,0,"Serious accessibility violations found; inspect artifacts/accessibility-audit.json");
}finally{await browser.close();}
