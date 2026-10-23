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
  // Floating dock uses actual MIT Headroom and Gumshoe, not decorative markup.
  assert.equal(await page.locator("#marsh-floating-nav").count(),1,"single site-wide floating dock");
  assert.equal(await page.locator(".floating-dock__page").count(),4,"all four destinations are accessible");
  assert.equal(await page.locator(".floating-dock__chapters a").count(),5,"home chapter navigation should be complete");
  assert.equal(await page.locator(".floating-dock__page[aria-current=page]").getAttribute("href"),"./index.html");
  assert.equal(await page.locator("#marsh-floating-nav").evaluate(el=>getComputedStyle(el).visibility),"hidden","dock must not obstruct initial hero");
  await page.evaluate(()=>window.scrollTo(0,1400));
  await page.waitForTimeout(280);
  await page.evaluate(()=>window.scrollBy(0,-280));
  await page.waitForTimeout(420);
  const dockState=await page.locator("#marsh-floating-nav").evaluate(el=>({
    eligible:el.classList.contains("is-available"),
    pinned:el.classList.contains("headroom--pinned"),
    visible:getComputedStyle(el).visibility,
    tracked:Boolean(el.__marshSpy),
    progress:el.style.getPropertyValue("--dock-progress"),
    activeSections:el.querySelectorAll(".floating-dock__chapter.active").length
  }));
  assert.equal(dockState.eligible,true,"floating bar should become available after scrolling");
  assert.equal(dockState.pinned,true,"Headroom must reveal bar on scrolling upward");
  assert.equal(dockState.visible,"visible","floating navigation must actually appear");
  assert.equal(dockState.tracked,true,"Gumshoe must activate section tracking");
  assert.ok(parseInt(dockState.progress,10)>0,"scroll reading indicator should advance");
  assert.ok(dockState.activeSections>=1,"currently viewed chapter should be highlighted");
  await page.screenshot({path:"artifacts/marshpulse-floating-desktop.png",fullPage:false});
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.waitForTimeout(180);
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
  const depth=await page.evaluate(()=>{
    const scenes=[...document.querySelectorAll("[data-botanical-tilt]")];
    return {
      lib:!!document.querySelector('link[href="./vendor/atropos/atropos.css"]'),
      main:scenes.length,
      depths:scenes.map(s=>new Set([...s.querySelectorAll("[data-atropos-offset]")].map(el=>el.getAttribute("data-atropos-offset"))).size),
      initialized:scenes.map(s=>Boolean(s.__marshAtropos)),
      specimen:!!document.querySelector(".marsh-specimen-card img"),
      foreground:[...document.querySelectorAll(".marsh-foreground-reeds,.marsh-story-reeds")].map(el=>({complete:el.complete,naturalWidth:el.naturalWidth})),
      heroReadable:document.querySelector(".flora-hero h1")?.textContent?.trim().length>10
    };
  });
  assert.equal(depth.lib,true,"Atropos stylesheet should be bundled locally");
  assert.equal(depth.main,2,"hero and story require separate photo dioramas");
  assert.ok(depth.depths.every(n=>n>=5),"each scene needs multiple independent depth layers");
  assert.ok(depth.initialized.every(Boolean),"real Atropos interaction must initialize");
  assert.ok(depth.specimen,"archival public-domain botanical print required");
  assert.ok(depth.foreground.every(im=>im.complete&&im.naturalWidth>0),"foreground SVG reeds must load");
  assert.ok(depth.heroReadable,"hero heading must remain visible");
  // The new interaction must do more than initialize a library: a real pointer
  // entering the stage should activate Atropos. Scrolling/clicking must remain normal.
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.waitForTimeout(120);
  const heroScene=page.locator(".marsh-hero-scene");
  const rect=await heroScene.boundingBox();
  assert.ok(rect&&rect.width>150&&rect.height>200,"photo scene needs visible stage dimensions");
  await page.mouse.move(rect.x+rect.width*.72,rect.y+rect.height*.32);
  await page.waitForTimeout(200);
  const activated=await heroScene.evaluate(el=>!!el.__marshAtropos?.isActive);
  assert.equal(activated,true,"3D scene must react to real desktop pointer");
  await page.mouse.move(0,0);

    assert.equal(appearance.stylesheet,true,"visual system must be linked");
  assert.equal(appearance.livingStyle,true,"topographic stylesheet must load");
  assert.equal(await page.locator('[data-organic-pattern] > .organic-pattern-svg').count(),4,"four white home sections require original river pattern");
  assert.ok(await page.locator('.organic-ribbon').count()>45,"water-inspired contours should be distributed across the home");
  assert.ok(await page.locator('[data-organic-pattern="hero"] .organic-ribbon').count()>=10);
  assert.equal(await page.locator('.flora-hero > .organic-pattern-svg').evaluate(el=>getComputedStyle(el).pointerEvents),"none","pattern must not intercept navigation");
  assert.ok(await page.locator('[data-mf-animation]').count()>=7,"sections require actual MotionFlow reveal bindings");
  assert.ok(await page.locator('.mf-init').count()>=4,"vendored MotionFlow should initialize in Chromium");
  assert.equal(await page.locator(".flora-bottom-grid h2").evaluate(el=>getComputedStyle(el).opacity),"1","final call-to-action must be readable without scrolling");
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
  assert.equal(await page.locator(".floating-dock__page").count(),4);
  const bottomDock=await page.locator("#marsh-floating-nav").evaluate(el=>({
    pos:getComputedStyle(el).position,bottom:getComputedStyle(el).bottom,
    width:el.getBoundingClientRect().width
  }));
  assert.equal(bottomDock.pos,"fixed");
  assert.ok(bottomDock.width<=390,"mobile dock must not overflow");
  await page.evaluate(()=>window.scrollTo(0,1250));
  await page.waitForTimeout(180);
  await page.evaluate(()=>window.scrollBy(0,-230));
  await page.waitForTimeout(430);
  assert.equal(await page.locator("#marsh-floating-nav").evaluate(el=>getComputedStyle(el).visibility),"visible","mobile floating dock must appear when scrolling up");
  await page.screenshot({path:"artifacts/marshpulse-floating-mobile.png",fullPage:false});
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.waitForTimeout(120);
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
    await page.setViewportSize({width:1440,height:950});
    await page.goto("http://127.0.0.1:8765/methods.html",{waitUntil:"networkidle"});
    await exposeAllSections(page);
    await page.screenshot({path:"artifacts/marshpulse-methods-desktop.png",fullPage:true});
    await page.setViewportSize({width:390,height:844});
  assert.equal(await page.locator(".timeline li").count(),5);
  assert.equal(await page.locator('[data-organic-pattern] > .organic-pattern-svg').count(),3,"methods has three background panels");
  await exposeAllSections(page);
  await page.screenshot({path:"artifacts/marshpulse-methods-mobile.png",fullPage:true});
    // Real Sentinel-2 record is genuinely loaded from tracked observational JSON.
  // It must never silently substitute the synthetic laboratory grid.
  await page.setViewportSize({width:1440,height:950});
  await page.goto("http://127.0.0.1:8765/monitor.html",{waitUntil:"networkidle"});
  await page.waitForFunction(()=>document.querySelector("#monitor-load-status")?.classList.contains("real-monitor-loaded"));
  assert.equal(await page.locator("#monitor-data-rows tr").count(),36,"genuine 36-month image record must load");
  assert.equal(await page.locator("#monitor-month").isDisabled(),false);
  assert.match(await page.locator("#monitor-date").textContent(),/2026-09/);
  assert.ok(await page.locator("#monitor-chart svg path").count()>=2,"actual SVG chart is not rendered");
  await page.locator("#monitor-month").evaluate(el=>{el.value="5";el.dispatchEvent(new Event("input",{bubbles:true}));});
  assert.equal(await page.locator("#monitor-date").textContent(),"2024-03","changing month should update actual observation");
  await page.screenshot({path:"artifacts/marshpulse-monitor-real-desktop.png",fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:"artifacts/marshpulse-monitor-real-mobile.png",fullPage:true});
  // Reflow audit at 320 CSS px; horizontal scrolling is allowed inside specific data
  // tables/controls, but not across the document viewport.
  for(const route of ["/","/lab.html","/model.html","/methods.html","/monitor.html"]){
    await page.setViewportSize({width:320,height:700});
    await page.goto("http://127.0.0.1:8765"+route,{waitUntil:"networkidle"});
    const widths=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:window.innerWidth}));
    assert.ok(widths.scroll<=widths.viewport+1,"Unexpected horizontal overflow on "+route+": "+JSON.stringify(widths));
  }
  assert.equal(errors.length,0,"browser console errors: "+errors.join(" | "));
  console.log("BROWSER_SMOKE_SUCCESS: 4 routes, desktop/mobile, CSV, MarshNet train/export/reimport, model-driven scenario and evidence verified");
}finally{await browser.close();}
