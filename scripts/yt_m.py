import os
import re
import requests
import paramiko
from urllib.parse import urlparse

# 設定檔案路徑
yt_info_path = "yt_info.txt"
output_dir = "output"
cookies_path = os.path.join(os.getcwd(), "cookies.txt")

# 讀取環境變數
SF_L = os.getenv("SF_L", "")
SF_L2 = os.getenv("SF_L2", "")
SF_L3 = os.getenv("SF_L3", "")

# 驗證環境變數
for name, val in [("SF_L", SF_L), ("SF_L2", SF_L2), ("SF_L3", SF_L3)]:
    if not val:
        print(f"❌ 環境變數 {name} 未設置")
        exit(1)

# 解析 SFTP URL
def parse_sftp(url):
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 221,
        "user": parsed.username,
        "password": parsed.password,
        "path": parsed.path or "/"
    }

SFTP_1 = parse_sftp(SF_L)
SFTP_2 = parse_sftp(SF_L2)
SFTP_3 = parse_sftp(SF_L3)

# 確保輸出目錄存在
os.makedirs(output_dir, exist_ok=True)

def grab(youtube_url):
    """從 YouTube 頁面抓取 M3U8 連結"""
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    cookies = {}
    if os.path.exists(cookies_path):
        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith('#') and '\t' in line:
                        parts = line.strip().split('\t')
                        if len(parts) >= 6:
                            cookies[parts[5]] = parts[6]
        except Exception as e:
            print(f"⚠️ Cookie 讀取失敗: {e}")

    try:
        res = requests.get(youtube_url, headers=headers, cookies=cookies, timeout=10)
        html = res.text
        m3u8_matches = re.findall(r'https://[^"]+\.m3u8', html)

        for url in m3u8_matches:
            if "googlevideo.com" in url:
                return url

        print("⚠️ 未找到有效的 .m3u8 連結")
    except Exception as e:
        print(f"⚠️ 抓取頁面失敗: {e}")

    return "https://raw.githubusercontent.com/chse-1/YT2m/main/assets/no_s.m3u8"

def process_yt_info():
    """解析 yt_info.txt 並生成 M3U8 和 PHP 檔案"""
    with open(yt_info_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 1
    for line in lines:
        line = line.strip()
        if line.startswith("~~") or not line:
            continue
        if "|" in line:
            continue
        else:
            youtube_url = line
            print(f"🔍 嘗試解析 M3U8: {youtube_url}")
            m3u8_url = grab(youtube_url)

            m3u8_content = f"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1280000\n{m3u8_url}\n"
            output_m3u8 = os.path.join(output_dir, f"y{i:02d}.m3u8")
            with open(output_m3u8, "w", encoding="utf-8") as f:
                f.write(m3u8_content)

            php_content = f"""<?php
header('Location: {m3u8_url}');
?>"""
            output_php = os.path.join(output_dir, f"y{i:02d}.php")
            with open(output_php, "w", encoding="utf-8") as f:
                f.write(php_content)

            print(f"✅ 生成 {output_m3u8} 和 {output_php}")
            i += 1

def upload_to_sftp(sftp_info, label):
    """上傳檔案到單一 SFTP"""
    print(f"🚀 上傳到 {label} ({sftp_info['host']})...")
    try:
        transport = paramiko.Transport((sftp_info["host"], sftp_info["port"]))
        transport.connect(username=sftp_info["user"], password=sftp_info["password"])
        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            sftp.chdir(sftp_info["path"])
        except IOError:
            print(f"📁 目錄 {sftp_info['path']} 不存在，創建中...")
            sftp.mkdir(sftp_info["path"])
            sftp.chdir(sftp_info["path"])

        for file in os.listdir(output_dir):
            local_path = os.path.join(output_dir, file)
            remote_path = os.path.join(sftp_info["path"], file)
            if os.path.isfile(local_path):
                print(f"⬆️ 上傳 {local_path} → {remote_path}")
                sftp.put(local_path, remote_path)

        sftp.close()
        transport.close()
        print(f"✅ {label} 上傳完成")

    except Exception as e:
        print(f"❌ {label} 上傳失敗: {e}")

def upload_files():
    upload_to_sftp(SFTP_1, "SFTP1")
    upload_to_sftp(SFTP_2, "SFTP2")
    upload_to_sftp(SFTP_3, "SFTP3")

if __name__ == "__main__":
    process_yt_info()
    upload_files()
