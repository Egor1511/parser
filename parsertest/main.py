import csv
import logging

from parsertest.proxy import get_proxy, check_proxies
from parsertest.utils import get_selenium_driver
from sbermarket import SbermarketParser

BASE_URL = 'https://sbermarket.ru/'
URL_FOR_CITY_ID = 'https://sbermarket.ru/api/v3/cities?lat=55.678088&lon=37.722738&with_pickup=true&per_page=500'
URL_PRODUCTS = "https://sbermarket.ru/api/web/v1/products"
CITY_NAME = "Москва"
STORE_NAME = "METRO"
ADDRESS = "Москва, Проспект Мира, 211с1"
ALL_PRODUCTS = "Все товары категории"
CATEGORY = "Овощи, фрукты, орехи"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "ru,en-US;q=0.9,en;q=0.8,ko;q=0.7,ru-RU;q=0.6",
    "Client-Token": "7ba97b6f4049436dab90c789f946ee2f",
    "Priority": "u=1, i",
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

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    logging.info("Starting parser")

    PROXY = get_proxy()
    proxy = check_proxies(PROXY)
    driver = get_selenium_driver(proxy)

    parser = SbermarketParser(driver, HEADERS, BASE_URL, URL_PRODUCTS)

    cookies = parser.get_cookies(BASE_URL)

    city_data = parser.fetch_data(URL_FOR_CITY_ID, cookies)
    city_id = parser.find_city_id(city_data.get('cities', []), CITY_NAME)

    url_for_store = f'https://sbermarket.ru/api/v3/retailers?include=shipping_methods%2Cstores_count%2Cnearest_store%2Clabels&shipping_method=pickup_from_store&city_id={city_id}'
    store_data = parser.fetch_data(url_for_store, cookies)

    shop_id, slug = parser.find_store_id(store_data, STORE_NAME)
    all_stores = parser.fetch_all_stores(city_id, shop_id)

    store_id = parser.find_store_id_by_address(all_stores, ADDRESS)

    category_slug, canonical_url = parser.find_canonical_url(store_id,
                                                             ALL_PRODUCTS,
                                                             CATEGORY)

    params = {
        "store_id": f"{store_id}",
        "page": "1",
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

    products = parser.fetch_products(params)

    save_to_csv(products, 'products.csv')
    logging.info("Parser finished successfully")


def save_to_csv(data, filename):
    if data:
        keys = data[list(data.keys())[0]].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file,
                                         fieldnames=['name'] + list(keys))
            dict_writer.writeheader()
            for name, info in data.items():
                dict_writer.writerow({'name': name, **info})


if __name__ == "__main__":
    main()
