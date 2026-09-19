const { Pool } = require("pg");

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : false
});

const POLL_MS = Number(process.env.BLOCKCHAIN_POLL_MS || 15000);
const BSC_RPC_URL = process.env.BSC_RPC_URL || "https://bsc-dataseed.binance.org";
const TRON_API_URL = (process.env.TRON_API_URL || "https://api.trongrid.io").replace(/\/$/, "");
const TRONGRID_API_KEY = process.env.TRONGRID_API_KEY || "";
const BSC_USDT_CONTRACT = (process.env.BSC_USDT_CONTRACT || "").toLowerCase();
const TRC20_USDT_CONTRACT = process.env.TRC20_USDT_CONTRACT || "";
const BSC_TREASURY = (process.env.BSC_TREASURY || "").toLowerCase();
const TRC20_TREASURY = process.env.TRC20_TREASURY || "";
const BSC_CONFIRMATIONS = Number(process.env.BSC_CONFIRMATIONS || 12);
const TRON_CONFIRMATIONS = Number(process.env.TRON_CONFIRMATIONS || 20);

function required(name,value){ if(!value) throw new Error(name+" is required"); }
function hexToAddress(topic){ return "0x" + topic.slice(-40).toLowerCase(); }
function hexToAmount(hex){ return Number(BigInt(hex)) / 1e18; }

async function rpc(method, params=[]){
  const r=await fetch(BSC_RPC_URL,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:1,method,params})});
  if(!r.ok) throw new Error("BSC RPC HTTP "+r.status);
  const j=await r.json(); if(j.error) throw new Error(j.error.message||"BSC RPC error"); return j.result;
}

async function bscScan(){
  required("BSC_RPC_URL",BSC_RPC_URL); required("BSC_USDT_CONTRACT",BSC_USDT_CONTRACT); required("BSC_TREASURY",BSC_TREASURY);
  const client=await pool.connect();
  try{
    const cur=await client.query("SELECT cursor FROM blockchain_cursors WHERE network='BEP-20'");
    const latest=Number(await rpc("eth_blockNumber"));
    const from=Math.max(cur.rows[0]?Number(cur.rows[0].cursor)+1:latest-100,0);
    const to=Math.max(latest-BSC_CONFIRMATIONS,from);
    if(to<from) return;
    const topicTo="0x"+BSC_TREASURY.slice(2).padStart(64,"0");
    const logs=await rpc("eth_getLogs",[{fromBlock:"0x"+from.toString(16),toBlock:"0x"+to.toString(16),address:BSC_USDT_CONTRACT,topics:["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",null,topicTo]}]);
    for(const log of logs){
      const amount=hexToAmount(log.data);
      if(!Number.isFinite(amount)||amount<=0) continue;
      const tx=log.transactionHash, idx=BigInt(log.logIndex).toString();
      await client.query("INSERT INTO blockchain_transfers(network,tx_hash,transfer_index,block_reference,token_contract,from_address,to_address,amount,confirmations,status) VALUES('BEP-20',$1,$2,$3,$4,$5,$6,$7,$8,'verified') ON CONFLICT(network,tx_hash,transfer_index) DO NOTHING",[tx,idx,parseInt(log.blockNumber,16).toString(),BSC_USDT_CONTRACT,hexToAddress(log.topics[1]),BSC_TREASURY,amount,latest-parseInt(log.blockNumber,16)+1]);
    }
    await client.query("INSERT INTO blockchain_cursors(network,cursor) VALUES('BEP-20',$1) ON CONFLICT(network) DO UPDATE SET cursor=EXCLUDED.cursor,updated_at=NOW()",[to.toString()]);
  } finally { client.release(); }
}

async function tronScan(){
  required("TRC20_USDT_CONTRACT",TRC20_USDT_CONTRACT); required("TRC20_TREASURY",TRC20_TREASURY);
  const headers={}; if(TRONGRID_API_KEY) headers["TRON-PRO-API-KEY"]=TRONGRID_API_KEY;
  const u=TRON_API_URL+"/v1/accounts/"+encodeURIComponent(TRC20_TREASURY)+"/transactions/trc20?only_to=true&limit=200&contract_address="+encodeURIComponent(TRC20_USDT_CONTRACT);
  const r=await fetch(u,{headers}); if(!r.ok) throw new Error("TRON API HTTP "+r.status);
  const j=await r.json(); const client=await pool.connect();
  try{ for(const t of (j.data||[])){ const amount=Number(t.value)/1e6; if(!Number.isFinite(amount)||amount<=0) continue; const tx=t.transaction_id; const idx=String(t.block_timestamp||0); const confirmed=t.confirmed===true && String(t.contractRet||"").toUpperCase()==="SUCCESS"; const confirmations=Number(t.confirmations||0); const status=confirmed ? "verified" : "confirming"; await client.query("INSERT INTO blockchain_transfers(network,tx_hash,transfer_index,block_reference,token_contract,from_address,to_address,amount,confirmations,status) VALUES('TRC-20',$1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT(network,tx_hash,transfer_index) DO UPDATE SET confirmations=EXCLUDED.confirmations,status=EXCLUDED.status",[tx,idx,String(t.block_timestamp||""),TRC20_USDT_CONTRACT,t.from,t.to,amount,confirmations,status]); } } finally { client.release(); }
}

async function reconcile(){
  const c=await pool.connect();
  try{
    await c.query("BEGIN");
    const transfers=await c.query("SELECT bt.* FROM blockchain_transfers bt LEFT JOIN deposits d ON d.transfer_id=bt.id WHERE bt.status='verified' AND d.id IS NULL ORDER BY bt.detected_at ASC LIMIT 100 FOR UPDATE SKIP LOCKED");
    for(const t of transfers.rows){
      const wallet=await c.query("SELECT id FROM wallet_addresses WHERE network=$1 AND LOWER(address)=LOWER($2) AND active=true LIMIT 1",[t.network,t.to_address]);
      if(!wallet.rows[0]){ await c.query("UPDATE blockchain_transfers SET status='rejected' WHERE id=$1",[t.id]); continue; }
      const existing=await c.query("SELECT id FROM deposits WHERE network=$1 AND tx_hash=$2 LIMIT 1",[t.network,t.tx_hash]);
      if(existing.rows[0]){ await c.query("UPDATE blockchain_transfers SET deposit_id=$1 WHERE id=$2",[existing.rows[0].id,t.id]); continue; }
      // A verified on-chain transfer is credited only once. User attribution is optional: if the user submitted the TXID, attach it; otherwise keep it in reconciliation for ops review.
      const submitted=await c.query("SELECT id,user_id FROM deposits WHERE network=$1 AND tx_hash=$2 LIMIT 1",[t.network,t.tx_hash]);
      if(!submitted.rows[0]){
        await c.query("INSERT INTO unmatched_transfers(transfer_id) VALUES($1) ON CONFLICT(transfer_id) DO NOTHING",[t.id]);
        continue;
      }
      const d=await c.query("UPDATE deposits SET status='completed',amount=$1,verified_at=NOW(),confirmations=$2,transfer_id=$3,rejection_reason=NULL WHERE id=$4 AND status<>'completed' RETURNING id,user_id,amount",[t.amount,t.confirmations,t.id,submitted.rows[0].id]);
      if(d.rows[0]) await c.query("INSERT INTO ledger_entries(user_id,type,amount,currency,reference_id,status) VALUES($1,'deposit',$2,'USDT',$3,'posted') ON CONFLICT DO NOTHING",[d.rows[0].user_id,d.rows[0].amount,d.rows[0].id]);
      await c.query("UPDATE blockchain_transfers SET deposit_id=$1 WHERE id=$2",[d.rows[0].id,t.id]);
    }
    await c.query("COMMIT");
  } catch(e){ await c.query("ROLLBACK"); throw e; } finally { c.release(); }
}

async function tick(){
  const lockClient=await pool.connect();
  try{
    const locked=await lockClient.query("SELECT pg_try_advisory_lock(hashtextextended('aster-blockchain-worker',0)) AS locked");
    if(!locked.rows[0].locked) return;
    try{ if(BSC_USDT_CONTRACT&&BSC_TREASURY) await bscScan(); if(TRC20_USDT_CONTRACT&&TRC20_TREASURY) await tronScan(); await reconcile(); console.log("Aster blockchain worker tick complete",new Date().toISOString()); }
    }catch(e){ console.error("Aster blockchain worker error",e); }
    finally{ await lockClient.query("SELECT pg_advisory_unlock(hashtextextended('aster-blockchain-worker',0))"); }
  }catch(e){ console.error("Aster worker lock error",e); }
  finally{ lockClient.release(); }
}
required("DATABASE_URL",process.env.DATABASE_URL);
tick(); setInterval(tick,POLL_MS);
process.on("SIGTERM",async()=>{await pool.end();process.exit(0);});
