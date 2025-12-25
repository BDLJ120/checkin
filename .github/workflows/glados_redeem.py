import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os

def get_latest_codes():
    url = "https://kerrynotes.com/glados-redeem-code/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找所有包含日期的段落
        date_paragraphs = []
        paragraphs = soup.find_all('p')
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and len(text) >= 10:
                # 检查是否为日期格式，如 2025-12-23:
                if text[-1] == ':' and text.count('-') == 2:
                    date_text = text[:-1].strip()  # 去除冒号
                    if len(date_text) == 10:
                        date_paragraphs.append((date_text, p))
        
        if not date_paragraphs:
            print("未找到日期段落")
            return []
        
        # 按日期排序，取最新的
        date_paragraphs.sort(key=lambda x: x[0], reverse=True)
        latest_date, latest_date_p = date_paragraphs[0]
        
        # 查找日期段落后面的第一个表格
        current_element = latest_date_p
        table = None
        
        while current_element:
            if current_element.name == 'figure' and current_element.find('table'):
                table = current_element.find('table')
                break
            current_element = current_element.next_element
        
        if not table:
            print("未找到日期对应的表格")
            return []
        
        # 提取兑换码
        codes = []
        rows = table.find_all('tr')
        
        for row in rows[1:]:  # 跳过表头
            cells = row.find_all('td')
            if cells:
                code = cells[0].get_text(strip=True)
                if code and len(code) >= 20 and '-' in code:
                    codes.append(code)
        
        print(f"获取到最新日期 {latest_date} 的兑换码: {codes}")
        return codes
    except Exception as e:
        print(f"获取兑换码失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def redeem_codes(codes):
    if not codes:
        print("没有可兑换的码")
        return
    
    driver = None
    
    try:
        # 配置Chrome选项，优化GitHub Actions环境下的运行
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--remote-debugging-port=9222')
        
        # 尝试使用不同的方式初始化Chrome
        from selenium.webdriver.chrome.service import Service
        import shutil
        
        # 查找chromedriver路径
        chromedriver_path = shutil.which('chromedriver') or shutil.which('chromium-chromedriver')
        
        # 查找Chrome/Chromium二进制路径
        chrome_binary_path = None
        possible_chrome_paths = [
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/usr/bin/google-chrome',
            '/usr/local/bin/chrome',
            '/opt/google/chrome/chrome'
        ]
        
        for path in possible_chrome_paths:
            if shutil.which(path):
                chrome_binary_path = path
                break
        
        if chrome_binary_path:
            print(f"找到Chrome二进制路径: {chrome_binary_path}")
            chrome_options.binary_location = chrome_binary_path
        
        if chromedriver_path:
            print(f"找到chromedriver路径: {chromedriver_path}")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            print("未找到chromedriver，尝试使用webdriver-manager")
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.implicitly_wait(15)
        wait = WebDriverWait(driver, 20)
        
        # 访问主页
        print("访问GLaDOS主页...")
        driver.get("https://glados.rocks/")
        time.sleep(5)
        
        # 添加cookies（如果存在）
        glados_cookies = os.getenv('GLADOS_COOKIES')
        if glados_cookies:
            print("正在添加cookies...")
            # 解析cookies字符串
            cookie_pairs = glados_cookies.split(';')
            added_cookies = 0
            
            for cookie_pair in cookie_pairs:
                cookie_pair = cookie_pair.strip()
                if '=' in cookie_pair:
                    key, value = cookie_pair.split('=', 1)
                    try:
                        # 只添加有效的cookie
                        if key and value:
                            driver.add_cookie({'name': key.strip(), 'value': value.strip(), 'domain': '.glados.rocks'})
                            added_cookies += 1
                    except Exception as e:
                        print(f"添加cookie {key} 失败: {e}")
            
            print(f"成功添加 {added_cookies} 个cookies")
        
        # 访问兑换页面
        print("访问兑换页面...")
        driver.get("https://glados.rocks/console/account")
        time.sleep(10)
        
        # 检查是否已登录
        if "login" in driver.current_url.lower():
            print("未登录，请检查GLADOS_COOKIES是否正确")
            # 保存页面截图用于调试
            driver.save_screenshot("login_fail.png")
            return
        
        # 打印当前页面标题和URL，用于调试
        print(f"当前页面标题: {driver.title}")
        print(f"当前页面URL: {driver.current_url}")
        
        # 尝试获取兑换码输入框和兑换按钮
        for code in codes:
            try:
                print(f"\n=== 尝试兑换: {code} ===")
                
                # 刷新页面，确保状态一致
                driver.refresh()
                time.sleep(8)
                
                # 多种方式查找兑换码输入框
                code_input = None
                input_locators = [
                    By.XPATH, "//input[contains(@placeholder, '兑换码') or contains(@placeholder, 'Redeem')]",
                    By.CSS_SELECTOR, "input[type='text']",
                    By.XPATH, "//form//input"
                ]
                
                for i in range(0, len(input_locators), 2):
                    by = input_locators[i]
                    locator = input_locators[i+1]
                    try:
                        print(f"尝试定位兑换码输入框: {by}={locator}")
                        code_input = wait.until(EC.presence_of_element_located((by, locator)))
                        print("找到兑换码输入框")
                        break
                    except Exception as e:
                        print(f"定位失败: {e}")
                        continue
                
                if not code_input:
                    print("未找到兑换码输入框")
                    # 保存页面截图和源代码
                    driver.save_screenshot(f"no_input_{code[:8]}.png")
                    with open(f"page_source_{code[:8]}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    continue
                
                # 清空并输入兑换码
                code_input.clear()
                time.sleep(1)
                code_input.send_keys(code)
                time.sleep(2)
                
                # 多种方式查找兑换按钮
                redeem_button = None
                button_locators = [
                    By.XPATH, "//button[contains(text(), '兑换') or contains(text(), 'Redeem')]",
                    By.CSS_SELECTOR, "button[type='submit']",
                    By.XPATH, "//form//button"
                ]
                
                for i in range(0, len(button_locators), 2):
                    by = button_locators[i]
                    locator = button_locators[i+1]
                    try:
                        print(f"尝试定位兑换按钮: {by}={locator}")
                        redeem_button = wait.until(EC.element_to_be_clickable((by, locator)))
                        print("找到兑换按钮")
                        break
                    except Exception as e:
                        print(f"定位失败: {e}")
                        continue
                
                if not redeem_button:
                    print("未找到兑换按钮")
                    continue
                
                # 点击兑换按钮
                print("点击兑换按钮...")
                redeem_button.click()
                time.sleep(5)
                
                # 检查兑换结果
                success = False
                try:
                    # 查找成功提示
                    success_msg = driver.find_element(By.XPATH, "//div[contains(text(), '成功') or contains(text(), 'Success') or contains(text(), 'success')]")
                    if success_msg:
                        print(f"✅ 兑换 {code} 成功")
                        success = True
                except Exception as e:
                    print(f"检查成功提示失败: {e}")
                    try:
                        # 查找失败提示
                        error_msg = driver.find_element(By.XPATH, "//div[contains(text(), '失败') or contains(text(), 'Error') or contains(text(), 'error') or contains(text(), '无效')]")
                        if error_msg:
                            print(f"❌ 兑换 {code} 失败: {error_msg.text}")
                    except Exception as e2:
                        print(f"检查失败提示失败: {e2}")
                        # 没有明确提示，可能成功
                        print(f"ℹ️ 兑换 {code} 完成，无法确认结果")
                
                # 等待一段时间后继续
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ 兑换 {code} 失败: {e}")
                import traceback
                traceback.print_exc()
                # 保存页面截图用于调试
                if driver:
                    driver.save_screenshot(f"error_{code[:8]}.png")
                time.sleep(5)
    
    except Exception as e:
        print(f"浏览器操作失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

def main():
    print("开始执行GLaDOS自动兑换任务")
    codes = get_latest_codes()
    redeem_codes(codes)
    print("任务执行完成")

if __name__ == "__main__":
    main()
