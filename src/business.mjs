import {validateBusinessDataset,evaluatePeriod,reportCsv,reportJson} from "./business-core.mjs";

const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat("ar-IQ",{maximumFractionDigits:3});
const percent = new Intl.NumberFormat("ar-IQ",{style:"percent",maximumFractionDigits:1});
const PREF_KEY = "marshpulse-business-preferences-v1";
let builtIn = null, source = null, sourceKind = "bundled_historical", report = null;
const controls = ["business-from","business-to","business-quality","business-drop"];
const buttons = ["business-print","business-csv","business-json"];
const status = (message,error=false) => {
  $("business-status").textContent=message;
  if(error)$("business-status").setAttribute("data-error","");
  else $("business-status").removeAttribute("data-error");
};
function readPrefs() {
  try {return JSON.parse(localStorage.getItem(PREF_KEY)||"{}")||{};}
  catch {return {};}
}
function selectOptions(data,settings) {
  for(const id of ["business-from","business-to"]) {
    const el=$(id); el.replaceChildren();
    for(const row of data.rows){
      const option=document.createElement("option");option.value=row[0];option.textContent=row[0];el.append(option);
    }
    el.disabled=false;
  }
  const months=new Set(data.rows.map(r=>r[0]));
  $("business-from").value=months.has(settings.from)?settings.from:data.rows[0][0];
  $("business-to").value=months.has(settings.to)?settings.to:data.rows.at(-1)[0];
  $("business-quality").value=["0.8","0.9","0.95","0.99"].includes(String(settings.quality)) ? String(settings.quality) : "0.9";
  $("business-drop").value=Number.isFinite(Number(settings.dropKm2))?String(settings.dropKm2):"5";
}
function currentOptions(){
  return {from:$("business-from").value,to:$("business-to").value,
    quality:Number($("business-quality").value),dropKm2:Number($("business-drop").value)};
}
function setExport(enabled){for(const id of buttons)$(id).disabled=!enabled;}
function drawChart(result) {
  const host=$("business-chart");
  const rows=result.selected;
  const max=Math.max(...rows.map(r=>r[1]),1);
  const fragment=document.createDocumentFragment();
  for(const [month,water,clear] of rows){
    const bar=document.createElement("div");
    bar.className="business-bar";bar.title=month+" · "+water+" كم² · "+Math.round(clear*100)+"%";
    if(clear<result.settings.quality)bar.setAttribute("data-low","");
    const fill=document.createElement("span");fill.className="business-bar-fill";
    fill.style.height=(Math.max(2,Math.round(135*water/max)))+"px";
    const label=document.createElement("small");label.textContent=month;
    bar.append(fill,label);fragment.append(bar);
  }
  host.replaceChildren(fragment);
  host.setAttribute("aria-label","المساحة المصنفة مياه من "+result.settings.from+" إلى "+result.settings.to+
    "؛ الخطوط المخططة تشير إلى أشهر تقل تغطيتها الصافية عن الحد المختار");
}
function paint() {
  if(!source)return;
  try{
    report=evaluatePeriod(source,currentOptions());
    const {summary,alerts,settings,provenance}=report;
    $("business-area").textContent=number.format(summary.lastProxyKm2);
    $("business-difference").textContent=(summary.areaDifferenceKm2>0?"+":"")+number.format(summary.areaDifferenceKm2);
    $("business-coverage").textContent=percent.format(summary.meanCoverage);
    $("business-alerts").textContent=number.format(summary.reviewDecreases);
    $("business-comparison-note").textContent="الفترة: "+settings.from+" إلى "+settings.to+" ("+summary.records+" أشهر). "+report.comparisonCaveat;
    const list=$("business-flag-list");
    const children=document.createDocumentFragment();
    for(const flag of alerts) {
      const li=document.createElement("li");
      if(flag.kind==="review_decrease") li.textContent=flag.month+": انخفاض مؤشر المياه على البكسلات المشتركة بمقدار "+number.format(Math.abs(flag.deltaKm2))+" كم²؛ يحتاج مراجعة بشرية.";
      else {li.textContent=flag.month+": تغطية صافية "+percent.format(flag.coverage)+" دون حد "+percent.format(settings.quality)+"؛ لا تعتمد على هذه المشاهدة وحدها.";li.setAttribute("data-low","");}
      children.append(li);
    }
    if(!alerts.length){const li=document.createElement("li");li.textContent="لم تظهر حالات مراجعة تتجاوز الحدود المختارة. هذا لا يؤكد سلامة الحالة البيئية.";children.append(li);}
    list.replaceChildren(children);
    drawChart(report);
    $("business-provenance").textContent=
      "المصدر: "+provenance.imagery+" | المربع [غرب، جنوب، شرق، شمال]: "+
      provenance.boundingBox.join(", ")+" | آخر شهر متاح: "+provenance.lastObservation+
      " | الحدود رسمية؟ لا | نوع البيانات: "+(sourceKind==="bundled_historical"?"سجل الحويزة التاريخي المضمّن":"ملف خارجي غير محقق مستقلًا");
    $("business-disclaimer").textContent=report.caveat;
    $("business-source-tag").textContent=sourceKind==="bundled_historical"?"سجل تاريخي مثبت المصدر، غير متحقق ميدانيًا":"ملف مستورد؛ المصدر غير متحقق";
    $("business-latest").textContent="آخر شهر متاح: "+provenance.lastObservation;
    const evidence=$("business-evidence");
    if(typeof provenance.sourceWorkflow==="string"&&/^https:\/\/github\.com\//i.test(provenance.sourceWorkflow)){
      evidence.href=provenance.sourceWorkflow;evidence.hidden=false;
    }else evidence.hidden=true;
    const url=new URL(location.href);
    url.search=new URLSearchParams({from:settings.from,to:settings.to,quality:String(settings.quality),dropKm2:String(settings.dropKm2)}).toString();
    url.hash="";
    $("business-share").href=url.toString();
    $("business-share-warning").textContent=sourceKind==="bundled_historical"?
      "الرابط يشارك فترة المقارنة والحدود فقط، مع سجل الحويزة الافتراضي.":
      "الرابط لا يتضمن ملفك المستورد؛ فتحه لدى شخص آخر سيعرض سجل الحويزة الافتراضي، وليس نتائج ملفك.";
    if(sourceKind==="bundled_historical"){
      try{localStorage.setItem(PREF_KEY,JSON.stringify(settings));}catch{}
    }
    status("تم تحميل "+source.rows.length+" شهرًا من مؤشر فضائي غير محقق ميدانيًا. النتائج للتحليل التاريخي فقط.");
    setExport(true);
  }catch(error){
    report=null;setExport(false);status("تعذر إعداد التقرير: "+error.message,true);
  }
}
function download(filename,content,type) {
  const blob=new Blob([type.startsWith("text/csv")?"\uFEFF": "",content],{type});
  const link=document.createElement("a");const url=URL.createObjectURL(blob);
  link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function loadBundled() {
  const response=await fetch("./data/hawizeh-actual-observations.json");
  if(!response.ok)throw new Error("HTTP "+response.status);
  const data=await response.json();
  if(!validateBusinessDataset(data))throw new Error("Invalid historical observation schema");
  builtIn=data;source=data;sourceKind="bundled_historical";
  const prefs={...readPrefs(),...Object.fromEntries(new URLSearchParams(location.search))};
  selectOptions(data,prefs);paint();
}
function bindUI(){
  for(const id of controls) $(id).addEventListener("change",paint);
  $("business-reset").addEventListener("click",()=>{
    if(!builtIn){status("السجل الأساسي غير متاح.",true);return;}
    source=builtIn;sourceKind="bundled_historical";$("business-upload").value="";
    selectOptions(builtIn,readPrefs());paint();
  });
  $("business-upload").addEventListener("change",async event=>{
    const file=event.target.files?.[0];
    if(!file)return;
    try{
      if(file.size>2_000_000)throw new Error("حجم الملف يتجاوز 2 MB");
      const data=JSON.parse(await file.text());
      if(!validateBusinessDataset(data))throw new Error("مخطط بيانات غير صالح، أو تواريخ/تغطية/مربع جغرافي غير صحيح");
      source=data;sourceKind="user_supplied_unverified";
      selectOptions(data,{});paint();
    }catch(error){status("لم نقبل الملف: "+error.message,true);event.target.value="";}
  });
  $("business-csv").addEventListener("click",()=>{if(report)download("marshpulse-observations.csv",reportCsv(report),"text/csv;charset=utf-8");});
  $("business-json").addEventListener("click",()=>{if(report)download("marshpulse-screening-report.json",reportJson(report,sourceKind,new Date().toISOString()),"application/json;charset=utf-8");});
  $("business-print").addEventListener("click",()=>{if(report)window.print();});
}
async function init() {
  bindUI();
  try{await loadBundled();}
  catch(error){status("تعذر تحميل بيانات الحويزة التاريخية. لا تُعرض بيانات اصطناعية بدلًا عنها: "+error.message,true);setExport(false);}
}
if(typeof document!=="undefined"){
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
}
