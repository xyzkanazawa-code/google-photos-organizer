import os
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    print("==================================================")
    print("【Googleフォト スクリーンショット自動整理ツール】")
    print("==================================================")
    print("※ 完全無料で動作します。")
    print("※ 安全のため、勝手に削除はしません。必ず最後に確認します。")
    print("==================================================")

    # ユーザーデータ（ログイン情報）のフォルダ
    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "browser_data")

    if not os.path.exists(user_data_dir):
        print("エラー: ログイン情報が見つかりません。先にログインテストを行ってください。")
        input("Enterキーを押して終了します...")
        return

    # 選択する枚数を尋ねる
    print("\n何枚のスクリーンショットを選択しますか？")
    count_str = input("枚数を入力してください（例: 10）[未入力時は 10]: ").strip()
    target_count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 10

    print(f"\nChromeを起動して、スクリーンショットを {target_count} 枚選択します...")

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
        time.sleep(3)  # 写真のサムネイルが読み込まれるのを待機

        # 写真アイテムのセレクタを探す
        # Googleフォトの写真要素（role="listitem" や aria-label を持つ要素）
        print("写真を検出中...")

        # 最初の写真を探してフォーカスを当てる
        # 画面中央付近をクリックするか、Tabキーやセレクタで最初の写真に到達
        photos = page.locator('c-wiz[role="region"] a[aria-label], div[role="listitem"]')
        photo_count = photos.count()

        if photo_count == 0:
            # 代替セレクタ
            photos = page.locator('a[aria-label*="写真"], a[aria-label*="Photo"], a[aria-label*="画像"]')
            photo_count = photos.count()

        print(f"画面上に写真を検出しました（約 {photo_count} 項目）。")

        if photo_count > 0:
            # 最初の写真をクリックしてフォーカス
            first_photo = photos.first
            first_photo.focus()
            first_photo.hover()
            time.sleep(0.5)

            # チェックボタン（チェックマーク）を探すか、キーボード操作で選択
            # Googleフォトは "x" キーで選択可能
            print(f"写真を順番に選択しています（目標: {target_count} 枚）...")
            
            selected = 0
            # 最初の写真を選択
            page.keyboard.press("x")
            selected += 1
            print(f"[{selected}/{target_count}] 枚目を選択しました")
            time.sleep(0.3)

            # 右矢印で次へ進みながら 'x' を押す
            for _ in range(target_count - 1):
                page.keyboard.press("ArrowRight")
                time.sleep(0.2)
                page.keyboard.press("x")
                selected += 1
                print(f"[{selected}/{target_count}] 枚目を選択しました")
                time.sleep(0.2)

            print(f"\n合計 {selected} 枚のスクリーンショットを選択しました！")
            print("ブラウザの画面を見て、正しく選択されているか確認してください。")

            # ユーザーに確認
            confirm = input("\nこれらをゴミ箱に移動しますか？ (y = ゴミ箱へ移動 / n = キャンセル): ").strip().lower()

            if confirm == "y":
                print("ゴミ箱への移動を実行します...")
                # Googleフォトのゴミ箱ショートカットは '#' キー
                page.keyboard.press("#")
                time.sleep(1.5)

                # 「ゴミ箱に移動」確認ダイアログのボタンを探してクリック
                trash_button = page.locator('button:has-text("ゴミ箱に移動"), button:has-text("Move to trash")')
                if trash_button.is_visible():
                    trash_button.click()
                    print("✅ ゴミ箱への移動が完了しました！")
                else:
                    # Enterキーでも確認ダイアログが決定される場合がある
                    page.keyboard.press("Enter")
                    print("✅ 移動コマンドを送信しました。")
                time.sleep(2)
            else:
                print("キャンセルしました。写真は削除されていません。")
        else:
            print("スクリーンショットが見つからないか、写真の読み込みに時間がかかっています。")
            print("ブラウザ画面を確認してください。")
            input("Enterキーを押すと終了します...")

        print("\nブラウザを終了します。お疲れ様でした！")
        time.sleep(1)
        context.close()

if __name__ == "__main__":
    main()
