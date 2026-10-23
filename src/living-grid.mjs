import Contours from "../vendor/d3-contour/contours.mjs";

/**
 * Living Grid — deterministic ornamental contours, not geographical elevation.
 * Geometry: D3-Contour (Mike Bostock, ISC); field synthesis: MarshPulse.
 * Render once at startup. CSS handles all motion; no rAF loop or scroll listener.
 */
const NS="http://www.w3.org/2000/svg";
const configs={
  hero:{columns:106,rows:59,levels:[-.49,-.18,.12,.4,.67],density:17,seed:31},
  map:{columns:90,rows:55,levels:[-.55,-.28,-.04,.21,.48,.69],density:12,seed:73},
  paths:{columns:106,rows:52,levels:[-.37,-.09,.21,.49],density:19,seed:57},
  intro:{columns:95,rows:55,levels:[-.42,-.10,.22,.52],density:18,seed:19}
};
const hash=(x,y,seed)=> {
  let a=(Math.imul(x+1,374761393)^Math.imul(y+17,668265263)^Math.imul(seed,1442695041))|0;
  a=Math.imul(a^(a>>>13),1274126177);
  return ((a^(a>>>16))>>>0)/4294967295;
};
/** A stylized marsh-branch scalar field; never render as a measured topographic map. */
export function syntheticWetlandField(width,height,seed=31){
  if(!Number.isInteger(width)||!Number.isInteger(height)||width<8||height<8)throw Error("Invalid decorative grid dimensions");
  const field=new Float32Array(width*height);
  for(let j=0;j<height;j++)for(let i=0;i<width;i++){
    const x=i/(width-1),y=j/(height-1);
    // Meandering channel centreline, two remote tributaries, and basin ripples.
    const primary=.51+.16*Math.sin(2*Math.PI*(x*1.26+.07))+.052*Math.sin(2*Math.PI*x*3.2);
    const secondary=.25+.09*Math.cos(2*Math.PI*x*1.9+.8);
    const river=Math.exp(-Math.pow((y-primary)/.105,2));
    const fork=.55*Math.exp(-Math.pow((y-secondary)/.091,2));
    const basin=.62*Math.exp(-((x-.77)/.24)**2-((y-.7)/.27)**2);
    const flat=.25*Math.sin((x*2.45+y*.48)*Math.PI*2)+.21*Math.cos((y*2.1-x*.8)*Math.PI*2);
    const soft=.045*Math.sin(i*.61+j*.24+seed*.17)+.025*(hash(Math.floor(i/4),Math.floor(j/4),seed)-.5);
    field[i+j*width]=Math.fround(.82*river+fork+basin+flat+soft-.49);
  }
  return field;
}
function appendSvg(parent,name,attrs){
  const n=parent.ownerDocument.createElementNS(NS,name);
  for(const [key,value] of Object.entries(attrs))n.setAttribute(key,String(value));
  parent.appendChild(n);return n;
}
function routePath(ring,sx,sy){
  let d="";
  // Convert all coordinates to *local decorative space*. No lat/long implied.
  for(let k=0;k<ring.length;k++){
    const [x,y]=ring[k];
    if(!Number.isFinite(x)||!Number.isFinite(y))continue;
    d+=(k?"L":"M")+(x*sx).toFixed(2)+","+(y*sy).toFixed(2);
  }
  return d+"Z";
}
export function contourPaths(width,height,seed,thresholds){
  const values=syntheticWetlandField(width,height,seed);
  const layers=Contours().size([width,height]).smooth(true).thresholds(thresholds)(values);
  return layers.map((geom,level)=>({
    level,
    value:geom.value,
    paths:geom.coordinates.flatMap(poly=>poly.map(ring=>routePath(ring,1200/width,720/height)).filter(d=>d.length>10))
  }));
}
export function buildLivingGrid(host){
  if(!host||!host.dataset||!configs[host.dataset.topoZone])return null;
  if(host.querySelector(".living-grid-svg"))return host.querySelector(".living-grid-svg");
  const cfg=configs[host.dataset.topoZone];
  const svg=host.ownerDocument.createElementNS(NS,"svg");
  svg.setAttribute("class","living-grid-svg");
  svg.setAttribute("viewBox","0 0 1200 720");
  svg.setAttribute("preserveAspectRatio","xMidYMid slice");
  svg.setAttribute("aria-hidden","true");
  svg.setAttribute("focusable","false");
  const layers=contourPaths(cfg.columns,cfg.rows,cfg.seed,cfg.levels);
  const group=appendSvg(svg,"g",{"class":"living-grid-contours"});
  for(const layer of layers){
    for(const path of layer.paths){
      appendSvg(group,"path",{d:path,"class":"living-grid-isoline","data-level":layer.level,
        "vector-effect":"non-scaling-stroke"});
    }
  }
  const dots=appendSvg(svg,"g",{"class":"living-grid-dots"});
  for(let j=1;j<Math.ceil(720/cfg.density);j++)for(let i=1;i<Math.ceil(1200/cfg.density);i++){
    const x=i*cfg.density,y=j*cfg.density;
    // Sparse deterministic coordinate dots, slightly denser on the river side.
    if(hash(i,j,cfg.seed)<(host.dataset.topoZone==="map"?.25:.105))appendSvg(dots,"circle",{
      cx:x,cy:y,r:(i+j)%7===0?"1.65":".94","class":"living-grid-dot"});
  }
  // A very small decorative locator; never use real coordinates for this synthetic field.
  appendSvg(svg,"text",{x:1166,y:695,"text-anchor":"end","class":"living-grid-label"}).textContent="STUDY GRID · ABSTRACT";
  host.prepend(svg);
  host.classList.add("living-grid-ready");
  return svg;
}
export function initLivingGrid(root=globalThis.document){
  if(!root?.querySelectorAll)return 0;
  let count=0;
  for(const element of root.querySelectorAll("[data-topo-zone]"))if(buildLivingGrid(element))count++;
  return count;
}
if(typeof document!=="undefined")initLivingGrid(document);
