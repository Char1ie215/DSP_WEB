"""Check archived table data against the paper; tables are not shown on the site."""
from pathlib import Path
import re

import fitz
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'static' / 'papers' / 'paper.pdf'
with fitz.open(SOURCE) as document:
    page5 = document[4].get_text()
    page6 = document[5].get_text()
expected = {
    'I': re.findall(r'\d+\.\d+', page5.split('TABLE II')[0]),
    'II': re.findall(r'\d+\.\d+', page5.split('TABLE II')[1].split('receives RGB')[0]),
    'III': re.findall(r'\d+/10', page6.split('TABLE III')[1].split('TABLE IV')[0]),
    'IV': re.findall(r'\d+/10', page6.split('TABLE IV')[1].split('selection strategy')[0]),
}
assert [len(expected[key]) for key in ['I', 'II', 'III', 'IV']] == [36, 5, 24, 2]

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        headless=True,
    )
    page = browser.new_page()
    page.goto((ROOT / 'index.html').as_uri())
    assert page.locator('table').count() == 0
    page.add_script_tag(path=str(ROOT / 'static' / 'js' / 'results.js'))
    data = page.evaluate('window.DSP_RESULTS')
    actual = {
        'I': [value for row in range(4) for benchmark in data['simulation'] for value in benchmark['rows'][row]],
        'II': [value for key in ['recovery', 'scaling'] for row in data[key]['rows'] for value in row],
        'III': [value for row in range(4) for task in ['cola', 'drawer', 'sweep'] for value in data['realWorld'][task]['rows'][row]],
        'IV': [value for row in data['realWorld']['coffee']['rows'] for value in row],
    }
    for key in expected:
        assert actual[key] == expected[key], (key, actual[key], expected[key])
        print(f'PASS manuscript Table {key}: {len(expected[key])} exact values')
    print('PASS archived data: 55 success entries, 12 push distances; no tables on homepage')
    browser.close()
