import {readFile,writeFile,mkdir,rm,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {zipSync} from 'fflate';

const here=dirname(fileURLToPath(import.meta.url));
const kit=join(here,'../mechanical/cad-rebuild');
const site=join(here,'site');
const sourceParameters=JSON.parse(await readFile(join(kit,'source/parameters.json'),'utf8'));
const names=['front','button-cap','back-dual-knockouts','back-lower-open','back-upper-open','stand'];
const models={};
for(const name of names){
  const raw=await readFile(join(kit,'STL',`${name}.stl`));
  const faces=raw.readUInt32LE(80);
  if(raw.length!==84+faces*50)throw new Error(`Invalid binary STL: ${name}`);
  const positions=[];
  for(let face=0;face<faces;face++)for(let v=0;v<9;v++)positions.push(raw.readFloatLE(84+face*50+12+v*4));
  models[name]={positions,triangles:faces};
}
await writeFile(join(here,'model-data.js'),`export const MODELS=${JSON.stringify(models)};\nexport const BASE_PARAMETERS=${JSON.stringify(sourceParameters)};\n`);
const bundle=await build({entryPoints:[join(here,'app.js')],bundle:true,write:false,minify:true,format:'iife',target:'es2022',legalComments:'inline'});
const css=await readFile(join(here,'workbench.css'),'utf8');
const template=await readFile(join(here,'template.html'),'utf8');
if(!template.includes('<!-- WORKBENCH_CSS -->')||!template.includes('<!-- WORKBENCH_JS -->'))throw new Error('Missing template markers');
const script=bundle.outputFiles[0].text.replaceAll('</script','<\\/script');
const html=template.replace('<!-- WORKBENCH_CSS -->',`<style>${css}</style>`).replace('<!-- WORKBENCH_JS -->',`<script>${script}</script>`);
await writeFile(join(here,'oled-maker-workbench.html'),html);
await rm(site,{recursive:true,force:true});
await mkdir(join(site,'cad-v3'),{recursive:true});
await writeFile(join(site,'index.html'),html);
const manifest=await readFile(join(kit,'SHA256SUMS.txt'),'utf8');
const kitFiles=manifest.trim().split('\n').map(line=>{
  const separator=line.indexOf('  ');
  return {hash:line.slice(0,separator),name:line.slice(separator+2)};
});
for(const {hash,name} of kitFiles){
  const bytes=await readFile(join(kit,name));
  if(createHash('sha256').update(bytes).digest('hex')!==hash)throw new Error(`CAD payload changed: ${name}`);
  const dest=join(site,'cad-v3',name);
  await mkdir(dirname(dest),{recursive:true});
  await writeFile(dest,bytes);
}
for(const name of ['SHA256SUMS.txt','OLED-case-CAD-v3-public.zip','OLED-case-CAD-v3-public.zip.sha256'])await copyFile(join(kit,name),join(site,'cad-v3',name));
await copyFile(join(here,'../case-playground/oled-case-playground.html'),join(site,'classic.html'));
await copyFile(join(here,'../case-playground/oled-case-workshop.zip'),join(site,'oled-case-workshop.zip'));
await copyFile(join(here,'../case-playground/THIRD-PARTY-NOTICES.txt'),join(site,'THIRD-PARTY-NOTICES.txt'));
await copyFile(join(here,'../LICENSE'),join(site,'LICENSE'));
await copyFile(join(here,'README.md'),join(site,'README.md'));
const offline={'index.html':new Uint8Array(Buffer.from(html)), 'README.md':new Uint8Array(await readFile(join(here,'README.md'))), 'classic.html':new Uint8Array(await readFile(join(site,'classic.html'))), 'oled-case-workshop.zip':new Uint8Array(await readFile(join(site,'oled-case-workshop.zip'))), 'THIRD-PARTY-NOTICES.txt':new Uint8Array(await readFile(join(site,'THIRD-PARTY-NOTICES.txt'))), 'LICENSE':new Uint8Array(await readFile(join(site,'LICENSE')))};
for(const {name} of kitFiles)offline[`cad-v3/${name}`]=new Uint8Array(await readFile(join(site,'cad-v3',name)));
for(const name of ['SHA256SUMS.txt','OLED-case-CAD-v3-public.zip','OLED-case-CAD-v3-public.zip.sha256'])offline[`cad-v3/${name}`]=new Uint8Array(await readFile(join(site,'cad-v3',name)));
const zip=zipSync(offline,{level:9});
await writeFile(join(here,'oled-maker-workbench.zip'),zip);
await writeFile(join(site,'oled-maker-workbench.zip'),zip);
console.log(JSON.stringify({htmlBytes:Buffer.byteLength(html),offlineBytes:zip.length,models:Object.fromEntries(names.map(n=>[n,models[n].triangles])),classicPreserved:true,assets:kitFiles.length+3}));
