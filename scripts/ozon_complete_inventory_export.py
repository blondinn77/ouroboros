import sys
import os
import json
import logging
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = "/opt/ouroboros"
sys.path.insert(0, repo_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Export complete inventory data from Ozon Seller API by combining
    stock information with product details to get names and other attributes.
    """
    try:
        from ouroboros.ozon_api import OzonSellerAPI
        from ouroboros.api.ozon_secrets import SELLER_CLIENT_ID, SELLER_API_KEY
        
        # Initialize API client
        client = OzonSellerAPI(SELLER_CLIENT_ID, SELLER_API_KEY)
        
        # Create data directory if it doesn't exist
        data_dir = os.path.join(repo_dir, "data", "ozon")
        os.makedirs(data_dir, exist_ok=True)
        
        # File path for the output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(data_dir, f"complete_stock_dump_{timestamp}.json")
        
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Repository directory: {repo_dir}")
        logger.info(f"Data directory: {data_dir}")
        logger.info(f"Output file path: {output_file}")
        
        logger.info("Fetching inventory data from Ozon API...")
        
        # Get all product information with detailed fields
        complete_inventory = []
        
        for item in client.get_product_list():
            # Extract basic information
            offer_id = item['offer_id']
            product_id = item['product_id']
            
            # Try to get product name from various sources
            name = None
            
            # First, check if name is directly available
            if item.get('name'):
                name = item['name']
            
            # If not, check attributes (commonly used for product name)
            if not name and item.get('attributes'):
                for attr in item['attributes']:
                    if attr.get('attribute_id') == 43 and attr.get('values'):
                        name = attr['values'][0].get('value')
                        break
            
            # If still no name, use offer_id as fallback
            if not name:
                name = offer_id

            # Extract pricing information
            price_info = {}
            if 'price' in item:
                price_info = item['price']
                
            # Extract analytics data (contains stock information)
            analytics_data = {}
            if 'analytics_data' in item:
                analytics_data = item['analytics_data']
                
            # Extract quantity information
            quantity = item.get('quantity', 0)
            
            # Create comprehensive inventory item
            complete_item = {
                'offer_id': offer_id,
                'product_id': product_id,
                'name': name,
                'price_info': price_info,
                'analytics_data': analytics_data,
                'quantity': quantity,
                'has_fbo_stocks': item.get('has_fbo_stocks', False),
                'has_fbs_stocks': item.get('has_fbs_stocks', False),
                'is_discounted': item.get('is_discounted', False),
                'archived': item.get('archived', False),
            }
            
            complete_inventory.append(complete_item)
        
        logger.info(f"Processed {len(complete_inventory)} complete inventory items")
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_inventory, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Complete inventory data saved to {output_file}")
        
        # Also save a stable symlink
        stable_file = os.path.join(data_dir, "complete_stock_dump.json")
        if os.path.exists(stable_file):
            os.remove(stable_file)
        os.symlink(output_file, stable_file)
        
        logger.info(f"Stable symlink created at {stable_file}")
        
        # Print summary
        logger.info("Summary of complete inventory data:")
        logger.info(f"Total SKUs: {len(complete_inventory)}")
        
        # Find non-archived items (active inventory)
        active_inventory = [item for item in complete_inventory if not item['archived']]
        logger.info(f"Active SKUs (not archived): {len(active_inventory)}")
        
        # Find items with quantity > 0
        in_stock_items = [item for item in complete_inventory if item['quantity'] > 0]
        logger.info(f"SKUs with positive quantity: {len(in_stock_items)}")
        
        # Calculate total inventory value if prices are available
        total_value = 0
        valued_items = 0
        for item in complete_inventory:
            if item['price_info'].get('price') and item['quantity'] > 0:
                total_value += item['price_info']['price'] * item['quantity']
                valued_items += 1
        
        if valued_items > 0:
            logger.info(f"Estimated total inventory value: {total_value} RUB for {valued_items} priced items")
        
        # Display first few items for verification
        logger.info("First 5 inventory items:")
        for i, item in enumerate(complete_inventory[:5]):
            price = item['price_info'].get('price', 'N/A')
            logger.info(f"  {i+1}. {item['name']}: {item['quantity']} units at {price} RUB")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to export complete inventory data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()