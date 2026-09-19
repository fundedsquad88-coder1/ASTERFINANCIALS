const crypto = require("crypto");

function signerConfigured(){
  return Boolean(process.env.TREASURY_SIGNER_URL && process.env.TREASURY_SIGNER_SECRET);
}

async function submitWithdrawal(request){
  if(!signerConfigured()) return {configured:false};
  const body={
    withdrawalId:request.id,
    network:request.network,
    destinationAddress:request.destinationAddress,
    grossAmount:String(request.grossAmount),
    feeAmount:String(request.feeAmount),
    netAmount:String(request.netAmount),
    requestedAt:request.requestedAt
  };
  const payload=JSON.stringify(body);
  const signature=crypto.createHmac("sha256",process.env.TREASURY_SIGNER_SECRET).update(payload).digest("hex");
  const response=await fetch(process.env.TREASURY_SIGNER_URL,{
    method:"POST",
    headers:{"content-type":"application/json","x-aster-signature":signature},
    body:payload
  });
  const text=await response.text();
  let data={};
  try{data=JSON.parse(text);}catch{}
  if(!response.ok) throw new Error("Treasury signer rejected request: HTTP "+response.status);
  return {configured:true,...data};
}

module.exports={signerConfigured,submitWithdrawal};
