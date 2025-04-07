#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import glob
import time
import logging
from datetime import datetime
import shutil
from collections import defaultdict

def classify_logs_by_date(summary_dir, filter_keywords=None):
    """
    サマリーファイルを日付ごとに分類する
    
    Args:
        summary_dir (str): サマリーファイルのディレクトリ
        filter_keywords (list, optional): フィルタリングするキーワードのリスト
        
    Returns:
        defaultdict: 日付ごとの論文情報
    """
    date_logs = defaultdict(list)
    
    # サマリーファイルを検索
    summary_files = glob.glob(os.path.join(summary_dir, '*_summary.json'))
    if not summary_files:
        logging.warning(f"サマリーファイルが見つかりません: {summary_dir}")
        return date_logs
    
    logging.info(f"サマリーファイル数: {len(summary_files)}")
    
    for summary_file in summary_files:
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # タイムスタンプを解析
            timestamp = summary_data.get('timestamp')
            if timestamp:
                date = timestamp.split()[0]  # YYYY-MM-DD
                
                # キーワードフィルタリング
                if filter_keywords:
                    # サマリーデータにキーワード情報がある場合
                    paper_keywords = summary_data.get('keywords', '').lower()
                    paper_title = summary_data.get('title', '').lower()
                    paper_summary = summary_data.get('summary', '').lower()
                    
                    # いずれかのキーワードが含まれているか確認
                    match_found = False
                    for keyword in filter_keywords:
                        keyword = keyword.lower()
                        if (keyword in paper_keywords or
                            keyword in paper_title or
                            keyword in paper_summary):
                            match_found = True
                            break
                    
                    # マッチしない場合はスキップ
                    if not match_found:
                        continue
                
                # 論文情報を作成
                paper_info = {
                    'title': summary_data.get('title', 'Unknown'),
                    'timestamp': timestamp,
                    'formatted_date': datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y年%m月%d日 %H:%M"),
                    'arxiv_id': summary_data.get('arxiv_id'),
                    'summary': summary_data.get('summary', '要約情報がありません。'),
                    'keywords': summary_data.get('keywords', '')
                }
                date_logs[date].append(paper_info)
        except Exception as e:
            logging.error(f"サマリーファイル {summary_file} の解析エラー: {str(e)}")
    
    logging.info(f"分類された論文数: {sum(len(papers) for papers in date_logs.values())}")
    return date_logs

def generate_webpage(summary_dir, output_dir, current_only=False, current_date=None, verbose=False, filter_keywords=None):
    """Webページを生成する"""
    # 出力ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)
    
    # CSSとJavaScriptのディレクトリを作成
    css_dir = os.path.join(output_dir, 'css')
    js_dir = os.path.join(output_dir, 'js')
    os.makedirs(css_dir, exist_ok=True)
    os.makedirs(js_dir, exist_ok=True)
    
    # CSSファイルを作成
    css_content = """
    body {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        margin: 0;
        padding: 0;
    }
    .paper-card {
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .paper-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    .paper-title {
        color: #2c3e50;
        margin-bottom: 10px;
    }
    .summary-text {
        font-size: 1em;
        line-height: 1.8;
        color: #444;
        cursor: pointer;
        user-select: all;
    }
    .summary-text:hover {
        background-color: #f8f9fa;
    }
    .copy-success {
        background-color: #d4edda;
        transition: background-color 0.3s ease;
    }
    """
    
    with open(os.path.join(css_dir, 'custom.css'), 'w') as f:
        f.write(css_content)
    
    # JavaScriptファイルを作成
    js_content = """
    document.addEventListener('DOMContentLoaded', function() {
        // クリップボードにコピーする関数
        function copyToClipboard(text) {
            // テキストエリアを作成
            const textarea = document.createElement('textarea');
            textarea.value = text;
            
            // スタイルを設定して画面外に配置
            textarea.style.position = 'fixed';
            textarea.style.opacity = 0;
            document.body.appendChild(textarea);
            
            // テキストを選択してコピー
            textarea.select();
            let success = false;
            
            try {
                // execCommandを試す
                success = document.execCommand('copy');
            } catch (err) {
                console.error('コピーに失敗しました:', err);
            }
            
            // テキストエリアを削除
            document.body.removeChild(textarea);
            
            // 新しいClipboard APIも試す（execCommandが失敗した場合）
            if (!success && navigator.clipboard) {
                navigator.clipboard.writeText(text).catch(err => {
                    console.error('Clipboard APIでのコピーに失敗しました:', err);
                });
                success = true;
            }
            
            return success;
        }
        
        // モーダルを表示する関数
        function showCopyModal() {
            const copyModal = new bootstrap.Modal(document.getElementById('copyModal'));
            copyModal.show();
            
            // 2秒後に自動的に閉じる
            setTimeout(() => {
                copyModal.hide();
            }, 2000);
        }
        
        // 要約文のクリップボードコピー機能
        document.querySelectorAll('.summary-text').forEach(function(element) {
            element.addEventListener('click', function() {
                const text = this.textContent;
                const success = copyToClipboard(text);
                
                if (success) {
                    // コピー成功の視覚的フィードバック
                    this.classList.add('copy-success');
                    setTimeout(() => {
                        this.classList.remove('copy-success');
                    }, 1000);
                    
                    showCopyModal();
                } else {
                    console.error('要約文のコピーに失敗しました。');
                }
            });
        });
    });
    """
    
    with open(os.path.join(js_dir, 'custom.js'), 'w') as f:
        f.write(js_content)
    
    # サマリーファイルを日付ごとに分類
    date_logs = classify_logs_by_date(summary_dir, filter_keywords)
    
    # 日付でソート
    dates = sorted(date_logs.keys(), reverse=True)
    
    # 現在の日付のみを処理する場合
    if current_only and current_date:
        dates = [d for d in dates if d == current_date]
    
    # 各日付のページを生成
    for date in dates:
        papers = date_logs[date]
        year, month, _ = date.split('-')
        
        # 日別ページを生成
        generate_daily_page(date, papers, output_dir)
        
        # 月別インデックスを生成
        generate_monthly_index(year, month, date_logs, output_dir)
        
        # 年別インデックスを生成
        generate_yearly_index(year, date_logs, output_dir)
    
    # メインインデックスを生成
    generate_main_index(date_logs, output_dir)

def generate_daily_page(date, papers, output_dir):
    """日付ごとのページを生成する"""
    # 年月日を分解
    year, month, day = date.split('-')
    
    # ナビゲーションリンクを作成
    nav_html = f"""
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="index.html">ホーム</a></li>
        <li class="breadcrumb-item"><a href="{year}.html">{year}年</a></li>
        <li class="breadcrumb-item"><a href="{year}-{month}.html">{year}年{month}月</a></li>
        <li class="breadcrumb-item active" aria-current="page">{year}年{month}月{day}日</li>
      </ol>
    </nav>
    """
    
    # HTMLを生成
    html = generate_html_template(f"{year}年{month}月{day}日の論文要約", papers, nav_html)
    
    # ファイルに保存
    file_path = os.path.join(output_dir, f"{date}.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_monthly_index(year, month, date_logs, output_dir):
    """月別インデックスページを生成する"""
    # 月内の日付リンクリスト
    date_links = []
    for date in sorted([d for d in date_logs.keys() if d.startswith(f"{year}-{month}")], reverse=True):
        y, m, d = date.split('-')
        date_links.append(f'<li><a href="{date}.html">{y}年{m}月{d}日</a> ({len(date_logs[date])}件)</li>')
    
    # ナビゲーションリンクを作成
    nav_html = f"""
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="index.html">ホーム</a></li>
        <li class="breadcrumb-item"><a href="{year}.html">{year}年</a></li>
        <li class="breadcrumb-item active" aria-current="page">{year}年{month}月</li>
      </ol>
    </nav>
    """
    
    # HTMLを生成
    html = f"""<!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{year}年{month}月の論文要約</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="css/custom.css">
    </head>
    <body>
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center text-dark text-decoration-none">
                    <span class="fs-4">{year}年{month}月の論文要約</span>
                    <span class="ms-auto">最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</span>
                </div>
            </header>
            
            {nav_html}
            
            <div class="alert alert-info">
                <p><strong>C(・ω・ )つ みんなー！</strong> {year}年{month}月の論文要約一覧だよ！</p>
            </div>
            
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            日別アーカイブ
                        </div>
                        <div class="card-body">
                            <ul>
                                {"".join(date_links)}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script src="js/custom.js"></script>
    </body>
    </html>
    """
    
    # ファイルに保存
    file_path = os.path.join(output_dir, f"{year}-{month}.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_yearly_index(year, date_logs, output_dir):
    """年別インデックスページを生成する"""
    # 年内の月を抽出
    months = sorted(set([d.split('-')[1] for d in date_logs.keys() if d.startswith(f"{year}-")]), reverse=True)
    
    # 月別リンクリスト
    month_links = []
    for month in months:
        # 月内の論文数をカウント
        month_papers_count = sum(len(date_logs[d]) for d in date_logs.keys() if d.startswith(f"{year}-{month}"))
        month_links.append(f'<li><a href="{year}-{month}.html">{year}年{month}月</a> ({month_papers_count}件)</li>')
    
    # ナビゲーションリンクを作成
    nav_html = f"""
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="index.html">ホーム</a></li>
        <li class="breadcrumb-item active" aria-current="page">{year}年</li>
      </ol>
    </nav>
    """
    
    # HTMLを生成
    html = f"""<!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{year}年の論文要約</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="css/custom.css">
    </head>
    <body>
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center text-dark text-decoration-none">
                    <span class="fs-4">{year}年の論文要約</span>
                    <span class="ms-auto">最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</span>
                </div>
            </header>
            
            {nav_html}
            
            <div class="alert alert-info">
                <p><strong>C(・ω・ )つ みんなー！</strong> {year}年の論文要約一覧だよ！</p>
            </div>
            
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            月別アーカイブ
                        </div>
                        <div class="card-body">
                            <ul>
                                {"".join(month_links)}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script src="js/custom.js"></script>
    </body>
    </html>
    """
    
    # ファイルに保存
    file_path = os.path.join(output_dir, f"{year}.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_main_index(date_logs, output_dir):
    """メインインデックスページを生成する"""
    # 最新の日付を取得
    latest_dates = sorted(date_logs.keys(), reverse=True)[:5]  # 最新5日分
    
    # 年のリストを作成
    years = sorted(set([d.split('-')[0] for d in date_logs.keys()]), reverse=True)
    
    # 最新の論文を取得
    latest_papers = []
    for date in latest_dates:
        latest_papers.extend(date_logs[date])
    
    # 最新10件に制限
    latest_papers = sorted(latest_papers, key=lambda x: x.get('timestamp', ''), reverse=True)[:10]
    
    # アーカイブリンクを作成
    archive_html = '<div class="card mt-4"><div class="card-header">アーカイブ</div><div class="card-body">'
    
    # 年別リンク
    for year in years:
        # 年内の論文数をカウント
        year_papers_count = sum(len(date_logs[d]) for d in date_logs.keys() if d.startswith(f"{year}-"))
        archive_html += f'<h5><a href="{year}.html">{year}年</a> ({year_papers_count}件)</h5>'
        
        # 月別リンク（最新の年のみ表示）
        if year == years[0]:
            archive_html += '<ul>'
            months = sorted(set([d.split('-')[1] for d in date_logs.keys() if d.startswith(f"{year}-")]), reverse=True)
            for month in months:
                # 月内の論文数をカウント
                month_papers_count = sum(len(date_logs[d]) for d in date_logs.keys() if d.startswith(f"{year}-{month}"))
                archive_html += f'<li><a href="{year}-{month}.html">{year}年{month}月</a> ({month_papers_count}件)</li>'
            archive_html += '</ul>'
    
    archive_html += '</div></div>'
    
    # HTMLを生成
    html = generate_html_template("arXiv論文要約", latest_papers, "", archive_html)
    
    # ファイルに保存
    file_path = os.path.join(output_dir, "index.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html)

def generate_html_template(title, papers, navigation="", archive=""):
    """基本的なHTMLテンプレートを生成する"""
    html = f"""<!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="css/custom.css">
    </head>
    <body>
        <!-- コピー成功モーダル -->
        <div class="modal fade" id="copyModal" tabindex="-1" aria-labelledby="copyModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-sm modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-body text-center py-4">
                        <h5 class="mb-0">コピーしました</h5>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="container py-4">
            <header class="pb-3 mb-4 border-bottom">
                <div class="d-flex align-items-center text-dark text-decoration-none">
                    <span class="fs-4">{title}</span>
                    <span class="ms-auto">最終更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</span>
                </div>
            </header>
            
            {navigation}
            
            <div class="alert alert-info">
                <p><strong>C(・ω・ )つ みんなー！</strong> 最新の論文要約をお届けします！</p>
            </div>
            
            <div class="row">
                {generate_paper_cards(papers)}
            </div>
            
            {archive}
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
        <script src="js/custom.js"></script>
    </body>
    </html>
    """
    
    return html

def generate_paper_cards(papers):
    """論文カードのHTMLを生成する"""
    cards_html = ""
    
    for paper in papers:
        # arXivリンク
        arxiv_url = ""
        if paper.get('arxiv_id'):
            arxiv_url = f"https://arxiv.org/abs/{paper['arxiv_id']}"
        
        # 要約文
        summary = paper.get('summary', '要約情報がありません。')
        
        cards_html += f"""
        <div class="col-md-6 mb-4">
            <div class="card paper-card h-100">
                <div class="card-body">
                    <h5 class="paper-title">{paper['title']}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">{paper.get('formatted_date', '')}</h6>
                    <div class="card-text mt-3">
                        <p class="summary-text">{summary}</p>
                        <div class="mt-3">
                            <a href="{arxiv_url}" class="btn btn-sm btn-outline-primary">arXiv</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    return cards_html