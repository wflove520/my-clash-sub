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

@app.route('/clash')
def generate_clash_yaml():
    try:
        # 1. 抓取最新节点
        requests.packages.urllib3.disable_warnings()
        r = requests.post(URL, headers=HDR, data=PAYLOAD, verify=False, timeout=10)
        nodes_data = json.loads(dec(r.text, K1))['data']['share_node']
        
        # 2. 构造你本地那种极简、完美的 Clash 骨架
        clash_config = {
            "port": 7890,
            "socks-port": 7891,
            "allow-lan": False,
            "mode": "Rule",
            "log-level": "info",
            "proxies": [],
            "proxy-groups": [
                {
                    "name": "Proxy",
                    "type": "select",
                    "proxies": ["DIRECT"]
                }
            ],
            "rules": [
                "MATCH,Proxy"
            ]
        }

        # 3. 解析并填充节点 (使用多行格式，绝不压缩)
        for n in nodes_data:
            link = dec(n['link'].replace('enc://', ''), K2).decode('utf-8', 'ignore')
            fixed_link = link.replace('obfs%3Bobfs%3Dhttp%3Bhost', 'obfs-local%3Bobfs%3Dhttp%3Bobfs-host')
            
            parsed = urllib.parse.urlparse(fixed_link)
            userinfo = parsed.username + '=' * (-len(parsed.username) % 4)
            decoded_userinfo = base64.urlsafe_b64decode(userinfo).decode('utf-8')
            method, password = decoded_userinfo.split(':', 1)

            proxy = {
                "name": n['node_name'],
                "type": "ss",
                "server": parsed.hostname,
                "port": parsed.port,
                "cipher": method,
                "password": password
            }

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

            clash_config["proxies"].append(proxy)
            clash_config["proxy-groups"][0]["proxies"].append(n['node_name'])

        # 4. 转化为完美的 YAML 文本
        yaml_str = yaml.dump(clash_config, allow_unicode=True, sort_keys=False)
        return Response(yaml_str, mimetype='text/yaml; charset=utf-8')

    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
