from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def get_selenium_driver(proxy):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--proxy-server=http://{proxy}')

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36")
    options.add_argument("--window-size=1920x1080")
    options.add_argument(
        "--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
            '''
    })

    return driver

headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru,en-US;q=0.9,en;q=0.8,ko;q=0.7,ru-RU;q=0.6",
        "Baggage": "sentry-environment=client,sentry-release=r24-06-03-1052-44452133,sentry-public_key=762453a5cdd74581a43744eb5eab5c59,sentry-trace_id=90b25b813df84e9e9823c156b4de4843,sentry-sample_rate=0.1,sentry-transaction=%2F%5B...slugs%5D,sentry-sampled=false",
        "Client-Token": "7ba97b6f4049436dab90c789f946ee2f",
        "If-None-Match": 'W/"a6e52512a189cf2573b986930db5ed16"',
        "Priority": "u=1, i",
        "Referer": "https://sbermarket.ru/metro?sid=1",
        "Sbm-Forward-Tenant": "sbermarket",
        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sentry-Trace": "90b25b813df84e9e9823c156b4de4843-99de013166300b82-0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }