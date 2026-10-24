import os
import time
from playwright.sync_api import sync_playwright

def main():
    print("==================================================")
    print("【Googleフォト ログイン・動作テスト】")
    print("==================================================")
    print("1. ブラウザが自動で開きます。")
    print("2. Googleフォトの画面が表示されたら、ログインしてください。")
    print("3. ログイン完了後、写真を閲覧できる状態になったら")
    print("   このターミナル（画面）に戻って Enter キーを押してください。")
    print("==================================================")

    # ログイン状態を保存する専用フォルダ（次回以降もログインが維持されます）
    user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_data")

    with sync_playwright() as p:
        # 画面を見ながら操作できるように headless=False で起動
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",  # パソコンに入っている本物のGoogle Chromeを使用（ロボット判定を回避しやすい）
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",  # 自動操作の旗を隠す
                "--start-maximized"
            ],
            no_viewport=True
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://photos.google.com/")

        # ユーザーがログインしてEnterを押すまで待機
        input("\nGoogleフォトへのログインが完了したら、ここに Enter キーを押してください: ")

        print("\n現在のページタイトル:", page.title())
        print("ログイン状態が 'browser_data' フォルダに正常に保存されました！")

        context.close()

if __name__ == "__main__":
    main()
