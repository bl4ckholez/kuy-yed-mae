import requests
import re
import json
import time
import os
import base64
import platform
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote, parse_qs, urljoin
from datetime import datetime
from clint.textui import colored
import tempfile
import warnings
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementClickInterceptedException
import cloudscraper

warnings.filterwarnings("ignore", category=DeprecationWarning)

# แสดงข้อความด้านบน
print("""
เว็บที่รองรับ

       seriesday-hd.com
       123-hd.com
       movie285.com

Created by d1nfuck3r

กรุณาใส่ URL :
""")

# Input URL
web_movie = input().strip()
f_path = "/sdcard/55/1DM/output/"
os.makedirs(f_path, exist_ok=True)

# เคลียร์หน้าจอ
if platform.system() == "Windows":
    os.system('cls')
else:
    os.system('clear')

# Date and time
date = datetime.now().strftime("%d")
mo = datetime.now().strftime("%m")
month = ['', 'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 
         'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
timeday = f'วันที่ {date} {month[int(mo)]} {int(datetime.now().strftime("%Y"))+543}'

# File naming
fname = unquote(urlparse(web_movie).path.strip('/').split('/')[-1])
wname = unquote(urlparse(web_movie).netloc.strip('.').split('.')[-2])
f_m3u = f"{wname}_{fname}.m3u"
f_w3u = f"{wname}_{fname}.w3u"
checkpoint_file = os.path.join(f_path, f"{wname}_{fname}_checkpoint.json")

# Flags
W_M3U = 1
W_W3U = 0
needHD = 1
M_f = 1
pcurrent = 1
max_pages = 3  # จำนวนหน้าที่ต้องการดึง (1=หน้าเดียว, 2=สองหน้า, 3=สามหน้า, 0=ทุกหน้า)

# Headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
    "Referer": f"{urlparse(web_movie).scheme}://{urlparse(web_movie).netloc}/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# JSON structure for W3U
aseries = """{
    "name": "",
    "author": "",
    "info": "",
    "image": "",
    "groups": []}"""
jseries = json.loads(aseries)

# Chrome options
options = Options()
options.binary_location = "/data/data/com.termux/files/usr/bin/chromium-browser"
options.add_argument('--ignore-certificate-errors')
options.add_argument('--incognito')
options.add_argument('--headless=new')
options.add_argument(f"user-agent={headers['User-Agent']}")
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_experimental_option('excludeSwitches', ['enable-logging'])
temp_dir = tempfile.mkdtemp()
options.add_argument(f"--user-data-dir={temp_dir}")

# ChromeDriver path
chromedriver_path = "/data/data/com.termux/files/usr/bin/chromedriver"
service = Service(executable_path=chromedriver_path)

# Initialize driver
driver = None
if 'movie285-hd.com' not in web_movie and 'xn--285-1klzd4a0j0b1d.com' not in web_movie:
    try:
        driver = webdriver.Chrome(service=service, options=options)
    except WebDriverException:
        exit(1)

# Requests session and cloudscraper
sess = requests.Session()
sess.headers.update(headers)
scraper = cloudscraper.create_scraper()

# เก็บลิงก์ที่ประมวลผลแล้ว
processed_links = set()

def fix_image_url(url, base_domain):
    if not url:
        return ""
    url = re.sub(r'-\d+x\d+', '', url)
    if url.startswith('//'):
        url = f"https:{url}"
    elif url.startswith('/'):
        url = f"https://{base_domain}{url}"
    elif not url.startswith(('http://', 'https://')):
        url = f"https://{base_domain}/{url}"
    return url

def find_hd(elink):
    purl = f"{urlparse(elink).scheme}://{urlparse(elink).netloc}/"
    try:
        view_page = sess.get(elink, timeout=3)
        regex_pattern = re.compile(r'RESOLUTION=(.+)*\n(.+[-a-zA-Z0-9()@:%_\+.~#?&//=])')
        result = regex_pattern.findall(view_page.text)
        if result:
            purl2 = result[-1][-1].lstrip('/')
            elink = purl + purl2
    except:
        pass
    return elink

def edit_link(elink):
    if not elink or elink in ["https://www.123-hd.com/api/fileprocess.html", "https://www.serie-day.com/api/get.php"]:
        return ""
    parsed_url = urlparse(elink)
    query_params = parse_qs(parsed_url.query)
    purl = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    
    if 'hot.24playerhd.com' in parsed_url.netloc and 'index.php' in parsed_url.path:
        if 'id' in query_params:
            cid = query_params['id'][0]
            return f"{purl}ioshls/{cid}/{cid}.m3u8"
        return ""
    
    if any(x in parsed_url.path for x in ['index_th.php', 'index_g.html', '/m3u8/']) and 'id' in query_params:
        cid = query_params['id'][0]
        return f"{purl}newplaylist/{cid}/{cid}.m3u8"
    
    try:
        cid = query_params['id'][0]
    except:
        return elink if elink.endswith('.m3u8') else ""
    
    if re.search(r'main\.77player\.xyz', elink):
        backup = query_params.get('backup', ['0'])[0]
        ptype = query_params.get('ptype', ['0'])[0]
        if backup == '1':
            return f"{purl}newplaylist_g/{cid}/{cid}.m3u8"
        else:
            if ptype == '2':
                return f"{purl}main.24playerhd.com/{cid}/{cid}.m3u8"
            else:
                return f"{purl}newplaylist/{cid}/{cid}.m3u8"
    elif re.search(r'xxx\.77player\.xyz', elink):
        ptype = query_params.get('ptype', ['0'])[0]
        if ptype == '2':
            return f"{purl}https://main.24playerhd.com/newplaylist/{cid}/{cid}.m3u8"
        else:
            return f"{purl}autoplaylist/{cid}/{cid}.m3u8"
    
    return elink if elink.endswith('.m3u8') else ""

def find_m3u8_link(soup, page_content, referer):
    source_match = None
    video = soup.find("video")
    if video:
        source = video.find("source")
        if source and source.get("src"):
            source_match = re.match(r'(https?://[^\s"]+\.m3u8)', source["src"])
    if not source_match:
        source_match = (
            re.search(r'file:\s*["\'](.+\.m3u8)["\']', page_content) or
            re.search(r'source src="(.+\.m3u8)"', page_content) or
            re.search(r'["\'](.+\.m3u8)["\']', page_content) or
            re.search(r'(https?://[^\s"]+\.m3u8)', page_content) or
            re.search(r'source\s*:\s*["\'](.+\.m3u8)["\']', page_content) or
            re.search(r'url\s*:\s*["\'](.+\.m3u8)["\']', page_content)
        )
    if not source_match:
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                match = re.search(r'(https?://[^\s"]+\.m3u8)', script.string) or \
                        re.search(r'file:\s*["\'](.+\.m3u8)["\']', script.string)
                if match:
                    source_match = match
                    break
    if source_match:
        elink = source_match.group(1)
        if not elink.startswith('http'):
            elink = urljoin(referer, elink)
        return elink
    return None

def extract_iframe_url(soup, page_content):
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "const encoded" in script.string:
            match = re.search(r'const encoded = "([^"]+)";', script.string)
            if match:
                encoded = match.group(1)
                try:
                    decoded = base64.b64decode(encoded).decode('utf-8')
                    return decoded
                except:
                    return None
    iframe = soup.find("iframe")
    if iframe:
        src = iframe.get('src') or iframe.get('data-src')
        if src:
            return src
    for script in scripts:
        if script.string:
            match = re.search(r'iframe\.src\s*=\s*["\']([^"\']+)["\']', script.string)
            if match:
                return match.group(1)
    return None

def load_page_with_retry(driver, url, retries=3, timeout=20):
    for attempt in range(retries):
        try:
            driver.get(url)
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".box, .item, article, .list-episode, .play-btn, .halim-btn, .btn, [class*='play'], button, video, iframe"))
            )
            time.sleep(3)
            return True
        except (TimeoutException, WebDriverException):
            if attempt < retries - 1:
                driver.refresh()
                time.sleep(2)
    return False

def get_page_content(url, session, referer):
    try:
        session.headers.update({'User-Agent': headers['User-Agent'], 'referer': referer, 'Accept': headers['Accept']})
        response = session.get(url, timeout=10)
        response.encoding = response.apparent_encoding or 'utf-8'
        return response
    except requests.RequestException:
        try:
            response = scraper.get(url, headers={'User-Agent': headers['User-Agent'], 'referer': referer, 'Accept': headers['Accept']}, timeout=10)
            response.encoding = response.apparent_encoding or 'utf-8'
            return response
        except:
            return None

def get_movie_info_movie285(article, base_domain):
    try:
        link = article.find("a")
        url = link['href'] if link else ""
        ppic = link.find("img")['src'] if link and link.find("img") else ""
        pname = link.find("h3", class_="movie-title").text.strip() if link and link.find("h3", class_="movie-title") else ""
        pinfo = ''
        if 'ซับไทย' in pname:
            pinfo = 'ซับไทย'
        elif 'พากย์ไทย' in pname:
            pinfo = 'พากย์ไทย'
        return url, pname, ppic, pinfo
    except:
        return None, None, None, None

def get_movie_info_123hd(article, base_domain):
    try:
        if article.find("div", class_="item"):
            url = article.find("a")['href'] if article.find("a") else ""
            pname = article.find("h3").text.strip() if article.find("h3") else ""
            img = article.find("img")
            ppic = fix_image_url(img.get("data-lazy-src") or img.get("src", ""), base_domain) if img else ""
            pinfo = article.find("div", class_="meta").text.strip().replace("\n", " ") if article.find("div", class_="meta") else ""
        elif article.find("div", class_="box-img"):
            url = article.find("a")['href'] if article.find("a") else ""
            pname = article.find("div", class_="p2").text.strip() if article.find("div", class_="p2") else ""
            img = article.find("div", class_="box-img").find("img")
            ppic = fix_image_url(img.get("data-lazy-src") or img.get("src", ""), base_domain) if img else ""
            pinfo = article.find("span", class_="EP").text.strip().replace("\n", " ") if article.find("span", class_="EP") else \
                    article.find("div", class_="p1").text.strip().replace("\n", " ") if article.find("div", class_="p1") else ""
        else:
            url = article.find("a")['href'] if article.find("a") else ""
            pname = article.find("h2").text.strip() if article.find("h2") else article.find("h3").text.strip() if article.find("h3") else ""
            img = article.find("img")
            ppic = fix_image_url(img.get("data-lazy-src") or img.get("src", ""), base_domain) if img else ""
            pinfo = article.find("div", class_="meta").text.strip().replace("\n", " ") if article.find("div", class_="meta") else ""
        return url, pname, ppic, pinfo
    except:
        return None, None, None, None

def get_pagination_movie285(soup):
    try:
        page = soup.find(role="navigation") or soup.find("nav", class_="pagination") or soup.find("div", class_="pagination")
        if page and page.find_all("a"):
            last_page = page.find_all("a")[-2]
            pmax_match = re.search(r'page/(\d+)/', last_page['href'])
            if pmax_match:
                pmax = int(pmax_match.group(1))
                print(f"[DEBUG] movie285 pagination: pmax={pmax} from last_page href")
                return pmax
            page_numbers = [int(a.text) for a in page.find_all("a") if a.text.isdigit()]
            if page_numbers:
                pmax = max(page_numbers)
                print(f"[DEBUG] movie285 pagination: pmax={pmax} from page numbers")
                return pmax
        next_page = soup.find("a", class_="next") or soup.find("a", text=re.compile(r'ถัดไป|Next'))
        if next_page and next_page.get('href'):
            pmax_match = re.search(r'page/(\d+)/', next_page['href'])
            if pmax_match:
                pmax = int(pmax_match.group(1))
                print(f"[DEBUG] movie285 pagination: pmax={pmax} from next_page href")
                return pmax
        print("[DEBUG] movie285 pagination: pmax=1 (no pagination found)")
        return 1
    except Exception as e:
        print(f"[DEBUG] movie285 pagination error: {str(e)}")
        return 1

def get_pagination_123hd(soup):
    try:
        page = soup.find("div", class_="pagination") or soup.find("nav", class_="navigation pagination")
        if page:
            links = page.find_all("a", class_="page-numbers") or page.find_all("a")
            if links:
                page_numbers = [int(link.text) for link in links if link.text.isdigit()]
                pmax = max(page_numbers) if page_numbers else 1
                print(f"[DEBUG] 123hd pagination: pmax={pmax} from page numbers")
                return pmax
        next_page = soup.find("a", class_="next page-numbers") or soup.find("a", text=re.compile(r'ถัดไป|Next'))
        if next_page and next_page.get('href'):
            last_page_match = re.search(r'page/(\d+)/', next_page['href'])
            if last_page_match:
                pmax = int(last_page_match.group(1))
                print(f"[DEBUG] 123hd pagination: pmax={pmax} from next_page href")
                return pmax
        print("[DEBUG] 123hd pagination: pmax=1 (no pagination found)")
        return 1
    except Exception as e:
        print(f"[DEBUG] 123hd pagination error: {str(e)}")
        return 1

def get_category_movie285(soup):
    try:
        ppname = soup.find("h1", class_="movie-title") or soup.find("h1")
        category = ppname.text.strip() if ppname else fname
        return category
    except:
        return "ดูหนังออนไลน์ หนังใหม่ HD ฟรี"

def get_category_123hd(soup):
    try:
        ppname = soup.find("h1")
        if ppname:
            category = ppname.text.strip()
            return category
        ppname = soup.find("div", class_="movietext")
        if ppname:
            ppname = ppname.text.strip()
            category = "ดูหนังออนไลน์ หนังใหม่ HD ฟรี" if ppname == "แนะนำหนังใหม่" else ppname
            return category
        return "ดูหนังออนไลน์ หนังใหม่ HD ฟรี"
    except:
        return "ดูหนังออนไลน์ หนังใหม่ HD ฟรี"

def get_episodes_123hd(soup_video, base_url):
    try:
        episodes = []
        episodes_table = soup_video.find("table", id="Sequel")
        if episodes_table:
            for row in episodes_table.find_all("tr")[1:]:
                link = row.find("a")
                if link and link.get('href'):
                    ep_num = link.text.strip()
                    ep_url = urljoin(base_url, link['href'])
                    episodes.append({'url': ep_url, 'number': ep_num})
        sequel_select = soup_video.find("select", {"name": "Sequel_select"})
        if sequel_select:
            for option in sequel_select.find_all("option"):
                ep_url = urljoin(base_url, option['value'])
                if ep_url and option['value']:
                    ep_num = option.text.strip()
                    episodes.append({'url': ep_url, 'number': ep_num})
        seen_urls = set()
        unique_episodes = []
        for ep in episodes:
            if ep['url'] not in seen_urls:
                seen_urls.add(ep['url'])
                unique_episodes.append(ep)
        return unique_episodes
    except:
        return []

def get_language_options_123hd(soup_video, driver, is_123hd=True):
    try:
        lang_options = []
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, div#halim-list-server, span, a, button"))
        )
        
        all_options = []
        
        lang_table = soup_video.find("table", style="width:100%; margin-top: -1px;")
        if lang_table:
            for th in lang_table.find_all("th", class_="selectmvbutton"):
                span = th.find("span")
                if span and span.text:
                    try:
                        span_element = driver.find_element(By.XPATH, f"//th[contains(@class, 'selectmvbutton')]//span[contains(text(), '{span.text}')]")
                        if "พากย์ไทย" in span.text:
                            all_options.append({'value': 'Thai', 'text': 'พากย์ไทย', 'element': span_element})
                        elif "ซับไทย" in span.text:
                            all_options.append({'value': 'Sound Track', 'text': 'ซับไทย', 'element': span_element})
                    except:
                        continue
        
        lang_div = soup_video.find("div", id="halim-list-server")
        if lang_div:
            for span in lang_div.find_all("span", class_="halim-btn"):
                if span.text:
                    try:
                        span_element = driver.find_element(By.XPATH, f"//div[@id='halim-list-server']//span[contains(@class, 'halim-btn') and contains(text(), '{span.text}')]")
                        if "พากย์ไทย" in span.text:
                            all_options.append({
                                'value': 'Thai', 'text': 'พากย์ไทย', 'element': span_element,
                                'data': {'postid': span.get('data-post-id', ''), 'episode': span.get('data-episode', ''), 'server': span.get('data-server', '')}
                            })
                        elif "ซับไทย" in span.text:
                            all_options.append({
                                'value': 'Sound Track', 'text': 'ซับไทย', 'element': span_element,
                                'data': {'postid': span.get('data-post-id', ''), 'episode': span.get('data-episode', ''), 'server': span.get('data-server', '')}
                            })
                    except:
                        continue
        
        additional_selectors = [
            "span[class*='btn'][class*='sound']",
            "a[class*='btn'][class*='sound']",
            "span:contains('พากย์')",
            "span:contains('ซับ')",
            "button:contains('พากย์')",
            "button:contains('ซับ')",
            "a:contains('พากย์')",
            "a:contains('ซับ')",
            "div:contains('พากย์')",
            "div:contains('ซับ')"
        ]
        for selector in additional_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if not text:
                        continue
                    if "พากย์ไทย" in text:
                        all_options.append({'value': 'Thai', 'text': 'พากย์ไทย', 'element': elem})
                    elif "ซับไทย" in text:
                        all_options.append({'value': 'Sound Track', 'text': 'ซับไทย', 'element': elem})
            except:
                continue
        
        has_thai_dub = any(opt['text'] == 'พากย์ไทย' for opt in all_options)
        
        if is_123hd:
            if has_thai_dub:
                lang_options = [opt for opt in all_options if opt['text'] == 'พากย์ไทย']
            else:
                lang_options = [opt for opt in all_options if opt['text'] == 'ซับไทย']
        else:
            lang_options = [opt for opt in all_options if opt['text'] in ['พากย์ไทย', 'ซับไทย']]
        
        if not lang_options:
            lang_options.append({'value': 'default', 'text': 'Default', 'element': None, 'data': {}})
        
        return lang_options
    except:
        return [{'value': 'default', 'text': 'Default', 'element': None, 'data': {}}]

def click_player_button_123hd(driver, btn_element):
    try:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(btn_element))
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_element)
        time.sleep(1)
        if btn_element.get_attribute("onclick"):
            driver.execute_script(btn_element.get_attribute("onclick"))
        else:
            try:
                driver.execute_script("arguments[0].click();", btn_element)
            except:
                btn_element.click()
        time.sleep(3)
        return True
    except (ElementClickInterceptedException, TimeoutException, WebDriverException):
        try:
            btn_element.send_keys(Keys.ENTER)
            time.sleep(3)
            return True
        except:
            try:
                driver.execute_script("arguments[0].dispatchEvent(new Event('click'));", btn_element)
                time.sleep(3)
                return True
            except:
                return False

def extract_m3u8_link_123hd(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#ajax-player iframe, iframe, video"))
        )
        soup_player = BeautifulSoup(driver.page_source, 'lxml')
        
        iframe = soup_player.select_one("#ajax-player iframe, iframe")
        if iframe and iframe.get("src"):
            elink = iframe["src"]
            if any(x in elink for x in ["serie-day.com/api/get.php", "123-hd.com/api/fileprocess.html", "waaw.to", "face", ".123players", "fembed.com"]):
                return None
            elink = edit_link(elink)
            if not elink or not elink.endswith('.m3u8'):
                return None
            hd_link = find_hd(elink) if needHD else elink
            return hd_link
        
        elink = find_m3u8_link(soup_player, driver.page_source, driver.current_url)
        if elink:
            hd_link = find_hd(elink) if needHD else elink
            return hd_link
        
        return None
    except:
        return None

def extract_m3u8_link_movie285(url, referer):
    try:
        view_page = get_page_content(url, sess, referer)
        if not view_page or "ขออภัย ไม่พบวิดีโอที่ต้องการ" in str(view_page.content):
            return None
        
        soup = BeautifulSoup(view_page.content, "lxml")
        
        player_iframe = soup.find("iframe")
        player_iframe_url = player_iframe.get('data-src') or player_iframe.get('src') if player_iframe else None
        if not player_iframe_url:
            elink = find_m3u8_link(soup, view_page.text, referer)
            if elink:
                return elink
            return None
        
        player_page = get_page_content(player_iframe_url, sess, referer)
        if not player_page:
            return None
        
        soup_player = BeautifulSoup(player_page.content, "lxml")
        
        outer_iframe_url = extract_iframe_url(soup_player, player_page.text)
        if not outer_iframe_url:
            elink = find_m3u8_link(soup_player, player_page.text, player_iframe_url)
            if elink:
                return elink
            return None
        
        outer_iframe_page = get_page_content(outer_iframe_url, sess, referer)
        if not outer_iframe_page:
            return None
        
        soup_outer_iframe = BeautifulSoup(outer_iframe_page.content, "lxml")
        
        elink = find_m3u8_link(soup_outer_iframe, outer_iframe_page.text, outer_iframe_url)
        if not elink:
            inner_iframe = soup_outer_iframe.find("iframe")
            if inner_iframe:
                inner_iframe_url = inner_iframe.get('src')
                inner_iframe_page = get_page_content(inner_iframe_url, sess, referer)
                if inner_iframe_page:
                    soup_inner_iframe = BeautifulSoup(inner_iframe_page.content, "lxml")
                    elink = find_m3u8_link(soup_inner_iframe, inner_iframe_page.text, inner_iframe_url)
        
        return elink
    except:
        return None

def is_series_movie285(url, soup_video):
    try:
        is_series = 'title="ซีรี่ย์"' in str(soup_video) and 'ตอนที่ 2' in str(soup_video)
        return is_series
    except:
        return False

def is_series_123hd(url, soup_video):
    try:
        url_lower = url.lower()
        if "ดูซีรีย์" in url_lower or "ซีรีย์" in url_lower or "/series/" in url_lower:
            return True
        if "ดูหนัง" in url_lower or "หนัง" in url_lower or "/movie/" in url_lower:
            return False
        if soup_video:
            title_tag = soup_video.find("title") or soup_video.find("h1")
            if title_tag and ("ซีรีย์" in title_tag.text.lower() or "series" in title_tag.text.lower()):
                return True
            meta_description = soup_video.find("meta", {"name": "description"})
            if meta_description and ("ซีรีย์" in meta_description.get("content", "").lower() or "series" in meta_description.get("content", "").lower()):
                return True
            episodes_table = soup_video.find("table", id="Sequel")
            sequel_select = soup_video.find("select", {"name": "Sequel_select"})
            if episodes_table or sequel_select:
                return True
        return False
    except:
        return False

def save_checkpoint(data, current_page, current_item):
    checkpoint_data = {"jseries": data, "current_page": current_page, "current_item": current_item}
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=1, ensure_ascii=False)
    except:
        pass

def load_checkpoint():
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            return checkpoint_data
        except:
            return None
    return None

def process_movie_content_123hd(driver, url, pname, ppic, pinfo, num, pmax, i, smax):
    try:
        display_name = pname
        tsub = pinfo
        if 'ซับไทย' in pname:
            tsub = 'ซับไทย'
            display_name = pname.replace('ซับไทย', '').strip()
        elif 'พากย์ไทย' in pname:
            tsub = 'พากย์ไทย'
            display_name = pname.replace('พากย์ไทย', '').strip()
        
        referer = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
        
        if not load_page_with_retry(driver, url):
            print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")
            return
        
        soup_video = BeautifulSoup(driver.page_source, 'lxml')
        is_123hd = '123-hd.com' in urlparse(web_movie).netloc
        language_options = get_language_options_123hd(soup_video, driver, is_123hd=is_123hd)
        
        for lang in language_options:
            tsub = lang['text']
            for attempt in range(3):
                try:
                    if lang['element'] is not None:
                        driver.execute_script("arguments[0].scrollIntoView(true);", lang['element'])
                        driver.execute_script("arguments[0].click();", lang['element'])
                        time.sleep(2)
                    play_btn = None
                    selectors = [
                        "a.play-btn", "span.halim-btn", "button[class*='play']", 
                        "a[class*='play']", "button.btn", "[onclick*='play']", 
                        ":contains('เล่น')", ":contains('Play')"
                    ]
                    for selector in selectors:
                        try:
                            play_btn = driver.find_element(By.CSS_SELECTOR, selector)
                            break
                        except:
                            continue
                    if not play_btn:
                        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")
                        continue
                    if not click_player_button_123hd(driver, play_btn):
                        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")
                        continue
                    elink = extract_m3u8_link_123hd(driver)
                    if not elink or elink in processed_links:
                        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")
                        continue
                    
                    processed_links.add(elink)
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [OK ✅]")
                    
                    if W_M3U:
                        global M_f
                        if M_f:
                            with open(os.path.join(f_path, f_m3u), 'w', encoding='utf-8') as f:
                                f.write("#EXTM3U\n\n")
                            M_f = 0
                        with open(os.path.join(f_path, f_m3u), 'a', encoding='utf-8') as f:
                            title = f"{display_name} {tsub}".strip()
                            f.write(f'#EXTINF:-1 group-title="MOVIE : {fname}" tvg-logo="{ppic}" ,{title}\n')
                            f.write(f'#EXTVLCOPT:http-referer={referer}\n')
                            f.write(f'{elink}\n\n')
                    
                    if W_W3U:
                        station_data = {
                            "name": display_name,
                            "info": tsub,
                            "image": ppic,
                            "url": elink,
                            "referer": referer
                        }
                        if tsub == 'พากย์ไทย':
                            station_data["subtitle"] = "https://pastebin.com/raw/cuyErKD4"
                        jseries['groups'].append({"name": display_name, "image": ppic, "info": tsub, "stations": [station_data]})
                    
                    save_checkpoint(jseries, num, i + 1)
                    break
                
                except:
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")
                    if attempt == 2:
                        break
                    time.sleep(2)
                    driver.get(url)
                    time.sleep(2)
                    continue
    
    except:
        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")

def process_movie_content_movie285(url, pname, ppic, pinfo, num, pmax, i, smax):
    try:
        display_name = pname
        tsub = pinfo
        if 'ซับไทย' in pname:
            tsub = 'ซับไทย'
            display_name = pname.replace('ซับไทย', '').strip()
        elif 'พากย์ไทย' in pname:
            tsub = 'พากย์ไทย'
            display_name = pname.replace('พากย์ไทย', '').strip()
        
        referer = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
        
        elink = extract_m3u8_link_movie285(url, referer)
        if not elink or elink in processed_links:
            print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")
            return
        
        processed_links.add(elink)
        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [OK ✅]")
        
        if W_M3U:
            global M_f
            if M_f:
                with open(os.path.join(f_path, f_m3u), 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n\n")
                M_f = 0
            with open(os.path.join(f_path, f_m3u), 'a', encoding='utf-8') as f:
                title = f"{display_name} {tsub}".strip()
                f.write(f'#EXTINF:-1 group-title="MOVIE : {fname}" tvg-logo="{ppic}" ,{title}\n')
                f.write(f'#EXTVLCOPT:http-referer={referer}\n')
                f.write(f'{elink}\n\n')
        
        if W_W3U:
            station_data = {
                "name": display_name,
                "info": tsub,
                "image": ppic,
                "url": elink,
                "referer": referer
            }
            if tsub == 'พากย์ไทย':
                station_data["subtitle"] = "https://pastebin.com/raw/cuyErKD4"
            jseries['groups'].append({"name": display_name, "image": ppic, "info": tsub, "stations": [station_data]})
        
        save_checkpoint(jseries, num, i + 1)
    
    except:
        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {tsub} [FAILED ❌]")

def process_series_content_123hd(driver, url, pname, ppic, pinfo, num, pmax, i, smax):
    try:
        display_name = pname
        if 'ซับไทย' in pname:
            pinfo = 'ซับไทย'
            display_name = pname.replace('ซับไทย', '').strip()
        elif 'พากย์ไทย' in pname:
            pinfo = 'พากย์ไทย'
            display_name = pname.replace('พากย์ไทย', '').strip()
        
        referer = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
        
        if not load_page_with_retry(driver, url):
            print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
            return
        
        soup_video = BeautifulSoup(driver.page_source, 'lxml')
        episodes = get_episodes_123hd(soup_video, url)
        
        if not episodes:
            process_movie_content_123hd(driver, url, pname, ppic, pinfo, num, pmax, i, smax)
            return
        
        jseries['groups'].append({"name": display_name, "image": ppic, "info": pinfo, "stations": []})
        g1 = len(jseries['groups']) - 1
        
        for episode in episodes:
            for attempt in range(3):
                try:
                    ep_name = episode['number']
                    ep_url = episode['url']
                    
                    if not load_page_with_retry(driver, ep_url):
                        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} [FAILED ❌]")
                        continue
                    
                    soup_video = BeautifulSoup(driver.page_source, 'lxml')
                    is_123hd = '123-hd.com' in urlparse(web_movie).netloc
                    language_options = get_language_options_123hd(soup_video, driver, is_123hd=is_123hd)
                    
                    for lang in language_options:
                        epinfo = lang['text']
                        try:
                            if lang['element'] is not None:
                                driver.execute_script("arguments[0].scrollIntoView(true);", lang['element'])
                                driver.execute_script("arguments[0].click();", lang['element'])
                                time.sleep(2)
                            
                            play_btn = None
                            selectors = [
                                "a.play-btn", "span.halim-btn", "button[class*='play']", 
                                "a[class*='play']", "button.btn", "[onclick*='play']", 
                                ":contains('เล่น')", ":contains('Play')"
                            ]
                            for selector in selectors:
                                try:
                                    play_btn = driver.find_element(By.CSS_SELECTOR, selector)
                                    break
                                except:
                                    continue
                            if not play_btn:
                                print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} {epinfo} [FAILED ❌]")
                                continue
                            if not click_player_button_123hd(driver, play_btn):
                                print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} {epinfo} [FAILED ❌]")
                                continue
                            elink = extract_m3u8_link_123hd(driver)
                            if not elink or elink in processed_links:
                                print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} {epinfo} [FAILED ❌]")
                                continue
                            
                            processed_links.add(elink)
                            print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} {epinfo} [OK ✅]")
                            
                            if W_M3U:
                                global M_f
                                if M_f:
                                    with open(os.path.join(f_path, f_m3u), 'w', encoding='utf-8') as f:
                                        f.write("#EXTM3U\n\n")
                                    M_f = 0
                                with open(os.path.join(f_path, f_m3u), 'a', encoding='utf-8') as f:
                                    title = f"{display_name} {ep_name} {epinfo}".strip()
                                    f.write(f'#EXTINF:-1 group-title="SERIES : {fname}" tvg-logo="{ppic}" ,{title}\n')
                                    f.write(f'#EXTVLCOPT:http-referer={referer}\n')
                                    f.write(f'{elink}\n\n')
                            
                            if W_W3U:
                                station_data = {
                                    "name": ep_name,
                                    "info": epinfo,
                                    "image": ppic,
                                    "url": elink,
                                    "referer": referer
                                }
                                if epinfo == 'พากย์ไทย':
                                    station_data["subtitle"] = "https://pastebin.com/raw/cuyErKD4"
                                jseries['groups'][g1]['stations'].append(station_data)
                            
                            save_checkpoint(jseries, num, i + 1)
                        
                        except:
                            print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} {epinfo} [FAILED ❌]")
                            continue
                    
                    break
                
                except:
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} [FAILED ❌]")
                    if attempt == 2:
                        break
                    time.sleep(3)
                    continue
    
    except:
        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")

def process_series_content_movie285(url, pname, ppic, pinfo, num, pmax, i, smax):
    try:
        display_name = pname
        if 'ซับไทย' in pname:
            pinfo = 'ซับไทย'
            display_name = pname.replace('ซับไทย', '').strip()
        elif 'พากย์ไทย' in pname:
            pinfo = 'พากย์ไทย'
            display_name = pname.replace('พากย์ไทย', '').strip()
        
        referer = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
        
        view_page = get_page_content(url, sess, referer)
        if not view_page:
            print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
            return
        
        soup = BeautifulSoup(view_page.content, "lxml")
        div = soup.find(class_="mt-right") or soup.find(id="single-post") or soup.find(class_="content")
        if not div:
            print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
            return
        
        episodes = []
        for link in div.find_all('a'):
            ep_url = link.get('href') or link.get('onclick', '').split("'")[1] if link.get('onclick') else ""
            if not ep_url:
                continue
            ep_img = link.find('img')['src'] if link.find('img') else ppic
            ename = link.find('img')['alt'] if link.find('img') else link.text.strip()
            if "ตอนที่" in ename:
                ep_num = "ตอนที่" + ename.split('ตอนที่')[-1].strip()
            elif "EP." in ename:
                ep_num = "ตอนที่ " + ename.split('EP.')[-1].strip()
            elif "EP" in ename:
                ep_num = "ตอนที่" + ename.split('EP')[-1].strip()
            else:
                ep_num = ename
            episodes.append({'url': urljoin(url, ep_url), 'number': ep_num, 'image': ep_img})
        
        jseries['groups'].append({"name": display_name, "image": ppic, "info": pinfo, "stations": []})
        g1 = len(jseries['groups']) - 1
        
        for ep_idx, episode in enumerate(episodes, start=1):
            try:
                ep_name = episode['number']
                ep_url = episode['url']
                ep_img = episode['image']
                
                epinfo = pinfo
                display_ename = ep_name
                if 'ซับไทย' in ep_name:
                    epinfo = 'ซับไทย'
                    display_ename = ep_name.replace('ซับไทย', '').strip()
                elif 'พากย์ไทย' in ep_name:
                    epinfo = 'พากย์ไทย'
                    display_ename = ep_name.replace('พากย์ไทย', '').strip()
                
                elink = extract_m3u8_link_movie285(ep_url, referer)
                if not elink or elink in processed_links:
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} {epinfo} [FAILED ❌]")
                    continue
                
                processed_links.add(elink)
                print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} {epinfo} [OK ✅]")
                
                if W_M3U:
                    global M_f
                    if M_f:
                        with open(os.path.join(f_path, f_m3u), 'w', encoding='utf-8') as f:
                            f.write("#EXTM3U\n\n")
                        M_f = 0
                    with open(os.path.join(f_path, f_m3u), 'a', encoding='utf-8') as f:
                        title = f"{display_name} {display_ename} {epinfo}".strip()
                        f.write(f'#EXTINF:-1 group-title="SERIES : {fname}" tvg-logo="{ep_img}" ,{title}\n')
                        f.write(f'#EXTVLCOPT:http-referer={referer}\n')
                        f.write(f'{elink}\n\n')
                
                if W_W3U:
                    station_data = {
                        "name": display_ename,
                        "info": epinfo,
                        "image": ep_img,
                        "url": elink,
                        "referer": referer
                    }
                    if epinfo == 'พากย์ไทย':
                        station_data["subtitle"] = "https://pastebin.com/raw/cuyErKD4"
                    jseries['groups'][g1]['stations'].append(station_data)
                
                save_checkpoint(jseries, num, i + 1)
            
            except:
                print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} {ep_name} [FAILED ❌]")
                continue
    
    except:
        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")

def process_page_movie285(url, base_url):
    try:
        checkpoint = load_checkpoint()
        if checkpoint:
            global jseries
            jseries = checkpoint['jseries']
            pcurrent = checkpoint['current_page']
            start_item = checkpoint['current_item']
        else:
            pcurrent = 1
            start_item = 1
        
        home_page = get_page_content(url, sess, headers['Referer'])
        if not home_page:
            print("[DEBUG] Failed to load home page")
            return
        
        soup = BeautifulSoup(home_page.content, "lxml")
        pmax = get_pagination_movie285(soup)
        ppname = get_category_movie285(soup)
        print(ppname)
        jseries['name'] = ppname
        jseries['image'] = 'https://movie285-hd.com/wp-content/uploads/2023/11/movie285logo.png'
        jseries['author'] = timeday
        
        # จำกัดจำนวนหน้าตาม max_pages
        end_page = min(pmax + 1, pcurrent + max_pages) if max_pages > 0 else pmax + 1
        print(f"[DEBUG] Processing pages from {pcurrent} to {end_page-1} (max_pages={max_pages}, pmax={pmax})")
        
        for num in range(int(pcurrent), end_page):
            plink = url if num == 1 else f"{url.rstrip('/')}page/{num}/"
            print(f"[DEBUG] Loading page {num}/{pmax}: {plink}")
            home_page = get_page_content(plink, sess, headers['Referer'])
            if not home_page:
                print(f"[หน้า : {num}/{pmax}] [FAILED ❌] ไม่สามารถโหลดหน้าได้")
                continue
            soup = BeautifulSoup(home_page.content, "lxml")
            
            articles = None
            selectors = [
                "div.movie-grid > figure.movie-box",
                "div.item",
                "article",
                "div.movie-item",
                "div.post"
            ]
            for selector in selectors:
                try:
                    articles = soup.select(selector)
                    if articles:
                        break
                except:
                    continue
            
            if not articles:
                print(f"[หน้า : {num}/{pmax}] [FAILED ❌] ไม่พบรายการในหน้า")
                continue
            
            smax = len(articles)
            print(f"[DEBUG] Found {smax} articles on page {num}")
            
            for i, article in enumerate(articles, start=1):
                if num == pcurrent and i < start_item:
                    continue
                url, pname, ppic, pinfo = get_movie_info_movie285(article, urlparse(web_movie).netloc)
                if not url or not pname:
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
                    continue
                
                try:
                    url = urljoin(base_url, url)
                    view_page = get_page_content(url, sess, headers['Referer'])
                    if not view_page:
                        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
                        continue
                    soup_video = BeautifulSoup(view_page.content, "lxml")
                    
                    if is_series_movie285(url, soup_video):
                        process_series_content_movie285(url, pname, ppic, pinfo, num, pmax, i, smax)
                    else:
                        process_movie_content_movie285(url, pname, ppic, pinfo, num, pmax, i, smax)
                
                except:
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
                    save_checkpoint(jseries, num, i)
                    continue
            
            # บันทึก checkpoint หลังจากประมวลผลแต่ละหน้า
            save_checkpoint(jseries, num + 1, 1)
        
        if W_W3U:
            with open(os.path.join(f_path, f_w3u), 'w', encoding='utf-8') as f:
                json.dump(jseries, f, indent=1, ensure_ascii=False)
    
    except Exception as e:
        print(f"[DEBUG] process_page_movie285 error: {str(e)}")

def process_page_123hd(url, base_url):
    try:
        checkpoint = load_checkpoint()
        if checkpoint:
            global jseries
            jseries = checkpoint['jseries']
            pcurrent = checkpoint['current_page']
            start_item = checkpoint['current_item']
        else:
            pcurrent = 1
            start_item = 1
        
        if not load_page_with_retry(driver, url):
            print("[DEBUG] Failed to load home page")
            return
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        pmax = get_pagination_123hd(soup)
        ppname = get_category_123hd(soup)
        print(ppname)
        jseries['name'] = ppname
        jseries['author'] = timeday
        
        # จำกัดจำนวนหน้าตาม max_pages
        end_page = min(pmax + 1, pcurrent + max_pages) if max_pages > 0 else pmax + 1
        print(f"[DEBUG] Processing pages from {pcurrent} to {end_page-1} (max_pages={max_pages}, pmax={pmax})")
        
        for num in range(int(pcurrent), end_page):
            plink = url if num == 1 else f"{url.rstrip('/')}page/{num}/"
            print(f"[DEBUG] Loading page {num}/{pmax}: {plink}")
            if not load_page_with_retry(driver, plink):
                print(f"[หน้า : {num}/{pmax}] [FAILED ❌] ไม่สามารถโหลดหน้าได้")
                continue
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            articles = soup.find_all("div", class_="box") or soup.find_all("div", class_="item") or soup.find_all("article")
            if not articles:
                print(f"[หน้า : {num}/{pmax}] [FAILED ❌] ไม่พบรายการในหน้า")
                continue
            
            smax = len(articles)
            print(f"[DEBUG] Found {smax} articles on page {num}")
            
            for i, article in enumerate(articles, start=1):
                if num == pcurrent and i < start_item:
                    continue
                url, pname, ppic, pinfo = get_movie_info_123hd(article, urlparse(web_movie).netloc)
                if not url or not pname:
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
                    continue
                
                try:
                    url = urljoin(base_url, url)
                    if not load_page_with_retry(driver, url):
                        print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
                        continue
                    soup_video = BeautifulSoup(driver.page_source, 'lxml')
                    
                    if is_series_123hd(url, soup_video):
                        process_series_content_123hd(driver, url, pname, ppic, pinfo, num, pmax, i, smax)
                    else:
                        process_movie_content_123hd(driver, url, pname, ppic, pinfo, num, pmax, i, smax)
                
                except:
                    print(f"[หน้า : {num}/{pmax} เรื่องที่ : {i}/{smax}] {pname} [FAILED ❌]")
                    save_checkpoint(jseries, num, i)
                    continue
            
            # บันทึก checkpoint หลังจากประมวลผลแต่ละหน้า
            save_checkpoint(jseries, num + 1, 1)
        
        if W_W3U:
            with open(os.path.join(f_path, f_w3u), 'w', encoding='utf-8') as f:
                json.dump(jseries, f, indent=1, ensure_ascii=False)
    
    except Exception as e:
        print(f"[DEBUG] process_page_123hd error: {str(e)}")

try:
    base_domain = urlparse(web_movie).netloc
    base_url = f"{urlparse(web_movie).scheme}://{base_domain}"
    
    if 'movie285-hd.com' in base_domain or 'xn--285-1klzd4a0j0b1d.com' in base_domain:
        process_page_movie285(web_movie, base_url)
    elif '123-hd.com' in base_domain or 'serieday-hd.com' in base_domain:
        process_page_123hd(web_movie, base_url)
    else:
        raise Exception("URL ไม่ตรงกับเว็บที่รองรับ")

finally:
    if driver:
        driver.quit()
    print(f"\nจบแล้ว ไฟล์: {f_m3u} ตำแหน่ง: {f_path}")
    if os.path.exists(checkpoint_file):
        try:
            os.remove(checkpoint_file)
        except:
            pass