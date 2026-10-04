import {models,model,shops,categories,regions,money} from './data.js';
import {mine} from './store.js';
import {esc,link,a,empty} from './ui.js';
import {assetUrl} from './routing.js';
import {modelOffers,sellable,imagePath} from './catalog-data.js';
import {homeBanners,newestModels,bySold} from './merchandising-data.js';
import {renderPage} from './catalog-view.js';
const liveOffers=m=>modelOffers(m.id).filter(o=>sellable(o)&&o.stock>0);
function commercial(m){const offers=liveOffers(m);return {count:new Set(offers.map(o=>o.shopId)).size,price:offers.length?money(Math.min(...offers.map(o=>o.price))):'Chưa có offer còn hàng'};}
function image(m,eager=false){return '<div class="home-media"><img data-product-image src="'+esc(m.image?assetUrl('images/products/'+m.image):imagePath(m))+'" alt="'+esc((m.image?'Ảnh tham khảo ':'Hình minh họa danh mục cho ')+m.name)+'" width="480" height="320" loading="'+(eager?'eager':'lazy')+'" decoding="async"><div class="image-fallback" hidden role="img" aria-label="Không tải được ảnh '+esc(m.name)+'"><strong>'+esc(categories[m.category])+'</strong><span>Ảnh đang không khả dụng</span></div></div>';}
const specs=m=>Object.entries(m.specs).slice(0,3).map(([k,v])=>'<span>'+esc(k)+': '+esc(v)+'</span>').join('');
function banner(b,index){const m=model(b.modelId);return '<article class="home-banner home-banner--'+b.id+'" data-banner="'+b.id+'"><div class="home-banner-copy"><'+(index?'h2':'h1')+'>'+esc(b.title)+'</'+(index?'h2':'h1')+'><p>'+esc(b.description)+'</p>'+a(b.cta,b.route,b.query,index?'secondary':'primary')+'</div>'+(m?image(m,true):'')+'</article>';}
function newestSlide(m,index,total){
 const c=commercial(m);
 return '<article class="home-newest-slide" id="newest-slide-'+index+'" data-slide-model="'+esc(m.id)+'" data-theme="'+esc(m.category)+'" role="group" aria-roledescription="slide" aria-label="'+(index+1)+' / '+total+' · '+esc(m.name)+'" '+(index?'hidden':'')+'><div class="home-newest-copy"><p class="home-newest-category">'+esc(categories[m.category])+'</p><h3>'+esc(m.name)+'</h3><p class="muted">Thêm vào catalogue demo ngày <time datetime="'+esc(m.createdAt)+'">'+new Intl.DateTimeFormat('vi-VN',{timeZone:'UTC'}).format(new Date(m.createdAt))+'</time></p><div class="home-specs">'+specs(m)+'</div><p class="home-price">'+(c.count?'Giá demo từ <strong>'+c.price+'</strong>':c.price)+' · '+c.count+' shop còn hàng</p><div class="cluster">'+a('Xem sản phẩm','model',{id:m.id},'primary')+a('Xem các shop bán','model',{id:m.id,compareOffers:1})+'</div></div>'+image(m)+'</article>';
}
function newest(items){
 if(!items.length)return '';
 const arrow=direction=>'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="'+(direction==='prev'?'m14 6-6 6 6 6':'m10 6 6 6-6 6')+'"/></svg>';
 return '<header class="home-newest-heading"><h2 id="newest-title">Sản phẩm mới nhất</h2><p>Khám phá linh kiện mới thêm vào catalogue demo</p></header><div class="home-newest-stage">'+items.map((m,i)=>newestSlide(m,i,items.length)).join('')+'<button class="btn btn--secondary home-newest-arrow" type="button" '+(items.length<2?'hidden':'')+'  data-newest-step="-1" aria-label="Banner trước">'+arrow('prev')+'</button><button class="btn btn--secondary home-newest-arrow" type="button" '+(items.length<2?'hidden':'')+'  data-newest-step="1" aria-label="Banner tiếp theo">'+arrow('next')+'</button></div><div class="home-newest-controls" '+(items.length<2?'hidden':'')+'><div class="home-newest-dots" role="group" aria-label="Chọn banner sản phẩm">'+items.map((m,i)=>'<button type="button" data-newest-index="'+i+'" aria-controls="newest-slide-'+i+'" aria-pressed="'+(!i)+'" aria-label="Xem banner '+esc(categories[m.category])+' · '+esc(m.name)+'"><span aria-hidden="true"></span></button>').join('')+'</div><span data-newest-position aria-hidden="true">1 / '+items.length+'</span></div><p class="sr-only" data-newest-status role="status" aria-atomic="true"></p>';
}
function installNewest(items){
 const root=document.querySelector('.home-newest');root.hidden=!items.length;
 if(!items.length){delete root.dataset.modelId;return;}
 const slides=[...root.querySelectorAll('.home-newest-slide')],dots=[...root.querySelectorAll('[data-newest-index]')];let current=0;
 root.dataset.modelId=items[0].id;
 function show(index){
  current=(index+items.length)%items.length;
  slides.forEach((slide,i)=>slide.hidden=i!==current);
  dots.forEach((dot,i)=>dot.setAttribute('aria-pressed',String(i===current)));
  root.dataset.modelId=items[current].id;
  root.querySelector('[data-newest-position]').textContent=(current+1)+' / '+items.length;
  root.querySelector('[data-newest-status]').textContent='Banner '+(current+1)+' / '+items.length+': '+items[current].name;
 }
 root.onclick=e=>{const step=e.target.closest('[data-newest-step]'),dot=e.target.closest('[data-newest-index]');if(step)show(current+Number(step.dataset.newestStep));if(dot)show(Number(dot.dataset.newestIndex));};
 root.onkeydown=e=>{
  if(e.altKey||e.ctrlKey||e.metaKey||!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
  e.preventDefault();show(e.key==='Home'?0:e.key==='End'?items.length-1:current+(e.key==='ArrowRight'?1:-1));
  if(e.target.closest('.home-newest-slide'))slides[current].querySelector('a').focus({preventScroll:true});
  else if(e.target.matches('[data-newest-index]'))dots[current].focus({preventScroll:true});
 };
 const stage=root.querySelector('.home-newest-stage');let touch=null;
 stage.addEventListener('touchstart',e=>{touch=e.touches.length===1?{x:e.touches[0].clientX,y:e.touches[0].clientY}:null;},{passive:true});
 stage.addEventListener('touchend',e=>{if(!touch)return;const end=e.changedTouches[0],dx=end.clientX-touch.x,dy=end.clientY-touch.y;touch=null;if(Math.abs(dx)>60&&Math.abs(dx)>Math.abs(dy)*1.5)show(current+(dx<0?1:-1));},{passive:true});
 stage.addEventListener('touchcancel',()=>touch=null,{passive:true});
}
function bestCard(m){const c=commercial(m);return '<article class="catalog-card" data-home-model="'+m.id+'" data-sold="'+m.soldCount+'"><a href="'+link('model',{id:m.id})+'">'+image(m)+'</a><div class="catalog-body"><p>'+esc(categories[m.category])+'</p><h3>'+a(m.name,'model',{id:m.id},'text')+'</h3><p>'+esc(Object.values(m.specs).slice(0,2).join(' · '))+'</p><div class="catalog-price"><small>Giá demo từ</small><strong>'+c.price+'</strong><span>'+c.count+' shop còn hàng · Đã bán '+m.soldCount+' (demo)</span></div><div class="cluster">'+a('Xem chi tiết','model',{id:m.id},'primary')+a('Xem các shop bán','model',{id:m.id,compareOffers:1})+'</div></div></article>';}
export function home(){
 const latest=newestModels(models),best=models.filter(m=>Number.isFinite(m.soldCount)&&m.soldCount>=0).slice().sort(bySold).slice(0,4);
 renderPage('Mua linh kiện',{
  banners:homeBanners.map(banner).join(''),
  categories:Object.entries(categories).map(([k,v])=>'<a href="'+link('search',{category:k})+'"><strong>'+k+'</strong><span>'+v+'</span></a>').join(''),
  newest:newest(latest),bestsellers:best.length?best.map(bestCard).join(''):empty('Chưa có dữ liệu bán chạy','Khám phá catalogue để chọn linh kiện.'),
  build:'<div><h2>Cần chọn cả cấu hình?</h2><p>Tự chọn từng linh kiện hoặc gửi nhu cầu để shop đề xuất.</p></div><div class="cluster">'+a('Tự build PC','builder')+a('Build theo ngân sách','requests',mine('requests').length?{}:{new:1})+'</div>',
  shops:shops.map(s=>'<a href="'+link('shop',{id:s.id})+'"><strong>'+esc(s.name)+'</strong><span>'+regions[s.region]+' · '+(s.active?'Đang bán (demo)':'Tạm ngừng bán')+'</span></a>').join('')
 });
 document.body.classList.add('home-page');installNewest(latest);
}
