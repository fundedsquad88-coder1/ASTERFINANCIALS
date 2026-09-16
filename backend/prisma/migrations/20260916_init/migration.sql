CREATE TYPE "LedgerDirection" AS ENUM ('DEBIT', 'CREDIT');
CREATE TYPE "TradeStatus" AS ENUM ('PENDING', 'OPEN', 'WON', 'LOST', 'CANCELLED');
CREATE TYPE "DepositStatus" AS ENUM ('PENDING', 'CONFIRMED', 'FAILED');
CREATE TYPE "WithdrawalStatus" AS ENUM ('PENDING', 'APPROVED', 'SENT', 'REJECTED');
CREATE TYPE "RewardType" AS ENUM ('REFERRAL', 'STAKING', 'TRADING', 'PROMOTION');

CREATE TABLE "User" (
  "id" TEXT NOT NULL,
  "email" TEXT NOT NULL,
  "passwordHash" TEXT NOT NULL,
  "referralCode" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");
CREATE UNIQUE INDEX "User_referralCode_key" ON "User"("referralCode");

CREATE TABLE "Referral" (
  "id" TEXT NOT NULL,
  "referrerId" TEXT NOT NULL,
  "refereeId" TEXT NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Referral_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "Referral_refereeId_key" ON "Referral"("refereeId");
CREATE INDEX "Referral_referrerId_idx" ON "Referral"("referrerId");

CREATE TABLE "Asset" (
  "id" TEXT NOT NULL,
  "symbol" TEXT NOT NULL,
  "decimals" INTEGER NOT NULL DEFAULT 6,
  CONSTRAINT "Asset_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "Asset_symbol_key" ON "Asset"("symbol");

CREATE TABLE "Wallet" (
  "id" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "assetId" TEXT NOT NULL,
  "available" DECIMAL(36,18) NOT NULL DEFAULT 0,
  "locked" DECIMAL(36,18) NOT NULL DEFAULT 0,
  CONSTRAINT "Wallet_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "Wallet_userId_assetId_key" ON "Wallet"("userId", "assetId");

CREATE TABLE "LedgerEntry" (
  "id" TEXT NOT NULL,
  "reference" TEXT NOT NULL,
  "account" TEXT NOT NULL,
  "assetSymbol" TEXT NOT NULL,
  "direction" "LedgerDirection" NOT NULL,
  "amount" DECIMAL(36,18) NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "LedgerEntry_pkey" PRIMARY KEY ("id")
);
CREATE INDEX "LedgerEntry_reference_idx" ON "LedgerEntry"("reference");
CREATE INDEX "LedgerEntry_account_assetSymbol_idx" ON "LedgerEntry"("account", "assetSymbol");

CREATE TABLE "Deposit" (
  "id" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "asset" TEXT NOT NULL,
  "amount" DECIMAL(36,18) NOT NULL,
  "txHash" TEXT,
  "status" "DepositStatus" NOT NULL DEFAULT 'PENDING',
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Deposit_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "Withdrawal" (
  "id" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "asset" TEXT NOT NULL,
  "amount" DECIMAL(36,18) NOT NULL,
  "address" TEXT NOT NULL,
  "txHash" TEXT,
  "status" "WithdrawalStatus" NOT NULL DEFAULT 'PENDING',
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Withdrawal_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "Trade" (
  "id" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "market" TEXT NOT NULL,
  "direction" TEXT NOT NULL,
  "amount" DECIMAL(36,18) NOT NULL,
  "status" "TradeStatus" NOT NULL DEFAULT 'PENDING',
  "openedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "expiresAt" TIMESTAMP(3) NOT NULL,
  "settledAt" TIMESTAMP(3),
  CONSTRAINT "Trade_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "Stake" (
  "id" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "asset" TEXT NOT NULL,
  "amount" DECIMAL(36,18) NOT NULL,
  "rateBps" INTEGER NOT NULL,
  "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "endsAt" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "Stake_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "Reward" (
  "id" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "type" "RewardType" NOT NULL,
  "amount" DECIMAL(36,18) NOT NULL,
  "asset" TEXT NOT NULL,
  "reference" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Reward_pkey" PRIMARY KEY ("id")
);

ALTER TABLE "Referral" ADD CONSTRAINT "Referral_referrerId_fkey" FOREIGN KEY ("referrerId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Referral" ADD CONSTRAINT "Referral_refereeId_fkey" FOREIGN KEY ("refereeId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Wallet" ADD CONSTRAINT "Wallet_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Wallet" ADD CONSTRAINT "Wallet_assetId_fkey" FOREIGN KEY ("assetId") REFERENCES "Asset"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Deposit" ADD CONSTRAINT "Deposit_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Withdrawal" ADD CONSTRAINT "Withdrawal_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Trade" ADD CONSTRAINT "Trade_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Stake" ADD CONSTRAINT "Stake_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Reward" ADD CONSTRAINT "Reward_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
