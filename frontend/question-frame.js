/* Presentation contract v1. Controllers keep raw submit values and server authority. */
(function(global){'use strict';
 const view=global.SolutionView||(typeof require==='function'?require('./solution-view.js'):null);
 const providers=new Set(['main','pilot','trial']);
 function doing(raw={},options={}){
  const provider=providers.has(options.provider)?options.provider:'main';
  const mode=raw.responseMode||options.responseMode||(raw.options?.length?'choice':'typed');
  const choices=(Array.isArray(raw.options)?raw.options:[]).map((option,index)=>{
   const object=option&&typeof option==='object';
   const value=provider==='trial'&&object?(option.id??option.value??index):option;
   const text=object?String(option.text||option.label||''):String(option);
   return Object.freeze({key:String(raw.id??raw.contentKey??'question')+':'+index,submitValue:value,text,label:String.fromCharCode(65+index)});
  });
  const prompt=Array.isArray(raw.prompt)?raw.prompt:null;
  // Only fields needed for doing a question enter this object; no answer/solution/rule.
  return Object.freeze({schemaVersion:1,provider,id:raw.id??raw.contentKey??null,revision:raw.revision??raw.versionId??null,
   stem:Object.freeze({blocks:prompt,text:typeof raw.prompt==='string'?raw.prompt:String(raw.text??'')}),
   response:Object.freeze({mode:mode==='choice'?'choice':'typed',kind:raw.answerKind||'auto',guide:raw.inputGuide||null,unit:raw.unit||'',choices:Object.freeze(choices)}),
   diagram:raw.sampleDiagram||null});
 }
 function choices(raw,options={}){return doing(raw,options).response.choices;}
 function prompt(raw,options={}){
  const model=doing(raw,options),tag=['p','h2','h3'].includes(options.tag)?options.tag:'h2';
  const text=options.renderText?options.renderText(model.stem.text):options.multiline?view.escape(model.stem.text).replace(/\n/g,'<br>'):view.text(model.stem.text);
  const attrs=(options.id?' id="'+view.escape(options.id)+'"':'')+(options.className?' class="'+view.escape(options.className)+'"':'')+(options.tabIndex!==undefined?' tabindex="'+Number(options.tabIndex)+'"':'');
  const body=model.stem.blocks&&options.renderBlocks?options.renderBlocks(model.stem.blocks):`<${tag}${attrs}>${text}</${tag}>`;
  return body+diagram({sampleDiagram:model.diagram},{className:options.diagramClass});
 }
 function diagram(raw,options={}){const html=view.sampleFigure(raw);return options.className?html.replace('class="solution-diagram-figure"','class="'+view.escape(options.className)+'"'):html;}
 function review(raw={}){
  // Only use payloads already authorized by the server. This function grants no access.
  const allowed=['answer','correct','solution','steps','thinking','keyPoint','check','extension','choiceRationales','sampleBand'];
  const result={};for(const key of allowed)if(Object.hasOwn(raw,key))result[key]=raw[key];
  return Object.freeze(result);
 }
 const api={doing,choices,prompt,diagram,review};global.QuestionFrame=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
