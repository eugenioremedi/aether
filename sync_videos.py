import os
import yt_dlp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -----------------------------
# CONFIGURATION
# -----------------------------

# YouTube RSS feed for the channel
CHANNEL_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=UC7sDT8jZ76VLV1u__krUutA"

# Google Drive folder ID
DRIVE_FOLDER_ID = "1NqifLrBXJ89eWtzuAW166X7BoRLm2YED"

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# -----------------------------
# GOOGLE DRIVE AUTH
# -----------------------------

creds = Credentials(
    None,
    refresh_token=os.environ["GDRIVE_REFRESH_TOKEN"],
    client_id=os.environ["GDRIVE_CLIENT_ID"],
    client_secret=os.environ["GDRIVE_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token"
)

drive = build("drive", "v3", credentials=creds)

# -----------------------------
# GET FILES ALREADY IN DRIVE
# -----------------------------

results = drive.files().list(
    q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
    fields="files(name)"
).execute()

drive_files = [f["name"] for f in results.get("files", [])]

print("Files already in Drive:", len(drive_files))

# -----------------------------
# GET YOUTUBE VIDEO LIST
# -----------------------------

ydl_opts = {
    "extract_flat": True,
    "quiet": True,
    "skip_download": True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(CHANNEL_URL, download=False)

videos = info["entries"]

print("Videos in RSS feed:", len(videos))

# -----------------------------
# PROCESS VIDEOS
# -----------------------------

for video in videos:

    video_id = video["id"]
    video_url = f"https://youtube.com/watch?v={video_id}"

    filename = f"{video_id}.mp4"

    if filename in drive_files:
        print("Skipping:", video_id)
        continue

    print("Downloading:", video_id)

    ydl_download_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "format": "best[ext=mp4]/best",
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_download_opts) as ydl2:
        ydl2.download([video_url])

    filepath = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(filepath):
        print("Download failed:", video_id)
        continue

    print("Uploading:", filename)

    media = MediaFileUpload(filepath)

    file_metadata = {
        "name": filename,
        "parents": [DRIVE_FOLDER_ID]
    }

    drive.files().create(
        body=file_metadata,
        media_body=media
    ).execute()

print("Sync finished")
