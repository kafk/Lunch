import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime


def get_weekday_swedish():
    """Get current weekday in Swedish."""
    weekdays = ['måndag', 'tisdag', 'onsdag', 'torsdag', 'fredag', 'lördag', 'söndag']
    return weekdays[datetime.now().weekday()]


def scrape_lunch_menu(url):
    """
    Scrape lunch menu from a given URL.
    Attempts to find and extract lunch menu content.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    # Try to detect encoding
    response.encoding = response.apparent_encoding or 'utf-8'

    soup = BeautifulSoup(response.text, 'lxml')

    # Remove script and style elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header']):
        element.decompose()

    # Get today's weekday in Swedish
    today = get_weekday_swedish()

    # Common patterns for lunch menu sections
    menu_keywords = [
        'lunch', 'meny', 'menu', 'veckomeny', 'veckans',
        'dagens', 'rätt', 'mat', today
    ]

    # Try to find menu sections
    menu_content = []

    # Look for elements containing lunch-related keywords
    for element in soup.find_all(['div', 'section', 'article', 'main', 'p', 'li', 'h1', 'h2', 'h3', 'h4']):
        text = element.get_text(separator=' ', strip=True).lower()

        # Check if element contains menu-related keywords
        if any(keyword in text for keyword in menu_keywords):
            # Get the text content
            content = element.get_text(separator='\n', strip=True)
            if len(content) > 20 and content not in menu_content:
                menu_content.append(content)

    if menu_content:
        # Combine and clean up the content
        combined = '\n\n'.join(menu_content[:5])  # Limit to first 5 sections
        # Clean up excessive whitespace
        combined = re.sub(r'\n{3,}', '\n\n', combined)
        combined = re.sub(r' {2,}', ' ', combined)
        return combined[:2000]  # Limit length

    # Fallback: get main content area
    main_content = soup.find('main') or soup.find('article') or soup.find('body')
    if main_content:
        text = main_content.get_text(separator='\n', strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text[:2000]

    return "Kunde inte hitta lunchmeny på denna sida."
