from playwright.sync_api import sync_playwright
import json
from typing import Dict, List, Any
from data_processor import process_vehicle_data, parse_vehicle_name

BASE_URL = "https://www.ford.com"
# INVENTORY_URL = "https://shop.ford.com/showroom/#/"

# Using the zip code of Marco Island, FL
POSTAL_CODE = '34145'

def build_url(model: str, offset: int = 0) -> str:
    return f"{BASE_URL}/inventory/{model}/results?postalCode={POSTAL_CODE}&radius=20&sort=distance-asc&offset={offset}"

models = [
    'escape',
    'broncosport',
    'bronco',
    'edge',
    'explorer',
    'expedition',
    'maverick',
    'ranger',
    'f150',
    'superduty',
    'transitvanwagon',
    'f150-lightning',
    'mustang',
    'mach-e',
    'e-series-stripped-chassis',
    'eseries-cutaway',
    'f-series-stripped-chassis',
    'transitchassis',
    'superduty',
    'e-transit',
    'chassis-cab',
    'f650-f750'
]

def format_features_and_warranty(data):
    """Format features and warranty information in a clean way."""
    if 'features' in data:
        formatted_features = {}
        for category, items in data['features'].items():
            if isinstance(items, str):
                # Split string into list and clean up
                items = [item.strip() for item in items.split('\n') if item.strip()]
            formatted_features[category] = items
        data['features'] = formatted_features

    if 'warranty' in data:
        if isinstance(data['warranty'], str):
            # Split warranty string into a dictionary
            warranty_items = {}
            for line in data['warranty'].split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    warranty_items[key.strip()] = value.strip()
            data['warranty'] = warranty_items

def extract_vehicle_data(page) -> Dict[str, Any]:
    """Extract specific vehicle data from the details page."""
    data = {}
    
    try:
        # Wait for the actual content to load
        page.wait_for_selector('.Loading_skeletonTitlePreview__V9IIJ', state='detached', timeout=60000)
        page.wait_for_timeout(5000)  # Wait after page load
        
        # Handle cookie consent
        try:
            consent_button = page.wait_for_selector('#onetrust-accept-btn-handler', timeout=10000)
            if consent_button:
                consent_button.click(force=True)
                page.wait_for_timeout(5000)  # Wait after clicking consent
                page.wait_for_selector('#onetrust-consent-sdk', state='hidden', timeout=10000)
        except Exception as e:
            print(f"Error handling cookie consent: {str(e)}")
        
        # Close any open drawers
        try:
            page.wait_for_timeout(2000)
            drawer_selectors = [
                '.drawer_container__0Emu8.drawer_open__6Lc6D',
                'div[class*="drawer"][class*="open"]',
                '[role="dialog"]'
            ]
            
            for selector in drawer_selectors:
                try:
                    open_drawers = page.locator(selector).all()
                    for drawer in open_drawers:
                        if drawer.is_visible():
                            close_button = drawer.locator('button[aria-label="Close"]').first
                            if close_button and close_button.is_visible():
                                close_button.click(force=True)
                                page.wait_for_timeout(5000)  # Wait after closing drawer
                            else:
                                page.mouse.click(0, 0)
                                page.wait_for_timeout(5000)  # Wait after clicking
                            page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"Error handling drawer with selector {selector}: {str(e)}")
            
            page.keyboard.press('Escape')
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Error handling drawers: {str(e)}")
        
        # Get vehicle name and parse it immediately
        try:
            name_element = page.locator('xpath=/html/body/div[2]/main/div/div/div[1]/div[2]/div/span')
            if name_element:
                vehicle_name = name_element.inner_text().strip()
                data['vehicle_name'] = vehicle_name
                page.wait_for_timeout(5000)  # Wait after getting name
                # Parse the name immediately
                parsed_name = parse_vehicle_name(vehicle_name)
                data['parsed_name'] = parsed_name
        except Exception as e:
            print(f"Error getting/parsing vehicle name: {str(e)}")
        
        # Get main image
        try:
            main_img = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/img')
            if main_img:
                data['main_image'] = main_img.get_attribute('src')
                page.wait_for_timeout(5000)  # Wait after getting main image
        except Exception as e:
            print(f"Error getting main image: {str(e)}")
        
        # Get additional images
        try:
            additional_imgs = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div/div//img').all()
            data['additional_images'] = [img.get_attribute('src') for img in additional_imgs if img.get_attribute('src')]
            page.wait_for_timeout(5000)  # Wait after getting additional images
        except Exception as e:
            print(f"Error getting additional images: {str(e)}")
            data['additional_images'] = []
        
        # Get price
        try:
            price_element = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div/span')
            if price_element:
                data['price'] = price_element.inner_text().strip()
                page.wait_for_timeout(5000)  # Wait after getting price
        except Exception as e:
            print(f"Error getting price: {str(e)}")
        
        # Get annual mileage
        try:
            mileage_button = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/button')
            if mileage_button:
                mileage_button.click()
                page.wait_for_timeout(5000)  # Wait after clicking mileage button
            
            mileage_element = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/div/div/div/div/div[3]/div[2]/div[2]/div/div/span')
            if mileage_element:
                data['annual_mileage'] = mileage_element.inner_text().strip()
                page.wait_for_timeout(5000)  # Wait after getting mileage
                
                close_button = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div[2]/div/button')
                if close_button.is_visible():
                    close_button.click(force=True)
                    page.wait_for_timeout(5000)  # Wait after closing mileage drawer
        except Exception as e:
            print(f"Error getting annual mileage: {str(e)}")
        
        # Get specifications
        specs = {}
        try:
            specs['horsepower'] = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[2]/dl/div[2]/div/dd/span').inner_text().strip()
            specs['epa_range'] = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[2]/dl/div[1]/div/dd/span').inner_text().strip()
            specs['torque'] = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[2]/dl/div[3]/div/dd/span').inner_text().strip()
            specs['exterior_color'] = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[2]/dl/div[5]/div/dd/span').inner_text().strip()
            specs['interior_color'] = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[2]/dl/div[6]/div/dd/span').inner_text().strip()
            specs['wheel_type'] = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[2]/dl/div[7]/div/dd/span').inner_text().strip()
            specs['drive'] = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[2]/dl/div[8]/div/dd/span').inner_text().strip()
            data['specifications'] = specs
            page.wait_for_timeout(5000)  # Wait after getting specifications
        except Exception as e:
            print(f"Error getting specifications: {str(e)}")
            data['specifications'] = {}
        
        # Get features
        features = {}
        try:
            features_section = page.locator('text=Features & Options')
            if features_section.is_visible():
                features_section.scroll_into_view_if_needed()
                page.wait_for_timeout(5000)  # Wait after scrolling
            
            def click_feature_button(button_text):
                button = page.locator(f'button:has-text("{button_text}")')
                if not button.is_visible():
                    button = page.locator(f'h3:has-text("{button_text}") button')
                
                if button.is_visible():
                    button.scroll_into_view_if_needed()
                    page.wait_for_timeout(5000)  # Wait before clicking
                    
                    try:
                        button.click(force=True, timeout=5000)
                    except:
                        try:
                            page.evaluate("button => button.click()", button.element_handle())
                        except:
                            page.evaluate("""button => {
                                button.dispatchEvent(new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }));
                            }""", button.element_handle())
                    
                    page.wait_for_timeout(5000)  # Wait after clicking
                    
                    try:
                        content = page.locator(f'div[role="region"]:has(h3:has-text("{button_text}")) ul')
                        if content.count() > 0:
                            all_text = []
                            for i in range(content.count()):
                                element_text = content.nth(i).inner_text().strip()
                                if element_text:
                                    items = [item.strip() for item in element_text.split('\n') if item.strip()]
                                    all_text.extend(items)
                            
                            button.click(force=True)
                            page.wait_for_timeout(5000)  # Wait after getting content
                            return all_text
                        else:
                            content = page.locator(f'div:has(h3:has-text("{button_text}")) ul')
                            if content.count() > 0:
                                all_text = []
                                for i in range(content.count()):
                                    element_text = content.nth(i).inner_text().strip()
                                    if element_text:
                                        items = [item.strip() for item in element_text.split('\n') if item.strip()]
                                        all_text.extend(items)
                                
                                button.click(force=True)
                                page.wait_for_timeout(5000)  # Wait after getting content
                                return all_text
                    except Exception as e:
                        print(f"Error extracting {button_text.lower()} content: {str(e)}")
                return None
            
            for section in ['Exterior', 'Interior', 'Functional']:
                try:
                    content = click_feature_button(section)
                    if content:
                        features[section.lower()] = content
                        page.wait_for_timeout(5000)  # Wait after processing section
                except Exception as e:
                    print(f"Error getting {section.lower()} features: {str(e)}")
            
            data['features'] = features
            format_features_and_warranty(data)
            page.wait_for_timeout(5000)  # Wait after formatting features
            
        except Exception as e:
            print(f"Error in feature extraction process: {str(e)}")
            data['features'] = {}
        
        # Get warranty information
        try:
            warranty_button = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[4]/div/div[1]/div[6]/h3/button')
            if warranty_button:
                warranty_button.scroll_into_view_if_needed()
                page.wait_for_timeout(5000)  # Wait before clicking warranty
                page.evaluate("(button) => button.click()", warranty_button.element_handle())
                try:
                    page.wait_for_selector('xpath=/html/body/div[2]/main/div/div/div[2]/div[4]/div/div[1]/div[6][@data-state="open"]', timeout=5000)
                    warranty_list = page.locator('xpath=/html/body/div[2]/main/div/div/div[2]/div[4]/div/div[1]/div[6]/div/div/ul')
                    if warranty_list:
                        data['warranty'] = warranty_list.inner_text().strip()
                        warranty_button.click(force=True)
                        page.wait_for_timeout(5000)  # Wait after getting warranty
                    else:
                        data['warranty'] = "No warranty information available"
                except Exception as e:
                    print(f"Error getting warranty content: {str(e)}")
                    data['warranty'] = "No warranty information available"
            else:
                data['warranty'] = "No warranty information available"
        except Exception as e:
            print(f"Error getting warranty: {str(e)}")
            data['warranty'] = "No warranty information available"
        
    except Exception as e:
        print(f"Error extracting vehicle data: {str(e)}")
    
    return data

def scrape_vehicle_data() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Scrape all vehicle data for each model."""
    model_data = {}
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Gecko/20100101 Firefox/95.0",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        for model in models:
            print(f"\nScraping data for model: {model}")
            offset = 0
            has_next_page = True
            model_data[model] = {}

            while has_next_page:
                current_url = build_url(model, offset)
                
                try:
                    # Try to load the page with retries
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            page.goto(current_url, wait_until="networkidle", timeout=120000)
                            page.wait_for_timeout(5000)  # Wait after page load
                            break
                        except Exception as e:
                            if attempt == max_retries - 1:
                                raise e
                            print(f"Retry {attempt + 1}/{max_retries} loading page: {str(e)}")
                            page.wait_for_timeout(5000)
                    
                    # Wait for the vehicle details section to load
                    page.wait_for_selector('.ford-baseball-card_detailsButtonSection__dUz3X', timeout=120000)
                    page.wait_for_timeout(5000)  # Wait after details section loads
        
                    # Get all vehicle details elements
                    vehicle_elements = page.locator('.ford-baseball-card_detailsButtonSection__dUz3X').all()
                    
                    for element in vehicle_elements:
                        # Get the link element
                        link = element.locator('a').first
                        if link:
                            href = link.get_attribute('href')
                            # Extract VIN from the URL
                            vin = href.split('/vin/')[1].split('/')[0] if '/vin/' in href else href
                            
                            # Navigate to the vehicle details page
                            vehicle_url = f"{BASE_URL}{href}"
                            try:
                                print(f"Processing VIN: {vin}")
                                page.goto(vehicle_url, wait_until="networkidle", timeout=120000)
                                page.wait_for_timeout(5000)  # Wait after navigating to vehicle page
                                
                                # Extract and process the vehicle data
                                vehicle_data = extract_vehicle_data(page)
                                vehicle_data['vin'] = vin
                                
                                # Print parsed name information
                                if 'parsed_name' in vehicle_data:
                                    parsed = vehicle_data['parsed_name']
                                    print(f"  Year: {parsed['year']}")
                                    print(f"  Make: {parsed['make']}")
                                    print(f"  Model: {parsed['model']}")
                                    print(f"  Trim: {parsed['trim']}")
                                
                                # Use vehicle_name as the key instead of VIN
                                if 'vehicle_name' in vehicle_data:
                                    vehicle_name = vehicle_data['vehicle_name']
                                    model_data[model][vehicle_name] = vehicle_data
                                else:
                                    # Fallback to VIN if vehicle_name is not available
                                    model_data[model][vin] = vehicle_data
                                
                                # Save progress after each vehicle
                                try:
                                    with open('vehicle_data.json', 'w') as f:
                                        json.dump(model_data, f, indent=2)
                                    print("  Saved. Waiting 5 seconds...")
                                    page.wait_for_timeout(5000)  # 5-second delay after saving
                                except Exception as e:
                                    print(f"Error saving progress: {str(e)}")
                                
                                page.goto(current_url, wait_until="networkidle", timeout=120000)
                                page.wait_for_timeout(5000)  # Wait after returning to main page
                            except Exception as e:
                                print(f"Error processing vehicle {vin}: {str(e)}")
                                continue

                    # Check if next button is disabled
                    next_button = page.locator('button[data-testid="next-button"]')
                    is_disabled = next_button.get_attribute('disabled') is not None
                    
                    if is_disabled:
                        has_next_page = False
                    else:
                        offset += 12  # Increment offset for next page
                        page.wait_for_timeout(5000)  # Wait before next page
                except Exception as e:
                    print(f"Error processing page: {str(e)}")
                    has_next_page = False
        
        browser.close()
    return model_data

if __name__ == "__main__":
    # First, scrape the data
    results = scrape_vehicle_data()
    print("\nScraping complete. Results saved to vehicle_data.json")
    
    # Then, process the vehicle names
    print("\nProcessing vehicle names...")
    processed_results = process_vehicle_data(results)
    
    # Save the processed results
    try:
        with open('processed_vehicle_data.json', 'w') as f:
            json.dump(processed_results, f, indent=2)
        print("Processed results saved to processed_vehicle_data.json")
    except Exception as e:
        print(f"Error saving processed results: {str(e)}")
