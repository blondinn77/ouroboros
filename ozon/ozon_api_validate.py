from ouroboros.ozon_api import OzonSellerAPI
from ouroboros.api.ozon_secrets import SELLER_CLIENT_ID, SELLER_API_KEY
import logging
import sys

# Configure logging
time.sleep(0.1)  # Ensure unique file name for git
debug_logging.basicConfig(level=logging.DEBUG)

def validate_api():
    """
    Validates the Ozon Seller API connection and data retrieval with correct endpoint usage.
    Focuses on using the /v4/product/info/stocks endpoint for accurate stock data.
    """
    print("--- Ozon API Connectivity Test ---")
    print(f"Client-ID: {SELLER_CLIENT_ID}")
    # Mask the actual API key for security
    print(f"Api-Key: {SELLER_API_KEY[:8]}...{SELLER_API_KEY[-8:]}")

    # 1. Initialize API client
    try:
        api = OzonSellerAPI(SELLER_CLIENT_ID, SELLER_API_KEY)
        print("✓ OzonSellerAPI client instantiated successfully.")
    except Exception as e:
        print(f"✗ Failed to create API client: {e}")
        return

    # 2. Test authentication with get_product_list (a basic working endpoint)
    try:
        products_gen = api.get_product_list()
        first_product = next(products_gen, None)
        if first_product:
            print("✓ Authentication successful. Can retrieve product list.")
            print(f"  First product ID: {first_product['product_id']}, Available: {first_product.get('quantity', 'N/A')}")
        else:
            print("✗ get_product_list returned no items.")
            return
    except Exception as e:
        print(f"✗ Authentication or fetch failed with get_product_list: {e}")
        return

    # 3. Validate /v4/product/info/stocks endpoint
    # First, get all product IDs for the query
    print("Attempting to use /v4/product/info/stocks endpoint...")
    try:
        # Collect product_ids
        product_ids = [item['product_id'] for item in api.get_product_list()]
        print(f"✓ Collected {len(product_ids)} product IDs for query.")

        # Construct the request data as per the documented schema.
        # Using the minimal working example with cursor and visibility filter.
        request_data = {
            "cursor": "",
            "limit": 1000,
            "filter": {
                "visibility": "VISIBLE" # Using "VISIBLE" based on working examples
            }
        }
        print(f"✓ Request data prepared: {request_data}")

        # Try to make the call.
        # Note: We don't use the wrapper `get_stocks_info()` as it uses the v4 path but an older body schema
        response = api._request('POST', '/v4/product/info/stocks', data=request_data)
        
        print("✓ Request to /v4/product/info/stocks succeeded.")
        if 'items' in response and len(response['items']) > 0:
            print(f"  Retrieved {len(response['items'])} items with stock data.")
            for item in response['items'][:2]: # Print first two for brevity
                present = sum(stock['present'] for stock in item.get('stocks', []))
                reserved = sum(stock['reserved'] for stock in item.get('stocks', []))
                print(f"  Offer ID: {item['offer_id']} -> Available: {present}, Reserved: {reserved}")
        else:
            print("  No items with stock data returned.")
            
    except Exception as e:
        print(f"✗ Call to /v4/product/info/stocks failed: {e}")
        return

    print("\n--- Validation Complete ---")

if __name__ == '__main__':
    validate_api()