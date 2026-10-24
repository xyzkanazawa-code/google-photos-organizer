import os
import sys
import time
import zipfile
import urllib.parse
from playwright.sync_api import sync_playwright

def main():
    print("==================================================")
    print("【Googleフォト ➜ Googleドライブ移動ツール】")
    print("==================================================")
    print("※ 写真内の文字（運行指示書など）をAI検索して")
    print("   パソコンの『G:\\マイドライブ\\運行指示書』へ直接保存します！")
    print("==================================================")

    # ユーザーデータ（ログイン情報）のフォルダ
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "browser_data")

    if not os.path.exists(user_data_dir):
        print("エラー: ログイン情報が見つかりません。先にログインを行ってください。")
        input("Enterキーを押して終了します...")
        return

    # 保存先フォルダ（G:\マイドライブ\運行指示書）
    drive_target_dir = r"G:\マイドライブ\運行指示書"
    if not os.path.exists(drive_target_dir):
        # もし見つからない場合のフォールバック（作成）
        try:
            os.makedirs(drive_target_dir, exist_ok=True)
        except Exception:
            # Gドライブがない場合はローカルの「運行指示書_保存」フォルダに保存
            drive_target_dir = os.path.join(base_dir, "運行指示書_保存")
            os.makedirs(drive_target_dir, exist_ok=True)

    print(f"📁 保存先フォルダ: {drive_target_dir}")

    # 検索キーワード
    keyword = input("\n検索キーワードを入力してください [未入力時は '運行指示書']: ").strip()
    if not keyword:
        keyword = "運行指示書"

    # 選択枚数
    count_str = input("ダウンロードする枚数を入力してください（例: 5）[未入力時は 5]: ").strip()
    target_count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 5

    print(f"\nChromeを起動して、『{keyword}』を検索し、最大 {target_count} 枚を保存します...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )

        page = context.pages[0] if context.pages else context.new_page()

        # Googleフォトでキーワード検索
        encoded_kw = urllib.parse.quote(keyword)
        search_url = f"https://photos.google.com/search/{encoded_kw}"
        print(f"\nGoogleフォトで『{keyword}』を検索中...")
        page.goto(search_url)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        print("写真を検出してチェック（選択）しています...")

        selected_count = 0
        scroll_attempts = 0

        while selected_count < target_count and scroll_attempts < 10:
            checkboxes = page.locator('div[role="checkbox"][aria-label^="写真 - "], div[role="checkbox"][aria-label^="動画 - "]').all()

            found_new = False
            for cb in checkboxes:
                if selected_count >= target_count:
                    break

                try:
                    if cb.get_attribute("aria-checked") != "true":
                        cb.click(force=True)
                        selected_count += 1
                        found_new = True
                        label = cb.get_attribute("aria-label") or "写真"
                        short_label = label.replace("写真 - ", "").replace("動画 - ", "")
                        print(f"  [{selected_count}/{target_count}] 選択: {short_label}")
                        time.sleep(0.3)
                except Exception:
                    continue

            if selected_count < target_count:
                page.mouse.wheel(0, 600)
                time.sleep(1.5)
                scroll_attempts += 1
                if not found_new and scroll_attempts >= 3:
                    break

        print(f"\n合計 {selected_count} 枚の写真を選択しました！")

        if selected_count > 0:
            # ダウンロード実行
            print("\n📥 Googleドライブへのダウンロードを開始します...")
            temp_download_dir = os.path.join(base_dir, "temp_downloads")
            os.makedirs(temp_download_dir, exist_ok=True)

            try:
                with page.expect_download(timeout=60000) as download_info:
                    # Shift + D で一括ダウンロード
                    page.keyboard.press("Shift+D")
                
                download = download_info.value
                download_path = os.path.join(temp_download_dir, download.suggested_filename)
                download.save_as(download_path)
                print(f"ダウンロード完了: {download.suggested_filename}")

                # ZIPファイルなら解凍してドライブフォルダへ移動
                if download_path.lower().endswith(".zip"):
                    print(f"ZIPファイルを解凍して Googleドライブ へ移動しています...")
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        zip_ref.extractall(drive_target_dir)
                    os.remove(download_path)
                else:
                    # 単一ファイル（画像など）の場合
                    dest_file = os.path.join(drive_target_dir, download.suggested_filename)
                    if os.path.exists(dest_file):
                        # 同名ファイルがある場合はタイムスタンプを付与
                        base, ext = os.path.splitext(download.suggested_filename)
                        dest_file = os.path.join(drive_target_dir, f"{base}_{int(time.time())}{ext}")
                    os.replace(download_path, dest_file)

                print("\n" + "=" * 50)
                print("🎉 【成功】 Googleドライブへの移動が完了しました！")
                print(f"保存先: {drive_target_dir}")
                print("=" * 50)

                # Googleフォト側の削除確認
                print("\nGoogleドライブに安全に保存できました。")
                confirm = input("Googleフォト側からこれらの写真を削除（ゴミ箱へ移動）しますか？\n(y = ゴミ箱へ移動 / n = フォト側にも残しておく): ").strip().lower()

                if confirm == "y":
                    print("Googleフォト側でゴミ箱へ移動しています...")
                    trash_btn = page.locator('button[aria-label*="ゴミ箱"], button[aria-label*="削除"], button[data-delete-origin]')
                    if trash_btn.count() > 0 and trash_btn.first.is_visible():
                        trash_btn.first.click()
                    else:
                        page.keyboard.press("#")

                    time.sleep(1.5)
                    confirm_btn = page.locator('button:has-text("ゴミ箱に移動"), button:has-text("Move to trash")')
                    if confirm_btn.count() > 0:
                        confirm_btn.first.click()
                        print("✅ Googleフォト側をゴミ箱へ移動しました！空き容量が増加します。")
                    else:
                        page.keyboard.press("Enter")
                        print("✅ 移動を完了しました。")
                    time.sleep(2)
                else:
                    print("フォト側にも写真をそのまま残しました。")

            except Exception as e:
                print(f"ダウンロード中にエラーが発生しました: {e}")
                print("画面右上のメニュー『︙』から手動でダウンロードすることも可能です。")
                input("Enterキーを押すと終了します...")

        else:
            print(f"『{keyword}』に一致する写真が見つかりませんでした。")
            input("Enterキーを押すと終了します...")

        print("\nブラウザを終了します。")
        time.sleep(1)
        context.close()

if __name__ == "__main__":
    main()
