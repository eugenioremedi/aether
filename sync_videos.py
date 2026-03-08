import os
import re
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
# PREPARE DOWNLOAD FOLDER
# ==========================================

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ==========================================
# CHECK VIDEOS ALREADY IN DRIVE
# ==========================================

def get_drive_video_ids():

    ids = set()
    page_token = None

    print("Scanning Drive...")

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


drive_ids = get_drive_video_ids()

# ==========================================
# UPLOAD FUNCTION
# ==========================================

def upload_to_drive(filepath):

    filename = os.path.basename(filepath)

    match = re.search(r"\[([A-Za-z0-9_-]{11})\]", filename)

    if match:

        video_id = match.group(1)

        if video_id in drive_ids:

            print("Already in Drive, skipping:", filename)
            os.remove(filepath)
            return

    print("Uploading:", filename)

    media = MediaFileUpload(filepath, resumable=True)

    drive.files().create(
        body={
            "name": filename,
            "parents": [DRIVE_FOLDER_ID],
        },
        media_body=media,
    ).execute()

    os.remove(filepath)

    print("Upload complete:", filename)

# ==========================================
# HOOK (UPLOAD AFTER DOWNLOAD)
# ==========================================

def progress_hook(d):

    if d["status"] == "finished":

        filepath = d["filename"]

        upload_to_drive(filepath)

# ==========================================
# YT-DLP OPTIONS
# ==========================================

ydl_opts = {

    # máxima calidad
    "format": "bestvideo+bestaudio/best",

    "merge_output_format": "mp4",

    # nombre del archivo
    "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s [%(id)s].%(ext)s",

    # evita duplicados
    "download_archive": ARCHIVE_FILE,

    # subida automática tras descarga
    "progress_hooks": [progress_hook],

    "retries": 10,
    "fragment_retries": 10,
}

# ==========================================
# START SYNC
# ==========================================

print("Checking channel for new videos...")

with yt_dlp.YoutubeDL(ydl_opts) as ydl:

    ydl.download([CHANNEL_URL])

print("Mirror sync complete.")
