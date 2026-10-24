import os
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("==================================================")
    print("【Googleフォト スクリーンショット自動整理ツール】")
    print("==================================================")
    print("※ 完全無料で動作します。")
    print("※ 勝手に削除はしません。必ず最後に確認します。")
    print("==================================================")

    # ユーザーデータ（ログイン情報）のフォルダ
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "browser_data")

    if not os.path.exists(user_data_dir):
        print("エラー: ログイン情報が見つかりません。先にログインを行ってください。")
        input("Enterキーを押して終了します...")
        return

    # 選択する枚数を尋ねる
    print("\n何枚のスクリーンショットを選択しますか？")
    count_str = input("枚数を入力してください（例: 5）[未入力時は 5]: ").strip()
    target_count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 5

    print(f"\nChromeを起動して、スクリーンショットを最大 {target_count} 枚選択します...")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )

        page = context.pages[0] if context.pages else context.new_page()

        # スクリーンショット一覧ページへアクセス
        print("\nGoogleフォトの「スクリーンショット」一覧を開いています...")
        page.goto("https://photos.google.com/search/screenshots")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)  # 写真が読み込まれるのを少し待機

        print(f"写真を順番にチェック（選択）していきます（目標: {target_count} 枚）...")

        selected_count = 0
        scroll_attempts = 0

        while selected_count < target_count and scroll_attempts < 10:
            # 写真アイテムのチェックボックス（aria-labelが「写真 - 」または「動画 - 」で始まるもの）
            checkboxes = page.locator('div[role="checkbox"][aria-label^="写真 - "], div[role="checkbox"][aria-label^="動画 - "]').all()

            found_new = False
            for cb in checkboxes:
                if selected_count >= target_count:
                    break

                try:
                    # まだチェックされていないか確認 (aria-checked="false")
                    is_checked = cb.get_attribute("aria-checked")
                    if is_checked != "true":
                        # チェックを入れる
                        cb.click(force=True)
                        selected_count += 1
                        found_new = True
                        label = cb.get_attribute("aria-label") or "写真"
                        # 日時部分をきれいに表示
                        short_label = label.replace("写真 - ", "").replace("動画 - ", "")
                        print(f"  [{selected_count}/{target_count}] 選択: {short_label}")
                        time.sleep(0.3)
                except Exception as e:
                    # スクロール等で要素が外れた場合はスキップ
                    continue

            if selected_count < target_count:
                # 枚数が足りない場合は下に少しスクロールして次の写真を読み込む
                page.mouse.wheel(0, 600)
                time.sleep(1.5)
                scroll_attempts += 1
                if not found_new and scroll_attempts >= 3:
                    # これ以上写真が見つからない場合
                    break

        print(f"\n合計 {selected_count} 枚のスクリーンショットを選択しました！")

        if selected_count > 0:
            print("\nブラウザの画面を見てください。青いチェックマークで選択されているはずです。")

            # ユーザーに確認
            confirm = input("\nこれらをゴミ箱に移動しますか？ (y = ゴミ箱へ移動 / n = キャンセル): ").strip().lower()

            if confirm == "y":
                print("ゴミ箱への移動を実行しています...")
                # 画面右上のゴミ箱ボタンをクリック、または '#' キー
                trash_btn = page.locator('button[aria-label*="ゴミ箱"], button[aria-label*="削除"], button[data-delete-origin]')
                if trash_btn.count() > 0 and trash_btn.first.is_visible():
                    trash_btn.first.click()
                else:
                    page.keyboard.press("#")

                time.sleep(1.5)

                # 確認ダイアログの「ゴミ箱に移動」ボタンをクリック
                confirm_btn = page.locator('button:has-text("ゴミ箱に移動"), button:has-text("Move to trash")')
                if confirm_btn.count() > 0:
                    confirm_btn.first.click()
                    print("✅ ゴミ箱への移動が完了しました！")
                else:
                    page.keyboard.press("Enter")
                    print("✅ 完了しました。")
                time.sleep(2)
            else:
                print("キャンセルしました。写真は削除されていません。安心してください。")
        else:
            print("スクリーンショットが見つかりませんでした。")

        print("\nブラウザを終了します。")
        time.sleep(1)
        context.close()

if __name__ == "__main__":
    main()
