import os
import sys
import traceback
import subprocess
from playwright.sync_api import sync_playwright

# 브라우저 저장 경로를 임시 폴더(MEIPASS)가 아닌 사용자 PC의 고정 경로로 강제 지정
local_app_data = os.environ.get("LOCALAPPDATA", os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local"))
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(local_app_data, "ms-playwright")

def ensure_playwright_browsers():
    print("브라우저 환경을 확인 중입니다...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        error_msg = str(e)
        if "playwright install" in error_msg:
            print("최초 실행이거나 브라우저 바이너리가 없습니다. 백그라운드에서 다운로드를 시작합니다...")
            print("네트워크 환경에 따라 1~3분 정도 소요될 수 있습니다. 진행 중에는 창을 닫지 마세요.")
            
            try:
                from playwright._impl._driver import compute_driver_executable, get_driver_env
                driver_executable = compute_driver_executable()
                env = get_driver_env()
                
                cmd = []
                if isinstance(driver_executable, tuple):
                    cmd = list(driver_executable) + ["install", "chromium"]
                else:
                    cmd = [driver_executable, "install", "chromium"]
                
                print(f"[디버그] 브라우저 설치 경로 강제 지정: {os.environ['PLAYWRIGHT_BROWSERS_PATH']}")
                subprocess.run(cmd, env=env, check=True)
                print("브라우저 다운로드가 완료되었습니다!\n")
            except Exception as dl_e:
                print(f"\n[다운로드 오류] 브라우저 설치 중 문제가 발생했습니다.")
                traceback.print_exc()
                raise dl_e
        else:
            print(f"\n[오류] 브라우저 확인 중 예상치 못한 문제가 발생했습니다.")
            traceback.print_exc()
            raise

def open_chatgpt():
    print("\n브라우저를 실행합니다...")
    
    # 세션(로그인 상태)을 유지할 폴더를 실행 파일 경로 기준으로 설정
    # PyInstaller의 단일 파일 빌드에서는 sys.executable이 임시 폴더를 가리키므로
    # 영구 저장을 위해 사용자 폴더(LOCALAPPDATA)를 사용합니다.
    if getattr(sys, 'frozen', False):
        base_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local")), "ChatGPT_Open")
        os.makedirs(base_dir, exist_ok=True)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    user_data_dir = os.path.join(base_dir, "chatgpt_user_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print(f"[디버그] 사용자 데이터 경로: {user_data_dir}")
    
    with sync_playwright() as p:
        # launch_persistent_context를 사용하여 프로필 형태로 실행 (쿠키/로그인 유지)
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # persistent_context는 기본적으로 페이지가 하나 열린 상태로 시작됨
        page = context.pages[0] if len(context.pages) > 0 else context.new_page()
        
        print("ChatGPT(https://chatgpt.com/)로 이동합니다...")
        page.goto("https://chatgpt.com/")
        
        print("\n=======================================================")
        print("페이지가 열렸습니다.")
        print("※ 처음 1회 직접 로그인을 진행해 주세요.")
        print("※ 로그인 후 브라우저 창을 닫으면 해당 상태가 저장되어, 다음 실행부터는 자동 로그인됩니다.")
        print("=======================================================\n")
        
        # 사용자가 브라우저 창을 직접 닫을 때까지 무한 대기
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        
        context.close()

if __name__ == "__main__":
    try:
        os.environ['PYTHONUNBUFFERED'] = '1'
        ensure_playwright_browsers()
        open_chatgpt()
    except Exception as main_e:
        print("\n==================================")
        print("프로그램 실행 중 치명적인 오류가 발생했습니다.")
        print("==================================")
        traceback.print_exc()
    finally:
        print("\n\n모든 작업이 끝났습니다.")
        input("터미널 창을 닫으려면 엔터 키를 누르세요...")
