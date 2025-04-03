#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import time
import logging
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import arxiv

# 追加モジュールをインポート
from arxiv_downloader import search_arxiv, process_paper, OpenAI, setup_directories, extract_arxiv_id
from web_generator import generate_webpage

def setup_logging():
    """ロギングを設定"""
    # ログディレクトリを作成
    log_dir = "./logs"
    os.makedirs(log_dir, exist_ok=True)

    # タイムスタンプ付きのログファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = os.path.join(log_dir, f"{timestamp}.log")

    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file

def load_config():
    """設定ファイルを読み込む"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"設定ファイルの読み込みエラー: {str(e)}")
        sys.exit(1)

def load_cache(cache_dir, cache_type):
    """キャッシュを読み込む"""
    cache_file = os.path.join(cache_dir, f"{cache_type}_cache.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"キャッシュファイルの読み込みエラー: {str(e)}")
    return {}

def save_cache(cache_dir, cache_type, cache_data):
    """キャッシュを保存"""
    cache_file = os.path.join(cache_dir, f"{cache_type}_cache.json")
    try:
        # arxiv.Resultオブジェクトを辞書に変換
        if cache_type == "search":
            serializable_data = []
            for paper in cache_data:
                if isinstance(paper, arxiv.Result):
                    paper_dict = {
                        'id': extract_arxiv_id(paper),
                        'title': paper.title,
                        'summary': paper.summary,
                        'pdf_url': paper.pdf_url,
                        'published': paper.published.isoformat(),
                        'updated': paper.updated.isoformat()
                    }
                else:
                    paper_dict = paper
                serializable_data.append(paper_dict)
            cache_data = serializable_data

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logging.error(f"キャッシュファイルの保存エラー: {str(e)}")

def get_cache_key(data_type, **kwargs):
    """キャッシュキーを生成"""
    if data_type == "search":
        # 検索キーワードとタイムスタンプからキーを生成
        keywords_str = "_".join(sorted(kwargs.get('keywords', [])))
        timestamp = kwargs.get('timestamp', '')
        return f"search_{keywords_str}_{timestamp}"
    elif data_type == "paper":
        # 論文IDからキーを生成
        return f"paper_{kwargs.get('paper_id', '')}"
    return None

def main():
    """メイン関数"""
    # コマンドライン引数のパーサーを設定
    parser = argparse.ArgumentParser(
        description='指定したキーワードでarXivを検索し、論文をダウンロード・要約してHTMLページを生成します。'
    )
    parser.add_argument(
        'keywords',
        nargs='+',
        help='検索キーワード（複数指定可能）。例: "LLM" "RAG" "Transformer"'
    )
    parser.add_argument(
        'output_dir',
        help='HTMLファイルの出力先ディレクトリ。生成されたHTMLファイルやアセットはこのディレクトリに保存されます。'
        '例: /var/www/html/arXiv'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='キャッシュを無視して強制的に再処理する'
    )

    # 引数を解析
    args = parser.parse_args()

    # ロギングを設定
    log_file = setup_logging()
    logging.info(f"ログファイル: {log_file}")

    # 設定を読み込む
    config = load_config()
    logging.info("設定ファイルを読み込みました")

    # 出力ディレクトリを作成
    os.makedirs(args.output_dir, exist_ok=True)
    logging.info(f"出力ディレクトリを確認: {args.output_dir}")

    # キャッシュディレクトリを設定
    cache_dir = "./cache"
    os.makedirs(cache_dir, exist_ok=True)

    # キャッシュを読み込む
    search_cache = load_cache(cache_dir, "search")
    paper_cache = load_cache(cache_dir, "paper")

    # 必要なディレクトリを設定
    dirs = setup_directories()

    # OpenAIクライアントを初期化
    openai_client = OpenAI(api_key=config['openai']['api_key'])

    # 検索期間を設定
    days_back = config.get('search', {}).get('days_back', 30)
    since_date = datetime.utcnow() - timedelta(days=days_back)
    since_timestamp = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # キャッシュキーを生成
    search_key = get_cache_key("search", keywords=args.keywords, timestamp=since_timestamp)

    # 検索結果を取得（キャッシュがある場合はそれを使用）
    if not args.force and search_key in search_cache:
        logging.info("検索キャッシュを使用します")
        results = []
        for paper_dict in search_cache[search_key]:
            # 辞書からarxiv.Resultオブジェクトを再構築
            paper = arxiv.Result(
                entry_id=f"http://arxiv.org/abs/{paper_dict['id']}",
                updated=datetime.fromisoformat(paper_dict['updated']),
                published=datetime.fromisoformat(paper_dict['published']),
                title=paper_dict['title'],
                authors=[],  # 必要に応じて著者情報を追加
                summary=paper_dict['summary'],
                comment="",
                journal_ref="",
                doi="",
                primary_category="",
                categories=[],
                links=[{"title": "pdf", "href": paper_dict['pdf_url'], "rel": "related", "type": "application/pdf"}],
                pdf_url=paper_dict['pdf_url']
            )
            results.append(paper)
    else:
        logging.info(f"キーワード '{' '.join(args.keywords)}' でarXivを検索中...")
        results = search_arxiv(
            keywords=args.keywords,
            max_results=100,
            since_timestamp=since_timestamp
        )
        # 検索結果をキャッシュに保存
        save_cache(cache_dir, "search", results)

    # 各論文を処理
    processed_papers = []
    for paper in results:
        paper_id = extract_arxiv_id(paper)
        paper_key = get_cache_key("paper", paper_id=paper_id)

        # サマリーファイルが存在するか確認
        summary_file = os.path.join(dirs['summary'], f"{paper_id}_summary.json")
        if os.path.exists(summary_file) and not args.force:
            logging.info(f"論文キャッシュを使用: {paper_id}")
            continue

        # 論文を処理
        logging.info(f"論文を処理中: {paper_id}")
        success = process_paper(
            paper,
            dirs,
            openai_client,
            config,
            force_process=True,  # 強制的に処理を実行
            skip_twitter=True  # Twitter投稿は常にスキップ
        )
        if success:
            paper_data = {
                'id': paper_id,
                'title': paper.title,
                'summary': paper.summary,
                'url': paper.pdf_url
            }
            paper_cache[paper_key] = paper_data
            processed_papers.append(paper_data)
            save_cache(cache_dir, "paper", paper_cache)

    # HTMLページを生成
    logging.info(f"HTMLページを生成: {args.output_dir}")
    generate_webpage(dirs['summary'], args.output_dir)

    logging.info("処理が完了しました")

if __name__ == "__main__":
    main()