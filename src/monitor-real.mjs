/* MarshPulse: genuine Sentinel proxy measurements, never synthetic lab data. */
const SVG_NS="http://www.w3.org/2000/svg";
export function validateMonitor(record){
 if(record?.format!=="marshpulse-observed-water-v1"||
    record.label!=="UNVERIFIED SATELLITE PROXY"||
    !Array.isArray(record.rows)||record.rows.length<24||
    record.official_wetland_boundary!==false)return false;
 const dates=new Set();
 for(const row of record.rows){
  if(!Array.isArray(row)||row.length!==4||
     !/^\d{4}-(0[1-9]|1[0-2])$/.test(row[0])||
     !Number.isFinite(row[1])||row[1]<0||
     !Number.isFinite(row[2])||row[2]<0||row[2]>1||
     (row[3]!==null&&!Number.isFinite(row[3]))||
     dates.has(row[0]))return false;
  dates.add(row[0]);
 }
 return record.rows.every((r,i)=>i===0||r[0]>record.rows[i-1][0]);
}
export function chartPoints(records,width=890,height=235){
 const values=records.map(x=>x[1]);
 const limit=Math.max(10,Math.ceil(Math.max(...values)/10)*10);
 const scaleX=i=>width*(i/(records.length-1));
 const scaleY=v=>height*(1-v/limit);
 return {points:values.map((v,i)=>[scaleX(i),scaleY(v)]),
         ceiling:limit,width,height};
}
function svgNode(tag,attrs={}){
 const el=document.createElementNS(SVG_NS,tag);
 for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));
 return el;
}
function view(record){
 const rows=record.rows;
 const status=document.querySelector("#monitor-load-status");
 const slider=document.querySelector("#monitor-month");
 const date=document.querySelector("#monitor-date");
 const area=document.querySelector("#monitor-area");
 const coverage=document.querySelector("#monitor-coverage");
 const change=document.querySelector("#monitor-change");
 const tbody=document.querySelector("#monitor-data-rows");
 const host=document.querySelector("#monitor-chart");
 if(!status||!slider||!host)return;
 const fmt=new Intl.NumberFormat("ar-IQ",{maximumFractionDigits:3});
 const percent=new Intl.NumberFormat("ar-IQ",{style:"percent",maximumFractionDigits:1});
 const layout=chartPoints(rows);
 const points=layout.points,ceiling=layout.ceiling,width=layout.width,height=layout.height;
 const svg=svgNode("svg",{viewBox:"0 0 980 300",preserveAspectRatio:"xMidYMid meet",role:"img",
   "aria-label":"مساحة المياه المصنفة فضائيًا عبر 36 شهرًا في منطقة تجريبية قرب الحويزة"});
 const plot=svgNode("g",{transform:"translate(62 22)"});
 for(let y=0;y<=ceiling;y+=10){
  plot.appendChild(svgNode("line",{x1:0,x2:width,y1:height*(1-y/ceiling),y2:height*(1-y/ceiling),
   stroke:y===0?"#a1bba9":"#c9dfca","stroke-width":y===0?1.5:1,"stroke-dasharray":y===0?"0":"4 6"}));
  const txt=svgNode("text",{x:-12,y:height*(1-y/ceiling)+5,"text-anchor":"end",
   fill:"#486658","font-size":13,direction:"ltr"});txt.textContent=String(y);plot.appendChild(txt);
 }
 rows.forEach((r,i)=>{
  if(r[2]>=.8)return;
  plot.appendChild(svgNode("rect",{x:points[i][0]-width/rows.length*.43,y:0,width:width/rows.length*.85,height,
   fill:"#e4b981",opacity:".16","aria-hidden":"true"}));
 });
 const d="M"+points.map(([x,y])=>x.toFixed(1)+" "+y.toFixed(1)).join(" L");
 plot.appendChild(svgNode("path",{d:d+" L "+width+" "+height+" L 0 "+height+" Z",fill:"#b5e8d5",opacity:".39"}));
 plot.appendChild(svgNode("path",{d,fill:"none",stroke:"#277a65","stroke-width":3,
   "stroke-linecap":"round","stroke-linejoin":"round"}));
 rows.forEach((r,i)=>{
  if(i%6!==0&&i!==rows.length-1)return;
  const tick=svgNode("text",{x:points[i][0],y:height+25,"text-anchor":i===0?"start":i===rows.length-1?"end":"middle",
    "font-size":12,"font-family":"system-ui, sans-serif",fill:"#648371",direction:"ltr"});
  tick.textContent=r[0];plot.appendChild(tick);
 });
 const focusLine=svgNode("line",{x1:0,y1:0,x2:0,y2:height,stroke:"#7658ae","stroke-width":1.4,"stroke-dasharray":"4 4"});
 const focusCircle=svgNode("circle",{cx:0,cy:0,r:6,fill:"#8b69ae",stroke:"#fff","stroke-width":2.5});
 plot.appendChild(focusLine);plot.appendChild(focusCircle);svg.appendChild(plot);
 host.replaceChildren(svg);
 const paint=index=>{
  const i=Math.max(0,Math.min(rows.length-1,Number(index)||0));
  const [month,wet,clear,delta]=rows[i];
  date.textContent=month;
  area.textContent=fmt.format(wet);
  coverage.textContent=percent.format(clear);
  change.textContent=delta===null?"—":(delta>0?"+":"")+fmt.format(delta);
  focusLine.setAttribute("x1",points[i][0]);focusLine.setAttribute("x2",points[i][0]);
  focusCircle.setAttribute("cx",points[i][0]);focusCircle.setAttribute("cy",points[i][1]);
  slider.setAttribute("aria-valuetext",month);
 };
 slider.max=String(rows.length-1);slider.value=String(rows.length-1);slider.disabled=false;
 slider.addEventListener("input",()=>paint(slider.value));
 paint(slider.value);
 const fragment=document.createDocumentFragment();
 for(const [month,water,clear,delta] of rows){
  const tr=document.createElement("tr");
  for(const value of [month,fmt.format(water),percent.format(clear),delta===null?"—":fmt.format(delta)]){
   const td=document.createElement("td");td.textContent=value;tr.appendChild(td);
  }
  fragment.appendChild(tr);
 }
 tbody.replaceChildren(fragment);
 status.textContent="36 سجلًا من صور فضائية حقيقية؛ تصنيف المياه غير محقق ميدانيًا.";
 status.classList.add("real-monitor-loaded");
}
export async function initRealMonitor(){
 const status=document.querySelector("#monitor-load-status");
 if(!status)return;
 try{
  const r=await fetch("./data/hawizeh-actual-observations.json");
  if(!r.ok)throw new Error("HTTP "+r.status);
  const data=await r.json();
  if(!validateMonitor(data))throw new Error("Invalid or unverified observation schema");
  view(data);
 }catch(err){
  status.textContent="تعذر تحميل سجل الصور الحقيقي. لا توجد بيانات اصطناعية بديلة. راجعي مصدر GitHub للتجربة.";
  status.classList.add("real-monitor-error");
  console.error("Real monitoring unavailable:",err.message);
 }
}
if(typeof document!=="undefined"){
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initRealMonitor,{once:true});
 else initRealMonitor();
}
