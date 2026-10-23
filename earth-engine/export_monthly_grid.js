// MarshPulse Earth Engine research export (Code Editor JavaScript).
// NOT run by this repository's CI. User must authenticate an eligible GEE account,
// inspect spatial boundaries, launch the Drive task, and review data validity.
// Outputs a complete time-indexed 2D cell grid in date,row,col,water format
// if all monthly cells have valid observations. Null observations must NOT be filled with 0.
//
// Official dataset: COPERNICUS/S2_SR_HARMONIZED
// Classification hypothesis: MNDWI (B3-B11)/(B3+B11) > 0.10.
// Needs local threshold validation, turbidity/reed sensitivity review, and independent reference.
// Pilot rectangle is a coarse study box, NOT an authoritative mapped Iraqi marsh boundary.
var WEST=46.65, SOUTH=30.72, EAST=47.25, NORTH=31.15;
var COLS=18, ROWS=13;
var START='2022-01-01', MONTHS=36, THRESHOLD=0.10;
var roi=ee.Geometry.Rectangle([WEST,SOUTH,EAST,NORTH],null,false);
var width=(EAST-WEST)/COLS,height=(NORTH-SOUTH)/ROWS;
var grid=ee.FeatureCollection(
  ee.List.sequence(0,ROWS-1).map(function(r){
    r=ee.Number(r);
    return ee.List.sequence(0,COLS-1).map(function(c){
      c=ee.Number(c);
      var left=ee.Number(WEST).add(c.multiply(width));
      var bottom=ee.Number(NORTH).subtract(r.add(1).multiply(height));
      var cell=ee.Geometry.Rectangle([left,bottom,left.add(width),bottom.add(height)],null,false);
      return ee.Feature(cell,{row:r,col:c});
    });
  }).flatten()
);
var sentinel=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(roi)
  .filterDate(START,ee.Date(START).advance(MONTHS,'month'));
function openWater(image){
  var scl=image.select('SCL');
  var valid=scl.neq(0).and(scl.neq(1)).and(scl.neq(2))
    .and(scl.neq(3)).and(scl.neq(8)).and(scl.neq(9))
    .and(scl.neq(10)).and(scl.neq(11));
  var index=image.normalizedDifference(['B3','B11']);
  return index.gt(THRESHOLD).rename('water').updateMask(valid);
}
var empty=ee.Image.constant(0).rename('water').updateMask(ee.Image.constant(0));
var months=ee.List.sequence(0,MONTHS-1);
var tables=months.map(function(offset){
  var first=ee.Date(START).advance(ee.Number(offset),'month');
  var last=first.advance(1,'month');
  // Masked filler ensures months without valid images produce null, never fake dry cells.
  var images=sentinel.filterDate(first,last).map(openWater).merge(ee.ImageCollection([empty]));
  var monthly=images.mean().rename('water').clip(roi);
  var samples=monthly.reduceRegions({
    collection:grid,
    reducer:ee.Reducer.mean(),
    scale:30,
    tileScale:4
  });
  var date=first.format('YYYY-MM');
  return samples.map(function(feature){
    return ee.Feature(null,{
      date:date,
      row:feature.get('row'),
      col:feature.get('col'),
      water:feature.get('mean')
    });
  });
});
var results=ee.FeatureCollection(months.map(function(i){
  return ee.FeatureCollection(tables.get(i));
})).flatten();
print('Pilot ROI (not a validated marsh boundary):',roi);
print('Monthly grid rows expected:',MONTHS*ROWS*COLS);
print('Preview, including null cells requiring review:',results.limit(10));
Map.centerObject(roi,9);
Map.addLayer(roi,{color:'68d4a6'},'Pilot AOI');
Export.table.toDrive({
  collection:results,
  description:'MarshPulse_S2_MNDWI_monthly_grid_2022_2024',
  fileFormat:'CSV',
  selectors:['date','row','col','water']
});
// Run the task under the Tasks tab. Check for nulls, clouds, seasonal bias,
// AOI alignment and license. Do not call a derived grid field-validated wetland truth.
