import {models,offers,shops,categories,regions,model,shop,money,shipping} from './data.js';
import {assetUrl} from './routing.js';
import {db,tx,user,mine,uid,addItems,currentOffer} from './store.js';
import {esc,params,link,go,a,button,field,select,textarea,submit,form,notice,empty,panel,head,mount,toast,dialog,requireUser,page} from './ui.js';
const price=m=>Math.min(...offers.filter(o=>o.modelId===m.id&&currentOffer(o.id).active).map(o=>currentOffer(o.id).price));
const context=()=>Object.fromEntries(['slot','build','version'].filter(k=>params.has(k)).map(k=>[k,params.get(k)]));
const catalogueLink=m=>link('model',{id:m.id,...context(),...(page==='search'?{from:params.toString()}: {})});
const available=m=>offers.filter(o=>o.modelId===m.id).map(o=>currentOffer(o.id)).filter(o=>o.active&&shop(o.shopId).active);
const priceText=m=>available(m).length?money(price(m)):'Chưa có offer đang bán';
export function card(m){const os=offers.filter(o=>o.modelId===m.id&&currentOffer(o.id).active);return '<article class="catalog-card"><a class="catalog-visual" href="'+catalogueLink(m)+'" aria-label="'+esc(m.name)+'"><span>'+m.category+'</span><small>'+esc(Object.values(m.specs).slice(0,2).join(' · '))+'</small></a><div class="catalog-body"><p class="muted">'+esc(categories[m.category])+'</p><h3><a href="'+catalogueLink(m)+'">'+esc(m.name)+'</a></h3><p class="muted">'+esc(Object.values(m.specs).slice(0,3).join(' · '))+'</p><div class="catalog-price"><small>Giá demo từ</small><strong>'+priceText(m)+'</strong><span>'+os.length+' shop bán</span></div><div class="cluster"><a class="btn btn--primary" href="'+catalogueLink(m)+'">Chọn shop</a>'+button('So sánh','compare-add',m.id)+'</div></div></article>';}
export function home(){mount('Mua linh kiện',head('Linh kiện cho chiếc PC của bạn.','Chọn sản phẩm, so sánh giá và điều kiện từ từng shop.',a('Khám phá linh kiện','search',{},'primary'))+'<nav class="category-strip" aria-label="Danh mục">'+Object.entries(categories).map(([k,v])=>'<a href="'+link('search',{category:k})+'"><strong>'+k+'</strong><span>'+v+'</span></a>').join('')+'</nav><section><div class="section-heading"><h2>Khám phá linh kiện</h2>'+a('Xem tất cả '+models.length+' model','search')+'</div><div class="catalog-grid">'+[models[0],models[7],models[5],models[9]].map(card).join('')+'</div></section><section class="build-entry"><div><h2>Cần chọn cả cấu hình?</h2><p>Tự chọn từng linh kiện hoặc gửi nhu cầu để shop đề xuất.</p></div><div class="cluster">'+a('Tự build PC','builder')+a('Build theo ngân sách','requests',mine('requests').length?{}:{new:'1'})+'</div></section><section><div class="section-heading"><h2>Gian hàng trên PCMatch</h2></div><div class="shop-strip">'+shops.map(s=>'<a href="'+link('shop',{id:s.id})+'"><strong>'+esc(s.name)+'</strong><span>'+regions[s.region]+' · '+(s.active?'Đang bán (demo)':'Tạm ngừng bán')+'</span></a>').join('')+'</div></section>');}

import {queryCatalog,technicalOptions,modelOffers,sellable,stockLabel,variant,imagePath} from './catalog-data.js';
import {renderPage,installDrawer,openFilters} from './catalog-view.js';

const breadcrumb=(items)=>'<a href="'+link('home')+'">Trang chủ</a>'+items.map(([label,url])=>'<span aria-hidden="true">/</span>'+(url?'<a href="'+esc(url)+'">'+esc(label)+'</a>':'<span aria-current="page">'+esc(label)+'</span>')).join('');
const reviewSummary=id=>{const rows=db().reviews.filter(r=>r.shopId===id);return rows.length?(rows.reduce((n,r)=>n+r.shopRating,0)/rows.length).toFixed(1)+'/5 · '+rows.length+' đánh giá shop demo':'Chưa có đánh giá shop demo';};
function productImage(m){return '<div class="product-image"><img data-product-image src="'+imagePath(m)+'" alt="Sơ đồ minh họa '+esc(categories[m.category])+' cho '+esc(m.name)+'" width="320" height="200"><div class="image-fallback" hidden role="img" aria-label="Không tải được ảnh '+esc(m.name)+'"><strong>'+m.category+'</strong><span>Không tải được ảnh</span></div></div><span class="image-caption">Hình minh họa danh mục · không phải ảnh hãng</span>';}
function resultCard(row){
 const m=row.model,os=row.offers,seller=page==='shop'?params.get('id'):params.get('shop');
 const args={id:m.id,...context(),...(seller?{shop:seller}:{}),...(params.get('region')?{region:params.get('region')}:{}),...(page==='search'?{from:params.toString()}:page==='shop'?{shopQuery:params.toString()}:{} )};
 return '<article class="catalog-card" data-model-id="'+m.id+'"><a class="catalog-product-image" href="'+link('model',args)+'">'+productImage(m)+'</a><div class="catalog-body"><p>'+esc(categories[m.category])+' · '+esc(m.brand)+'</p><h3><a href="'+link('model',args)+'">'+esc(m.name)+'</a></h3><p>'+esc(variant(m))+'</p><div class="catalog-price"><small>Giá demo theo bộ lọc từ</small><strong>'+money(row.price)+'</strong><span>'+os.length+' offer phù hợp · '+os.filter(o=>sellable(o)&&o.stock>0).length+' còn hàng</span></div><div class="cluster"><a class="btn btn--primary" href="'+link('model',args)+'">'+(seller?'Xem offer của shop':'Chọn shop')+'</a>'+button('Thêm so sánh','compare-add',m.id)+'</div></div></article>';
}
function compareTray(){
 const chosen=db().compare.map(model).filter(Boolean);
 return chosen.length?'<div class="compare-tray-inner"><strong>Đang so sánh '+chosen.length+'/4</strong><div class="cluster">'+chosen.map(m=>button(esc(m.name)+' · Bỏ','compare-remove',m.id)).join('')+'</div><div class="cluster">'+a('Xem bảng so sánh','compare')+button('Xóa danh sách','compare-clear')+'</div></div>':'';
}
function updateTray(){document.querySelectorAll('[data-content="compare-tray"]').forEach(n=>n.innerHTML=compareTray());document.querySelectorAll('[data-compare-link]').forEach(n=>n.textContent='So sánh ('+db().compare.length+')');}
function fillOptions(el,values,selected=''){el.innerHTML=Object.entries(values).map(([value,label])=>'<option value="'+esc(value)+'">'+esc(label)+'</option>').join('');el.value=selected;}
function fillTechnical(f,category,p=new URLSearchParams()){
 f.querySelector('[data-technical]').innerHTML=technicalOptions(category).map(({key,values})=>select(key,'tech:'+key,{'':'Tất cả',...Object.fromEntries(values.map(v=>[v,v]))},p.get('tech:'+key)||'')).join('')||'<p class="muted">Chọn danh mục để lọc thông số phù hợp.</p>';
}
function configureFilters(lockedShop=''){
 const f=document.querySelector('#catalog-filters'),cat=params.get('slot')||params.get('category')||'';
 fillOptions(f.elements.category,{'':'Tất cả',...categories},cat);f.elements.category.disabled=params.has('slot');
 const brands=category=>Object.fromEntries([...new Set(models.filter(m=>!category||m.category===category).map(m=>m.brand))].map(b=>[b,b]));
 fillOptions(f.elements.brand,{'':'Tất cả',...brands(cat)},params.get('brand')||'');
 fillOptions(f.elements.shop,{'':'Tất cả shop',...Object.fromEntries(shops.map(s=>[s.id,s.name]))},lockedShop||params.get('shop')||'');
 if(lockedShop){f.elements.shop.disabled=true;f.elements.shop.closest('label').hidden=true;}
 fillOptions(f.elements.region,{'':'Tất cả khu vực',...regions},params.get('region')||'');
 for(const name of ['q','min','max','sort'])f.elements[name].value=params.get(name)||'';
 f.elements.availability.value=params.get('availability')||(params.has('stock')?'in':'');
 fillTechnical(f,cat,params);
 f.elements.category.addEventListener('change',()=>{fillOptions(f.elements.brand,{'':'Tất cả',...brands(f.elements.category.value)});fillTechnical(f,f.elements.category.value);});
 f.querySelector('[data-clear-filters]').href=lockedShop?link('shop',{id:lockedShop}):link('search',context());
 installDrawer();
}
function chips(){
 const labels={q:'Từ khóa',category:'Danh mục',brand:'Hãng',min:'Giá từ',max:'Giá đến',shop:'Shop',region:'Nơi nhận',stock:'Còn hàng',availability:'Tình trạng',spec:'Thông số'};
 return [...params.entries()].filter(([key])=>labels[key]||key.startsWith('tech:')).map(([key,value])=>{
  const display=key==='category'?categories[value]:key==='shop'?shop(value)?.name:key==='region'?regions[value]:key==='availability'?{in:'Còn hàng',out:'Hết hàng',paused:'Tạm ngừng'}[value]:value;
  return button(esc((labels[key]||key.slice(5))+': '+(display||value||'Có'))+' ×','remove-filter',key);
 }).join('');
}
function paginate(rows,route,args){
 const pages=Math.max(1,Math.ceil(rows.length/6)),current=Math.min(pages,Math.max(1,Math.trunc(Number(params.get('p')))||1));
 return {shown:rows.slice((current-1)*6,current*6),html:'<nav class="pagination" aria-label="Phân trang">'+(current>1?a('Trước',route,{...args,p:current-1}):'')+'<span>Trang '+current+' / '+pages+'</span>'+(current<pages?a('Tiếp',route,{...args,p:current+1}):'')+'</nav>'};
}
export function search(){
 const cat=params.get('slot')||params.get('category')||'',q=params.get('q')?.trim(),rows=queryCatalog(params),failed=params.get('error')==='1';
 const title=params.has('slot')?'Chọn '+(categories[cat]||cat):q?'Kết quả cho “'+q+'”':cat?categories[cat]||'Danh mục không tồn tại':'Tất cả linh kiện';
 const paging=paginate(rows,'search',Object.fromEntries(params));
 renderPage(title,{
  breadcrumb:breadcrumb([['Linh kiện',cat||q?link('search'):null],...(cat?[[categories[cat]||cat,null]]:[])]),
  heading:head(title,'Tìm model phù hợp, sau đó chọn offer của shop.',params.has('slot')?a('Về cấu hình','builder'):''),
  count:failed?'Chưa tải được kết quả':rows.length+' model phù hợp · dữ liệu demo',
  status:failed?notice('Lỗi tải danh mục mô phỏng. Bộ lọc được giữ. '+button('Thử lại','search-retry'),'error'):'',
  chips:chips(),
  results:failed?'':paging.shown.length?paging.shown.map(resultCard).join(''):empty('Không có kết quả','Bỏ từng điều kiện ở phía trên hoặc xóa bộ lọc để tìm lại.',a('Xóa bộ lọc','search',context())),
  pagination:failed?'':paging.html+a('Thử lỗi tải demo','search',{...Object.fromEntries(params),error:1},'quiet'),
  'compare-tray':compareTray()
 });
 configureFilters();updateTray();document.querySelector('#global-search').value=params.get('q')||'';
}
function offerTable(os,region){
 const headers=['Shop / khu vực','Giá demo','Giao dự kiến','Tổng một món + giao','Bảo hành','Tồn / trạng thái','Thời gian giao','Đánh giá shop','Chọn offer'];
 return '<h3>So sánh các offer của cùng model</h3><p>Phí cho một món đến '+esc(regions[region])+'. Chưa giữ giá hoặc tồn.</p><div class="table-wrap offer-table" tabindex="0" aria-label="Bảng so sánh shop, cuộn ngang để xem đủ cột"><table class="data-table"><caption>Giá và điều kiện từng shop · dữ liệu demo</caption><thead><tr>'+headers.map(h=>'<th scope="col">'+h+'</th>').join('')+'</tr></thead><tbody>'+os.map(o=>{const fee=shipping(o.shopId,region);return '<tr><th scope="row">'+esc(shop(o.shopId).name)+'<br><small>'+regions[shop(o.shopId).region]+'</small></th><td>'+money(o.price)+'</td><td>'+(fee===null?'Chưa hỗ trợ':money(fee))+'</td><td>'+(fee===null?'Chưa tính được':money(o.price+fee))+'</td><td>'+o.warranty+' tháng</td><td>'+stockLabel(o)+'</td><td>'+(fee===null?'Chưa có dữ liệu':'3–5 ngày (demo)')+'</td><td>'+reviewSummary(o.shopId)+'</td><td>'+button('Xem offer','offer-focus',o.id)+'</td></tr>';}).join('')+'</tbody></table></div>';
}
function offerCard(o,region){
 const s=shop(o.shopId),fee=shipping(o.shopId,region),blocked=!sellable(o)||o.stock<1,selected=params.get('shop')===s.id;
 return '<article id="offer-'+o.id+'" class="offer-card'+(selected?' offer-selected':'')+'"><div>'+(selected?'<p><strong>Offer từ gian hàng bạn chọn</strong></p>':'')+'<h3><a href="'+link('shop',{id:s.id})+'">'+esc(s.name)+'</a></h3><p>'+o.id+' · '+regions[s.region]+'</p><p>'+reviewSummary(s.id)+'</p><strong class="price">'+money(o.price)+'</strong><p>'+stockLabel(o)+'</p>'+(blocked?'<p>Mua mới bị khóa. Bạn có thể chọn offer khác hoặc quay lại sau.</p>':'')+'</div><div><p>Bảo hành '+o.warranty+' tháng · Tiếp nhận tại '+esc(s.name)+'</p><p>'+esc(o.accessories)+'</p><p>Phí giao ước tính: '+(fee===null?'Chưa hỗ trợ khu vực này':money(fee))+'</p><p>Thời gian giao: '+(fee===null?'Chưa có dữ liệu':'3–5 ngày (demo)')+'</p><details><summary>Điều kiện bán và bảo hành</summary><p>Hàng mới; shop tiếp nhận kiểm tra lỗi. Đổi/trả trong 7 ngày sau giao theo kịch bản demo; không tự động chấp nhận hoàn. Bảo hành theo số tháng của offer.</p></details></div>'+form('offer','<input type="hidden" name="offerId" value="'+o.id+'">'+field('Số lượng','qty',1,'number','required min="1" max="'+Math.max(1,o.stock)+'" step="1" '+(blocked?'disabled':''))+select('Thao tác','target',{cart:'Thêm vào giỏ',build:'Thêm vào cấu hình'},params.has('slot')?'build':'cart')+'<button type="submit" class="btn btn--primary" '+(blocked?'disabled':'')+'>'+(params.has('slot')?'Thêm vào cấu hình':'Thêm vào giỏ')+'</button>')+a('Báo cáo tin bán','cases',{new:'report',target:o.id})+'</article>';
}
export function detail(){
 const m=model(params.get('id'));if(!m){mount('Model',empty('Không tìm thấy model','Chọn một model từ danh mục.'));return;}
 const region=regions[params.get('region')]?params.get('region'):'HCM';
 const os=modelOffers(m.id).sort((a,b)=>Number(b.shopId===params.get('shop'))-Number(a.shopId===params.get('shop')));
 const back=params.has('from')?Object.fromEntries(new URLSearchParams(params.get('from'))):{category:m.category,...context()};
 renderPage(m.name,{
  breadcrumb:breadcrumb([['Linh kiện',link('search')],[categories[m.category],link('search',{category:m.category})],[m.name,null]]),
  heading:head(m.name,'Model '+m.id+' · '+m.brand,a('Về kết quả tìm kiếm','search',back)+(params.get('shop')?a('Về gian hàng','shop',params.has('shopQuery')?Object.fromEntries(new URLSearchParams(params.get('shopQuery'))):{id:params.get('shop')}):'')+button('Thêm so sánh','compare-add',m.id)),
  image:productImage(m),
  specs:'<p class="price">'+priceText(m)+' <small>giá demo từ</small></p><p><strong>Biến thể: </strong>'+esc(variant(m))+'</p><p>'+esc(m.description)+'</p><dl class="spec-grid">'+Object.entries(m.specs).map(([k,v])=>'<div><dt>'+esc(k)+'</dt><dd>'+esc(v||'Chưa có dữ liệu')+'</dd></div>').join('')+'</dl>'+notice('Thông số minh họa, không phải chứng nhận của hãng. Nguồn: <a href="'+assetUrl('js/data.js')+'">dữ liệu catalogue demo</a>.'),
  region:form('region',select('Khu vực nhận','region',regions,region)+submit('Cập nhật phí')),
  'offer-count':os.filter(sellable).length+' shop đang bán · '+os.length+' offer trong dữ liệu demo',
  'offer-table':offerTable(os,region),offers:os.map(o=>offerCard(o,region)).join(''),
  questions:db().questions.filter(x=>x.modelId===m.id).map(x=>'<article class="list-row"><div><strong>'+esc(x.text)+'</strong><p>'+esc(shop(x.shopId)?.name)+' · '+esc(x.reply||'Chưa có trả lời')+'</p></div></article>').join('')+form('question',select('Shop nhận câu hỏi','shopId',Object.fromEntries(os.map(o=>[o.shopId,shop(o.shopId).name])),params.get('shop')||os[0]?.shopId)+textarea('Câu hỏi (không ghi số điện thoại/địa chỉ)','text')+submit('Gửi câu hỏi')),
  reviews:db().reviews.filter(r=>r.modelId===m.id).map(r=>'<p><strong>Đã mua trong demo · Sản phẩm '+r.productRating+'/5 · Shop '+r.shopRating+'/5</strong><br>'+esc(r.text)+'</p>').join('')||'<p>Chưa có đánh giá. Chỉ dòng hàng đã giao mới được đánh giá.</p>'+a('Mở đơn của tôi để đánh giá','orders'),
  'compare-tray':compareTray(),report:a('Báo cáo nội dung sản phẩm','cases',{new:'report',target:m.id})
 });
 document.querySelectorAll('form[data-form=offer] select').forEach(el=>el.addEventListener('change',()=>el.form.querySelector('[type=submit]').textContent=el.value==='build'?'Thêm vào cấu hình':'Thêm vào giỏ'));
 if(params.get('compareOffers')==='1'){document.querySelector('#offer-comparison').hidden=false;document.querySelector('[data-action=offers-toggle]').setAttribute('aria-expanded','true');}
}
export function storefront(){
 const s=shop(params.get('id'));if(!s){mount('Gian hàng',empty('Không tìm thấy shop','Mở shop từ trang sản phẩm.'));return;}
 const rows=queryCatalog(params,s.id),paging=paginate(rows,'shop',Object.fromEntries(params)),reviews=db().reviews.filter(r=>r.shopId===s.id);
 renderPage(s.name,{
  breadcrumb:breadcrumb([['Gian hàng '+s.name,null]]),
  heading:'<div class="shop-monogram" role="img" aria-label="Biểu trưng demo '+esc(s.name)+'">'+s.id+'</div>'+head(s.name,regions[s.region]+' · 09:00–18:00 (demo)',a('Báo cáo shop','cases',{new:'report',target:s.id})),
  status:notice(s.active?'Gian hàng minh họa · chưa xác minh thực tế.':'Shop tạm dừng bán; không nhận mua mới. Đơn cũ vẫn có đường hỗ trợ.',s.active?'info':'warn'),
  policies:'<p>Gian hàng linh kiện mới tại '+regions[s.region]+'. Sản phẩm và điều kiện bên dưới là dữ liệu demo.</p><dl class="shop-policies"><dt>Giao hàng</dt><dd>Phí theo khu vực nhận và từng shop; dự kiến 3–5 ngày.</dd><dt>Đổi/trả</dt><dd>Tiếp nhận trong 7 ngày sau giao theo kịch bản demo; kiểm tra trước khi quyết định.</dd><dt>Bảo hành</dt><dd>Theo từng offer. Nơi tiếp nhận: '+esc(s.name)+'.</dd><dt>Dịch vụ</dt><dd>'+(s.consult?'Tư vấn cấu hình. ':'')+(s.assembly?'Lắp ráp khi shop cung cấp đủ bộ.':'Chưa hỗ trợ lắp ráp.')+'</dd></dl><div class="cluster">'+(s.consult&&s.active?a('Gửi cấu hình để tư vấn','consultation',{new:1,shop:s.id}):'')+a('Hỗ trợ đơn đã mua','orders')+'</div>',
  reviews:'<p>'+reviewSummary(s.id)+'</p>'+reviews.map(r=>'<p>'+r.shopRating+'/5 · '+esc(r.text)+'</p>').join(''),
  count:rows.length+' model phù hợp trong shop',chips:chips(),results:paging.shown.length?paging.shown.map(resultCard).join(''):empty('Không có sản phẩm phù hợp','Bỏ bớt bộ lọc hoặc xem toàn bộ gian hàng.',a('Xóa tìm kiếm','shop',{id:s.id})),pagination:paging.html,'compare-tray':compareTray()
 });configureFilters(s.id);
}
export function compare(){
 const ms=db().compare.map(model).filter(Boolean),keys=['Biến thể','Giá từ',...new Set(ms.flatMap(m=>Object.keys(m.specs))),'Nguồn'];
 renderPage('So sánh linh kiện',{
  breadcrumb:breadcrumb([['Linh kiện',link('search')],['So sánh model',null]]),heading:head('So sánh linh kiện','Chọn tối đa 4 model cùng danh mục',a('Thêm model','search',ms.length?{category:ms[0].category}:{})+button('Xóa danh sách','compare-clear')),
  comparison:!ms.length?empty('Chưa chọn model','Thêm model từ kết quả tìm kiếm.'): (ms.length===1?notice('Chọn thêm model cùng danh mục để đối chiếu.'): '')+'<div class="table-wrap" tabindex="0" aria-label="Bảng so sánh thông số cuộn ngang"><table class="data-table"><caption>'+esc(categories[ms[0].category])+' · dữ liệu demo</caption><thead><tr><th scope="col">Thông số</th>'+ms.map(m=>'<th scope="col">'+esc(m.name)+button('Bỏ','compare-remove',m.id)+'</th>').join('')+'</tr></thead><tbody>'+keys.map(k=>'<tr><th scope="row">'+esc(k)+'</th>'+ms.map(m=>'<td>'+(k==='Giá từ'?priceText(m):k==='Biến thể'?esc(variant(m)):k==='Nguồn'?'<a href="'+assetUrl('js/data.js')+'">Catalogue demo</a>':esc(m.specs[k]||'Chưa có dữ liệu'))+'</td>').join('')+'</tr>').join('')+'<tr><th scope="row">Chọn người bán</th>'+ms.map(m=>'<td>'+a('Chọn offer','model',{id:m.id})+'</td>').join('')+'</tr></tbody></table></div>'
 });
}
export function action(act,id){
 if(act==='filters-open'){openFilters();return true;}
 if(act==='filters-close'){document.querySelector('#filter-drawer').close();return true;}
 if(act==='offers-toggle'){const n=document.querySelector('#offer-comparison');n.hidden=!n.hidden;document.querySelector('[data-action=offers-toggle]').setAttribute('aria-expanded',String(!n.hidden));return true;}
 if(act==='offer-focus'){const n=document.getElementById('offer-'+id);n.scrollIntoView({block:'center'});const input=n.querySelector('[name=qty]');if(!input.disabled)input.focus();else{n.tabIndex=-1;n.focus();}return true;}
 if(act==='search-retry'||act==='remove-filter'){const p=new URLSearchParams(params);p.delete(act==='search-retry'?'error':id);if(act==='remove-filter'){p.delete('p');if(id==='category')for(const k of [...p.keys()])if(k.startsWith('tech:')||k==='spec'||k==='brand')p.delete(k);}go(page==='shop'?'shop':'search',Object.fromEntries(p));return true;}
 if(act==='compare-add'){
  const m=model(id),chosen=db().compare.map(model).filter(Boolean);if(!m)throw Error('Không tìm thấy model.');
  if(chosen.some(x=>x.category!==m.category))throw Error('Chỉ so sánh model cùng loại. Xóa danh sách hiện tại trước.');
  if(!db().compare.includes(id)){if(chosen.length>=4)throw Error('Tối đa 4 model.');tx(s=>s.compare.push(id));}
  updateTray();toast('Đã thêm '+m.name+' vào so sánh.');return true;
 }
 if(act==='compare-clear'||act==='compare-remove'){tx(s=>s.compare=act==='compare-clear'?[]:s.compare.filter(x=>x!==id));if(page==='compare')compare();else updateTray();return true;}
 return false;
}
export async function submitForm(name,f,d){
 if(name==='filters'||name==='shop-filter'){
  if(d.max&&+d.max<+d.min)throw Error('Giá đến phải lớn hơn hoặc bằng giá từ.');
  const values=Object.fromEntries(Object.entries(d).filter(([,v])=>v));go(name==='shop-filter'?'shop':'search',{...values,...context(),...(name==='shop-filter'?{id:params.get('id')}:{})});return true;
 }
 if(name==='region'){go('model',{...Object.fromEntries(params),region:d.region,...(!document.querySelector('#offer-comparison').hidden?{compareOffers:1}:{})});return true;}
 if(name==='offer'){
  const o=currentOffer(d.offerId),qty=Number(d.qty);if(!o||!sellable(o)||!Number.isInteger(qty)||qty<1||qty>o.stock)throw Error('Offer không còn khả dụng hoặc số lượng vượt tồn demo.');
  if(d.target==='cart'){
   const put=()=>{addItems([{offerId:o.id,qty}]);go('cart');};
   if(db().checkout.proposal)dialog('Chuyển giỏ proposal sang mua lẻ?','Thêm sản phẩm sẽ bỏ điều kiện lắp ráp và báo giá trọn bộ. Các món đang có được giữ.',put);else put();
  }else{
   const b=db().draftBuild,cat=model(o.modelId).category;
   if(params.has('slot')&&(params.get('slot')!==cat||params.get('build')!==b.id||+params.get('version')!==b.version))throw Error('Cấu hình đã đổi hoặc sai slot. Quay về Builder chọn lại.');
   const put=()=>{const latest=currentOffer(o.id);if(!sellable(latest)||qty>latest.stock)throw Error('Offer vừa thay đổi; chọn lại.');if(db().draftBuild.id!==b.id||db().draftBuild.version!==b.version)throw Error('Cấu hình vừa thay đổi; quay về Builder.');tx(s=>{s.draftBuild.slots[cat]={offerId:o.id,qty,owned:false};s.draftBuild.version++;});go('builder');};
   if(b.slots[cat])dialog('Thay linh kiện '+cat+'?','Thay '+esc(model(currentOffer(b.slots[cat].offerId).modelId).name)+' bằng '+esc(model(o.modelId).name)+'. Các slot khác được giữ.',put);else put();
  }return true;
 }
 if(name==='question'){if(!requireUser())return true;if(!d.text.trim())throw Error('Nhập câu hỏi.');if(!modelOffers(params.get('id')).some(o=>o.shopId===d.shopId))throw Error('Shop không có offer cho model này.');tx(s=>s.questions.push({id:uid('QA'),userId:user().id,modelId:params.get('id'),shopId:d.shopId,text:d.text}));detail();toast('Đã gửi câu hỏi demo.');return true;}
 return false;
}
