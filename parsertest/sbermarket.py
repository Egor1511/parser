import logging
import random
import time

import requests
from selenium.common.exceptions import WebDriverException

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class SbermarketParser:
    def __init__(self, driver, headers, base_url, url_products):
        self.driver = driver
        self.headers = headers
        self.base_url = base_url
        self.url_products = url_products

    def sleep_random(self, min_time=1, max_time=2):
        time.sleep(random.uniform(min_time, max_time))

    def get_cookies(self, url):
        try:
            self.driver.get(url)
            cookies = self.driver.get_cookies()
            return {cookie['name']: cookie['value'] for cookie in cookies}
        except WebDriverException as e:
            logging.error(f"Error getting cookies from {url}: {e}")
            return {}

    def fetch_data(self, url, cookies):
        try:
            response = requests.get(url, headers=self.headers, cookies=cookies)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error fetching data from {url}: {e}")
            return {}

    def find_city_id(self, cities, city_name):
        city = next((city for city in cities if city['name'] == city_name),
                    None)
        return city['id'] if city else None

    def find_store_id(self, stores, store_name):
        store = next(
            (store for store in stores if store['name'] == store_name), None)
        return (store['id'], store['slug']) if store else (None, None)

    def fetch_all_stores(self, city_id, retailer_id, per_page=10):
        all_stores = []
        page = 1

        while True:
            paginated_url = f"{self.base_url}api/v3/stores_with_pagination?city_id={city_id}&retailer_id={retailer_id}&include=full_address%2Cdistance%2Copening_hours_text&shipping_method=pickup_from_store&zero_price=true&page={page}&per_page={per_page}"
            data = self.fetch_data(paginated_url,
                                   self.get_cookies(self.base_url))
            stores = data.get('stores', [])

            if not stores:
                break

            all_stores.extend(stores)
            if len(stores) < per_page:
                break

            page += 1

        return all_stores

    def find_canonical_url(self, store_id, name1, name2):
        url = f"{self.base_url}api/v3/stores/{store_id}/categories?depth=2"
        js_script = """
        var callback = arguments[arguments.length - 1];
        fetch(arguments[0])
          .then(response => response.json())
          .then(data => callback(data))
          .catch(error => callback(error));
        """

        try:
            data = self.driver.execute_async_script(js_script, url)
            categories = data.get("categories", [])

            for category in categories:
                if category.get("name") == name2:
                    for child in category.get("children", []):
                        if child.get("name") == name1:
                            return child.get("slug"), child.get(
                                "canonical_url")
        except WebDriverException as e:
            logging.error(f"Error executing script for {url}: {e}")

        logging.error("Failed to get a valid response from the server.")
        return None, None

    def find_store_id_by_address(self, stores, address):
        store = next((store for store in stores if
                      store.get('full_address') == address), None)
        return store['store_id'] if store else None

    def fetch_products(self, params):
        js_script = """
        var callback = arguments[arguments.length - 1];
        fetch(arguments[0], {
          method: 'POST',
          headers: arguments[1],
          body: JSON.stringify(arguments[2])
        })
        .then(response => response.json())
        .then(data => callback(data))
        .catch(error => callback(error));
        """

        try:
            data = self.driver.execute_async_script(js_script,
                                                    self.url_products,
                                                    self.headers, params)
            products = data.get("products", [])
            return {
                product.get("name"): {
                    "image_url": product.get("image_urls", [None])[0],
                    "canonical_url": product.get("canonical_url"),
                    "original_price": product.get("original_price"),
                    "price": product.get("price")
                } for product in products
            }
        except WebDriverException as e:
            logging.error(f"Error fetching products: {e}")
            return {}
