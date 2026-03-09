import os
import yt_dlp
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload

CHANNEL_URL = "https://www.youtube.com/@aetherautomation/videos"
CHANNEL_ID = "UCD8b2ZmXG1xI9kyKZYAu-UQ"  # extraído del log
DRIVE_FOLDER_ID = "1NqifLrBXJ89eWtzuAW166X7BoRLm2YED"

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]

DOWNLOAD_FOLDER = "downloads"
ARCHIVE_FILE = "download_archive.txt"

# ── Google Drive auth ──────────────────────────────────────────────────────────
creds = Credentials(
    None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)
drive = build("drive", "v3", credentials=creds)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ── Leer el archive para saber qué ya se descargó ─────────────────────────────
def load_archive():
    downloaded = set()
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    downloaded.add(parts[1])  # formato: "youtube VIDEO_ID"
    return downloaded

def mark_downloaded(video_id):
    with open(ARCHIVE_FILE, "a") as f:
        f.write(f"youtube {video_id}\n")

# ── Obtener videos del canal via YouTube Data API (sin bot-check) ─────────────
def get_channel_videos(api_key, channel_id, max_results=50):
    """Devuelve lista de (video_id, title) del canal, del más reciente al más antiguo."""
    youtube = build("youtube", "v3", developerKey=api_key)
    videos = []
    next_page = None

    while True:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": 50,
            "order": "date",
            "type": "video",
        }
        if next_page:
            params["pageToken"] = next_page

        response = youtube.search().list(**params).execute()

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            videos.append((video_id, title))

        next_page = response.get("nextPageToken")
        if not next_page or len(videos) >= max_results:
            break

    return videos

# ── yt-dlp config usando cliente android (no requiere cookies) ────────────────
ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "merge_output_format": "mp4",
    "outtmpl": f"{DOWNLOAD_FOLDER}/%(title)s [%(id)s].%(ext)s",
    # Lee las cookies directamente del navegador instalado en esta máquina.
    # Cambiá "chrome" por "firefox" o "edge" si usás otro navegador.
    # Las cookies se renuevan solas cuando usás YouTube normalmente.
    "cookiesfrombrowser": ("chrome",),
    "quiet": False,
    "no_warnings": False,
}

# ── Main ──────────────────────────────────────────────────────────────────────
print("Checking channel for new videos via YouTube Data API...")

downloaded = load_archive()
videos = get_channel_videos(YOUTUBE_API_KEY, CHANNEL_ID)
new_videos = [(vid, title) for vid, title in videos if vid not in downloaded]

if not new_videos:
    print("No new videos found.")
else:
    print(f"Found {len(new_videos)} new video(s) to download.")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for video_id, title in new_videos:
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"Downloading: {title} ({video_id})")
            try:
                ydl.download([url])
                mark_downloaded(video_id)
            except Exception as e:
                print(f"ERROR downloading {video_id}: {e}")
                continue

# ── Upload to Google Drive ────────────────────────────────────────────────────
uploaded_count = 0
for file in os.listdir(DOWNLOAD_FOLDER):
    if file.endswith(".mp4"):
        filepath = os.path.join(DOWNLOAD_FOLDER, file)
        print(f"Uploading: {file}")
        try:
            media = MediaFileUpload(filepath, resumable=True)
            drive.files().create(
                body={
                    "name": file,
                    "parents": [DRIVE_FOLDER_ID],
                },
                media_body=media,
            ).execute()
            os.remove(filepath)
            uploaded_count += 1
        except Exception as e:
            print(f"ERROR uploading {file}: {e}")

print(f"Sync complete. {uploaded_count} video(s) uploaded to Google Drive.")
