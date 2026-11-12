const fs=require('node:fs');
const path=require('node:path');

function getPackage(name,{modules}={}) {
 const candidates=[modules,process.env.CODEX_NODE_MODULES,
  path.resolve(path.dirname(process.execPath),'..','node_modules'),
  path.resolve(path.dirname(process.execPath),'node_modules')].filter(Boolean);
 for(const base of [...new Set(candidates)]) {
  try { return require(require.resolve(name,{paths:[base]})); } catch(error) {
   if(error.code!=='MODULE_NOT_FOUND')throw error;
  }
 }
 try { return require(name); } catch(error) {
  if(error.code!=='MODULE_NOT_FOUND')throw error;
 }
 throw new Error('Không tìm thấy '+name+'. Dùng load_workspace_dependencies rồi đặt CODEX_NODE_MODULES tới thư mục packages; không tự cài gói qua mạng.');
}

function chromePath() {
 const candidates=[process.env.CHROME_PATH,
  process.env.PROGRAMFILES&&path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe'),
  process.env['PROGRAMFILES(X86)']&&path.join(process.env['PROGRAMFILES(X86)'],'Google/Chrome/Application/chrome.exe'),
  process.env.LOCALAPPDATA&&path.join(process.env.LOCALAPPDATA,'Google/Chrome/Application/chrome.exe')].filter(Boolean);
 return candidates.find(p=>fs.existsSync(p));
}

module.exports={getPackage,chromePath};
