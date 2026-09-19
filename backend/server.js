const express = require("express");
const helmet = require("helmet");
const cors = require("cors");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { Pool } = require("pg");
const crypto = require("crypto");
const rateLimit = require("express-rate-limit");
const { signerConfigured, submitWithdrawal } = require("./treasury-signer");

const app = express();
const port = Number(process.env.PORT || 8080);
const jwtSecret = process.env.JWT_SECRET;
const databaseUrl = process.env.DATABASE_URL;
const resendApiKey = process.env.RESEND_API_KEY;
const emailFrom = process.env.EMAIL_FROM;
const appBaseUrl = process.env.APP_BASE_URL;

if (!jwtSecret || !databaseUrl || (process.env.NODE_ENV === "production" && !process.env.CORS_ORIGINS)) {
  console.error("JWT_SECRET, DATABASE_URL and production CORS_ORIGINS are required.");
  process.exit(1);
}

const pool = new Pool({
  connectionString: databaseUrl,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : false
});

app.use(helmet());
const allowedOrigins = String(process.env.CORS_ORIGINS || "").split(",").map(x => x.trim()).filter(Boolean);
app.use(cors({ origin: (origin, cb) => {
  if (!origin || allowedOrigins.includes(origin)) return cb(null, true);
  return cb(new Error("CORS_ORIGIN_NOT_ALLOWED"));
}, credentials: true }));
app.use(express.json({ limit: "32kb" }));
app.set("trust proxy", 1);
const authLimiter = rateLimit({ windowMs: 15 * 60 * 1000, limit: 30, standardHeaders: "draft-8", legacyHeaders: false });
const sensitiveLimiter = rateLimit({ windowMs: 15 * 60 * 1000, limit: 10, standardHeaders: "draft-8", legacyHeaders: false });
app.use((req,res,next)=>{ req.requestId=crypto.randomUUID(); res.setHeader("X-Request-ID",req.requestId); next(); });
app.use("/api/auth/login",authLimiter);
app.use("/api/auth/register",authLimiter);
app.use("/api/auth/forgot-password",sensitiveLimiter);
app.use("/api/auth/reset-password",sensitiveLimiter);

app.get("/health", (_req, res) => res.json({ ok: true, service: "aster-financials-api" }));

function signAccessToken(user) {
  return jwt.sign(
    { sub: user.id, email: user.email },
    jwtSecret,
    { expiresIn: "15m", issuer: "aster-financials" }
  );
}

function auth(req, res, next) {
  const header = req.headers.authorization || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!token) return res.status(401).json({ error: "AUTH_REQUIRED" });
  try {
    req.user = jwt.verify(token, jwtSecret, { issuer: "aster-financials" });
    next();
  } catch {
    return res.status(401).json({ error: "AUTH_INVALID" });
  }
}

function publicUser(row) {
  return {
    id: row.id,
    email: row.email,
    fullName: row.full_name,
    createdAt: row.created_at,
    emailVerified: Boolean(row.email_verified_at)
  };
}

function tokenHash(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

async function sendEmail(to, subject, html) {
  if (!resendApiKey || !emailFrom || !appBaseUrl) {
    console.warn("Email provider is not configured; email delivery skipped.");
    return false;
  }
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": "Bearer " + resendApiKey,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ from: emailFrom, to: [to], subject, html })
  });
  if (!response.ok) throw new Error("Email provider rejected the request.");
  return true;
}

function makeToken() {
  return crypto.randomBytes(32).toString("hex");
}

function makeReferralCode(){
  return crypto.randomBytes(5).toString("hex").toUpperCase();
}

async function uniqueReferralCode(){
  for(let i=0;i<8;i++){
    const code=makeReferralCode();
    const r=await pool.query("SELECT 1 FROM users WHERE referral_code=$1 LIMIT 1",[code]);
    if(!r.rows[0]) return code;
  }
  throw new Error("Could not allocate referral code.");
}

app.post("/api/auth/register", async (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const password = String(req.body?.password || "");
  const fullName = String(req.body?.fullName || "").trim();
  const referralCode = String(req.body?.referralCode || "").trim().toUpperCase();

  if (!fullName || !email || !/^\\S+@\\S+\\.\\S+$/.test(email) || password.length < 8) {
    return res.status(400).json({ error: "INVALID_INPUT", message: "Name, valid email and an 8+ character password are required." });
  }

  try {
    let referredBy=null;
    if(referralCode){
      const ref=await pool.query("SELECT id FROM users WHERE referral_code=$1 LIMIT 1",[referralCode]);
      if(!ref.rows[0]) return res.status(400).json({error:"INVALID_REFERRAL_CODE",message:"That referral code is not valid."});
      referredBy=ref.rows[0].id;
    }
    const ownReferralCode=await uniqueReferralCode();
    const passwordHash = await bcrypt.hash(password, 12);
    const verificationToken = makeToken();
    const result = await pool.query(
      "INSERT INTO users (email, password_hash, full_name, referral_code, referred_by, verification_token_hash, verification_expires_at) VALUES ($1,$2,$3,$4,$5,$6,NOW()+INTERVAL '24 hours') RETURNING id,email,full_name,created_at,email_verified_at",
      [email, passwordHash, fullName, ownReferralCode, referredBy, tokenHash(verificationToken)]
    );
    const user = publicUser(result.rows[0]);
    const verifyUrl = appBaseUrl ? appBaseUrl.replace(/\/$/,"") + "/verify-email?token=" + verificationToken : "";
    await sendEmail(email, "Verify your Aster Financials account",
      "<p>Welcome to Aster Financials.</p><p>Verify your email to activate account access.</p>" +
      (verifyUrl ? "<p><a href=\"" + verifyUrl + "\">Verify email</a></p>" : ""));
    return res.status(201).json({ verificationRequired: true, accessToken: signAccessToken(user), user });
  } catch (error) {
    if (error.code === "23505") return res.status(409).json({ error: "EMAIL_EXISTS", message: "An account with this email already exists." });
    console.error(error);
    return res.status(500).json({ error: "SERVER_ERROR" });
  }
});

app.post("/api/auth/login", async (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const password = String(req.body?.password || "");

  try {
    const result = await pool.query("SELECT id,email,full_name,password_hash,created_at,email_verified_at FROM users WHERE LOWER(email)=LOWER($1) LIMIT 1", [email]);
    const row = result.rows[0];
    if (!row || !(await bcrypt.compare(password, row.password_hash))) {
      return res.status(401).json({ error: "INVALID_CREDENTIALS", message: "Email or password is incorrect." });
    }
    if (!row.email_verified_at) {
      return res.status(403).json({ error: "EMAIL_NOT_VERIFIED", message: "Verify your email before signing in." });
    }
    const user = publicUser(row);
    return res.json({ accessToken: signAccessToken(user), user });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: "SERVER_ERROR" });
  }
});

app.get("/api/auth/me", auth, async (req, res) => {
  const result = await pool.query("SELECT id,email,full_name,created_at,email_verified_at FROM users WHERE id=$1 LIMIT 1", [req.user.sub]);
  if (!result.rows[0]) return res.status(404).json({ error: "USER_NOT_FOUND" });
  res.json({ user: publicUser(result.rows[0]) });
});

app.post("/api/auth/resend-verification", async (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const result = await pool.query("SELECT id,email,full_name,email_verified_at FROM users WHERE LOWER(email)=LOWER($1) LIMIT 1", [email]);
  if (!result.rows[0] || result.rows[0].email_verified_at) return res.json({ ok: true });
  const token = makeToken();
  await pool.query("UPDATE users SET verification_token_hash=$1, verification_expires_at=NOW()+INTERVAL '24 hours' WHERE id=$2", [tokenHash(token), result.rows[0].id]);
  const verifyUrl = appBaseUrl ? appBaseUrl.replace(/\/$/,"") + "/verify-email?token=" + token : "";
  await sendEmail(email, "Verify your Aster Financials account",
    "<p>Verify your Aster Financials email address.</p>" + (verifyUrl ? "<p><a href=\"" + verifyUrl + "\">Verify email</a></p>" : ""));
  res.json({ ok: true });
});

app.post("/api/auth/verify-email", async (req, res) => {
  const token = String(req.body?.token || "");
  if (!token) return res.status(400).json({ error: "INVALID_TOKEN" });
  const result = await pool.query("UPDATE users SET email_verified_at=NOW(), verification_token_hash=NULL, verification_expires_at=NULL WHERE verification_token_hash=$1 AND verification_expires_at>NOW() RETURNING id,email,full_name,created_at,email_verified_at", [tokenHash(token)]);
  if (!result.rows[0]) return res.status(400).json({ error: "TOKEN_EXPIRED", message: "Verification link is invalid or expired." });
  res.json({ ok: true, user: publicUser(result.rows[0]) });
});

app.post("/api/auth/forgot-password", async (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const result = await pool.query("SELECT id,email FROM users WHERE LOWER(email)=LOWER($1) LIMIT 1", [email]);
  if (result.rows[0]) {
    const token = makeToken();
    await pool.query("UPDATE users SET reset_token_hash=$1, reset_expires_at=NOW()+INTERVAL '30 minutes' WHERE id=$2", [tokenHash(token), result.rows[0].id]);
    const resetUrl = appBaseUrl ? appBaseUrl.replace(/\/$/,"") + "/reset-password?token=" + token : "";
    await sendEmail(email, "Reset your Aster Financials password",
      "<p>A password reset was requested for your Aster account.</p>" +
      (resetUrl ? "<p><a href=\"" + resetUrl + "\">Reset password</a></p>" : ""));
  }
  res.json({ ok: true });
});

app.post("/api/auth/reset-password", async (req, res) => {
  const token = String(req.body?.token || "");
  const password = String(req.body?.password || "");
  if (!token || password.length < 8) return res.status(400).json({ error: "INVALID_INPUT" });
  const hash = await bcrypt.hash(password, 12);
  const result = await pool.query("UPDATE users SET password_hash=$1, reset_token_hash=NULL, reset_expires_at=NULL WHERE reset_token_hash=$2 AND reset_expires_at>NOW() RETURNING id", [hash, tokenHash(token)]);
  if (!result.rows[0]) return res.status(400).json({ error: "TOKEN_EXPIRED", message: "Reset link is invalid or expired." });
  res.json({ ok: true });
});

app.get("/api/referrals/summary", auth, async (req,res)=>{
  const user=await pool.query("SELECT referral_code AS \"referralCode\" FROM users WHERE id=$1",[req.user.sub]);
  const stats=await pool.query(
    "SELECT COUNT(*)::int AS invited, COALESCE(SUM(CASE WHEN status='posted' THEN reward_amount ELSE 0 END),0) AS earned, COUNT(*) FILTER (WHERE status='posted')::int AS paid_rewards FROM referral_rewards WHERE referrer_user_id=$1",
    [req.user.sub]
  );
  res.json({referralCode:user.rows[0]?.referralCode||null,invited:stats.rows[0]?.invited||0,earned:String(stats.rows[0]?.earned||0),paidRewards:stats.rows[0]?.paid_rewards||0,rate:0.15});
});

app.get("/api/referrals/list", auth, async (req,res)=>{
  const result=await pool.query(
    "SELECT u.id,u.full_name AS \"fullName\",u.created_at AS \"joinedAt\",COALESCE(SUM(rr.reward_amount) FILTER (WHERE rr.status='posted'),0) AS \"rewarded\" FROM users u LEFT JOIN referral_rewards rr ON rr.referred_user_id=u.id WHERE u.referred_by=$1 GROUP BY u.id ORDER BY u.created_at DESC LIMIT 100",
    [req.user.sub]
  );
  res.json({referrals:result.rows});
});

app.get("/api/funding/wallets", auth, async (_req, res) => {
  const result = await pool.query(
    "SELECT network,address,qr_asset_url AS qrAssetUrl FROM wallet_addresses WHERE active=TRUE ORDER BY network"
  );
  res.json({ wallets: result.rows });
});

app.post("/api/funding/deposits", auth, async (req, res) => {
  const network=String(req.body?.network||"").trim();
  const txHash=String(req.body?.txHash||"").trim();
  const claimedAmount=String(req.body?.amount||"").trim()||null;
  if(!["TRC-20","BEP-20"].includes(network)||!txHash) return res.status(400).json({error:"INVALID_INPUT",message:"Network and transaction hash are required."});
  if(claimedAmount&&!/^\d+(\.\d{1,8})?$/.test(claimedAmount)) return res.status(400).json({error:"INVALID_AMOUNT"});
  const wallet=await pool.query("SELECT id,address FROM wallet_addresses WHERE network=$1 AND active=TRUE LIMIT 1",[network]);
  if(!wallet.rows[0]) return res.status(503).json({error:"WALLET_NOT_CONFIGURED"});
  try{
    const result=await pool.query("INSERT INTO deposits(user_id,wallet_address_id,network,amount,tx_hash,user_submitted_amount,claim_expires_at,status,source) VALUES($1,$2,$3,0,$4,$5,NOW()+INTERVAL '7 days','pending','user_claim') RETURNING id,network,amount,tx_hash AS \"txHash\",status,submitted_at AS \"submittedAt\"",[req.user.sub,wallet.rows[0].id,network,txHash,claimedAmount]);
    await pool.query("INSERT INTO deposit_claims(deposit_id,user_id,network,tx_hash) VALUES($1,$2,$3,$4) ON CONFLICT(network,tx_hash) DO NOTHING",[result.rows[0].id,req.user.sub,network,txHash]);
    const verified=await pool.query("SELECT id,amount,confirmations FROM blockchain_transfers WHERE network=$1 AND tx_hash=$2 AND status='verified' ORDER BY detected_at DESC LIMIT 1",[network,txHash]);
    if(verified.rows[0]){
      await pool.query("UPDATE deposits SET status='completed',amount=$1,verified_at=NOW(),confirmations=$2,transfer_id=$3 WHERE id=$4",[verified.rows[0].amount,verified.rows[0].confirmations,verified.rows[0].id,result.rows[0].id]);
      await pool.query("INSERT INTO ledger_entries(user_id,type,amount,currency,reference_id,status) VALUES($1,'deposit',$2,'USDT',$3,'posted')",[req.user.sub,verified.rows[0].amount,result.rows[0].id]);
      await pool.query("UPDATE blockchain_transfers SET deposit_id=$1 WHERE id=$2",[result.rows[0].id,verified.rows[0].id]);
    }
    res.status(201).json({deposit:result.rows[0],message:"Submitted for independent blockchain verification. Balance changes only after verification."});
  }catch(error){if(error.code==="23505")return res.status(409).json({error:"TX_HASH_EXISTS"});console.error(error);res.status(500).json({error:"SERVER_ERROR"});}
});
app.post("/api/admin/withdrawals/:id/execute",auth,adminOnly,requireRole("super_admin","finance_admin"),async(req,res)=>{
  const row=await pool.query("SELECT id,network,destination_address AS \"destinationAddress\",amount,fee_amount AS \"feeAmount\",net_amount AS \"netAmount\",status,requested_at AS \"requestedAt\" FROM withdrawals WHERE id=$1 LIMIT 1",[req.params.id]);
  if(!row.rows[0]) return res.status(404).json({error:"WITHDRAWAL_NOT_FOUND"});
  const w=row.rows[0];
  if(w.status!=="processing") return res.status(409).json({error:"WITHDRAWAL_NOT_PROCESSING"});
  if(!signerConfigured()) return res.status(503).json({error:"TREASURY_SIGNER_NOT_CONFIGURED",message:"Configure the isolated treasury signer/custody service before automated execution."});
  try{
    const result=await submitWithdrawal(w);
    await pool.query("UPDATE withdrawals SET execution_provider='external_signer',execution_reference=$1 WHERE id=$2",[result.executionReference||result.id||null,w.id]);
    const c2=await pool.connect();
    try{await audit(c2,req.user.sub,"withdrawal_execution_submitted","withdrawal",w.id,{provider:"external_signer",result});}finally{c2.release();}
    res.json({ok:true,status:"processing",execution:result});
  }catch(e){console.error(e);res.status(502).json({error:"TREASURY_SIGNER_ERROR",message:e.message});}
});

app.post("/api/admin/withdrawals/:id/cancel-processing",auth,adminOnly,requireRole("super_admin","finance_admin"),async(req,res)=>{
  const client=await pool.connect();
  try{
    await client.query("BEGIN");
    const row=await client.query("SELECT * FROM withdrawals WHERE id=$1 FOR UPDATE",[req.params.id]);
    if(!row.rows[0]){await client.query("ROLLBACK");return res.status(404).json({error:"WITHDRAWAL_NOT_FOUND"});}
    const w=row.rows[0];
    if(w.status!=="processing"){await client.query("ROLLBACK");return res.status(409).json({error:"WITHDRAWAL_NOT_PROCESSING"});}
    await client.query("UPDATE withdrawals SET status='rejected',rejection_reason=$1,processed_at=NOW() WHERE id=$2",[String(req.body?.reason||"Treasury execution cancelled"),w.id]);
    await client.query("INSERT INTO ledger_entries(user_id,type,amount,currency,reference_id,status) VALUES($1,'adjustment',$2,'USDT',$3,'posted')",[w.user_id,w.amount,w.id]);
    if(w.investment_id) await client.query("UPDATE investments SET status='active',updated_at=NOW() WHERE id=$1",[w.investment_id]);
    await audit(client,req.user.sub,"withdrawal_processing_cancelled","withdrawal",w.id,{reason:String(req.body?.reason||"")});
    await client.query("COMMIT");
    res.json({ok:true,status:"rejected"});
  }catch(e){await client.query("ROLLBACK");console.error(e);res.status(500).json({error:"SERVER_ERROR"});}finally{client.release();}
});

app.get("/api/admin/unmatched-transfers",auth,adminOnly,requireRole("super_admin","operations_admin","finance_admin"),async(req,res)=>{
  const result=await pool.query("SELECT ut.id,ut.transfer_id AS \"transferId\",bt.network,bt.tx_hash AS \"txHash\",bt.amount,bt.from_address AS \"fromAddress\",bt.to_address AS \"toAddress\",bt.confirmations,bt.detected_at AS \"detectedAt\" FROM unmatched_transfers ut JOIN blockchain_transfers bt ON bt.id=ut.transfer_id WHERE ut.reviewed=FALSE ORDER BY ut.created_at ASC LIMIT 200");
  res.json({transfers:result.rows});
});

