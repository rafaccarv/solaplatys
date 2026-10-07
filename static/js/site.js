const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const toast=(m,t='success')=>{const e=document.createElement('div');e.className='toast '+t;e.textContent=m;$('#toasts').append(e);setTimeout(()=>e.remove(),3500)};
(window.FLASH||[]).forEach(([c,m])=>toast(m,c));
// menu / sticky
const menu=$('[data-menu]'),nav=$('#nav');menu?.addEventListener('click',()=>{const o=nav.classList.toggle('open');menu.setAttribute('aria-expanded',o)});
const hdr=$('.hdr');addEventListener('scroll',()=>hdr.classList.toggle('scrolled',scrollY>10),{passive:true});
// lazy images fade-in + reveal
const imgLoaded=i=>{const d=()=>{i.classList.add('loaded');i.closest('.ph')?.style.setProperty('animation','none')};i.complete?d():i.addEventListener('load',d)};
const watch=r=>{$$('.lazy-img',r).forEach(imgLoaded);const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.12});$$('.reveal',r).forEach(e=>io.observe(e))};watch(document);
// search + autocomplete
const S=$('#search'),sq=$('#sq'),sres=$('#sres');let tm;
const openS=()=>{S.hidden=false;sq.focus()},closeS=()=>S.hidden=true;
$('[data-search]').addEventListener('click',openS);$('[data-search-close]').addEventListener('click',closeS);addEventListener('keydown',e=>e.key==='Escape'&&closeS());
sq.addEventListener('input',()=>{clearTimeout(tm);const v=sq.value.trim();if(v.length<2){sres.innerHTML='';return}
 tm=setTimeout(async()=>{const r=await (await fetch('/api/search?q='+encodeURIComponent(v))).json();
 sres.innerHTML=r.length?r.map(p=>`<a href="${p.url}"><img src="${p.img}" alt=""><span><b>${p.name.replace(/</g,'&lt;')}</b><br><small>${p.cat} · ${p.price}</small></span></a>`).join(''):'<p class="muted">Nenhum resultado.</p>'},180)});
// filters (ajax)
const F=$('#filters');if(F){const host=$('#grid-host');$('[data-filters]')?.addEventListener('click',()=>F.classList.toggle('open'));
 const run=async()=>{const p=new URLSearchParams(new FormData(F));[...p].forEach(([k,v])=>!v&&p.delete(k));const u=location.pathname+(p.toString()?'?'+p:'');host.classList.add('busy');history.replaceState(null,'',u);
  try{host.innerHTML=await (await fetch(u,{headers:{'X-Requested-With':'fetch'}})).text();watch(host)}catch{toast('Erro ao carregar','error')}host.classList.remove('busy')};
 let t2;F.addEventListener('change',run);F.addEventListener('input',e=>{if(e.target.type==='number'){clearTimeout(t2);t2=setTimeout(run,400)}});F.addEventListener('submit',e=>{e.preventDefault();run()})}
// gallery
$$('.thumbs button').forEach(b=>b.addEventListener('click',()=>{const m=$('#main-img');m.style.opacity=0;setTimeout(()=>{m.src=b.dataset.src;m.style.opacity=1},150);$$('.thumbs button').forEach(x=>x.classList.toggle('on',x===b))}));
