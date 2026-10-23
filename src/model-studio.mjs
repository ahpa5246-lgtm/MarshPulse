import {demoData,parseCSV} from "./engine.mjs";
import {fitMarshNet,validateMarshNet} from "./marshnet.mjs";
const by=id=>document.getElementById(id);
const choice=by("dataset-choice"),fileField=by("file-field"),status=by("training-status");
let latest=null;
function sync(){fileField.hidden=choice.value!=="csv";latest=null;by("download-weights").disabled=true;by("inspect-weights").disabled=true;by("training-results").hidden=true;status.textContent="مصدر جديد مختار. ابدأ تدريبًا جديدًا لتوليد نتائج وأوزان مرتبطة به.";}
choice.addEventListener("change",sync);
const num=n=>Number(n).toFixed(4);
by("train-model").addEventListener("click",async()=>{
  const button=by("train-model"),seed=Number(by("seed").value),epochs=Number(by("epochs").value);
  if(!Number.isInteger(seed)||seed<1||seed>999999){status.textContent="البذرة يجب أن تكون عددًا صحيحًا بين 1 و999999.";return;}
  button.disabled=true;latest=null;by("download-weights").disabled=true;by("inspect-weights").disabled=true;
  try {
    let dataset=demoData();
    if(choice.value==="csv"){
      const f=by("training-csv").files?.[0];
      if(!f)throw Error("اختاري ملف CSV أولًا.");
      if(f.size>9e6)throw Error("الملف أكبر من 9 ميغابايت.");
      dataset=parseCSV(await f.text());
    }
    status.textContent="يجري تحضير البيانات وتوحيد السمات اعتمادًا على فترة التدريب فقط…";
    await new Promise(resolve=>setTimeout(resolve,20));
    const model=await fitMarshNet(dataset,{seed,epochs,reportProgress:p=>{
      status.textContent="التدريب: الدورة "+p.epoch+" / "+epochs+" | خطأ التحقق "+p.validationBrier.toFixed(4);
    }});
    validateMarshNet(model);latest=model;
    const net=model.evaluation.model,base=model.evaluation.persistence;
    by("net-brier").textContent=num(net.brier);
    by("base-brier").textContent=num(base.brier);
    by("net-f1").textContent=num(net.f1);
    by("base-f1").textContent=num(base.f1);
    by("model-summary").textContent=(net.brier<base.brier?"تفوّق MarshNet على مرجع الاستمرار في مجموعة الاختبار لهذا الملف.":"لم يتفوّق MarshNet على مرجع الاستمرار. هذا فشل يجب توثيقه، وليس نتيجة إيجابية.")+
      " أفضل دورة: "+model.training.bestEpoch+" من أصل "+model.training.completedEpochs+"؛ اختُبرت "+model.training.holdoutSamples+" عينة بين "+model.training.holdoutStart+" و"+model.training.holdoutEnd+".";
    by("source-summary").textContent="المصدر: "+dataset.name+" | الحالة: "+(dataset.origin==="synthetic"?"اصطناعي بالكامل — ليس قياسات العراق":"مستورد ولم يتحقق من مصداقيته مستقلًا")+".";
    by("training-results").hidden=false;
    by("download-weights").disabled=false;by("inspect-weights").disabled=false;
    status.textContent="اكتمل التدريب والتقييم. الأوزان جاهزة للتصدير؛ النتائج ليست إثباتًا ميدانيًا.";
  }catch(error){status.textContent="لم يكتمل التدريب: "+error.message;}
  finally{button.disabled=false;}
});
by("download-weights").addEventListener("click",()=>{
  if(!latest)return;
  const blob=new Blob([JSON.stringify(latest,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="marshnet-"+latest.provenance.lastMonth+".json";document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
by("inspect-weights").addEventListener("click",()=>{
  if(!latest)return;
  status.textContent="معمارية: "+latest.architecture.input+" مدخلات ← "+latest.architecture.hidden+" وحدة مخفية ← "+latest.architecture.output+
    " خرج | أوزان: "+(latest.weights.W1.length+latest.weights.W2.length+latest.weights.b1.length+1)+" | تاريخ اختبار: "+latest.training.holdoutStart+" إلى "+latest.training.holdoutEnd+".";
});
