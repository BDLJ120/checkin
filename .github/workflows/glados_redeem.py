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
        # 配置Chrome选项，优化运行速度和稳定性
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--enable-javascript')
        
        # 初始化Chrome驱动
        from selenium.webdriver.chrome.service import Service
        import shutil
        
        # 查找chromedriver和Chrome二进制路径
        chromedriver_path = shutil.which('chromedriver') or shutil.which('chromium-chromedriver')
        chrome_binary_path = shutil.which('chromium-browser') or shutil.which('chromium') or shutil.which('google-chrome')
        
        if chrome_binary_path:
            chrome_options.binary_location = chrome_binary_path
        
        # 初始化driver
        if chromedriver_path:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 设置等待时间
        driver.implicitly_wait(10)
        wait = WebDriverWait(driver, 20)
        
        # 访问GLaDOS主页建立会话
        print("访问GLaDOS主页...")
        driver.get("https://glados.rocks/")
        time.sleep(3)
        
        # 添加cookies
        default_cookies = "__stripe_mid=9907a4bf-76fd-4d64-b7b0-1a69a060ed1fcaf17b; _ga=GA1.1.1748889280.1693378985; _ga_CZFVKMNT9J=GS1.1.1735090741.53.1.1735090809.0.0.0; koa:sess=eyJ1c2VySWQiOjE1NTc1NSwiX2V4cGlyZSI6MTc4MDkwOTY2MTY1MSwiX21heEFnZSI6MjU5MjAwMDAwMDB9; koa:sess.sig=NqnPtBj7OPYakoMsEoGAsuJflwk"
        glados_cookies = os.getenv('GLADOS_COOKIES', default_cookies)
        
        # 解析cookies字符串
        cookie_pairs = glados_cookies.split(';')
        added_cookies = 0
        
        for cookie_pair in cookie_pairs:
            cookie_pair = cookie_pair.strip()
            if '=' in cookie_pair:
                key, value = cookie_pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    try:
                        cookie = {
                            'name': key,
                            'value': value,
                            'domain': '.glados.rocks',
                            'path': '/',
                            'secure': True,
                            'httpOnly': key in ['koa:sess', 'koa:sess.sig'],
                            'sameSite': 'Lax'
                        }
                        driver.add_cookie(cookie)
                        added_cookies += 1
                    except:
                        pass  # 忽略cookie添加失败
        
        print(f"成功添加 {added_cookies} 个cookies")
        
        # 访问账户页面
        print("\n访问账户页面...")
        driver.get("https://glados.rocks/console/account")
        time.sleep(10)  # 等待页面加载
        
        # 检查是否已登录
        if "login" in driver.current_url.lower():
            print("未登录，请检查GLADOS_COOKIES是否正确")
            return
        
        # 查找并点击"输入兑换码"按钮
        print("\n查找并点击'输入兑换码'按钮...")
        try:
            redeem_code_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '输入兑换码')]")))
            redeem_code_button.click()
            time.sleep(10)  # 等待页面切换
            print("✅ 点击'输入兑换码'按钮成功")
        except Exception as e:
            print(f"❌ 点击'输入兑换码'按钮失败: {e}")
            # 尝试直接访问兑换码页面
            driver.get("https://glados.rocks/console/code")
            time.sleep(10)
        
        # 定位兑换码输入框和兑换按钮
        print("\n定位兑换码输入框和兑换按钮...")
        
        # 等待并定位输入框
        code_input = wait.until(EC.presence_of_element_located((By.NAME, "code")))
        print("✅ 找到兑换码输入框")
        
        # 等待并定位兑换按钮
        redeem_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '兑换')]")))
        print("✅ 找到兑换按钮")
        
        # 开始批量兑换
        print(f"\n=== 开始批量兑换 {len(codes)} 个码 ===")
        
        for i, code in enumerate(codes):
            try:
                print(f"\n[{i+1}/{len(codes)}] 尝试兑换: {code}")
                
                # 清空并输入兑换码
                code_input.clear()
                code_input.send_keys(code)
                time.sleep(2)  # 给足时间输入
                
                # 点击兑换按钮
                redeem_button.click()
                
                # 等待兑换结果提示出现
                print("  等待兑换结果提示...")
                time.sleep(2)  # 等待提示出现
                
                # 尝试获取不同形式的提示信息
                success_message = None
                
                # 方式1: 查找页面上的消息提示元素
                try:
                    # 查找常见的消息提示元素
                    message_selectors = [
                        "//div[contains(@class, 'alert') or contains(@class, 'message') or contains(@class, 'toast')]",
                        "//div[@role='alert']",
                        "//div[contains(text(), '成功') or contains(text(), '失败') or contains(text(), '兑换')]",
                        "//span[contains(text(), '成功') or contains(text(), '失败') or contains(text(), '兑换')]",
                        "//p[contains(text(), '成功') or contains(text(), '失败') or contains(text(), '兑换')]"
                    ]
                    
                    for selector in message_selectors:
                        try:
                            message_element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                            message_text = message_element.text.strip()
                            if message_text:
                                success_message = message_text
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"  获取页面提示失败: {e}")
                
                # 方式2: 查找已使用的兑换码列表，查看是否有当前码
                if not success_message:
                    try:
                        used_codes_element = driver.find_element(By.XPATH, "//div[contains(text(), '已使用的兑换码')]/following-sibling::div")
                        used_codes_text = used_codes_element.text
                        if code in used_codes_text:
                            success_message = "兑换码已添加到已使用列表"
                    except Exception as e:
                        print(f"  获取已使用列表失败: {e}")
                
                # 方式3: 检查页面标题或URL变化
                if not success_message:
                    try:
                        # 检查页面是否有新的内容
                        page_source = driver.page_source
                        if "成功" in page_source:
                            success_message = "检测到页面包含成功信息"
                        elif "失败" in page_source:
                            success_message = "检测到页面包含失败信息"
                    except Exception as e:
                        print(f"  检查页面内容失败: {e}")
                
                # 打印结果
                if success_message:
                    print(f"✅ 兑换 {code} 成功: {success_message}")
                else:
                    print(f"✅ 兑换 {code} 完成")
                
                # 等待一段时间，确保页面稳定
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ 兑换 {code} 失败: {e}")
                time.sleep(5)  # 失败时等待更长时间
    
    except Exception as e:
        print(f"浏览器操作失败: {e}")
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
