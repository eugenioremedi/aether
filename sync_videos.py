import os
import json
import requests
import yt_dlp

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ------------------------
# CONFIG
# ------------------------

CHANNEL_ID = "UC7sDT8jZ76VLV1u__krUutA"
API_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

DRIVE_FOLDER_ID = "1NqifLrBXJ89eWtzuAW166X7BoRLm2YED"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

INDEX_FILE = "video_ids.json"

# ------------------------
# LOAD INDEX
# ------------------------

if os.path.exists(INDEX_FILE):
    with open(INDEX_FILE, "r") as f:
        known_ids = set(json.load(f))
else:
    known_ids = set()

# ------------------------
# GET VIDEOS FROM RSS
# ------------------------

import xml.etree.ElementTree as ET

response = requests.get(API_URL)
root = ET.fromstring(response.content)

namespace = {
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "atom": "http://www.w3.org/2005/Atom"
}

rss_ids = []

for entry in root.findall("atom:entry", namespace):
    video_id = entry.find("yt:videoId", namespace).text
    rss_ids.append(video_id)

# ------------------------
# FIND NEW VIDEOS
# ------------------------

new_videos = [vid for vid in rss_ids if vid not in known_ids]

print("New videos:", new_videos)

if not new_videos:
    print("No new videos. Exiting.")
    exit()

# ------------------------
# GOOGLE DRIVE AUTH
# ------------------------

creds = Credentials(
    None,
    refresh_token=os.environ["GDRIVE_REFRESH_TOKEN"],
    client_id=os.environ["GDRIVE_CLIENT_ID"],
    client_secret=os.environ["GDRIVE_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token"
)

drive = build("drive", "v3", credentials=creds)

# ------------------------
# DOWNLOAD + UPLOAD
# ------------------------

for video_id in new_videos:

    url = f"https://youtube.com/watch?v={video_id}"

    print("Downloading:", video_id)

    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "format": "best[ext=mp4]/best",
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    filepath = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")

    if not os.path.exists(filepath):
        print("Download failed:", video_id)
        continue

    print("Uploading:", video_id)

    media = MediaFileUpload(filepath)

    file_metadata = {
        "name": f"{video_id}.mp4",
        "parents": [DRIVE_FOLDER_ID]
    }

    drive.files().create(
        body=file_metadata,
        media_body=media
    ).execute()

    known_ids.add(video_id)

# ------------------------
# SAVE INDEX
# ------------------------

with open(INDEX_FILE, "w") as f:
    json.dump(sorted(list(known_ids)), f, indent=2)

print("Index updated.")
