import {readFile,writeFile} from 'node:fs/promises';
import {zipSync} from 'fflate';

// Explicit inventory excludes dependencies, local test evidence and private state.
const names=[
  '.gitignore','README.md','LICENSE','THIRD-PARTY-NOTICES.txt',
  'package.json','package-lock.json','build.mjs','package-workshop.mjs',
  'app.js','geometry.js','linked-controls.js','worker.js','template.html',
  'test-geometry.mjs','test-linked-controls.mjs','test-dimension-feedback.mjs','verify-browser.mjs',
  'extract-zip-reference.py','oled-case-playground.html',
  'starter-snap-print-set.zip','starter-zip-face-print-set.zip',
  'reference/screeen1.stl','reference/source-meshes.json',
  'reference/096+4btn+-+bat_stls.zip','reference/zip-meshes.json'
];
const files=Object.fromEntries(await Promise.all(names.map(async name=>[name,new Uint8Array(await readFile(new URL(name,import.meta.url)))])));
const bytes=zipSync(files,{level:9});
await writeFile(new URL('oled-case-workshop.zip',import.meta.url),bytes);
console.log(`Packaged ${names.length} files; ${bytes.length.toLocaleString()} bytes.`);
