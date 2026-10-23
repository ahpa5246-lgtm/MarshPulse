import Headroom from "../vendor/headroom/Headroom.mjs";

/**
 * MarshPulse floating navigation.
 * Actual open-source engines: Headroom.js (scroll direction), Gumshoe (active
 * section), both MIT licensed and vendored locally. Works without a build step.
 *
 * The original static site navigation remains usable when JavaScript is off.
 */
export const FLOAT_PAGES=[
 {path:"index.html",label:"الرئيسية",short:"الرئيسية",icon:"home"},
 {path:"lab.html",label:"مختبر المياه",short:"المختبر",icon:"water"},
 {path:"model.html",label:"MarshNet AI",short:"MarshNet",icon:"brain"},
 {path:"methods.html",label:"المنهجية",short:"المنهجية",icon:"book"}
];
export const FLOAT_CHAPTERS={
 "index.html":[
  {selector:".flora-hero",id:"home-intro",label:"البداية"},
  {selector:".flora-intro",id:"home-vision",label:"فكرة المشروع"},
  {selector:".flora-experiences",id:"home-explore",label:"المسارات"},
  {selector:".flora-story",id:"home-story",label:"قصة الأهوار"},
  {selector:".flora-bottom-cta",id:"home-next",label:"الخطوة القادمة"}
 ],
 "lab.html":[
  {selector:".hero",id:"top",label:"المقدمة"},
  {selector:"#lab",id:"lab",label:"تحليل المياه"},
  {selector:"#evidence",id:"evidence",label:"الأدلة"},
  {selector:"#about",id:"about",label:"المنهجية"}
 ],
 "model.html":[
  {selector:".inner-intro",id:"model-overview",label:"المقدمة"},
  {selector:".model-v2-feature",id:"model-v2",label:"MarshNet V2"},
  {selector:".main-stack",id:"model-workbench",label:"التدريب والتقييم"}
 ],
 "methods.html":[
  {selector:".inner-intro",id:"methods-intro",label:"المقدمة"},
  {selector:".main-stack.two-col",id:"methods-process",label:"خطوات البحث"},
  {selector:".study-note",id:"methods-limitations",label:"حدود النتائج"}
 ],
 "monitor.html":[
  {selector:".real-monitor-hero",id:"monitor-introduction",label:"الرصد الحقيقي"},
  {selector:"#observed-record",id:"observed-record",label:"سجل المياه"},
  {selector:"#science-check",id:"science-check",label:"موثوقية النموذج"}
 ]
};
const NS="http://www.w3.org/2000/svg";
const DRAW={
 home:['M3 10.5 12 3l9 7.5','M5.5 9.5V20h13V9.5','M9.2 20v-6.4h5.6V20'],
 water:['M2 8.5c2.7-3 5.3-3 8 0s5.3 3 8 0 4.5-3 4.5-3','M2 14c2.7-3 5.3-3 8 0s5.3 3 8 0 4.5-3 4.5-3','M2 19c2.7-3 5.3-3 8 0s5.3 3 8 0 4.5-3 4.5-3'],
 brain:['M12 6a3.5 3.5 0 0 0-6.8 1.2 4 4 0 0 0-1.6 6.6A4 4 0 0 0 7 20h2.5V4.7','M12 6a3.5 3.5 0 0 1 6.8 1.2 4 4 0 0 1 1.6 6.6A4 4 0 0 1 17 20h-2.5V4.7','M9.5 11H6.8M14.5 12H18M9.5 16H7.5'],
 book:['M12 6a8 8 0 0 0-9-2v14a8 8 0 0 1 9 2','M12 6a8 8 0 0 1 9-2v14a8 8 0 0 0-9 2','M12 6v14']
};
export function pageFromPath(pathname){
 const value=String(pathname??"").split("?")[0].split("#")[0].split("/").pop();
 return FLOAT_CHAPTERS[value]?value:"index.html";
}
export function readingProgress(scrollY,scrollHeight,innerHeight){
 const span=Math.max(0,scrollHeight-innerHeight);
 if(!span)return 0;
 return Math.min(100,Math.max(0,Math.round(scrollY/span*100)));
}
function node(doc,tag,className,text){
 const result=doc.createElement(tag);
 if(className)result.className=className;
 if(text!==undefined)result.textContent=text;
 return result;
}
function createIcon(doc,name){
 const svg=doc.createElementNS(NS,"svg");
 for(const [a,b] of Object.entries({viewBox:"0 0 24 24",width:"19",height:"19",fill:"none",stroke:"currentColor","stroke-width":"1.7","stroke-linecap":"round","stroke-linejoin":"round","aria-hidden":"true"}))svg.setAttribute(a,b);
 for(const d of DRAW[name]||[]){
  const p=doc.createElementNS(NS,"path");p.setAttribute("d",d);svg.appendChild(p);
 }
 return svg;
}
function getTargets(doc,route){
 const found=[];
 for(const section of FLOAT_CHAPTERS[route]){
  const el=doc.querySelector(section.selector);
  if(!el)continue;
  // Give every chapter a permanent, meaningful anchor without breaking
  // pre-existing lab.html IDs and their inbound links.
  if(!el.id)el.id=section.id;
  found.push({id:el.id,label:section.label});
 }
 return found;
}
function makeDock(doc,route,chapters){
 const dock=node(doc,"nav","floating-dock");
 dock.setAttribute("aria-label","التنقل العائم بين صفحات MarshPulse وأقسامها");
 dock.setAttribute("dir","rtl");
 dock.id="marsh-floating-nav";
 const gloss=node(doc,"div","floating-dock__gloss");
 gloss.setAttribute("aria-hidden","true");dock.appendChild(gloss);
 const brand=node(doc,"a","floating-dock__brand");
 brand.href="./index.html";brand.setAttribute("aria-label","MarshPulse — الرئيسية");
 brand.appendChild(node(doc,"span","floating-dock__mark","≋"));
 brand.appendChild(node(doc,"span","floating-dock__brand-word","MarshPulse"));
 dock.appendChild(brand);
 const routeLinks=node(doc,"div","floating-dock__pages");
 routeLinks.setAttribute("role","group");routeLinks.setAttribute("aria-label","الصفحات");
 for(const page of FLOAT_PAGES){
  const a=node(doc,"a","floating-dock__page");
  a.href="./"+page.path;a.setAttribute("aria-label",page.label);
  a.appendChild(createIcon(doc,page.icon));
  a.appendChild(node(doc,"span","floating-dock__page-text",page.short));
  if(route===page.path||(route==="monitor.html"&&page.path==="lab.html")){a.classList.add("is-current");a.setAttribute("aria-current","page");}
  routeLinks.appendChild(a);
 }
 dock.appendChild(routeLinks);
 const divider=node(doc,"span","floating-dock__separator");
 divider.setAttribute("aria-hidden","true");dock.appendChild(divider);
 const chapterSide=node(doc,"div","floating-dock__chapter-side");
 const chapterText=node(doc,"div","floating-dock__chapter-label");
 chapterText.appendChild(node(doc,"span","floating-dock__chapter-prefix","الآن في"));
 const current=node(doc,"span","floating-dock__chapter-name",chapters[0]?.label??"المقدمة");
 chapterText.appendChild(current);
 chapterSide.appendChild(chapterText);
 const ol=node(doc,"ol","floating-dock__chapters");
 ol.setAttribute("aria-label","أقسام الصفحة الحالية");
 for(const section of chapters){
  const li=node(doc,"li","floating-dock__chapter");
  const a=node(doc,"a","floating-dock__chapter-link");
  a.href="#"+section.id;
  a.title=section.label;
  a.setAttribute("aria-label","اذهب إلى قسم "+section.label);
  a.appendChild(node(doc,"span","floating-dock__chapter-dot"));
  li.appendChild(a);ol.appendChild(li);
 }
 chapterSide.appendChild(ol);dock.appendChild(chapterSide);
 const top=node(doc,"a","floating-dock__backtop");
 top.href="#"+(chapters[0]?.id??"top");
 top.title="العودة إلى البداية";
 top.setAttribute("aria-label","العودة إلى بداية الصفحة");
 top.textContent="↑";
 dock.appendChild(top);
 const track=node(doc,"span","floating-dock__progress");
 track.setAttribute("aria-hidden","true");
 track.appendChild(node(doc,"span","floating-dock__progress-fill"));
 dock.appendChild(track);
 return dock;
}
export function initFloatingNavigation(doc=globalThis.document,win=globalThis.window){
 if(!doc?.body||!win||!doc.querySelector||!win.addEventListener)return null;
 const previous=doc.getElementById("marsh-floating-nav");
 if(previous)return previous;
 const route=pageFromPath(win.location?.pathname);
 const sections=getTargets(doc,route);
 if(!sections.length)return null;
 const dock=makeDock(doc,route,sections);
 doc.body.appendChild(dock);
 const current=dock.querySelector(".floating-dock__chapter-name");
 const selectSection=link=>{
  const section=sections.find(item=>link?.getAttribute("href")==="#"+item.id);
  if(section)current.textContent=section.label;
 };
 // Gumshoe is a tiny MIT scrollspy with collision-aware offsets and reflow.
 const Gumshoe=win.Gumshoe;
 if(typeof Gumshoe==="function"){
  const spy=new Gumshoe(".floating-dock__chapters a",{offset:()=>Math.min(250,Math.max(96,win.innerHeight*.29)),reflow:true});
  dock.__marshSpy=spy;
  dock.addEventListener("gumshoeActivate",event=>selectSection(event.detail?.link));
 }else{
  // The site and chapter links remain normal links even if scrollspy is absent.
  dock.querySelector(".floating-dock__chapter")?.classList.add("active");
 }
 const nav=new Headroom(dock,{
  offset:{up:175,down:175},
  tolerance:{up:5,down:12},
  onPin:()=>dock.classList.add("is-peeking"),
  onUnpin:()=>dock.classList.remove("is-peeking")
 });
 nav.init();
 dock.__marshHeadroom=nav;
 let scheduled=false;
 const update=()=>{
  scheduled=false;
  const scroll=win.scrollY??win.pageYOffset??0;
  const height=Math.max(doc.documentElement?.scrollHeight??0,doc.body?.scrollHeight??0);
  dock.classList.toggle("is-available",scroll>=175);
  dock.style.setProperty("--dock-progress",readingProgress(scroll,height,win.innerHeight)+"%");
 };
 const schedule=()=>{
  if(scheduled)return;
  scheduled=true;
  if(win.requestAnimationFrame)win.requestAnimationFrame(update);
  else update();
 };
 win.addEventListener("scroll",schedule,{passive:true});
 win.addEventListener("resize",schedule,{passive:true});
 dock.addEventListener("focusin",()=>dock.classList.add("is-keyboard-open"));
 dock.addEventListener("focusout",event=>{
  if(!dock.contains(event.relatedTarget))dock.classList.remove("is-keyboard-open");
 });
 // Hide the floating control while users are editing forms, especially in
 // the water lab and MarshNet workbench; primary header navigation remains.
 doc.addEventListener("focusin",event=>{
  const target=event.target;
  const editing=target?.matches?.("input,textarea,select,[contenteditable='true']");
  if(editing)dock.classList.add("is-editing");
 });
 doc.addEventListener("focusout",event=>{
  if(event.target?.matches?.("input,textarea,select,[contenteditable='true']")){
   dock.classList.remove("is-editing");
  }
 });
 dock.__marshRefresh=update;
 update();
 return dock;
}
if(typeof document!=="undefined"){
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",()=>initFloatingNavigation(document,window),{once:true});
 else initFloatingNavigation(document,window);
}
