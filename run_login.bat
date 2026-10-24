@echo off
chcp 65001 > nul
echo ==================================================
echo Googleフォト 自動化ツール（ログイン・起動テスト）
echo ==================================================
echo.
echo ブラウザ（Chrome）を起動しています...
echo.

cd /d "%~dp0"
python login_test.py

pause
