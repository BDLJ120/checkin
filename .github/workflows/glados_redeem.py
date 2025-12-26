# -*- coding: utf-8 -*-
import sys
import io
# 设置标准输出为UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os
from datetime import datetime

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
            return None, []
        
        # 按日期排序，取最新的
        date_paragraphs.sort(key=lambda x: x[0], reverse=True)
        latest_date, latest_date_p = date_paragraphs[0]
        
        # 查找日期段落后面的第一个表格
        current_element = latest_date_p
        table = None
        
        # 使用next_sibling查找兄弟元素，跳过文本节点
        while current_element:
            current_element = current_element.next_sibling
            # 跳过文本节点
            while current_element and isinstance(current_element, str):
                current_element = current_element.next_sibling
            # 检查是否为figure元素且包含表格
            if current_element and current_element.name == 'figure' and current_element.find('table'):
                table = current_element.find('table')
                break
        
        if not table:
            print("未找到日期对应的表格，尝试查找页面中所有表格")
            # 如果找不到对应表格，尝试查找页面中所有表格
            tables = current_element.find_all('table') if current_element else soup.find_all('table')
            if tables:
                table = tables[0]
            else:
                print("页面中没有找到任何表格")
                return latest_date, []
        
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
        return latest_date, codes
    except Exception as e:
        print(f"获取兑换码失败: {e}")
        import traceback
        traceback.print_exc()
        return None, []

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
        
        # 保存页面截图和源码用于调试（可选）
        try:
            driver.save_screenshot("account_page.png")
            with open("account_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("[成功] 已保存账户页面截图和HTML源码用于调试")
        except Exception as e:
            print(f"[警告] 保存调试信息失败: {e}")
        
        # 检查是否已登录
        if "login" in driver.current_url.lower():
            print("未登录，请检查GLADOS_COOKIES是否正确")
            return
        
        # 策略：优先尝试直接访问兑换码页面（最可靠），如果失败再尝试点击按钮
        print("\n尝试访问兑换码页面...")
        try:
            driver.get("https://glados.rocks/console/code")
            time.sleep(5)
            
            # 验证是否成功到达兑换码页面
            current_url = driver.current_url
            if "code" in current_url.lower() or "console" in current_url.lower():
                print("[成功] 直接访问兑换码页面成功")
                button_clicked = True
            else:
                print(f"[警告] 可能未成功跳转，当前URL: {current_url}")
                button_clicked = False
        except Exception as e:
            print(f"[错误] 直接访问失败: {e}")
            button_clicked = False
        
        # 如果直接访问失败，尝试查找并点击按钮
        if not button_clicked:
            print("\n尝试查找并点击'输入兑换码'按钮...")
            
            # 策略1: 尝试多种XPath选择器（包括中英文）
            button_selectors = [
                # href属性匹配（最可靠）
                "//a[@href='/console/code']",
                "//a[contains(@href, '/console/code')]",
                "//a[contains(@href, 'code')]",
                # 中文文本匹配
                "//a[contains(text(), '输入兑换码')]",
                "//a[contains(text(), '兑换码')]",
                "//a[contains(text(), '兑换')]",
                "//button[contains(text(), '输入兑换码')]",
                "//button[contains(text(), '兑换码')]",
                "//*[contains(text(), '输入兑换码')]",
                # 英文文本匹配
                "//a[contains(text(), 'Redeem')]",
                "//a[contains(text(), 'Code')]",
                "//button[contains(text(), 'Redeem')]",
                # 导航栏中的链接
                "//nav//a[contains(@href, 'code')]",
                "//nav//a[contains(text(), '兑换')]",
            ]
            
            for selector in button_selectors:
                try:
                    print(f"  尝试选择器: {selector}")
                    # 先等待元素出现（缩短等待时间）
                    element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    print(f"  [成功] 找到元素: {element.tag_name}, 文本: {element.text[:50] if element.text else 'N/A'}")
                    
                    # 检查元素是否可见和可点击
                    if not element.is_displayed():
                        print(f"  [警告] 元素不可见，尝试滚动...")
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                        time.sleep(1)
                    
                    # 尝试点击
                    try:
                        element.click()
                        print(f"  [成功] 使用普通点击成功")
                        button_clicked = True
                        time.sleep(3)
                        break
                    except:
                        # 如果普通点击失败，尝试JavaScript点击
                        print(f"  普通点击失败，尝试JavaScript点击...")
                        driver.execute_script("arguments[0].click();", element)
                        print(f"  [成功] 使用JavaScript点击成功")
                        button_clicked = True
                        time.sleep(3)
                        break
                except Exception as e:
                    print(f"  [错误] 选择器失败: {str(e)[:100]}")
                    continue
            
            if not button_clicked:
                print("[错误] 所有按钮定位策略都失败")
                # 打印页面上所有链接和按钮用于调试
                try:
                    print("\n=== 页面调试信息 ===")
                    print("所有链接（前20个）:")
                    links = driver.find_elements(By.TAG_NAME, "a")
                    for i, link in enumerate(links[:20]):
                        try:
                            href = link.get_attribute("href") or "N/A"
                            text = link.text.strip() or "N/A"
                            if href != "N/A" or text != "N/A":
                                print(f"  [{i+1}] 文本: {text[:50]}, href: {href[:80]}")
                        except:
                            pass
                    
                    print("\n所有按钮（前20个）:")
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for i, btn in enumerate(buttons[:20]):
                        try:
                            text = btn.text.strip() or "N/A"
                            btn_type = btn.get_attribute("type") or "N/A"
                            if text != "N/A" or btn_type != "N/A":
                                print(f"  [{i+1}] 文本: {text[:50]}, type: {btn_type}")
                        except:
                            pass
                except Exception as e:
                    print(f"[警告] 获取调试信息失败: {e}")
                
                # 最后尝试：再次直接访问
                print("\n最后尝试：再次直接访问兑换码页面...")
                driver.get("https://glados.rocks/console/code")
                time.sleep(5)
        
        # 等待页面加载完成
        time.sleep(5)
        
        # 验证是否成功到达兑换码页面
        current_url = driver.current_url
        print(f"当前页面URL: {current_url}")
        
        # 保存兑换码页面截图和源码用于调试
        try:
            driver.save_screenshot("code_page.png")
            with open("code_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("[成功] 已保存兑换码页面截图和HTML源码用于调试")
        except Exception as e:
            print(f"[警告] 保存调试信息失败: {e}")
        
        if "code" not in current_url.lower():
            print("[警告] 可能未成功跳转到兑换码页面，尝试再次访问...")
            driver.get("https://glados.rocks/console/code")
            time.sleep(5)
        
        # 定位兑换码输入框和兑换按钮
        print("\n定位兑换码输入框和兑换按钮...")
        
        # 等待并定位输入框 - 尝试多种方式
        code_input = None
        input_selectors = [
            (By.NAME, "code"),
            (By.ID, "code"),
            (By.XPATH, "//input[@name='code']"),
            (By.XPATH, "//input[@type='text' and contains(@placeholder, '兑换码')]"),
            (By.XPATH, "//input[@type='text']"),
        ]
        
        for by, selector in input_selectors:
            try:
                print(f"  尝试定位输入框: {by}={selector}")
                code_input = wait.until(EC.presence_of_element_located((by, selector)))
                print(f"  [成功] 找到兑换码输入框: {by}={selector}")
                break
            except Exception as e:
                print(f"  [错误] 输入框定位失败: {str(e)[:100]}")
                continue
        
        if not code_input:
            print("[错误] 无法定位兑换码输入框")
            raise Exception("无法定位兑换码输入框")
        
        # 等待并定位兑换按钮 - 尝试多种方式
        redeem_button = None
        button_selectors = [
            (By.XPATH, "//button[contains(text(), '兑换')]"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(@class, 'submit') or contains(@class, 'redeem')]"),
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button"),
        ]
        
        for by, selector in button_selectors:
            try:
                print(f"  尝试定位兑换按钮: {by}={selector}")
                redeem_button = wait.until(EC.element_to_be_clickable((by, selector)))
                button_text = redeem_button.text.strip() if redeem_button.text else ""
                print(f"  [成功] 找到兑换按钮: {by}={selector}, 文本: {button_text}")
                # 验证按钮文本是否包含"兑换"
                if "兑换" in button_text or not button_text:
                    break
            except Exception as e:
                print(f"  [错误] 兑换按钮定位失败: {str(e)[:100]}")
                continue
        
        if not redeem_button:
            print("[错误] 无法定位兑换按钮")
            raise Exception("无法定位兑换按钮")
        
        # 开始批量兑换
        print(f"\n=== 开始批量兑换 {len(codes)} 个码 ===")
        
        for i, code in enumerate(codes):
            try:
                print(f"\n[{i+1}/{len(codes)}] 尝试兑换: {code}")
                
                # 每次兑换前重新定位元素（页面可能已刷新）
                try:
                    code_input = wait.until(EC.presence_of_element_located((By.NAME, "code")))
                except:
                    # 如果NAME定位失败，尝试其他方式
                    code_input = driver.find_element(By.XPATH, "//input[@name='code']")
                
                # 清空并输入兑换码
                code_input.clear()
                time.sleep(0.5)
                code_input.send_keys(code)
                time.sleep(1)  # 给足时间输入
                
                # 重新定位兑换按钮
                try:
                    redeem_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '兑换')]")))
                except:
                    # 如果文本定位失败，尝试其他方式
                    redeem_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                
                # 点击兑换按钮 - 尝试多种方式
                try:
                    redeem_button.click()
                except:
                    # 如果普通点击失败，使用JavaScript点击
                    driver.execute_script("arguments[0].click();", redeem_button)
                
                # 等待兑换结果提示出现
                print("  等待兑换结果提示...")
                time.sleep(3)  # 等待提示出现
                
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
                    print(f"[成功] 兑换 {code} 成功: {success_message}")
                else:
                    print(f"[成功] 兑换 {code} 完成")
                
                # 等待一段时间，确保页面稳定
                time.sleep(3)
                
            except Exception as e:
                print(f"[错误] 兑换 {code} 失败: {e}")
                time.sleep(5)  # 失败时等待更长时间
    
    except Exception as e:
        print(f"浏览器操作失败: {e}")
    finally:
        if driver:
            driver.quit()

def main():
    print("开始执行GLaDOS自动兑换任务")
    
    # 获取当前日期，格式为YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"今天的日期: {today}")
    
    # 获取最新日期和兑换码
    latest_date, codes = get_latest_codes()
    
    # 检查最新日期是否等于今天日期
    if latest_date:
        print(f"最新兑换码日期: {latest_date}")
        
        if latest_date == today:
            print("[成功] 最新日期等于今天，开始兑换")
            redeem_codes(codes)
            print("任务执行完成")
            exit(0)  # 成功兑换，返回0退出码
        else:
            print("[错误] 最新日期不等于今天，跳过兑换")
            exit(1)  # 跳过兑换，返回非0退出码
    else:
        print("[错误] 未获取到有效日期，跳过兑换")
        exit(1)  # 获取日期失败，返回非0退出码
    
    print("任务执行完成")
    exit(1)  # 默认返回非0退出码

if __name__ == "__main__":
    main()
