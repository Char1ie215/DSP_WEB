"""Check research-field parity, hybrid invariants, and real browser interactions."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'test-results'
OUTPUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
    page = browser.new_page()
    page.goto((ROOT / 'index.html').as_uri())
    report = page.evaluate('''() => {
      const {Demo, field, projectCLF, innovation, norm, sub, add} = DSPRecovery;
      let maxError = 0, recoveries = 0, longest = 0;
      for (const preset of DSP_RECOVERY_DATA.presets) {
        for (const test of preset.fixtures) {
          const error = norm(sub(field(preset, test.phase, test.point), test.value));
          maxError = Math.max(maxError, error);
          if (error > 1e-9) throw Error(`Python parity: ${error}`);
        }
      }
      if (innovation([0.01,0], [0.01,0]) !== 0) throw Error('Nominal innovation');
      if (innovation([0,0.1], [0.01,0]) < .09) throw Error('Transverse innovation');
      const P=[[2,.3],[.3,3]], offset=[.1,.2], raw=[.08,.06], radius=.04;
      const gradient=[P[0][0]*offset[0]+P[0][1]*offset[1],P[1][0]*offset[0]+P[1][1]*offset[1]];
      const dot=(a,b)=>a[0]*b[0]+a[1]*b[1];
      const d=Math.sqrt(dot(offset,gradient)), required=DSP_RECOVERY_DATA.contraction*d*(d-radius);
      const projected=projectCLF(offset,raw,P,radius);
      if(Math.abs(dot(gradient,projected)+required)>1e-12)throw Error('Eq. 9 smooth-tube descent');
      if(norm(sub(projectCLF([.001,0],raw,P,radius),raw))!==0)throw Error('Projection active inside tolerance');
      const inward=[-.1,-.2];
      if(norm(sub(projectCLF(offset,inward,P,radius),inward))!==0)throw Error('Unnecessary CLF correction');
      for (let variant = 0; variant < 2; variant++) {
        for (const phase of [0, 5, 16, 24, 38, 48]) {
          for (const point of [[.02,.02],[.78,.02],[.02,.43],[.78,.43],[.4,.1],[.4,.42]]) {
            const m = new Demo(); m.presetIndex=variant; m.phase=phase; m.state='executing';
            m.position=add(m.preset.path[phase],[.004,.002]);
            m.observePosition();
            m.lastNativePosition=[...m.position]; m.beginDrag();m.drag(point);m.endDrag();
            if(m.state!=='recovering') throw Error('No recovery');
            const anchor=[...m.anchor];
            let ticks=0;
            while(m.state==='recovering' && ticks<1801) {
              m.step(1/60); ticks++;
              if(m.phase!==phase || m.lockedPhase!==phase || norm(sub(m.anchor,anchor))>1e-12)
                throw Error('Reference/phase changed during recovery');
            }
            if(m.state!=='replanning' || norm(sub(m.position,anchor))>DSP_RECOVERY_DATA.reentryRadius)
              throw Error(`Recovery failed: variant ${variant}, phase ${phase}, point ${point}, error ${norm(sub(m.position,anchor))}`);
            longest=Math.max(longest,ticks);recoveries++;
            for(let i=0;i<180;i++)m.step(1/60);
            if(m.query!==2 || m.presetIndex===variant) throw Error('No new synthetic query');
          }
        }
      }
      const m = new Demo(); m.state='executing';m.phase=12;m.position=[...m.preset.path[12]];
      m.observePosition();
      m.lastNativePosition=[...m.position];m.beginDrag();m.drag(add(m.position,[0,.001]));m.endDrag();
      if(m.state!=='executing')throw Error('Within-support drag triggered recovery');
      m.beginDrag();m.drag(m.world(m.preset.path[38]));m.endDrag();
      if(m.state!=='recovering'||m.lockedPhase!==12)throw Error('Future segment advanced recovery phase');
      const locked=[...m.anchor];m.beginDrag();m.drag([.03,.03]);m.endDrag();
      if(norm(sub(locked,m.anchor))>1e-12)throw Error('Repeated drag changed reference');
      const n=new Demo();n.state='executing';n.phase=12;n.position=[...n.preset.path[12]];
      n.observePosition();const accepted=[...n.acceptedPosition];
      n.lastNativePosition=add(n.position,[0,.1]);n.expected=[0,0];n.beginDrag();
      n.drag(add(n.position,[0,.1]));n.endDrag();
      if(n.state!=='executing')throw Error('Support departure alone triggered recovery');
      if(norm(sub(n.acceptedPosition,accepted))!==0)throw Error('Outside state was accepted');
      const a=new Demo();
      while(a.state!=='executing'||a.phase<12)a.step(1/60);
      const onset=[...a.position], onsetPhase=a.phase;
      a.beginDrag();
      if(a.anchor!==null||a.lockedPhase!==null)throw Error('Locked on pointer-down');
      for(let i=0;i<30;i++)a.step(1/60);
      if(a.phase<=onsetPhase||a.state!=='executing'||a.anchor!==null)throw Error('Pointer hold stopped native execution');
      a.drag(add(a.position,[0,.002]));
      if(a.state!=='executing'||norm(sub(a.position,a.acceptedPosition))!==0)throw Error('In-tube pose not accepted');
      const lastAccepted=[...a.acceptedPosition], lastAcceptedPhase=a.acceptedPhase;
      if(norm(sub(lastAccepted,onset))<.005)throw Error('Reference did not update after onset');
      a.drag(add(a.position,[0,-.09]));
      if(a.state!=='recovering'||norm(sub(a.anchor,lastAccepted))!==0||a.lockedPhase!==lastAcceptedPhase)
        throw Error('Did not lock most recent accepted state');
      const frozenPhase=a.phase;
      for(let i=0;i<60;i++)a.step(1/60);
      if(a.phase!==frozenPhase||norm(sub(a.anchor,lastAccepted))!==0)throw Error('Recovery lock changed while held');
      a.endDrag();
      // Accepted phase can precede trigger phase when an outside state has low innovation.
      n.phase=13;n.lastNativePosition=[...n.position];n.beginDrag();n.drag(add(n.position,[.1,0]));n.endDrag();
      if(n.state!=='recovering'||n.phase!==13||n.lockedPhase!==12||norm(sub(n.anchor,accepted))!==0)
        throw Error('Accepted phase was replaced by trigger phase');
      // Small successive pointer motions must trigger at the first slight
      // transverse departure, rather than requiring one large mouse event.
      const edge=new Demo();edge.state='executing';edge.phase=12;
      const start=edge.preset.path[12], end=edge.preset.path[13];
      edge.position=[(start[0]+end[0])/2,(start[1]+end[1])/2];edge.observePosition();
      const tangent=sub(end,start), length=norm(tangent), normal=[-tangent[1]/length,tangent[0]/length];
      edge.beginDrag();let crossed=false;
      for(let i=0;i<200;i++) {
        edge.lastNativePosition=[...edge.position];edge.expected=[0,0];
        edge.drag(add(edge.position,normal.map(v=>v*.0002)));
        const ratio=DSPRecovery.supportRatio(edge.preset,edge.phase,edge.position);
        if(ratio<=1) {
          if(edge.state!=='executing'||edge.anchor!==null)throw Error('Premature boundary trigger');
        } else {
          if(edge.state!=='recovering'||ratio>1.03)throw Error('Slight departure did not trigger');
          crossed=true;break;
        }
      }
      if(!crossed)throw Error('Boundary test never crossed support');
      return {maxError,recoveries,longestSeconds:longest/60};
    }''')
    print('PASS numerical parity and recovery invariants:', report, flush=True)
    page.close()

    for name, width, height, touch in [('desktop',1440,1000,False),('mobile',390,844,True),('small',360,780,True)]:
        context=browser.new_context(viewport={'width':width,'height':height},has_touch=touch,is_mobile=touch)
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.goto((ROOT / 'index.html').as_uri())
        page.locator('#interactive-recovery').scroll_into_view_if_needed()
        page.evaluate('''() => {
          const m=DSP_DEMO.model;
          while(m.state!=='executing'||m.phase<16)m.step(1/60);
          m.paused=true;DSP_DEMO.draw();
        }''')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        before=page.evaluate('DSP_DEMO.model.snapshot()')
        assert page.evaluate('DSP_DEMO.fieldPaths().length') == 0
        handle=page.locator('#eef-handle').bounding_box()
        start={'x':handle['x']+handle['width']/2,'y':handle['y']+handle['height']/2}
        target={'x':start['x']+min(width*.14,160),'y':start['y']-75}
        if touch:
            cdp=context.new_cdp_session(page)
            cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[start]})
            cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[target]})
        else:
            page.mouse.move(**start);page.mouse.down();page.mouse.move(**target,steps=8)
        held=page.evaluate('DSP_DEMO.model.snapshot()')
        assert held['state']=='recovering' and held['dragging'], held
        assert held['phase']==before['phase'] and held['anchor']==held['acceptedPosition'], held
        streamlines=page.evaluate('''() => {
          const {model,fieldPaths}=DSP_DEMO;
          const before=JSON.stringify(model.snapshot());
          const paths=fieldPaths();
          if(paths.length<12)throw Error('Too few streamlines');
          if(fieldPaths()!==paths)throw Error('Field geometry not cached');
          let segments=0,minCosine=1;
          for(const points of paths)for(let i=1;i<points.length;i++) {
            const a=points[i-1],b=points[i],mid=[(a[0]+b[0])/2,(a[1]+b[1])/2];
            if(!b.every(Number.isFinite))throw Error('Nonfinite streamline');
            const d=[b[0]-a[0],b[1]-a[1]],v=model.velocity(mid);
            const cosine=(d[0]*v[0]+d[1]*v[1])/(Math.hypot(...d)*Math.hypot(...v));
            if(!(cosine>.8))throw Error('Streamline disagrees with recovery field');
            minCosine=Math.min(minCosine,cosine);segments++;
          }
          if(before!==JSON.stringify(model.snapshot()))throw Error('Rendering changed recovery state');
          return {curves:paths.length,segments,minCosine};
        }''')
        print(f'PASS {name} streamlines: {streamlines}',flush=True)
        with_field=page.locator('canvas').evaluate('c=>c.toDataURL()')
        page.evaluate("document.getElementById('demo-field').checked=false;DSP_DEMO.draw()")
        assert page.locator('canvas').evaluate('c=>c.toDataURL()') != with_field
        page.evaluate("document.getElementById('demo-field').checked=true;DSP_DEMO.draw()")
        page.locator('#interactive-recovery').screenshot(path=str(OUTPUT/f'{name}-interactive-held.png'))
        if touch:
            cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        else: page.mouse.up()
        page.locator('#demo-pause').click()
        page.locator('#recovery-canvas').scroll_into_view_if_needed()
        page.wait_for_function('DSP_DEMO.model.position[1] !== '+str(held['position'][1]))
        page.locator('#demo-pause').click()
        page.evaluate('''() => {
          const m=DSP_DEMO.model;m.paused=false;
          for(let i=0;i<80 && m.state==='recovering';i++)m.step(1/60);
          m.paused=true;DSP_DEMO.draw();
        }''')
        pixels=page.locator('canvas').evaluate('''c => {
          const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
          let count=0;for(let i=3;i<a.length;i+=4)if(a[i]>0)count++;
          return count;
        }''')
        assert pixels>1500, pixels
        page.locator('#interactive-recovery').screenshot(path=str(OUTPUT/f'{name}-interactive-recovery.png'))
        page.evaluate('''() => {
          const m=DSP_DEMO.model;m.paused=false;
          for(let i=0;i<1801 && m.state==='recovering';i++)m.step(1/60);
          m.paused=true;DSP_DEMO.draw();
        }''')
        assert page.evaluate('DSP_DEMO.model.state')=='replanning'
        page.locator('#demo-candidates').uncheck()
        page.locator('#demo-field').uncheck()
        page.locator('#demo-reset').click()
        assert page.evaluate('DSP_DEMO.model.query')==1
        page.evaluate("DSP_DEMO.model.state='executing';DSP_DEMO.draw()")
        page.locator('#demo-perturb').click()
        assert page.evaluate('DSP_DEMO.model.state')=='recovering'
        page.locator('#demo-reset').click()
        page.evaluate("DSP_DEMO.model.state='executing';DSP_DEMO.model.paused=true;DSP_DEMO.draw()")
        page.locator('#eef-handle').focus()
        page.keyboard.press('ArrowUp')
        assert page.evaluate('DSP_DEMO.model.state')=='recovering'
        page.locator('#demo-reset').click()
        page.locator('#demo-field').check()
        page.evaluate('''() => {
          const m=DSP_DEMO.model;
          while(m.state!=='executing'||m.phase<8)m.step(1/60);
          DSP_DEMO.draw();
        }''')
        page.locator('#recovery-canvas').scroll_into_view_if_needed()
        handle=page.locator('#eef-handle').bounding_box()
        start={'x':handle['x']+handle['width']/2,'y':handle['y']+handle['height']/2}
        if touch:
            cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[start]})
        else:
            page.mouse.move(**start);page.mouse.down()
        phase=page.evaluate('DSP_DEMO.model.phase')
        page.wait_for_function('DSP_DEMO.model.phase > '+str(phase))
        held_inside=page.evaluate('DSP_DEMO.model.snapshot()')
        assert held_inside['dragging'] and held_inside['state']=='executing'
        assert held_inside['anchor'] is None and held_inside['lockedPhase'] is None
        assert held_inside['acceptedPosition']==held_inside['position']
        page.locator('#interactive-recovery').screenshot(path=str(OUTPUT/f'{name}-interactive-before-trigger.png'))
        if touch:
            cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        else: page.mouse.up()
        assert not errors, errors
        print(f'PASS {name}: drag/touch, native progress during hold, trigger-only lock, fixed anchor, playback, restart, keyboard, rendering, no overflow/errors',flush=True)
        context.close()
    browser.close()
