#!/usr/bin/env python
# coding: utf-8

# # DLNA file browsing html create notebook
# 
# **This notebook does**
# - Get video files on network drive of NAS
# - Get video files via DLNA protocol
# - Map video files between network drive and DLNA
# - Create html files to browse video files with thumbnail
# 
# **Preparation**
# - Install ffmpeg for extracting thumbnail from video
# - set environment variables
#  - nas_mount_dir : mount path of NAS for video files
#  - nas_mount_thumb_folder : mount path of NAS for thumbnail
#  - html_thumb_folder : video thumbnail folder in web server
#  - BASIC_USER : basic authentication user name for php
#  - BASIC_PASSWD : basic authentication password for php
# - mount DLNA server as network drive

# # Initial setting

import pandas as pd
import datetime
import glob
import os
import sys
from typing import List
from tqdm import tqdm
import warnings
import subprocess
from IPython.display import clear_output

warnings.filterwarnings('ignore')


paths = ['../dlnautil']
paths = [p for p in paths if p not in sys.path]
sys.path.extend(paths)


# # Setting from environment variables

nas_mount_dir = os.environ['nas_mount_dir']
nas_ip_address = os.environ['nas_ip_address']

nas_mount_thumb_output_folder = os.environ['nas_mount_thumb_folder']
html_thumb_folder = os.environ['html_thumb_folder']
html_output_folder = './htmls'

user = os.environ['BASIC_USER']
pwd = os.environ['BASIC_PASSWD']


# # Get file paths on NAS (Network Attached Storage)

def get_files(dir_name: str, exts: List, level: int =0) -> dict:
    #print(dir_name)
    ret = {}
    exts_ = {e.upper(): e for e in exts}
    files = glob.glob(f'{dir_name}/*')
    nlevel = level + 1
    for i, f in enumerate(files):
        if os.path.isdir(f):
            files_dict = get_files(f, exts, nlevel)
            for k, v in files_dict.items():
                ret.setdefault(k, []).extend(v)
        elif os.path.isfile(f):
            ext = f.split('.')[-1].upper() if '.' in f else ''
            if exts_.get(ext):
                ret.setdefault(exts_.get(ext), []).append(f)
        if level == 0:
            print(f'{i+1}/{len(files)}')

    return ret


files = get_files(nas_mount_dir, ['mp4', 'm2ts', 'mts'])

# # Create thumbnail

def create_thumb(filename, ext='mp4', ss=1, vframes=1):
    result = None
    out_filename = filename.replace(f'.{ext.upper()}', '.jpg').replace(f'.{ext}', '.jpg')
    out_folder = out_filename.split('/')[-2]
    out_folder = f'{nas_mount_thumb_output_folder}/{out_folder}'
    out_filename = os.path.basename(out_filename)
    out_filepath = f'{out_folder}/{out_filename}'
    #print(filename)
    #print(out_filepath)
    if out_filepath.endswith('.jpg'):
        if not os.path.exists(out_folder):
            os.makedirs(out_folder, exist_ok=True)
        if not os.path.exists(out_filepath):
            print(out_filepath)
            command = f'ffmpeg -i {filename} -ss {ss} -vframes {vframes} -s 320x180 {out_filepath}'
            command = command.split(' ')
            print(command)
            result = subprocess.run(command)
            print(result)
            clear_output()
            return out_filepath
        
    return None


thumbnails = []
for k, v in files.items():
    for filepath in v:
        thumb = create_thumb(filepath, ext=k)
        if thumb:
            thumbnails.append(thumb)
            #print(thumb)
            #break

print(f'thumb count={len(thumbnails)}')

# # Create file list

df_mp4 = pd.DataFrame(files['mp4'], columns=['path'])
df_mp4['key'] = df_mp4['path'].map(lambda x: '.'.join(x.split('.')[:-1]))
df_m2ts = pd.DataFrame(files['m2ts'], columns=['path'])
df_m2ts['key'] = df_m2ts['path'].map(lambda x: '.'.join(x.split('.')[:-1]))
df_mts = pd.DataFrame(files['mts'], columns=['path'])
df_mts['key'] = df_mts['path'].map(lambda x: '.'.join(x.split('.')[:-1]))
df_m2ts = pd.concat([df_m2ts, df_mts])

df_files = pd.merge(df_m2ts, df_mp4, how='outer', on='key', suffixes=['_m2ts', '_mp4'])
df_files['path'] = df_files['path_m2ts'].where(~df_files['path_m2ts'].isnull(), df_files['path_mp4'])
df_files['stat'] = df_files['path'].map(os.stat)
df_files

df_files['title'] = df_files['path'].map(os.path.basename)
df_files['title'] = df_files['title'].map(lambda x: x.split('.'))

df_files['ext'] = df_files['title'].map(lambda x: x[-1] if len(x) > 1 else '')
df_files['title'] = df_files['title'].map(lambda x: '.'.join(x[:-1]) if len(x) > 1 else x)

df_files['size'] = df_files['stat'].map(lambda x: x.st_size)
df_files['atime'] = df_files['stat'].map(lambda x: datetime.datetime.fromtimestamp(x.st_atime))
df_files['mtime'] = df_files['stat'].map(lambda x: datetime.datetime.fromtimestamp(x.st_mtime))
df_files['ctime'] = df_files['stat'].map(lambda x: datetime.datetime.fromtimestamp(x.st_ctime))
df_files = df_files.sort_values('path')
df_files


# # Get DLNA ContentDirectory Media Server

import importlib
import content_browse
import server_search
importlib.reload(server_search)


servers = server_search.search()
servers

servers[0].get_detail()


# choose server
server = None
for s in servers:
    url = s.get_detail().get('url')
    print(url)
    if nas_ip_address not in url:
        print('skip')
        continue
    server = s
    stype = s.get_detail()['serviceType']
    break


# # DLNA Contents browsing (Get video files via DLNA)

# root folder検索
contents = content_browse.browse(url=url, st=stype)
contents


# "ビデオ" を検索
item = [c for c in contents if c.get_data().get('title') == 'ビデオ'][0]
items = content_browse.browse(url=url, st=stype, item_id=item.get_data().get('id'))
items


# "全てのビデオ" を検索
item = [i for i in items if i.get_data().get('title') == '全てのビデオ'][0]
item_id = item.get_data().get('id')

all_items = content_browse.browse(url=url, st=stype, item_id=item_id)
df_dlna = pd.DataFrame([i.get_data() for i in all_items])
df_dlna


df_files['album'] = df_files['path'].map(lambda x: x.split('/')[-2])
df_files['key'] = df_files['album'] + '/' + df_files['title']
df_dlna['key'] = df_dlna['album'] + '/' + df_dlna['title']


df_all = pd.merge(df_dlna, df_files, how='left', on='key', suffixes=['_dlna', '_file'])
df_all[~df_all['path'].isnull()]
df_all = df_all[df_all['path'].str.startswith(nas_mount_dir).fillna(False)]
df_all['year'] = df_all['date'].map(lambda x: x.split('-')[0])
df_all = df_all.sort_values(['album_dlna', 'title_dlna', 'protocolInfo'])
df_all


df_all['mtime_dlna'] = df_all['modificationTime'].map(lambda x: datetime.datetime.fromtimestamp(int(x)))
df_all['atime_dlna'] = df_all['addedTime'].map(lambda x: datetime.datetime.fromtimestamp(int(x)))
df_all['utime_dlna'] = df_all['lastUpdated'].map(lambda x: datetime.datetime.fromtimestamp(int(x)))
df_all['year'] = df_all['album_dlna'].map(lambda x: x[:4])
df_all['month'] = df_all['album_dlna'].map(lambda x: x[5:7])
# sort by protoclInfo and keep last (mt2s is prioritized than mp4)
df_all = df_all.sort_values(['album_dlna', 'title_dlna', 'protocolInfo'])
df_all = df_all.drop_duplicates(subset=['path'], keep='last')
df_all


# # Create html

# ## Create html per year

html_template_1 = """<?php
switch(true) {
  case !isset($_SERVER['PHP_AUTH_USER'], $_SERVER['PHP_AUTH_PW']):
  case $_SERVER['PHP_AUTH_USER'] !== '{user}':
  case $_SERVER['PHP_AUTH_PW'] !== '{pwd}':
    header('WWW-Authenticate: Basic realm="Enter username/password."');
    header('Content-Type: text/plain; charset=utf-8');
    die('Private page. Need to login.');
}

header('Content-Type: text/html; charset=utf-8');
?>
"""

html_item_template = """
<div class="grid_cell">
  <div class="grid_title">{grid_title}</div>
  <div class="grid_subtitle">{resolution}/{ext}</div>
  <div class="grid_subtitle2">{duration}</div>
  <img class="grid_image" src="{thumb}"/>
  <img class="grid_playicon" src="icons/play.png" style="visibility:hidden"/>
  <div class="grid_image_overlay" id="{seq_idx}"></div>
</div>
"""

html_year_template_1 = """
<html>
<head>
    <meta charset="UTF-8">
    <meta name = "format-detection" content = "telephone=no">    
    <link href="https://fonts.googleapis.com/css?family=Anton rel="stylesheet">
    <link rel="stylesheet" href="css.css">
    <title>{key}</title>
    <script type="text/javascript">
      let _videos = [{videos_array}];
      let _playIcons = [];
      let _titles = [];
      let _curPlayIcon = null;
      let _curPlayIdx = -1;
      let _curTimeout = null;
      let _prevPlayPosition = null;
      let _waitForNextState = false;

      function closePlayObject() {{
        var req = new XMLHttpRequest();
        req.open("GET", "video_stop.php", false);
        req.send(null);

        var playArea = document.getElementById("play_area");
        if (playArea.children.length > 0) {{
          console.log('remove')
          playArea.children[0].remove()
        }}
      }}

      function clearPlay() {{
        closePlayObject()
        if (_curTimeout != null) {{
            clearTimeout(_curTimeout);
            _curTimeout = null;
        }}
        if (_curPlayIcon != null) {{
          _curPlayIcon.style.visibility = 'hidden';
          _curPlayIcon = null;
        }}
        document.getElementById('play_status').style.visibility = 'hidden'
        document.getElementById('play_status').innerHTML = ''
      }}

      function curPlay() {{
        clearPlay()
        if (_curPlayIdx < _playIcons.length) {{
          _curPlayIcon = _playIcons[_curPlayIdx];
          _curPlayIcon.style.visibility = 'visible';
        }}

        // MP4
        if (_videos[_curPlayIdx].endsWith('mp4') || _videos[_curPlayIdx].endsWith('MP4')) {{
          console.log('start mp4')
          var video = document.createElement("video");
          video.src = _videos[_curPlayIdx];
          video.setAttribute("controls","");
          document.getElementById('play_area').appendChild(video);
          video.addEventListener('ended', function() {
            console.log('mp4 ended')
            _curPlayIdx = _curPlayIdx + 1;
            if (_curPlayIdx >= _videos.length) {{
              _curPlayIdx = 0;
            }}
            curPlay()
          },false)
          video.play()
          video.width = 600
          video.height = 400
          return
        }}

        // M2TS
        var req = new XMLHttpRequest();
        req.open("GET", "video_set_play.php?url=" + _videos[_curPlayIdx], false);
        req.send(null);
        curTimeout = setTimeout(checkPlay, 5000);
        document.getElementById('play_status').style.visibility = 'visible'
        play_status = 'Now buffering ... ' + _titles[_curPlayIdx] + '(' + (_curPlayIdx+1) + '/' + _videos.length + ')'
      }}

      function removeTag(target, source) {{
        ret = source.replace('<' + target + '>', '');
        ret = ret.replace('</' + target + '>', '');
        return ret
      }}

      function checkPlay() {{
        var req = new XMLHttpRequest();
        req.open("GET", "video_get_position.php", false);
        req.send(null);
        trackUri = req.responseText.match(/<TrackURI>.*<\/TrackURI>/)[0];
        trackUri = removeTag('TrackURI', trackUri);
        durationTxt = req.responseText.match(/<TrackDuration>.*<\/TrackDuration>/)[0];
        durationTxt = removeTag('TrackDuration', durationTxt);
        durationTxt = durationTxt.split('.')[0];
        progressTxt = req.responseText.match(/<RelTime>.*<\/RelTime>/)[0];
        progressTxt = removeTag('RelTime', progressTxt);
        progressTxt = progressTxt.split('.')[0];
        relCount = req.responseText.match(/<RelCount>.*<\/RelCount>/)[0];
        relCount = removeTag('RelCount', relCount);
        play_status = 'Now plaing ... ' + _titles[_curPlayIdx] + '(' + (_curPlayIdx+1) + '/' + _videos.length + ') : ' + progressTxt + '/' + durationTxt;
        //console.log(play_status);
        document.getElementById('play_status').innerHTML = play_status;

        isCurUri = trackUri == _videos[_curPlayIdx];
        if (isCurUri && (_prevPlayPosition == '0' || _prevPlayPosition != relCount)) {{
          _curTimeout = setTimeout(checkPlay, 1000);
        }} else if (_waitForNextState == false) {{
          _waitForNextState = true;
          _curTimeout = setTimeout(checkPlay, 1500);
        }} else {{
          _waitForNextState = false;
          _curPlayIdx = _curPlayIdx + 1;
          if (_curPlayIdx >= _videos.length) {{
            _curPlayIdx = 0;
          }}
          console.log('nextPlay--- ' + _curPlayIdx + ', ' + isCurUri + ', ' + _prevPlayPosition + ', ' + relCount);
          curPlay()
        }}
        _prevPlayPosition = relCount;
      }}

      function init() {{
        var root = document.getRootNode()

        // Stop icon setting
        var stop = document.getElementById("overlay_icon");
        stop.addEventListener('click', function() {{
          console.log("click stop");
          clearPlay()
        }})

        // Grid item
        var gridItems = root.getElementsByClassName("grid_cell");
        console.log('grid item size = ' + gridItems.length);
        // Grid child setting
        for (var i = 0; i < gridItems.length; i++) {{
          console.log('--- item ' + i);
          item = gridItems[i];
          for (var j = 0; j < item.children.length; j++) {{
            childItem = item.children[j];
            if (childItem.className == 'grid_title') {{
              _titles.push(childItem.innerHTML)
            }} else if (childItem.className == 'grid_playicon') {{
              _playIcons.push(childItem)
            }} else if (childItem.className == 'grid_image_overlay') {{
              var video_idx = parseInt(childItem.id, 10);

              console.log(childItem.id + ' ' + video_idx)
              if (video_idx < _videos.length) {{
                console.log('item ' + video_idx + ' addEventLister for play');
                childItem.addEventListener('click', {videoIdx: video_idx, handleEvent: function() {{
                  console.log("start play " + this.videoIdx);
                  _curPlayIdx = this.videoIdx;
                  curPlay()
                }
                }})
              }}
            }}
          }}
        }}
      }}
    </script>
</head>

<body onload="init()">
<a href="index.php">Top</a>{prev_year}{next_year}
"""

html_year_template_2 = """
</div>
<p>
<p>
<div id="play_area"></div>
<div id="play_status"></div>
<div id="overlay_icon"><img src="icons/stop.png"/></div>
<a href="index.php">Top</a>{prev_year}{next_year}
</body>
</html>
"""


import re

def create_item(key, x, seq_idx):
    #url = x['res']
    path = x['path']
    #title = x['title_dlna']
    resolution = x['resolution']
    ext = x['ext']
    duration = x['duration']
    album = x['album_dlna']
    name = os.path.basename(path)
    name = name.replace(f'.{ext}', '')
    m = re.match('\d{14}', name)
    time_str = None
    if m:
        time_str = name[8:]
    grid_title = f'{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}' if time_str else name
    
    if duration:
        duration = duration.split('.')[0]

    thumb = f'{html_thumb_folder}/{album}/{name}.jpg'
    #if ext.lower().endswith('m2ts') or ext.lower().endswith('mts'):
    #    url = f'./videoplay.html?title={grid_title}&duration={duration}&thumb={thumb}&url={url}'

    return html_item_template \
            .replace('{grid_title}', grid_title) \
            .replace('{resolution}', resolution) \
            .replace('{ext}', ext) \
            .replace('{duration}', duration) \
            .replace('{thumb}', thumb) \
            .replace('{seq_idx}', str(seq_idx))


def create_year_html(key, group, years):
    # print(key)
    df = group.sort_values('title_dlna')

    html_text = html_template_1.replace('{user}', user).replace('{pwd}', pwd)

    year_idx = years.index(key) if key in years else None
    prev_year = years[year_idx-1] if year_idx - 1 >= 0 else None
    prev_year = f': <a href="{prev_year}.php">{prev_year}</a>' if prev_year else ''
    next_year = years[year_idx+1] if year_idx + 1 < len(years) else None
    next_year = f': <a href="{next_year}.php">{next_year}</a>' if next_year else ''
    
    html_text += html_year_template_1.replace('{key}', key)\
                                     .replace('{prev_year}', prev_year)\
                                     .replace('{next_year}', next_year)

    video_urls = []
    seq_idx = 0
    for key2, group2 in df.groupby('album_dlna'):
        html_text += f'<div class="title">{key2}</div>\n'
        html_text += '<div class="grid">'

        df2 = group2.sort_values('title_dlna')
        for i in range(len(df2)):
            x = df2.iloc[i, :]
            html_text += create_item(key, x, seq_idx)
            url = x['res']
            video_urls.append(url)
            seq_idx += 1
        
        html_text += '</div>\n'

    html_text += html_year_template_2.replace('{prev_year}', prev_year)\
                                     .replace('{next_year}', next_year)
    
    html_text = html_text.replace('{videos_array}', ','.join(["'" + url + "'" for url in video_urls]))

    phpfile = f'{html_output_folder}/{key}.php'
    with open(phpfile, 'w', encoding='utf-8') as f:
        f.write(html_text)
    print(f'output {key}')
    keys.append(key)


###### main loop ######
os.makedirs(html_output_folder, exist_ok=True)
years = sorted(df_all['year'].unique().tolist())
keys = []

for key, group in df_all.groupby('year'):
    create_year_html(key, group, years)


# ## Create html for top

html_top_item_template = \
"""    
<div class="grid_cell">
    <div class="grid_title_large">{k}</div>
    <a href="{k}.php" target="_blank" rel="noopener noreferrer"><img class="grid_image" src="{html_thumb_folder}/{thumb}.jpg"/></a>
</div>
"""

html_top_template_1 = \
"""
<html>
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css?family=Anton rel="stylesheet">
    <link rel="stylesheet" href="css.css">
    <title>Family Videos</title>
</head>

<body>
<div class="title">Family Videos</div>
<div class="grid">
"""

html_top_template_2 = \
"""
</div>
</body>
</html>
"""

import random

html_text = html_template_1.replace('{user}', user).replace('{pwd}', pwd)
html_text += html_top_template_1

for k in keys:
    # create year item
    df_tmp = df_all[df_all['year'] == k]
    print(f'video of {k} : {len(df_tmp)}')
    item = df_tmp.iloc[random.randint(0, len(df_tmp)-1)]
    thumb = f'{item.album_dlna}/{item.title_dlna}'    
    html_text += html_top_item_template.replace('{k}', k)\
                                       .replace('{html_thumb_folder}', html_thumb_folder)\
                                       .replace('{thumb}', thumb)

html_text += html_top_template_2

phpfile = f'{html_output_folder}/index.php'
with open(phpfile, 'w', encoding='utf-8') as f:
    f.write(html_text)
print(f'output {phpfile}')
