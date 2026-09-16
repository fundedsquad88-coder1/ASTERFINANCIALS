import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';

const app = Fastify({ logger: true });

async function main() {
  await app.register(helmet);
  await app.register(cors, { origin: false });

  app.get('/health', async () => ({
    ok: true,
    service: 'aster-financials-api',
    environment: process.env.NODE_ENV ?? 'development',
    timestamp: new Date().toISOString()
  }));

  app.get('/api/v1/system/status', async () => ({
    api: 'online',
    trading: 'sandbox',
    blockchain: 'sandbox',
    message: 'Production integrations are intentionally disabled in this foundation.'
  }));

  await app.listen({ host: '0.0.0.0', port: Number(process.env.PORT ?? 3000) });
}

main().catch((error) => {
  app.log.error(error);
  process.exit(1);
});
