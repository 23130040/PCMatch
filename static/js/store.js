import {offer,model,shop} from './data.js';
const KEY='pcmatch-demo-v2';
export const uid=prefix=>prefix+'-'+crypto.randomUUID().slice(0,8).toUpperCase();
export const clone=x=>JSON.parse(JSON.stringify(x));
const initial=()=>({version:2,users:[],cart:[],orders:[],addresses:[],builds:[],requests:[],proposals:[],consultations:[],cases:[],reviews:[],questions:[],notifications:[],draftBuild:{id:uid('BLD'),version:1,name:'Cấu hình của tôi',slots:{}},compare:[],overrides:{},checkout:{},recovery:[]});
let state;try{state=JSON.parse(localStorage.getItem(KEY))||initial();if(state.version!==2)throw Error();}catch{state=initial();}
try{localStorage.setItem(KEY,JSON.stringify(state));}catch{}
export const db=()=>state;
export function save(){try{localStorage.setItem(KEY,JSON.stringify(state));}catch{throw Error('Không lưu được dữ liệu trong trình duyệt. Kiểm tra dung lượng hoặc quyền lưu trữ rồi thử lại.');}}
function restore(target, snapshot){
 if(Array.isArray(snapshot)){
  const previous=[...target];target.length=0;
  for(const value of snapshot){const existing=value&&typeof value==='object'?previous.find(x=>x&&x.id&&x.id===value.id):null;target.push(existing?restore(existing,value):clone(value));}
 }else{for(const key of Object.keys(target))if(!(key in snapshot))delete target[key];for(const [key,value] of Object.entries(snapshot)){if(value&&typeof value==='object'&&target[key]&&typeof target[key]==='object'&&Array.isArray(value)===Array.isArray(target[key]))restore(target[key],value);else target[key]=clone(value);}}
 return target;
}
export function tx(fn){const before=clone(state);try{const result=fn(state);save();return result;}catch(e){restore(state,before);throw e;}}
export function user(){try{const s=JSON.parse(sessionStorage.getItem('pcmatch-session'));return s&&s.expires>Date.now()?state.users.find(u=>u.id===s.userId&&!u.locked):null;}catch{return null;}}
const workspaceKeys=['cart','checkout','draftBuild','compare'];
const freshWorkspace=()=>({cart:[],checkout:{},compare:[],draftBuild:{id:uid('BLD'),version:1,name:'Cấu hình của tôi',slots:{}}});
function switchWorkspace(owner){
 state.workspaces||={};const previous=state.workspaceOwner||'guest';
 state.workspaces[previous]=Object.fromEntries(workspaceKeys.map(k=>[k,clone(state[k])]));
 const next=state.workspaces[owner]||freshWorkspace();for(const k of workspaceKeys)state[k]=clone(next[k]);state.workspaceOwner=owner;
}
// Migrate the active legacy workspace once; expired sessions cannot expose it as a guest.
if(state.workspaceOwner===undefined)state.workspaceOwner=user()?.id||'guest';
if(state.workspaceOwner!==(user()?.id||'guest'))tx(()=>switchWorkspace(user()?.id||'guest'));
export function login(u){
 tx(()=>{if(state.workspaceOwner!==u.id){const guest=state.workspaceOwner==='guest'?clone({cart:state.cart,draftBuild:state.draftBuild,compare:state.compare}):null;switchWorkspace(u.id);if(guest){
  for(const item of guest.cart){const existing=state.cart.find(x=>x.offerId===item.offerId);if(existing)existing.qty+=item.qty;else state.cart.push(item);}
  if(guest.cart.length){state.checkout={};state.cart.forEach(i=>i.source=null);}
  if(Object.keys(guest.draftBuild.slots).length)state.draftBuild=guest.draftBuild;
  if(guest.compare.length)state.compare=guest.compare;state.workspaces.guest=freshWorkspace();
 }}});
 for(const key of Object.keys(sessionStorage)){if(key.startsWith('pcmatch-form:')&&key.endsWith(':guest')){sessionStorage.setItem(key.slice(0,-5)+u.id,sessionStorage.getItem(key));sessionStorage.removeItem(key);}}
 sessionStorage.setItem('pcmatch-session',JSON.stringify({userId:u.id,expires:Date.now()+3600000}));
}
export function logout(){if(state.workspaceOwner!=='guest')tx(()=>switchWorkspace('guest'));sessionStorage.removeItem('pcmatch-session');}
export function reset(){localStorage.removeItem(KEY);for(const key of Object.keys(sessionStorage))if(key.startsWith('pcmatch-'))sessionStorage.removeItem(key);state=initial();}
export const currentOffer=id=>{const o=offer(id);return o?{...o,...state.overrides[id]}:null;};
export function cartIssues(){return state.cart.flatMap(c=>{const o=currentOffer(c.offerId);return !o||!o.active||!shop(o.shopId).active?[model(o?.modelId)?.name+': ngừng bán']:!Number.isInteger(c.qty)||c.qty<1||c.qty>o.stock?[model(o.modelId).name+': số lượng vượt tồn demo']:[];});}
export function addItems(items,{replace=false,source=null}={}){
for(const i of items){const o=currentOffer(i.offerId);if(!o||!o.active||!shop(o.shopId).active||!Number.isInteger(i.qty)||i.qty<1||i.qty>o.stock)throw Error('Offer không khả dụng hoặc số lượng không hợp lệ.');}
tx(s=>{const mixed=!replace&&!!s.checkout.proposal;if(replace)s.cart=[];else if(s.checkout.proposal)s.cart.forEach(c=>c.source=null);for(const i of items){const existing=s.cart.find(c=>c.offerId===i.offerId);const o=currentOffer(i.offerId);if(existing){if(existing.qty+i.qty>o.stock)throw Error('Tổng số lượng trong giỏ vượt tồn demo.');existing.qty+=i.qty;}else s.cart.push({id:uid('CI'),offerId:i.offerId,qty:i.qty,price:o.price,stock:o.stock,warranty:o.warranty,accessories:o.accessories,source});}s.checkout=mixed?{mixed:true}:{};});}
export const mine=collection=>state[collection].filter(x=>x.userId===user()?.id);
export function notify(title,path){state.notifications.unshift({id:uid('NT'),userId:user().id,title,path,kind:path.includes('order')||path.includes('payment')?'Đơn hàng':path.includes('cases')?'Hậu mãi':'Cấu hình & báo giá',at:Date.now(),read:false});}
export async function fingerprint(text){const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));return Array.from(new Uint8Array(b)).map(x=>x.toString(16).padStart(2,'0')).join('');}
