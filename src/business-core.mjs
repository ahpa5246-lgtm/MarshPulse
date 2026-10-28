import {validateMonitor} from "./monitor-real.mjs";

export const WATER_DISCLAIMER = "مؤشر فضائي تجريبي غير محقق ميدانيًا؛ لا يمثل مساحة الأهوار الرسمية أو حجم المياه، وليس إنذارًا عامًا أو توصية تشغيلية.";
export const QUALITY_FLOOR = 0.5;

export function validateBusinessDataset(data) {
  if (!validateMonitor(data) || !Array.isArray(data.bbox) || data.bbox.length !== 4) return false;
  const [west,south,east,north] = data.bbox;
  if (![west,south,east,north].every(Number.isFinite)) return false;
  if (west < -180 || east > 180 || south < -90 || north > 90 || west >= east || south >= north) return false;
  return typeof data.imagery === "string" && data.imagery.length > 3;
}

export function normalizedOptions(rows, options = {}) {
  if (!Array.isArray(rows) || !rows.length) throw new Error("No observations");
  const months = new Set(rows.map(row => row[0]));
  const from = months.has(options.from) ? options.from : rows[0][0];
  const to = months.has(options.to) ? options.to : rows.at(-1)[0];
  if (from > to) throw new RangeError("Start month is after end month");
  const quality = Number(options.quality);
  const drop = Number(options.dropKm2);
  return {
    from, to,
    quality: Number.isFinite(quality) ? Math.min(1, Math.max(QUALITY_FLOOR, quality)) : .9,
    dropKm2: Number.isFinite(drop) ? Math.min(1000, Math.max(.001, drop)) : 5
  };
}

export function evaluatePeriod(data, requested = {}) {
  if (!validateBusinessDataset(data)) throw new Error("Invalid source record");
  const settings = normalizedOptions(data.rows, requested);
  const selected = data.rows.filter(row => row[0] >= settings.from && row[0] <= settings.to);
  const alerts = [];
  const firstIndex = data.rows.findIndex(row => row[0] === settings.from);
  for (let i = firstIndex; i < data.rows.length; i++) {
    const current = data.rows[i];
    if (current[0] > settings.to) break;
    if (current[2] < settings.quality) alerts.push({month:current[0],kind:"low_coverage",coverage:current[2]});
    if (i === 0) continue;
    const previous = data.rows[i-1];
    if (current[3] !== null && current[3] <= -settings.dropKm2 &&
        current[2] >= settings.quality && previous[2] >= settings.quality) {
      alerts.push({month:current[0],kind:"review_decrease",deltaKm2:current[3],coverage:current[2]});
    }
  }
  const first = selected[0], last = selected.at(-1);
  const areaDifferenceKm2 = Number((last[1] - first[1]).toFixed(3));
  return {
    settings, selected, alerts,
    summary: {
      records: selected.length, firstMonth:first[0], lastMonth:last[0],
      firstProxyKm2:first[1], lastProxyKm2:last[1], areaDifferenceKm2,
      percentDifference: first[1] > 0 ? Number((areaDifferenceKm2 / first[1] * 100).toFixed(1)) : null,
      meanCoverage: selected.reduce((sum,row)=>sum+row[2],0)/selected.length,
      reviewDecreases:alerts.filter(a=>a.kind==="review_decrease").length,
      lowCoverageMonths:alerts.filter(a=>a.kind==="low_coverage").length
    },
    provenance: {
      label:data.label, imagery:data.imagery, boundingBox:data.bbox,
      officialWetlandBoundary:false, sourceWorkflow:data.source_workflow || null,
      sourceArtifact:data.source_artifact || null,
      indexFormula:data.index_formula || null,
      lastObservation:data.rows.at(-1)[0]
    },
    caveat:WATER_DISCLAIMER,
    comparisonCaveat:"فرق مساحة المؤشر بين بداية الفترة ونهايتها لا يقارن البكسلات المتطابقة، وقد يتأثر بتغير التغطية الصافية. التغير الشهري في السجل الأصلي وحده محسوب على البكسلات المشتركة."
  };
}

export function reportCsv(result) {
  const rows = [["month","proxy_water_km2","clear_fraction","matched_pixel_change_km2"],
    ...result.selected.map(r=>[r[0],r[1],r[2],r[3] === null ? "" : r[3]])];
  return rows.map(row=>row.map(cell=>'"'+String(cell).replaceAll('"','""')+'"').join(",")).join("\r\n")+"\r\n";
}

export function reportJson(result, sourceKind, generatedAt) {
  return JSON.stringify({
    format:"marshpulse-business-report-v1",
    exportedAt:generatedAt,
    sourceKind,
    researchOnly:true,
    settings:result.settings,
    summary:result.summary,
    flags:result.alerts,
    provenance:result.provenance,
    disclaimer:result.caveat,
    comparisonCaveat:result.comparisonCaveat,
    observations:result.selected.map(([month,proxy,clear,matchedDelta])=>({
      month,proxyWaterKm2:proxy,clearFraction:clear,matchedPixelChangeKm2:matchedDelta
    }))
  },null,2)+"\n";
}
