import os
import sys
import time
import zipfile
import json
import urllib.parse
from playwright.sync_api import sync_playwright

PROTECTED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "protected_photos.json")

def load_protected_photos():
    """残す（除外する）写真のリストを読み込む"""
    if os.path.exists(PROTECTED_FILE):
        try:
            with open(PROTECTED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_protected_photos(protected_set):
    """残す（除外する）写真のリストを保存する"""
    try:
        with open(PROTECTED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(protected_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保護リストの保存に失敗しました: {e}")

def main():
    print("==================================================")
    print("【Googleフォト ➜ Googleドライブ移動ツール】")
    print("==================================================")
    print("※ 好きな言葉（運行指示書、領収書など）で検索して、")
    print("   Googleドライブ（Gドライブ）のお好きなフォルダへ自動保存できます！")
    print("※ 新しいフォルダ名を入れると、自動で新規作成されます。")
    print("==================================================")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "browser_data")

    if not os.path.exists(user_data_dir):
        print("エラー: ログイン情報が見つかりません。先にログインを行ってください。")
        input("Enterキーを押して終了します...")
        return

    # 保護リストの読み込み
    protected_photos = load_protected_photos()

    # 1. 検索キーワードの入力
    print("\n【ステップ 1】探したい写真のキーワード")
    keyword = input("検索キーワードを入力してください [未入力時は '運行指示書']: ").strip()
    if not keyword:
        keyword = "運行指示書"

    # 2. 保存先フォルダの決定
    print("\n【ステップ 2】Googleドライブ内の保存先フォルダ")
    my_drive_base = r"G:\マイドライブ"
    if not os.path.exists(my_drive_base):
        # Gドライブが見つからない場合の予備（ローカル）
        my_drive_base = os.path.join(base_dir, "GoogleDrive_保存先")

    default_folder_name = keyword
    print(f"どのフォルダに保存しますか？（未入力なら自動で『{default_folder_name}』になります）")
    folder_input = input("フォルダ名を入力 [未入力時はそのままEnter]: ").strip()

    target_folder_name = folder_input if folder_input else default_folder_name
    drive_target_dir = os.path.join(my_drive_base, target_folder_name)

    # フォルダが存在しなければ自動作成
    if not os.path.exists(drive_target_dir):
        try:
            os.makedirs(drive_target_dir, exist_ok=True)
            print(f"✨ 新しいフォルダ『{target_folder_name}』をGoogleドライブに作成しました！")
        except Exception as e:
            print(f"フォルダ作成エラー: {e}")

    print(f"📁 保存先: {drive_target_dir}")

    # 3. 選択枚数
    print("\n【ステップ 3】枚数の指定")
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
        initially_checked_labels = []

        while selected_count < target_count and scroll_attempts < 15:
            checkboxes = page.locator('div[role="checkbox"][aria-label^="写真 - "], div[role="checkbox"][aria-label^="動画 - "]').all()

            found_new = False
            for cb in checkboxes:
                if selected_count >= target_count:
                    break

                try:
                    label = cb.get_attribute("aria-label") or ""
                    short_label = label.replace("写真 - ", "").replace("動画 - ", "")

                    # 過去にマサが除外した写真ならスキップ
                    if label in protected_photos or short_label in protected_photos:
                        continue

                    if cb.get_attribute("aria-checked") != "true":
                        cb.click(force=True)
                        selected_count += 1
                        found_new = True
                        initially_checked_labels.append(label)
                        print(f"  [{selected_count}/{target_count}] 選択: {short_label}")
                        time.sleep(0.3)
                except Exception:
                    continue

            if selected_count < target_count:
                page.mouse.wheel(0, 600)
                time.sleep(1.5)
                scroll_attempts += 1
                if not found_new and scroll_attempts >= 4:
                    break

        print(f"\n合計 {selected_count} 枚の写真を選択しました！")

        if selected_count > 0:
            print("\nブラウザの画面を見てください。青いチェックマークで選択されています。")
            print("💡 残したい写真や対象外の写真があれば、画面上でクリックしてチェックを外してください。")

            input("\n画面の確認が終わったら、ここに Enter キーを押してください: ")

            # ユーザーがチェックを外したアイテムを判定
            unselected_by_user = []
            for label in initially_checked_labels:
                try:
                    cb = page.locator(f'div[role="checkbox"][aria-label="{label}"]').first
                    if cb.count() > 0:
                        if cb.get_attribute("aria-checked") != "true":
                            unselected_by_user.append(label)
                except Exception:
                    pass

            if unselected_by_user:
                for lbl in unselected_by_user:
                    protected_photos.add(lbl)
                    short = lbl.replace("写真 - ", "").replace("動画 - ", "")
                    protected_photos.add(short)
                save_protected_photos(protected_photos)
                print(f"✨ チェックを外した {len(unselected_by_user)} 枚の写真を次回以降スキップするよう記憶しました。")

            # ダウンロード実行
            print(f"\n📥 Googleドライブの『{target_folder_name}』へダウンロードを開始します...")
            temp_download_dir = os.path.join(base_dir, "temp_downloads")
            os.makedirs(temp_download_dir, exist_ok=True)

            try:
                with page.expect_download(timeout=60000) as download_info:
                    page.keyboard.press("Shift+D")

                download = download_info.value
                download_path = os.path.join(temp_download_dir, download.suggested_filename)
                download.save_as(download_path)
                print(f"ダウンロード完了: {download.suggested_filename}")

                # ZIPファイルなら解凍してドライブフォルダへ移動
                if download_path.lower().endswith(".zip"):
                    print(f"ZIPを展開して Googleドライブ へ移動中...")
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        zip_ref.extractall(drive_target_dir)
                    os.remove(download_path)
                else:
                    dest_file = os.path.join(drive_target_dir, download.suggested_filename)
                    if os.path.exists(dest_file):
                        base, ext = os.path.splitext(download.suggested_filename)
                        dest_file = os.path.join(drive_target_dir, f"{base}_{int(time.time())}{ext}")
                    os.replace(download_path, dest_file)

                print("\n" + "=" * 50)
                print(f"🎉 【成功】 Googleドライブの『{target_folder_name}』フォルダへ保存完了！")
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
                        print("✅ Googleフォト側をゴミ箱へ移動しました！")
                    else:
                        page.keyboard.press("Enter")
                        print("✅ 移動を完了しました。")
                    time.sleep(2)
                else:
                    print("フォト側にも写真をそのまま残しました。")

            except Exception as e:
                print(f"ダウンロード中にエラーが発生しました: {e}")
                input("Enterキーを押すと終了します...")

        else:
            print(f"『{keyword}』に一致する写真が見つかりませんでした。")
            input("Enterキーを押すと終了します...")

        print("\nブラウザを終了します。")
        time.sleep(1)
        context.close()

if __name__ == "__main__":
    main()
