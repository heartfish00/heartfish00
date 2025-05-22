import requests
from bs4 import BeautifulSoup
import re
import json # For parsing embedded JSON data

def fetch_search_page(brand_name):
    """
    Fetches the Target.com search results page for a given brand name.

    Args:
        brand_name (str): The brand name to search for.

    Returns:
        str or None: The HTML content of the page if successful, None otherwise.
    """
    url = f"https://www.target.com/s?searchTerm={brand_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Fetching URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        if response.status_code == 200:
            return response.text
        else:
            print(f"Error: Received status code {response.status_code}")
            return None
            
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Status code: {response.status_code}")
        print(f"Response content: {response.text[:500]}...") # Print some of the response
        return None
    except requests.exceptions.RequestException as err:
        print(f"An error occurred: {err}")
        return None

def parse_product_data(html_content):
    """
    Parses product information from HTML content.

    Args:
        html_content (str): The HTML content of the search results page.

    Returns:
        list: A list of dictionaries, where each dictionary contains
              the name, price, and URL of a product. Returns an empty
              list if no products are found or if parsing fails.
    """
    products = []
    if not html_content:
        return products

    soup = BeautifulSoup(html_content, 'html.parser')

    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script')
    
    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script')
    
    # Attempt 1: __TGT_INITIAL_REhydration_DATA__
    for script in scripts:
        script_content = script.string
        if script_content and '__TGT_INITIAL_REhydration_DATA__' in script_content:
            print("Found script with '__TGT_INITIAL_REhydration_DATA__'")
            try:
                json_str = script_content.split('window.__TGT_INITIAL_REhydration_DATA__ = ', 1)[-1].strip()
                if json_str.endswith(';'): json_str = json_str[:-1]
                data = json.loads(json_str)
                
                def find_product_lists_recursive(json_obj): # Note: Renamed for clarity if used elsewhere
                    found_lists_rehydration = []
                    if isinstance(json_obj, dict):
                        for k, v_rehydration in json_obj.items():
                            if isinstance(v_rehydration, list) and len(v_rehydration) > 0:
                                product_like_score_rehydration = 0
                                for item_check_rehydration in v_rehydration[:min(len(v_rehydration),3)]:
                                    if isinstance(item_check_rehydration, dict) and \
                                       ('tcin' in item_check_rehydration or 'id' in item_check_rehydration or 'title' in item_check_rehydration or 'name' in item_check_rehydration) and \
                                       ('price' in item_check_rehydration or 'priceInfo' in item_check_rehydration or 'offers' in item_check_rehydration) and \
                                       ('url' in item_check_rehydration or 'link' in item_check_rehydration or 'product_url' in item_check_rehydration):
                                        product_like_score_rehydration +=1
                                if product_like_score_rehydration >=1:
                                    found_lists_rehydration.append(v_rehydration)
                            elif isinstance(v_rehydration, (dict, list)):
                                found_lists_rehydration.extend(find_product_lists_recursive(v_rehydration))
                    elif isinstance(json_obj, list):
                        for item_in_list_rehydration in json_obj:
                            found_lists_rehydration.extend(find_product_lists_recursive(item_in_list_rehydration))
                    return found_lists_rehydration

                product_list_candidates_rehydration = find_product_lists_recursive(data)
                if product_list_candidates_rehydration:
                    print(f"Generic recursive search found {len(product_list_candidates_rehydration)} potential product list(s) in __TGT_INITIAL_REhydration_DATA__.")

                for product_list_rehydration in product_list_candidates_rehydration:
                    if not product_list_rehydration or not isinstance(product_list_rehydration, list): continue
                    current_run_products_rehydration = []
                    for item_rehydration in product_list_rehydration:
                        if not isinstance(item_rehydration, dict): continue
                        name_rehydration, url_rehydration, price_str_rehydration = None, None, None
                        name_rehydration = item_rehydration.get('title') or item_rehydration.get('name')
                        if not name_rehydration and isinstance(item_rehydration.get('item'), dict): name_rehydration = item_rehydration['item'].get('title')

                        url_path_rehydration = item_rehydration.get('url')
                        if not url_path_rehydration and isinstance(item_rehydration.get('item'), dict) and isinstance(item_rehydration['item'].get('enrichment_data'), dict):
                             url_path_rehydration = item_rehydration['item']['enrichment_data'].get('product_url')
                        if url_path_rehydration:
                            url_rehydration = f"https://www.target.com{url_path_rehydration}" if url_path_rehydration.startswith('/') else url_path_rehydration
                        elif item_rehydration.get('tcin'): url_rehydration = f"https://www.target.com/p/-/A-{item_rehydration['tcin']}"

                        price_data_rehydration = item_rehydration.get('price')
                        if isinstance(price_data_rehydration, dict):
                            if price_data_rehydration.get('current_retail') is not None: price_str_rehydration = f"${price_data_rehydration['current_retail']}"
                            elif price_data_rehydration.get('formatted_current_price'): price_str_rehydration = price_data_rehydration['formatted_current_price']
                        
                        if name_rehydration and url_rehydration and price_str_rehydration:
                            if not any(p['url'] == url_rehydration.strip() for p in products) and \
                               not any(crp['url'] == url_rehydration.strip() for crp in current_run_products_rehydration) :
                                current_run_products_rehydration.append({'name': name_rehydration.strip(), 'price': price_str_rehydration.strip(), 'url': url_rehydration.strip()})
                    if current_run_products_rehydration:
                        products.extend(current_run_products_rehydration)
                        print(f"Parsed {len(current_run_products_rehydration)} products from a list in __TGT_INITIAL_REhydration_DATA__.")
                        return products 
            except Exception as e_rehydration:
                # print(f"Error in __TGT_INITIAL_REhydration_DATA__: {e_rehydration}")
                pass

    # Attempt 2: application/ld+json (if first method yielded no results)
    if not products: 
        for script in scripts:
            script_content = script.string
            if not script_content or script.get('type') != 'application/ld+json': continue
            print("Found script with type='application/ld+json'")
            try:
                ld_json_data = json.loads(script_content)
                item_list_ld = []
                # More specific extraction for LD+JSON structures
                if isinstance(ld_json_data, list): # Root is a list of items
                    for item_in_list in ld_json_data:
                        if isinstance(item_in_list, dict) and item_in_list.get('@type') == 'Product':
                            item_list_ld.append(item_in_list)
                elif isinstance(ld_json_data.get('@graph'), list): # Items are in @graph
                    for item_in_graph in ld_json_data['@graph']:
                        if isinstance(item_in_graph, dict) and item_in_graph.get('@type') == 'Product':
                            item_list_ld.append(item_in_graph)
                elif ld_json_data.get('@type') == 'ItemList' and isinstance(ld_json_data.get('itemListElement'), list):
                    for entry_ld in ld_json_data.get('itemListElement', []):
                        item_content_ld = entry_ld.get('item', entry_ld) 
                        if isinstance(item_content_ld, dict) and item_content_ld.get('@type') == 'Product':
                            item_list_ld.append(item_content_ld)
                elif ld_json_data.get('@type') == 'Product': # Root is a single Product
                    item_list_ld.append(ld_json_data)

                temp_ld_products = []
                for item_ld in item_list_ld: # Renamed item to item_ld for clarity
                    if not isinstance(item_ld, dict) or item_ld.get('@type') != 'Product': continue
                    name_ld, url_ld_val, price_ld_val_str = item_ld.get('name'), item_ld.get('url'), None # Renamed variables
                    offers_data_ld = item_ld.get('offers')
                    current_offer_ld = None
                    if isinstance(offers_data_ld, list) and offers_data_ld: current_offer_ld = offers_data_ld[0]
                    elif isinstance(offers_data_ld, dict): current_offer_ld = offers_data_ld
                    
                    if isinstance(current_offer_ld, dict):
                        price_keys_ld = ['price', 'lowPrice', 'highPrice']
                        for key_ld in price_keys_ld:
                            val_ld = current_offer_ld.get(key_ld)
                            if val_ld is not None: price_ld_val_str = str(val_ld); break 
                    
                    if name_ld and url_ld_val and price_ld_val_str and price_ld_val_str != "None":
                        url_ld_abs = f"https://www.target.com{url_ld_val}" if url_ld_val.startswith('/') else url_ld_val
                        if not url_ld_abs.startswith('http') : url_ld_abs = f"https://www.target.com/{url_ld_abs.lstrip('/')}" # Ensure only one slash if adding

                        if not any(p['url'] == url_ld_abs.strip() for p in products) and \
                           not any(tp['url'] == url_ld_abs.strip() for tp in temp_ld_products):
                            temp_ld_products.append({'name': name_ld.strip(), 'price': f"${price_ld_val_str}", 'url': url_ld_abs.strip()})
                
                if temp_ld_products:
                    products.extend(temp_ld_products)
                    print(f"Parsed {len(temp_ld_products)} products from LD+JSON.")
                    return products # Return if LD+JSON was successful
            except Exception as e_ld: # Renamed exception variable
                # print(f"Error in application/ld+json: {e_ld}")
                pass
                
    if not products:
        print("No product data found in any embedded JSON.")
    return products

if __name__ == "__main__":
    brand = "goodfellow"
    print(f"Attempting to fetch search results for brand: '{brand}'")
    html_content = fetch_search_page(brand)

    if html_content:
        print("Successfully fetched page content.")
        # print("First 500 characters of the HTML content:")
        # print(html_content[:500]) #  No longer needed, focus on parsed data

        print("\nAttempting to parse product data...")
        parsed_products = parse_product_data(html_content)

        if parsed_products:
            print(f"\nSuccessfully parsed {len(parsed_products)} products.")
            print("Details of the first 1-2 products:")
            for i, product in enumerate(parsed_products[:2]): # Print first two products
                print(f"Product {i+1}:")
                print(f"  Name: {product['name']}")
                print(f"  Price: {product['price']}")
                print(f"  URL: {product['url']}")
        else:
            print("\nNo products found or failed to parse product data.")
            # It's useful to print a snippet of HTML here if parsing fails, to help debug selectors
            # print("\nHTML snippet for debugging (first 1000 chars):")
            # print(html_content[:1000])


    else:
        print("Failed to fetch page content.")
