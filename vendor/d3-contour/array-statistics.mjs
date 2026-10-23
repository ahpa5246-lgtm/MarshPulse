// Minimal numeric helpers for vendored d3-contour.
// The original d3-contour source uses d3-array; our actual deployment passes
// explicit array thresholds, so no default tick generation is exercised.
// These helpers retain a sane default for other / local use.
export function extent(values, valueOf = x=>x) {
  let low=Infinity,high=-Infinity;
  for (const value of values) {
    const n=+valueOf(value);
    if(Number.isFinite(n)){if(n<low)low=n;if(n>high)high=n;}
  }
  return low===Infinity?[undefined,undefined]:[low,high];
}
export function thresholdSturges(values) {
  let count=0;for(const value of values)if(Number.isFinite(+value))count++;
  return Math.max(1,Math.ceil(Math.log2(count)+1));
}
export function ticks(start,stop,count) {
  if(!Number.isFinite(start)||!Number.isFinite(stop)||count<=0)return [];
  if(start===stop)return [start];
  const reversed=stop<start;
  if(reversed)[start,stop]=[stop,start];
  const raw=(stop-start)/count;
  const power=10**Math.floor(Math.log10(raw));
  const factor=raw/power;
  const step=power*(factor>=7.5?10:factor>=3.5?5:factor>=1.5?2:1);
  const first=Math.ceil(start/step),last=Math.floor(stop/step),out=[];
  for(let i=first;i<=last&&out.length<512;i++)out.push(+((i*step).toPrecision(12)));
  return reversed?out.reverse():out;
}
export function nice(start,stop,count) {
  const arr=ticks(start,stop,count);
  if(arr.length<2)return [start,stop];
  const step=Math.abs(arr[1]-arr[0]);
  return [Math.floor(start/step)*step,Math.ceil(stop/step)*step];
}
