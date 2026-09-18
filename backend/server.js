const express = require("express");
const helmet = require("helmet");
const cors = require("cors");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { Pool } = require("pg");

const app = express();
const port = Number(process.env.PORT || 8080);
const jwtSecret = process.env.JWT_SECRET;
const databaseUrl = process.env.DATABASE_URL;

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
  return { id: row.id, email: row.email, fullName: row.full_name, createdAt: row.created_at };
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
    const result = await pool.query(
      "INSERT INTO users (email, password_hash, full_name) VALUES ($1,$2,$3) RETURNING id,email,full_name,created_at",
      [email, passwordHash, fullName]
    );
    const user = publicUser(result.rows[0]);
    return res.status(201).json({ accessToken: signAccessToken(user), user });
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
    const result = await pool.query("SELECT id,email,full_name,password_hash,created_at FROM users WHERE LOWER(email)=LOWER($1) LIMIT 1", [email]);
    const row = result.rows[0];
    if (!row || !(await bcrypt.compare(password, row.password_hash))) {
      return res.status(401).json({ error: "INVALID_CREDENTIALS", message: "Email or password is incorrect." });
    }
    const user = publicUser(row);
    return res.json({ accessToken: signAccessToken(user), user });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: "SERVER_ERROR" });
  }
});

app.get("/api/auth/me", auth, async (req, res) => {
  const result = await pool.query("SELECT id,email,full_name,created_at FROM users WHERE id=$1 LIMIT 1", [req.user.sub]);
  if (!result.rows[0]) return res.status(404).json({ error: "USER_NOT_FOUND" });
  res.json({ user: publicUser(result.rows[0]) });
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
