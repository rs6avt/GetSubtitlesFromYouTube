import json
import os
import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import streamlit as st
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache" / "transcripts"
VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")

st.title("YouTube 字幕取得ツール")

st.markdown(
    """
    <style>
    [data-testid="stCode"] pre,
    [data-testid="stCode"] code {
        white-space: pre-wrap !important;
        overflow-wrap: anywhere !important;
        word-break: break-word !important;
        overflow-x: hidden !important;
    }
    [data-testid="stImage"] img {
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_dotenv_file():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def webshare_credentials():
    username = os.environ.get("WEBSHARE_USERNAME", "").strip()
    password = os.environ.get("WEBSHARE_PASSWORD", "").strip()
    if username and password:
        return username, password
    try:
        username = str(st.secrets.get("WEBSHARE_USERNAME", "")).strip()
        password = str(st.secrets.get("WEBSHARE_PASSWORD", "")).strip()
    except Exception:
        username, password = "", ""
    return username, password


def build_transcript_client():
    username, password = webshare_credentials()
    if not username or not password:
        raise RuntimeError(
            "Webshareの認証情報がありません。"
            ".streamlit/secrets.toml か Streamlit Cloud の Secrets、"
            "または .env に WEBSHARE_USERNAME と WEBSHARE_PASSWORD を設定してください。"
        )
    return YouTubeTranscriptApi(
        proxy_config=WebshareProxyConfig(
            proxy_username=username,
            proxy_password=password,
        )
    )


def get_id(input_text):
    match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", input_text)
    return match.group(1) if match else input_text.strip()


def cache_path(video_id):
    return CACHE_DIR / f"{video_id}.json"


def load_disk_cache(video_id):
    if not VIDEO_ID_PATTERN.match(video_id):
        return None
    path = cache_path(video_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("transcript"):
        return None
    return data


def save_disk_cache(video_id, payload):
    if not VIDEO_ID_PATTERN.match(video_id):
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path(video_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def format_time(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"[{minutes:02d}:{secs:02d}]"


def format_text_with_time(transcript):
    return "\n".join(f"{format_time(item['start'])} {item['text']}" for item in transcript)


def format_plain_text_with_breaks(transcript):
    return "\n".join(item["text"] for item in transcript)


def get_video_meta(video_id):
    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    oembed_url = f"https://www.youtube.com/oembed?url={watch_url}&format=json"
    title = ""
    author = ""
    try:
        req = Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        title = data.get("title") or ""
        author = data.get("author_name") or ""
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        pass
    return {
        "title": title,
        "author": author,
        "thumbnail_url": thumbnail_url,
        "watch_url": watch_url,
    }


def fetch_from_youtube(video_id):
    ytt = build_transcript_client()
    transcript_list = ytt.list(video_id)
    transcript = transcript_list.find_transcript(["ja", "ja-JP", "en"]).fetch()
    items = [{"start": item.start, "text": item.text} for item in transcript]
    return {
        "video_id": video_id,
        "transcript": items,
        "meta": get_video_meta(video_id),
    }


def youtube_error_message(exc):
    if isinstance(exc, TranscriptsDisabled):
        return "エラー: この動画は字幕機能が無効化されています。"
    if isinstance(exc, NoTranscriptFound):
        return "エラー: 指定された言語の字幕が見つかりませんでした。"
    error_msg = str(exc)
    if "blocking requests" in error_msg or "IP" in error_msg:
        return "エラー: YouTube側からアクセス制限（IPブロック）を受けています。時間を置いて再試行するか、別の動画でお試しください。"
    return f"エラー詳細: {error_msg}"


def init_session_state():
    if "result" not in st.session_state:
        st.session_state.result = None
    if "error" not in st.session_state:
        st.session_state.error = None
    if "from_cache" not in st.session_state:
        st.session_state.from_cache = False
    if "cache_fallback" not in st.session_state:
        st.session_state.cache_fallback = False


def apply_cached_result(video_id, cached, fallback=False):
    cached["video_id"] = video_id
    st.session_state.result = cached
    st.session_state.from_cache = True
    st.session_state.cache_fallback = fallback
    if not fallback:
        st.session_state.error = None


def render_video_header(meta):
    with st.container(border=True):
        col_thumb, col_info = st.columns([1, 2], gap="large", vertical_alignment="center")
        with col_thumb:
            st.image(meta["thumbnail_url"], use_container_width=True)
        with col_info:
            if meta.get("title"):
                st.subheader(meta["title"])
            else:
                st.subheader("タイトルを取得できませんでした")
            if meta.get("author"):
                st.caption(meta["author"])
            st.link_button("YouTubeで開く", meta["watch_url"])


def render_result(result, from_cache, cache_fallback=False):
    video_id = result["video_id"]
    transcript = result["transcript"]
    formatted_text_with_time = format_text_with_time(transcript)
    plain_text = format_plain_text_with_breaks(transcript)

    if cache_fallback:
        if st.session_state.error:
            st.error(st.session_state.error)
        st.warning("YouTubeからの再取得に失敗したため、前回のキャッシュを表示しています。")
    elif from_cache:
        st.success("キャッシュから表示しています（YouTubeにはアクセスしていません）")
    else:
        st.success("取得成功！")

    st.caption(f"抽出された動画ID: `{video_id}`")
    render_video_header(result["meta"])

    tab1, tab2 = st.tabs(["🕒 タイムスタンプ付き", "📝 テキストのみ（文章）"])

    with tab1:
        st.caption("※右上のアイコンからワンクリックでコピーできます")
        st.code(formatted_text_with_time, language="text", height=400, wrap_lines=True)
        st.download_button(
            "タイムスタンプ付きファイルをダウンロード",
            formatted_text_with_time,
            f"{video_id}_timestamp.txt",
        )

    with tab2:
        st.caption("※右上のアイコンからワンクリックでコピーできます")
        st.code(plain_text, language="text", height=400, wrap_lines=True)
        st.download_button(
            "テキストファイルをダウンロード",
            plain_text,
            f"{video_id}_plain.txt",
        )


load_dotenv_file()
init_session_state()

user_input = st.text_input("YouTubeのURLまたは動画IDを入力してください")
skip_cache = st.checkbox("キャッシュを使わず再取得する")

if st.button("字幕を取得"):
    if not user_input:
        st.session_state.result = None
        st.session_state.from_cache = False
        st.session_state.cache_fallback = False
        st.session_state.error = "入力してください。"
    else:
        video_id = get_id(user_input)
        cached = None if skip_cache else load_disk_cache(video_id)
        if cached:
            apply_cached_result(video_id, cached)
        else:
            try:
                payload = fetch_from_youtube(video_id)
                save_disk_cache(video_id, payload)
                st.session_state.result = payload
                st.session_state.from_cache = False
                st.session_state.cache_fallback = False
                st.session_state.error = None
            except Exception as exc:
                fallback = load_disk_cache(video_id)
                if fallback:
                    apply_cached_result(video_id, fallback, fallback=True)
                    st.session_state.error = youtube_error_message(exc)
                else:
                    st.session_state.result = None
                    st.session_state.from_cache = False
                    st.session_state.cache_fallback = False
                    st.session_state.error = youtube_error_message(exc)

if st.session_state.error and not st.session_state.cache_fallback:
    if st.session_state.error == "入力してください。":
        st.warning(st.session_state.error)
    else:
        st.error(st.session_state.error)

if st.session_state.result:
    render_result(
        st.session_state.result,
        st.session_state.from_cache,
        cache_fallback=st.session_state.cache_fallback,
    )
