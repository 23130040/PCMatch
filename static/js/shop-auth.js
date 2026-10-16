import {renderTemplate,params,link,go,field,submit,form,mount,toast,enterShop} from './shop-ui.js';
import {sdb,stx,seller,shopLogin,fingerprint,uid,getOrCreateDemoSeller,shops} from './shop-store.js';

export function loginPage(){
  if(seller()){enterShop();return;}
  mount('Đăng nhập Kênh bán',renderTemplate("shop-auth-loginPage-2", {
    shopLoginForm: form('shop-login',renderTemplate("shop-auth-loginPage-1", {
      emailField: field('Email','email','shop@pcmatch.local','email','required autocomplete="username"'),
      forgotUrl: link('forgot'),
      content: submit('Đăng nhập')
    })),
    registerUrl: link('register')
  }));
}

export function registerPage(){
  if(seller()){go('dashboard');return;}
  const step=parseInt(params.get('step')||'1');
  mount('Đăng ký Kênh bán',renderTemplate("shop-auth-registerPage-1", {
    contentRows: ['Thông tin tài khoản','Thông tin shop','Xác minh'].map((s,i)=>renderTemplate("shop-auth-registerPage-2", {
      stepContent: step===i+1?' is-current':step>i+1?' is-done':'',
      stepContent2: step>i+1?'✓':i+1,
      s: s
    })).join(''),
    min: Math.min(step/3*100,100),
    content: renderRegStep(step)
  }));
}

function renderRegStep(step){
  if(step===1)return form('shop-reg-1',renderTemplate("shop-auth-renderRegStep-1", {
    nameField: field('Tên đầy đủ','name','','text','required maxlength="80"'),
    emailField: field('Email','email','','email','required autocomplete="email"'),
    phoneField: field('Số điện thoại','phone','','tel','required pattern="0[0-9]{9}"'),
    loginUrl: link('login'),
    content: submit('Tiếp theo')
  }));
  if(step===2)return form('shop-reg-2',renderTemplate("shop-auth-renderRegStep-3", {
    shopNameField: field('Tên shop','shopName','','text','required maxlength="100"'),
    taxCodeField: field('Mã số thuế (nếu có)','taxCode','','text','maxlength="14"'),
    categoryField: field('Ngành hàng chính','category','Linh kiện máy tính','text','required'),
    addressField: field('Địa chỉ kho / văn phòng','address','','text','required minlength="10" maxlength="200"'),
    content: submit('Tiếp theo')
  }));
  return renderTemplate("shop-auth-renderRegStep-2", {
    loginUrl: link('login')
  });
}

export function forgotPage(){
  mount('Quên mật khẩu',renderTemplate("shop-auth-forgotPage-1", {
    shopForgotForm: form('shop-forgot',field('Email đã đăng ký','email','','email','required')+submit('Gửi liên kết khôi phục')),
    loginUrl: link('login')
  }));
}

export function action(act,id){
  if(act==='shop-eye'){
    const wrap=document.querySelectorAll('.password-wrap input');
    if(!wrap.length)return true;
    const show=wrap[0].type==='password';
    wrap.forEach(x=>x.type=show?'text':'password');
    document.querySelectorAll('.password-eye').forEach(b=>{b.textContent=show?'🙈':'👁';b.setAttribute('aria-label',show?'Ẩn mật khẩu':'Hiện mật khẩu');});
    return true;
  }
  if(act==='shop-demo-login'){
    (async()=>{
      let sel=getOrCreateDemoSeller();
      if(!sel.password){const password=await fingerprint('Demo123456');stx(()=>sel.password=password);}
      shopLogin(sel);
      enterShop();
    })().catch(e=>toast(e.message));
    return true;
  }
  if(act==='reg-back'){go('register',{step:'1'});return true;}
  return false;
}

export async function submitForm(name,f,d){
  if(name==='shop-login'){
    if(d.email.trim().toLowerCase()==='shop@pcmatch.local'){
      const demo=getOrCreateDemoSeller();
      if(!demo.password){const password=await fingerprint('Demo123456');stx(()=>demo.password=password);}
    }
    const sel=sdb().sellers.find(s=>s.email===d.email.trim().toLowerCase());
    if(!sel||sel.password!==await fingerprint(d.password))throw Error('Email hoặc mật khẩu không đúng.');
    if(sel.suspended)throw Error('Tài khoản đang bị tạm ngưng.');
    shopLogin(sel);
    enterShop();
    return true;
  }
  if(name==='shop-reg-1'){
    if(!d.name.trim())throw Error('Nhập họ tên đầy đủ.');
    if(d.password!==d.confirm)throw Error('Mật khẩu nhập lại không khớp.');
    if(d.password.length<8)throw Error('Mật khẩu cần ít nhất 8 ký tự.');
    const email=d.email.trim().toLowerCase();
    if(sdb().sellers.some(s=>s.email===email))throw Error('Email đã được đăng ký.');
    sessionStorage.setItem('pcmatch-shop-reg',JSON.stringify({name:d.name.trim(),email,password:await fingerprint(d.password),phone:d.phone}));
    go('register',{step:'2'});
    return true;
  }
  if(name==='shop-reg-2'){
    const step1=JSON.parse(sessionStorage.getItem('pcmatch-shop-reg')||'{}');
    if(!step1.email)throw Error('Phiên đăng ký hết hạn. Bắt đầu lại.');
    if(!d.shopName.trim())throw Error('Nhập tên shop.');
    if(sdb().sellers.some(s=>s.email===step1.email))throw Error('Email đã được đăng ký.');
    if(!d.address.trim()||d.address.trim().length<10)throw Error('Nhập địa chỉ đầy đủ (ít nhất 10 ký tự).');
    const shop=shops.find(s=>s.active)||shops[0];
    const sel={
      id:uid('SELLER'),name:step1.name,email:step1.email,password:step1.password,phone:step1.phone,
      shopId:shop.id,shopName:d.shopName.trim(),taxCode:d.taxCode||'',category:d.category||'Linh kiện',
      address:d.address.trim(),businessType:d.businessType||'Cá nhân kinh doanh',
      joinedAt:Date.now(),suspended:false,verified:false,rating:0,totalProducts:0,totalSold:0
    };
    stx(s=>s.sellers.push(sel));
    sessionStorage.removeItem('pcmatch-shop-reg');
    go('register',{step:'3'});
    return true;
  }
  if(name==='shop-forgot'){
    toast('Demo chưa hỗ trợ khôi phục mật khẩu hoặc gửi email.');
    return true;
  }
  return false;
}
