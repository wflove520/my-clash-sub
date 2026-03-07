import base64
import json
import urllib.parse
import requests
import yaml
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from flask import Flask, Response

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

def get_latest_nodes():
    """实时请求目标服务器获取并解密最新节点"""
    requests.packages.urllib3.disable_warnings()
    r = requests.post(URL, headers=HDR, data=PAYLOAD, verify=False, timeout=10)
    nodes_data = json.loads(dec(r.text, K1))['data']['share_node']
    
    links = []
    for n in nodes_data:
        link = dec(n['link'].replace('enc://', ''), K2).decode('utf-8', 'ignore')
        fixed_link = link.replace('obfs%3Bobfs%3Dhttp%3Bhost', 'obfs-local%3Bobfs%3Dhttp%3Bobfs-host') + '#' + n['node_name']
        links.append(fixed_link)
    return links

def parse_ss(link):
    """解析单条 SS 链接为 Clash 字典格式"""
    link = link.strip()
    if not link or not link.startswith('ss://'): return None
    try:
        if '#' in link:
            link, name = link.split('#', 1)
            name = urllib.parse.unquote(name)
        else:
            name = "Unnamed_Node"

        parsed = urllib.parse.urlparse(link)
        userinfo = parsed.username
        if not userinfo: return None
            
        userinfo += '=' * (-len(userinfo) % 4)
        decoded_userinfo = base64.urlsafe_b64decode(userinfo).decode('utf-8')
        method, password = decoded_userinfo.split(':', 1)

        proxy = {
            "name": name,
            "type": "ss",
            "server": parsed.hostname,
            "port": parsed.port,
            "cipher": method,
            "password": password
        }

        if parsed.query:
            query = urllib.parse.parse_qs(parsed.query)
            if 'plugin' in query:
                plugin_str = query['plugin'][0]
                if 'obfs-local' in plugin_str:
                    proxy['plugin'] = 'obfs'
                    opts = {}
                    for item in plugin_str.split(';'):
                        if '=' in item:
                            k, v = item.split('=', 1)
                            if k == 'obfs': opts['mode'] = v
                            if k == 'obfs-host': opts['host'] = v
                    proxy['plugin-opts'] = opts
        return proxy
    except Exception as e:
        return None

@app.route('/clash')
def generate_clash_yaml():
    """Web 接口：返回最终的 YAML 订阅配置"""
    try:
        links = get_latest_nodes()
        
        # 基础 Clash 配置模板
        clash_config = {
            "port": 7890,
            "socks-port": 7891,
            "allow-lan": False,
            "mode": "Rule",
            "log-level": "info",
            "proxies": [],
            "proxy-groups": [
                {
                    "name": "🚀 节点选择",
                    "type": "select",
                    "proxies": ["DIRECT"]
                }
            ],
            "rules": [
                "MATCH,🚀 节点选择"
            ]
        }

        # 填充解析好的节点
        for link in links:
            p = parse_ss(link)
            if p:
                clash_config["proxies"].append(p)
                clash_config["proxy-groups"][0]["proxies"].append(p["name"])

        # 生成 YAML 文本
        yaml_str = yaml.dump(clash_config, allow_unicode=True, sort_keys=False)
        
        # 伪装成文件下载，确保 Clash 能正确识别
        return Response(
            yaml_str, 
            mimetype='text/yaml; charset=utf-8',
            headers={"Content-Disposition": "attachment; filename=config.yaml"}
        )
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)