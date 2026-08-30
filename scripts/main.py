import streamlit as st
import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

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
    # タイムスタンプを含めず、テキストのみを1行ずつ結合
    lines = [item.text for item in transcript]
    return "\n".join(lines)

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