@echo off
echo =======================================
echo Playwright 네이버 접속 스크립트 빌드 시작
echo =======================================

echo 가상환경(venv) 생성 중...
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo 필수 패키지(playwright, pyinstaller) 설치 중...
pip install playwright pyinstaller

echo.
echo Playwright 브라우저(chromium) 설치 중...
playwright install chromium

echo.
echo 실행 파일(.exe) 빌드 중...
pyinstaller --onefile --name "Naver_Open" naver_open.py

echo.
echo =======================================
echo 빌드가 완료되었습니다!
echo 실행 파일 위치: dist\Naver_Open.exe
echo =======================================
pause
