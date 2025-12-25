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
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        # 访问兑换页面
        driver.get("https://glados.rocks/console/account")
        
        # 添加cookies（如果存在）
        glados_cookies = os.getenv('GLADOS_COOKIES')
        if glados_cookies:
            print("正在添加cookies...")
            # 先访问主页以初始化域名
            driver.get("https://glados.rocks/")
            time.sleep(2)
            # 解析cookies字符串，格式：key1=value1; key2=value2
            cookie_pairs = glados_cookies.split(';')
            for cookie_pair in cookie_pairs:
                cookie_pair = cookie_pair.strip()
                if '=' in cookie_pair:
                    key, value = cookie_pair.split('=', 1)
                    try:
                        driver.add_cookie({'name': key, 'value': value, 'domain': '.glados.rocks'})
                    except Exception as e:
                        print(f"添加cookie失败: {e}")
            # 重新访问兑换页面
            driver.get("https://glados.rocks/console/account")
        
        # 等待页面加载
        time.sleep(5)
        
        # 检查是否已登录
        if "login" in driver.current_url.lower():
            print("未登录，请在GitHub Secrets中设置GLADOS_COOKIES")
            return
        
        # 尝试获取兑换码输入框
        for code in codes:
            try:
                print(f"尝试兑换: {code}")
                
                # 查找兑换码输入框
                code_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='兑换码'], input[placeholder*='Redeem']"))
                )
                
                # 清空并输入兑换码
                code_input.clear()
                code_input.send_keys(code)
                
                # 查找兑换按钮
                redeem_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '兑换') or contains(text(), 'Redeem')]"))
                )
                
                # 点击兑换按钮
                redeem_button.click()
                
                # 等待兑换结果
                time.sleep(3)
                
                # 检查兑换结果
                try:
                    # 查找可能的成功或失败提示
                    success_msg = driver.find_element(By.XPATH, "//div[contains(text(), '成功') or contains(text(), 'Success')]")
                    if success_msg:
                        print(f"兑换 {code} 成功")
                except:
                    try:
                        error_msg = driver.find_element(By.XPATH, "//div[contains(text(), '失败') or contains(text(), 'Error') or contains(text(), '无效')]")
                        if error_msg:
                            print(f"兑换 {code} 失败: {error_msg.text}")
                    except:
                        print(f"兑换 {code} 完成（无法确认结果）")
                
            except Exception as e:
                print(f"兑换 {code} 失败: {e}")
                # 刷新页面重试
                if driver:
                    driver.refresh()
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
