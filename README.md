# YouTube 字幕取得ツール (YouTube Subtitle Extractor)

YouTube動画のURLまたは動画IDから、字幕データを自動抽出してテキスト・ファイル形式でダウンロードできるWebアプリケーションです。

## 🚀 主な機能

- **2種類の表示フォーマット:** タイムスタンプ付きテキスト / プレーンテキスト（文章のみ）の切り替え表示
- **ワンクリック操作:** 画面上のテキストコピー機能および `.txt` ファイルでのダウンロード機能
- **高速化・耐障害性:** ディスクキャッシュ機構による再リクエストの高速化とYouTube側の通信負荷軽減

## 🛠 使用技術

- **Language:** Python
- **Framework:** Streamlit
- **Library:** `youtube-transcript-api`
- **Deployment:** Streamlit Community Cloud

## 💡 アーキテクチャと工夫したポイント

### 1. キャッシュ機構（IPブロック・レートリミット対策）
クラウドサーバー（Streamlit Cloud等）からの連続アクセスによるYouTube側のIPブロック制限を考慮し、一度取得した字幕データはローカル/サーバーのディスク上（`.cache/transcripts/`）にJSON形式で保存されます。2回目以降の同一動画リクエストに対しては外部通信を発生させずに高速応答します。

### 2. 入力値バリデーションと安全性
正規表現パターン（11文字の動画ID判定）を用いた事前検証を行い、無効な文字列入力による不要なAPI通信やファイルシステム障害を抑止しています。

## 💻 ローカルでの実行手順

```bash
# 1. リポジトリのクローン
git clone [https://github.com/rs6avt/GetSubtitilesFromYouTube.git](https://github.com/rs6avt/GetSubtitilesFromYouTube.git)

# 2. 依存パッケージのインストール
pip install -r requirements.txt

# 3. アプリケーションの起動
streamlit.exe run main.py
```
