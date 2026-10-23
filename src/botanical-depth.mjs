import Atropos from "../vendor/atropos/atropos.mjs";

/**
 * Interactive depth is progressive enhancement: real photographs, readable
 * captions and botanical layers remain visible without JS/hover.
 * Atropos v2, MIT: vendor/atropos/LICENSE.
 */
export const botanicalScenePreset=Object.freeze({
 hero:Object.freeze({activeOffset:24,rotateXMax:6,rotateYMax:8,duration:650,
   rotateTouch:false,highlight:false,shadow:false,commonOrigin:true}),
 story:Object.freeze({activeOffset:18,rotateXMax:5,rotateYMax:6,duration:650,
   rotateTouch:false,highlight:false,shadow:false,commonOrigin:true})
});
export function shouldAnimateDepth(env=globalThis){
 const media=env?.matchMedia;
 if(typeof media!=="function")return false;
 return !!media("(hover:hover) and (pointer:fine)").matches &&
   !media("(prefers-reduced-motion: reduce)").matches &&
   !media("(prefers-reduced-data: reduce)").matches;
}
export function initBotanicalDepth(root=globalThis.document,env=globalThis){
 if(!root?.querySelectorAll||!shouldAnimateDepth(env))return [];
 const scenes=[];
 for(const element of root.querySelectorAll("[data-botanical-tilt]")){
   const kind=element.dataset.botanicalTilt;
   if(!Object.hasOwn(botanicalScenePreset,kind)||element.__marshAtropos)continue;
   const eventsEl=element.closest(".flora-stage,.flora-story-visual")??element;
   const instance=Atropos({el:element,eventsEl,...botanicalScenePreset[kind]});
   element.__marshAtropos=instance;
   scenes.push(instance);
 }
 return scenes;
}
if(typeof document!=="undefined"){
 if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",()=>initBotanicalDepth(document,globalThis),{once:true});
 }else initBotanicalDepth(document,globalThis);
}
