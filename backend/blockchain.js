const NETWORKS={
  "BEP-20":{rpcUrl:process.env.BSC_RPC_URL||"",confirmations:Number(process.env.BSC_CONFIRMATIONS||12),usdtContract:(process.env.BSC_USDT_CONTRACT||"").toLowerCase()},
  "TRC-20":{rpcUrl:process.env.TRON_RPC_URL||"https://api.trongrid.io",confirmations:Number(process.env.TRON_CONFIRMATIONS||20),usdtContract:(process.env.TRON_USDT_CONTRACT||"").toLowerCase()}
};
function isBep20Address(a){return /^0x[a-fA-F0-9]{40}$/.test(String(a||""))}
function isTrc20Address(a){return /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(String(a||""))}
function validateDestination(network,address){return network==="BEP-20"?isBep20Address(address):isTrc20Address(address)}
async function rpc(url,method,params=[]){
  if(!url)throw new Error("RPC_NOT_CONFIGURED");
  const r=await fetch(url,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({jsonrpc:"2.0",id:1,method,params})});
  if(!r.ok)throw new Error("RPC_HTTP_"+r.status);
  const j=await r.json();if(j.error)throw new Error(j.error.message||"RPC_ERROR");return j.result;
}
async function bscLatestBlock(){return parseInt(await rpc(NETWORKS["BEP-20"].rpcUrl,"eth_blockNumber"),16)}
async function bscTransferLogs(fromBlock,toBlock,tokenContract,treasury){
  if(!tokenContract||!treasury)return[];
  const transfer="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a0dfb0f8e";
  const toTopic="0x"+treasury.toLowerCase().replace(/^0x/,"").padStart(64,"0");
  const logs=await rpc(NETWORKS["BEP-20"].rpcUrl,"eth_getLogs",[{
    fromBlock:"0x"+fromBlock.toString(16),toBlock:"0x"+toBlock.toString(16),
    address:tokenContract,topics:[transfer,null,toTopic]
  }]);
  return logs.map(x=>({network:"BEP-20",txHash:x.transactionHash,transferIndex:String(parseInt(x.logIndex,16)),
    tokenContract:String(x.address).toLowerCase(),fromAddress:"0x"+x.topics[1].slice(-40),toAddress:"0x"+x.topics[2].slice(-40),
    amount:(BigInt(x.data)/100000000n).toString(),blockNumber:parseInt(x.blockNumber,16),blockHash:x.blockHash}));
}
async function bscTxReceipt(txHash){return rpc(NETWORKS["BEP-20"].rpcUrl,"eth_getTransactionReceipt",[txHash])}
async function tronTransfersForAddress(address){
  const base=NETWORKS["TRC-20"].rpcUrl.replace(/\/$/,""),contract=NETWORKS["TRC-20"].usdtContract;if(!contract)return[];
  const u=base+"/v1/accounts/"+encodeURIComponent(address)+"/transactions/trc20?only_to=true&limit=200&contract_address="+encodeURIComponent(contract);
  const r=await fetch(u,{headers:process.env.TRONGRID_API_KEY?{"TRON-PRO-API-KEY":process.env.TRONGRID_API_KEY}:{}});
  if(!r.ok)throw new Error("TRON_HTTP_"+r.status);const j=await r.json();
  return(j.data||[]).map(x=>({network:"TRC-20",txHash:x.transaction_id,transferIndex:String(x.event_index??0),tokenContract:x.token_info?.address||contract,
    fromAddress:x.from,toAddress:x.to,amount:(Number(x.value)/1e6).toFixed(6),blockNumber:Number(x.block_timestamp||0),blockHash:null}));
}
module.exports={NETWORKS,validateDestination,bscLatestBlock,bscTransferLogs,bscTxReceipt,tronTransfersForAddress};
