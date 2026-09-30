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
  let fieldCache = null;
  const colors = {path:'#7c3bb0', tube:'rgba(44,157,115,.13)', candidate:'#259b91',
    robot:'#c02b42', anchor:'#7c3bb0', field:'#247a9d', trail:'#e79a39'};
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
  function fieldPaths() {
    if (demo.state !== 'recovering' || !demo.anchor) return [];
    if (fieldCache && fieldCache.anchor === demo.anchor && fieldCache.width === width) return fieldCache.paths;
    const paths = [], occupied = new Set();
    const spacing = width < 550 ? .042 : .026, step = .003;
    const cell = p => `${Math.round(p[0]/spacing)},${Math.round(p[1]/spacing)}`;
    const inside = p => p[0] >= .015 && p[0] <= .785 && p[1] >= .015 && p[1] <= .435;
    const direction = p => {
      const v = demo.velocity(p), speed = norm(v);
      return speed > 1e-8 && Number.isFinite(speed) ? mul(v,1/speed) : null;
    };
    // Arc-length RK2 traces the existing field without changing its dynamics.
    // Stop near the reference or other curves to keep converging lines readable.
    function trace(seed, sign) {
      const points = [seed], visited = new Set();
      let p = seed;
      for (let i=0; i<550; i++) {
        if (norm(sub(p,demo.anchor)) < .012) break;
        const d = direction(p);
        if (!d) break;
        const mid = direction(add(p,mul(d,sign*step/2)));
        if (!mid) break;
        const next = add(p,mul(mid,sign*step)), key = cell(next);
        if (!inside(next) || occupied.has(key)) break;
        if (key !== cell(p)) {
          if (visited.has(key)) break;
          visited.add(cell(p));
        }
        points.push(next); p = next;
      }
      return points;
    }
    const seeds = [];
    for (let x=.025; x<.79; x+=spacing*2) seeds.push([x,.025],[x,.425]);
    for (let y=.065; y<.42; y+=spacing*2) seeds.push([.025,y],[.775,y]);
    for (let y=.065; y<.42; y+=spacing*2)
      for (let x=.065; x<.77; x+=spacing*2) seeds.push([x,y]);
    for (const seed of seeds) {
      if (occupied.has(cell(seed))) continue;
      const backward = trace(seed,-1), forward = trace(seed,1);
      const points = backward.reverse().concat(forward.slice(1));
      if (points.length < 24) continue;
      paths.push(points);
      points.forEach(p=>occupied.add(cell(p)));
    }
    fieldCache = {anchor:demo.anchor, width, paths};
    return paths;
  }
  function drawField() {
    if (!arrows.checked || demo.state !== 'recovering') return;
    ctx.save(); ctx.lineCap='round'; ctx.lineJoin='round';
    for (const points of fieldPaths()) {
      ctx.globalAlpha=.62; line(points,colors.field,1.15);
      ctx.globalAlpha=.95;
      let distance=0, nextArrow=28;
      for (let i=1; i<points.length; i++) {
        const a=screen(points[i-1]), b=screen(points[i]);
        distance+=Math.hypot(b[0]-a[0],b[1]-a[1]);
        if (distance < nextArrow || norm(sub(points[i],demo.anchor)) < .02) continue;
        const v=demo.velocity(points[i]), speed=norm(v);
        if (speed < 1e-8) continue;
        const d=mul(v,1/speed), size=width<550?5:6;
        ctx.beginPath(); ctx.moveTo(...b);
        ctx.lineTo(b[0]-d[0]*size-d[1]*size*.48,b[1]-d[1]*size+d[0]*size*.48);
        ctx.lineTo(b[0]-d[0]*size+d[1]*size*.48,b[1]-d[1]*size-d[0]*size*.48);
        ctx.closePath(); ctx.fillStyle=colors.field;ctx.fill();
        nextArrow=distance+90;
      }
    }
    ctx.restore();
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
    drawField();
    if (candidates.checked || ['predicting','selecting'].includes(demo.state)) {
      ctx.save();
      if (demo.state==='recovering') ctx.globalAlpha=.35;
      preset.candidates.forEach((points,k)=>{
        if (k===preset.medoid) return;
        const member=preset.members.includes(k);
        line(points.slice(first).map(p=>demo.world(p)),member?'rgba(37,155,145,.30)':'rgba(135,143,151,.32)',1,member?[]:[4,5]);
      });
      ctx.restore();
    }
    line(path,'#d5c9df',1.5);
    line(path.slice(first),colors.path,2.3,demo.anchor?[5,5]:[]);
    if (demo.anchor) {
      const prefix=path.slice(0,demo.lockedPhase+1).map(p=>add(p,demo.anchorOffset));
      line(prefix,colors.path,2.5);
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
  window.DSP_DEMO={model:demo,draw,screen:p=>screen(p),fieldPaths};
  resize();requestAnimationFrame(frame);
})();
