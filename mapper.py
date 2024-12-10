"""
此脚本用于下载网站内容。
主要功能：
1. 获取网站首页内容
2. 解析HTML找到链接
3. 下载相关内容
"""

# 导入必要的模块
import os
import requests
from bs4 import BeautifulSoup
import urllib.parse
import threading
import queue
import sys
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import random
import time

# 创建队列存储URL
urls_to_visit = queue.Queue()
visited_urls = set()
downloaded_files = queue.Queue()

def clean_url(url):
    """清理URL格式"""
    url = url.replace('：', ':')
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url.lstrip('/')
    return url

def is_valid_url(url, base_domain):
    """检查URL是否属于目标域名"""
    try:
        parsed = urllib.parse.urlparse(url)
        return base_domain in parsed.netloc
    except:
        return False

def download_content(url, save_path=None):
    """下载网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        # 添加重试机制
        for attempt in range(3):  # 最多重试3次
            try:
                session = requests.Session()
                response = session.get(
                    url, 
                    headers=headers, 
                    verify=False, 
                    timeout=30,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    if save_path:
                        # 确保目录存在
                        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
                        # 保存内容
                        with open(save_path, 'wb') as f:
                            f.write(response.content)
                        print(f"[+] 已保存: {save_path}")
                    return response.text
                elif response.status_code == 403:
                    print(f"[-] 访问被拒绝 {url}")
                    break
                else:
                    print(f"[-] 状态码 {response.status_code} for {url}")
                    if attempt < 2:  # 如果不是最后一次尝试
                        time.sleep(2 * (attempt + 1))  # 递增等待时间
                        continue
                    
            except requests.exceptions.ConnectionError as e:
                if 'Connection aborted' in str(e) and attempt < 2:
                    print(f"[*] 连接被重置，等待后重试... ({attempt + 1}/3)")
                    time.sleep(5 * (attempt + 1))
                    continue
                else:
                    raise
                    
    except requests.exceptions.RequestException as e:
        print(f"[-] 下载错误 {url}: {str(e)}")
    except Exception as e:
        print(f"[-] 其他错误 {url}: {str(e)}")
    return None

def process_url():
    """处理URL队列中的链接"""
    while True:
        try:
            url = urls_to_visit.get_nowait()
        except queue.Empty:
            break
            
        if url in visited_urls:
            continue
            
        visited_urls.add(url)
        print(f"\n[*] 正在处理: {url}")
        
        # 在每个请求之间添加随机延时
        time.sleep(random.uniform(1, 3))
        
        content = download_content(url)
        if not content:
            continue
            
        # 解析HTML
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # 保存页面
            filename = urllib.parse.urlparse(url).path
            if not filename or filename == '/':
                filename = 'index.html'
            filename = filename.lstrip('/')
            if not os.path.splitext(filename)[1]:
                filename += '.html'
            
            # 确保文件名合法
            filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.', '/'))
            download_content(url, filename)
            downloaded_files.put(filename)
            
            # 获取所有链接
            for link in soup.find_all(['a', 'link', 'script', 'img']):
                href = link.get('href') or link.get('src')
                if not href:
                    continue
                    
                # 转换为绝对URL
                try:
                    abs_url = urllib.parse.urljoin(url, href)
                    if is_valid_url(abs_url, base_domain):
                        if abs_url not in visited_urls:
                            urls_to_visit.put(abs_url)
                except Exception as e:
                    print(f"[-] URL解析错误 {href}: {str(e)}")
                    
        except Exception as e:
            print(f"[-] 解析错误 {url}: {str(e)}")

if __name__ == '__main__':
    # 获取目标URL
    target_url = input('请输入url:')
    target_url = clean_url(target_url)
    base_domain = urllib.parse.urlparse(target_url).netloc
    
    print(f"\n目标域名: {base_domain}")
    
    # 创建输出目录
    if not os.path.exists('output'):
        os.makedirs('output')
    os.chdir('output')
    
    # 添加首页到队列
    urls_to_visit.put(target_url)
    
    print("\n开始下载网站内容...")
    # 创建线程池
    threads = []
    for i in range(3):  # 减少线程数，避免请求过于频繁
        print(f"正在启动线程 {i}")
        t = threading.Thread(target=process_url)
        t.start()
        threads.append(t)
    
    # 等待所有线程完成
    for t in threads:
        t.join()
    
    print("\n下载完成！已保存的文件：")
    downloaded_count = 0
    while not downloaded_files.empty():
        print(downloaded_files.get())
        downloaded_count += 1
    
    if downloaded_count == 0:
        print("未能成功下载任何文件。可能原因：")
        print("1. 网站有反爬虫机制")
        print("2. 需要身份验证")
        print("3. 网络连接问题")
        print("4. 网站可能暂时不可用")
    
    input("按回车键继续:")