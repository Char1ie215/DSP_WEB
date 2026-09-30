'use strict';

(() => {
  const section = document.getElementById('interactive-recovery');
  const canvas = document.getElementById('recovery-canvas');
  if (!section || !canvas || !window.DSPRecovery) return;
  const ctx = canvas.getContext('2d');
  const {Demo, add, sub, mul, norm} = window.DSPRecovery;
  const demo = new Demo();
  const handle = document.getElementById('eef-handle');
  const pause = document.getElementById('demo-pause');
  const status = document.getElementById('demo-status');
  const progress = document.getElementById('demo-phase');
  const query = document.getElementById('demo-query');
  const candidates = document.getElementById('demo-candidates');
  const arrows = document.getElementById('demo-field');
  let width = 900, height = 450, scale = 1000, ox = 0, oy = 0;
  let visible = false, last = 0, accumulated = 0, pointer = null, lastPointer = null;
  const colors = {path:'#7c3bb0', tube:'rgba(44,157,115,.13)', candidate:'#259b91',
    robot:'#c02b42', anchor:'#7c3bb0', field:'#158e94', trail:'#e79a39'};
  const labels = {predicting:'Prediction', selecting:'Candidate selection', executing:'Native execution',
    recovering:'Recovery / phase locked', replanning:'Replanning', complete:'Complete',
    'recovery-timeout':'Recovery timed out'};

  function screen(p) { return [ox + p[0]*scale, oy + p[1]*scale]; }
  function world(event) {
    const r = canvas.getBoundingClientRect();
    return [Math.max(.015, Math.min(.785, (event.clientX-r.left-ox)/scale)),
      Math.max(.015, Math.min(.435, (event.clientY-r.top-oy)/scale))];
  }
  function line(points, color, weight=1, dash=[]) {
    if (!points.length) return;
    ctx.beginPath(); points.forEach((p, i) => { const [x,y]=screen(p); i ? ctx.lineTo(x,y) : ctx.moveTo(x,y); });
    ctx.strokeStyle=color; ctx.lineWidth=weight; ctx.setLineDash(dash); ctx.stroke(); ctx.setLineDash([]);
  }
  function ring(p, radius, color) {
    const [x,y]=screen(p); ctx.beginPath(); ctx.arc(x,y,radius,0,2*Math.PI);
    ctx.fillStyle='#fff'; ctx.fill(); ctx.strokeStyle=color; ctx.lineWidth=2; ctx.stroke();
  }
  function draw() {
    ctx.clearRect(0,0,width,height);
    const preset=demo.preset, path=preset.path.map(p=>demo.world(p));
    const first=demo.phase;
    const normals=path.map((p,i)=>{
      const d=sub(path[Math.min(i+1,path.length-1)],path[Math.max(0,i-1)]);
      const l=Math.max(norm(d),1e-12); return [-d[1]/l,d[0]/l];
    });
    // A ribbon depicts transverse cluster spread; active-segment checks also
    // constrain longitudinal distance, as in the research executor.
    const ribbon=path.map((p,i)=>add(p,mul(normals[i],preset.radii[i])))
      .concat(path.map((p,i)=>sub(p,mul(normals[i],preset.radii[i]))).reverse());
    ctx.beginPath(); ribbon.forEach((p,i)=>{ const [x,y]=screen(p); i?ctx.lineTo(x,y):ctx.moveTo(x,y); });
    ctx.closePath(); ctx.fillStyle=colors.tube; ctx.fill();
    if (candidates.checked || ['predicting','selecting'].includes(demo.state)) {
      preset.candidates.forEach((points,k)=>{
        if (k===preset.medoid) return;
        const member=preset.members.includes(k);
        line(points.slice(first).map(p=>demo.world(p)),member?'rgba(37,155,145,.30)':'rgba(135,143,151,.32)',1,member?[]:[4,5]);
      });
    }
    line(path,'#d5c9df',1.5);
    line(path.slice(first),colors.path,2.3,demo.anchor?[5,5]:[]);
    if (demo.anchor) {
      const prefix=path.slice(0,demo.lockedPhase+1).map(p=>add(p,demo.anchorOffset));
      line(prefix,colors.path,2.5);
      if (arrows.checked && demo.state==='recovering') {
        for(let x=.055;x<.79;x+=.048) for(let y=.045;y<.44;y+=.048) {
          const p=[x,y], v=demo.velocity(p), length=norm(v);
          if(length<1e-7 || norm(sub(p,demo.anchor))<.022) continue;
          const a=screen(p), d=mul(v,1/length), size=Math.min(17,scale*.025);
          const b=[a[0]+d[0]*size,a[1]+d[1]*size];
          ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b);
          ctx.moveTo(b[0]-d[0]*4-d[1]*2.8,b[1]-d[1]*4+d[0]*2.8);
          ctx.lineTo(...b); ctx.lineTo(b[0]-d[0]*4+d[1]*2.8,b[1]-d[1]*4-d[0]*2.8);
          ctx.strokeStyle='rgba(21,142,148,.36)';ctx.lineWidth=1;ctx.stroke();
        }
      }
      line(demo.trail,colors.trail,2);
      ring(demo.anchor,7,colors.anchor);
    }
    ring(path[path.length-1],4,'#7d858c');
    const [x,y]=screen(demo.position);
    handle.style.left=`${x}px`; handle.style.top=`${y}px`;
    handle.classList.toggle('is-dragging',demo.dragging);
    handle.disabled=!['executing','recovering','complete'].includes(demo.state);
    const text=(demo.paused?'Paused / ':'')+labels[demo.state];
    if(status.textContent!==text) status.textContent=text;
    section.dataset.state=demo.state;
    progress.textContent=demo.lockedPhase===null
      ? `Phase ${String(demo.phase).padStart(2,'0')} / ${demo.maxPhase}`
      : `Reference phase ${String(demo.lockedPhase).padStart(2,'0')} / locked`;
    query.textContent=`Query ${demo.query} / K = 16`;
    document.getElementById('demo-perturb').disabled=handle.disabled;
  }
  function resize() {
    const r=canvas.getBoundingClientRect(); width=r.width; height=r.height;
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    scale=Math.min(width/.8,height/.45); ox=(width-scale*.8)/2;oy=(height-scale*.45)/2;
    draw();
  }
  function syncPause() {
    pause.setAttribute('aria-label',demo.paused?'Resume':'Pause');
    pause.title=demo.paused?'Resume':'Pause';
    pause.querySelector('img').src=`static/icons/${demo.paused?'play':'pause'}.svg`;
  }
  pause.addEventListener('click',()=>{demo.paused=!demo.paused;syncPause();draw();});
  document.getElementById('demo-reset').addEventListener('click',()=>{
    if(pointer!==null && handle.hasPointerCapture(pointer)) handle.releasePointerCapture(pointer);
    pointer=null;lastPointer=null;demo.reset();accumulated=0;syncPause();draw();
  });
  document.getElementById('demo-perturb').addEventListener('click',()=>{demo.perturb();draw();});
  handle.addEventListener('pointerdown',e=>{
    if(pointer!==null || !demo.beginDrag()) return;
    pointer=e.pointerId;lastPointer=world(e);handle.setPointerCapture(pointer);e.preventDefault();draw();
  });
  handle.addEventListener('pointermove',e=>{
    if(e.pointerId!==pointer)return;
    const next=world(e);
    // Pointer motion adds a disturbance to the moving robot; simply holding
    // the handle does not stop native commands or snap it back to the pointer.
    demo.drag(add(demo.position,sub(next,lastPointer)));lastPointer=next;draw();
  });
  const release=e=>{
    if(e.pointerId!==pointer) return;
    pointer=null;lastPointer=null;demo.endDrag();draw();
  };
  handle.addEventListener('pointerup',release);
  handle.addEventListener('pointercancel',release);
  handle.addEventListener('lostpointercapture',release);
  handle.addEventListener('keydown',e=>{
    const moves={ArrowLeft:[-.02,0],ArrowRight:[.02,0],ArrowUp:[0,-.02],ArrowDown:[0,.02]};
    if(!moves[e.key])return;e.preventDefault();
    if(demo.beginDrag()){demo.drag(add(demo.position,moves[e.key]));demo.endDrag();draw();}
  });
  candidates.addEventListener('change',draw);arrows.addEventListener('change',draw);
  new ResizeObserver(resize).observe(canvas);
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;last=0;}, {threshold:.15}).observe(canvas);
  document.addEventListener('visibilitychange',()=>{last=0;});
  function frame(time) {
    if(visible && !document.hidden){
      if(last) accumulated+=Math.min((time-last)/1000,.06);
      while(accumulated>=1/60){demo.step(1/60);accumulated-=1/60;}
      draw();
    }
    last=time;requestAnimationFrame(frame);
  }
  window.DSP_DEMO={model:demo,draw,screen:p=>screen(p)};
  resize();requestAnimationFrame(frame);
})();
