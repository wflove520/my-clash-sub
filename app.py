import base64
import json
import time
import urllib.parse
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from flask import Flask, Response, redirect, request

app = Flask(__name__)

# --- 核心配置 ---
K1 = bytes.fromhex('1712ea6dbb9ceabb1712ea6dbb9ceabb1712ea6dbb9ceabb1712ea6dbb9ceabb')
K2 = b'bitboo8888oobtib'
IV = b'\x00' * 16
URL = "https://81.71.98.184/api/node_list"
HDR = {"user-agent": "Dart/3.8 (dart:io)", "content-type": "application/json"}
PAYLOAD = "IzlE5qur1yao+SgMPGpYzOVX5I8oYPXUhR7qxkOve0piNGSpeW360VAPnQMczjvPVDlE7+obIvn24RhELIWG+zjTQsHQZb4Z1bbx1tNfdTAhh3G27ZihoqRYgrUtLv0FQ/xZG0N9C7yKNW8h87vmxGwMIy9SX26anvDN8zKYtzcsZDaueL7VNZY6PKjmHgeWFEQz+EInr3btMFtVuh2Kl7SJQBsb+esx35qZ5lS6FCRlMHSlmyWCu0P0o8qJFbp/QWdl5c0PsOnaXKsiaT8eKg=="

def dec(d, k):
    return unpad(AES.new(k, AES.MODE_CBC, IV).decrypt(base64.b64decode(d)), 16)

# 接口1：只负责输出纯净 Base64 节点（供转换器拉取用）
@app.route('/clash')
def generate_sub():
    try:
        requests.packages.urllib3.disable_warnings()
        r = requests.post(URL, headers=HDR, data=PAYLOAD, verify=False, timeout=10)
        nodes_data = json.loads(dec(r.text, K1))['data']['share_node']
        
        links = []
        for n in nodes_data:
            link = dec(n['link'].replace('enc://', ''), K2).decode('utf-8', 'ignore')
            fixed_link = link.replace('obfs%3Bobfs%3Dhttp%3Bhost', 'obfs-local%3Bobfs%3Dhttp%3Bobfs-host') + '#' + n['node_name']
            links.append(fixed_link)
            
        raw_text = '\n'.join(links)
        b64_text = base64.b64encode(raw_text.encode('utf-8')).decode('utf-8')
        return Response(b64_text, mimetype='text/plain; charset=utf-8')
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

# 接口2：Clash 专属的智能更新入口 (自动打破缓存)
@app.route('/auto')
def auto_update():
    # 1. 自动获取你当前的 Render 域名
    source_url = f"{request.host_url.rstrip('/')}/clash"
    encoded_url = urllib.parse.quote(source_url)
    
    # 2. 生成实时时间戳 (比如 1712345678)
    t = int(time.time())
    
    # 3. 拼接给转换器的终极链接，利用 _t=时间戳 骗过它的缓存
    sub_url = f"https://api.wcc.best/sub?target=clash&url={encoded_url}&insert=false&_t={t}"
    
    # 4. 下达 302 指令，让 Clash 软件自动跳转过去下载！
    return redirect(sub_url, code=302)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
