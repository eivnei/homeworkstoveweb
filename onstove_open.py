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

def open_onstove():
    print("\n브라우저를 실행합니다...")
    
    # 세션(로그인 상태)을 유지할 폴더를 실행 파일 경로 기준으로 설정
    # 주의: PyInstaller의 단일 파일 빌드에서는 sys.executable이 임시 폴더를 가리키므로
    # 영구 저장을 위해 사용자 폴더(예: LOCALAPPDATA)를 사용합니다.
    
    # 실행 환경 확인
    is_frozen = getattr(sys, 'frozen', False)
    print(f"[디버그] frozen 상태: {is_frozen}")
    print(f"[디버그] LOCALAPPDATA: {local_app_data}")
    
    if is_frozen:
        base_dir = os.path.join(local_app_data, "Onstove_Open")
        os.makedirs(base_dir, exist_ok=True)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    user_data_dir = os.path.join(base_dir, "onstove_user_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    # 로그인 상태 확인 및 디버그 정보 출력
    print(f"\n[디버그] 실행 환경: {'EXE (PyInstaller)' if is_frozen else 'Python 스크립트'}")
    print(f"[디버그] Base 디렉토리: {base_dir}")
    print(f"[디버그] User Data 디렉토리: {user_data_dir}")
    
    # 폴더 존재 여부 및 접근 권한 확인
    try:
        test_file = os.path.join(user_data_dir, ".test_write")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print(f"[디버그] 폴더 접근 권한: ✓ 있음")
    except Exception as e:
        print(f"[디버그] 폴더 접근 권한: ✗ 없음 - {e}")
    
    # 저장된 쿠키 파일 확인
    has_cookies = False
    try:
        default_profile = os.path.join(user_data_dir, "Default")
        cookies_file = os.path.join(default_profile, "Network", "Cookies")
        has_cookies = os.path.exists(cookies_file)
        print(f"[디버그] 저장된 쿠키 여부: {'있음' if has_cookies else '없음'}")
    except Exception as e:
        print(f"[디버그] 쿠키 확인 오류: {e}")
    
    with sync_playwright() as p:
        # launch_persistent_context를 사용하여 프로필 형태로 실행 (쿠키/로그인 유지)
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # 저장된 쿠키 불러오기
        cookies_file = os.path.join(base_dir, "cookies.json")
        if os.path.exists(cookies_file):
            try:
                import json
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    saved_cookies = json.load(f)
                context.add_cookies(saved_cookies)
                print(f"[디버그] {len(saved_cookies)}개의 저장된 쿠키를 성공적으로 불러왔습니다.")
            except Exception as e:
                print(f"[경고] 쿠키 불러오기 중 오류 발생: {e}")
        
        # persistent_context는 기본적으로 페이지가 하나 열린 상태로 시작됨
        page = context.pages[0] if len(context.pages) > 0 else context.new_page()
        
        print("Onstove 리워드(https://reward.onstove.com/ko)로 이동합니다...")
        page.goto("https://reward.onstove.com/ko")
        
        # 페이지 로드 대기
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        
        # 로그인 상태 확인
        is_logged_in = page.evaluate("""
        () => {
            // '로그인' 텍스트가 없으면 로그인된 상태
            const loginBtn = Array.from(document.querySelectorAll('button, a')).find(el => 
                el.textContent.trim().includes('로그인') && !el.textContent.trim().includes('로그아웃')
            );
            return !loginBtn;
        }
        """)
        
        print("\n=======================================================")
        if is_logged_in:
            print("✓ 로그인 상태: 이미 로그인되어 있습니다.")
            print("자동 미션 수행을 시작합니다...")
        else:
            print("✗ 로그인 상태: 로그인이 필요합니다.")
            print("※ 직접 로그인을 진행해 주세요.")
        print("=======================================================\n")
            
        # JS 헬퍼 함수 정의
        js_check_mission = """
        (missionText) => {
            const normalize = t => (t || '').replace(/\s+/g, '').toLowerCase();
            const target = normalize(missionText);
            const elements = Array.from(document.querySelectorAll('*'));
            const titleEls = elements.filter(el => normalize(el.textContent).includes(target) && el.children.length === 0);
            if (titleEls.length === 0) return false;
            let parent = titleEls[0].parentElement;
            while (parent && parent !== document.body) {
                const btns = Array.from(parent.querySelectorAll('button, a'));
                const btn = btns.find(b => normalize(b.textContent).includes('미션하기'));
                if (btn) return true;
                parent = parent.parentElement;
            }
            return false;
        }
        """

        # 만약 로그인이 필요하면 로그인 완료까지 대기 (최대 3분)
        if not is_logged_in:
            print("로그인 대기 중... (최대 3분)")
            login_timeout = 180000  # 3분
            
            try:
                # 로그인이 완료될 때까지 폴링 (10초마다 확인)
                login_complete = False
                elapsed = 0
                while not login_complete and elapsed < login_timeout:
                    page.wait_for_timeout(10000)
                    elapsed += 10000
                    
                    login_complete = page.evaluate("""
                    () => {
                        const loginBtn = Array.from(document.querySelectorAll('button, a')).find(el => 
                            el.textContent.trim().includes('로그인') && !el.textContent.trim().includes('로그아웃')
                        );
                        return !loginBtn;
                    }
                    """)
                    
                    if login_complete:
                        print("✓ 로그인이 완료되었습니다!")
                        page.wait_for_timeout(2000)  # 안정화 대기
                        break
                    
                if not login_complete:
                    print("⚠ 3분 내에 로그인이 완료되지 않았습니다.")
                    print("미션 수행을 스킵합니다.")
                    context.close()
                    return
                    
            except Exception as e:
                print(f"[경고] 로그인 대기 중 오류: {e}")
        
        # 로그인 상태 다시 확인
        is_logged_in_now = page.evaluate("""
        () => {
            const loginBtn = Array.from(document.querySelectorAll('button, a')).find(el => 
                el.textContent.trim().includes('로그인') && !el.textContent.trim().includes('로그아웃')
            );
            return !loginBtn;
        }
        """)
        
        if not is_logged_in_now:
            print("✗ 로그인 상태를 확인할 수 없습니다. 프로그램을 종료합니다.")
            context.close()
            return

        js_click_mission = """
        (missionText) => {
            const normalize = t => (t || '').replace(/\s+/g, '').toLowerCase();
            const target = normalize(missionText);
            const elements = Array.from(document.querySelectorAll('*'));
            const titleEls = elements.filter(el => normalize(el.textContent).includes(target) && el.children.length === 0);
            if (titleEls.length === 0) return false;
            let parent = titleEls[0].parentElement;
            while (parent && parent !== document.body) {
                const btns = Array.from(parent.querySelectorAll('button, a'));
                const btn = btns.find(b => normalize(b.textContent).includes('미션하기'));
                if (btn) {
                    btn.click();
                    return true;
                }
                parent = parent.parentElement;
            }
            return false;
        }
        """

        # 1. My 홈 방문하기 자동 탭 닫기
        try:
            if page.evaluate(js_check_mission, "My 홈 방문하기"):
                print(">> 'My 홈 방문하기' 미션을 수행합니다...")
                with context.expect_page(timeout=5000) as new_page_info:
                    page.evaluate(js_click_mission, "My 홈 방문하기")
                new_page = new_page_info.value
                try:
                    new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                
                print(">> 방문 기록 갱신을 위해 3초 대기합니다...")
                new_page.wait_for_timeout(3000)
                new_page.close()
                print(">> 새 탭을 닫았습니다.")
                page.wait_for_timeout(3000)
        except Exception:
            pass

        # 2. 스토브 메인 방문하기 자동 탭 닫기
        try:
            if page.evaluate(js_check_mission, "스토브 메인 방문하기"):
                print(">> '스토브 메인 방문하기' 미션을 수행합니다...")
                with context.expect_page(timeout=5000) as new_page_info:
                    page.evaluate(js_click_mission, "스토브 메인 방문하기")
                new_page = new_page_info.value
                try:
                    new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                
                print(">> 방문 기록 갱신을 위해 3초 대기합니다...")
                new_page.wait_for_timeout(3000)
                new_page.close()
                print(">> 새 탭을 닫았습니다.")
                page.wait_for_timeout(3000)
        except Exception:
            pass

        # 3. 라운지 글쓰기 자동 미션
        try:
            if page.evaluate(js_check_mission, "라운지 글쓰기"):
                print(">> '라운지 글쓰기' 미션을 수행합니다...")
                with context.expect_page(timeout=5000) as new_page_info:
                    page.evaluate(js_click_mission, "라운지 글쓰기")
                new_page = new_page_info.value
                try:
                    new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                
                print(">> 게시글 작성을 시작합니다...")
                new_page.wait_for_timeout(2000)
                
                # '오늘의 생각을 공유해 보세요' 클릭하여 포커스
                try:
                    new_page.locator("text=오늘의 생각을 공유해 보세요").first.click(timeout=5000)
                except Exception:
                    new_page.locator("[placeholder*='오늘의 생각을 공유해 보세요']").first.click(timeout=5000)
                new_page.wait_for_timeout(1000)
                
                print(">> 글 제목과 내용을 입력합니다...")
                new_page.locator("[placeholder*='제목을 입력해 주세요']").first.fill("a")
                
                # 본문 작성 (에디터 구조 변화에 대응하기 위해 contenteditable 혹은 Tab 키 이동 사용)
                try:
                    new_page.locator("[contenteditable='true']").first.click(timeout=3000)
                    new_page.keyboard.type("a")
                except Exception:
                    new_page.locator("[placeholder*='제목을 입력해 주세요']").first.click(timeout=2000)
                    new_page.keyboard.press("Tab")
                    new_page.keyboard.type("a")
                new_page.wait_for_timeout(1000)
                
                print(">> 게시글을 등록합니다...")
                new_page.locator("button:has-text('등록')").first.click(timeout=5000)
                
                print(">> 게시글 등록 완료 대기 중 (약 4초)...")
                new_page.wait_for_timeout(4000)
                
                print(">> 게시글 하단의 하트(좋아요)를 클릭합니다...")
                new_page.evaluate("""
                    () => {
                        const btns = Array.from(document.querySelectorAll('button, a'));
                        const heartBtn = btns.find(b => {
                            if (b.innerText.includes('좋아요') || b.innerText.includes('추천')) return true;
                            if (b.className && typeof b.className === 'string' && b.className.toLowerCase().includes('like')) return true;
                            const html = b.innerHTML.toLowerCase();
                            return html.includes('heart') || html.includes('좋아요');
                        });
                        if (heartBtn) { heartBtn.click(); }
                    }
                """)
                new_page.wait_for_timeout(1500)
                
                print(">> 댓글을 작성합니다...")
                try:
                    new_page.locator("[placeholder*='댓글을 달아보세요']").first.fill("a", timeout=3000)
                except Exception:
                    new_page.locator("text=댓글을 달아보세요").first.click()
                    new_page.keyboard.type("a")
                new_page.wait_for_timeout(1000)
                
                print(">> 댓글을 등록합니다...")
                try:
                    # 클릭 가능한(활성화된) 가시적 '등록' 버튼을 확실하게 찾아 클릭
                    new_page.evaluate("""
                        () => {
                            const btns = Array.from(document.querySelectorAll('button, a, span'));
                            const submitBtns = btns.filter(b => 
                                b.innerText.trim() === '등록' && 
                                b.offsetParent !== null && 
                                !b.disabled &&
                                !String(b.className).includes('disabled')
                            );
                            if (submitBtns.length > 0) {
                                submitBtns[submitBtns.length - 1].click();
                            }
                        }
                    """)
                except Exception:
                    new_page.locator("button:has-text('등록')").filter(state="visible").last.click(timeout=5000)
                new_page.wait_for_timeout(3000)
                
                print(">> 수행 기록 갱신을 위해 2초 대기합니다...")
                new_page.wait_for_timeout(2000)
                new_page.close()
                print(">> 새 탭을 닫았습니다.")
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[경고] 라운지 글쓰기 미션 중 오류: {e}")

        # 모든 탭 닫기/미션이 완료되었으므로, 현재(기존) 탭을 새로고침
        print(">> 페이지를 새로고침하여 미션 상태를 갱신합니다...")
        try:
            page.reload(timeout=10000)
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        # 4. 모든 '받기' 버튼 클릭
        js_click_receive = """
        async () => {
            let clicked = 0;
            const btns = Array.from(document.querySelectorAll('button, a'));
            const receiveBtns = btns.filter(b => b.textContent.trim() === '받기');
            for (const btn of receiveBtns) {
                try { 
                    btn.click(); 
                    clicked++; 
                    await new Promise(r => setTimeout(r, 1500));
                } catch(e) {}
            }
            return clicked;
        }
        """
        try:
            print(">> 수령 가능한 모든 '받기' 버튼을 클릭합니다...")
            receive_count = page.evaluate(js_click_receive)
            if receive_count > 0:
                print(f">> {receive_count}개의 '받기' 버튼을 클릭하여 보상을 수령했습니다!")
                page.wait_for_timeout(2000)
            else:
                print(">> 누를 수 있는 '받기' 버튼이 없습니다.")
        except Exception:
            pass

        print("\n모든 자동 미션 작업이 완료되었습니다.")
        
        # 현재 쿠키를 저장소에 명시적으로 저장
        try:
            cookies = context.cookies()
            import json
            cookies_file = os.path.join(base_dir, "cookies.json")
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2)
            print(f"[디버그] 쿠키가 저장되었습니다: {cookies_file}")
            print(f"[디버그] 저장된 쿠키 수: {len(cookies)}")
        except Exception as e:
            print(f"[경고] 쿠키 저장 중 오류 발생: {e}")
        
        print("창을 닫을 때까지 대기합니다...")
        
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
        open_onstove()
    except Exception as main_e:
        print("\n==================================")
        print("프로그램 실행 중 치명적인 오류가 발생했습니다.")
        print("==================================")
        traceback.print_exc()
    finally:
        print("\n\n모든 작업이 끝났습니다.")
        input("터미널 창을 닫으려면 엔터 키를 누르세요...")
