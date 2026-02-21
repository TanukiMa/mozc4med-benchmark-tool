import pyautogui
import time
import sys
import pyperclip
import argparse
import logging
import re
from typing import List, Dict, Any

import pykakasi

def safe_paste(retries=3, delay=0.3):
    for _ in range(retries):
        try:
            return pyperclip.paste()
        except Exception as e:
            logging.error(f"クリップボードエラー: {e} リトライします...")
            time.sleep(delay)
    return ""

def convert_to_romaji(text: str) -> str:
    text = text.replace('ー', '-')

    # ザ行・ダ行+小文字 の特殊処理 (例: ディ -> dexi, ジェ -> zixe)
    target_gyo = {
        'ざ': 'za', 'じ': 'zi', 'ず': 'zu', 'ぜ': 'ze', 'ぞ': 'zo',
        'だ': 'da', 'ぢ': 'di', 'づ': 'du', 'で': 'de', 'ど': 'do'
    }
    small_kana = {
        'ぁ': 'xa', 'ぃ': 'xi', 'ぅ': 'xu', 'ぇ': 'xe', 'ぉ': 'xo',
        'ゃ': 'xya', 'ゅ': 'xyu', 'ょ': 'xyo',
        'っ': 'xtu'
    }

    def replace_target_small(match):
        parent = match.group(1)
        child = match.group(2)
        return target_gyo[parent] + small_kana[child]

    # [ざ-ぞだ-ど] の後ろに [ぁ-ぉゃ-ょっ] が続く場合を先に置換
    text = re.sub(r'(ざ|じ|ず|ぜ|ぞ|だ|ぢ|づ|で|ど)(ぁ|ぃ|ぅ|ぇ|ぉ|ゃ|ゅ|ょ|っ)', replace_target_small, text)

    kks = pykakasi.Kakasi()
    
    # 'ん' で分割して処理することで、'ん' を確実に 'nn' に変換する
    parts = text.split('ん')
    
    romaji_parts = []
    for part in parts:
        if not part:
            romaji_parts.append("")
            continue
            
        result = kks.convert(part)
        r = "".join([item['kunrei'] for item in result])
        # 余計なスペースやアポストロフィを除去
        r = r.replace(' ', '').replace("'", "")
        romaji_parts.append(r)
        
    final_romaji = "nn".join(romaji_parts)
    return final_romaji

def main():
    parser = argparse.ArgumentParser(description='日本語IME精度評価ツール v1.5（ローマ字入力シミュレーション・変換結果保存のみ）')
    parser.add_argument('correct_answer_file', help='正答文字列（比較元）を収録したファイル')
    parser.add_argument('--source', required=True, help='自動入力の元となるひらがな文字列のファイル')
    parser.add_argument('--results', required=False, help='IMEからの変換結果（文字列のみ）を保存するファイル')
    parser.add_argument('--output', dest='output', help='IMEからの変換結果（文字列のみ）を保存するファイル（別名）')
    parser.add_argument('--result_file', dest='result_file', help='IMEからの変換結果（文字列のみ）を保存するファイル（別名）')
    parser.add_argument('--log_file', help='処理ログを保存するファイルパス')
    args = parser.parse_args()

    results_path = args.results or args.output or args.result_file
    if not results_path:
        parser.error("--results, --output, --result_file のいずれかを指定してください。")

    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=log_format)
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(console_handler)
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file, 'w', 'utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)

    logging.info("スクリプトを開始します。")

    try:
        logging.info(f"正答ファイルを読み込みます: '{args.correct_answer_file}'")
        with open(args.correct_answer_file, 'r', encoding='utf-8') as f:
            correct_texts = [line.strip() for line in f if line.strip()]
        logging.info(f"ひらがな入力元ファイルを読み込みます: '{args.source}'")
        with open(args.source, 'r', encoding='utf-8') as f:
            hiragana_inputs = [line.strip() for line in f if line.strip()]
    except FileNotFoundError as e:
        logging.error(f"ファイルが見つかりません。 {e}")
        sys.exit(1)
    if len(correct_texts) != len(hiragana_inputs):
        logging.error(f"正答ファイル({len(correct_texts)}行)とひらがな入力ファイル({len(hiragana_inputs)}行)の行数が一致しません。")
        sys.exit(1)

    with open(results_path, 'w', encoding='utf-8') as out_f:
        logging.info("10秒後に処理を開始します。")
        logging.info("入力ウィンドウにフォーカスを合わせ、IMEが「ローマ字入力」モードになっていることを確認してください。")
        time.sleep(10)
        try:
            for i, hiragana_text in enumerate(hiragana_inputs):
                logging.info(f"--- 処理 {i+1}/{len(hiragana_inputs)} を開始 ---")
                romaji_text = convert_to_romaji(hiragana_text)
                logging.info(f"ひらがな -> ローマ字変換: '{hiragana_text}' -> '{romaji_text}'")
                logging.debug(f"キーボード入力: pyautogui.typewrite('{romaji_text}')")
                pyautogui.typewrite(romaji_text, interval=0.05)
                time.sleep(1.0)
                logging.debug("キー操作: press('space') で変換")
                pyautogui.press('space')
                time.sleep(1.5)
                logging.debug("キー操作: press('enter') で確定")
                pyautogui.press('enter')
                time.sleep(1.0)
                output_text = ""
                logging.debug("変換結果の取得処理を開始...")
                for attempt in range(5):
                    pyperclip.copy("")
                    logging.debug(f"試行 {attempt + 1}: Ctrl+A, Ctrl+C")
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.hotkey('ctrl', 'c')
                    time.sleep(0.5)
                    pasted_text = safe_paste().strip()
                    if pasted_text:
                        output_text = pasted_text
                        logging.debug(f"テキスト取得成功: '{output_text}'")
                        break
                    logging.warning(f"試行 {attempt + 1}: テキスト取得失敗。リトライします。")
                    time.sleep(1.0)
                out_f.write(output_text + '\n')
                out_f.flush()
                logging.debug("入力フィールドをクリア (Ctrl+A, Delete)")
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.press('delete')
                logging.info(f"結果: 「{correct_texts[i]}」 -> 「{output_text}」")
        except KeyboardInterrupt:
            logging.warning("\nスクリプトがユーザーによって中断されました。")
        except Exception as e:
            logging.error(f"\n予期せぬエラーが発生しました: {e}", exc_info=True)
        finally:
            logging.info(f"自動入力処理が完了しました。結果は '{results_path}' に保存されています。")

    logging.info("スクリプトが正常に終了しました。")

if __name__ == "__main__":
    main()
