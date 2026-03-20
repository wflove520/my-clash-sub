import base64
import json
import urllib.parse
import requests
import yaml
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from flask import Flask, Response

# 初始化 Flask 应用（就是这里刚才被删掉了）
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
        requests.packages.urllib3.disable_warnings()
        r = requests.post(URL, headers=HDR, data=PAYLOAD, verify=False, timeout=10)
        nodes_data = json.loads(dec(r.text, K1))['data']['share_node']
        
        # 基础骨架：加入了 url 和 interval，并且去掉了 DIRECT 防止测速卡住
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
                    "url": "http://www.gstatic.com/generate_204",
                    "interval": 300,
                    "proxies": []
                }
            ],
            "rules": [
                "MATCH,Proxy"
            ]
        }

        # 遍历解析节点
        for n in nodes_data:
            link = dec(n['link'].replace('enc://', ''), K2).decode('utf-8', 'ignore')
            fixed_link = link.replace('obfs%3Bobfs%3Dhttp%3Bhost', 'obfs-local%3Bobfs%3Dhttp%3Bobfs-host')
            
            parsed = urllib.parse.urlparse(fixed_link)
            userinfo = parsed.username
            if userinfo:
                userinfo += '=' * (-len(userinfo) % 4)
                decoded_userinfo = base64.urlsafe_b64decode(userinfo).decode('utf-8')
                method, password = decoded_userinfo.split(':', 1)
            else:
                continue

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

        # 生成 YAML
        yaml_str = yaml.dump(clash_config, allow_unicode=True, sort_keys=False)
        
        # 伪装成文件下载，完美兼容 FlClash
        return Response(
            yaml_str, 
            mimetype='application/x-yaml; charset=utf-8',
            headers={
                "Content-Disposition": "attachment; filename=config.yaml",
                "profile-update-interval": "60"
            }
        )

    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
