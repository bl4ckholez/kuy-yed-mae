import requests, re, json, os, base64
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote, urljoin
from clint.textui import colored
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# กำหนดค่าเริ่มต้น
web_movie = "https://xn--285-1klzd4a0j0b1d.com/"
#web_movie = input("\n กรุณาใส่ URL : ")
f_path = "/sdcard/55/1DM/output/"
try:
    if not os.path.exists(f_path):
        os.makedirs(f_path)
    test_file = os.path.join(f_path, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
except Exception as e:
    print(colored.red(f"Cannot write to {f_path}: {e}"))
    exit(1)

date = datetime.now().strftime("%d")
mo = datetime.now().strftime("%m")
month = ['', 'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
timeday = f'วันที่ {date} {month[int(mo)]} {int(datetime.now().strftime("%Y"))+543}'

fname = unquote(urlparse(web_movie).path.strip('/').split('/')[-1])
wname = unquote(urlparse(web_movie).netloc.strip('.').split('.')[-2])
f_w3u = wname + "_" + fname + ".w3u"
f_m3u = wname + "_" + fname + ".m3u"
checkpoint_file = os.path.join(f_path, f"{wname}_{fname}_checkpoint.json")

W_W3U = 0
W_M3U = 1
M_f = 1
pcurrent = 1

aseries = """{
    "name": "",
    "author": "",
    "info": "",
    "image": "",
    "key": []}"""

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

jmovie = json.loads(aseries)
jmovie['stations'] = jmovie.pop('key')
jseries = json.loads(aseries)
jseries['groups'] = jseries.pop('key')

parsed_uri = urlparse(web_movie)
referer = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
sess = requests.Session()
sess.headers.update(headers)

def validate_url(url):
    try:
        result = requests.head(url, headers=headers, timeout=5)
        return result.status_code == 200
    except requests.RequestException:
        return False

def get_page_content(url, session, referer):
    try:
        session.headers.update({'referer': referer})
        response = session.get(url, timeout=15)
        response.encoding = response.apparent_encoding or 'utf-8'
        return response
    except requests.RequestException:
        return None

def get_dynamic_page(url):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument(f"user-agent={headers['User-Agent']}")
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        content = driver.page_source
        driver.quit()
        return content
    except Exception:
        return None

def find_m3u8_link(soup, page_content, referer, depth):
    source_match = None
    video = soup.find("video")
    if video:
        source = video.find("source")
        if source and source.get("src"):
            source_match = re.match(r'(https?://[^\s"]+\.m3u8)', source["src"])
    
    if not source_match:
        patterns = [
            r'file:\s*["\'](.+\.m3u8)["\']',
            r'source src="(.+\.m3u8)"',
            r'["\'](.+\.m3u8)["\']',
            r'(https?://[^\s"]+\.m3u8)',
            r'source\s*:\s*["\'](.+\.m3u8)["\']',
            r'url\s*:\s*["\'](.+\.m3u8)["\']',
            r'playlist\s*:\s*["\'](.+\.m3u8)["\']',
            r'master\s*:\s*["\'](.+\.m3u8)["\']',
            r'hls\s*:\s*["\'](.+\.m3u8)["\']',
            r'src\s*:\s*["\'](.+\.m3u8)["\']',
            r'data-source\s*:\s*["\'](.+\.m3u8)["\']',
            r'video\s*:\s*["\'](.+\.m3u8)["\']'
        ]
        for pattern in patterns:
            match = re.search(pattern, page_content.text if hasattr(page_content, 'text') else page_content, re.IGNORECASE)
            if match:
                source_match = match
                break
    
    if not source_match:
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                for pattern in patterns:
                    match = re.search(pattern, script.string, re.IGNORECASE)
                    if match:
                        source_match = match
                        break
                if source_match:
                    break
    
    if source_match:
        elink = source_match.group(1)
        if not elink.startswith('http'):
            elink = urljoin(referer, elink)
        if validate_url(elink):
            return elink
    return None

def extract_iframe_url(soup, page_content, referer):
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "const encoded" in script.string:
            match = re.search(r'const encoded = "([^"]+)";', script.string)
            if match:
                encoded = match.group(1)
                try:
                    return base64.b64decode(encoded).decode('utf-8')
                except Exception:
                    pass
    
    iframe = soup.find("iframe")
    if iframe:
        return iframe.get('src') or iframe.get('data-src')
    
    for script in scripts:
        if script.string:
            match = re.search(r'iframe\.src\s*=\s*["\']([^"\']+)["\']', script.string)
            if match:
                return match.group(1)
            match = re.search(r'(https?://[^\s"]+player[^"\s]*)', script.string, re.IGNORECASE)
            if match:
                return match.group(1)
    return None

def process_iframe(url, session, referer, depth=0, max_depth=4):
    if depth >= max_depth:
        return None
    
    page = get_page_content(url, session, referer)
    if page:
        soup = BeautifulSoup(page.content, "lxml")
        elink = find_m3u8_link(soup, page, referer, depth)
        if elink:
            return elink
    else:
        page_content = get_dynamic_page(url)
        if page_content:
            soup = BeautifulSoup(page_content, "lxml")
            elink = find_m3u8_link(soup, page_content, referer, depth)
            if elink:
                return elink
    
    next_iframe_url = extract_iframe_url(soup, page or page_content, referer)
    if next_iframe_url:
        if not next_iframe_url.startswith('http'):
            next_iframe_url = urljoin(referer, next_iframe_url)
        new_referer = urlparse(next_iframe_url).scheme + '://' + urlparse(next_iframe_url).netloc + '/'
        return process_iframe(next_iframe_url, session, new_referer, depth + 1, max_depth)
    return None

def save_checkpoint(data, current_page, current_item):
    try:
        checkpoint_data = {
            "jseries": data,
            "current_page": current_page,
            "current_item": current_item
        }
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=1, ensure_ascii=False)
    except Exception:
        pass

def load_checkpoint():
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            return checkpoint_data
        except Exception:
            return None
    return None

# ตรวจสอบ URL
if not validate_url(web_movie):
    print(colored.red("Invalid URL provided"))
    exit(1)

# โหลด checkpoint
checkpoint = load_checkpoint()
if checkpoint:
    jseries = checkpoint['jseries']
    pcurrent = checkpoint['current_page']
    start_item = checkpoint['current_item']
else:
    start_item = 1

# ดึงหน้าแรก
home_page = get_page_content(web_movie, sess, referer)
if not home_page:
    print(colored.red("Failed to fetch home page"))
    exit(1)

soup = BeautifulSoup(home_page.content, "html.parser")
page = soup.find(role="navigation")
if page is not None and page.find_all("a"):
    pmax = page.find_all("a")[-2]['href']
    pmax = unquote(urlparse(pmax).path.strip('/').split('/')[-1])
else:
    pmax = 1

# ดึงชื่อหมวดหมู่
category_display = soup.find("h1", class_="movie-title").text.strip() if soup.find("h1", class_="movie-title") else fname
jmovie['name'] = jseries['name'] = category_display
jmovie['image'] = jseries['image'] = 'https://movie285-hd.com/wp-content/uploads/2023/11/movie285logo.png'
jmovie['author'] = jseries['author'] = timeday
print(colored.yellow(category_display))

# วนลูปแต่ละหน้า
pbak = web_movie
for num in range(int(pcurrent), int(pmax)+1):
    print(f"\n\n\033[1m\033[37m[Pages : {num:}/{pmax:}]\033[0m \033[93m{category_display}\033[0m")
    #print(f"[Pages : {num}/{pmax}]")
    if num == 1:
        plink = pbak = web_movie
    else:
        plink = f"page/{num}/"
        plink = pbak = web_movie.rstrip('/') + '/' + plink.lstrip('/')
    
    home_page = get_page_content(plink, sess, referer)
    if not home_page:
        continue
        
    soup = BeautifulSoup(home_page.content, "lxml")
    div = soup.find("div", class_="movie-grid")
    if not div:
        continue
        
    figures = div.find_all("figure", class_="movie-box")
    for i, figure in enumerate(figures, start=1):
        if num == pcurrent and i < start_item:
            continue
        try:
            link = figure.find("a")
            purl = link['href']
            ppic = link.find("img")['src']
            pname = link.find("h3", class_="movie-title").text.strip()
            
            pinfo = ''
            if 'ซับไทย' in pname:
                pinfo = 'ซับไทย'
                display_name = pname.replace('ซับไทย', '').strip()
            elif 'พากย์ไทย' in pname:
                pinfo = 'พากย์ไทย'
                display_name = pname.replace('พากย์ไทย', '').strip()
            else:
                display_name = pname
            
            print(f"\n\n \033[1m\033[37m[Movies : {i:}/{len(figures):}] {pname} \033[0m")
            #print(f"\033[1m\033[37m[MOVIES : ภาค {i}]\033[0m")
            #print(f"[No. : {i}/{len(figures)}] {pname}")
            #print(f"[MOVIES : ภาค {i}]")
            
            view_page = get_page_content(purl, sess, referer)
            if not view_page or "ขออภัย ไม่พบวิดีโอที่ต้องการ" in str(view_page.content):
                print(f"     Name  : {pname} [FAILED ❌]")
                continue
                
            soup = BeautifulSoup(view_page.content, "lxml")
            
            jseries['groups'].append({"name": display_name, "image": ppic, "info": pinfo, "stations": []})
            g1 = len(jseries['groups']) - 1
            
            is_series = 'title="ซีรี่ย์"' in str(soup) and 'ตอนที่ 2' in str(soup)
            
            if not is_series:  # หนัง
                player_div = soup.find("div", class_="movie-player")
                if not player_div:
                    print(f"     Name  : {pname} [FAILED ❌]")
                    continue
                
                player_iframe = player_div.find("iframe")
                player_iframe_url = player_iframe.get('data-src') or player_iframe.get('src') if player_iframe else None
                if not player_iframe_url:
                    print(f"     Name  : {pname} [FAILED ❌]")
                    continue
                
                elink = process_iframe(player_iframe_url, sess, referer)
                if not elink:
                    print(f"     Name  : {pname} [FAILED ❌]")
                    continue
                
                print(f"     \033[1m\033[37mName : {pname} [OK ✅]\033[0m")
                print(f"     \033[1m\033[37mPlaylist : {elink}\033[0m")
                #print(f"     Name  : {pname} [OK ✅]")
                #print(f"     Playlist : {elink}")
                
                station_data = {
                    "name": display_name,
                    "info": pinfo,
                    "image": ppic,
                    "url": elink,
                    "referer": referer
                }
                if pinfo == 'พากย์ไทย':
                    station_data["subtitle"] = "https://pastebin.com/raw/cuyErKD4"
                    
                jseries['groups'][g1]['stations'].append(station_data)
                
                if W_M3U:
                    try:
                        if M_f:
                            path = os.path.join(f_path, f_m3u)
                            with open(path, 'w', encoding='utf-8') as f:
                                f.write("#EXTM3U\n\n")
                            M_f = 0
                        
                        with open(os.path.join(f_path, f_m3u), 'a', encoding='utf-8') as f:
                            title = f'{display_name} {pinfo}'.strip() if pinfo else display_name
                            f.write(f'#EXTINF:-1 group-title="MOVIE : {fname}" tvg-logo="{ppic}" ,{title}\n')
                            f.write(f'#EXTVLCOPT:http-referer={referer}\n')
                            f.write(f'{elink}\n\n')
                    except Exception as e:
                        print(colored.red(f"Failed to write to .m3u file: {e}"))
                        continue
                
                save_checkpoint(jseries, num, i + 1)
            
            else:  # ซีรี่ย์
                div = soup.find(class_="mt-right").find(id="single-post")
                if not div:
                    print(f"     Name  : {pname} [FAILED ❌]")
                    continue
                    
                for i, link in enumerate(div.find_all('a'), start=1):
                    try:
                        purl = link['onclick'].split("'")[1] + "?web=49"
                        ppic = link.img['src']
                        ename = link.img['alt']
                        
                        if "ตอนที่" in ename:
                            ename = "ตอนที่" + ename.split('ตอนที่')[-1].strip()
                        elif "EP." in ename:
                            ename = "ตอนที่ " + ename.split('EP.')[-1].strip()
                        elif "EP" in ename:
                            ename = "ตอนที่" + ename.split('EP')[-1].strip()
                            
                        epinfo = ''
                        if 'ซับไทย' in ename:
                            epinfo = 'ซับไทย'
                            display_ename = ename.replace('ซับไทย', '').strip()
                        elif 'พากย์ไทย' in ename:
                            epinfo = 'พากย์ไทย'
                            display_ename = ename.replace('พากย์ไทย', '').strip()
                        else:
                            display_ename = ename
                        
                        print(f"     Name  : {ename} [EP {i}]")
                        
                        view_page = get_page_content(purl, sess, referer)
                        if not view_page:
                            print(f"     Name  : {ename} [FAILED ❌]")
                            continue
                            
                        soup_iframe = BeautifulSoup(view_page.content, "lxml")
                        elink = find_m3u8_link(soup_iframe, view_page, purl, 0)
                        if not elink:
                            print(f"     Name  : {ename} [FAILED ❌]")
                            continue
                            
                        print(f"     Name  : {ename} [OK ✅]")
                        print(f"     Playlist : {elink}")
                        
                        station_data = {
                            "name": display_ename,
                            "info": epinfo,
                            "image": ppic,
                            "url": elink,
                            "referer": referer
                        }
                        if epinfo == 'พากย์ไทย':
                            station_data["subtitle"] = "https://pastebin.com/raw/cuyErKD4"
                            
                        jseries['groups'][g1]['stations'].append(station_data)
                        
                        if W_M3U:
                            try:
                                if M_f:
                                    path = os.path.join(f_path, f_m3u)
                                    with open(path, 'w', encoding='utf-8') as f:
                                        f.write("#EXTM3U\n\n")
                                    M_f = 0
                                
                                with open(os.path.join(f_path, f_m3u), 'a', encoding='utf-8') as f:
                                    title = f'{display_ename} {epinfo}'.strip() if epinfo else display_ename
                                    f.write(f'#EXTINF:-1 group-title="MOVIE : {fname}" tvg-logo="{ppic}" ,{title}\n')
                                    f.write(f'#EXTVLCOPT:http-referer={referer}\n')
                                    f.write(f'{elink}\n\n')
                            except Exception as e:
                                print(colored.red(f"Failed to write to .m3u file: {e}"))
                                continue
                        
                        save_checkpoint(jseries, num, i + 1)
                    except Exception:
                        print(f"     Name  : {ename} [FAILED ❌]")
                        save_checkpoint(jseries, num, i)
                        continue
        
        except Exception:
            print(f"     Name  : {pname} [FAILED ❌]")
            save_checkpoint(jseries, num, i)
            continue

# เขียนไฟล์ W3U
if W_W3U:
    out = os.path.join(f_path, f_w3u)
    try:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(jseries, f, indent=1, ensure_ascii=False)
    except Exception:
        pass

# แสดงผลเมื่อจบและลบ checkpoint
if W_M3U:
    out = os.path.join(f_path, f_m3u)
    if os.path.exists(out):
        print(colored.green(f"The END ตำแหน่งไฟล์: {f_path}{f_m3u}"))
    else:
        print(colored.red(f"No .m3u file created at: {f_path}{f_m3u}"))

if os.path.exists(checkpoint_file):
    try:
        os.remove(checkpoint_file)
    except Exception:
        pass