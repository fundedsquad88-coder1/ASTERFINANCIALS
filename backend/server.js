const express = require("express");
const helmet = require("helmet");
const cors = require("cors");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { Pool } = require("pg");
const crypto = require("crypto");

const app = express();
const port = Number(process.env.PORT || 8080);
const jwtSecret = process.env.JWT_SECRET;
const databaseUrl = process.env.DATABASE_URL;
const resendApiKey = process.env.RESEND_API_KEY;
const emailFrom = process.env.EMAIL_FROM;
const appBaseUrl = process.env.APP_BASE_URL;

if (!jwtSecret || !databaseUrl) {
  console.error("JWT_SECRET and DATABASE_URL are required.");
  process.exit(1);
}

const pool = new Pool({
  connectionString: databaseUrl,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : false
});

app.use(helmet());
app.use(cors({ origin: true, credentials: true }));
app.use(express.json({ limit: "32kb" }));

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

app.post("/api/auth/register", async (req, res) => {
  const email = String(req.body?.email || "").trim().toLowerCase();
  const password = String(req.body?.password || "");
  const fullName = String(req.body?.fullName || "").trim();

  if (!fullName || !email || !/^\\S+@\\S+\\.\\S+$/.test(email) || password.length < 8) {
    return res.status(400).json({ error: "INVALID_INPUT", message: "Name, valid email and an 8+ character password are required." });
  }

  try {
    const passwordHash = await bcrypt.hash(password, 12);
    const verificationToken = makeToken();
    const result = await pool.query(
      "INSERT INTO users (email, password_hash, full_name, verification_token_hash, verification_expires_at) VALUES ($1,$2,$3,$4,NOW()+INTERVAL '24 hours') RETURNING id,email,full_name,created_at,email_verified_at",
      [email, passwordHash, fullName, tokenHash(verificationToken)]
    );
    const user = publicUser(result.rows[0]);
    const verifyUrl = appBaseUrl ? appBaseUrl.replace(/\\/$/,"") + "/verify-email?token=" + verificationToken : "";
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
  const verifyUrl = appBaseUrl ? appBaseUrl.replace(/\\/$/,"") + "/verify-email?token=" + token : "";
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
    const resetUrl = appBaseUrl ? appBaseUrl.replace(/\\/$/,"") + "/reset-password?token=" + token : "";
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

app.get("/api/funding/wallets", auth, async (_req, res) => {
  const result = await pool.query(
    "SELECT network,address,qr_asset_url AS qrAssetUrl FROM wallet_addresses WHERE active=TRUE ORDER BY network"
  );
  res.json({ wallets: result.rows });
});

app.post("/api/funding/deposits", auth, async (req, res) => {
  const network = String(req.body?.network || "").trim();
  const amount = String(req.body?.amount || "").trim();
  const txHash = String(req.body?.txHash || "").trim() || null;

  if (!["TRC-20","BEP-20"].includes(network) || !/^\\d+(\\.\\d{1,8})?$/.test(amount)) {
    return res.status(400).json({ error: "INVALID_INPUT" });
  }

  const wallet = await pool.query("SELECT id,address FROM wallet_addresses WHERE network=$1 AND active=TRUE LIMIT 1", [network]);
  if (!wallet.rows[0]) return res.status(503).json({ error: "WALLET_NOT_CONFIGURED", message: "This deposit network is not configured yet." });

  try {
    const result = await pool.query(
      "INSERT INTO deposits(user_id,wallet_address_id,network,amount,tx_hash) VALUES($1,$2,$3,$4,$5) RETURNING id,network,amount,tx_hash AS txHash,status,submitted_at AS submittedAt",
      [req.user.sub,wallet.rows[0].id,network,amount,txHash]
    );
    res.status(201).json({ deposit: result.rows[0] });
  } catch (error) {
    if (error.code === "23505") return res.status(409).json({ error: "TX_HASH_EXISTS", message: "This transaction hash has already been submitted." });
    console.error(error);
    res.status(500).json({ error: "SERVER_ERROR" });
  }
});

app.get("/api/funding/deposits", auth, async (req, res) => {
  const result = await pool.query(
    "SELECT id,network,amount,tx_hash AS \"txHash\",status,submitted_at AS \"submittedAt\",verified_at AS \"verifiedAt\" FROM deposits WHERE user_id=$1 ORDER BY submitted_at DESC LIMIT 50",
    [req.user.sub]
  );
  res.json({ deposits: result.rows });
});

app.get("/api/account/summary", auth, async (req, res) => {
  const result = await pool.query(
    "SELECT " +
    "COALESCE(SUM(CASE WHEN le.type IN ('deposit','referral_reward','adjustment') AND le.status='posted' THEN le.amount WHEN le.type IN ('withdrawal','investment_principal') AND le.status='posted' THEN -le.amount WHEN le.type='investment_gain' AND le.status='posted' AND NOT COALESCE(i.compounding,TRUE) THEN le.amount ELSE 0 END),0) AS available_balance, " +
    "COALESCE((SELECT SUM(current_value) FROM investments WHERE user_id=$1 AND status IN ('active','withdrawal_pending')),0) AS invested_balance " +
    "FROM ledger_entries le LEFT JOIN investments i ON i.id=le.reference_id WHERE le.user_id=$1",
    [req.user.sub]
  );
  const available=Number(result.rows[0].available_balance);
  const invested=Number(result.rows[0].invested_balance);
  res.json({ availableBalance: available.toFixed(8), investedBalance: invested.toFixed(8), totalBalance: (available+invested).toFixed(8), currency: "USDT" });
});

app.get("/api/investments/:id/updates", auth, async (req,res)=>{
  const result=await pool.query(
    "SELECT iu.id,iu.period_ending AS \"periodEnding\",iu.opening_value AS \"openingValue\",iu.realized_rate AS \"realizedRate\",iu.gain_amount AS \"gainAmount\",iu.closing_value AS \"closingValue\" FROM investment_updates iu JOIN investments i ON i.id=iu.investment_id WHERE iu.investment_id=$1 AND i.user_id=$2 ORDER BY iu.period_ending DESC LIMIT 52",
    [req.params.id,req.user.sub]
  );
  res.json({updates:result.rows});
});

// Internal weekly accounting worker.
// It only applies a server-supplied REALIZED rate; projection_rate is never used as a gain.
app.post("/api/internal/investments/publish-rate", async (req,res)=>{
  const secret=req.headers["x-aster-job-secret"];
  if(!process.env.JOB_SECRET || secret!==process.env.JOB_SECRET) return res.status(401).json({error:"JOB_UNAUTHORIZED"});
  const category=String(req.body?.category||"").toLowerCase();
  const periodEnding=new Date(req.body?.periodEnding||"");
  const realizedRate=Number(req.body?.realizedRate);
  if(!["crypto","forex"].includes(category) || !Number.isFinite(realizedRate) || realizedRate < -1 || realizedRate > 1 || Number.isNaN(periodEnding.getTime()))
    return res.status(400).json({error:"INVALID_INPUT"});
  await pool.query(
    "INSERT INTO investment_weekly_rates(category,period_ending,realized_rate) VALUES($1,$2,$3) ON CONFLICT(category,period_ending) DO UPDATE SET realized_rate=EXCLUDED.realized_rate,published_at=NOW()",
    [category,periodEnding.toISOString(),realizedRate]
  );
  res.json({ok:true});
});

app.post("/api/internal/investments/process-published-rates", async (req,res)=>{
  const secret=req.headers["x-aster-job-secret"];
  if(!process.env.JOB_SECRET || secret!==process.env.JOB_SECRET) return res.status(401).json({error:"JOB_UNAUTHORIZED"});
  const periodEnding=new Date(req.body?.periodEnding||"");
  if(Number.isNaN(periodEnding.getTime())) return res.status(400).json({error:"INVALID_PERIOD"});
  const rates=await pool.query("SELECT category,realized_rate FROM investment_weekly_rates WHERE period_ending=$1",[periodEnding.toISOString()]);
  const updates=[];
  for(const r of rates.rows){
    const invs=await pool.query("SELECT id FROM investments WHERE category=$1 AND status='active' AND (next_update_at IS NULL OR next_update_at<=$2)",[r.category,periodEnding.toISOString()]);
    for(const i of invs.rows) updates.push({investmentId:i.id,realizedRate:Number(r.realized_rate)});
  }
  req.body.updates=updates;
  // Reuse the same audited transactional worker below.
  req.url="/api/internal/investments/weekly-update";
  return weeklyUpdateHandler(req,res);
});

async function weeklyUpdateHandler(req,res){
  const secret=req.headers["x-aster-job-secret"];
  if(!process.env.JOB_SECRET || secret!==process.env.JOB_SECRET) return res.status(401).json({error:"JOB_UNAUTHORIZED"});
  const periodEnding=req.body?.periodEnding ? new Date(req.body.periodEnding) : new Date();
  const updates=Array.isArray(req.body?.updates) ? req.body.updates : [];
  const client=await pool.connect();
  let processed=0;
  try{
    await client.query("BEGIN");
    for(const item of updates){
      const id=String(item.investmentId||"");
      const realizedRate=Number(item.realizedRate);
      if(!id || !Number.isFinite(realizedRate) || realizedRate < -1 || realizedRate > 1) continue;
      const locked=await client.query(
        "SELECT id,user_id,current_value,compounding,status FROM investments WHERE id=$1 FOR UPDATE",
        [id]
      );
      if(!locked.rows[0] || locked.rows[0].status!=="active") continue;
      const inv=locked.rows[0];
      const opening=Number(inv.current_value);
      const gain=opening*realizedRate;
      const closing=inv.compounding ? opening+gain : opening;
      const inserted=await client.query(
        "INSERT INTO investment_updates(investment_id,period_ending,opening_value,realized_rate,gain_amount,closing_value) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(investment_id,period_ending) DO NOTHING RETURNING id",
        [id,periodEnding.toISOString(),opening,realizedRate,gain,closing]
      );
      if(!inserted.rows[0]) continue;
      await client.query(
        "UPDATE investments SET current_value=$1,realized_rate=$2,next_update_at=$3,updated_at=NOW() WHERE id=$4",
        [closing,realizedRate,new Date(periodEnding.getTime()+7*24*60*60*1000).toISOString(),id]
      );
      if(gain!==0){
        await client.query(
          "INSERT INTO ledger_entries(user_id,type,amount,currency,reference_id,status) VALUES($1,'investment_gain',$2,'USDT',$3,'posted')",
          [inv.user_id,gain,id]
        );
      }
      processed++;
    }
    await client.query("COMMIT");
    res.json({ok:true,processed,periodEnding:periodEnding.toISOString()});
  }catch(error){
    await client.query("ROLLBACK");
    console.error(error);
    res.status(500).json({error:"SERVER_ERROR"});
  }finally{client.release();}
}

app.post("/api/internal/investments/weekly-update", weeklyUpdateHandler);

app.post("/api/funding/withdrawals", auth, async (req,res)=>{
  const network=String(req.body?.network||"").trim();
  const destinationAddress=String(req.body?.destinationAddress||"").trim();
  const amount=String(req.body?.amount||"").trim();
  const investmentId=String(req.body?.investmentId||"").trim() || null;

  if(!["TRC-20","BEP-20"].includes(network) || !destinationAddress || !/^\\d+(\\.\\d{1,8})?$/.test(amount) || Number(amount)<=0){
    return res.status(400).json({error:"INVALID_INPUT",message:"Enter a valid network, destination address and USDT amount."});
  }

  const value=Number(amount);
  const client=await pool.connect();
  try{
    await client.query("BEGIN");
    await client.query("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",[req.user.sub]);

    let sourceType="available";
    if(investmentId){
      const inv=await client.query(
        "SELECT id,current_value,status FROM investments WHERE id=$1 AND user_id=$2 FOR UPDATE",
        [investmentId,req.user.sub]
      );
      if(!inv.rows[0]){ await client.query("ROLLBACK"); return res.status(404).json({error:"INVESTMENT_NOT_FOUND"}); }
      if(inv.rows[0].status!=="active"){ await client.query("ROLLBACK"); return res.status(400).json({error:"INVESTMENT_NOT_ACTIVE"}); }
      if(value!==Number(inv.rows[0].current_value)){ await client.query("ROLLBACK"); return res.status(400).json({error:"FULL_INVESTMENT_WITHDRAWAL_REQUIRED",message:"Investment withdrawals must request the full current investment value."}); }
      const pending=await client.query("SELECT 1 FROM withdrawals WHERE investment_id=$1 AND status IN ('pending','processing') LIMIT 1",[investmentId]);
      if(pending.rows[0]){ await client.query("ROLLBACK"); return res.status(409).json({error:"WITHDRAWAL_ALREADY_PENDING"}); }
      sourceType="investment";
    }else{
      const balance=await client.query(
        "SELECT COALESCE(SUM(CASE WHEN le.type IN ('deposit','referral_reward','adjustment') AND le.status='posted' THEN le.amount WHEN le.type IN ('withdrawal','investment_principal') AND le.status='posted' THEN -le.amount WHEN le.type='investment_gain' AND le.status='posted' AND NOT COALESCE(i.compounding,TRUE) THEN le.amount ELSE 0 END),0) - COALESCE((SELECT SUM(w.amount) FROM withdrawals w WHERE w.user_id=$1 AND w.status IN ('pending','processing') AND w.investment_id IS NULL),0) AS available_balance FROM ledger_entries le LEFT JOIN investments i ON i.id=le.reference_id WHERE le.user_id=$1",
        [req.user.sub]
      );
      if(value>Number(balance.rows[0].available_balance)){
        await client.query("ROLLBACK");
        return res.status(400).json({error:"INSUFFICIENT_BALANCE",message:"Your verified available balance is insufficient."});
      }
    }

    const result=await client.query(
      "INSERT INTO withdrawals(user_id,network,destination_address,amount,status,investment_id) VALUES($1,$2,$3,$4,'pending',$5) RETURNING id,network,destination_address AS \"destinationAddress\",amount,status,requested_at AS \"requestedAt\"",
      [req.user.sub,network,destinationAddress,amount,investmentId]
    );

    if(sourceType==="investment"){
      await client.query("UPDATE investments SET status='withdrawal_pending',updated_at=NOW() WHERE id=$1",[investmentId]);
    }

    // Funds become unavailable immediately through this pending withdrawal only after processing;
    // no balance is credited or debited until the withdrawal is approved/posted.
    await client.query("COMMIT");
    res.status(201).json({withdrawal:result.rows[0],source:sourceType});
  }catch(error){
    await client.query("ROLLBACK");
    console.error(error);
    res.status(500).json({error:"SERVER_ERROR"});
  }finally{client.release();}
});

app.get("/api/funding/withdrawals", auth, async (req,res)=>{
  const result=await pool.query(
    "SELECT id,network,destination_address AS \"destinationAddress\",amount,status,investment_id AS \"investmentId\",requested_at AS \"requestedAt\",processed_at AS \"processedAt\" FROM withdrawals WHERE user_id=$1 ORDER BY requested_at DESC LIMIT 50",
    [req.user.sub]
  );
  res.json({withdrawals:result.rows});
});

app.get("/api/account/activity", auth, async (req,res)=>{
  const result=await pool.query(
    "SELECT id,type,amount,currency,status,created_at AS \"createdAt\" FROM ledger_entries WHERE user_id=$1 ORDER BY created_at DESC LIMIT 50",
    [req.user.sub]
  );
  res.json({activity:result.rows});
});

app.post("/api/investments", auth, async (req,res)=>{
  const category=String(req.body?.category||"").toLowerCase();
  const principal=String(req.body?.principal||"").trim();
  const rate=Number(req.body?.projectionRate);
  const compounding=req.body?.compounding !== false;

  if(!["crypto","forex"].includes(category) || !/^\\d+(\\.\\d{1,8})?$/.test(principal) ||
     Number(principal)<=0 || !Number.isFinite(rate) || rate<0 || rate>100){
    return res.status(400).json({error:"INVALID_INPUT",message:"Choose a valid strategy and investment amount."});
  }

  const client=await pool.connect();
  try{
    await client.query("BEGIN");
    await client.query("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",[req.user.sub]);

    const balance=await client.query(
      "SELECT COALESCE(SUM(CASE WHEN type IN ('deposit','referral_reward','adjustment') AND status='posted' THEN amount WHEN type IN ('withdrawal','investment_principal') AND status='posted' THEN -amount ELSE 0 END),0) AS available_balance FROM ledger_entries WHERE user_id=$1",
      [req.user.sub]
    );
    const available=Number(balance.rows[0].available_balance);
    const amount=Number(principal);
    if(amount>available){
      await client.query("ROLLBACK");
      return res.status(400).json({error:"INSUFFICIENT_BALANCE",message:"Your verified available balance is insufficient for this investment."});
    }

    const investment=await client.query(
      "INSERT INTO investments(user_id,category,principal,current_value,projection_rate,compounding,status,next_update_at) VALUES($1,$2,$3,$3,$4,$5,'active',NOW()+INTERVAL '7 days') RETURNING id,category,principal,current_value AS \"currentValue\",projection_rate AS \"projectionRate\",compounding,status,started_at AS \"startedAt\",next_update_at AS \"nextUpdateAt\"",
      [req.user.sub,category,principal,rate,compounding]
    );
    await client.query(
      "INSERT INTO ledger_entries(user_id,type,amount,currency,reference_id,status) VALUES($1,'investment_principal',$2,'USDT',$3,'posted')",
      [req.user.sub,principal,investment.rows[0].id]
    );
    await client.query("COMMIT");
    res.status(201).json({investment:investment.rows[0]});
  }catch(error){
    await client.query("ROLLBACK");
    console.error(error);
    res.status(500).json({error:"SERVER_ERROR"});
  }finally{
    client.release();
  }
});

app.get("/api/investments", auth, async (req,res)=>{
  const result=await pool.query(
    "SELECT id,category,principal,current_value AS \"currentValue\",projection_rate AS \"projectionRate\",compounding,status,started_at AS \"startedAt\",next_update_at AS \"nextUpdateAt\",updated_at AS \"updatedAt\" FROM investments WHERE user_id=$1 ORDER BY started_at DESC",
    [req.user.sub]
  );
  res.json({investments:result.rows});
});

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: "SERVER_ERROR" });
});

app.listen(port, () => console.log("Aster Financials API listening on " + port));
