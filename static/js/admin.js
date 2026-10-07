const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const toast=(m,t='success')=>{const e=document.createElement('div');e.className='toast '+t;e.textContent=m;$('#toasts').append(e);setTimeout(()=>e.remove(),3500)};
(window.FLASH||[]).forEach(([c,m])=>toast(m,c));
const post=(u,b)=>fetch(u,{method:'POST',headers:{'X-CSRF':CSRF,'Content-Type':'application/json'},body:JSON.stringify(b||{})});
// drag & drop (reorder). data-sortable = persist to server; data-local = only DOM (submitted with form)
let dragged=null;
$$('[data-sortable],[data-local]').forEach(list=>{
 list.addEventListener('dragstart',e=>{dragged=e.target.closest('li');dragged?.classList.add('drag')});
 list.addEventListener('dragend',async()=>{if(!dragged)return;dragged.classList.remove('drag');$$('.over',list).forEach(x=>x.classList.remove('over'));dragged=null;
  if(list.dataset.url){const r=await post(list.dataset.url,{ids:$$('li[data-id]',list).map(l=>l.dataset.id)});toast(r.ok?'Ordem salva.':'Erro ao salvar ordem.',r.ok?'success':'error')}});
 list.addEventListener('dragover',e=>{e.preventDefault();const t=e.target.closest('li');if(!t||!dragged||t===dragged||t.parentNode!==list)return;
  const after=e.clientY>t.getBoundingClientRect().top+t.offsetHeight/2||e.clientX>t.getBoundingClientRect().left+t.offsetWidth/2&&list.classList.contains('thumbs-a');list.insertBefore(dragged,after?t.nextSibling:t)})});
// toggles
$$('[data-toggle]').forEach(c=>c.addEventListener('change',async()=>{const r=await post(c.dataset.toggle);toast(r.ok?'Atualizado.':'Erro.',r.ok?'success':'error')}));
// confirm delete
$$('form[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{if(!confirm(f.dataset.confirm))e.preventDefault()}));
// image previews
$$('[data-preview]').forEach(i=>i.addEventListener('change',()=>{const im=i.parentNode.querySelector('img'),f=i.files[0];if(f){im.src=URL.createObjectURL(f);im.hidden=false}}));
$$('[data-multi-preview]').forEach(i=>i.addEventListener('change',()=>{const box=$('#newprev');box.innerHTML='';[...i.files].forEach(f=>{const l=document.createElement('li');l.innerHTML='<img alt="">';l.firstChild.src=URL.createObjectURL(f);box.append(l)})}));
// show/hide fields by section type
const sw=$('[data-type-switch]');if(sw){const up=()=>$$('[data-show]').forEach(f=>f.hidden=!f.dataset.show.split(' ').includes(sw.value));sw.addEventListener('change',up);up()}
// validation + loading state
$$('form[data-validate]').forEach(f=>f.addEventListener('submit',e=>{let bad=0;$$('[required]',f).forEach(i=>{const b=!i.value.trim();i.classList.toggle('err',b);bad+=b});
 if(bad){e.preventDefault();toast('Preencha os campos obrigatórios.','error');return}const b=e.submitter||$('.abtn',f);b?.classList.add('loading')}));
// appearance: live preview + presets
const pv=$('#preview');if(pv){const apply=i=>{if(i.dataset.var&&i.value)pv.style.setProperty(i.dataset.var,i.dataset.var.match(/radius|fs/)?i.value+'px':i.value)};
 $$('[data-var]').forEach(i=>{apply(i);i.addEventListener('input',()=>apply(i))});
 $$('[data-preset]').forEach(b=>b.addEventListener('click',()=>{const p=JSON.parse(b.dataset.preset);for(const k in p){const i=$(`[name=${k}]`);if(i){i.value=p[k];apply(i)}}toast('Preset aplicado — clique em Salvar para publicar.','info')}))}
