import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {validateBusinessDataset,normalizedOptions,evaluatePeriod,reportCsv,reportJson} from "../src/business-core.mjs";
const file = fileURLToPath(new URL("../data/hawizeh-actual-observations.json",import.meta.url));
const sample = () => JSON.parse(readFileSync(file,"utf8"));

test("accept existing real-proxy schema and reject invalid geography / synthetic data",()=>{
  const x=sample(); assert.equal(validateBusinessDataset(x),true);
  x.bbox[0]=1000; assert.equal(validateBusinessDataset(x),false);
  const y=sample(); y.label="SYNTHETIC"; assert.equal(validateBusinessDataset(y),false);
  const z=sample(); z.bbox=null; assert.equal(validateBusinessDataset(z),false);
});

test("period comparison never claims matched-pixel or field-valid results",()=>{
  const output=evaluatePeriod(sample(),{from:"2025-01",to:"2025-07",quality:.9,dropKm2:5});
  assert.equal(output.summary.records,7);
  assert.equal(output.summary.firstProxyKm2,27.794);
  assert.equal(output.summary.lastProxyKm2,0);
  assert.equal(output.summary.areaDifferenceKm2,-27.794);
  assert.equal(output.provenance.officialWetlandBoundary,false);
  assert.match(output.comparisonCaveat,/لا يقارن البكسلات المتطابقة/);
});

test("flags require adequate coverage on both adjacent months",()=>{
  const r=evaluatePeriod(sample(),{from:"2024-06",to:"2025-07",quality:.9,dropKm2:5});
  const decrease=r.alerts.filter(a=>a.kind==="review_decrease").map(a=>a.month);
  assert.ok(decrease.includes("2024-07"));
  assert.ok(decrease.includes("2025-06"));
  assert.ok(!decrease.includes("2025-04"),"prior low coverage suppresses decline flag");
  assert.ok(r.alerts.some(a=>a.kind==="low_coverage"&&a.month==="2025-03"));
});

test("unavailable comparisons remain null and thresholds are bounded",()=>{
  const data=sample(); const r=evaluatePeriod(data,{from:"2023-10",to:"2023-11"});
  assert.equal(r.summary.percentDifference,null);
  assert.throws(()=>normalizedOptions(data.rows,{from:"2026-09",to:"2023-10"}),RangeError);
  assert.equal(normalizedOptions(data.rows,{quality:0,dropKm2:-10}).quality,.5);
  assert.equal(normalizedOptions(data.rows,{quality:0,dropKm2:-10}).dropKm2,.001);
  assert.equal(normalizedOptions(data.rows,{quality:"bad",dropKm2:"bad"}).quality,.9);
});

test("CSV and JSON export retain provenance, exact source flags, and no made-up confidence",()=>{
  const r=evaluatePeriod(sample(),{from:"2026-06",to:"2026-09"});
  const csv=reportCsv(r);
  assert.match(csv,/matched_pixel_change_km2/);
  assert.equal(csv.trim().split("\r\n").length,5);
  const parsed=JSON.parse(reportJson(r,"bundled_historical","2026-10-29T00:00:00Z"));
  assert.equal(parsed.researchOnly,true);
  assert.equal(parsed.provenance.lastObservation,"2026-09");
  assert.equal(parsed.observations.length,4);
  assert.equal(parsed.sourceKind,"bundled_historical");
  assert.ok(!("forecast" in parsed));
});
