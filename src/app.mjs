import {demoData,parseCSV,connectivity,articulation,train,scenario,report} from "./engine.mjs";
import {validateMarshNet,predictMarshNet} from "./marshnet.mjs";
const $ = id => document.getElementById(id);
const svgNS="http://www.w3.org/2000/svg";
const state={data:demoData(),model:null,result:null,layer:"observed",selected:null,stress:25,budget:6,custom:null};
const fmt=n=>new Intl.NumberFormat("ar-IQ",{maximumFractionDigits:1}).format(n);
const pct=n=>fmt(100*n)+"%";
function toast(message,isError=false){
  const el=$("toast");el.textContent=message;el.classList.toggle("error",isError);el.classList.add("visible");
  clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove("visible"),3800);
}
function download(filename,content,type){
  const blob=new Blob([content],{type}),url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),500);
}
function selectedDetails(){
  const {data,result,selected}=state,el=$("cell-details");
  if(selected===null){el.textContent="اختاري خلية من الخريطة لمعرفة حالتها واحتمال بقائها مائية في الشهر التالي.";return;}
  const row=Math.floor(selected/data.width),col=selected%data.width;
  const w=result.current[selected],p=result.probabilities[selected],isCritical=result.corridor.includes(selected),protectedCell=result.selected.some(s=>s.index===selected);
  el.textContent="الصف "+fmt(row)+" · العمود "+fmt(col)+" | "+(w?"ماء":"يابسة")+" في آخر رصد | احتمال الماء المتوقع تحت الضغط "+pct(p)+(isCritical?" | نقطة اتصال حرجة":"")+(protectedCell?" | أُضيفت للتدخل النظري":"");
}
function drawMap(){
  const {data,result,layer,selected}=state;const svg=$("map"),w=data.width,h=data.height;
  const size=20;svg.setAttribute("viewBox","0 0 "+(w*size)+" "+(h*size));
  const mask=layer==="observed"?result.current:layer==="forecast"?result.baseline:result.protected;
  const critical=new Set(result.corridor),improved=new Set(result.selected.map(x=>x.index));
  let markup="";
  for(let i=0;i<mask.length;i++){
    const row=Math.floor(i/w),col=i%w,wet=mask[i];
    let fill=wet?"#48a6b0":"#152d36";
    if(layer==="observed"&&wet)fill="#338b9c";
    if(layer!=="observed"&&wet&&result.probabilities[i]>0.85)fill="#72c5c2";
    if(critical.has(i)&&layer==="observed")fill="#e5a96d";
    if(improved.has(i)&&layer==="protected")fill="#e7d57f";
    const stroke=selected===i?"#ffffff":"#10242d",width=selected===i?2.2:0.8;
    markup+='<rect data-cell="'+i+'" x="'+(col*size+0.65)+'" y="'+(row*size+0.65)+'" width="'+(size-1.3)+'" height="'+(size-1.3)+'" rx="2.4" fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+width+'" tabindex="0" role="button" aria-label="cell '+row+' '+col+'"><title>Row '+row+' Col '+col+'</title></rect>';
  }
  svg.innerHTML=markup;
  $("map-date").textContent=layer==="observed"?data.dates.at(-1):result.date;
  $("grid-shape").textContent=w+" × "+h;
  selectedDetails();
}
function drawHistory(){
  const {data}=state,vals=data.frames.map(f=>f.filter(v=>v>=0.5).length/f.length);
  const w=700,h=230,padX=46,top=22,bottom=188;
  const x=i=>padX+i*(w-padX-20)/Math.max(1,vals.length-1);
  const y=v=>bottom-v*(bottom-top);
  let html='';
  for(let k=0;k<=4;k++){
    const yy=y(k/4);
    html+='<line x1="'+padX+'" y1="'+yy+'" x2="'+(w-14)+'" y2="'+yy+'" stroke="#31505a" stroke-dasharray="3 6"/><text x="8" y="'+(yy+4)+'" fill="#91b0b8" font-size="12">'+(k*25)+'%</text>';
  }
  const pts=vals.map((v,i)=>x(i)+","+y(v)).join(" ");
  const fill=padX+","+bottom+" "+pts+" "+x(vals.length-1)+","+bottom;
  html+='<polygon points="'+fill+'" fill="#55bbaa" fill-opacity="0.11"/><polyline points="'+pts+'" fill="none" stroke="#82e0c7" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>';
  const last=vals.length-1;
  html+='<circle cx="'+x(last)+'" cy="'+y(vals[last])+'" r="5.5" fill="#a8f5d9" stroke="#0a222c" stroke-width="3"/>';
  for(const j of [0,Math.floor(last/2),last])html+='<text x="'+x(j)+'" y="215" text-anchor="middle" font-size="12" fill="#a4bcc3">'+data.dates[j]+'</text>';
  $("history-chart").innerHTML=html;
  $("date-range").textContent=fmt(vals.length)+" أشهر • "+data.dates[0]+" — "+data.dates.at(-1)+" • مساحة شبكية لا كيلومترات مربعة";
}
function priorityList(){
  const selected=state.result.selected,el=$("priority-list");el.replaceChildren();
  $("selection-count").textContent=fmt(selected.length);
  if(!selected.length){const li=document.createElement("li");li.textContent="لم تظهر خلايا مؤهلة أو مفيدة لهذا السيناريو. جرّبي تغيير ضغط الجفاف أو الميزانية.";el.append(li);return;}
  for(const item of selected){
    const li=document.createElement("li"),lead=document.createElement("div"),title=document.createElement("strong"),small=document.createElement("small");
    title.textContent="R"+item.row+" · C"+item.col;
    small.textContent=item.wasCritical?"نقطة اتصال حرجة":"تحسين ترابط متوقع";
    lead.append(title,small);li.append(lead);
    const action=document.createElement("button");action.textContent="↗";action.type="button";action.setAttribute("aria-label","عرض الخلية "+item.row+" "+item.col);
    action.addEventListener("click",()=>{state.selected=item.index;state.layer="protected";setTab();drawMap();$("map").scrollIntoView({behavior:"smooth",block:"center"});});
    li.append(action);el.append(li);
  }
}
function setTab(){for(const btn of document.querySelectorAll("[data-layer]")){const active=btn.dataset.layer===state.layer;btn.classList.toggle("active",active);btn.setAttribute("aria-pressed",String(active));}}
function updateScenario(){
  const {data,model}=state;
  state.result=scenario(data,model,{stress:state.stress,budget:state.budget,predictor:state.custom?((data,t,i)=>predictMarshNet(state.custom,data,t,i)):null});
  const actual=data.frames.at(-1).map(v=>v>=0.5),measured=connectivity(actual,data.width,data.height);
  const corridor=articulation(actual,data.width,data.height);
  $("stat-water").textContent=pct(measured.wet/actual.length);
  $("stat-connectivity").textContent=pct(measured.share);
  $("stat-corridors").textContent=fmt(corridor.size);
  $("stat-months").textContent=fmt(data.dates.length);
  $("stress-value").textContent=state.stress+"%";
  $("budget-value").textContent=fmt(state.budget)+" نقاط";
  $("before-largest").textContent=fmt(state.result.before.largest);
  $("after-largest").textContent=fmt(state.result.after.largest);
  const delta=state.result.after.largest-state.result.before.largest;
  $("improvement").textContent=(delta>0?"+":"")+fmt(delta)+" خلية";
  $("policy-opt").textContent=fmt(state.result.policyComparison.optimizedLargest)+" خلية";
  $("policy-risk").textContent=fmt(state.result.policyComparison.riskFirstLargest)+" خلية";
  $("policy-random").textContent=fmt(state.result.policyComparison.randomMeanLargest)+" خلية";
  priorityList();drawMap();
}
function updateModel(){
  const {data,model}=state;
  $("provenance-title").textContent=data.origin==="synthetic"?"وضع تجريبي: بيانات اصطناعية":"بيانات مستوردة: المصدر غير محقَّق تلقائيًا";
  $("provenance-desc").textContent=data.description;
  $("data-pill").textContent=data.origin==="synthetic"?"SIMULATED DATA":"IMPORTED · UNVERIFIED";
  $("data-pill").classList.toggle("imported",data.origin!=="synthetic");
  $("model-brier").textContent=model.metrics.brier.toFixed(4);
  $("baseline-brier").textContent=model.baseline.brier.toFixed(4);
  $("model-f1").textContent=pct(model.metrics.f1);
  $("holdout-samples").textContent=fmt(model.holdoutSamples);
  $("holdout-dates").textContent="فترة الاختبار: "+model.holdoutStart+" — "+model.holdoutEnd+" | آخر تدريب: "+model.trainingEnd;
  $("model-verdict").textContent=model.metrics.brier<model.baseline.brier?
    "اجتاز هذا النموذج المرجع في خطأ Brier على البيانات الحالية؛ هذا لا يثبت صلاحيته ميدانيًا.":
    "لم يتفوق على مرجع الاستمرار في خطأ Brier. لا ينبغي اعتباره تحسنًا علميًا دون مراجعة.";
  $("model-verdict").classList.toggle("caution",model.metrics.brier>=model.baseline.brier);
  drawHistory();updateScenario();
}
function loadData(ds){
  state.data=ds;state.custom=null;$("active-model").textContent="النموذج المرجعي: Logistic";state.selected=null;state.layer="observed";setTab();
  state.model=train(ds);updateModel();
}
for(const btn of document.querySelectorAll("[data-layer]"))btn.addEventListener("click",()=>{state.layer=btn.dataset.layer;setTab();drawMap();});
$("map").addEventListener("click",e=>{const rect=e.target.closest("[data-cell]");if(rect){state.selected=Number(rect.dataset.cell);drawMap();}});
$("map").addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){const rect=e.target.closest("[data-cell]");if(rect){e.preventDefault();state.selected=Number(rect.dataset.cell);drawMap();}}});
$("stress").addEventListener("input",e=>{state.stress=Number(e.target.value);updateScenario();});
$("budget").addEventListener("input",e=>{state.budget=Number(e.target.value);updateScenario();});
$("data-upload").addEventListener("change",async e=>{
  const file=e.target.files?.[0];if(!file)return;
  try {
    if(file.size>9000000)throw Error("The CSV file exceeds 9 MB");
    const data=parseCSV(await file.text());
    loadData(data);toast("تم استيراد البيانات وتشغيل التحقق الزمني. لم يُتحقق من المصدر.");
  }catch(err){toast("تعذّر الاستيراد: "+err.message,true);}
  e.target.value="";
});
$("marshnet-upload").addEventListener("change",async e=>{
  const f=e.target.files?.[0];if(!f)return;
  try{
    if(f.size>2e6)throw Error("ملف الأوزان أكبر من 2 ميغابايت");
    const candidate=JSON.parse(await f.text());validateMarshNet(candidate);
    const p=candidate.provenance??{},d=state.data;
    if(p.lastMonth!==d.dates.at(-1)||p.firstMonth!==d.dates[0]||p.grid?.[0]!==d.width||p.grid?.[1]!==d.height||p.origin!==d.origin)
      throw Error("الملف مُدرّب على مصدر أو فترة أو شبكة مختلفة. اختاري بيانات التدريب المطابقة أولًا.");
    state.custom=candidate;
    $("active-model").textContent="MarshNet · نموذج خاص مُدرَّب ("+candidate.training?.bestEpoch+" دورات أفضل وزن)";
    $("model-brier").textContent=Number(candidate.evaluation?.model?.brier).toFixed(4);
    $("baseline-brier").textContent=Number(candidate.evaluation?.persistence?.brier).toFixed(4);
    $("model-f1").textContent=Math.round(100*candidate.evaluation?.model?.f1)+"%";
    $("holdout-samples").textContent=fmt(candidate.training?.holdoutSamples??0);
    $("holdout-dates").textContent="نطاق الاختبار المسجّل في ملف MarshNet: "+candidate.training?.holdoutStart+" — "+candidate.training?.holdoutEnd;
    $("model-verdict").textContent=Number(candidate.evaluation?.model?.brier)<Number(candidate.evaluation?.persistence?.brier)
      ?"MarshNet تجاوز مرجع الاستمرار في ملف التقييم المستورد؛ نتائج المصدر غير محقَّقة خارجيًا."
      :"MarshNet لم يتجاوز مرجع الاستمرار وفق ملف التقييم المستورد.";
    updateScenario();toast("تم تفعيل MarshNet على بيانات مطابقة في الشبكة والفترة. هذا لا يتحقق من مصدرها.");
  }catch(err){toast("تعذّر تحميل MarshNet: "+err.message,true);}
  e.target.value="";
});
$("reset-demo").addEventListener("click",()=>{loadData(demoData());toast("عادت بيانات المحاكاة التركيبية.");});
$("csv-example").addEventListener("click",()=>{
  const ds=demoData(),lines=["date,row,col,water"];
  for(let t=0;t<12;t++)for(let row=0;row<3;row++)for(let col=0;col<3;col++){
    const i=(row+7)*ds.width+col+10;lines.push(ds.dates[t]+","+row+","+col+","+(ds.frames[t][i]>=0.5?1:0));
  }
  download("marshpulse-format-example.csv",lines.join("\n")+"\n","text/csv;charset=utf-8");
});
$("export-report").addEventListener("click",()=>{
  const data=report(state.data,state.model,state.result);
  if(state.custom){
    data.predictor="MarshNet · imported MLP";
    data.training=state.custom.training;
    data.modelEvaluation=state.custom.evaluation;
    data.modelProvenance=state.custom.provenance;
    data.modelArchitecture=state.custom.architecture;
    data.disclaimer+=" Imported custom model measurements are reported from the supplied artifact and are not independently recomputed or certified.";
  }else{
    data.predictor="Logistic · built-in baseline";
  }
  download("marshpulse-evidence-"+state.data.dates.at(-1)+".json",JSON.stringify(data,null,2),"application/json");
  toast("تم تصدير التقرير بما فيه الافتراضات ونتائج الاختبار.");
});
try{loadData(state.data);}catch(err){toast("فشل تشغيل المحرك: "+err.message,true);console.error(err);}
