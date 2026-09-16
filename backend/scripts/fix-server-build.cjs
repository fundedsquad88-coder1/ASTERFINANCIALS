const fs = require('node:fs');
const path = require('node:path');

const file = path.join(__dirname, '..', 'src', 'server.ts');
let text = fs.readFileSync(file, 'utf8');

// Repair the four compact admin handlers whose return object currently has
// an extra closing parenthesis before the route callback.
for (const name of ['deposits', 'withdrawals', 'stakes', 'ledger']) {
  const pattern = new RegExp(`return \\{ ${name}: await ([^\\n]+?) \\}\\) \\}\\);`, 'g');
  text = text.replace(pattern, `return { ${name}: await $1 };`);
}

fs.writeFileSync(file, text);
console.log('Applied server syntax normalization for admin routes.');
