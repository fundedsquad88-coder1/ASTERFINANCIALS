import Fastify from 'fastify';
import { createRequestId } from './production-guard';

const app = Fastify({ logger: true, requestIdHeader: 'x-request-id', genReqId: () => createRequestId() });

app.addHook('onRequest', async (request, reply) => {
  reply.header('x-request-id', request.id);
  reply.header('cache-control', 'no-store');
});

app.get('/health', async () => ({
  ok: true,
  service: 'aster-financials-api',
  environment: process.env.NODE_ENV ?? 'development',
  timestamp: new Date().toISOString()
}));

export default app;
