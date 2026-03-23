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
        
        # First, get all stock information
        stock_items = {}
        for item in client.get_stock_info():
            offer_id = item['offer_id']
            stock_items[offer_id] = {
                'offer_id': offer_id,
                'product_id': item['product_id'],
                'available': item['available'],
                'reserved': item['reserved'],
                'total_stock': item['available'] + item['reserved']
            }
        
        logger.info(f"Retrieved {len(stock_items)} inventory items")
        
        # Now, get product details for each item to get names
        complete_inventory = []
        processed_product_ids = set()
        
        for item in client.get_product_list():
            offer_id = item['offer_id']
            product_id = item['product_id']
            
            # Skip if we've already processed this product
            if product_id in processed_product_ids:
                continue
                
            processed_product_ids.add(product_id)
            
            # Get product name and other details
            name = item.get('name')
            
            # If name is not in the main object, check attributes
            if not name:
                attributes = item.get('attributes', [])
                for attr in attributes:
                    if attr.get('attribute_id') == 43 and attr.get('values'):
                        # 43 is typically the attribute_id for product name
                        name = attr['values'][0].get('value')
                        break
            
            # If still no name, use offer_id as fallback
            if not name:
                name = offer_id

            # Combine with stock information if available
            stock_info = stock_items.get(offer_id, {
                'available': 0,
                'reserved': 0,
                'total_stock': 0
            })
            
            complete_item = {
                'offer_id': offer_id,
                'product_id': product_id,
                'name': name,
                'available': stock_info['available'],
                'reserved': stock_info['reserved'],
                'total_stock': stock_info['total_stock']
            }
            
            complete_inventory.append(complete_item)
        
        # For any stock items that don't have product info, add them with fallback name
        for offer_id, item in stock_items.items():
            if not any(i['offer_id'] == offer_id for i in complete_inventory):
                complete_inventory.append({
                    'offer_id': offer_id,
                    'product_id': item['product_id'],
                    'name': offer_id,  # fallback name
                    'available': item['available'],
                    'reserved': item['reserved'],
                    'total_stock': item['total_stock']
                })
        
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
        
        # Find items with available stock
        active_stock = [item for item in complete_inventory if item.get('available', 0) > 0]
        logger.info(f"SKUs with available stock: {len(active_stock)}")
        
        # Calculate total inventory
        total_available = sum(item.get('available', 0) for item in complete_inventory)
        logger.info(f"Total available inventory: {total_available} units")
        
        # Display first few items for verification
        logger.info("First 5 inventory items:")
        for i, item in enumerate(complete_inventory[:5]):
            logger.info(f"  {i+1}. {item['name']}: {item['total_stock']} total ({item['available']} available)")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to export complete inventory data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()