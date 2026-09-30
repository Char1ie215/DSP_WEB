from pathlib import Path
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "test-results"
OUTPUT.mkdir(exist_ok=True)
PUBLIC_URL = "https://char1ie215.github.io/DSP_WEB/"
assert [node.text for node in ET.parse(ROOT / "sitemap.xml").findall(
    "{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
)] == [PUBLIC_URL]

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=True,
    )
    for name, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844), ("small", 360, 780)]:
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "index.html").as_uri())
        assert page.locator('meta[name="robots"]').get_attribute('content') == 'index, follow'
        assert page.locator('link[rel="canonical"]').get_attribute('href') == PUBLIC_URL
        assert page.locator('link[rel="sitemap"]').get_attribute('href') == 'sitemap.xml'
        page.evaluate("document.querySelectorAll('img').forEach(i => i.loading = 'eager')")
        page.locator("footer").scroll_into_view_if_needed()
        page.wait_for_function("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), name
        assert page.locator('#authors > span').count() == 9
        assert page.locator('#affiliations').is_visible()
        assert page.locator('#affiliations > span').count() == 4
        assert page.locator('#authors > span > sup').all_text_contents() == ['1,*', '2,*', '2', '2', '3', '1', '1', '4', '2']
        assert page.locator('#author-note').is_visible()
        assert page.locator('#author-note').inner_text() == '* Equal contribution'
        assert page.locator('#teaser-video').is_visible()
        assert page.locator('#paper-link').is_visible()
        assert page.locator('#paper-link').get_attribute('href') == 'static/papers/paper.pdf'
        assert page.locator('#fullVideo-link').is_visible()
        assert page.locator('#fullVideo-link').get_attribute('href') == 'static/videos/dsp-overview.mp4'
        assert page.locator('#teaser-video').get_attribute('src') == 'static/videos/dsp-overview.mp4'
        assert page.locator('#teaser-video').get_attribute('poster') == 'static/images/videos/overview.jpg'
        assert page.locator('#teaser-download').get_attribute('href') == 'static/videos/dsp-overview.mp4'
        assert page.title() == 'Dynamic System Policy: Robust Visuomotor Policies via Gaussian Dynamic Fields'
        assert page.locator('.task-picker').count() == 0
        assert page.locator('#task-list > section').count() == 4
        assert page.locator('#sweep-title').inner_text() == 'Sweep Ball'
        assert page.locator('#task-list [data-role="description"], .clip-note').count() == 0
        assert page.locator('#task-list h3').all_text_contents() == [
            'Sweep Ball', 'Pick Cola', 'Place Bottle & Close Drawer', 'Coffee Preparation'
        ]
        assert page.locator('#task-list video').count() == 8
        assert page.locator('table').count() == 0
        assert page.locator('#results, .task-results, .paper-section').count() == 0
        assert page.locator('.method-figure').count() == 1
        assert page.locator('#interactive-title').inner_text() == 'What Is a Dynamical System?'
        assert page.locator('.field-explanation').inner_text() == (
            'A dynamical system describes how a state changes over time. '
            'Ours specifies how the robot should move from its current position to recover toward a fixed reference.'
        )
        assert page.locator('#abstract, a[href="#abstract"]').count() == 0
        assert page.locator('#recovery-canvas').is_visible()
        assert page.evaluate('typeof window.DSP_RESULTS') == 'undefined'
        previous_bottom = 0
        for task in ["sweep", "cola", "drawer", "coffee"]:
            section = page.locator(f'#task-{task}')
            assert section.is_visible()
            bounds = section.evaluate('(el) => ({y: el.getBoundingClientRect().top + scrollY, height: el.getBoundingClientRect().height})')
            assert bounds['y'] >= previous_bottom
            previous_bottom = bounds['y'] + bounds['height']
            for outcome in ['success', 'failure']:
                assert page.locator(f'#{task}-{outcome}-video').get_attribute('src').endswith(f'{task}-{outcome}.mp4')
            section.locator('[data-action="play"]').click()
            page.wait_for_function("task => Array.from(document.querySelectorAll(`#task-${task} video`)).every(v => v.currentTime > 0.1 && v.videoWidth > 0 && !v.error)", arg=task)
            assert page.evaluate("task => Array.from(document.querySelectorAll('#task-list video')).filter(v => !v.closest(`#task-${task}`)).every(v => v.paused)", task)
            section.locator('[data-action="pause"]').click()
            assert section.locator('video').evaluate_all('(videos) => videos.every(v => v.paused)')
            section.locator('[data-action="replay"]').click()
            page.wait_for_function("task => Array.from(document.querySelectorAll(`#task-${task} video`)).every(v => !v.paused && v.currentTime > 0.05 && v.currentTime < 3)", arg=task)
            section.locator('[data-action="pause"]').click()
            first, second = [v.bounding_box() for v in section.locator('video').all()]
            if width > 550:
                assert abs(first['y'] - second['y']) < 2
                assert first['x'] + first['width'] <= second['x']
            else:
                assert first['y'] + first['height'] <= second['y']
        page.locator('#teaser-video').evaluate('(v) => {v.muted = true; return v.play();}')
        page.wait_for_function("document.getElementById('teaser-video').currentTime > 0.1")
        assert abs(page.locator('#teaser-video').evaluate('(v) => v.duration') - 168.033) < 0.1
        page.locator('#teaser-video').evaluate('(v) => {v.pause(); v.currentTime = 0;}')
        for link in page.locator("a[href]").all():
            href = link.get_attribute("href")
            if href.startswith("#"):
                assert page.locator(href).count() == 1, href
            elif not href.startswith(("https:", "http:")):
                assert (ROOT / href).is_file(), href
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        page.screenshot(path=str(OUTPUT / f"{name}.png"), full_page=True)
        page.screenshot(path=str(OUTPUT / f"{name}-viewport.png"))
        page.locator('#task-list').screenshot(path=str(OUTPUT / f'{name}-videos.png'))
        page.locator('#interactive-recovery').screenshot(path=str(OUTPUT / f'{name}-field.png'))
        assert not errors, errors
        print(f"PASS {name}: authors, 168-second overview playback, paper link, no tables/scope, one method figure, field explanation, four tasks, 8 clips, controls, links, overflow, console")
        page.close()
    browser.close()
