import requests
from bs4 import BeautifulSoup
import datetime # Import the datetime module
import json # Add json import for loading config

# Main script for the Newsletter Generator

APPAREL_KEYWORDS = [
    "tee", "t-shirt", "shirt", "hoodie", "sweatshirt", "jacket", "coat", "pant", "trouser", "jean", "denim",
    "dress", "skirt", "blouse", "sweater", "knitwear", "footwear", "shoe", "sneaker", "boot", "accessory",
    "bag", "hat", "scarf", "glove", "textile", "fabric", "cotton", "polyester", "wool", "silk", "leather",
    "garment", "sourcing", "trend", "retail", "apparel", "fashion", "clothing", "outfit", "look", "style",
    "designer", "brand", "collection", "runway", "couture", "sustainable", "sustainability", "ethical",
    "manufacturing", "supply chain", "e-commerce", "consumer", "market", "shop", "store", "boutique",
    "textile industry", "fashion tech", "athleisure", "streetwear", "vintage", "resale"
]
# Convert all keywords to lowercase for case-insensitive matching
APPAREL_KEYWORDS = [keyword.lower() for keyword in APPAREL_KEYWORDS]

# Sumy imports for summarization
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer as SumyTokenizer # Alias to avoid conflict if NLTK Tokenizer is used
from sumy.summarizers.lsa import LsaSummarizer
# from sumy.summarizers.luhn import LuhnSummarizer # Luhn is another option
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words as sumy_get_stop_words


# For more advanced filtering, consider stemming/lemmatization (e.g., with NLTK)
# to match word roots (e.g., "trend" matching "trending", "trends").

def filter_articles_by_title(articles_by_site, keywords):
    """
    Filters articles based on the presence of keywords in their titles.

    Args:
        articles_by_site (dict): A dictionary where keys are site URLs and 
                                 values are lists of article dictionaries 
                                 (each with 'title' and 'url').
        keywords (list): A list of keywords (assumed to be lowercase).

    Returns:
        dict: A new dictionary structured like articles_by_site, 
              containing only the filtered articles.
    """
    filtered_articles_by_site = {}
    for site_url, articles_list in articles_by_site.items():
        site_filtered_articles = []
        for article in articles_list:
            title_lower = article['title'].lower()
            if any(keyword in title_lower for keyword in keywords):
                site_filtered_articles.append(article)
        
        if site_filtered_articles: # Only add site to results if it has relevant articles
            filtered_articles_by_site[site_url] = site_filtered_articles
            
    return filtered_articles_by_site

def summarize_text(text, num_sentences=3, language="english"):
    """
    Summarizes the given text using sumy's LSA Summarizer.

    Args:
        text (str): The text content to summarize.
        num_sentences (int): The desired number of sentences in the summary.
        language (str): The language of the text (for stop words and tokenizer).

    Returns:
        str: The summarized text, or an error message if summarization fails.
    """
    if not text or not text.strip():
        return "Cannot summarize empty text."
    try:
        parser = PlaintextParser.from_string(text, SumyTokenizer(language))
        stemmer = Stemmer(language)
        
        # Using LSA Summarizer (Luhn is another good option)
        summarizer = LsaSummarizer(stemmer)
        summarizer.stop_words = sumy_get_stop_words(language)
        
        summary_sentences = []
        for sentence in summarizer(parser.document, num_sentences):
            summary_sentences.append(str(sentence))
        
        return " ".join(summary_sentences)
    except Exception as e:
        print(f"Error during summarization: {e}")
        # Fallback: return first few sentences of the original text if sumy fails hard
        # This is a very basic fallback.
        try:
            # Simple sentence split, not as robust as NLTK's sent_tokenize
            sentences = text.split('.') 
            fallback_summary = ". ".join(sentences[:num_sentences]).strip()
            if fallback_summary:
                 return f"Summarization failed. Fallback: {fallback_summary}."
            else:
                return "Summarization failed. Content was minimal."
        except Exception as fallback_e:
            print(f"Error during basic fallback summarization: {fallback_e}")
            return "Summarization failed and fallback also failed."


def get_article_content(article_url):
    """
    Fetches and extracts the main text content from an article URL.

    Args:
        article_url (str): The URL of the article.

    Returns:
        str: The extracted text content as a single string, or None if fetching/extraction fails.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Common selectors for article content. This list can be expanded.
        # Order can matter: more specific or common ones first.
        content_selectors = [
            'article',
            'div.article-content',
            'div.article-body',
            'div.post-content',
            'div.entry-content',
            'div.td-post-content', # Common in some news themes
            'div.story-content',   # Common in other news themes
            'main#main',
            'div#content',
            'div.content',
            'div.text', # For ITNK and similar
            'div.main-content',
            'div.postarea', # For Tistory
            'div.article_body', # General
            'div.news_article', # General
            'div#article_body_content', # Sourcing Journal specific based on quick check
            'div.lpHolder', # WWD specific based on quick check
            'div.article-body__content', # Retail Dive
            'div.body.e1s846r30', # Business of Fashion
            'div.article-text', # FashionUnited
            'div.newscontent', # FashionNetwork
            'article#contents', # ApparelNews
            'div.tt_article_useless_p_margin', # Tistory common content wrapper
        ]

        text_parts = []
        content_found = False

        for selector in content_selectors:
            content_area = soup.select_one(selector)
            if content_area:
                # Remove script, style, ad elements, etc.
                for unwanted_tag in content_area.find_all(['script', 'style', 'aside', 'figure', 'figcaption', '.advertisement', '.ads', '.ad', 'nav', 'header', 'footer', '.related-articles', '.share-buttons']):
                    unwanted_tag.decompose()
                
                # Get all paragraph texts, or if no paragraphs, the whole text of the area
                paragraphs = content_area.find_all('p')
                if paragraphs:
                    for p in paragraphs:
                        text_parts.append(p.get_text(separator=' ', strip=True))
                else: # If no <p> tags, get text from the content_area directly, might be less clean
                    text_parts.append(content_area.get_text(separator=' ', strip=True))
                
                content_found = True
                break # Stop after finding the first matching selector that yields content

        if not content_found:
            # Fallback: try to get all text from body and hope for the best (can be very noisy)
            # This is a last resort and might not be very effective.
            body_text = soup.body.get_text(separator=' ', strip=True)
            if body_text:
                text_parts.append(body_text)
                # print(f"Warning: Used fallback (body text) for {article_url}. Content might be noisy.")
            else:
                print(f"Could not find main content for {article_url} using defined selectors or body fallback.")
                return None
        
        return "\n".join(text_parts).strip()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching content for {article_url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing content for {article_url}: {e}")
        return None

def get_articles_sourcing_journal(url):
    """
    Fetches articles from Sourcing Journal published within the last 7 days.

    Args:
        url (str): The URL of the Sourcing Journal website.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        response = requests.get(url, timeout=10) # Added timeout
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')
        
        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)

        for item in soup.find_all('article'):
            try:
                title_element = item.find('h3', class_='c-title')
                if not title_element:
                    continue

                link_element = title_element.find('a')
                if not link_element or not link_element.has_attr('href'):
                    continue
                
                title = link_element.text.strip()
                url = link_element['href']

                time_element = item.find('time', class_='c-date')
                if not time_element or not time_element.has_attr('datetime'):
                    continue
                
                # The datetime attribute is in 'YYYY-MM-DDTHH:MM:SSZ' format
                article_date_str = time_element['datetime'].split('T')[0]
                article_date = datetime.datetime.strptime(article_date_str, '%Y-%m-%d').date()

                if article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': url})
            except Exception as e:
                print(f"Error parsing an article: {e}") # Log error and continue
                continue


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
    except Exception as e: # Catch other potential exceptions during parsing
        print(f"An error occurred: {e}")
    
    return articles

def get_articles_wwd(url):
    """
    Fetches articles from WWD.com published within the last 7 days.

    Args:
        url (str): The URL of the WWD.com website.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)

        for item in soup.find_all('li', class_='o-tease-news'): # Common pattern for WWD articles
            try:
                title_element = item.find('h3', class_='c-title')
                if not title_element:
                    continue

                link_element = title_element.find('a')
                if not link_element or not link_element.has_attr('href'):
                    continue
                
                title = link_element.text.strip()
                url = link_element['href']
                
                # WWD URLs are sometimes relative, so make them absolute
                if not url.startswith('http'):
                    # Need to get the base URL from the response object or hardcode if necessary
                    # For now, assuming WWD.com base if relative
                    if url.startswith('/'):
                        url = "https://wwd.com" + url
                    else:
                        url = "https://wwd.com/" + url


                time_element = item.find('time', class_='c-date')
                if not time_element or not time_element.has_attr('datetime'):
                    # Sometimes the date might be in a different element or missing
                    # Try to find date in a span with class 'c-timestamp' as a fallback
                    time_element_alt = item.find('span', class_='c-timestamp')
                    if time_element_alt:
                        date_text = time_element_alt.text.strip()
                        # WWD uses formats like "August 29, 2023, 10:00am" or "1h ago" or "Yesterday"
                        # This requires more sophisticated date parsing
                        # For simplicity, we'll try a specific format first, then handle relative dates
                        try:
                            article_date = datetime.datetime.strptime(date_text, '%B %d, %Y, %I:%M%p').date()
                        except ValueError:
                            # Handle relative dates like "1h ago", "Yesterday"
                            if "ago" in date_text.lower(): # if it's recent, include it
                                article_date = today
                            elif "yesterday" in date_text.lower():
                                article_date = today - datetime.timedelta(days=1)
                            else: # Skip if date format is not recognized or too old
                                print(f"Skipping article due to unrecognized date format: {title} - {date_text}")
                                continue
                    else:
                        print(f"Skipping article due to missing date: {title}")
                        continue # Skip if no date found
                else:
                    article_date_str = time_element['datetime'].split('T')[0]
                    article_date = datetime.datetime.strptime(article_date_str, '%Y-%m-%d').date()


                if article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': url})
            except Exception as e:
                print(f"Error parsing a WWD article: {title} - {e}") # Log error and continue
                continue

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles

def get_articles_retail_dive(url):
    """
    Fetches articles from Retail Dive published within the last 7 days.

    Args:
        url (str): The URL of the Retail Dive website.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        base_url = "https://www.retaildive.com"

        # Retail Dive has different sections (news, library, etc.)
        # The main news feed seems to be primary for articles
        article_list = soup.find_all('li', class_='row feed__item')
        if not article_list: # Fallback for other list structures if any
            article_list = soup.find_all('div', class_='list-item-wrapper')


        for item in article_list:
            try:
                title_element = item.find('h3', class_='feed__title')
                if not title_element or not title_element.find('a'):
                    continue
                
                title = title_element.find('a').text.strip()
                link_href = title_element.find('a')['href']
                
                if not link_href.startswith('http'):
                    url = base_url + link_href
                else:
                    url = link_href

                date_element = item.find('span', class_='secondary-label')
                date_text = ""
                if date_element:
                    date_text = date_element.text.strip()
                else: # Try another common location for dates
                    date_wrapper = item.find('div', class_='feed__content-wrapper')
                    if date_wrapper:
                        secondary_label = date_wrapper.find('span', class_='secondary-label')
                        if secondary_label:
                             date_text = secondary_label.text.strip()


                if not date_text or "Published " not in date_text:
                    # Fallback: check for <meta property="article:published_time" content="YYYY-MM-DDTHH:MM:SSZ" />
                    # This is less ideal as it might require fetching each article URL
                    # For now, if primary date is not found, skip or try to infer from URL structure if possible
                    # Or, if the site consistently has it elsewhere, update selector.
                    # For Retail Dive, the "Published Month Day, Year" format is common.
                    print(f"Skipping article due to missing or unrecognized date format: {title} - Date text: '{date_text}'")
                    continue
                
                # Extract date part after "Published "
                article_date_str = date_text.replace("Published ", "").strip()
                
                # Retail Dive uses "Month Day, Year" e.g. "Oct. 2, 2023" or "Sept. 29, 2023"
                # Python's strptime needs specific month abbreviations.
                article_date_str = article_date_str.replace("Sept.", "Sep") # Common abbreviation
                
                try:
                    article_date = datetime.datetime.strptime(article_date_str, '%b. %d, %Y').date()
                except ValueError:
                    try: # Try without dot if Sep instead of Sep.
                        article_date = datetime.datetime.strptime(article_date_str, '%b %d, %Y').date()
                    except ValueError as ve:
                        print(f"Error parsing date '{article_date_str}' for article '{title}': {ve}")
                        continue


                if article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': url})
            except Exception as e:
                print(f"Error parsing a Retail Dive article: {title} - {e}")
                continue

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles

def get_articles_bof(url):
    """
    Fetches articles from Business of Fashion published within the last 7 days.

    Args:
        url (str): The URL of the Business of Fashion website.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        # Business of Fashion might be tricky due to paywalls/dynamic content.
        # Headers might be needed to mimic a browser.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7) # For potential future use if dates become available
        base_url = "https://www.businessoffashion.com"

        # BoF structure can be complex and dynamic. These are potential selectors.
        # Prioritize common article list patterns.
        # Example: list items or specific article teaser divs
        # Note: BoF's dates are often not easily accessible on list pages without JS rendering or are relative like "2 hours ago".
        # This scraper will focus on getting the latest headlines and links.
        # True date filtering for the "last 7 days" is difficult without more advanced tools (like Selenium) or API access.
        
        # Looking for common container patterns for articles
        # This is a guess based on typical modern web layouts. May need adjustment.
        possible_article_containers = soup.find_all('li') # A common list pattern
        if not possible_article_containers:
            # Fallback to another common pattern, div with a class that implies a card or teaser
            possible_article_containers = soup.find_all('div', attrs={'data-test-id': 'item-card'}) # Example, specific class might vary

        for item in possible_article_containers:
            try:
                title_element = item.find(['h2', 'h3']) # BoF uses different heading levels
                link_element = item.find('a', href=True)

                if title_element and link_element:
                    title = title_element.text.strip()
                    link_href = link_element['href']

                    if not link_href.startswith('http'):
                        url = base_url + link_href
                    else:
                        url = link_href
                    
                    # Date extraction is problematic for BoF on listing pages.
                    # For now, we'll add the article and note the limitation.
                    # A more robust solution would need to visit each article page or use Selenium.
                    articles.append({'title': title, 'url': url})
                    
                    # Limit to a certain number of articles if date filtering is not possible to avoid too many old articles
                    if len(articles) >= 15: # Arbitrary limit for latest news
                        break 
            
            except Exception as e:
                # Log error and continue, but don't include title if it wasn't found
                print(f"Error parsing a Business of Fashion item: {e}")
                continue
        
        if not articles:
            print(f"Could not find article containers or extract content from {url}. BoF structure might have changed or requires JavaScript.")
            print("Scraped content might be limited due to paywall or dynamic loading.")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles

def get_articles_fashionunited(url):
    """
    Fetches articles from FashionUnited published within the last 7 days.

    Args:
        url (str): The URL of the FashionUnited website (news archive).

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        headers = { # FashionUnited might require a User-Agent
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        base_url = "https://fashionunited.com" # For constructing absolute URLs

        # FashionUnited's structure can vary. Look for common article list patterns.
        # The /newsarchive page has articles in <div class="story-teaser">
        # Each teaser has <a class="story-teaser__title-link"> and <span class="story-teaser__date">
        
        article_elements = soup.find_all('div', class_='story-teaser')

        for item in article_elements:
            try:
                title_link_element = item.find('a', class_='story-teaser__title-link')
                date_element = item.find('span', class_='story-teaser__date')

                if not title_link_element or not title_link_element.has_attr('href') or not date_element:
                    continue

                title = title_link_element.text.strip()
                link_href = title_link_element['href']

                if not link_href.startswith('http'):
                    article_url = base_url + link_href
                else:
                    article_url = link_href
                
                date_text = date_element.text.strip() # e.g., "26 Oct 2023" or "Yesterday" or "2 hours ago"

                article_date = None
                if "ago" in date_text.lower():
                    article_date = today # Approximate as today if "ago"
                elif "yesterday" in date_text.lower():
                    article_date = today - datetime.timedelta(days=1)
                else:
                    try:
                        # Format like "26 Oct 2023"
                        article_date = datetime.datetime.strptime(date_text, '%d %b %Y').date()
                    except ValueError as ve:
                        print(f"Could not parse date '{date_text}' for FashionUnited article '{title}': {ve}")
                        continue
                
                if article_date and article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': article_url})

            except Exception as e:
                print(f"Error parsing a FashionUnited article: {title if 'title' in locals() else 'Unknown title'} - {e}")
                continue
        
        if not article_elements:
             print(f"No article elements found on {url}. Structure might have changed.")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles

def get_articles_fashionnetwork(url):
    """
    Fetches articles from FashionNetwork published within the last 7 days.

    Args:
        url (str): The URL of the FashionNetwork website.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Good practice to check for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')

        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        base_url = "https://us.fashionnetwork.com"

        # FashionNetwork lists articles in <li> elements with class 'news-lst-item'
        # Inside these, <p class="news-lst-title"><a>...</a></p> and <p class="news-lst-date">...</p>
        
        article_elements = soup.find_all('li', class_='news-lst-item')

        for item in article_elements:
            try:
                title_element = item.find('p', class_='news-lst-title')
                date_element = item.find('p', class_='news-lst-date')

                if not title_element or not title_element.find('a') or not date_element:
                    continue

                title_anchor = title_element.find('a')
                title = title_anchor.text.strip()
                link_href = title_anchor['href']

                if not link_href.startswith('http'):
                    article_url = base_url + link_href
                else:
                    article_url = link_href
                
                date_text = date_element.text.strip() # e.g., "October 26, 2023"
                
                article_date = None
                try:
                    # Format like "October 26, 2023"
                    article_date = datetime.datetime.strptime(date_text, '%B %d, %Y').date()
                except ValueError as ve:
                    # FashionNetwork also uses "today" and "yesterday"
                    if "today" in date_text.lower():
                        article_date = today
                    elif "yesterday" in date_text.lower():
                        article_date = today - datetime.timedelta(days=1)
                    else:
                        print(f"Could not parse date '{date_text}' for FashionNetwork article '{title}': {ve}")
                        continue
                
                if article_date and article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': article_url})

            except Exception as e:
                print(f"Error parsing a FashionNetwork article: {title if 'title' in locals() else 'Unknown title'} - {e}")
                continue
        
        if not article_elements:
            print(f"No article elements found on {url} for FashionNetwork. Structure might have changed.")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles

def get_articles_itnk(url):
    """
    Fetches articles from ITNK (itnk.co.kr) published within the last 7 days.
    This is a Korean website, so character encoding is implicitly handled by requests/BeautifulSoup (usually to UTF-8).

    Args:
        url (str): The URL of the ITNK website (likely a news or articles section).

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        # Explicitly try to decode using 'utf-8' or 'euc-kr' if there are issues, though BS4 usually handles it.
        # response.encoding = response.apparent_encoding # or 'euc-kr' / 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')

        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        base_url = "https://www.itnk.co.kr"

        # Articles are in <div class="section_list_all_sum Box">
        # Title in <div class="Text"><a>...</a></div>
        # Date in <div class="Time"><span>YYYY-MM-DD HH:MM:SS</span></div>
        
        article_elements = soup.find_all('div', class_='section_list_all_sum Box')

        for item in article_elements:
            try:
                title_div = item.find('div', class_='Text')
                time_div = item.find('div', class_='Time')

                if not title_div or not title_div.find('a') or not time_div or not time_div.find('span'):
                    continue

                title_anchor = title_div.find('a')
                title = title_anchor.text.strip()
                link_href = title_anchor['href']

                if not link_href.startswith('http'):
                    article_url = base_url + link_href
                else:
                    article_url = link_href
                
                date_span = time_div.find('span')
                date_text = date_span.text.strip() # Format: YYYY-MM-DD HH:MM:SS
                
                article_date_str = date_text.split(' ')[0] # Get the YYYY-MM-DD part
                article_date = datetime.datetime.strptime(article_date_str, '%Y-%m-%d').date()
                
                if article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': article_url})

            except Exception as e:
                print(f"Error parsing an ITNK article: {title if 'title' in locals() else 'Unknown title'} - {e}")
                continue
        
        if not article_elements:
            print(f"No article elements found on {url} for ITNK. Structure might have changed.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles

def get_articles_tistory_jinil(url):
    """
    Fetches articles from Jinil Tistory Blog published within the last 7 days.

    Args:
        url (str): The URL of the Jinil Tistory Blog.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        # Base URL might not be needed if Tistory provides full URLs or if we construct them carefully
        # For jinil.tistory.com, links are like "/entry/Post-Title"
        base_url = url.rstrip('/') # Ensure base_url is like https://jinil.tistory.com

        # Common Tistory structures:
        # - Main page list: <div class="list-item"> or <li class="post-item">
        # - Title: <a class="link-article"><strong class="title-article">...</strong></a> or <a class="title">...</a>
        # - Date: <span class="date">YYYY.MM.DD HH:MM</span> or <span class="meta-date">YYYY.MM.DD</span>
        
        # For jinil.tistory.com:
        # List items: <div class="list-item">
        # Link and Title: <a href="/entry/..." class="link-article"><strong class="title-article">TITLE</strong>...</a>
        # Date: <span class="date">YYYY.MM.DD. HH:MM</span> (note the extra dot after DD)
        
        article_elements = soup.find_all('div', class_='list-item')
        if not article_elements: # Fallback for other Tistory themes
            article_elements = soup.find_all('li', class_='post-item') # A common alternative

        for item in article_elements:
            try:
                link_element = item.find('a', class_='link-article')
                if not link_element: # Try another common selector
                    link_element = item.find('a', class_=['title', 'link_title']) 
                
                if not link_element or not link_element.has_attr('href'):
                    continue

                title_text_element = link_element.find(['strong', 'span']) # Title can be in strong or span
                if not title_text_element:
                     title_text_element = link_element # Sometimes the link itself has the title
                
                title = title_text_element.text.strip()
                link_href = link_element['href']

                if not link_href.startswith('http'):
                    article_url = base_url + link_href
                else:
                    article_url = link_href
                
                date_element = item.find('span', class_='date')
                if not date_element : # Fallback for other date classes
                     date_element = item.find(['span','p'], class_=['meta-date', 'datetime', 'post-date'])

                if not date_element:
                    print(f"Skipping Tistory article due to missing date: {title}")
                    continue
                
                date_text = date_element.text.strip() # e.g., "YYYY.MM.DD. HH:MM" or "YYYY.MM.DD" or "X minutes ago"
                
                article_date = None
                if "분 전" in date_text or "시간 전" in date_text or "방금 전" in date_text: # Korean for "minutes ago", "hours ago", "just now"
                    article_date = today
                elif "어제" in date_text: # Korean for "yesterday"
                     article_date = today - datetime.timedelta(days=1)
                else:
                    try:
                        # Format "YYYY.MM.DD." or "YYYY.MM.DD" (sometimes with time)
                        if " " in date_text: # Contains time
                            date_text_cleaned = date_text.split(" ")[0]
                        else:
                            date_text_cleaned = date_text
                        
                        date_text_cleaned = date_text_cleaned.rstrip('.') # Remove trailing dot if present
                        article_date = datetime.datetime.strptime(date_text_cleaned, '%Y.%m.%d').date()
                    except ValueError as ve:
                        print(f"Could not parse date '{date_text}' for Tistory article '{title}': {ve}")
                        continue
                
                if article_date and article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': article_url})

            except Exception as e:
                print(f"Error parsing a Tistory (jinil) article: {title if 'title' in locals() else 'Unknown title'} - {e}")
                continue
        
        if not article_elements:
            print(f"No article elements found on {url} for Tistory (jinil). Structure might have changed or is custom.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles

def get_articles_apparelnews(url):
    """
    Fetches articles from Apparel News (apparelnews.co.kr) published within the last 7 days.
    This is a Korean website.

    Args:
        url (str): The URL of the Apparel News website (likely a news or articles section).

    Returns:
        list: A list of dictionaries, where each dictionary contains 'title' and 'url' for an article.
    """
    articles = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        today = datetime.date.today()
        seven_days_ago = today - datetime.timedelta(days=7)
        base_url = "https://apparelnews.co.kr" # From config

        # Apparel News structure (main page or /news/ list):
        # Articles in <div class="NwslistBox"> (often in a list) or similar structure
        # Title: <dt><a>TITLE</a></dt> or <div class="subject"><a>TITLE</a></div>
        # Date: <dd class="date"><span>YYYY-MM-DD HH:MM:SS</span></dd> or similar
        
        article_elements = soup.find_all('div', class_='NwslistBox')
        if not article_elements: # Fallback for other potential list structures
            # Example: looking for list items if the above class is not found
            article_elements = soup.find_all('li', class_=lambda x: x and 'item' in x.lower())


        for item in article_elements:
            try:
                title_element = item.find('dt') # Common for <dt><a>TITLE</a></dt>
                link_element = None
                if title_element:
                    link_element = title_element.find('a')
                
                if not link_element: # Fallback: Try finding by a subject class
                    title_subject_div = item.find(['div','p'], class_=['subject', 'title', 'art_tit'])
                    if title_subject_div:
                        link_element = title_subject_div.find('a')
                
                if not link_element or not link_element.has_attr('href'):
                    continue

                title = link_element.text.strip()
                link_href = link_element['href']

                if not link_href.startswith('http'):
                    # Check if it's a full path or needs base_url
                    if link_href.startswith('/'):
                        article_url = base_url + link_href
                    else: # Relative to current path, less common for news links
                        article_url = base_url + "/" + link_href # Basic assumption
                else:
                    article_url = link_href
                
                date_dd = item.find('dd', class_='date') # Common: <dd class="date"><span>...</span></dd>
                date_span = None
                if date_dd:
                    date_span = date_dd.find('span')
                
                if not date_span: # Fallback for other date locations/tags
                    date_span = item.find(['span', 'p'], class_=['date', 'time', 'news_date'])

                if not date_span:
                    print(f"Skipping Apparel News article due to missing date: {title}")
                    continue
                
                date_text = date_span.text.strip() # Format: YYYY-MM-DD HH:MM:SS
                
                article_date_str = date_text.split(' ')[0] # Get the YYYY-MM-DD part
                article_date = datetime.datetime.strptime(article_date_str, '%Y-%m-%d').date()
                
                if article_date >= seven_days_ago:
                    articles.append({'title': title, 'url': article_url})

            except Exception as e:
                print(f"Error parsing an Apparel News article: {title if 'title' in locals() else 'Unknown title'} - {e}")
                continue
        
        if not article_elements:
            print(f"No article elements found on {url} for Apparel News. Structure might have changed.")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
    except Exception as e:
        print(f"An error occurred while parsing {url}: {e}")
    return articles


# ... (keep all existing functions get_articles_sourcing_journal, get_articles_wwd, get_articles_retail_dive, get_articles_bof)

def load_config(config_path="config.json"):
    """Loads the configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{config_path}'.")
        return None

if __name__ == "__main__":
    print("Newsletter Generator")
    
    config = load_config()
    if not config or "websites" not in config:
        print("Exiting: Website configuration is missing or invalid.")
        exit()

    scraper_mapping = {
        "sourcingjournal.com": get_articles_sourcing_journal,
        "wwd.com": get_articles_wwd,
        "www.retaildive.com": get_articles_retail_dive, # Using www. for matching
        "www.businessoffashion.com": get_articles_bof, # Using www. for matching
        "fashionunited.com": get_articles_fashionunited, # Assumes config URL will be /newsarchive or similar
        "us.fashionnetwork.com": get_articles_fashionnetwork,
        "www.itnk.co.kr": get_articles_itnk, # This key should match the domain from the updated config URL
        "jinil.tistory.com": get_articles_tistory_jinil,
        "apparelnews.co.kr": get_articles_apparelnews,
    }

    all_articles = {}

    for site_url_config in config["websites"]:
        # Extract a comparable part of the URL (e.g., domain name) to match keys in scraper_mapping
        # This handles "https://www.retaildive.com/" vs "www.retaildive.com"
        domain_name = site_url_config.replace("https://", "").replace("http://", "").split('/')[0]

        if domain_name in scraper_mapping:
            scraper_function = scraper_mapping[domain_name]
            print(f"\nFetching articles from: {site_url_config}")
            articles = scraper_function(site_url_config) # Pass the full URL from config
            if articles:
                all_articles[site_url_config] = articles
                print(f"Found {len(articles)} articles from {domain_name}:")
                for article in articles:
                    print(f"- {article['title']}: {article['url']}")
            else:
                print(f"No articles found from {domain_name} or an error occurred.")
        else:
            print(f"\nNo scraper configured for website: {site_url_config} (domain: {domain_name})")

    # At this point, all_articles dictionary contains articles from all configured and scraped sites
    # This can be used for further processing (e.g., email generation)
    if not all_articles:
        print("\nNo articles collected from any website.")
    else:
        print(f"\n--- Collected {sum(len(v) for v in all_articles.values())} articles from {len(all_articles)} sites before filtering ---")

        # Filter articles by keywords
        filtered_articles = filter_articles_by_title(all_articles, APPAREL_KEYWORDS)
        
        total_filtered_count = 0
        if not filtered_articles:
            print("\nNo articles found matching the apparel keywords in their titles.")
        else:
            print("\n--- Filtered Articles Relevant to Apparel/Sourcing/Trends/Retail (with Summaries) ---")
            summarized_articles_count = 0
            for site_url, articles_list in filtered_articles.items():
                site_name_short = site_url.replace("https://", "").replace("http://", "").split('/')[0]
                print(f"\n--- Summarizing relevant articles from {site_name_short} ---")
                
                site_relevant_articles_with_summaries = []
                for article in articles_list:
                    print(f"\nFetching content for: {article['title']} ({article['url']})")
                    content = get_article_content(article['url'])
                    
                    if content:
                        # Determine language for summarizer
                        # Basic check, can be made more robust
                        current_language = "english"
                        if "itnk.co.kr" in site_url or "tistory.com" in site_url or "apparelnews.co.kr" in site_url:
                            current_language = "korean" 
                            print(f"Attempting summarization in Korean for: {article['title']}")
                        else:
                            print(f"Attempting summarization in English for: {article['title']}")

                        summary = summarize_text(content, num_sentences=3, language=current_language)
                        article['summary'] = summary
                        print(f"Title: {article['title']}")
                        print(f"URL: {article['url']}")
                        print(f"Summary: {article['summary']}")
                        site_relevant_articles_with_summaries.append(article)
                        summarized_articles_count +=1
                    else:
                        article['summary'] = "Could not fetch or extract content for summarization."
                        print(f"Title: {article['title']}")
                        print(f"URL: {article['url']}")
                        print(f"Summary: {article['summary']}")
                        site_relevant_articles_with_summaries.append(article) # Keep article even if no summary
                
                # Update the list in filtered_articles (or a new dict if preferred)
                filtered_articles[site_url] = site_relevant_articles_with_summaries 
                total_filtered_count += len(site_relevant_articles_with_summaries) # This counts articles attempted for summary

            if summarized_articles_count > 0:
                 print(f"\n--- Successfully generated summaries for {summarized_articles_count} relevant articles ---")
            else:
                print("\n--- No summaries could be generated for the relevant articles ---")
            
            # This total_filtered_count might be confusing here as it's incremented per site list
            # Recalculate total relevant articles that had summaries attempted:
            final_relevant_article_count = sum(len(v) for v in filtered_articles.values())
            print(f"\n--- Total relevant articles (summary attempted): {final_relevant_article_count} ---")
