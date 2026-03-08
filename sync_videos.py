import os
import re
import time
import yt_dlp

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

# ==========================================
# CONFIG
# ==========================================

CHANNEL_URL = "https://www.youtube.com/@aetherautomation/videos"

DRIVE_FOLDER_ID = "1NqifLrBXJ89eWtzuAW166X7BoRLm2YED"

DOWNLOAD_FOLDER = "downloads"
ARCHIVE_FILE = "download_archive.txt"

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

# ==========================================
# GOOGLE DRIVE AUTH
# ==========================================

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

drive = build("drive", "v3", credentials=creds)

# ==========================================
# PREPARE FOLDER
# ==========================================

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ==========================================
# REMOVE LOCAL DUPLICATES
# ==========================================

def remove_duplicate_videos(folder):

    seen_ids = set()

    for file in os.listdir(folder):

        if not file.endswith(".mp4"):
            continue

        match = re.search(r"\[([A-Za-z0-9_-]{11})\]", file)

        if not match:
            continue

        video_id = match.group(1)

        filepath = os.path.join(folder, file)

        if video_id in seen_ids:

            print("Duplicate detected, removing:", file)

            os.remove(filepath)

        else:

            seen_ids.add(video_id)

# ==========================================
# GET EXISTING VIDEOS IN DRIVE
# ==========================================

def get_drive_video_ids():

    print("Scanning Google Drive folder...")

    ids = set()

    page_token = None

    while True:

        response = drive.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
            fields="nextPageToken, files(name)",
            pageToken=page_token
        ).execute()

        for file in response.get("files", []):

            match = re.search(r"\[([A-Za-z0-9_-]{11})\]", file["name"])

            if match:
                ids.add(match.group(1))

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    print("Videos already in Drive:", len(ids))

    return ids

# ==========================================
# DOWNLOAD VIDEOS
# ==========================================

ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s [%(id)s].%(ext)s",
    "download_archive": ARCHIVE_FILE,
    "retries": 10,
    "fragment_retries": 10,
}

print("Checking channel for new videos...")

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([CHANNEL_URL])

# ==========================================
# CLEAN DUPLICATES
# ==========================================

print("Cleaning duplicates...")

remove_duplicate_videos(DOWNLOAD_FOLDER)

# ==========================================
# DRIVE CHECK
# ==========================================

drive_ids = get_drive_video_ids()

# ==========================================
# UPLOAD
# ==========================================

for file in os.listdir(DOWNLOAD_FOLDER):

    if not file.endswith(".mp4"):
        continue

    match = re.search(r"\[([A-Za-z0-9_-]{11})\]", file)

    if not match:
        continue

    video_id = match.group(1)

    if video_id in drive_ids:

        print("Already in Drive, skipping:", file)

        os.remove(os.path.join(DOWNLOAD_FOLDER, file))

        continue

    filepath = os.path.join(DOWNLOAD_FOLDER, file)

    print("Uploading:", file)

    media = MediaFileUpload(filepath, resumable=True)

    drive.files().create(
        body={
            "name": file,
            "parents": [DRIVE_FOLDER_ID],
        },
        media_body=media,
    ).execute()

    os.remove(filepath)

    time.sleep(1)

print("Mirror sync complete.")
