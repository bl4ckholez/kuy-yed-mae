import requests, re, json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import logging, os

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

web_movie = "https://037hd.tv/%e0%b8%ab%e0%b8%99%e0%b8%b1%e0%b8%87%e0%b9%80%e0%b8%ad%e0%b9%80%e0%b8%8a%e0%b8%b5%e0%b8%a2/"

web_movie = "https://037hd.tv/%e0%b8%94%e0%b8%b9%e0%b8%8b%e0%b8%b5%e0%b8%a3%e0%b8%b5%e0%b9%88%e0%b8%a2%e0%b9%8c/"
f_path = "/sdcard/"
debug_path = "/data/data/com.termux/files/home/"
fname = unquote(urlparse(web_movie).path.strip('/').split('/')[-1])
wname = unquote(urlparse(web_movie).netloc.strip('.').split('.')[-2])
f_m3u = f_m3u1 = wname + "_" + fname + ".m3u"
f_preM = "Movie_"
f_preS = "Series_"
W_M3U = M_S = 1
checkpoint_file = f"{f_path}{wname}_{fname}_checkpoint.json"

# ดึงหมวดหมู่จาก web_movie
category_from_url = unquote(web_movie.split('/')[-2]).replace('-', ' ').replace('_', '')

# ตรวจสอบสิทธิ์ /sdcard/
try:
    with open(f"{f_path}test.txt", 'w') as f:
        f.write("test")
    os.remove(f"{f_path}test.txt")
except PermissionError:
    logger.error("ไม่มีสิทธิ์เขียนใน /sdcard/. รัน 'termux-setup-storage' และลองใหม่")
    exit(1)

if W_M3U:
    for prefix in ([f_preM, f_preS] if M_S else [""]):
        try:
            with open(f"{f_path}{prefix}{f_m3u1}", 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
        except PermissionError as e:
            logger.error(f"ไม่สามารถเขียนไฟล์ {f_path}{prefix}{f_m3u1}: {str(e)}")
            exit(1)

def save_checkpoint(pcurrent, processed_urls):
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump({"current_page": pcurrent, "processed_urls": list(processed_urls)}, f)
    except PermissionError as e:
        logger.error(f"ไม่สามารถเขียน checkpoint: {str(e)}")

def load_checkpoint():
    return {"current_page": 1, "processed_urls": []}  # เริ่มหน้า 1 เสมอ

def test_link(elink, referer, headers):
    try:
        sess = requests.Session()
        sess.headers.update(headers | {'referer': referer, 'origin': referer.rstrip('/')})
        resp = sess.get(elink, stream=True, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            content = resp.text[:500].lower()
            if 'm3u8' in content or 'candyxplay.com' in elink or resp.headers.get('content-type', '').startswith(('application', 'video')):
                return True, resp.text
        return False, resp.text
    except Exception as e:
        logger.error(f"Error testing link {elink}: {str(e)}")
        return False, str(e)

def fetch_m3u8_link(url, referers, headers, depth=0):
    if depth > 2:
        logger.error(f"Max depth reached for {url}")
        return None
    try:
        sess = requests.Session()
        sess.headers.update(headers)
        for referer in referers:
            sess.headers.update({'referer': referer, 'origin': referer.rstrip('/')})
            resp = sess.get(url, timeout=10)
            if resp.status_code == 200:
                break
        else:
            logger.error(f"Failed to fetch {url}")
            return None
        soup = BeautifulSoup(resp.content, "lxml")
        purl = re.sub(r'\n|\r', '', str(soup))
        patterns = [
            r'(https?://[^\s"]+\.m3u8)', 
            r'(https?://master\.streamhls\.com/p2p/[^\s"]+)', 
            r'(https?://vidhide\.com/[^\s"]+)', 
            r'(https?://candyxplay\.com/hls/[^\s"]+/index\.m3u8)', 
            r'(https?://candyxplay\.com/player/[^\s"]+)'
        ]
        for pattern in patterns:
            if match := re.search(pattern, purl):
                elink = re.sub(r'[\'";\\]', '', match.group(1)).strip()
                if not elink.startswith('http'):
                    elink = f"{referers[0]}{elink.lstrip('/')}"
                if test_link(elink, referers[0], headers)[0]:
                    logger.error(f"Found valid link: {elink}")
                    return elink
        for tag in soup.find_all(['video', 'source', 'iframe']):
            if src := tag.get('src', ''):
                elink = src if src.startswith('http') else f"{referers[0]}{src.lstrip('/')}"
                if test_link(elink, referers[0], headers)[0]:
                    logger.error(f"Found valid tag link: {elink}")
                    return elink
        for script in soup.find_all('script'):
            if script.string and any(x in script.string for x in ['m3u8', 'hls/', 'candyxplay.com']):
                if match := re.search(r'(https?://(?:[^\s"]+\.m3u8|candyxplay\.com/(?:hls|player)/[^\s"]+))', script.string):
                    elink = re.sub(r'[\'";\\]', '', match.group(1)).strip()
                    if test_link(elink, referers[0], headers)[0]:
                        logger.error(f"Found valid script link: {elink}")
                        return elink
        if 'candyxplay.com/player/' in url:
            elink = url.replace('/player/', '/hls/') + '/index.m3u8'
            if test_link(elink, referers[0], headers)[0]:
                logger.error(f"Found valid converted link: {elink}")
                return elink
        return None
    except Exception as e:
        logger.error(f"Error fetching link from {url}: {str(e)}")
        return None

def get_movie_category(soup, purl, plink):
    return category_from_url

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}
referers = ['https://037hd.tv/', 'https://vidhide.com/', 'https://master.streamhls.com/', 'https://candyxplay.com/']
sess = requests.Session()
sess.headers.update(headers)

home_page = sess.get(web_movie)
soup = BeautifulSoup(home_page.content, "lxml")

try:
    with open(f"{debug_path}debug_home.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
except Exception as e:
    logger.error(f"Cannot save debug_home.html: {str(e)}")

container = soup.find(["section", "div"], class_=re.compile(r'contentmovie|content-movie|movies|content|archive|list|movie-list|content-area|post-list|entry-content'))
if not container:
    logger.error("No content container found. Check debug_home.html.")
    exit(1)

grid_movie = container.find(["div", "section"], class_=re.compile(r'grid-movie|movie-grid|posts|items|list|archive|movie-list|post-list'))
if not grid_movie:
    logger.error("No grid container found. Check debug_home.html.")
    exit(1)

movies = [m for m in grid_movie.find_all(["div", "article"], class_=re.compile(r'box|item|post|movie|entry|movie-item|post-item|card'))
          if m.find("a", href=re.compile(r'https://037hd\.tv/[^/]+/$')) and not any(x in ' '.join(m.get("class", [])) for x in ['ad', 'banner', 'widget', 'sidebar'])]
if not movies:
    logger.error("No movie items found. Falling back to direct links...")
    movies = [a for a in soup.find_all("a", href=re.compile(r'https://037hd\.tv/[^/]+/$')) 
              if "fillter" not in a['href'] and "?" not in a['href'] and not any(x in ' '.join(a.get("class", [])) for x in ['ad', 'banner', 'widget', 'sidebar'])]
    if not movies:
        logger.error("No direct movie links found. Check debug_home.html.")
        exit(1)

logger.error(f"Found {len(movies)} movie items on home page")

checkpoint = load_checkpoint()
pcurrent = checkpoint["current_page"]
processed_urls = set(checkpoint["processed_urls"])

pagination = soup.find(["div", "nav"], class_=re.compile(r'pagination|page-navigation|paging|nav-links'))
if pagination:
    page_links = pagination.find_all("a", href=re.compile(r'/page/\d+/'))
    pages = [int(re.search(r'/page/(\d+)/', a['href']).group(1)) for a in page_links if re.search(r'/page/(\d+)/', a['href'])]
    lastpage = max(pages) if pages else 1
else:
    page_matches = re.findall(r'/page/(\d+)/', str(soup))
    lastpage = max([int(p) for p in page_matches]) if page_matches else 1

if lastpage < 123:
    logger.error(f"พบแค่ {lastpage} หน้า ลองค้นหาเพิ่ม...")
    page_matches = re.findall(r'/page/(\d+)/', str(soup))
    if page_matches:
        lastpage = max([int(p) for p in page_matches])
    if lastpage < 123:
        for i in range(2, 124):
            test_url = f"{web_movie}page/{i}/"
            resp = sess.get(test_url, timeout=5)
            if resp.status_code == 200:
                lastpage = max(lastpage, i)
            else:
                break

print(f"พบทั้งหมด {lastpage} หน้า")
while True:
    try:
        user_input = input(f"ต้องการดึงกี่หน้า? (1-{lastpage}, 0 หรือว่างเพื่อดึงทั้งหมด): ").strip()
        if user_input == "" or user_input == "0":
            user_pages = lastpage
            break
        user_pages = int(user_input)
        if 1 <= user_pages <= lastpage:
            break
        print(f"กรุณาป้อนตัวเลขระหว่าง 1-{lastpage} หรือ 0")
    except ValueError:
        print("กรุณาป้อนตัวเลขเท่านั้น")
lastpage = user_pages
onepage = 0 if lastpage > 1 else 1
print(soup.title.string)

while pcurrent <= lastpage:
    plink = web_movie if pcurrent == 1 else f"{web_movie}page/{pcurrent}/"
    
    home_page = sess.get(plink)
    soup = BeautifulSoup(home_page.content, "lxml")
    
    try:
        with open(f"{debug_path}debug_page_{pcurrent}.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
    except Exception as e:
        logger.error(f"Cannot save debug_page_{pcurrent}.html: {str(e)}")
    
    container = soup.find(["section", "div"], class_=re.compile(r'contentmovie|content-movie|movies|content|archive|list|movie-list|content-area|post-list|entry-content'))
    if not container:
        logger.error(f"No content container for page {pcurrent}. Skipping...")
        pcurrent += 1
        continue
    
    grid_movie = container.find(["div", "section"], class_=re.compile(r'grid-movie|movie-grid|posts|items|list|archive|movie-list|post-list'))
    if not grid_movie:
        logger.error(f"No grid container for page {pcurrent}. Skipping...")
        pcurrent += 1
        continue
    
    movies = [m for m in grid_movie.find_all(["div", "article"], class_=re.compile(r'box|item|post|movie|entry|movie-item|post-item|card'))
              if m.find("a", href=re.compile(r'https://037hd\.tv/[^/]+/$')) and not any(x in ' '.join(m.get("class", [])) for x in ['ad', 'banner', 'widget', 'sidebar'])]
    if not movies:
        logger.error(f"No movie items on page {pcurrent}. Falling back to direct links...")
        movies = [a for a in soup.find_all("a", href=re.compile(r'https://037hd\.tv/[^/]+/$')) 
                  if "fillter" not in a['href'] and "?" not in a['href'] and not any(x in ' '.join(a.get("class", [])) for x in ['ad', 'banner', 'widget', 'sidebar'])]
        if not movies:
            logger.error(f"No direct movie links on page {pcurrent}. Skipping...")
            pcurrent += 1
            continue
    
    logger.error(f"Found {len(movies)} movie items on page {pcurrent}")
    
    for i, movie in enumerate(movies, 1):
        try:
            if movie.name == 'a':
                purl = movie['href']
                if "fillter" in purl or "?" in purl:
                    continue
            else:
                a_tag = movie.find("a", href=re.compile(r'https://037hd\.tv/[^/]+/$'))
                if not a_tag:
                    continue
                purl = a_tag['href']
                if "fillter" in purl or "?" in purl:
                    continue
            pname = movie.get_text().strip() if movie.name == 'a' else (movie.find(["div", "h2", "h3"], class_=re.compile(r'p2|title|name')).get_text().strip() if movie.find(["div", "h2", "h3"], class_=re.compile(r'p2|title|name')) else "Unknown Title")
            ppic = movie.find("img", class_=re.compile(r'attachment|poster|thumbnail'))['src'] if movie.find("img", class_=re.compile(r'attachment|poster|thumbnail')) else ""
            pquality = movie.find("div", class_=re.compile(r'movie-corner|quality')).get_text().strip() if movie.find("div", class_=re.compile(r'movie-corner|quality')) else "HD"
        except Exception as e:
            logger.error(f"Error parsing movie {i} on page {pcurrent}: {str(e)}")
            continue
        
        ptype = "Series" if "/series/" in purl else "Movies"
        referers = ['https://037hd.tv/', f"{'://'.join(purl.split('/')[:3])}/", 'https://vidhide.com/', 'https://master.streamhls.com/', 'https://candyxplay.com/']
        sess.headers.update({'referer': referers[0]})
        home_page = sess.get(purl)
        soup = BeautifulSoup(home_page.content, "lxml")
        
        try:
            with open(f"{debug_path}debug_movie_{re.sub(r'[^\w\s-]', '_', soup.title.get_text().strip())[:50]}.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
        except Exception as e:
            logger.error(f"Cannot save debug_movie.html: {str(e)}")
        
        title_type = "TITLE SERIES" if ptype == "Series" else "TITLE MOVIE"
        print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality})")
        
        if ptype == "Movies":
            category = get_movie_category(soup, purl, plink)
            group_title = f"MOVIE : {category}"
            iframe = soup.find("iframe")
            if not iframe:
                logger.error(f"No iframe for {pname}")
                print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality}) [FAILED ❌]")
                processed_urls.add(purl)
                save_checkpoint(pcurrent, processed_urls)
                continue
            elink = fetch_m3u8_link(iframe['src'], referers, headers)
            if not elink:
                logger.error(f"No valid link for {pname}")
                print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality}) [FAILED ❌]")
                processed_urls.add(purl)
                save_checkpoint(pcurrent, processed_urls)
                continue
            f_m3u = f"{f_preM}{f_m3u1}" if M_S else f_m3u
            try:
                with open(f"{f_path}{f_m3u}", 'a', encoding='utf-8') as f:
                    f.write(f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{ppic}" ,{pname} ({pquality})\n')
                    f.write(f'#EXTVLCOPT:http-referrer={referers[0]}\n{elink}\n')
                print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality}) [OK ✔️]")
            except Exception as e:
                logger.error(f"Error writing to {f_path}{f_m3u}: {str(e)}")
                print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality}) [FAILED ❌]")
        else:
            group_title = f"SERIES : {pname} ({pquality})"
            purl_str = re.sub(r'\n|\r', '', str(soup))
            data = re.search(r"let movieList = (.+?)\;", purl_str)
            if not data:
                logger.error(f"No movieList for {pname}")
                iframe = soup.find("iframe")
                if iframe and (elink := fetch_m3u8_link(iframe['src'], referers, headers)):
                    f_m3u = f"{f_preS}{f_m3u1}" if M_S else f_m3u
                    try:
                        with open(f"{f_path}{f_m3u}", 'a', encoding='utf-8') as f:
                            f.write(f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{ppic}" ,{pname} ({pquality})\n')
                            f.write(f'#EXTVLCOPT:http-referrer={referers[0]}\n{elink}\n')
                        print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality}) [OK ✔️]")
                    except Exception as e:
                        logger.error(f"Error writing to {f_path}{f_m3u}: {str(e)}")
                        print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality}) [FAILED ❌]")
                processed_urls.add(purl)
                save_checkpoint(pcurrent, processed_urls)
                continue
            data = re.sub(r'\s|//|\\|/\*.+?\*/', '', data.group(1)).replace(',}', '}')
            try:
                site_json = json.loads(data)
            except Exception as e:
                logger.error(f"JSON parse error for {pname}: {str(e)}")
                print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {pname} ({pquality}) [FAILED ❌]")
                processed_urls.add(purl)
                save_checkpoint(pcurrent, processed_urls)
                continue
            ep_counter = 1
            for ID in site_json['seasonList']:
                season_name = site_json['seasonList'][ID]['name']
                for EP in site_json['seasonList'][ID]['epList']:
                    try:
                        esound = len(site_json['seasonList'][ID]['epList'][EP]['sound'])
                    except:
                        logger.error(f"Error parsing episode for {pname}")
                        continue
                    for num in range(esound):
                        nsound = site_json['seasonList'][ID]['epList'][EP]['sound'][num]
                        pinfo = site_json['seasonList'][ID]['epList'][EP]['link'][nsound][0]['MU_sound'].capitalize()
                        ename = f"ตอนที่ {ep_counter}"
                        MU_url = site_json['seasonList'][ID]['epList'][EP]['link'][nsound][0]['MU_url']
                        MU_url = re.sub(r'.*https://', 'https://', MU_url) if '/https://' in MU_url else MU_url.replace('https:', 'https://')
                        if elink := fetch_m3u8_link(MU_url, referers, headers):
                            f_m3u = f"{f_preS}{f_m3u1}" if M_S else f_m3u
                            try:
                                with open(f"{f_path}{f_m3u}", 'a', encoding='utf-8') as f:
                                    f.write(f'#EXTINF:-1 group-title="{group_title}" tvg-logo="{ppic}" ,{ename}\n')
                                    f.write(f'#EXTVLCOPT:http-referrer={referers[0]}\n{elink}\n')
                                print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {ename} [OK ✔️]")
                            except Exception as e:
                                logger.error(f"Error writing to {f_path}{f_m3u}: {str(e)}")
                                print(f"[หน้า{pcurrent:>3}/{lastpage:<3}] [เรื่อง {i:>2}/{len(movies):<2}] {title_type} : {ename} [FAILED ❌]")
                        ep_counter += 1
        processed_urls.add(purl)
        save_checkpoint(pcurrent, processed_urls)
    
    if onepage:
        break
    pcurrent += 1
    save_checkpoint(pcurrent, processed_urls)

print("THE END")
if W_M3U:
    print(f"M3u Go to {f_path}{f_m3u}")