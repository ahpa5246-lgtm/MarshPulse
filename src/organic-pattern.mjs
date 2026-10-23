import Contours from "../vendor/d3-contour/contours.mjs";
import {syntheticWetlandField} from "./living-grid.mjs";

/**
 * Organic river-line pattern, built from real D3 Contour Marching Squares rings.
 * Long open sections + directionally extended tapered ends. Deterministic.
 * All shapes are decorative, never actual marsh topography or remote-sensing.
 */
const NS="http://www.w3.org/2000/svg";
const SETTINGS={
 hero:{seed:11,lines:20,levels:[-.35,-.12,.12,.37,.6],dots:100},
 light:{seed:37,lines:18,levels:[-.42,-.16,.12,.4],dots:92},
 cards:{seed:53,lines:20,levels:[-.46,-.2,.08,.35],dots:100},
 bottom:{seed:77,lines:16,levels:[-.33,-.06,.25,.5],dots:60},
 intro:{seed:91,lines:15,levels:[-.43,-.10,.26,.46],dots:75},
 analysis:{seed:115,lines:17,levels:[-.4,-.13,.13,.4],dots:80}
};
const clamp=(v,low,high)=>Math.max(low,Math.min(high,v));
function randomGen(seed){let s=seed>>>0;return ()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};}
function copyPoint(point,width,height){return [point[0]*1200/width,point[1]*820/height];}
function normalUnit(a,b){
 const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy)||1;
 return [dx/len,dy/len];
}
function extendOpenEnds(points,random){
 if(points.length<3)return points;
 const a=normalUnit(points[Math.min(5,points.length-1)],points[0]);
 const b=normalUnit(points[Math.max(0,points.length-6)],points[points.length-1]);
 const front=115+random()*145,back=145+random()*190;
 const head=[[points[0][0]+a[0]*front,points[0][1]+a[1]*front],
             [points[0][0]+a[0]*front*.50,points[0][1]+a[1]*front*.50]];
 const tail=[[points.at(-1)[0]+b[0]*back*.45,points.at(-1)[1]+b[1]*back*.45],
             [points.at(-1)[0]+b[0]*back,points.at(-1)[1]+b[1]*back]];
 return [...head,...points,...tail];
}
const ease=t=>t*t*(3-2*t);
function pathFromPoints(points,side){
 const all=points.map(p=>p.map(v=>Math.round(v*100)/100));
 let d="M"+all[0].join(",");
 for(let i=1;i<all.length-1;i++){
  const a=all[i],b=all[i+1];
  d+=" Q"+a.join(",")+" "+((a[0]+b[0])/2).toFixed(2)+","+((a[1]+b[1])/2).toFixed(2);
 }
 return d+" L"+all.at(-1).join(",");
}
/** Returns a genuinely tapered, filled organic ribbon, not an even-width closed contour. */
export function taperedRibbon(points,width=1.8,frontTaper=.26,backTaper=.32){
 if(!Array.isArray(points)||points.length<4)return "";
 const upper=[],lower=[];
 for(let i=0;i<points.length;i++){
  const prev=points[Math.max(0,i-1)],next=points[Math.min(points.length-1,i+1)];
  const dir=normalUnit(prev,next),normal=[-dir[1],dir[0]];
  const t=i/(points.length-1);
  const taper=ease(clamp(t/frontTaper,0,1))*ease(clamp((1-t)/backTaper,0,1));
  const half=(width*taper)/2;
  upper.push([points[i][0]+normal[0]*half,points[i][1]+normal[1]*half]);
  lower.push([points[i][0]-normal[0]*half,points[i][1]-normal[1]*half]);
 }
 return pathFromPoints(upper)+" "+pathFromPoints(lower.reverse()).replace(/^M/,"L")+" Z";
}
function extractedSegments(settings){
 const cols=105,rows=72;
 const field=syntheticWetlandField(cols,rows,settings.seed);
 const shapes=Contours().size([cols,rows]).smooth(true).thresholds(settings.levels)(field);
 const all=shapes.flatMap(shape=>shape.coordinates.flatMap(poly=>poly))
  .filter(ring=>ring.length>37);
 // Avoid treating a contour as if it were a georeferenced polyline.
 const random=randomGen(settings.seed*4099+71);
 const paths=[];
 if(!all.length)return paths;
 for(let i=0;i<settings.lines*3&&paths.length<settings.lines;i++){
  const ring=all[Math.floor(random()*all.length)];
  // Segments span substantial arcs without degenerating into uniform concentric rings.
  const start=Math.floor(random()*Math.max(1,ring.length-5));
  const want=Math.min(ring.length-4,Math.round(38+random()*125));
  const step=(.85+random()*.55);
  const sampled=[];
  for(let j=0;j<want;j+=step){
   const at=(start+Math.floor(j))%Math.max(1,ring.length-1);
   sampled.push(copyPoint(ring[at],cols,rows));
  }
  if(sampled.length<12)continue;
  const extended=extendOpenEnds(sampled,random);
  const d=taperedRibbon(extended,.85+random()*1.25,.22+random()*.08,.29+random()*.12);
  if(d.length>100)paths.push({d,variant:i%5});
 }
 return paths;
}
export function patternGeometry(zone="light"){
 if(!Object.hasOwn(SETTINGS,zone))throw Error("Unknown pattern zone");
 const settings=SETTINGS[zone],random=randomGen(settings.seed+509);
 const paths=extractedSegments(settings);
 const dots=[];
 for(let i=0;i<settings.dots;i++){
  dots.push({x:Math.round(random()*1200),y:Math.round(random()*820),
    r:+(.65+random()*1.25).toFixed(2)});
 }
 return {paths,dots,seed:settings.seed};
}
function element(parent,tag,props){
 const child=parent.ownerDocument.createElementNS(NS,tag);
 for(const [key,v] of Object.entries(props))child.setAttribute(key,String(v));
 parent.appendChild(child);return child;
}
export function mountOrganicPattern(host){
 if(!host?.dataset?.organicPattern)return null;
 if(host.querySelector(":scope > .organic-pattern-svg"))return host.querySelector(":scope > .organic-pattern-svg");
 const geometry=patternGeometry(host.dataset.organicPattern);
 const svg=host.ownerDocument.createElementNS(NS,"svg");
 for(const [name,value] of Object.entries({class:"organic-pattern-svg",viewBox:"0 0 1200 820",
   preserveAspectRatio:"xMidYMid slice","aria-hidden":"true",focusable:"false"}))svg.setAttribute(name,value);
 const layer=element(svg,"g",{class:"organic-pattern-ribbons"});
 for(const path of geometry.paths)element(layer,"path",{d:path.d,class:"organic-ribbon",
   "data-variant":path.variant});
 const dots=element(svg,"g",{class:"organic-pattern-dots"});
 for(const p of geometry.dots)element(dots,"circle",{class:"organic-dot",cx:p.x,cy:p.y,r:p.r});
 host.prepend(svg);
 host.classList.add("organic-pattern-ready");
 return svg;
}
export function initOrganicPattern(root=globalThis.document){
 if(!root?.querySelectorAll)return 0;
 let count=0;
 for(const host of root.querySelectorAll("[data-organic-pattern]")){
  if(mountOrganicPattern(host))count++;
 }
 return count;
}
if(typeof document!=="undefined")initOrganicPattern(document);
