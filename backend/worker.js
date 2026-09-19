const {Pool}=require("pg");
const {NETWORKS,bscLatestBlock,bscTransferLogs,tronTransfersForAddress,bscTxReceipt}=require("./blockchain");
const pool=new Pool({connectionString:process.env.DATABASE_URL,ssl:process.env.NODE_ENV==="production"?{rejectUnauthorized:false}:false});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function lease(name,fn){
  const c=await pool.connect();let locked=false;
  try{const q=await c.query("SELECT pg_try_advisory_lock(hashtext($1)) locked",[name]);locked=q.rows[0].locked;if(locked)await fn(c)}
  finally{if(locked)try{await c.query("SELECT pg_advisory_unlock(hashtext($1))",[name])}catch{}c.release()}
}
async function wallet(network){const r=await pool.query("SELECT id,address FROM wallet_addresses WHERE network=$1 AND active=TRUE LIMIT 1",[network]);return r.rows[0]||null}
async function recordInbound(t){
  const w=await wallet(t.network);if(!w||t.toAddress.toLowerCase()!==w.address.toLowerCase())return;
  const c=await pool.connect();
  try{
    await c.query("BEGIN");
    const exists=await c.query("SELECT id FROM blockchain_transfers WHERE network=$1 AND tx_hash=$2 AND transfer_index=$3",[t.network,t.txHash,t.transferIndex]);
    if(exists.rows[0]){await c.query("COMMIT");return}
    const bt=await c.query("INSERT INTO blockchain_transfers(network,direction,tx_hash,transfer_index,token_contract,from_address,to_address,amount,block_number,block_hash,status) VALUES($1,'inbound',$2,$3,$4,$5,$6,$7,$8,$9,'detected') RETURNING id",
      [t.network,t.txHash,t.transferIndex,t.tokenContract,t.fromAddress,t.toAddress,t.amount,t.blockNumber,t.blockHash]);
    const d=await c.query("SELECT id,user_id,amount,status FROM deposits WHERE network=$1 AND tx_hash=$2 FOR UPDATE",[t.network,t.txHash]);
    if(d.rows[0])await c.query("UPDATE deposits SET status='confirming',block_number=$1,token_contract=$2,transfer_index=$3,confirmations=0 WHERE id=$4",[t.blockNumber,t.tokenContract,t.transferIndex,d.rows[0].id]),await c.query("UPDATE blockchain_transfers SET deposit_id=$1 WHERE id=$2",[d.rows[0].id,bt.rows[0].id]);
    await c.query("COMMIT");
  }catch(e){await c.query("ROLLBACK");throw e}finally{c.release()}
}
async function scan(){
  for(const network of ["BEP-20","TRC-20"]){
    const w=await wallet(network);if(!w)continue;let ts=[];
    if(network==="BEP-20"){
      const latest=await bscLatestBlock();const cur=await pool.query("SELECT last_block FROM blockchain_cursors WHERE network=$1",[network]);
      const from=Math.max(0,Number(cur.rows[0]?.last_block||latest-100));const to=Math.min(latest,from+2000);
      ts=await bscTransferLogs(from,to,NETWORKS[network].usdtContract,w.address);
      await pool.query("INSERT INTO blockchain_cursors(network,last_block) VALUES($1,$2) ON CONFLICT(network) DO UPDATE SET last_block=EXCLUDED.last_block,updated_at=NOW()",[network,to]);
    }else ts=await tronTransfersForAddress(w.address);
    for(const t of ts)await recordInbound(t);
  }
}
async function confirmDeposits(){
  const rs=await pool.query("SELECT bt.*,d.user_id,d.id deposit_id FROM blockchain_transfers bt JOIN deposits d ON d.id=bt.deposit_id WHERE bt.status IN ('detected','confirming')");
  for(const x of rs.rows){
    const confirmations=x.network==="BEP-20"?Math.max(0,(await bscLatestBlock())-Number(x.block_number)+1):NETWORKS[x.network].confirmations;
    if(confirmations<NETWORKS[x.network].confirmations){await pool.query("UPDATE blockchain_transfers SET confirmations=$1,status='confirming' WHERE id=$2",[confirmations,x.id]);await pool.query("UPDATE deposits SET confirmations=$1,status='confirming' WHERE id=$2",[confirmations,x.deposit_id]);continue}
    const c=await pool.connect();try{
      await c.query("BEGIN");const d=await c.query("SELECT * FROM deposits WHERE id=$1 FOR UPDATE",[x.deposit_id]);
      if(!d.rows[0]||d.rows[0].status==="completed"){await c.query("COMMIT");continue}
      await c.query("UPDATE blockchain_transfers SET confirmations=$1,status='confirmed',confirmed_at=NOW() WHERE id=$2",[confirmations,x.id]);
      await c.query("UPDATE deposits SET status='completed',confirmations=$1,verified_at=NOW() WHERE id=$2",[confirmations,x.deposit_id]);
      await c.query("INSERT INTO ledger_entries(user_id,type,amount,currency,reference_id,status) VALUES($1,'deposit',$2,'USDT',$3,'posted')",[x.user_id,x.amount,x.deposit_id]);
      await c.query("COMMIT");
    }catch(e){await c.query("ROLLBACK");throw e}finally{c.release()}
  }
}
async function confirmWithdrawals(){
  const rs=await pool.query("SELECT w.id,w.network,j.id job_id,j.tx_hash FROM withdrawals w JOIN withdrawal_jobs j ON j.withdrawal_id=w.id WHERE j.tx_hash IS NOT NULL AND w.status IN ('processing','broadcast','confirming')");
  for(const x of rs.rows)if(x.network==="BEP-20"){
    const receipt=await bscTxReceipt(x.tx_hash);
    if(receipt?.status==="0x1"){await pool.query("UPDATE withdrawals SET status='completed',processed_at=NOW() WHERE id=$1",[x.id]);await pool.query("UPDATE withdrawal_jobs SET status='completed',updated_at=NOW() WHERE id=$1",[x.job_id])}
  }
}
async function run(){
  if(!process.env.DATABASE_URL)throw new Error("DATABASE_URL required");
  while(true){
    try{await lease("aster:blockchain-scan",scan)}catch(e){console.error("scan",e)}
    try{await lease("aster:deposit-confirm",confirmDeposits)}catch(e){console.error("deposit",e)}
    try{await lease("aster:withdrawal-confirm",confirmWithdrawals)}catch(e){console.error("withdrawal",e)}
    await sleep(Number(process.env.WORKER_INTERVAL_MS||15000));
  }
}
run().catch(e=>{console.error(e);process.exit(1)});
