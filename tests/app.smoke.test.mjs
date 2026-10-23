import test from "node:test";
import assert from "node:assert/strict";
class FakeElement {
  constructor(name="div"){this.name=name;this.textContent="";this.innerHTML="";this.value="";this.dataset={};this.attrs={};this.children=[];this.listeners={};this.classList={add(){},remove(){},toggle(){}};}
  setAttribute(k,v){this.attrs[k]=String(v);}
  addEventListener(k,cb){this.listeners[k]=cb;}
  append(...args){this.children.push(...args);}
  replaceChildren(...args){this.children=[...args];}
  remove(){}
  click(){}
  scrollIntoView(){}
  closest(){return this;}
}
const elements=new Map(),ids=["toast","map","history-chart","cell-details","grid-shape","map-date","provenance-title","provenance-desc","data-pill","stat-water","stat-connectivity","stat-corridors","stat-months","stress","stress-value","budget","budget-value","before-largest","after-largest","improvement","selection-count","priority-list","model-brier","baseline-brier","model-f1","holdout-samples","holdout-dates","model-verdict","date-range","data-upload","reset-demo","csv-example","export-report"];
for(const id of ids)elements.set(id,new FakeElement(id));
const buttons=["observed","forecast","protected"].map(layer=>{const b=new FakeElement("button");b.dataset.layer=layer;return b;});
globalThis.document={
  body:new FakeElement("body"),
  getElementById:id=>{if(!elements.has(id))throw Error("Unexpected DOM ID: "+id);return elements.get(id);},
  querySelectorAll:query=>query==="[data-layer]"?buttons:[],
  createElement:tag=>new FakeElement(tag)
};
const el=id=>elements.get(id);
test("dashboard imports, initializes model and renders actual SVG cells",async()=>{
  await import("../src/app.mjs");
  assert.match(el("map").innerHTML,/<rect data-cell="0"/);
  assert.ok(el("history-chart").innerHTML.includes("<polyline"));
  assert.ok(el("model-brier").textContent.length>0);
  assert.ok(el("stat-water").textContent.length>0);
  assert.match(el("provenance-title").textContent,/اصطناعية/);
});
test("layer switching and stress sliders recalculate output",()=>{
  buttons[1].listeners.click();
  assert.equal(buttons[1].attrs["aria-pressed"],"true");
  assert.ok(el("map-date").textContent.length>0);
  el("stress").listeners.input({target:{value:"65"}});
  assert.equal(el("stress-value").textContent,"65%");
  el("budget").listeners.input({target:{value:"3"}});
  assert.equal(el("budget-value").textContent,"3 نقاط");
  assert.ok(el("priority-list").children.length>=1);
});
