@app.route('/clash')
def generate_clash_yaml():
    try:
        requests.packages.urllib3.disable_warnings()
        r = requests.post(URL, headers=HDR, data=PAYLOAD, verify=False, timeout=10)
        nodes_data = json.loads(dec(r.text, K1))['data']['share_node']
        
        # 1. 核心修复：添加 url 和 interval 测速参数，并去掉 DIRECT
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
                    "url": "http://www.gstatic.com/generate_204",  # 告诉 FlClash 去哪里测速
                    "interval": 300,                              # 告诉 FlClash 每隔多久自动测速
                    "proxies": []
                }
            ],
            "rules": [
                "MATCH,Proxy"
            ]
        }

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

        yaml_str = yaml.dump(clash_config, allow_unicode=True, sort_keys=False)
        
        # 2. 核心修复：强制伪装成 .yaml 文件下载，并声明配置更新间隔
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
