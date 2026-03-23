import sys
import os

# Add parent directory to path to import ozon_api
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ouroboros.ozon_api import OzonSellerAPI
from ouroboros.ozon_api_env import OZON_SELLER_CLIENT_ID, OZON_SELLER_API_KEY


def test_ozon_api_client_creation():
    """Test that the OzonSellerAPI client can be created."""
    client = OzonSellerAPI(OZON_SELLER_CLIENT_ID, OZON_SELLER_API_KEY)
    assert client is not None
    assert client.client_id == OZON_SELLER_CLIENT_ID
    assert client.api_key == OZON_SELLER_API_KEY


def test_get_product_list():
    """Test that we can get a list of products."""
    client = OzonSellerAPI(OZON_SELLER_CLIENT_ID, OZON_SELLER_API_KEY)
    
    # Get first few products
    products = []
    for product in client.get_product_list():
        products.append(product)
        if len(products) >= 5:
            break
    
    assert len(products) > 0, "No products returned from API"
    
    # Check basic structure of a product
    product = products[0]
    essential_fields = ['product_id', 'offer_id', 'price', 'quantity']
    for field in essential_fields:
        assert field in product, f"Field {field} missing from product"
    
    # 'name' might be under a different key, check alternative structures
    if 'name' not in product:
        # Try to find name in attributes or other common structures
        # For now, log and skip the assertion if not found
        print(f"Warning: 'name' not found in product. Keys: {list(product.keys())}")
        # Check for other possible name fields
        possible_name_fields = ['name', 'offer_name', 'title', 'product_name']
        has_name = any(field in product for field in possible_name_fields)
        assert has_name, "No name-like field found in product"
    else:
        # If 'name' is present in the structure, ensure it has content
        assert product['name'].strip() != '', "Product name is empty"


def test_get_stock_info():
    """Test that we can get stock information."""
    client = OzonSellerAPI(OZON_SELLER_CLIENT_ID, OZON_SELLER_API_KEY)
    
    # Get first few stock items
    stock_items = []
    for item in client.get_stock_info():
        stock_items.append(item)
        if len(stock_items) >= 5:
            break
    
    assert len(stock_items) > 0, "No stock information returned from API"
    
    # Check basic structure of a stock item
    stock = stock_items[0]
    for field in ['offer_id', 'product_id', 'name', 'available', 'reserved']:
        assert field in stock, f"Field {field} missing from stock item"


if __name__ == '__main__':
    """Run tests manually."""
    print("Running Ozon API Client tests...")
    
    test_ozon_api_client_creation()
    print("✓ test_ozon_api_client_creation passed")
    
    test_get_product_list()
    print("✓ test_get_product_list passed")
    
    test_get_stock_info()
    print("✓ test_get_stock_info passed")
    
    print("\nAll tests passed!")