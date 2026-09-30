"""Copy the overview and extract original task clips from the matching deck."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import hashlib
import json
import shutil
import subprocess

import cv2
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / 'Downloads'
VIDEOS = ROOT / 'static' / 'videos'
POSTERS = ROOT / 'static' / 'images' / 'videos'
VIDEOS.mkdir(parents=True, exist_ok=True)
POSTERS.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SOURCES = {
    'cola': {'success': (12, 'media10.mp4'), 'failure': (11, 'media8.mp4')},
    'drawer': {'success': (12, 'media1.mp4'), 'failure': (11, 'media6.mp4')},
    'sweep': {'success': (12, 'media9.mp4'), 'failure': (11, 'media7.mp4')},
    'coffee': {'success': (12, 'media4.mp4'), 'failure': (11, 'media5.mp4')},
}


def run(*args):
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', *args], check=True)


def metadata(path):
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    result = {'duration': capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps,
              'width': int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
              'height': int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
              'fps': fps, 'bytes': path.stat().st_size}
    capture.release()
    return result


source = DOWNLOADS / 'ICRA2027_DSP_video_under20MB.mp4'
overview = VIDEOS / 'dsp-overview.mp4'
shutil.copy2(source, overview)
assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(overview.read_bytes()).digest()
run('-ss', '0.5', '-i', str(overview), '-frames:v', '1', '-q:v', '2', str(POSTERS / 'overview.jpg'))
manifest = {'overview': {'source': source.name, 'path': 'static/videos/dsp-overview.mp4',
                         'operation': 'byte-for-byte copy', **metadata(overview)}, 'clips': {}}
with ZipFile(DOWNLOADS / 'ICRA2027_DSP_video_template.pptx') as deck, TemporaryDirectory() as temp:
    for task, outcomes in SOURCES.items():
        manifest['clips'][task] = {}
        for outcome, (slide, name) in outcomes.items():
            embedded = 'ppt/media/' + name
            data = deck.read(embedded)
            raw = Path(temp) / name
            raw.write_bytes(data)
            output = VIDEOS / f'{task}-{outcome}.mp4'
            # Stream copy preserves all frames, audio, and existing playback speed.
            run('-i', str(raw), '-map', '0:v:0', '-map', '0:a?', '-c', 'copy',
                '-movflags', '+faststart', str(output))
            poster = POSTERS / f'{task}-{outcome}.jpg'
            run('-ss', '0.5', '-i', str(output), '-frames:v', '1', '-vf', 'scale=960:-2',
                '-q:v', '2', str(poster))
            manifest['clips'][task][outcome] = {
                'deck': 'ICRA2027_DSP_video_template.pptx', 'slide': slide,
                'embedded': embedded, 'source_sha256': hashlib.sha256(data).hexdigest(),
                'path': output.relative_to(ROOT).as_posix(),
                'poster': poster.relative_to(ROOT).as_posix(),
                'operation': 'stream copy, fast-start MP4; no crop, trim, or speed change',
                **metadata(output),
            }
(ROOT / 'video_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest, indent=2))
