import {spawnSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import {redirects} from './netlify-routing.mjs';
const rules = redirects(process.env.RMB_API_ORIGIN); // Falha antes do build se estiver incorreto.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const pnpm = process.platform === 'win32' ? 'pnpm.cmd' : 'pnpm';
function run(args) {
 const result = spawnSync(pnpm, args, {cwd:root,stdio:'inherit',env:{...process.env,VITE_HOSTED_BUILD:'true'},shell:process.platform === 'win32'});
 if (result.status !== 0) throw new Error(`Build falhou: ${result.error?.message || result.status}`);
}
run(['--dir','web','install','--frozen-lockfile']);
run(['--dir','web','run','build']);
writeFileSync(resolve(root,'web/dist/_redirects'),rules);
console.log('Painel e proxy /api preparados para Netlify.');
