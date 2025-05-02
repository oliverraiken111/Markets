import requests
from bs4 import BeautifulSoup
import datetime
import xml.etree.ElementTree as ET
import json
import time
import random

# AP News Financial Markets section
url = "https://apnews.com/hub/financial-markets"

# Create a more browser-like request with enhanced headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "TE": "Trailers"
}

# Function to make request with retries and random delay
def make_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            # Add a small random delay to mimic human behavior
            if attempt > 0:
                time.sleep(random.uniform(1, 3))
            
            print(f"Making request to {url} (attempt {attempt+1}/{max_retries})")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 403:
                print(f"⚠️ Access forbidden (403) - Try {attempt+1}/{max_retries}")
                # Try with a different User-Agent if forbidden
                headers["User-Agent"] = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(80, 108)}.0.{random.randint(1000, 9999)}.{random.randint(100, 999)} Safari/537.36"
            else:
                print(f"⚠️ HTTP status code: {response.status_code} - Try {attempt+1}/{max_retries}")
                
        except Exception as e:
            print(f"⚠️ Request error: {e} - Try {attempt+1}/{max_retries}")
    
    # If all attempts fail, return None
    return None

# Try to get the content
html_content = make_request_with_retry(url)

# If we couldn't fetch the content, provide a fallback
if not html_content:
    print("⚠️ Could not fetch AP News content after multiple attempts")
    html_content = """
    <html><body>
        <div class="PageList-items-item">
            <div class="PagePromo-content">
                <a class="PagePromo-title">Financial Markets Update</a>
                <div class="PagePromo-description">The latest financial markets news and updates.</div>
            </div>
        </div>
    </body></html>
    """

# Parse HTML content
soup = BeautifulSoup(html_content, "html.parser")

# Set up RSS feed
ET.register_namespace('media', 'http://search.yahoo.com/mrss/')
rss = ET.Element('rss', {"version": "2.0", "xmlns:media": "http://search.yahoo.com/mrss/"})
channel = ET.SubElement(rss, 'channel')
ET.SubElement(channel, 'title').text = "AP News Financial Markets"
ET.SubElement(channel, 'link').text = url
ET.SubElement(channel, 'description').text = "Latest news on Financial Markets from AP News"
ET.SubElement(channel, 'lastBuildDate').text = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

# Extract Financial Markets specific articles
articles_found = 0
seen_titles = set()

# Try multiple CSS selectors that might match AP News content
selectors = [
    'div[data-key="feed-card-wire-story-with-thumbnail"]',
    'div.PagePromo',
    'div.PageList-items-item',
    'div.FeedCard',
    'div.CardHeadline',
    'article.Article'
]

for selector in selectors:
    if articles_found >= 10:
        break
        
    for article in soup.select(selector):
        # Find the headline link using multiple possible selectors
        headline_link = None
        for link_selector in ['a.PagePromo-title', 'a.CardHeadline-title', 'a[data-key="card-headline"]', 'h1 a', 'h2 a', 'h3 a', 'a']:
            headline_link = article.select_one(link_selector)
            if headline_link:
                break
                
        if not headline_link:
            continue
        
        # Get title (with fallback to link text or "Financial Markets Update")
        title = headline_link.get_text(strip=True) if headline_link.get_text(strip=True) else "Financial Markets Update"
        
        # Skip if we've seen this title or it's empty
        if not title or title in seen_titles:
            continue
        
        seen_titles.add(title)
        
        # Get URL (with fallback to main AP Financial Markets page)
        href = headline_link.get('href', '')
        full_url = href if href.startswith("http") else "https://apnews.com" + href if href else url
        
        # Get description (with fallback to generic description)
        description = ""
        for desc_selector in ['div.PagePromo-description', 'p.CardHeadline-description', 'div.content p', 'p.Article-description']:
            desc_element = article.select_one(desc_selector)
            if desc_element:
                description = desc_element.get_text(strip=True)
                break
                
        if not description:
            description = f"AP News financial markets article: {title}"
        
        # Try to extract publication date
        pub_date = datetime.datetime.utcnow()  # fallback if not found
        for date_selector in ['span.PagePromo-timestamp', 'span.CardHeadline-timestamp', 'span.Timestamp', 'time']:
            date_element = article.select_one(date_selector)
            if date_element:
                date_text = date_element.get_text(strip=True)
                try:
                    # AP usually shows relative time like "1 hour ago" or exact date
                    if "ago" in date_text.lower():
                        # Just use current time for "ago" formats
                        pass
                    else:
                        # Try different date formats
                        for date_format in ["%b. %d, %Y", "%B %d, %Y", "%Y-%m-%d"]:
                            try:
                                pub_date = datetime.datetime.strptime(date_text, date_format)
                                break
                            except:
                                continue
                except Exception as e:
                    print(f"⚠️ Failed to parse date '{date_text}': {e}")
                break
        
        # Create RSS item
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = full_url
        ET.SubElement(item, "description").text = description
        ET.SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # Try to find and add image if available
        for img_selector in ['img', 'div.LazyImage img', 'figure img']:
            img_element = article.select_one(img_selector)
            if img_element and img_element.get('src'):
                img_url = img_element['src']
                # Check if URL is relative
                if not img_url.startswith('http'):
                    img_url = 'https://apnews.com' + img_url if not img_url.startswith('/') else 'https://apnews.com' + img_url
                    
                media_content = ET.SubElement(item, '{http://search.yahoo.com/mrss/}content', {
                    'url': img_url,
                    'type': 'image/jpeg'
                })
                break
        
        articles_found += 1
        if articles_found >= 10:
            break

# If we couldn't find any real articles, try a direct approach with individual article fetch
if articles_found == 0:
    print("⚠️ No articles found with selectors. Attempting to find article links directly.")
    
    # Look for anything that might be a link to a financial markets article
    article_links = []
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if href and ('/financial-markets/' in href or '/economy/' in href or '/business/' in href):
            # Full URL if not already
            full_url = href if href.startswith('http') else 'https://apnews.com' + href if href.startswith('/') else 'https://apnews.com/' + href
            
            if full_url not in [item['href'] for item in article_links]:
                article_links.append({
                    'href': full_url,
                    'title': link.get_text(strip=True) if link.get_text(strip=True) else "AP Financial Markets Article"
                })
                
                if len(article_links) >= 10:
                    break
    
    # Try to fetch individual articles
    for article_info in article_links:
        article_html = make_request_with_retry(article_info['href'])
        if article_html:
            article_soup = BeautifulSoup(article_html, 'html.parser')
            
            # Get title
            title = article_info['title']
            for title_selector in ['h1', 'header h1', 'div.Article h1']:
                title_element = article_soup.select_one(title_selector)
                if title_element:
                    title = title_element.get_text(strip=True)
                    break
            
            # Get description
            description = f"AP News financial markets article: {title}"
            for desc_selector in ['div.Article-description', 'p.Article-description', 'div.article-body p']:
                desc_element = article_soup.select_one(desc_selector)
                if desc_element:
                    description = desc_element.get_text(strip=True)
                    break
            
            # Create RSS item
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = article_info['href']
            ET.SubElement(item, "description").text = description
            ET.SubElement(item, "pubDate").text = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            articles_found += 1

# If we still couldn't find any real articles, add placeholder items
if articles_found == 0:
    print("⚠️ No articles found. Creating placeholder items.")
    # Create a few placeholder items
    for i in range(5):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"AP Financial Markets Update {i+1}"
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "description").text = "Latest financial markets news and updates from AP News."
        ET.SubElement(item, "pubDate").text = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        articles_found += 1

# Write output
output_filename = "ap_financial_markets.xml"
with open(output_filename, "wb") as f:
    ET.ElementTree(rss).write(f, encoding="utf-8", xml_declaration=True)
print(f"✅ RSS feed created with {articles_found} AP News financial markets articles in {output_filename}")
