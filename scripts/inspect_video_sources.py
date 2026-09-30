"""Inspect supplied video and embedded clips without modifying the sources."""
from pathlib import Path
from zipfile import ZipFile
import json
import posixpath
import cv2
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results' / 'media-inspection'
OUT.mkdir(parents=True, exist_ok=True)
DOWNLOADS = Path.home() / 'Downloads'
NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def frames(path, times, prefix):
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    for time in times or [0.5, duration - 0.5]:
        capture.set(cv2.CAP_PROP_POS_MSEC, time * 1000)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f'Cannot read {path} at {time}')
        cv2.imwrite(str(OUT / f'{prefix}-{time:.1f}.jpg'), frame)
    capture.release()
    return duration


frames(DOWNLOADS / 'ICRA2027_DSP_video_under20MB.mp4', [0.5, 137, 145, 154, 162, 167], 'overview')
records = []
with ZipFile(DOWNLOADS / 'ICRA2027_DSP_video_template.pptx') as deck:
    for slide in [11, 12]:
        xml = etree.fromstring(deck.read(f'ppt/slides/slide{slide}.xml'))
        rels = etree.fromstring(deck.read(f'ppt/slides/_rels/slide{slide}.xml.rels'))
        targets = {r.get('Id'): r.get('Target') for r in rels}
        for pic in xml.findall('.//p:pic', NS):
            video = pic.find('.//a:videoFile', NS)
            if video is None:
                continue
            name = pic.find('.//p:cNvPr', NS).get('name')
            rid = video.get('{' + NS['r'] + '}link')
            source = posixpath.normpath('ppt/slides/' + targets[rid])
            local = OUT / Path(source).name
            local.write_bytes(deck.read(source))
            offset = pic.find('.//a:off', NS)
            record = {'slide': slide, 'name': name, 'source': source,
                      'x': int(offset.get('x')), 'y': int(offset.get('y')),
                      'duration': frames(local, None, local.stem)}
            records.append(record)
(OUT / 'inspection.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print(json.dumps(records, indent=2))
