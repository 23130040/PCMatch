import {bySold} from './merchandising-data.js';
// Catalogue queries are isolated from rendering. A backend adapter can replace these reads.
import {models,offers,categories,regions,shop,shipping} from './data.js';
import {assetUrl} from './routing.js';
import {currentOffer} from './store.js';
export const technicalFields={CPU:['Socket','Nhân / luồng','iGPU'],MB:['Socket','RAM','Form'],GPU:['VRAM','Nguồn đề nghị','Chiều dài'],RAM:['RAM','Dung lượng','Kit'],SSD:['Dung lượng','Chuẩn','Form'],PSU:['Công suất','Form'],CASE:['Form','GPU tối đa','Tản tối đa'],COOL:['Socket','Chiều cao']};
export const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/đ/g,'d').trim();
export const modelOffers=id=>offers.filter(o=>o.modelId===id).map(o=>currentOffer(o.id));
export const sellable=o=>o.active&&shop(o.shopId)?.active;
export const stockLabel=o=>!shop(o.shopId)?.active?'Shop tạm dừng bán':!o.active?'Offer ngừng bán':o.stock>0?'Còn '+o.stock+' (demo)':'Hết hàng (demo)';
export const variant=m=>m.category==='RAM'?(m.specs.Kit+' · '+m.specs.RAM):m.specs['Dung lượng']||m.specs.VRAM||m.specs['Công suất']||m.specs.Socket||m.specs.Form||'Bản tiêu chuẩn demo';
export const imagePath=m=>assetUrl('images/catalog/'+m.category.toLowerCase()+'.svg');
export const technicalOptions=category=>(technicalFields[category]||[]).map(key=>({key,values:[...new Set(models.filter(m=>m.category===category).map(m=>m.specs[key]).filter(v=>v&&v!=='Chưa có dữ liệu'))]}));
export function queryCatalog(p,lockedShop=''){
 const category=p.get('slot')||p.get('category')||'',keyword=normalize(p.get('q')),min=p.get('min')?Number(p.get('min')):0,max=p.get('max')?Number(p.get('max')):Infinity;
 const seller=lockedShop||p.get('shop'),region=p.get('region'),availability=p.get('availability')||(p.has('stock')?'in':'');
 let rows=models.filter(m=>(!category||m.category===category)&&(!keyword||normalize([m.name,m.brand,m.id,categories[m.category]].join(' ')).includes(keyword))&&(!p.get('brand')||m.brand===p.get('brand'))&&(!p.get('spec')||Object.values(m.specs).includes(p.get('spec')))&&[...p.entries()].filter(([key])=>key.startsWith('tech:')).every(([key,value])=>!value||m.specs[key.slice(5)]===value)).map(m=>{
  const matches=modelOffers(m.id).filter(o=>(!seller||o.shopId===seller)&&(!region||shipping(o.shopId,region)!==null)&&o.price>=min&&o.price<=max&&(availability==='in'?sellable(o)&&o.stock>0:availability==='out'?sellable(o)&&o.stock===0:availability==='paused'?!sellable(o):true));
  return {model:m,offers:matches,price:matches.length?Math.min(...matches.map(o=>o.price)):Infinity};
 }).filter(row=>row.offers.length);
 if(p.get('sort')==='sold')rows.sort((a,b)=>bySold(a.model,b.model));else if(p.get('sort')==='price')rows.sort((a,b)=>a.price-b.price);else if(p.get('sort')==='desc')rows.sort((a,b)=>b.price-a.price);else if(p.get('sort')==='name')rows.sort((a,b)=>a.model.name.localeCompare(b.model.name,'vi'));
 return rows;
}
export const regionName=id=>regions[id]||'Chưa chọn khu vực';
