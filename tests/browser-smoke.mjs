import {chromium} from "playwright";
import assert from "node:assert/strict";
import {mkdir,readFile} from "node:fs/promises";
const browser=await chromium.launch({channel:"chrome",headless:true,args:["--no-sandbox"]});
const page=await browser.newPage({viewport:{width:1440,height:950},deviceScaleFactor:1,acceptDownloads:true});
const errors=[];
async function exposeAllSections(page){
  await page.evaluate(async()=>{
    const delay=t=>new Promise(resolve=>setTimeout(resolve,t));
    const step=Math.max(240,Math.floor(window.innerHeight*0.74));
    for(let y=0;y<document.documentElement.scrollHeight;y+=step){
      window.scrollTo(0,y);
      await delay(45);
    }
    window.scrollTo(0,0);
    await delay(820);
  });
}
page.on("pageerror",err=>errors.push(String(err)));
page.on("console",msg=>{if(msg.type()==="error")errors.push(msg.text());});
try{
  const res=await page.goto("http://127.0.0.1:8765/lab.html",{waitUntil:"networkidle"});
  assert.equal(res.status(),200,"homepage HTTP status");
  await page.locator("#model-brier").waitFor({state:"visible"});
  await page.waitForFunction(()=>document.getElementById("model-brier").textContent.includes("."));
  assert.ok((await page.locator("#map [data-cell]").count())>100,"rendered raster map");
  assert.ok((await page.locator('[data-topo-zone="map"] .living-grid-isoline').count())>8,"map should have D3-generated topography");
  assert.equal(await page.locator('[data-topo-zone="map"] .living-grid-svg').evaluate(el=>getComputedStyle(el).pointerEvents),"none","decorative contours may not intercept map clicks");
  assert.ok((await page.locator("#history-chart polyline").count())>=1,"time series");
  assert.equal(await page.locator('[data-organic-pattern] > .organic-pattern-svg').count(),4,"lab white sections should all have ornament");
  assert.ok(await page.locator('[data-organic-pattern="analysis"] .organic-ribbon').count()>=6,"lab analysis needs long tapered paths");
  assert.match(await page.locator("#provenance-title").textContent(),/اصطناعية/);
  await page.locator('[data-layer="forecast"]').click();
  assert.equal(await page.locator('[data-layer="forecast"]').getAttribute("aria-pressed"),"true");
  await page.locator("#stress").evaluate(e=>{e.value="60";e.dispatchEvent(new Event("input",{bubbles:true}));});
  assert.match(await page.locator("#stress-value").textContent(),/60%/);
  await page.locator("#budget").evaluate(e=>{e.value="4";e.dispatchEvent(new Event("input",{bubbles:true}));});
  await page.locator("#map [data-cell]").first().click();
  assert.match(await page.locator("#cell-details").textContent(),/الصف/);
  await mkdir("artifacts",{recursive:true});
  await exposeAllSections(page);
  await page.screenshot({path:"artifacts/marshpulse-desktop.png",fullPage:true});
  const [sample]=await Promise.all([page.waitForEvent("download"),page.locator("#csv-example").click()]);
  const samplePath="artifacts/format-sample.csv";
  await sample.saveAs(samplePath);
  const sampleText=await readFile(samplePath,"utf8");
  assert.match(sampleText,/date,row,col,water/);
  await page.locator("#data-upload").setInputFiles(samplePath);
  await page.waitForFunction(()=>document.getElementById("provenance-title").textContent.includes("مستوردة"));
  assert.match(await page.locator("#data-pill").textContent(),/UNVERIFIED/);
  const [out]=await Promise.all([page.waitForEvent("download"),page.locator("#export-report").click()]);
  const outFile="artifacts/exported-evidence.json";
  await out.saveAs(outFile);
  const json=JSON.parse(await readFile(outFile,"utf8"));
  assert.equal(json.dataset.origin,"imported_unverified");
  assert.equal(json.dataset.verified,false);
  assert.ok(json.training.holdoutSamples>0);
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:"artifacts/marshpulse-mobile.png",fullPage:true});
  // Validate route boundaries and the actual custom-model journey.
  await page.goto("http://127.0.0.1:8765/",{waitUntil:"networkidle"});
  assert.match(await page.locator("h1").textContent(),/تتغيّر/);
  assert.equal(await page.locator('.path-grid .path').count(),3);
  await page.setViewportSize({width:1440,height:950});
  // Real visual assets are essential for this design, not decorative placeholders.
  for(const img of await page.locator(".botanical-home img").all()){
    await img.scrollIntoViewIfNeeded();
    await img.evaluate(el=>{el.loading="eager";});
    const loaded=await img.evaluate(async el=>{
      try { await el.decode(); } catch(_) {}
      return {loaded:el.complete&&el.naturalWidth>0,src:el.currentSrc};
    });
    assert.ok(loaded.loaded,"Broken botanical image: "+loaded.src);
  }
    // Protect the new design tokens from regressions: real CSS must load and have
  // visible atmospheric grid, image elevation and distinctly colored cards.
  const appearance=await page.evaluate(()=>{
    const g=el=>getComputedStyle(el);
    const hero=document.querySelector(".flora-hero");
    const photo=document.querySelector(".flora-main-photo");
    const cards=[...document.querySelectorAll(".flora-path")];
    return {
      stylesheet:!!document.querySelector('link[href="./visual-effects.css"]'),
      livingStyle:!!document.querySelector('link[href="./living-grid.css"]'),
      heroContours:hero.querySelectorAll(".living-grid-isoline").length,
      heroDots:hero.querySelectorAll(".living-grid-dot").length,
      pathsContours:document.querySelectorAll('[data-topo-zone="paths"] .living-grid-isoline').length,
      behindText:getComputedStyle(hero.querySelector(".living-grid-svg")).pointerEvents,
      photoShadow:g(photo).boxShadow,
      colors:cards.map(c=>g(c).backgroundImage),
      glow:g(document.querySelector(".flora-stage-glow")).backgroundImage,
      story:g(document.querySelector(".flora-story")).backgroundImage
    };
  });
  assert.equal(appearance.stylesheet,true,"visual system must be linked");
  assert.equal(appearance.livingStyle,true,"topographic stylesheet must load");
  assert.equal(await page.locator('[data-organic-pattern] > .organic-pattern-svg').count(),4,"four white home sections require original river pattern");
  assert.ok(await page.locator('.organic-ribbon').count()>45,"water-inspired contours should be distributed across the home");
  assert.ok(await page.locator('[data-organic-pattern="hero"] .organic-ribbon').count()>=10);
  assert.equal(await page.locator('.flora-hero > .organic-pattern-svg').evaluate(el=>getComputedStyle(el).pointerEvents),"none","pattern must not intercept navigation");
  assert.ok(await page.locator('[data-mf-animation]').count()>=7,"sections require actual MotionFlow reveal bindings");
  assert.ok(await page.locator('.mf-init').count()>=4,"vendored MotionFlow should initialize in Chromium");
  assert.ok(appearance.heroContours>8,"must generate nontrivial contour geometries");
  assert.ok(appearance.pathsContours>4,"chapter background should feature living contour lines");
  assert.ok(appearance.heroDots>8,"decorative coordinate dots must render");
  assert.equal(appearance.behindText,"none","topography must not block readable or interactive content");
  assert.notEqual(appearance.photoShadow,"none","hero photography must have depth");
  assert.equal(new Set(appearance.colors).size,3,"feature cards must use three distinct palettes");
  assert.match(appearance.glow,/gradient/,"photo lighting is absent");
  assert.match(appearance.story,/gradient/,"story contrast is absent");
  await exposeAllSections(page);
  assert.ok(await page.locator(".mf-animate").count()>=4,"MotionFlow must reveal content after scrolling");
  await page.screenshot({path:"artifacts/marshpulse-home-desktop.png",fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:"artifacts/marshpulse-home-mobile.png",fullPage:true});
  await page.goto("http://127.0.0.1:8765/model.html",{waitUntil:"networkidle"});
  assert.match(await page.locator("h1").textContent(),/MarshNet/);
  assert.equal(await page.locator('[data-organic-pattern] > .organic-pattern-svg').count(),2,"model reading areas need pattern");
  await page.locator("#epochs").selectOption("15");
  await page.locator("#train-model").click();
  await page.waitForFunction(()=>!document.getElementById("training-results").hidden,{timeout:60000});
  assert.equal(await page.locator("#download-weights").isDisabled(),false);
  assert.ok(Number(await page.locator("#net-brier").textContent())>=0);
  await page.setViewportSize({width:1440,height:950});
  await exposeAllSections(page);
  await page.screenshot({path:"artifacts/marshpulse-model-desktop.png",fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:"artifacts/marshpulse-model.png",fullPage:true});
  const [trainedFile]=await Promise.all([page.waitForEvent("download"),page.locator("#download-weights").click()]);
  const trainedPath="artifacts/trained-marshnet-synthetic.json";
  await trainedFile.saveAs(trainedPath);
  const trainedJSON=JSON.parse(await readFile(trainedPath,"utf8"));
  assert.equal(trainedJSON.format,"marshnet-v1");
  assert.equal(trainedJSON.provenance.origin,"synthetic");
  await page.goto("http://127.0.0.1:8765/lab.html",{waitUntil:"networkidle"});
  await page.locator("#marshnet-upload").setInputFiles(trainedPath);
  await page.waitForFunction(()=>document.getElementById("active-model").textContent.includes("MarshNet"));
  assert.match(await page.locator("#active-model").textContent(),/MarshNet/);
  const [modelEvidence]=await Promise.all([page.waitForEvent("download"),page.locator("#export-report").click()]);
  await modelEvidence.saveAs("artifacts/marshnet-in-lab-evidence.json");
  const loadedReport=JSON.parse(await readFile("artifacts/marshnet-in-lab-evidence.json","utf8"));
  assert.match(loadedReport.predictor,/MarshNet/);
    await page.goto("http://127.0.0.1:8765/methods.html",{waitUntil:"networkidle"});
  assert.equal(await page.locator(".timeline li").count(),5);
  assert.equal(await page.locator('[data-organic-pattern] > .organic-pattern-svg').count(),3,"methods has three background panels");
  await exposeAllSections(page);
  await page.screenshot({path:"artifacts/marshpulse-methods-mobile.png",fullPage:true});
    // Reflow audit at 320 CSS px; horizontal scrolling is allowed inside specific data
  // tables/controls, but not across the document viewport.
  for(const route of ["/","/lab.html","/model.html","/methods.html"]){
    await page.setViewportSize({width:320,height:700});
    await page.goto("http://127.0.0.1:8765"+route,{waitUntil:"networkidle"});
    const widths=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:window.innerWidth}));
    assert.ok(widths.scroll<=widths.viewport+1,"Unexpected horizontal overflow on "+route+": "+JSON.stringify(widths));
  }
  assert.equal(errors.length,0,"browser console errors: "+errors.join(" | "));
  console.log("BROWSER_SMOKE_SUCCESS: 4 routes, desktop/mobile, CSV, MarshNet train/export/reimport, model-driven scenario and evidence verified");
}finally{await browser.close();}
