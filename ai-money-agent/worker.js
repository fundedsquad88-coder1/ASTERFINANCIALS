import pg from "pg";
const pool=new pg.Pool({connectionString:process.env.DATABASE_URL,ssl:process.env.DATABASE_URL?.includes("railway")?{rejectUnauthorized:false}:undefined});
async function tick(){await pool.query("create table if not exists agent_runs(id bigserial primary key,ran_at timestamptz default now(),status text not null)");await pool.query("insert into agent_runs(status) values('alive')");console.log("agent worker tick",new Date().toISOString());}
await tick();setInterval(tick,60000);