# -*- coding: utf-8 -*-
import sys
import io
# 设置标准输出为UTF-8编码（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime
import json

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
    """
    使用API方式批量兑换GLaDOS兑换码
    
    @param {string[]} codes - 要兑换的兑换码列表
    """
    if not codes:
        print("没有可兑换的码")
        return
    
    # 获取cookies
    default_cookies = "__stripe_mid=9907a4bf-76fd-4d64-b7b0-1a69a060ed1fcaf17b; _ga=GA1.1.1748889280.1693378985; _ga_CZFVKMNT9J=GS1.1.1735090741.53.1.1735090809.0.0.0; koa:sess=eyJ1c2VySWQiOjE1NTc1NSwiX2V4cGlyZSI6MTc4MDkwOTY2MTY1MSwiX21heEFnZSI6MjU5MjAwMDAwMDB9; koa:sess.sig=NqnPtBj7OPYakoMsEoGAsuJflwk"
    glados_cookies = os.getenv('GLADOS_COOKIES', default_cookies)
    
    # 设置请求头
    headers = {
        'cookie': glados_cookies,
        'referer': 'https://glados.rocks/console/code',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://glados.rocks',
    }
    
    # 创建session以保持cookies
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # 验证cookies是否有效 - 先尝试获取用户状态
        print("验证cookies有效性...")
        try:
            status_response = session.get('https://glados.rocks/api/user/status', timeout=10)
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get('code') == 0:
                    print(f"[成功] Cookies有效，用户ID: {status_data.get('data', {}).get('email', 'N/A')}")
                else:
                    print(f"[警告] Cookies可能无效: {status_data.get('message', '未知错误')}")
            else:
                print(f"[警告] 验证cookies失败，状态码: {status_response.status_code}")
        except Exception as e:
            print(f"[警告] 验证cookies时出错: {e}")
        
        # 开始批量兑换
        print(f"\n=== 开始批量兑换 {len(codes)} 个码 ===")
        
        # 尝试多个可能的API端点
        api_endpoints = [
            'https://glados.rocks/api/user/redeem',
            'https://glados.rocks/api/user/redeemCode',
            'https://glados.rocks/api/redeem',
        ]
        
        successful_endpoint = None
        
        # 先测试第一个端点是否可用
        for endpoint in api_endpoints:
            try:
                # 测试请求（使用第一个码）
                test_response = session.post(
                    endpoint,
                    json={'code': codes[0]},
                    timeout=10
                )
                if test_response.status_code in [200, 201]:
                    successful_endpoint = endpoint
                    print(f"[成功] 找到可用的API端点: {endpoint}")
                    break
            except Exception as e:
                print(f"[警告] 测试端点 {endpoint} 失败: {e}")
                continue
        
        if not successful_endpoint:
            # 如果所有端点都失败，尝试使用第一个端点（可能是参数格式不同）
            successful_endpoint = api_endpoints[0]
            print(f"[警告] 无法确定API端点，使用默认端点: {successful_endpoint}")
        
        # 批量兑换
        for i, code in enumerate(codes):
            try:
                print(f"\n[{i+1}/{len(codes)}] 尝试兑换: {code}")
                
                # 尝试不同的请求体格式
                request_bodies = [
                    {'code': code},
                    {'redeemCode': code},
                    {'redeem_code': code},
                    {'code': code, 'token': 'glados.one'},
                ]
                
                redeemed = False
                for body in request_bodies:
                    try:
                        response = session.post(
                            successful_endpoint,
                            json=body,
                            timeout=15
                        )
                        
                        # 解析响应
                        try:
                            result = response.json()
                        except:
                            result = {'message': response.text[:200]}
                        
                        # 检查响应状态
                        if response.status_code in [200, 201]:
                            if result.get('code') == 0 or 'success' in str(result).lower():
                                print(f"  [成功] 兑换成功: {result.get('message', '兑换码已使用')}")
                                redeemed = True
                                break
                            elif result.get('code') == -1 or 'error' in str(result).lower():
                                error_msg = result.get('message', '未知错误')
                                print(f"  [失败] 兑换失败: {error_msg}")
                                # 如果是已使用或无效的码，继续下一个
                                if 'already' in error_msg.lower() or 'used' in error_msg.lower() or 'invalid' in error_msg.lower():
                                    redeemed = True  # 标记为已处理，不再尝试其他格式
                                break
                            else:
                                print(f"  [信息] 响应: {result}")
                        else:
                            print(f"  [警告] HTTP状态码: {response.status_code}, 响应: {result}")
                            
                    except requests.exceptions.Timeout:
                        print(f"  [错误] 请求超时")
                        continue
                    except Exception as e:
                        print(f"  [错误] 请求失败: {e}")
                        continue
                
                if not redeemed:
                    print(f"  [警告] 所有请求格式都失败，跳过此码")
                
                # 避免请求过快
                time.sleep(2)
                
            except Exception as e:
                print(f"[错误] 兑换 {code} 失败: {e}")
                time.sleep(2)
    
    except Exception as e:
        print(f"[错误] API操作失败: {e}")
        import traceback
        traceback.print_exc()

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
