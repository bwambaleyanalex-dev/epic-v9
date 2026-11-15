
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BEAST BOTH - PAPER TRADING</title>
<style>
body{background:#000;color:#fff;font-family:Arial;padding:10px}
h1{color:#7CFF00;margin:0;text-align:center;font-size:30px}
.beast{background:#1a1a1a;border:3px solid #7CFF00;border-radius:16px;padding:12px;margin-top:12px}
.beast.pepe{border-color:#00FF88}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin:10px 0}
.grid div{background:#000;border-radius:8px;padding:7px;overflow-wrap:anywhere}
.grid span{color:#aaa;font-size:10px}
.b{width:100%;padding:13px;border-radius:10px;font-weight:900;border:0;font-size:16px}
.row{display:flex;justify-content:space-between;gap:8px;padding:7px 0;border-bottom:1px solid #333;font-size:12px}
.small{font-size:12px;color:#aaa;text-align:center}
</style>
</head>
<body>

<h1>🤖 BEAST BOTH</h1>
<p class="small">REAL MARKET PRICES • PAPER TRADING • NO DERIV • NO MT5</p>

<div style="background:#1a1a1a;border-radius:14px;padding:12px;text-align:center;border:2px solid #7CFF00">
<div>MY VIRTUAL BALANCE</div>
<div style="font-size:38px;color:#7CFF00">$<b id="bal">20.00</b></div>
<div>Started $20.00 | Profit: $<b id="profit">0.00</b></div>
<div>Wins: <b id="wT" style="color:#00ff00">0</b> |
Losses: <b id="lT" style="color:#ff3b30">0</b> |
Trades: <b id="trades">0</b></div>
<div>Open positions: <b id="openCount">0</b>/2</div>
<button class="b" style="background:#7CFF00;margin-top:8px" onclick="toggleAuto()">
▶️ <span id="autoBtn">START AUTO BEAST</span>
</button>
<p class="small">Checks market prices every 15 seconds. Signals use observed price movement. TP and SL are checked against actual fetched prices.</p>
<div id="status" style="color:#aaa;font-size:12px">Waiting for market data...</div>
</div>

<div class="beast">
<h2>🐶 DOGE BEAST - <span id="sigDOGE">WAITING...</span></h2>
<div>Price: <b id="pDOGE" style="color:#7CFF00">...</b>
<span id="cDOGE"></span></div>
<div class="grid">
<div><span>ENTRY</span><br><b id="eDOGE">-</b></div>
<div><span>TP</span><br><b id="tpDOGE" style="color:#7CFF00">-</b></div>
<div><span>SL</span><br><b id="slDOGE" style="color:#ff3b30">-</b></div>
<div><span>STAKE</span><br><b id="stakeDOGE">$1.00</b></div>
<div><span>LAST RESULT</span><br><b id="lastDOGE">-</b></div>
<div><span>STREAK</span><br><b id="streakDOGE">0</b></div>
</div>
</div>

<div class="beast pepe">
<h2>🐸 PEPE BEAST - <span id="sigPEPE">WAITING...</span></h2>
<div>Price: <b id="pPEPE" style="color:#00FF88">...</b>
<span id="cPEPE"></span></div>
<div class="grid">
<div><span>ENTRY</span><br><b id="ePEPE">-</b></div>
<div><span>TP</span><br><b id="tpPEPE" style="color:#00FF88">-</b></div>
<div><span>SL</span><br><b id="slPEPE" style="color:#ff3b30">-</b></div>
<div><span>STAKE</span><br><b id="stakePEPE">$1.00</b></div>
<div><span>LAST RESULT</span><br><b id="lastPEPE">-</b></div>
<div><span>STREAK</span><br><b id="streakPEPE">0</b></div>
</div>
</div>

<div style="background:#1a1a1a;border-radius:14px;padding:12px;margin-top:12px">
<h3 style="color:#7CFF00;margin:0">📓 LIVE TRADE FEED</h3>
<div id="log">Waiting for first market scan...</div>
<button class="b" style="background:#fff;margin-top:8px" onclick="resetAll()">
RESET BALANCE TO $20
</button>
</div>

<p class="small">
Fixed stake: $1 per position. TP: 0.5%. SL: 0.3%.
No martingale and no random wins.
This is a virtual trading experiment, not real-money trading.
Keep Chrome open while running. Browser background restrictions may pause it.
</p>

<script>
const START_BALANCE = 20;
const STAKE = 1;
const TP_PERCENT = 0.005;
const SL_PERCENT = 0.003;
const SIGNAL_PERCENT = 0.0002;
const INTERVAL = 15000;
const STORAGE_KEY = "beast_both_fixed_v1";

const names = ["DOGE","PEPE"];

let state = {
 balance: START_BALANCE,
 wins: 0,
 losses: 0,
 positions: {DOGE:null,PEPE:null},
 streak: {DOGE:0,PEPE:0},
 lastResult: {DOGE:"-",PEPE:"-"},
 log: []
};

let previous = {DOGE:null,PEPE:null};
let auto = false;
let busy = false;
let timer = null;

function loadState(){
 try{
  const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
  if(saved && typeof saved.balance === "number"){
   state = {...state,...saved};
   state.positions = {...state.positions};
   state.streak = {...state.streak};
   state.lastResult = {...state.lastResult};
  }
 }catch(e){}
}

function saveState(){
 try{
  localStorage.setItem(STORAGE_KEY,JSON.stringify(state));
 }catch(e){}
}

function money(n){
 return Number(n).toFixed(2);
}

function priceText(n){
 return Number(n).toFixed(8);
}

function addLog(message,color="#fff"){
 const log = document.getElementById("log");
 const div = document.createElement("div");
 div.className = "row";
 const span = document.createElement("span");
 span.textContent = new Date().toLocaleTimeString()+" "+message;
 const result = document.createElement("span");
 result.textContent = "";
 result.style.color = color;
 div.append(span,result);
 log.prepend(div);
 state.log.unshift(new Date().toLocaleTimeString()+" "+message);
 state.log = state.log.slice(0,30);
 saveState();
}

function update(){
 document.getElementById("bal").textContent=money(state.balance);
 document.getElementById("profit").textContent=money(state.balance-START_BALANCE);
 document.getElementById("wT").textContent=state.wins;
 document.getElementById("lT").textContent=state.losses;
 document.getElementById("trades").textContent=state.wins+state.losses;

 let count=names.filter(n=>state.positions[n]).length;
 document.getElementById("openCount").textContent=count;

 names.forEach(n=>{
  const p=state.positions[n];
  document.getElementById("stake"+n).textContent="$"+money(STAKE);
  document.getElementById("streak"+n).textContent=state.streak[n];
  document.getElementById("last"+n).textContent=state.lastResult[n];

  if(p){
   document.getElementById("e"+n).textContent=priceText(p.entry);
   document.getElementById("tp"+n).textContent=priceText(p.tp);
   document.getElementById("sl"+n).textContent=priceText(p.sl);
   document.getElementById("sig"+n).textContent="OPEN "+p.side;
  }else{
   document.getElementById("e"+n).textContent="-";
   document.getElementById("tp"+n).textContent="-";
   document.getElementById("sl"+n).textContent="-";
  }
 });
 saveState();
}

function openPosition(name,side,price){
 const tp=side==="BUY"
  ?price*(1+TP_PERCENT)
  :price*(1-TP_PERCENT);

 const sl=side==="BUY"
  ?price*(1-SL_PERCENT)
  :price*(1+SL_PERCENT);

 state.positions[name]={
  side,
  entry:price,
  tp,
  sl,
  stake:STAKE
 };

 document.getElementById("sig"+name).textContent="OPEN "+side;
 addLog(name+" "+side+" OPENED @ $"+priceText(price));
 update();
}

function closePosition(name,exitPrice,reason){
 const p=state.positions[name];
 if(!p)return;

 let change=p.side==="BUY"
  ?(exitPrice-p.entry)/p.entry
  :(p.entry-exitPrice)/p.entry;

 const profit=p.stake*change;
 state.balance+=profit;

 if(profit>=0){
  state.wins++;
  state.streak[name]=Math.max(0,state.streak[name])+1;
  state.lastResult[name]="WIN +$"+money(profit);
 }else{
  state.losses++;
  state.streak[name]=Math.min(0,state.streak[name])-1;
  state.lastResult[name]="LOSS -$"+money(Math.abs(profit));
 }

 document.getElementById("last"+name).style.color=
  profit>=0?"#00ff00":"#ff3b30";

 state.positions[name]=null;
 document.getElementById("sig"+name).textContent=reason;

 addLog(
  name+" "+reason+" | "+(profit>=0?"WIN":"LOSS")+
  " $"+money(profit),
  profit>=0?"#00ff00":"#ff3b30"
 );

 update();
}

function checkPosition(name,price){
 const p=state.positions[name];
 if(!p)return false;

 if(p.side==="BUY"){
  if(price>=p.tp){
   closePosition(name,p.tp,"TAKE PROFIT");
   return true;
  }
  if(price<=p.sl){
   closePosition(name,p.sl,"STOP LOSS");
   return true;
  }
 }else{
  if(price<=p.tp){
   closePosition(name,p.tp,"TAKE PROFIT");
   return true;
  }
  if(price>=p.sl){
   closePosition(name,p.sl,"STOP LOSS");
   return true;
  }
 }
 return false;
}

function analyze(name,price){
 const old=previous[name];

 if(old===null){
  document.getElementById("sig"+name).textContent="LEARNING";
  return;
 }

 if(state.positions[name]){
  checkPosition(name,price);
  return;
 }

 const movement=(price-old)/old;

 if(movement>=SIGNAL_PERCENT){
  document.getElementById("sig"+name).textContent="BUY SIGNAL";
  openPosition(name,"BUY",price);
 }else if(movement<=-SIGNAL_PERCENT){
  document.getElementById("sig"+name).textContent="SELL SIGNAL";
  openPosition(name,"SELL",price);
 }else{
  document.getElementById("sig"+name).textContent="WAITING";
 }
}

async function scan(){
 if(busy)return;
 busy=true;

 try{
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),10000);

  let response;
  try{
   response=await fetch(
    "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin,pepe&vs_currencies=usd&include_24hr_change=true",
    {signal:controller.signal,cache:"no-store"}
   );
  }finally{
   clearTimeout(timeout);
  }

  if(!response.ok){
   throw new Error("Market API error: "+response.status);
  }

  const data=await response.json();

  if(!data.dogecoin || !data.pepe ||
     !Number.isFinite(data.dogecoin.usd) ||
     !Number.isFinite(data.pepe.usd)){
   throw new Error("Invalid market price data");
  }

  const prices={
   DOGE:data.dogecoin.usd,
   PEPE:data.pepe.usd
  };

  const changes={
   DOGE:data.dogecoin.usd_24h_change,
   PEPE:data.pepe.usd_24h_change
  };

  names.forEach(name=>{
   const price=prices[name];

   document.getElementById("p"+name).textContent="$"+priceText(price);

   const change=Number(changes[name]);
   document.getElementById("c"+name).textContent=
    Number.isFinite(change)?change.toFixed(2)+"% (24h)":"";

   if(auto){
    analyze(name,price);
   }else if(state.positions[name]){
    checkPosition(name,price);
   }

   previous[name]=price;
  });

  document.getElementById("status").textContent=
   "Market connected • Updated "+new Date().toLocaleTimeString();

  update();

 }catch(error){
  document.getElementById("status").textContent=
   "Market unavailable: "+error.message+" • Retrying...";
 }finally{
  busy=false;
 }
}

function toggleAuto(){
 if(auto){
  auto=false;
  clearInterval(timer);
  timer=null;
  document.getElementById("autoBtn").textContent="START AUTO BEAST";
  document.getElementById("status").textContent="Auto trading paused";
  names.forEach(n=>{
   if(!state.positions[n])
    document.getElementById("sig"+n).textContent="PAUSED";
  });
 }else{
  auto=true;
  document.getElementById("autoBtn").textContent="STOP AUTO BEAST";
  document.getElementById("status").textContent="Starting market scans...";
  scan();
  timer=setInterval(scan,INTERVAL);
 }
}

function resetAll(){
 auto=false;
 clearInterval(timer);
 timer=null;
 previous={DOGE:null,PEPE:null};

 state={
  balance:START_BALANCE,
  wins:0,
  losses:0,
  positions:{DOGE:null,PEPE:null},
  streak:{DOGE:0,PEPE:0},
  lastResult:{DOGE:"-",PEPE:"-"},
  log:[]
 };

 localStorage.removeItem(STORAGE_KEY);
 document.getElementById("autoBtn").textContent="START AUTO BEAST";
 document.getElementById("log").textContent="Reset to $20. Press START to begin.";
 document.getElementById("status").textContent="Reset complete";
 names.forEach(n=>{
  document.getElementById("sig"+n).textContent="WAITING...";
  document.getElementById("last"+n).style.color="#fff";
 });
 update();
 scan();
}

loadState();
update();
scan();
setInterval(()=>{if(!auto)scan();},INTERVAL);

</script>
</body>
</html>
