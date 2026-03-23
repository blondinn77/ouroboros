import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = "/opt/ouroboros"
sys.path.insert(0, repo_dir)

from ouroboros.ozon_api import OzonSellerAPI
from ouroboros.api.ozon_secrets import SELLER_CLIENT_ID, SELLER_API_KEY

client = OzonSellerAPI(SELLER_CLIENT_ID, SELLER_API_KEY)

# Get first few products from the list
products = []
for product in client.get_product_list():
    products.append(product)
    if len(products) >= 2:  # Just get 2 products for testing
        break

print("First 2 products from get_product_list:")
for i, product in enumerate(products):
    print(f"\nProduct {i+1}:")
    print(f"  offer_id: {product.get('offer_id')}")
    print(f"  product_id: {product.get('product_id')}")
    print(f"  name: {product.get('name')}")
    
    # Print price information if available
    if 'price' in product:
        print(f"  price: {product['price']}")
    
    # Print quantity information if available
    if 'quantity' in product:
        print(f"  quantity: {product['quantity']}")
    
    # Print analytics data if available
    if 'analytics_data' in product:
        print(f"  analytics_data: {product['analytics_data']}")
    
    # Print the full item for inspection
    print(f"  Full item keys: {list(product.keys())}")