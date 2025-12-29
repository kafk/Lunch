import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from io import BytesIO
from PyPDF2 import PdfReader


# User agent för att undvika blockeringar
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
}

# Nyckelord för att hitta lunchlänkar - prioriterade först
LUNCH_KEYWORDS_HIGH = ['lunch', 'lunchmeny', 'veckomeny', 'veckans-lunch', 'dagens-lunch', 'veckans_lunch']
LUNCH_KEYWORDS_LOW = ['menu', 'meny', 'matsedel']


def fetch_page(url, timeout=15):
    """Hämta en sida med proper headers."""
    response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response


def find_lunch_links(html, base_url):
    """
    Hitta alla länkar som kan vara relaterade till lunchmenyn.
    Returnerar lista med (url, typ, score) där typ är 'page' eller 'pdf'.
    Prioriterar lunch-specifika länkar över generiska meny-länkar.
    """
    soup = BeautifulSoup(html, 'html.parser')
    candidates = []

    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True).lower()

        # Bygg fullständig URL
        full_url = urljoin(base_url, href)

        # Kolla om det är en PDF
        is_pdf = href.lower().endswith('.pdf') or 'pdf' in href.lower()

        # Beräkna score baserat på hur relevant länken verkar vara
        score = 0
        href_lower = href.lower()

        # Hög prioritet för lunch-specifika nyckelord
        for keyword in LUNCH_KEYWORDS_HIGH:
            if keyword in href_lower:
                score += 25  # Högre score för lunch i URL
            if keyword in text:
                score += 15  # Hög score för lunch i länktext

        # Låg prioritet för generiska meny-nyckelord
        for keyword in LUNCH_KEYWORDS_LOW:
            if keyword in href_lower and score == 0:  # Bara om ingen lunch hittats
                score += 5
            if keyword in text and score < 15:
                score += 3

        # PDF:er med lunch-relaterade namn får extra poäng
        if is_pdf and score > 0:
            score += 20

        # Ignorera externa länkar, mailto, tel, etc.
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue

        # Lägg till om score > 0
        if score > 0:
            link_type = 'pdf' if is_pdf else 'page'
            candidates.append({
                'url': full_url,
                'type': link_type,
                'score': score,
                'text': text[:50]
            })

    # Sortera efter score (högst först)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates


def format_menu_text(text):
    """Formatera menytext för bättre läsbarhet."""
    # Veckodagar - lägg till radbrytning före
    weekdays = ['MÅNDAG', 'TISDAG', 'ONSDAG', 'TORSDAG', 'FREDAG', 'LÖRDAG', 'SÖNDAG']
    for day in weekdays:
        text = re.sub(rf'({day})', r'\n\n\1', text, flags=re.IGNORECASE)

    # Kategorier - lägg till radbrytning före
    categories = ['KÖTT', 'FISK', 'PASTA', 'SALLAD', 'BURGARE', 'VEGETARISKT', 'VEGAN', 'DESSERT', 'LUNCH V']
    for cat in categories:
        text = re.sub(rf'({cat})', r'\n\n\1', text, flags=re.IGNORECASE)

    # Bullet points (❖) - lägg till radbrytning före
    text = re.sub(r'(❖)', r'\n  \1 ', text)

    # Andra vanliga punkttecken
    text = re.sub(r'(•)', r'\n  \1 ', text)
    text = re.sub(r'(\*\s)', r'\n  \1', text)

    # Priser - lägg till radbrytning efter
    text = re.sub(r'(\d+\s*kr/?(?:\s*\d+\s*kr)?)', r'\1\n', text)

    # Städa upp multipla radbrytningar
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\s+', '', text)  # Ta bort inledande whitespace

    return text.strip()


def extract_pdf_text(pdf_content):
    """Extrahera text från PDF-innehåll."""
    try:
        pdf_file = BytesIO(pdf_content)
        reader = PdfReader(pdf_file)

        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = '\n'.join(text_parts)

        # Formatera texten för bättre läsbarhet
        full_text = format_menu_text(full_text)

        return full_text.strip()
    except Exception as e:
        return f"Kunde inte läsa PDF: {str(e)}"


def extract_menu_from_html(html):
    """Extrahera menytext från HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    # Ta bort onödiga element (navigation, footer, etc.)
    for el in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe']):
        el.decompose()

    # Ta bort element med navigation-klasser
    nav_patterns = ['nav', 'menu', 'header', 'footer', 'sidebar', 'social', 'cookie', 'popup']
    for el in soup.find_all(class_=lambda x: x and any(p in str(x).lower() for p in nav_patterns)):
        el.decompose()

    # Ta bort navigation-liknande ul/li-listor med korta länkar
    for ul in soup.find_all('ul'):
        links = ul.find_all('a')
        if links and len(links) > 3:
            # Kolla om det är korta navigationslänkar
            short_links = sum(1 for a in links if len(a.get_text(strip=True)) < 20)
            if short_links / len(links) > 0.7:
                ul.decompose()

    # Hämta huvudinnehållet
    main = soup.find('main') or soup.find('article') or soup.find('body')
    if main:
        text = main.get_text(separator='\n', strip=True)

        # Filtrera bort typiska navigationsrader
        lines = text.split('\n')
        filtered_lines = []
        nav_keywords = ['meny', 'menu', 'lunch', 'events', 'catering', 'galleri', 'gallery', 'boka bord',
                       'om oss', 'about', 'kontakt', 'contact', 'instagram', 'facebook',
                       'copyright', 'all rights', 'integritetspolicy', 'privacy', 'the grill']

        for line in lines:
            line_lower = line.lower().strip()
            # Skippa korta rader som bara är navigation (exakt match eller innehåller keyword)
            if len(line_lower) < 20:
                if line_lower in nav_keywords or any(nav == line_lower for nav in nav_keywords):
                    continue
            # Skippa copyright-rader
            if 'copyright' in line_lower or '©' in line:
                continue
            filtered_lines.append(line)

        text = '\n'.join(filtered_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Formatera för bättre läsbarhet
        text = format_menu_text(text)

        return text[:3000]

    return "Kunde inte extrahera menyinnehåll."


def scrape_lunch_menu(url):
    """
    Huvudfunktion: Scrapa lunchmeny från en URL.

    1. Hämta huvudsidan
    2. Leta efter lunch-relaterade länkar (inkl. PDF)
    3. Om PDF hittas - läs den
    4. Annars - försök extrahera från sidan
    """
    result = {
        'success': False,
        'menu': None,
        'source_type': None,
        'source_url': url,
        'lunch_links': [],
        'error': None
    }

    try:
        # Steg 1: Hämta huvudsidan
        response = fetch_page(url)
        html = response.text

        # Steg 2: Hitta lunchlänkar
        lunch_links = find_lunch_links(html, url)
        result['lunch_links'] = lunch_links[:5]  # Spara top 5

        # Steg 3: Försök med bästa kandidaten
        if lunch_links:
            best = lunch_links[0]

            if best['type'] == 'pdf':
                # Hämta och läs PDF
                pdf_response = fetch_page(best['url'])
                menu_text = extract_pdf_text(pdf_response.content)
                result['menu'] = menu_text
                result['source_type'] = 'pdf'
                result['source_url'] = best['url']
                result['success'] = True
            else:
                # Hämta undersidan
                sub_response = fetch_page(best['url'])

                # Kolla om den sidan har PDF-länkar
                sub_links = find_lunch_links(sub_response.text, best['url'])
                pdf_links = [l for l in sub_links if l['type'] == 'pdf']

                if pdf_links:
                    # Hämta PDF från undersidan
                    pdf_response = fetch_page(pdf_links[0]['url'])
                    menu_text = extract_pdf_text(pdf_response.content)
                    result['menu'] = menu_text
                    result['source_type'] = 'pdf'
                    result['source_url'] = pdf_links[0]['url']
                    result['success'] = True
                else:
                    # Extrahera från HTML
                    menu_text = extract_menu_from_html(sub_response.text)
                    result['menu'] = menu_text
                    result['source_type'] = 'html'
                    result['source_url'] = best['url']
                    result['success'] = True
        else:
            # Ingen lunchlänk hittad - försök extrahera från huvudsidan
            menu_text = extract_menu_from_html(html)
            result['menu'] = menu_text
            result['source_type'] = 'html'
            result['success'] = True

    except requests.exceptions.RequestException as e:
        result['error'] = f"Kunde inte hämta sidan: {str(e)}"
    except Exception as e:
        result['error'] = f"Ett fel uppstod: {str(e)}"

    return result
