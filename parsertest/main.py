import asyncio
import csv
import logging
import os

from dotenv import load_dotenv

from parsertest.proxy import get_proxy, check_proxies
from parsertest.utils import get_selenium_driver
from sbermarket import SbermarketParser

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
URL_FOR_CITY_ID = os.getenv("URL_FOR_CITY_ID")
URL_PRODUCTS = os.getenv("URL_PRODUCTS")
CITY_NAME = os.getenv("CITY_NAME")
STORE_NAME = os.getenv("STORE_NAME")
ADDRESS = os.getenv("ADDRESS")
ALL_PRODUCTS = os.getenv("ALL_PRODUCTS")
CATEGORIES = os.getenv("CATEGORIES")
PAGES = 3

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "ru,en-US;q=0.9,en;q=0.8,ko;q=0.7,ru-RU;q=0.6",
    "Client-Token": "7ba97b6f4049436dab90c789f946ee2f",
    "Priority": "u=1, i",
    "Sbm-Forward-Tenant": "sbermarket",
    "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125",'
                 ' "Not.A/Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sentry-Trace": "90b25b813df84e9e9823c156b4de4843-99de013166300b82-0",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/"
                  "537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s '
                                               '- %(message)s')


async def main():
    logging.info("Starting parser")

    PROXY = get_proxy()
    proxy = check_proxies(PROXY)
    driver = get_selenium_driver(proxy)
    logging.info("Start process")

    parser = SbermarketParser(driver, HEADERS, BASE_URL, URL_PRODUCTS)

    cookies = await parser.get_cookies(BASE_URL)

    city_data = await parser.fetch_data(URL_FOR_CITY_ID, cookies)
    city_id = parser.find_city_id(city_data.get('cities', []), CITY_NAME)

    url_for_store = (f'https://sbermarket.ru/api/v3/retailers?include='
                     f'shipping_methods%2Cstores_count%2Cnearest_store%'
                     f'2Clabels&shipping_method=pickup_from_store&'
                     f'city_id={city_id}')
    store_data = await parser.fetch_data(url_for_store, cookies)

    shop_id, slug = parser.find_store_id(store_data, STORE_NAME)
    all_stores = await parser.fetch_all_stores(city_id, shop_id, cookies)

    store_id = parser.find_store_id_by_address(all_stores, ADDRESS)

    all_products = {}
    for category in CATEGORIES:
        category_slug, canonical_url = await parser.find_canonical_url(
            store_id, ALL_PRODUCTS, category)
        tasks = []
        for page in range(1, PAGES + 1):
            params = {
                "store_id": f"{store_id}",
                "page": f"{page}",
                "per_page": "24",
                "tenant_id": "sbermarket",
                "category_permalink": category_slug,
                "store_meta_keys": [],
                "store_meta_values": [],
                "filter": [
                    {"key": "brand", "values": []},
                    {"key": "permalinks", "values": []},
                    {"key": "discounted", "values": []}
                ],
                "ads_identity": {
                    "ads_promo_identity": {
                        "site_uid": "c9qep2jupf8ugo3scn10",
                        "placement_uid": "cg4tmrigsvdveog2p240"
                    }
                }
            }
            task = parser.fetch_products(params, category)
            tasks.append(task)
        products_list = await asyncio.gather(*tasks)
        for products in products_list:
            all_products.update(products)

    await parser.close()
    save_to_csv(all_products, 'products.csv')
    logging.info("Parser finished successfully")


def save_to_csv(data, filename):
    if data:
        keys = data[next(iter(data))].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file,
                                         fieldnames=['name'] + list(keys))
            dict_writer.writeheader()
            for name, info in data.items():
                dict_writer.writerow({'name': name, **info})


if __name__ == "__main__":
    asyncio.run(main())
