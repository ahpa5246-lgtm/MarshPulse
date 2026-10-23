/**
 * Transition direction and staggering are assigned before MotionFlow's DOMContentLoaded
 * auto-initializer. No scroll listeners are added by this file. MotionFlow (MIT) owns
 * the reveal animation. Interactive scientific controls are intentionally excluded.
 */
const sections=[
 [".flora-intro-grid h2","fade-up",0],
 [".flora-intro-grid > div","fade-up",120],
 [".flora-section-heading","fade-up",0],
 [".flora-path","fade-up",110],
 [".flora-story-copy","fade-up",0],
 [".flora-bottom-grid > *","fade-up",100],
 [".inner-intro h1","fade-up",0],
 [".inner-intro > p:last-child","fade-up",110],
 [".model-v2-feature .v2-copy","fade-up",0],
 [".model-v2-feature .v2-diagram","fade-up",100],
 [".paper-panel","fade-up",60],
 [".method-card","fade-up",60],
 [".study-note > div","fade-up",80],
 [".shell .section-heading","fade-up",0],
 [".shell .metric","fade-up",65],
 [".shell .chart-panel","fade-up",0],
 [".shell .benchmark-panel","fade-up",110]
];
export function prepareSectionMotion(root=globalThis.document,reduced=false){
 if(!root?.querySelectorAll||reduced)return 0;
 let mounted=0;
 for(const [selector,preset,baseDelay] of sections){
  for(const [index,node] of [...root.querySelectorAll(selector)].entries()){
   if(node.hasAttribute("data-mf-animation"))continue;
   node.setAttribute("data-mf-animation",preset);
   node.setAttribute("data-mf-animation-duration","780");
   node.setAttribute("data-mf-animation-distance","26");
   node.setAttribute("data-mf-animation-delay",String(Math.min(280,baseDelay+index*45)));
   node.setAttribute("data-mf-animation-once","true");
   mounted++;
  }
 }
 return mounted;
}
if(typeof document!=="undefined"){
 const reduced=globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches??false;
 prepareSectionMotion(document,reduced);
}
