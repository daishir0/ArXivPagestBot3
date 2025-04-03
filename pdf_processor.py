#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import PyPDF2
import logging

def extract_text_from_pdf(pdf_path, output_dir):
    """PDFからテキストを抽出する"""
    try:
        # 出力ファイルパスを作成
        filename = os.path.basename(pdf_path)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{base_name}.txt")
        
        # PDFファイルを開く
        logging.info(f"PDFファイルを開いています: {pdf_path}")
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            logging.info(f"PDFファイルを読み込みました（ページ数: {num_pages}ページ）")
            
            # テキストを抽出
            logging.info("PDFからテキストを抽出中...")
            text = ""
            for i, page in enumerate(reader.pages, 1):
                text += page.extract_text() + "\n\n"
                if i % 10 == 0:
                    logging.info(f"  {i}/{num_pages}ページ処理完了")
            
            # 最後のページ数を表示
            if num_pages % 10 != 0:
                logging.info(f"  {num_pages}/{num_pages}ページ処理完了")
            
            logging.info(f"テキスト抽出完了（文字数: {len(text)}文字）")
            
            # テキストをファイルに保存
            logging.info(f"抽出したテキストをファイルに保存中: {output_path}")
            with open(output_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(text)
            
            logging.info(f"テキスト抽出・保存完了: {pdf_path} -> {output_path}（所要時間: {0:.2f}秒）")
            
            return output_path
    
    except Exception as e:
        logging.error(f"テキスト抽出エラー: {pdf_path} - {str(e)}")
        return None