#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import logging
from openai import OpenAI
from datetime import datetime

def truncate_text(text, max_length=10000):
    """テキストを指定された長さに切り詰める"""
    if len(text) <= max_length:
        return text
    
    # 最初の部分を保持
    first_part = text[:max_length // 2]
    
    # 最後の部分を保持
    last_part = text[-max_length // 2:]
    
    # 中間部分を省略したことを示す
    return first_part + "\n...(中略)...\n" + last_part

def generate_summary(client, text, prompt_template, summary_dir, title, arxiv_id):
    """論文の要約を生成する"""
    try:
        # テキストを切り詰める
        truncated_text = truncate_text(text)
        
        # プロンプトを作成
        logging.info(f"論文 '{title}' のプロンプトを作成中...")
        prompt = prompt_template.format(論文テキスト=truncated_text)
        logging.info(f"プロンプト作成完了（文字数: {len(prompt)}文字）")
        
        # OpenAI APIを呼び出し
        max_retries = 3
        retry_count = 0
        backoff_time = 2
        
        while retry_count < max_retries:
            try:
                retry_count += 1
                logging.info(f"OpenAI APIを呼び出し中... (試行: {retry_count}/{max_retries})")
                start_time = time.time()
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "あなたは研究者です。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                end_time = time.time()
                logging.info(f"OpenAI API呼び出し完了（所要時間: {end_time - start_time:.2f}秒）")
                
                # レスポンスから要約を抽出
                logging.info("APIレスポンスから要約を抽出中...")
                summary = response.choices[0].message.content.strip()
                logging.info(f"要約抽出完了（文字数: {len(summary)}文字）")
                
                # arXivのURLを追加
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                
                # 要約文を作成（URLを先頭に、その後にgreetingを追加）
                summary = f"{arxiv_url} C(・ω・ )つ みんなー！{summary}"
                
                # 要約結果をJSONファイルに保存
                result = {
                    'title': title,
                    'arxiv_id': arxiv_id,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'summary': summary,
                }
                
                # サマリーディレクトリを作成
                os.makedirs(summary_dir, exist_ok=True)
                
                # ファイル名を作成
                summary_file = os.path.join(summary_dir, f"{arxiv_id}_summary.json")
                logging.info(f"要約結果をファイルに保存中: {summary_file}")
                
                # JSONファイルに保存
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                logging.info(f"要約生成・保存完了: {summary_file}")
                
                return result
            
            except Exception as e:
                logging.warning(f"APIエラーが発生しました: {str(e)}。{backoff_time}秒後にリトライします。({retry_count}/{max_retries})")
                if retry_count < max_retries:
                    time.sleep(backoff_time)
                    backoff_time *= 2
                else:
                    logging.error(f"要約生成エラー: {str(e)}")
                    return None
    
    except Exception as e:
        logging.error(f"要約生成エラー: {str(e)}")
        return None