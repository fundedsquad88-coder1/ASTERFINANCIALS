import pg from "pg";
import { JsonRpcProvider, Interface, getAddress, formatUnits } from "ethers";
const pool=new pg.Pool({connectionString:process.env.DATABASE_URL,ssl:process.env.DATABASE_URL?.includes("railway")?{rejectUnauthorized:false}:undefined});
const rpc=new JsonRpcProvider(process.env.BSC_RPC_URL||"https://bsc-dataseed.binance.org");
const token=getAddress(process.env.USDT_CONTRACT||"0x55d398326f99059fF775485246999027B3197955");
const destination=getAddress(process.env.PAYOUT_ADDRESS);
const iface=new Interface(["event Transfer(address indexed from,address indexed to,uint256 value)"]);
const topic=iface.getEvent("Transfer").topicHash;
let busy=false;
async function init(){
 await pool.query("create table if not exists agent_runs(id bigserial primary key,ran_at timestamptz default now(),status text not null)");
 await pool.query("create table if not exists watcher_state(id integer primary key,last_block bigint not null)");
 const latest=await rpc.getBlockNumber();
 await pool.query("insert into watcher_state(id,last_block) values(1,$1) on conflict(id) do nothing",[Math.max(0,latest-20)]);
}
async function scan(){
 if(busy)return; busy=true;
 try{
  const latest=await rpc.getBlockNumber();
  const s=await pool.query("select last_block from watcher_state where id=1");
  let from=Number(s.rows[0]?.last_block??Math.max(0,latest-20));
  if(from>=latest){busy=false;return;}
  const to=Math.min(latest,from+1000);
  const logs=await rpc.getLogs({address:token,topics:[topic,null,"0x"+destination.slice(2).padStart(64,"0")],fromBlock:from+1,toBlock:to});
  for(const log of logs){
   const parsed=iface.parseLog(log); if(!parsed)continue;
   const amount=formatUnits(parsed.args.value,18); const txHash=log.transactionHash;
   const client=await pool.connect();
   try{
    await client.query("begin");
    const p=await client.query("select * from payment_requests where status='pending' and amount_usdt=$1 and (expires_at is null or expires_at>now()) order by created_at asc limit 1 for update skip locked",[amount]);
    if(p.rowCount){
     const row=p.rows[0];
     await client.query("update payment_requests set status='verified',tx_hash=$1 where id=$2",[txHash,row.id]);
     await client.query("insert into revenue_events(amount_usdt,source,external_id,status) values($1,$2,$3,'verified') on conflict(external_id) do nothing",[amount,"bsc-usdt",txHash]);
     console.log("verified USDT payment",amount,row.customer_ref,txHash);
    }else{
     await client.query("insert into revenue_events(amount_usdt,source,external_id,status) values($1,$2,$3,'pending') on conflict(external_id) do nothing",[amount,"bsc-usdt-unmatched",txHash]);
     console.log("unmatched USDT transfer",amount,txHash);
    }
    await client.query("commit");
   }catch(e){await client.query("rollback");throw e;}finally{client.release();}
  }
  await pool.query("update watcher_state set last_block=$1 where id=1",[to]);
  await pool.query("insert into agent_runs(status) values($1)",["bsc_scan_"+logs.length]);
 }catch(e){console.error("watcher error",e.message);}finally{busy=false;}
}
await init(); await scan(); setInterval(scan,15000);