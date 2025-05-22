# Script to attempt crawling Goodfellow & Co products from Target.com.
# The initial goal was to fetch product information (name, price, URL)
# for this brand and potentially save it.

# Note: This script is the result of an investigation into scraping Target.com.
# It was determined that Target.com loads its product search results and
# much of its product data dynamically using JavaScript.
# The methods employed in this script (fetching static HTML with `requests`
# and parsing it with `BeautifulSoup`, including attempts to find embedded JSON)
# were ultimately UNRELIABLE for consistently extracting product data
# from search result pages. This script is preserved as a demonstration of
# these attempts and their outcome. For reliable scraping of Target.com,
# tools that can render JavaScript (e.g., Selenium, Playwright) would
# likely be necessary.

import requests
from bs4 import BeautifulSoup
import re # re was used in some JSON parsing attempts for price cleaning
import json # For parsing embedded JSON data

if __name__ == "__main__":
    # Target brand for the search
    brand_name = "goodfellow"
    print(f"Attempting to fetch data for brand: '{brand_name}'")

    # --- Logic from former fetch_search_page function ---
    # Construct the search URL
    search_url = f"https://www.target.com/s?searchTerm={brand_name}"
    
    # Standard headers to mimic a browser request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Fetching URL: {search_url}")
    
    html_content = None
    try:
        # Make the HTTP GET request
        response = requests.get(search_url, headers=headers, timeout=10)
        # Raise an exception for HTTP errors (4xx or 5xx)
        response.raise_for_status()
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Successfully fetched HTML content.")
            html_content = response.text
            # print(f"HTML content snippet (first 500 chars): {html_content[:500]}") # Optional: for quick check
        else:
            # This case might not be reached if raise_for_status() triggers first
            print(f"Error fetching page: Status code {response.status_code}")
            
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Status code: {response.status_code if 'response' in locals() else 'N/A'}")
        # print(f"Response content snippet: {response.text[:500] if 'response' in locals() else 'N/A'}...")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred during the request: {err}")
    # --- End of former fetch_search_page logic ---

    products = []
    if html_content:
        print("\nAttempting to parse product data from fetched HTML...")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # --- Start of former parse_product_data logic (now heavily commented) ---
        # The following section represents the latest attempt to parse product data,
        # primarily by looking for embedded JSON in script tags.
        # Previous attempts to parse the direct HTML structure (e.g., specific divs,
        # data-test attributes) for product cards failed because the product information
        # is not consistently present in the static HTML for search result pages.

        print("Searching for embedded JSON data in <script> tags...")
        scripts = soup.find_all('script')
        
        # Attempt 1: Look for __TGT_INITIAL_REhydration_DATA__
        # This variable name was observed in some analyses of Target's website as
        # potentially holding initial page data.
        found_tgt_rehydration_data = False
        for script in scripts:
            script_content = script.string
            if script_content and '__TGT_INITIAL_REhydration_DATA__' in script_content:
                found_tgt_rehydration_data = True
                print("Found script tag potentially containing '__TGT_INITIAL_REhydration_DATA__'.")
                # Actual parsing logic for this was complex and involved trying to
                # navigate a large JSON structure. It included:
                # 1. Extracting the JSON string (e.g., `script_content.split('window.__TGT_INITIAL_REhydration_DATA__ = ', 1)[-1]`)
                # 2. Cleaning it (e.g., removing trailing semicolons).
                # 3. Parsing with `json.loads()`.
                # 4. Navigating known paths (e.g., `data['search_response']['products']`)
                # 5. A generic recursive search for lists of product-like objects if known paths failed.
                # This approach was ultimately unreliable as the structure varied or product lists were not found.
                print("  Detailed parsing of this data was attempted but proved unreliable for consistent product extraction.")
                break # Process only the first occurrence if found
        if not found_tgt_rehydration_data:
            print("Script tag with '__TGT_INITIAL_REhydration_DATA__' not found.")

        # Attempt 2: Look for application/ld+json (if __TGT_INITIAL_REhydration_DATA__ didn't yield results)
        # JSON-LD is a standard way to embed structured data.
        if not products: # Only attempt if previous method didn't populate products
            found_ld_json_tags = False
            for script in scripts:
                script_content = script.string
                if script_content and script.get('type') == 'application/ld+json':
                    found_ld_json_tags = True
                    print("Found <script type='application/ld+json'> tag.")
                    # Parsing logic for LD+JSON involved:
                    # 1. Parsing with `json.loads(script_content)`.
                    # 2. Checking if the root was a list of products or an object with `@graph` or `itemListElement`.
                    # 3. Extracting 'name', 'url', and 'offers' (for price) from items with `@type: "Product"`.
                    # This also proved unreliable for finding a comprehensive list of search results.
                    # Sometimes it contained data for a single product or unrelated structured data.
                    print("  Detailed parsing of LD+JSON was attempted but was not consistently fruitful for search listings.")
                    # For this refactored version, we won't attempt the full parse again.
                    # We're just noting that this was a strategy.
                    # If products were found, the list would be populated here. Example:
                    # try:
                    #     ld_data = json.loads(script_content)
                    #     # ... (logic to extract products from ld_data) ...
                    # except json.JSONDecodeError:
                    #     print("    Could not parse LD+JSON content.")
            if not found_ld_json_tags:
                print("No <script type='application/ld+json'> tags found.")
        
        # --- End of former parse_product_data logic ---

        if not products: # If products list is still empty after JSON attempts
            print("\nNo product data successfully extracted from embedded JSON.")
            print("This is expected for Target.com search pages, as product data is typically loaded dynamically.")
            print("Previous attempts to parse HTML directly (looking for specific tags/classes like 'ProductCard') also failed for the same reason.")
        
    else:
        print("No HTML content was fetched, so parsing cannot be attempted.")

    # Final output based on parsing attempts
    if products:
        print(f"\nSuccessfully parsed {len(products)} products (this is unexpected and likely from a non-standard page structure or error in logic).")
        print("Details of the first 1-2 products found:")
        for i, product in enumerate(products[:2]):
            print(f"  Product {i+1}: Name: {product.get('name', 'N/A')}, Price: {product.get('price', 'N/A')}, URL: {product.get('url', 'N/A')}")
    else:
        print("\nNo products found or failed to parse product data, as expected due to dynamic content.")

    print("\nScript finished.")
    # End of main execution block
