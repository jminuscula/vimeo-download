import base64
import requests
import tempfile
import os
import os.path
import subprocess

from urllib.parse import urljoin
from distutils.spawn import find_executable


import logging
logging.basicConfig()
logger = logging.getLogger('vimeodownload')


def get_manifest_data(manifest_url):
    resp = requests.get(manifest_url)
    if not resp.ok:
        logger.error('Could not fetch manifest data: {}'.format(resp))
        logger.debug('Url: {} | Response: {}'.format(manifest_url, resp.content.decode('utf-8')))
        return None

    return resp.json()


def download_component(base_url, component, path):
    component_base_url = urljoin(base_url, component['base_url'])
    init_segment = base64.b64decode(component['init_segment'])

    with open(path, 'wb') as fp:
        fp.write(init_segment)

        for segment in component['segments']:
            segment_url = urljoin(component_base_url, segment['url'])
            resp = requests.get(segment_url, stream=True)

            if not resp.ok:
                logger.error('Error downloading data segment: {}'.format(resp))
                logger.debug('Url: {} | Response: {}'.format(segment_url, resp.content.decode('utf-8')))
                return False

            for chunk in resp:
                fp.write(chunk)

    return True


def download_video(base_url, data, tempdir):
    # find entry with max resolution
    video = max(data, key=lambda e: e.get('height', -1))
    path = os.path.join(tempdir, 'video.mp4')

    logger.debug('Downloading video...')
    if download_component(base_url, video, path):
        return path


def download_audio(base_url, data, tempdir):
    path = os.path.join(tempdir, 'audio.mp3')

    logger.debug('Downloading audio...')
    if download_component(base_url, data[0], path):
        return path


def merge_video_and_audio(video_path, audio_path, out_path):
    if os.name == 'nt':
        ffmpeg, shell = 'ffmpeg.exe', True
    else:
        ffmpeg, shell = find_executable("ffmpeg") or 'ffmpeg', False

    command = (
        ffmpeg,
        '-i', video_path,
        '-i', audio_path,
        '-vcodec', 'copy',
        '-acodec', 'copy',
        out_path
    )

    logger.debug('Merging data...')
    return subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)


def download(manifest_url, out_path):
    manifest = get_manifest_data(manifest_url)
    base_url = urljoin(manifest_url, manifest.get('base_url'))
    video_data = manifest.get('video')
    audio_data = manifest.get('audio')

    if not all((base_url, video_data, audio_data)):
        logger.error('Invalid video metadata')
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        logger.debug('Downloading video to {}'.format(tmpdir))
        video_path = download_video(base_url, video_data, tmpdir)
        audio_path = download_audio(base_url, audio_data, tmpdir)

        if not all((video_path, audio_path)):
            logger.error('Could not fetch video data')
            return

        merge_video_and_audio(video_path, audio_path, out_path)

    return True
