#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import arxiv
import requests
import os
import sys
import time
import argparse
import yaml
import logging
import json
from pathlib import Path
from urllib.parse import urlparse
from openai import OpenAI

# 追加モジュールをインポート
from pdf_processor import extract_text_from_pdf
from ai_summarizer import generate_summary

def load_config():
    """
    設定ファイルを読み込む
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def setup_directories():
    """
    必要なディレクトリを作成
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = {
        'dl': os.path.join(base_dir, 'dl'),
        'text': os.path.join(base_dir, 'text'),
        'summary': os.path.join(base_dir, 'summary'),
        'processed': os.path.join(base_dir, 'processed'),
        'logs': os.path.join(base_dir, 'logs')
    }
    
    for dir_name, dir_path in dirs.items():
        os.makedirs(dir_path, exist_ok=True)
    
    return dirs

def extract_arxiv_id(paper):
    """
    論文オブジェクトからarXiv IDを抽出
    
    Args:
        paper (arxiv.Result): 論文情報
        
    Returns:
        str: arXiv ID
    """
    pdf_url = paper.pdf_url
    parsed_url = urlparse(pdf_url)
    path_parts = parsed_url.path.split('/')
    arxiv_id = path_parts[-1]
    if arxiv_id.endswith('.pdf'):
        arxiv_id = arxiv_id[:-4]
    return arxiv_id

def search_arxiv(keywords, max_results=100, use_or=False, since_timestamp=None, last_paper_id=None):
    """
    arXivで指定されたキーワードを使用して論文を検索します。
    
    Args:
        keywords (list): 検索キーワードのリスト
        max_results (int): 取得する最大論文数
        use_or (bool): キーワードをORで結合するかどうか
        since_timestamp (str, optional): 指定したタイムスタンプ以降の論文のみを検索
        last_paper_id (str, optional): 指定したID以降の論文のみを検索
    
    Returns:
        list: 検索結果の論文リスト
    """
    logging.info(f"キーワード '{' '.join(keywords)}' でarXivを検索中...")
    
    # 検索クエリを作成（キーワードをスペースで結合）
    query = ' '.join(keywords)
    
    # タイムスタンプフィルタを追加
    if since_timestamp:
        date_filter = f" submittedDate:[{since_timestamp} TO *]"
        query += date_filter
        logging.info(f"タイムスタンプフィルタを適用: {since_timestamp} 以降")
        logging.info(f"最終的な検索クエリ: {query}")
    
    # arXivクライアントを作成
    client = arxiv.Client(
        page_size=100,  # 一度に取得する論文数を増やす
        delay_seconds=1.0,  # リクエスト間の待機時間を1秒に短縮
        num_retries=3  # リトライ回数
    )
    
    # デフォルトのタイムスタンプフィルタ（30日前から）
    if not since_timestamp:
        from datetime import datetime, timedelta
        default_since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        query = f"{query} submittedDate:[{default_since} TO *]"
    logging.info(f"検索クエリ: {query}")
    
    # 検索オブジェクトを作成
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    # 結果を取得
    results = list(client.results(search))
    
    logging.info(f"{len(results)}件の論文が見つかりました。")
    
    # デバッグ出力を追加
    for paper in results:
        paper_id = extract_arxiv_id(paper)
        logging.info(f"検索結果:")
        logging.info(f"  - ID: {paper_id}")
        logging.info(f"  - タイトル: {paper.title}")
        logging.info(f"  - 投稿日: {paper.published}")
        logging.info(f"  - 最終更新日: {paper.updated}")
        logging.info("---")
    
    return results

def download_pdf(paper, download_dir, force_download=False):
    """
    論文のPDFをダウンロードします。
    
    Args:
        paper (arxiv.Result): 論文情報
        download_dir (str): ダウンロード先ディレクトリ
        force_download (bool): 既存のファイルを上書きするかどうか
    
    Returns:
        tuple: (成功したかどうか, ダウンロードパス, arXiv ID)
    """
    # PDFのURLを取得
    pdf_url = paper.pdf_url
    
    # ファイル名を作成（arXiv IDを使用）
    parsed_url = urlparse(pdf_url)
    path_parts = parsed_url.path.split('/')
    arxiv_id = path_parts[-1]
    if not arxiv_id.endswith('.pdf'):
        arxiv_id = f"{arxiv_id}.pdf"
    
    # arXiv IDから拡張子を除去（処理済みチェック用）
    arxiv_id_without_ext = os.path.splitext(arxiv_id)[0]
    
    # ダウンロード先のパスを作成
    download_path = os.path.join(download_dir, arxiv_id)
    
    # 既にファイルが存在する場合はスキップ（force_downloadがFalseの場合）
    if os.path.exists(download_path) and not force_download:
        logging.info(f"ファイル {arxiv_id} は既に存在します。スキップします。")
        return True, download_path, arxiv_id_without_ext
    
    try:
        # PDFをダウンロード
        logging.info(f"ダウンロード中: {paper.title} ({arxiv_id})")
        
        # arXivサーバーに負荷をかけないよう、ダウンロード前に待機
        time.sleep(5)  # 5秒待機
        
        response = requests.get(pdf_url)
        response.raise_for_status()
        
        # ファイルに保存
        with open(download_path, 'wb') as f:
            f.write(response.content)
        
        logging.info(f"ダウンロード完了: {download_path}")
        
        # ダウンロード後も少し待機
        time.sleep(2)  # 2秒待機
        
        return True, download_path, arxiv_id_without_ext
    
    except Exception as e:
        logging.error(f"ダウンロード失敗: {arxiv_id} - エラー: {str(e)}")
        return False, None, arxiv_id_without_ext

def process_paper(paper, dirs, openai_client, config, force_process=False, skip_twitter=False):
    """
    論文を処理する（ダウンロード、テキスト抽出、要約生成）
    
    Args:
        paper (arxiv.Result): 論文情報
        dirs (dict): ディレクトリパス
        openai_client (OpenAI): OpenAIクライアント
        config (dict): 設定情報
        force_process (bool): 処理済みの論文も強制的に処理するかどうか
        skip_twitter (bool): Twitter投稿をスキップするかどうか
    
    Returns:
        bool: 処理が成功したかどうか
    """
    # 1. PDFをダウンロード
    logging.info(f"論文 '{paper.title}' のPDFをダウンロード中...")
    start_time = time.time()
    success, pdf_path, arxiv_id = download_pdf(paper, dirs['dl'])
    end_time = time.time()
    if not success:
        logging.error(f"論文 '{paper.title}' のPDFダウンロードに失敗しました")
        return False
    logging.info(f"論文 '{paper.title}' のPDFダウンロードが完了しました（所要時間: {end_time - start_time:.2f}秒）")
    
    # 2. PDFからテキストを抽出
    logging.info(f"論文 '{paper.title}' のテキスト抽出中...")
    start_time = time.time()
    text_path = extract_text_from_pdf(pdf_path, dirs['text'])
    end_time = time.time()
    if not text_path:
        logging.error(f"論文 '{paper.title}' のテキスト抽出に失敗しました")
        return False
    logging.info(f"論文 '{paper.title}' のテキスト抽出が完了しました（所要時間: {end_time - start_time:.2f}秒）")
    
    # 3. テキストを読み込み
    with open(text_path, 'r', encoding='utf-8') as f:
        paper_text = f.read()

    # 4. 要約を生成
    logging.info(f"論文 '{paper.title}' の要約を生成中...")
    start_time = time.time()
    summary = generate_summary(
        openai_client,
        paper_text,
        config['prompt']['template'],
        dirs['summary'],
        paper.title,
        arxiv_id
    )
    end_time = time.time()
    if not summary:
        logging.error(f"論文 '{paper.title}' の要約生成に失敗しました")
        return False
    
    logging.info(f"論文 '{paper.title}' の要約生成が完了しました（所要時間: {end_time - start_time:.2f}秒）")
    
    # arXiv IDを追加
    summary['arxiv_id'] = arxiv_id
    
    # 投稿テキストを生成
    if 'post_text' not in summary:
        post_text = summary['summary']
        
        # arXivのURLを追加
        if arxiv_id:
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
            # URLを追加しても280文字以内に収まるか確認
            if len(post_text) + len(arxiv_url) + 2 <= 280:  # 改行分の2文字を追加
                post_text += f"\n\n{arxiv_url}"
        
        summary['post_text'] = post_text
    
    # サマリーファイルを生成
    summary_path = os.path.join(dirs['summary'], f"{arxiv_id}_summary.json")
    summary_data = {
        "title": paper.title,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary['summary'],
        "post_text": summary['post_text'],
        "arxiv_id": arxiv_id
    }
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    # ログファイルを生成
    log_path = os.path.join(dirs['logs'], f"{arxiv_id}_log.json")
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    return True
