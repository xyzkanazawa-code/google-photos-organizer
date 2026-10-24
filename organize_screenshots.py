import os
import sys
import time
import json
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
    print("【Googleフォト スクリーンショット自動整理ツール】")
    print("==================================================")
    print("※ 完全無料で動作します。")
    print("※ チェックを外した写真は自動で『残すリスト』に記憶され、")
    print("   次回以降は自動でスキップ（除外）されます！")
    print("==================================================")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(base_dir, "browser_data")

    if not os.path.exists(user_data_dir):
        print("エラー: ログイン情報が見つかりません。先にログインを行ってください。")
        input("Enterキーを押して終了します...")
        return

    # 保護リストの読み込み
    protected_photos = load_protected_photos()
    if protected_photos:
        print(f"現在、{len(protected_photos)} 枚の写真が『残す写真』として記憶されています。")

    # 選択する枚数を尋ねる
    print("\n何枚のスクリーンショットを選択しますか？")
    count_str = input("枚数を入力してください（例: 5）[未入力時は 5]: ").strip()
    target_count = int(count_str) if count_str.isdigit() and int(count_str) > 0 else 5

    print(f"\nChromeを起動して、未保護のスクリーンショットを最大 {target_count} 枚選択します...")

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

        print("\nGoogleフォトの「スクリーンショット」一覧を開いています...")
        page.goto("https://photos.google.com/search/screenshots")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        print(f"写真を順番にチェック（選択）していきます（目標: {target_count} 枚）...")

        selected_count = 0
        scroll_attempts = 0
        
        # 今回自動でチェックを入れたアイテムのラベル一覧
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

                    # 過去にマサが「残す」と決めた写真ならスキップ
                    if label in protected_photos or short_label in protected_photos:
                        continue

                    # まだチェックされていない写真ならチェック
                    is_checked = cb.get_attribute("aria-checked")
                    if is_checked != "true":
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

        print(f"\n合計 {selected_count} 枚のスクリーンショットを選択しました！")

        if selected_count > 0:
            print("\nブラウザの画面を見てください。青いチェックマークで選択されています。")
            print("💡 残したい写真があれば、画面上でクリックしてチェックを外してください。")

            confirm = input("\nゴミ箱に移動しますか？\n(y = 移動実行 / n = 全てキャンセル): ").strip().lower()

            # ユーザーがチェックを外したかどうか（現在 aria-checked="false" になっているもの）を判定
            unselected_by_user = []
            for label in initially_checked_labels:
                try:
                    cb = page.locator(f'div[role="checkbox"][aria-label="{label}"]').first
                    if cb.count() > 0:
                        if cb.get_attribute("aria-checked") != "true":
                            unselected_by_user.append(label)
                except Exception:
                    pass

            # チェックが外された写真を保護リストに追加
            if unselected_by_user:
                for lbl in unselected_by_user:
                    protected_photos.add(lbl)
                    short = lbl.replace("写真 - ", "").replace("動画 - ", "")
                    protected_photos.add(short)
                save_protected_photos(protected_photos)
                print(f"\n✨ チェックを外した {len(unselected_by_user)} 枚の写真を『残すリスト』に記憶しました！")
                print("   次回以降、この写真は自動選択から除外（スキップ）されます。")

            if confirm == "y":
                print("\nゴミ箱への移動を実行しています...")
                trash_btn = page.locator('button[aria-label*="ゴミ箱"], button[aria-label*="削除"], button[data-delete-origin]')
                if trash_btn.count() > 0 and trash_btn.first.is_visible():
                    trash_btn.first.click()
                else:
                    page.keyboard.press("#")

                time.sleep(1.5)
                confirm_btn = page.locator('button:has-text("ゴミ箱に移動"), button:has-text("Move to trash")')
                if confirm_btn.count() > 0:
                    confirm_btn.first.click()
                    print("✅ ゴミ箱への移動が完了しました！")
                else:
                    page.keyboard.press("Enter")
                    print("✅ 完了しました。")
                time.sleep(2)
            else:
                print("\nキャンセルしました。写真は削除されていません。")
        else:
            print("新しく選択できるスクリーンショットが見つかりませんでした。")

        print("\nブラウザを終了します。")
        time.sleep(1)
        context.close()

if __name__ == "__main__":
    main()
