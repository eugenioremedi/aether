import os
import yt_dlp
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CHANNEL_URL = "https://www.youtube.com/@aetherautomation/videos"
DRIVE_FOLDER_ID = "1NqifLrBXJ89eWtzuAW166X7BoRLm2YED"
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

creds = Credentials(
    None,
    refresh_token=os.environ["GDRIVE_REFRESH_TOKEN"],
    client_id=os.environ["GDRIVE_CLIENT_ID"],
    client_secret=os.environ["GDRIVE_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token"
)

drive = build("drive", "v3", credentials=creds)

results = drive.files().list(
    q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
    fields="files(name)"
).execute()

drive_files = [f["name"] for f in results.get("files", [])]

print("Files already in Drive:", len(drive_files))

ydl_opts = {
    "extract_flat": True,
    "quiet": True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(CHANNEL_URL, download=False)

videos = info["entries"]

print("Videos on channel:", len(videos))

for video in videos:

    title = video["title"]
    video_url = f"https://youtube.com/watch?v={video['id']}"
    filename = f"{title}.mp4"

    if filename in drive_files:
        print("Skipping:", title)
        continue

    print("Downloading:", title)

    ydl_download_opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "format": "mp4"
    }

    with yt_dlp.YoutubeDL(ydl_download_opts) as ydl2:
        ydl2.download([video_url])

    filepath = os.path.join(DOWNLOAD_DIR, filename)

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
