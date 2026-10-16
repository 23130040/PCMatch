import {renderTemplate,esc,params,go,link,a,btn,field,select,textarea,submit,form,mount,toast,dialog,requireSeller} from './shop-ui.js';
import {mineSeller,stx,seller,uid,money} from './shop-store.js';
import {categories} from './shop-data.js';

const CAT_OPTS=Object.fromEntries(Object.entries(categories));

export function offers(){
  if(!requireSeller())return;
  const q=(params.get('q')||'').toLowerCase();
  const cat=params.get('cat')||'';
  const statusFilter=params.get('status')||'';
  let products=mineSeller('shopProducts');
  const total=products.length;
  const selling=products.filter(p=>p.active&&p.stock>0).length;
  const outOfStock=products.filter(p=>p.stock===0&&p.active).length;
  const hidden=products.filter(p=>!p.active).length;

  if(q)products=products.filter(p=>p.name.toLowerCase().includes(q)||p.brand?.toLowerCase().includes(q));
  if(cat)products=products.filter(p=>p.category===cat);
  if(statusFilter==='active')products=products.filter(p=>p.active&&p.stock>0);
  else if(statusFilter==='out')products=products.filter(p=>p.stock===0&&p.active);
  else if(statusFilter==='inactive')products=products.filter(p=>!p.active);

  const isNew=params.has('new');
  const editId=params.get('edit');
  const editProduct=editId?mineSeller('shopProducts').find(p=>p.id===editId):null;

  const allCount=mineSeller('shopProducts').length;
  const activeCount=mineSeller('shopProducts').filter(p=>p.active&&p.stock>0).length;
  const outCount=mineSeller('shopProducts').filter(p=>p.stock===0&&p.active).length;
  const hiddenCount=mineSeller('shopProducts').filter(p=>!p.active).length;

  mount('Sản phẩm bán',renderTemplate("shop-products-offers-3", {
    dashboardUrl: link('dashboard'),
    total: total,
    offersLink: a('+ Thêm sản phẩm','offers',{new:'1'},'primary'),
    total2: total,
    outOfStock: outOfStock,
    selling: selling,
    hidden: hidden,
    isNewContent: isNew||editProduct?renderProductForm(editProduct):renderTemplate("shop-products-offers-7", {
      get: esc(params.get('q')||''),
      entriesRows: Object.entries(CAT_OPTS).map(([k,v])=>renderTemplate("shop-products-offers-4", {
        k: esc(k),
        kContent: k===cat?'selected':'',
        v: esc(v)
      })).join(''),
      length: products.length,
      contentContent: !statusFilter?'is-active':'',
      allCount: allCount,
      statusFilterContent: statusFilter==='active'?'is-active':'',
      activeCount: activeCount,
      statusFilterContent2: statusFilter==='out'?'is-active':'',
      outCount: outCount,
      statusFilterContent3: statusFilter==='inactive'?'is-active':'',
      hiddenCount: hiddenCount,
      lengthContent: products.length?renderTemplate("shop-products-offers-6", {
        productsRows: products.map(p=>renderTemplate("shop-products-offers-5", {
          name: esc(p.name),
          name2: esc(p.name),
          id: esc(p.id),
          value: esc(categories[p.category]||p.category),
          priceMoney: money(p.price),
          stockContent: p.stock===0?'text-danger':p.stock<=3?'text-warn':'',
          stock: p.stock,
          sold: p.sold||0,
          content: _productStatus(p),
          offersLink: a('✎ Sửa','offers',{edit:p.id},'sa-detail-btn'),
          activeContent: p.active?'sa-detail-btn--warn':'',
          id2: esc(p.id),
          activeContent2: p.active?'Ẩn':'Hiện',
          id3: esc(p.id)
        })).join('')
      }):renderTemplate("shop-products-offers-1", {
        offersLink: a('+ Thêm sản phẩm','offers',{new:'1'},'primary')
      }),
      lengthContent2: products.length?renderTemplate("shop-products-offers-2", {
        length: products.length,
        length2: products.length
      }):''
    })
  }));

  // Gắn filter tabs
  document.querySelectorAll('[data-action="sa-filter"]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const s=btn.dataset.status;
      const newParams=new URLSearchParams(location.search);
      if(s)newParams.set('status',s);else newParams.delete('status');
      location.href=link('offers',Object.fromEntries(newParams));
    });
  });
  // Search inline
  const si=document.getElementById('sa-search-input');
  if(si){
    si.addEventListener('keydown',e=>{
      if(e.key==='Enter'){
        const newParams=new URLSearchParams(location.search);
        if(si.value.trim())newParams.set('q',si.value.trim());else newParams.delete('q');
        location.href=link('offers',Object.fromEntries(newParams));
      }
    });
  }
  const cs=document.getElementById('sa-cat-select');
  if(cs){
    cs.addEventListener('change',()=>{
      const newParams=new URLSearchParams(location.search);
      if(cs.value)newParams.set('cat',cs.value);else newParams.delete('cat');
      location.href=link('offers',Object.fromEntries(newParams));
    });
  }
}

function _productStatus(p){
  if(p.active&&p.stock>0)return renderTemplate("shop-products-_productStatus-1");
  if(p.active&&p.stock===0)return renderTemplate("shop-products-_productStatus-2");
  return renderTemplate("shop-products-_productStatus-3");
}

function renderProductForm(product){
  const isEdit=!!product;
  return renderTemplate("shop-products-renderProductForm-2", {
    isEditContent: isEdit?'Sửa sản phẩm: '+esc(product.name):'Thêm sản phẩm mới',
    productFormForm: form('product-form',renderTemplate("shop-products-renderProductForm-1", {
      isEditContent: isEdit?esc(product.id):'',
      categoryField: select('Danh mục sản phẩm','category',CAT_OPTS,isEdit?product.category:'CPU'),
      nameField: field('Tên sản phẩm','name',isEdit?product.name:'','text','required maxlength="200"'),
      brandField: field('Thương hiệu','brand',isEdit?product.brand||'':'','text','required maxlength="60"'),
      priceField: field('Giá bán (VND)','price',isEdit?product.price:'','number','required min="1000" step="1000"'),
      stockField: field('Số lượng tồn kho','stock',isEdit?product.stock:'','number','required min="0" step="1"'),
      warrantyField: field('Thời gian bảo hành (tháng)','warranty',isEdit?product.warranty||36:'36','number','required min="0" max="120"'),
      descriptionField: textarea('Mô tả sản phẩm','description',isEdit?product.description||'':''),
      content: submit(isEdit?'Lưu thay đổi':'Thêm sản phẩm'),
      offersLink: a('Hủy','offers')
    }))
  });
}

export function inventory(){
  if(!requireSeller())return;
  const products=mineSeller('shopProducts');
  const low=products.filter(p=>p.active&&p.stock<=3);
  const out=products.filter(p=>p.active&&p.stock===0);
  const ok=products.filter(p=>p.active&&p.stock>3);

  mount('Tồn kho',renderTemplate("shop-products-inventory-1", {
    dashboardUrl: link('dashboard'),
    length: products.length,
    length2: ok.length,
    length3: low.length,
    length4: out.length,
    lengthContent: low.length?renderTemplate("shop-products-inventory-3", {
      lowRows: low.map(p=>renderTemplate("shop-products-inventory-2", {
        stockContent: p.stock===0?'sa-row--danger':'sa-row--warn',
        name: esc(p.name),
        stockContent2: p.stock===0?'var(--color-red)':'var(--color-amber)',
        stock: p.stock,
        sold: p.sold||0,
        id: esc(p.id),
        stock2: p.stock
      })).join('')
    }):'',
    filterRows: products.filter(p=>p.active).map(p=>renderTemplate("shop-products-inventory-4", {
      name: esc(p.name),
      value: esc(categories[p.category]||p.category),
      priceMoney: money(p.price),
      stockContent: p.stock===0?'text-danger':p.stock<=3?'text-warn':'',
      stock: p.stock,
      sold: p.sold||0,
      id: esc(p.id),
      stock2: p.stock
    })).join('')
  }));
}

export function action(act,id){
  if(!requireSeller())return true;
  if(act==='toggle-product'){
    const p=mineSeller('shopProducts').find(x=>x.id===id);
    if(!p)throw Error('Không tìm thấy sản phẩm.');
    dialog(`${p.active?'Ẩn':'Hiện'} sản phẩm?`,`Sản phẩm "${esc(p.name)}" sẽ ${p.active?'không còn hiển thị':'được hiển thị trở lại'} với người mua.`,()=>{
      stx(()=>p.active=!p.active);
      offers();
      toast(`Đã ${p.active?'hiện':'ẩn'} sản phẩm.`);
    });
    return true;
  }
  if(act==='delete-product'){
    const p=mineSeller('shopProducts').find(x=>x.id===id);
    if(!p)throw Error('Không tìm thấy sản phẩm.');
    dialog('Xóa sản phẩm?',`Xóa "${esc(p.name)}" khỏi danh sách? Không thể khôi phục.`,()=>{
      stx(s=>s.shopProducts=s.shopProducts.filter(x=>x.id!==id));
      offers();
      toast('Đã xóa sản phẩm.');
    });
    return true;
  }
  return false;
}

export async function submitForm(name,f,d){
  if(!requireSeller())return true;
  if(name==='prod-filter'){go('offers',Object.fromEntries(Object.entries(d).filter(([,v])=>v)));return true;}
  if(name==='product-form'){
    if(!d.name.trim())throw Error('Nhập tên sản phẩm.');
    if(!d.brand.trim())throw Error('Nhập thương hiệu.');
    if(!Number.isFinite(+d.price)||+d.price<1000)throw Error('Giá cần ít nhất 1.000 đ.');
    if(!Number.isSafeInteger(+d.stock)||+d.stock<0)throw Error('Tồn kho phải là số nguyên không âm.');
    if(!Number.isSafeInteger(+d.warranty)||+d.warranty<0||+d.warranty>120)throw Error('Bảo hành phải từ 0 đến 120 tháng.');
    if(!Object.hasOwn(CAT_OPTS,d.category))throw Error('Danh mục không hợp lệ.');
    if(d.id){
      const p=mineSeller('shopProducts').find(x=>x.id===d.id);
      if(!p)throw Error('Không có quyền sửa sản phẩm này.');
      stx(()=>Object.assign(p,{name:d.name.trim(),brand:d.brand.trim(),category:d.category,price:+d.price,stock:+d.stock,warranty:+d.warranty,description:d.description.trim()}));
      toast('Đã cập nhật sản phẩm.');
    }else{
      const sel=seller();
      const newProduct={id:uid('SP'),sellerId:sel.id,shopId:sel.shopId,name:d.name.trim(),brand:d.brand.trim(),category:d.category,price:+d.price,stock:+d.stock,sold:0,warranty:+d.warranty,description:d.description.trim(),active:true,createdAt:Date.now(),images:[]};
      stx(s=>s.shopProducts.push(newProduct));
      toast('Đã thêm sản phẩm mới.');
    }
    go('offers');
    return true;
  }
  if(name==='update-stock'){
    if(!Number.isSafeInteger(+d.qty)||+d.qty<0)throw Error('Tồn kho phải là số nguyên không âm.');
    const p=mineSeller('shopProducts').find(x=>x.id===d.id);
    if(!p)throw Error('Không tìm thấy sản phẩm.');
    stx(()=>p.stock=+d.qty);
    inventory();
    toast(`Đã cập nhật tồn kho: ${p.name} → ${d.qty} sản phẩm`);
    return true;
  }
  return false;
}
