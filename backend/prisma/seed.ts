import { PrismaClient } from '@prisma/client';

const db = new PrismaClient();

async function main() {
  const usdt = await db.asset.upsert({
    where: { symbol: 'USDT' },
    update: { decimals: 6 },
    create: { symbol: 'USDT', decimals: 6 },
  });

  console.log(`Seeded asset ${usdt.symbol} (${usdt.id})`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await db.$disconnect();
  });
