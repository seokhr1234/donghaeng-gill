import {cp,rm,mkdir,readFile,writeFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {build} from 'esbuild';
const mobile=fileURLToPath(new URL('../',import.meta.url)),project=path.resolve(mobile,'../..'),source=path.join(project,'donghaeng-nav/dist'),out=path.join(mobile,'www');
await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});await cp(source,out,{recursive:true});
async function removeGzip(dir){for(const e of await readdir(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())await removeGzip(p);else if(e.name.endsWith('.gz'))await rm(p)}}
await removeGzip(out);
await writeFile(path.join(out,'build-profile.js'),"globalThis.DONGHAENG_BUILD=Object.freeze({target:'android-demo',transitEnabled:true});\n");
for(const name of ['index.html','expansion.html']){let html=(await readFile(path.join(out,name),'utf8')).replace(/ data-compressed-src="[^"]+"/g,'');html=html.replace('<script src="build-profile.js"></script>','<script src="build-profile.js"></script><script src="native-runtime.js"></script>');await writeFile(path.join(out,name),html)}
await build({entryPoints:[path.join(mobile,'src/runtime.js')],bundle:true,format:'iife',platform:'browser',target:'chrome100',outfile:path.join(out,'native-runtime.js'),plugins:[{name:'android-shared-services',setup(b){
 b.onResolve({filter:/city-walk\/router\.mjs$/},()=>({path:path.join(mobile,'src/city-backend.js')}));
 b.onResolve({filter:/^node:crypto$/},()=>({path:path.join(mobile,'src/hash.js')}));
}}]});
console.log('Android assets generated from shared source; native-only key, no key in HTML/JS');
