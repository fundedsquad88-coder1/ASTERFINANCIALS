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
      (verifyUrl ? "<p><a href="" + verifyUrl + "">Verify email</a></p>" : ""));
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
    "<p>Verify your Aster Financials email address.</p>" + (verifyUrl ? "<p><a href="" + verifyUrl + "">Verify email</a></p>" : ""));
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
      (resetUrl ? "<p><a href="" + resetUrl + "">Reset password</a></p>" : ""));
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

app.get("/api/account/summary", auth, async (req, res) => {
  const result = await pool.query(
    "SELECT COALESCE(SUM(CASE WHEN type IN ('deposit','investment_gain','referral_reward','adjustment') AND status='posted' THEN amount WHEN type IN ('investment_principal','withdrawal') AND status='posted' THEN -amount ELSE 0 END),0) AS balance FROM ledger_entries WHERE user_id=$1",
    [req.user.sub]
  );
  res.json({ availableBalance: result.rows[0].balance, currency: "USDT" });
});

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: "SERVER_ERROR" });
});

app.listen(port, () => console.log("Aster Financials API listening on " + port));
