CREATE TYPE "Network" AS ENUM ('TRC20', 'BEP20');
CREATE TYPE "CustodyTxStatus" AS ENUM ('OBSERVED', 'CONFIRMED', 'REJECTED');

ALTER TABLE "Deposit" ADD COLUMN "network" "Network", ADD COLUMN "depositAddressId" TEXT, ADD COLUMN "confirmations" INTEGER NOT NULL DEFAULT 0, ADD COLUMN "confirmedAt" TIMESTAMP(3);
ALTER TABLE "Withdrawal" ADD COLUMN "network" "Network", ADD COLUMN "approvedAt" TIMESTAMP(3), ADD COLUMN "sentAt" TIMESTAMP(3);

CREATE TABLE "DepositAddress" (
  "id" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "network" "Network" NOT NULL,
  "address" TEXT NOT NULL,
  "label" TEXT,
  "active" BOOLEAN NOT NULL DEFAULT true,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "DepositAddress_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "DepositAddress_network_address_key" ON "DepositAddress"("network", "address");
CREATE INDEX "DepositAddress_userId_network_idx" ON "DepositAddress"("userId", "network");
CREATE INDEX "DepositAddress_network_active_idx" ON "DepositAddress"("network", "active");
ALTER TABLE "DepositAddress" ADD CONSTRAINT "DepositAddress_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

CREATE TABLE "CustodyTransaction" (
  "id" TEXT NOT NULL,
  "network" "Network" NOT NULL,
  "txHash" TEXT NOT NULL,
  "asset" TEXT NOT NULL,
  "amount" DECIMAL(36,18) NOT NULL,
  "fromAddress" TEXT,
  "toAddress" TEXT NOT NULL,
  "blockNumber" BIGINT,
  "confirmations" INTEGER NOT NULL DEFAULT 0,
  "status" "CustodyTxStatus" NOT NULL DEFAULT 'OBSERVED',
  "userId" TEXT,
  "depositId" TEXT,
  "observedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "confirmedAt" TIMESTAMP(3),
  "raw" JSONB,
  CONSTRAINT "CustodyTransaction_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "CustodyTransaction_network_txHash_key" ON "CustodyTransaction"("network", "txHash");
CREATE UNIQUE INDEX "CustodyTransaction_depositId_key" ON "CustodyTransaction"("depositId");
CREATE INDEX "CustodyTransaction_network_toAddress_idx" ON "CustodyTransaction"("network", "toAddress");
CREATE INDEX "CustodyTransaction_status_idx" ON "CustodyTransaction"("status");
CREATE INDEX "CustodyTransaction_userId_idx" ON "CustodyTransaction"("userId");
ALTER TABLE "CustodyTransaction" ADD CONSTRAINT "CustodyTransaction_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "CustodyTransaction" ADD CONSTRAINT "CustodyTransaction_depositId_fkey" FOREIGN KEY ("depositId") REFERENCES "Deposit"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "Deposit" ADD CONSTRAINT "Deposit_depositAddressId_fkey" FOREIGN KEY ("depositAddressId") REFERENCES "DepositAddress"("id") ON DELETE SET NULL ON UPDATE CASCADE;
