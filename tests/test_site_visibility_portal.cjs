'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('backend/site_visibility.py','utf8').match(/SCRIPT=r'''([\s\S]*?)'''/)[1];
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
 let release;const waiting=new Promise(r=>release=r),calls=[];
 const nodes={login:{hidden:false},control:{hidden:true},status:{},current:{},logout:{}};
 const radios={true:{checked:false},false:{checked:false}};
 const context={document:{getElementById:id=>nodes[id],querySelector:s=>radios[s.includes('value=true')?'true':'false']},fetch:async(url,options)=>{calls.push({url,options});if(url.endsWith('/session'))return {ok:true,json:async()=>({authenticated:true,csrf:'test-csrf'})};return waiting;},console,confirm:()=>true,FormData:class{},};
 vm.runInNewContext(source,context);await tick();
 assert.equal(calls.length,2);assert.equal(nodes.control.hidden,true,'Admin controls must stay unavailable while visibility/revision is loading');
 release({ok:true,json:async()=>({visibility:{hidden:true,revision:7}})});await tick();await tick();
 assert.equal(nodes.control.hidden,false);assert.equal(radios.true.checked,true);assert.match(nodes.current.textContent,/đang ẩn/);
 console.log('PASS: recovery controls become available only after the current visibility/revision has loaded');
})().catch(e=>{console.error(e);process.exitCode=1;});
