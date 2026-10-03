// Native constraints remain the source of truth; errors also stay beside fields.
export function fieldError(form, name, message) {
 const input=form.elements.namedItem(name);if(!input)return;
 let error=input.parentElement.querySelector('.field-error');
 if(!error){error=document.createElement('small');error.className='field-error';error.id='error-'+crypto.randomUUID();input.parentElement.append(error);}
 error.textContent=message;input.setAttribute('aria-invalid','true');input.setAttribute('aria-describedby',error.id);
}
export function rejectField(form,name,message){fieldError(form,name,message);throw Error(message);}
export function installValidation(){
 document.addEventListener('invalid',e=>{const input=e.target,f=input.closest('form');if(!f)return;fieldError(f,input.name,input.validity.valueMissing?'Vui lòng điền hoặc xác nhận trường này.':input.validity.typeMismatch?'Nhập email đúng định dạng.':input.validity.patternMismatch?'Nhập số điện thoại gồm 10 chữ số, bắt đầu bằng 0.':input.validationMessage);},true);
 document.addEventListener('input',e=>{const input=e.target;if(input.hasAttribute('aria-invalid')){input.removeAttribute('aria-invalid');input.removeAttribute('aria-describedby');input.parentElement.querySelector('.field-error')?.remove();}});
}
