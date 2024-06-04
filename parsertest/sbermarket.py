import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import aiohttp
from selenium.common.exceptions import WebDriverException

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class SbermarketParser:
    def __init__(self, driver, headers, base_url, url_products):
        self.driver = driver
        self.headers = headers
        self.base_url = base_url
        self.url_products = url_products
        self.loop = asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor()
        self.conn_limit = 100

    async def get_cookies(self, url):
        try:
            await self.loop.run_in_executor(self.executor, self.driver.get,
                                            url)
            cookies = await self.loop.run_in_executor(self.executor,
                                                      self.driver.get_cookies)
            return {cookie['name']: cookie['value'] for cookie in cookies}
        except WebDriverException as e:
            logging.error(f"Error getting cookies from {url}: {e}")
            return {}

    async def fetch_data(self, url, cookies):
        try:
            async with aiohttp.ClientSession(headers=self.headers,
                                             cookies=cookies) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    logging.info(f"Request URL: {url}")
                    return await response.json()
        except aiohttp.ClientError as e:
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

    async def fetch_all_stores(self, city_id, retailer_id, cookies,
                               per_page=10):
        all_stores = []
        page = 1

        while True:
            paginated_url = (f"{self.base_url}api/v3/stores_with_pagination?"
                             f"city_id={city_id}&retailer_id={retailer_id}&"
                             f"include=full_address%2Cdistance%2Copening_"
                             f"hours_text&shipping_method=pickup_from_store&z"
                             f"ero_price=true&page={page}&per_page={per_page}")
            data = await self.fetch_data(paginated_url, cookies)
            stores = data.get('stores', [])

            if not stores:
                break

            all_stores.extend(stores)
            if len(stores) < per_page:
                break

            page += 1

        logging.info(f"Total stores fetched: {len(all_stores)}")
        return all_stores

    def find_store_id_by_address(self, stores, address):
        store = next((store for store in stores if
                      store.get('full_address') == address), None)
        return store['store_id'] if store else None

    async def find_canonical_url(self, store_id, name1, name2):
        url = f"{self.base_url}api/v3/stores/{store_id}/categories?depth=2"
        js_script = """
        var callback = arguments[arguments.length - 1];
        fetch(arguments[0])
          .then(response => response.json())
          .then(data => callback(data))
          .catch(error => callback(error));
        """

        try:
            data = await self.loop.run_in_executor(self.executor,
                                                   self.driver.execute_async_script,
                                                   js_script, url)
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

    async def fetch_products(self, params, category):
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
            data = await self.loop.run_in_executor(
                self.executor,
                self.driver.execute_async_script,
                js_script,
                self.url_products,
                self.headers,
                params
            )
            products = data.get("products", [])
            logging.info(
                f"Category: {category}, Page: {params['page']}, "
                f"Total products fetched: {len(products)}")
            return {
                product.get("name"): {
                    "category": category,
                    "image_url": product.get("image_urls", [None])[0],
                    "canonical_url": product.get("canonical_url"),
                    "original_price": product.get("original_price"),
                    "price": product.get("price")
                } for product in products
            }
        except WebDriverException as e:
            logging.error(f"Error fetching products: {e}")
            return {}

    async def close(self):
        await self.loop.run_in_executor(self.executor, self.driver.quit)
        self.executor.shutdown()
