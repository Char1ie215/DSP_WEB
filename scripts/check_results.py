"""Compare every reported table value against the supplied manuscript PDF."""
from pathlib import Path
import re

import fitz
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / 'Downloads' / 'ICRA2027_DSP.pdf'
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
    tables = {item['id']: item for item in data['simulation']}
    tables.update(data['realWorld'])
    tables.update({key: data[key] for key in ['recovery', 'scaling']})
    assert page.locator('.data-table').count() == 9
    for key, table in tables.items():
        rendered = page.locator(f'#results-{key} tbody td').all_text_contents()
        assert rendered == [value for row in table['rows'] for value in row], key
        assert page.locator(f'#results-{key} tbody th').all_text_contents() == table.get('methods', data['methods']), key
    print('PASS all 9 rendered tables: method labels, 55 success entries, 12 push distances')
    browser.close()
