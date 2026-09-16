const fs = require('node:fs');
const path = require('node:path');

const file = path.join(__dirname, '..', 'src', 'server.ts');
let text = fs.readFileSync(file, 'utf8');
text = text.replace(/return \{ (deposits|withdrawals|stakes|ledger): await ([^;]+?) \}\); \}\);/g, 'return { $1: await $2 }; });');
fs.writeFileSync(file, text);
console.log('Applied server syntax normalization before TypeScript build.');
