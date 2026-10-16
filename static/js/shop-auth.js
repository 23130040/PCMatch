import {sdb,stx,seller,shopLogin,shopLogout,fingerprint,uid,getOrCreateDemoSeller,shops} from './shop-store.js';
import {esc,params,link,go,field,submit,form,notice,head,mount,toast,operation} from './shop-ui.js';

const PASSWORD_PLACEHOLDER='';

export function loginPage(){
  if(seller()){go('dashboard');return;}
  mount('Đăng nhập Kênh bán',`
    <div class="shop-auth-page">
      <div class="shop-auth">
        <div class="shop-auth__card">
          <div class="shop-auth__brand">
            <a class="logo" href="/">
              <svg width="28" height="28" viewBox="0 0 32 32" fill="none" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#1e40af"/><path d="M8 24V10l8-4 8 4v14M12 24v-8h8v8" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>
              PCMatch
            </a>
            <h1>Kênh bán</h1>
            <p>Đăng nhập để quản lý shop của bạn</p>
          </div>
          <div id="shop-auth-error" class="shop-auth__error" hidden></div>
          ${form('shop-login',`
            <div class="shop-auth__form">
              ${field('Email','email','shop@pcmatch.local','email','required autocomplete="username"')}
              <label class="field"><span>Mật khẩu</span><span class="password-wrap"><input name="password" type="password" value="Demo123456" required autocomplete="current-password"><button type="button" class="password-eye" data-action="shop-eye" aria-label="Hiện mật khẩu">👁</button></span></label>
              <div class="shop-auth__row">
                <label class="shop-auth__remember check"><input type="checkbox" name="remember"> <span>Ghi nhớ</span></label>
                <a href="${link('forgot')}" class="linklike">Quên mật khẩu?</a>
              </div>
              ${submit('Đăng nhập')}
            </div>
          `)}
          <button type="button" class="btn btn--secondary" style="width:100%" data-action="shop-demo-login">Vào luôn shop demo</button>
          <p class="shop-auth__switch">Chưa có tài khoản? <a href="${link('register')}">Đăng ký người bán</a></p>
          <div class="shop-auth__footer">
            <span>PCMatch</span><span>·</span>
            <a href="/">Trang mua hàng</a>
          </div>
        </div>
      </div>
    </div>
  `);
}

export function registerPage(){
  if(seller()){go('dashboard');return;}
  const step=parseInt(params.get('step')||'1');
  mount('Đăng ký Kênh bán',`
    <div class="shop-auth-page">
      <div class="shop-reg">
        <div class="shop-reg__card">
          <div class="shop-reg__brand">
            <h1 id="reg-title">Đăng ký Kênh bán</h1>
            <p>Tạo tài khoản shop để bắt đầu bán hàng trên PCMatch</p>
          </div>
          <ol class="reg-steps">
            ${['Thông tin tài khoản','Thông tin shop','Xác minh'].map((s,i)=>`<li class="reg-steps__item${step===i+1?' is-current':step>i+1?' is-done':''}"><div class="reg-steps__num">${step>i+1?'✓':i+1}</div><span>${s}</span></li>`).join('')}
          </ol>
          <div class="reg-progress"><i style="width:${Math.min(step/3*100,100)}%"></i></div>
          ${renderRegStep(step)}
        </div>
      </div>
    </div>
  `);
}

function renderRegStep(step){
  if(step===1)return form('shop-reg-1',`
    <div class="reg-pane">
      <h2>Thông tin tài khoản đăng nhập</h2>
      ${field('Tên đầy đủ','name','','text','required maxlength="80"')}
      ${field('Email','email','','email','required autocomplete="email"')}
      <label class="field"><span>Mật khẩu</span><span class="password-wrap"><input name="password" type="password" required minlength="8"><button type="button" class="password-eye" data-action="shop-eye" aria-label="Hiện mật khẩu">👁</button></span></label>
      <div class="pw-meter" id="pw-meter" data-level="0"><i></i><i></i><i></i><i></i></div>
      <label class="field"><span>Nhập lại mật khẩu</span><span class="password-wrap"><input name="confirm" type="password" required minlength="8"><button type="button" class="password-eye" data-action="shop-eye" aria-label="Hiện mật khẩu">👁</button></span></label>
      ${field('Số điện thoại','phone','','tel','required pattern="0[0-9]{9}"')}
      <div class="reg-nav"><a href="${link('login')}" class="btn btn--secondary">Đã có tài khoản</a>${submit('Tiếp theo')}</div>
    </div>
  `);
  if(step===2)return form('shop-reg-2',`
    <div class="reg-pane">
      <h2>Thông tin shop</h2>
      ${field('Tên shop','shopName','','text','required maxlength="100"')}
      <div class="biz-types">
        <label class="check"><input type="radio" name="businessType" value="Cá nhân kinh doanh" required checked> <span>Cá nhân kinh doanh</span></label>
        <label class="check"><input type="radio" name="businessType" value="Công ty / Doanh nghiệp"> <span>Công ty / Doanh nghiệp</span></label>
      </div>
      ${field('Mã số thuế (nếu có)','taxCode','','text','maxlength="14"')}
      ${field('Ngành hàng chính','category','Linh kiện máy tính','text','required')}
      ${field('Địa chỉ kho / văn phòng','address','','text','required minlength="10" maxlength="200"')}
      <div class="reg-nav"><button type="button" class="btn btn--secondary" data-action="reg-back">Quay lại</button>${submit('Tiếp theo')}</div>
    </div>
  `);
  return `<div class="reg-pane reg-success">
    <div class="reg-success__icon">✓</div>
    <h2>Đăng ký thành công!</h2>
    <p>Tài khoản demo của bạn đã được tạo. Đăng nhập để bắt đầu quản lý shop.</p>
    <a href="${link('login')}" class="btn btn--primary">Đăng nhập ngay</a>
  </div>`;
}

export function forgotPage(){
  mount('Quên mật khẩu',`
    <div class="shop-auth-page">
      <div class="shop-auth">
        <div class="shop-auth__card">
          <div class="shop-auth__brand">
            <h1>Khôi phục mật khẩu</h1>
            <p>Nhập email để nhận liên kết đặt lại mật khẩu (mô phỏng)</p>
          </div>
          ${form('shop-forgot',field('Email đã đăng ký','email','','email','required')+submit('Gửi liên kết khôi phục'))}
          <p style="text-align:center"><a href="${link('login')}">Quay lại đăng nhập</a></p>
        </div>
      </div>
    </div>
  `);
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
      if(!sel.password)sel.password=await fingerprint('Demo123456');
      shopLogin(sel);
      const next=params.get('next');
      location.href=next&&next.startsWith('/')?next:link('dashboard');
    })().catch(e=>toast(e.message));
    return true;
  }
  if(act==='reg-back'){go('register',{step:'1'});return true;}
  return false;
}

export async function submitForm(name,f,d){
  if(name==='shop-login'){
    const sel=sdb().sellers.find(s=>s.email===d.email.trim().toLowerCase());
    if(!sel||sel.password!==await fingerprint(d.password))throw Error('Email hoặc mật khẩu không đúng.');
    if(sel.suspended)throw Error('Tài khoản đang bị tạm ngưng.');
    shopLogin(sel);
    const next=params.get('next');
    location.href=next&&next.startsWith('/')?next:link('dashboard');
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
    const sel=sdb().sellers.find(s=>s.email===d.email.trim().toLowerCase());
    const resetToken=uid('RESET');
    f.insertAdjacentHTML('afterend',notice('Liên kết demo (không gửi email thật): <a href="'+link('login')+'?reset='+resetToken+'">Đặt lại mật khẩu</a>'));
    return true;
  }
  return false;
}
