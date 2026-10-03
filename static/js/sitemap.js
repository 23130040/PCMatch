const input=document.querySelector('.topbar input[type=search]');
const groups=[...document.querySelectorAll('.screen-group')];
const status=document.createElement('p');status.className='container';status.setAttribute('role','status');
document.querySelector('#catalog').prepend(status);
input.addEventListener('input',()=>{
 const term=input.value.trim().toLocaleLowerCase('vi');let count=0;
 for(const group of groups){let visible=0;for(const item of group.querySelectorAll('.screen-link')){const match=item.textContent.toLocaleLowerCase('vi').includes(term);item.hidden=!match;item.style.display=match?'':'none';visible+=Number(match);}group.hidden=!visible;group.style.display=visible?'':'none';count+=visible;}
 status.textContent=term?(count?count+' màn hình phù hợp.':'Không tìm thấy màn hình. Xóa hoặc đổi từ khóa để thử lại.'):'';
});
