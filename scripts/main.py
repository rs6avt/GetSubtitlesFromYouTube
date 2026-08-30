import json
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

import streamlit as st
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

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

def get_id(input_text):
    match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", input_text)
    return match.group(1) if match else input_text.strip()

def format_time(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"[{minutes:02d}:{secs:02d}]"

def format_plain_text_with_breaks(transcript):
    lines = [item.text for item in transcript]
    return "\n".join(lines)

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

def render_video_header(video_id):
    meta = get_video_meta(video_id)
    with st.container(border=True):
        col_thumb, col_info = st.columns([1, 2], gap="large", vertical_alignment="center")
        with col_thumb:
            st.image(meta["thumbnail_url"], use_container_width=True)
        with col_info:
            if meta["title"]:
                st.subheader(meta["title"])
            else:
                st.subheader("タイトルを取得できませんでした")
            if meta["author"]:
                st.caption(meta["author"])
            st.link_button("YouTubeで開く", meta["watch_url"])

user_input = st.text_input("YouTubeのURLまたは動画IDを入力してください")

if st.button("字幕を取得"):
    if user_input:
        video_id = get_id(user_input)
        st.caption(f"抽出された動画ID: `{video_id}`")

        try:
            ytt = YouTubeTranscriptApi()
            transcript_list = ytt.list(video_id)
            transcript = transcript_list.find_transcript(['ja', 'ja-JP', 'en']).fetch()

            lines_with_time = [f"{format_time(item.start)} {item.text}" for item in transcript]
            formatted_text_with_time = "\n".join(lines_with_time)

            plain_text = format_plain_text_with_breaks(transcript)

            st.success("取得成功！")
            render_video_header(video_id)

            tab1, tab2 = st.tabs(["🕒 タイムスタンプ付き", "📝 テキストのみ（文章）"])

            with tab1:
                st.caption("※右上のアイコンからワンクリックでコピーできます")
                st.code(formatted_text_with_time, language="text", height=400, wrap_lines=True)
                st.download_button("タイムスタンプ付きファイルをダウンロード", formatted_text_with_time, f"{video_id}_timestamp.txt")

            with tab2:
                st.caption("※右上のアイコンからワンクリックでコピーできます")
                st.code(plain_text, language="text", height=400, wrap_lines=True)
                st.download_button("テキストファイルをダウンロード", plain_text, f"{video_id}_plain.txt")

        except TranscriptsDisabled:
            st.error("エラー: この動画は字幕機能が無効化されています。")
        except NoTranscriptFound:
            st.error("エラー: 指定された言語の字幕が見つかりませんでした。")
        except Exception as e:
            error_msg = str(e)
            if "blocking requests" in error_msg or "IP" in error_msg:
                st.error("エラー: YouTube側からアクセス制限（IPブロック）を受けています。時間を置いて再試行するか、別の動画でお試しください。")
            else:
                st.error(f"エラー詳細: {error_msg}")
    else:
        st.warning("入力してください。")