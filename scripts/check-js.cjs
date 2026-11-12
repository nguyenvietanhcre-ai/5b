'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const files=[];
function walk(directory){
 for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
  const file=path.join(directory,entry.name);
  if(entry.isDirectory())walk(file);
  else if(/\.(?:cjs|mjs|js)$/.test(entry.name))files.push(file);
 }
}
for(const directory of ['frontend','scripts','tests','tools/mascot-animation'])if(fs.existsSync(path.join(root,directory)))walk(path.join(root,directory));
for(const file of files){
 const result=spawnSync(process.execPath,['--check',file],{encoding:'utf8'});
 if(result.status!==0){process.stderr.write(result.stderr||result.stdout||file);process.exit(result.status||1);}
}
console.log('JavaScript syntax verified: '+files.length+' files');
