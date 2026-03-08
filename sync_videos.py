import os
import yt_dlp
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

CHANNEL_URL = "https://www.youtube.com/@aetherautomation/videos"
DRIVE_FOLDER_ID = "1NqifLrBXJ89eWtzuAW166X7BoRLm2YED"

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

DOWNLOAD_FOLDER = "downloads"
ARCHIVE_FILE = "download_archive.txt"

creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

drive = build("drive", "v3", credentials=creds)

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",

    # 👇 nombre con título del video
    "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s [%(id)s].%(ext)s",

    "download_archive": ARCHIVE_FILE,
}

print("Checking channel for new videos...")

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([CHANNEL_URL])

for file in os.listdir(DOWNLOAD_FOLDER):

    if file.endswith(".mp4"):

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

print("Sync complete")
