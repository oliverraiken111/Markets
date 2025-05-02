import requests
from bs4 import BeautifulSoup
import datetime
import xml.etree.ElementTree as ET
import json

# AP News Financial Markets section
url = "https://apnews.com/hub/financial-markets"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
response = requests.get(url, headers=headers)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

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

# AP News uses different HTML structure, we need to adapt our selectors
# Look for article cards on the page
for article in soup.select('div[data-key="feed-card-wire-story-with-thumbnail"]'):
    # Get the headline link
    headline_link = article.select_one('a.PagePromo-title')
    if not headline_link:
        continue
    
    title = headline_link.get_text(strip=True)
    href = headline_link["href"]
    
    if not title or title in seen_titles:
        continue
    
    seen_titles.add(title)
    
    # Check if href is a full URL or relative path
    if href.startswith("http"):
        full_url = href
    else:
        full_url = "https://apnews.com" + href
    
    # Try to extract description/summary if available
    description = ""
    desc_element = article.select_one('div.PagePromo-description')
    if desc_element:
        description = desc_element.get_text(strip=True)
    else:
        description = f"AP News financial markets article: {title}"
    
    # Try to extract publication date
    pub_date = datetime.datetime.utcnow()  # fallback if not found
    date_element = article.select_one('span.PagePromo-timestamp')
    if date_element:
        date_text = date_element.get_text(strip=True)
        try:
            # AP usually shows relative time like "1 hour ago" or exact date
            # This is a simplified approach; might need refinement based on actual format
            if "ago" in date_text.lower():
                # Just use current time for "ago" formats
                pass
            else:
                # Try to parse an actual date
                pub_date = datetime.datetime.strptime(date_text, "%b. %d, %Y")
        except Exception as e:
            print(f"⚠️ Failed to parse date '{date_text}': {e}")
    
    # Create RSS item
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = full_url
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # Try to find and add image if available
    img_element = article.select_one('img')
    if img_element and img_element.get('src'):
        img_url = img_element['src']
        media_content = ET.SubElement(item, '{http://search.yahoo.com/mrss/}content', {
            'url': img_url,
            'type': 'image/jpeg'  # Assuming JPEG, adapt if needed
        })
    
    articles_found += 1
    if articles_found >= 10:
        break

# If we didn't find enough articles with the first method, try an alternative approach
if articles_found < 10:
    # Alternative selector based on AP News structure
    for article in soup.select('div.CardHeadline'):
        headline_link = article.select_one('a')
        if not headline_link:
            continue
        
        title = headline_link.get_text(strip=True)
        href = headline_link.get('href')
        
        if not title or title in seen_titles or not href:
            continue
        
        seen_titles.add(title)
        
        # Check if href is a full URL or relative path
        if href.startswith("http"):
            full_url = href
        else:
            full_url = "https://apnews.com" + href
        
        # Create RSS item
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = full_url
        ET.SubElement(item, "description").text = f"AP News financial markets article: {title}"
        ET.SubElement(item, "pubDate").text = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        articles_found += 1
        if articles_found >= 10:
            break

# Write output
with open("markets.xml", "wb") as f:
    ET.ElementTree(rss).write(f, encoding="utf-8", xml_declaration=True)
print(f"✅ RSS feed created with {articles_found} AP News Financial Markets articles.")
