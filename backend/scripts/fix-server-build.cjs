const fs = require('node:fs');
const path = require('node:path');

const file = path.join(__dirname, '..', 'src', 'server.ts');
let text = fs.readFileSync(file, 'utf8');
const fixes = [
  [
    "return { deposits: await db.deposit.findMany({ take: 500, orderBy: { createdAt: 'desc' }, include: { user: { select: { id: true, email: true } } } }) }); });",
    "return { deposits: await db.deposit.findMany({ take: 500, orderBy: { createdAt: 'desc' }, include: { user: { select: { id: true, email: true } } } }) }; });"
  ],
  [
    "return { withdrawals: await db.withdrawal.findMany({ take: 500, orderBy: { createdAt: 'desc' }, include: { user: { select: { id: true, email: true } } } } ) }); });",
    "return { withdrawals: await db.withdrawal.findMany({ take: 500, orderBy: { createdAt: 'desc' }, include: { user: { select: { id: true, email: true } } } }); });"
  ],
  [
    "return { stakes: await db.stake.findMany({ take: 500, orderBy: { startedAt: 'desc' }, include: { user: { select: { id: true, email: true } } } }) }); });",
    "return { stakes: await db.stake.findMany({ take: 500, orderBy: { startedAt: 'desc' }, include: { user: { select: { id: true, email: true } } } }) }; });"
  ],
  [
    "return { ledger: await db.ledgerEntry.findMany({ take: 500, orderBy: { createdAt: 'desc' } }) }); });",
    "return { ledger: await db.ledgerEntry.findMany({ take: 500, orderBy: { createdAt: 'desc' } }) }; });"
  ]
];
for (const [from, to] of fixes) text = text.replace(from, to);
fs.writeFileSync(file, text);
console.log('Applied server syntax normalization before TypeScript build.');
