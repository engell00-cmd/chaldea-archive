(function cxTheme(){
  var SCENES = window.CX_SCENES || {};
  var bg = document.getElementById('cx-bg'); if(!bg) return;
  var photo = bg.querySelector('.cx-photo');
  function txt(el){return (el && el.textContent || '').replace(/\s+/g,' ').trim()}

  // 화자 분류: GM 내레이션 / 배경 매크로 오류 숨김
  [].forEach.call(document.querySelectorAll('.grp'),function(g){
    var w = txt(g.querySelector('.who'));
    if(/^GM[\s_]/.test(w) || w==='GM') g.classList.add('cx-gm');
    if(w.indexOf('「배경」')===0) g.classList.add('cx-noise');
  });
  [].forEach.call(document.querySelectorAll('.cast span'),function(s){
    if(txt(s).indexOf('「배경」')===0) s.classList.add('cx-noise');
  });

  // 시스템 라인 분류
  var markers = [];
  [].forEach.call(document.querySelectorAll('.sys'),function(s){
    var t = txt(s);
    if(/(has connected|is disconnected|has disconnected|님이 (접속|퇴장))/i.test(t)){ s.classList.add('cx-conn'); return; }
    if(t.indexOf('「배경」')>=0){
      var rest = t.replace(/.*?「배경」\s*/,'');
      var m = rest.match(/「([^」]+)」/);
      var name = m ? m[1] : rest;
      s.classList.add('cx-scene'); s.dataset.scene = name; s.title = t;
      var p = s.querySelector('.line'); if(p) p.textContent = name;
      s.tabIndex=0; s.setAttribute('role','button'); s.setAttribute('aria-label',name+' 장면 — 칼데아스로 비추기');
      var go=function(){ document.dispatchEvent(new CustomEvent('cx-scene',{detail:name})); };
      s.addEventListener('click',go); s.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } });
      markers.push(s); return;
    }
    if(/^[♬♪]/.test(t)) s.classList.add('cx-title');
  });

  // 장면 배경 전환 (CX_SCENES에 이미지 주소가 있는 장면만)
  var cur;
  function apply(name){
    if(name===cur) return; var first = (cur===undefined); cur = name;
    if(!first && name) document.dispatchEvent(new CustomEvent('cx-scene',{detail:name}));
    var v = name && SCENES[name] || SCENES['기본'] || ''; var url = typeof v==='string' ? v : (v && v.img) || '';
    if(url){
      var img = new Image();
      img.onload = function(){ if(cur!==name) return; photo.style.backgroundImage='url("'+url.replace(/"/g,'%22')+'")'; photo.classList.add('on'); bg.classList.add('has-photo'); };
      img.src = url;
    } else { photo.classList.remove('on'); bg.classList.remove('has-photo'); }
  }
  var tick=false;
  function scan(){
    tick=false; var mid=innerHeight*.55, best=null;
    for(var i=0;i<markers.length;i++){ if(markers[i].getBoundingClientRect().top<mid) best=markers[i]; else break; }
    apply(best ? best.dataset.scene : null);
  }
  window.addEventListener('scroll',function(){ if(!tick){ tick=true; requestAnimationFrame(scan); } },{passive:true});
  scan();
})();

/* ---- 칼데아스: 회전하는 3D 지구본 (캔버스, 육지 데이터 약 2.7KB) ----
   장면(「배경」)이 바뀌면 지구본이 한 바퀴 빙그르르 돌아 그 장소를 비춘다. */
(function cxGlobe(){
  var cvs = [].slice.call(document.querySelectorAll('canvas.cx-globe-cv')); if(!cvs.length || !window.CX_LAND) return;
  var RAD = Math.PI/180;
  var PLACES = Object.assign({ '칼데아':[-78,10], '남극':[-78,10], '런던':[51.5,-0.1], '시계탑':[51.5,-0.1], '영국':[52,-1.5], '브리튼':[52,-1.5],
    '후유키':[34.7,135.2], '일본':[36,138] }, window.CX_PLACES||{});
  Object.keys(window.CX_SCENES||{}).forEach(function(k){ var v=window.CX_SCENES[k]; if(v && v.pos) PLACES[k]=v.pos; });
  var raw = atob(window.CX_LAND), W = 180, H = 90, pts = [];
  function land(x,y){ var i=y*W+x; return (raw.charCodeAt(i>>3)>>(i&7))&1; }
  for(var y=0;y<H;y++){
    var lat=(89-2*y)*RAD, c=Math.cos(lat), step=Math.max(1,Math.round(1/Math.max(c,.08)));
    for(var x=0;x<W;x+=step){
      var isLand=land(x,y); if(!isLand && (y%2 || (x/step)%2)) continue;
      pts.push([Math.sin(lat),c,(-179+2*x)*RAD,isLand]);
    }
  }
  var st = {lon:0, lat:-22*RAD, spin:null, mark:null}, col = {};
  function readColors(){ var cs=getComputedStyle(document.documentElement);
    col.land=cs.getPropertyValue('--cx-land').trim()||'#7fe0ff'; col.sea=cs.getPropertyValue('--cx-sea').trim()||'rgba(95,210,255,.2)'; col.rim=cs.getPropertyValue('--cx-rim').trim()||'rgba(95,210,255,.5)'; col.acc=cs.getPropertyValue('--accent').trim()||'#5fd2ff'; }
  var views = cvs.map(function(cv){ return {cv:cv, ctx:cv.getContext('2d')}; });
  function size(){ views.forEach(function(v){ v.dpr=Math.min(window.devicePixelRatio||1,2); var r=v.cv.getBoundingClientRect();
    v.cv.width=Math.max(1,Math.round(r.width*v.dpr)); v.cv.height=Math.max(1,Math.round(r.height*v.dpr)); v.cx=v.cv.width/2; v.cy=v.cv.height/2; v.R=Math.min(v.cx,v.cy)*.92; }); }
  function proj(v,sp,cp,lon){ var d=lon-st.lon, cl=Math.cos(d), s0=Math.sin(st.lat), c0=Math.cos(st.lat);
    return {z:s0*sp+c0*cp*cl, x:v.cx+v.R*cp*Math.sin(d), y:v.cy-v.R*(c0*sp-s0*cp*cl)}; }
  function draw(now){
    views.forEach(function(v){ var ctx=v.ctx, cx=v.cx, cy=v.cy, R=v.R, dpr=v.dpr; if(v.cv.width>2) v.cv.parentNode.classList.add('live');
      ctx.clearRect(0,0,v.cv.width,v.cv.height);
      var g=ctx.createRadialGradient(cx-R*.3,cy-R*.35,R*.1,cx,cy,R*1.05); g.addColorStop(0,col.sea); g.addColorStop(1,'rgba(0,0,0,0)');
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(cx,cy,R,0,6.2832); ctx.fill(); ctx.strokeStyle=col.rim; ctx.lineWidth=1.2*dpr; ctx.stroke();
      var s=1.6*dpr*Math.max(.7,R/(160*dpr));
      for(var i=0;i<pts.length;i++){ var p=pts[i], q=proj(v,p[0],p[1],p[2]); if(q.z<=0) continue;
        ctx.globalAlpha = p[3] ? (.35+.65*q.z) : .35*q.z; ctx.fillStyle = p[3] ? col.land : col.rim;
        var k = p[3] ? s*(.6+.6*q.z) : s*.6; ctx.fillRect(q.x-k/2,q.y-k/2,k,k); }
      ctx.globalAlpha=1;
      if(st.mark){ var m=st.mark, q=proj(v,Math.sin(m[0]),Math.cos(m[0]),m[1]);
        if(q.z>0){ var pulse=(now/900)%1, rr=(4+pulse*14)*dpr;
          ctx.strokeStyle=col.acc; ctx.lineWidth=1.5*dpr; ctx.globalAlpha=1-pulse; ctx.beginPath(); ctx.arc(q.x,q.y,rr,0,6.2832); ctx.stroke();
          ctx.globalAlpha=1; ctx.fillStyle=col.acc; ctx.beginPath(); ctx.arc(q.x,q.y,2.6*dpr,0,6.2832); ctx.fill();
          ctx.beginPath(); ctx.moveTo(q.x-10*dpr,q.y); ctx.lineTo(q.x-5*dpr,q.y); ctx.moveTo(q.x+5*dpr,q.y); ctx.lineTo(q.x+10*dpr,q.y);
          ctx.moveTo(q.x,q.y-10*dpr); ctx.lineTo(q.x,q.y-5*dpr); ctx.moveTo(q.x,q.y+5*dpr); ctx.lineTo(q.x,q.y+10*dpr); ctx.stroke(); } }
    });
  }
  function ease(t){ return t<.5 ? 4*t*t*t : 1-Math.pow(-2*t+2,3)/2; }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches, last=0, lastT=0;
  // 장면 전환: 한 바퀴 빙그르르 → 그 장소에서 멈춤 (장소를 모르면 한 바퀴만)
  function spinTo(name){
    var tgt = PLACES[name]; var lat1 = tgt ? Math.max(-80,Math.min(80,tgt[0]))*RAD : -22*RAD;
    var lon1 = tgt ? tgt[1]*RAD : st.lon;
    var base = st.lon, delta = ((lon1-base)%(2*Math.PI)+2*Math.PI)%(2*Math.PI); // 동쪽으로 남은 각
    st.mark = null;
    if(reduce){ st.lon=lon1; st.lat=lat1; st.mark=tgt?[tgt[0]*RAD,tgt[1]*RAD]:null; draw(performance.now()); return; }
    st.spin = {t0:performance.now(), dur:1900, lon0:base, lon1:base+delta+2*Math.PI, lat0:st.lat, lat1:lat1, mark:tgt?[tgt[0]*RAD,tgt[1]*RAD]:null};
  }
  function loop(t){
    var dt = Math.min(100, t-(lastT||t)); lastT=t;
    if(st.spin){ var k=Math.min(1,(t-st.spin.t0)/st.spin.dur), e=ease(k);
      st.lon = st.spin.lon0 + (st.spin.lon1-st.spin.lon0)*e; st.lat = st.spin.lat0 + (st.spin.lat1-st.spin.lat0)*e;
      if(k>=1){ st.mark = st.spin.mark; st.spin=null; } }
    else st.lon += dt/1000*(st.mark ? .012 : .06);
    if(views.some(function(v){ return v.cv.width<2; })) size();
    if(!document.hidden && (st.spin || t-last>33)){ draw(t); last=t; }
    requestAnimationFrame(loop);
  }
  readColors(); size(); draw(0);
  window.addEventListener('resize',function(){ size(); draw(performance.now()); });
  if(window.ResizeObserver){ var ro=new ResizeObserver(function(){ size(); draw(performance.now()); }); cvs.forEach(function(c){ ro.observe(c); }); }
  document.addEventListener('cx-theme',function(){ readColors(); draw(performance.now()); });
  document.addEventListener('cx-scene',function(e){ spinTo(e.detail); });
  if(window.matchMedia) matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(){ readColors(); draw(performance.now()); });
  if(!reduce) requestAnimationFrame(loop);
})();

/* ---- 관제실 조명: 켜면 라이트, 끄면 다크 ---- */
(function cxLights(){
  var btn = document.querySelector('.cx-light'); if(!btn) return;
  var root = document.documentElement, veil = document.getElementById('cx-lights'), KEY='cx-lights';
  function sysDark(){ return window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches; }
  function isOn(){ var t=root.getAttribute('data-theme'); return t ? t==='light' : !sysDark(); }
  function label(){ var on=isOn(); btn.setAttribute('aria-pressed', on?'true':'false'); btn.querySelector('.lb').textContent = on?'조명 ON':'조명 OFF'; }
  function set(on, animate){
    var apply=function(){ root.setAttribute('data-theme', on?'light':'dark'); label(); document.dispatchEvent(new Event('cx-theme')); };
    if(animate && veil){ veil.className=''; void veil.offsetWidth; veil.className = on?'on':'off'; setTimeout(apply, on?0:270); }
    else apply();
    try{ localStorage.setItem(KEY, on?'on':'off'); }catch(e){}
  }
  var saved=null; try{ saved=localStorage.getItem(KEY); }catch(e){}
  if(saved==='on'||saved==='off') set(saved==='on', false); else label();
  btn.addEventListener('click', function(){ set(!isOn(), true); });
})();

/* ---- 마슈의 미니 관계도: 이 기록의 등장인물끼리 이어진 실 ---- */
(function cxRel(){
  var R = window.CX_REL, box = document.querySelector('.cast-box'); if(!R || !box) return;
  var idx = {}; R.nodes.forEach(function(n){ n.names.forEach(function(k){ idx[k]=n.id; }); });
  var here = {}, order = [];
  [].forEach.call(box.querySelectorAll('.cast span'),function(s){
    if(s.classList.contains('cx-noise')) return;
    var nm=(s.textContent||'').trim(), id=idx[nm]; if(!id || here[id]) return;
    var tk=s.querySelector('.tk'); here[id]={name:nm, tk:tk?tk.className:''}; order.push(id);
  });
  var es = R.edges.filter(function(e){ return here[e.a] && here[e.b]; });
  if(!es.length) return;
  var used = order.filter(function(id){ return es.some(function(e){return e.a===id||e.b===id}); });
  var wrap=document.createElement('div'); wrap.className='cx-rel';
  wrap.innerHTML='<div class="cx-rel-h"><span>마슈의 메모 · 이 기록의 인물 관계</span>'+(window.CX_BOARD?'<a href="'+window.CX_BOARD+'">전체 관계도 →</a>':'')+'</div><div class="cx-cork"><svg aria-hidden="true"></svg></div>';
  box.appendChild(wrap);
  var cork=wrap.querySelector('.cx-cork'), svg=cork.querySelector('svg'), NS='http://www.w3.org/2000/svg', P={};
  used.forEach(function(id){ var c=document.createElement('div'); c.className='cx-pc';
    c.innerHTML='<i class="cx-pin"></i><span class="cx-ph '+(here[id].tk||'')+'"></span><b>'+here[id].name.replace(/[&<]/g,'')+'</b>'; cork.appendChild(c); P[id]=c; });
  var tags = es.map(function(e){ var t=document.createElement('span'); t.className='cx-tag '+e.kind; t.textContent=e.label; cork.appendChild(t); return t; });
  function lay(){
    var w=cork.clientWidth, h=cork.clientHeight; if(!w) return; var n=used.length, pos={};
    used.forEach(function(id,i){ var a = n===2 ? Math.PI*i : -Math.PI/2 + 2*Math.PI*i/n;
      var x=w/2+Math.cos(a)*(w/2-70), y=h/2+Math.sin(a)*(h/2-56); pos[id]={x:x,y:y};
      P[id].style.left=(x-40)+'px'; P[id].style.top=(y-44)+'px'; });
    svg.setAttribute('viewBox','0 0 '+w+' '+h); svg.innerHTML='';
    es.forEach(function(e,i){ var A=pos[e.a], B=pos[e.b]; A={x:A.x,y:A.y-40}; B={x:B.x,y:B.y-40};
      var L=Math.hypot(B.x-A.x,B.y-A.y), mx=(A.x+B.x)/2, my=(A.y+B.y)/2+Math.min(40,L*.12);
      var p=document.createElementNS(NS,'path'); p.setAttribute('d','M'+A.x+' '+A.y+' Q'+mx+' '+my+' '+B.x+' '+B.y); p.setAttribute('class',e.kind); svg.appendChild(p);
      tags[i].style.left=(.25*A.x+.5*mx+.25*B.x)+'px'; tags[i].style.top=(.25*A.y+.5*my+.25*B.y)+'px'; });
  }
  box.addEventListener('toggle',lay); window.addEventListener('resize',lay); lay();
})();
