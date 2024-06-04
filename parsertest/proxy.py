from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup as BS
from requests.exceptions import ProxyError, Timeout, RequestException, \
    ConnectTimeout

header = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
}


def get_proxy():
    data_link = {"https": '1', "submit": 'Search'}
    r = requests.get("https://www.iplocation.net/proxy-list", data=data_link,
                     headers=header)
    proxy_list = []
    if r.status_code == 200:
        soup = BS(r.text, 'html.parser')
        table = soup.select_one('table.table.table-hover')
        rows = table.select('tr')[1:]
        for row in rows[1:3]:
            columns = row.find_all('td')
            ip_address = columns[0].get_text().strip()
            port = columns[1].get_text().strip()
            location = columns[3].get_text().strip()
            proxy_info = (ip_address, port, location)
            proxy_list.append(proxy_info)

        return proxy_list
    else:
        return []


def test_proxy(proxy):
    ip, port, location = proxy
    proxy_url = f"http://{ip}:{port}"
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }
    try:
        response = requests.get("http://www.google.com", proxies=proxies,
                                timeout=5)
        if response.status_code == 200:
            return (ip, port, location, True, None)
        else:
            return (ip, port, location, False,
                    f"Unexpected status code: {response.status_code}")
    except ProxyError as e:
        return (ip, port, location, False, f"ProxyError: {e}")
    except ConnectTimeout as e:
        return (ip, port, location, False, f"ConnectTimeout: {e}")
    except Timeout as e:
        return (ip, port, location, False, f"Timeout: {e}")
    except RequestException as e:
        return (ip, port, location, False, f"RequestException: {e}")


def check_proxies(proxy_list, max_workers=10):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy
                           in proxy_list}
        for future in as_completed(future_to_proxy):
            result = future.result()
            results.append(result)
    return results


def output_proxy(proxy_list):
    with open('proxy.txt', 'w') as file:
        for proxy in proxy_list:
            ip_address, port, location = proxy
            file.write('*' * 30 + '\n')
            file.write(f'{ip_address}:{port:5}\n')
            file.write(f'Location: {location:14}\n')
            file.write('*' * 30 + '\n')

    print('[+] Saved in the text file “proxy.txt”')


def log_info():
    print("[!] Proxy search started...")
    proxy_list = get_proxy()
    if proxy_list:
        output_proxy(proxy_list)
    else:
        print("[!] Failed to connect...")