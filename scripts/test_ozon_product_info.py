import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = "/opt/ouroboros"
sys.path.insert(0, repo_dir)

from ouroboros.ozon_api import OzonSellerAPI
from ouroboros.api.ozon_secrets import SELLER_CLIENT_ID, SELLER_API_KEY

client = OzonSellerAPI(SELLER_CLIENT_ID, SELLER_API_KEY)

# Get product info for a specific product
product_info = client.get_product_info(1380713587)
print("Product info for ID 1380713587:")
print(product_info)