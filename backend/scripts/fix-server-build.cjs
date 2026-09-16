const fs = require('node:fs');
const path = require('node:path');

const file = path.join(__dirname, '..', 'src', 'server.ts');
let text = fs.readFileSync(file, 'utf8');

// Normalize the compact admin list-return statements produced in server.ts.
// The source currently contains an extra closing parenthesis after the return object
// for these four handlers. Normalize both the original and already-partially-fixed forms.
for (const name of ['deposits', 'withdrawals', 'stakes', 'ledger']) {
  const malformed = new RegExp(`return \\{ ${name}: await ([^\\n]+?) \\}\\) \\}\\); \\}\\);`, 'g');
  text = text.replace(malformed, `return { ${name}: await $1 }; });`);

  const normalized = new RegExp(`return \\{ ${name}: await ([^\\n]+?) \\}\\); \\}\\);`, 'g');
  text = text.replace(normalized, `return { ${name}: await $1 }; });`);
}

fs.writeFileSync(file, text);
console.log('Applied server syntax normalization for admin routes.');
