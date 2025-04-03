# ArXivPagestBot3

## Overview
ArXivPagestBot3 is a Python tool that automatically searches arXiv for papers based on specified keywords, downloads them, generates easy-to-understand summaries using OpenAI's API, and creates a web page to display these summaries. The summaries are written in a casual, friendly style aimed at making academic papers more accessible to a general audience.

## Installation
1. Clone the repository:
```bash
git clone https://github.com/daishir0/ArXivPagestBot3.git
cd ArXivPagestBot3
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Create a configuration file:
```bash
cp config.sample.yaml config.yaml
```

4. Edit `config.yaml` and add your OpenAI API key:
```yaml
openai:
  api_key: your-openai-api-key-here
```

## Usage
Run the script with search keywords and output directory:
```bash
python create_arXiv_page.py "keyword1" "keyword2" "/path/to/output/directory"
```

Examples:
```bash
# Search for a single keyword
python create_arXiv_page.py "WCAG" "/var/www/html/arXiv/wcag"

# Search for multiple keywords
python create_arXiv_page.py "LLM" "RAG" "/var/www/html/arXiv/llm_rag"
```

## Notes
- The tool requires an OpenAI API key for generating summaries
- Generated web pages include copy-to-clipboard functionality for easy sharing
- Summaries are cached to avoid unnecessary API calls
- The tool is designed to run on Linux systems

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---

# ArXivPagestBot3

## 概要
ArXivPagestBot3は、指定したキーワードでarXivの論文を検索し、ダウンロードして、OpenAIのAPIを使用して分かりやすい要約を生成し、それらをWebページとして表示するPythonツールです。要約は、学術論文を一般の方々にも親しみやすくするため、カジュアルでフレンドリーな文体で書かれています。

## インストール方法
1. レポジトリをクローン:
```bash
git clone https://github.com/daishir0/ArXivPagestBot3.git
cd ArXivPagestBot3
```

2. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```

3. 設定ファイルを作成:
```bash
cp config.sample.yaml config.yaml
```

4. `config.yaml`を編集してOpenAI APIキーを追加:
```yaml
openai:
  api_key: あなたのOpenAI-APIキーをここに入力
```

## 使い方
検索キーワードと出力ディレクトリを指定して実行:
```bash
python create_arXiv_page.py "キーワード1" "キーワード2" "/出力先/ディレクトリ"
```

例:
```bash
# 単一キーワードで検索
python create_arXiv_page.py "WCAG" "/var/www/html/arXiv/wcag"

# 複数キーワードで検索
python create_arXiv_page.py "LLM" "RAG" "/var/www/html/arXiv/llm_rag"
```

## 注意点
- 要約生成にはOpenAI APIキーが必要です
- 生成されるWebページには、クリップボードへのコピー機能が含まれています
- 要約はキャッシュされ、不要なAPI呼び出しを避けます
- このツールはLinuxシステムでの実行を想定しています

## ライセンス
このプロジェクトはMITライセンスの下でライセンスされています。詳細はLICENSEファイルを参照してください。