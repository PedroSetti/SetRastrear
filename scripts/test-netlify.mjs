import assert from 'node:assert/strict';
import {redirects,apiOrigin} from './netlify-routing.mjs';
assert.equal(apiOrigin('https://api.example.com/'),'https://api.example.com');
assert.equal(redirects('https://api.example.com'),'/api/*  https://api.example.com/api/:splat  200!\n/*  /index.html  200\n');
for(const input of ['', 'http://api.example.com','https://user:pass@api.example.com','https://api.example.com/api','https://api.example.com/?token=x','https://api.example.com/#x'])assert.throws(()=>apiOrigin(input));
console.log('Configuração Netlify: validação de origem e prioridade de proxy aprovadas.');
