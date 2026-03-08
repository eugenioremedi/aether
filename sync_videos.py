import os
import re
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


def get_drive_service():
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    return build("drive", "v3", credentials=creds)


def sanitize_filename(name):
    """Remove or replace characters that are invalid on Windows."""
    # Replace problematic characters with underscores
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove trailing dots and spaces (Windows doesn't allow them)
    name = name.rstrip(". ")
    return name


def get_existing_drive_files(drive):
    """Get set of filenames already in the Drive folder to avoid re-uploading."""
    existing = set()
    page_token = None
    query = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false"

    while True:
        resp = drive.files().list(
            q=query,
            fields="nextPageToken, files(name)",
            pageToken=page_token,
            pageSize=100,
        ).execute()

        for f in resp.get("files", []):
            existing.add(f["name"])

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return existing


def upload_to_drive(drive, filepath, filename):
    """Upload a single file to Google Drive with error handling."""
    print(f"  Uploading: {filename}")
    media = MediaFileUpload(filepath, resumable=True)

    drive.files().create(
        body={
            "name": filename,
            "parents": [DRIVE_FOLDER_ID],
        },
        media_body=media,
    ).execute()

    print(f"  Uploaded OK: {filename}")


def main():
    drive = get_drive_service()
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    # Fetch list of files already in Drive (as a safety net beyond the archive)
    print("Checking existing files in Drive folder...")
    existing_files = get_existing_drive_files(drive)
    print(f"  Found {len(existing_files)} file(s) already in Drive.")

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s [%(id)s].%(ext)s",
        "download_archive": ARCHIVE_FILE,
        "restrictfilenames": False,
        # Windows-safe: let yt-dlp replace problematic chars
        "windowsfilenames": True,
    }

    print("Checking channel for new videos...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([CHANNEL_URL])

    # Upload any downloaded mp4 files
    uploaded = 0
    errors = 0

    for file in os.listdir(DOWNLOAD_FOLDER):
        if not file.endswith(".mp4"):
            continue

        filepath = os.path.join(DOWNLOAD_FOLDER, file)
        safe_name = sanitize_filename(file)

        if safe_name in existing_files:
            print(f"  Skipping (already in Drive): {safe_name}")
            os.remove(filepath)
            continue

        try:
            upload_to_drive(drive, filepath, safe_name)
            os.remove(filepath)
            uploaded += 1
        except Exception as e:
            print(f"  ERROR uploading {safe_name}: {e}")
            errors += 1

    print(f"\nSync complete — uploaded: {uploaded}, errors: {errors}")


if __name__ == "__main__":
    main()
