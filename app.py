import streamlit as st
import yt_dlp
from pytube import Search
import os
from supabase import create_client, Client, ClientOptions
from urllib.parse import quote, urlparse, parse_qs
import streamlit.components.v1 as components

SUPABASE_URL = "https://iazpdrquqqxuanvonfjk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlhenBkcnF1cXF4dWFudm9uZmprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzYzOTIsImV4cCI6MjA1Nzg1MjM5Mn0.vMyQVNlIjiZ3XpmhuL8QP07mq3FTy2C--KQ2j5EMTP4"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(auto_refresh_token=True))

st.set_page_config(page_title="🎵 Tune In", layout="centered")
st.title("🎶 YouTube Audio Downloader with Cloud Playlist")

components.html("""
    <script>
        const params = new URLSearchParams(window.location.hash.substring(1));
        const token = params.get("access_token");
        if (token) {
            window.location.href = window.location.pathname + "?access_token=" + token;
        }
    </script>
""", height=0)

if "user" not in st.session_state:
    st.session_state.user = None

# ---------- Authentication Flow ----------
redirect_url = "https://tune-in-uhkf4oh9qerz9b8dv3kjwj.streamlit.app"  # Change to your Streamlit Cloud URL after deployment
login_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"

query_params = st.query_params
print(query_params)

if 'access_token' in query_params and not st.session_state.user:
    print("Hi")
    access_token = query_params['access_token']
    user_info = supabase.auth.get_user(access_token)
    if user_info and user_info.user:
        st.session_state.user = {
            "id": user_info.user.id,
            "email": user_info.user.email,
            "token": access_token
        }
        st.success(f"✅ Logged in as {st.session_state.user['email']}")

# ---------- Login / Logout Buttons ----------
if st.session_state.user:
    print("Logged in")
    st.success(f"✅ Logged in as {st.session_state.user['email']}")
    if st.button("🔒 Logout"):
        st.session_state.user = None
        st.experimental_rerun()
else:
    print("Not logged in")
    st.markdown(f"[🟢 Login with Google]({login_url})", unsafe_allow_html=True)

# ---------- Utility Functions ----------
def sanitize_filename(title):
    return title.replace('|', '').replace('｜', '').replace(',', '').strip()

def generate_public_url(bucket_name, file_name):
    encoded_file_name = quote(file_name, safe='()')
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{encoded_file_name}"

def upload_to_supabase_storage(file_path, storage_filename):
    bucket_name = 'songs'
    with open(file_path, 'rb') as f:
        supabase.storage.from_(bucket_name).update(storage_filename, f, {"content-type": "audio/mpeg"})
    return generate_public_url(bucket_name, storage_filename)

def save_song_metadata(user_id, title, public_url):
    supabase.table("songs").insert({"user_id": user_id, "title": title, "file_path": public_url}).execute()

def fetch_user_songs(user_id):
    response = supabase.table("songs").select("title, file_path").eq("user_id", user_id).execute()
    return response.data if response.data else []

def search_youtube(query):
    search = Search(query)
    if search.results:
        return search.results[0].watch_url, search.results[0].title
    return None, None

def download_audio(video_url, title, output_folder="temp_download"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'ffmpeg_location': r'D:/Downloads/ffmpeg-2025-03-17-git-5b9356f18e-full_build/ffmpeg-2025-03-17-git-5b9356f18e-full_build/bin',  # Update your path
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        local_file = ydl.prepare_filename(info_dict).replace(".webm", ".mp3").replace(".m4a", ".mp3")
    return local_file

# ---------- Search and Download Section ----------
query = st.text_input("🔎 Enter song name to search and download audio:")
if st.button("Search & Download"):
    if query:
        video_url, video_title = search_youtube(query)
        if video_url:
            st.write(f"### 🎬 Found: [{video_title}]({video_url})")
            st.video(video_url)

            local_file = download_audio(video_url, video_title)
            sanitized_title = sanitize_filename(video_title)
            public_url = upload_to_supabase_storage(local_file, sanitized_title + ".mp3")
            os.remove(local_file)

            st.audio(public_url, format="audio/mp3")
            st.markdown(f"[Download Audio]({public_url})", unsafe_allow_html=True)

            if st.session_state.user:
                save_song_metadata(st.session_state.user['id'], video_title, public_url)
                st.success("✅ Audio saved to your playlist!")
            else:
                st.info("Login to save the song to your playlist.")
        else:
            st.error("No results found.")
    else:
        st.warning("Please enter a search query!")

# ---------- Playlist Section ----------
st.subheader("🎵 Your Playlist")
if st.session_state.user:
    playlist = fetch_user_songs(st.session_state.user['id'])
    if playlist:
        for song in playlist:
            st.write(f"🎧 {song['title']}")
            st.audio(song['file_path'], format="audio/mp3")
            st.markdown(f"[Download]({song['file_path']})", unsafe_allow_html=True)
    else:
        st.info("Your playlist is empty.")
else:
    st.info("Login to view your personal playlist.")
