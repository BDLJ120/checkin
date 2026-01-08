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
            if text and len(text) >= 8:
                # 支持多种日期格式
                # 格式1: 2025-12-23: 或 2026-1-6: (带冒号)
                # 格式2: 2025-12-23, 或 2026-1-6, (带逗号)
                # 格式3: 2025/12/23 或 2026/1/6 (使用斜杠)
                # 格式4: 2025.12.23 或 2026.1.6 (使用点号)
                # 格式5: 2025年12月23日 或 2026年1月6日 (中文格式)
                
                date_text = None
                separator = None
                
                # 检查是否以冒号或逗号结尾
                if text[-1] in [':', ',']:
                    potential_date = text[:-1].strip()
                else:
                    potential_date = text
                
                # 尝试不同的分隔符
                if '-' in potential_date and potential_date.count('-') == 2:
                    separator = '-'
                elif '/' in potential_date and potential_date.count('/') == 2:
                    separator = '/'
                elif '.' in potential_date and potential_date.count('.') == 2:
                    separator = '.'
                elif '年' in potential_date and '月' in potential_date and '日' in potential_date:
                    # 中文格式: 2026年1月6日
                    try:
                        year = int(potential_date.split('年')[0])
                        month = int(potential_date.split('月')[0].split('年')[1])
                        day = int(potential_date.split('日')[0].split('月')[1])
                        dt = datetime(year, month, day)
                        formatted_date = dt.strftime("%Y-%m-%d")
                        date_paragraphs.append((formatted_date, p))
                        continue
                    except (ValueError, IndexError):
                        continue
                
                if separator:
                    try:
                        parts = potential_date.split(separator)
                        if len(parts) == 3:
                            year = int(parts[0])
                            month = int(parts[1])
                            day = int(parts[2])
                            # 创建日期对象
                            dt = datetime(year, month, day)
                            # 转换为标准格式 YYYY-MM-DD
                            formatted_date = dt.strftime("%Y-%m-%d")
                            date_paragraphs.append((formatted_date, p))
                    except (ValueError, IndexError):
                        # 不是有效日期，跳过
                        continue
        
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
        
        # 使用正确的API端点（已通过测试确认）
        successful_endpoint = 'https://glados.rocks/api/user/code'
        print(f"[成功] 使用API端点: {successful_endpoint}")
        
        # 初始等待，避免立即触发频率限制
        print("等待3秒以避免频率限制...")
        time.sleep(3)
        
        # 批量兑换
        for i, code in enumerate(codes):
            try:
                print(f"\n[{i+1}/{len(codes)}] 尝试兑换: {code}")
                
                # 使用正确的请求体格式（已通过测试确认）
                request_bodies = [
                    {'code': code},  # 标准格式
                    {'code': code, 'token': 'glados.one'},  # 带token格式
                ]
                
                redeemed = False
                max_retries = 3  # 最大重试次数
                retry_count = 0
                
                # 使用POST请求，JSON格式（已确认的正确格式）
                for body in request_bodies:
                    if redeemed:
                        break
                    
                    retry_count = 0
                    while retry_count < max_retries:
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
                            
                            # 检查响应状态（API返回格式: {'code': 0或1或-2, 'message': '...'}）
                            if response.status_code == 200:
                                api_code = result.get('code')
                                api_message = result.get('message', '')
                                
                                if api_code == 0:
                                    # code=0 表示成功
                                    print(f"  [成功] 兑换成功: {api_message}")
                                    redeemed = True
                                    break
                                elif api_code == -2:
                                    # code=-2 表示已使用的兑换码
                                    print(f"  [信息] 兑换码已使用: {api_message}")
                                    redeemed = True  # 标记为已处理
                                    break
                                elif api_code == 1:
                                    # code=1 表示失败（如找不到码）
                                    error_msg = api_message
                                    print(f"  [失败] 兑换失败: {error_msg}")
                                    # 如果是已使用或无效的码，标记为已处理
                                    if 'already' in error_msg.lower() or 'used' in error_msg.lower() or 'invalid' in error_msg.lower() or 'can not find' in error_msg.lower():
                                        redeemed = True  # 标记为已处理，不再尝试其他格式
                                    break
                                else:
                                    print(f"  [信息] 响应: {result}")
                                    redeemed = True  # 未知状态码，标记为已处理
                                    break
                            elif response.status_code == 429:
                                # 429表示请求过于频繁，需要等待更长时间
                                retry_count += 1
                                wait_time = 10 * retry_count  # 递增等待时间
                                print(f"  [警告] 请求过于频繁（{retry_count}/{max_retries}），等待{wait_time}秒后重试...")
                                time.sleep(wait_time)
                                # 继续重试
                                continue
                            elif response.status_code == 404:
                                # 404说明端点不对，跳过
                                print(f"  [错误] API端点不存在")
                                break
                            else:
                                print(f"  [警告] HTTP状态码: {response.status_code}, 响应: {result}")
                                break
                                
                        except requests.exceptions.Timeout:
                            retry_count += 1
                            if retry_count < max_retries:
                                print(f"  [错误] 请求超时（{retry_count}/{max_retries}），等待5秒后重试...")
                                time.sleep(5)
                                continue
                            else:
                                print(f"  [错误] 请求超时，已达到最大重试次数")
                                break
                        except Exception as e:
                            print(f"  [错误] 请求失败: {e}")
                            break
                    
                    if redeemed:
                        break
                
                if not redeemed:
                    print(f"  [警告] 所有请求格式都失败，跳过此码")
                
                # 避免请求过快（增加延迟以避免429错误）
                # 如果遇到429错误，等待更长时间
                if i < len(codes) - 1:  # 不是最后一个码
                    wait_time = 5
                    print(f"  等待{wait_time}秒后继续下一个码...")
                    time.sleep(wait_time)
                
            except Exception as e:
                print(f"[错误] 兑换 {code} 失败: {e}")
                time.sleep(2)
    
    except Exception as e:
        print(f"[错误] API操作失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='GLaDOS自动兑换码脚本')
    parser.add_argument('-f', '--force', action='store_true', help='强制兑换所有获取到的码，不管日期是否匹配')
    args = parser.parse_args()
    
    print("开始执行GLaDOS自动兑换任务")
    
    # 获取当前日期，格式为YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"今天的日期: {today}")
    
    # 获取最新日期和兑换码
    latest_date, codes = get_latest_codes()
    
    # 检查最新日期是否等于今天日期
    if latest_date:
        print(f"最新兑换码日期: {latest_date}")
        
        if latest_date == today or args.force:
            if args.force and latest_date != today:
                print("[信息] 强制模式，开始兑换非今日的码")
            else:
                print("[成功] 最新日期等于今天，开始兑换")
            redeem_codes(codes)
            print("任务执行完成")
            exit(0)  # 成功兑换，返回0退出码
        else:
            print("[信息] 最新日期不等于今天，跳过兑换")
            exit(0)  # 跳过兑换，但返回成功退出码，因为脚本执行正常
    else:
        print("[错误] 未获取到有效日期，跳过兑换")
        exit(1)  # 获取日期失败，返回非0退出码
    
    print("任务执行完成")
    exit(0)  # 默认返回成功退出码

if __name__ == "__main__":
    main()
