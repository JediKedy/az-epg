import xml.etree.ElementTree as ET
import gzip
import json
import re
import requests
import time
from datetime import datetime, timezone, timedelta

# Bakı vaxtı: UTC+4
AZ_TZ = timezone(timedelta(hours=4))

# ==========================================
# YALNIZ EPG-SİNİ ÇƏKMƏK İSTƏDİYİNİZ KANALLAR
# (M3U faylınızdakı tvg-id adları ilə eyni olmalıdır)
# Əgər bütün kanalları çəkmək istəsəniz, içi boş saxlayın: WANTED_CHANNELS = []
# ==========================================
WANTED_CHANNELS = [
    "TRT1.tr",
    "ATV.tr",
    "A2.tr",
    "NOW.tr",
    "STARTV.tr",
    "SHOWTV.tr",
    "KANALD.tr",
    "TV8.tr",
    "TV85.tr",
    "BEYAZTV.tr",
    "KANAL7.tr",
    "TV2.tr",
    "360.tr",
    "TV4.tr",
    "DMAX.tr",
    "TLC.tr",
    "TRTBELGESEL.tr",
    "TRTCOCUK.tr",
    "TRTWorld.tr",
    "TRTTURK.tr",
    "TRTMUZIK.tr",
    "TRTSPOR.tr",
    "CARTOONNETWORK.tr",
    "MINIKAGO.tr",
    "CNNTURK.tr",
    "NTV.tr",
    "HABERTURK.tr",
    "AHABER.tr",
    "TV100.tr",
    "ASPOR.tr"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
}

def extract_json_array(text, key):
    """HTML içərisindən istənilən JSON massivini qoparan funksiya"""
    pattern = f'"{key}"\\s*:\\s*\\['
    match = re.search(pattern, text)
    if not match:
        return []
    
    start_idx = match.end() - 1
    bracket_count = 0
    in_string = False
    escape = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
        elif char == '"':
            in_string = not in_string
        elif not in_string:
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    json_str = text[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        print(f"JSON Parse xətası: {e}")
                        return []
    return []

def format_xmltv_date(timestamp_str):
    try:
        ts = float(timestamp_str)
        if ts > 10000000000:
            ts = ts / 1000
        dt = datetime.fromtimestamp(ts, tz=AZ_TZ)
        return dt.strftime("%Y%m%d%H%M%S +0400")
    except (ValueError, TypeError):
        return str(timestamp_str)

def normalize_tr_id(name):
    clean = name.replace(" ", "").replace("HD", "").replace("hd", "").strip()
    char_map = str.maketrans("üöşıçğÜÖŞİÇĞ", "uosicgUOSICG")
    clean = clean.translate(char_map)
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean)
    return f"{clean}.tr"

def normalize_slug(name):
    slug = name.lower().replace(" ", "-").strip()
    char_map = str.maketrans("üöşıçğ", "uosicg")
    slug = slug.translate(char_map)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def main():
    root = ET.Element("tv", {"generator-info-name": "TVPlus_TR_EPG"})
    print(f"[TR] TV+ məlumatları çəkilir... (Hədəf: {len(WANTED_CHANNELS)} kanal)")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        url = "https://tvplus.com.tr/canli-tv/yayin-akisi"
        res = session.get(url, timeout=20)
        res.raise_for_status()

        clean_text = res.text.replace('\\"', '"').replace('\\\\', '\\')
        channels = extract_json_array(clean_text, "channelData")

        if not channels:
            print("[TR] HEC BIR KANAL TAPILMADI!")
            return

        added_count = 0
        for ch in channels:
            ch_name = ch.get("name", "").strip()
            ch_num = ch.get("id")
            
            if not ch_name or not ch_num: 
                continue
            
            tr_id = normalize_tr_id(ch_name)
            
            # KANAL FİLTRİ: Əgər siyahıda yoxdursa, NÖVBƏTİ KANALA KEÇ (SKIP)
            if len(WANTED_CHANNELS) > 0 and tr_id not in WANTED_CHANNELS:
                continue
                
            slug = normalize_slug(ch_name)
            
            channel_el = ET.SubElement(root, "channel", id=tr_id)
            ET.SubElement(channel_el, "display-name").text = ch_name
            if ch.get("picture"):
                ET.SubElement(channel_el, "icon", src=ch.get("picture"))
                
            channel_url = f"https://tvplus.com.tr/canli-tv/yayin-akisi/{slug}--{ch_num}"
            try:
                time.sleep(0.1)
                epg_res = session.get(channel_url, timeout=10)
                if epg_res.status_code == 200:
                    clean_epg_text = epg_res.text.replace('\\"', '"').replace('\\\\', '\\')
                    playbills = extract_json_array(clean_epg_text, "playbills")
                    
                    if playbills and isinstance(playbills, list) and isinstance(playbills[0], list):
                        playbills = [item for sublist in playbills for item in sublist]
                        
                    for prog in playbills:
                        start_ts = prog.get("starttime")
                        end_ts = prog.get("endtime")
                        title = prog.get("name", "")
                        
                        if not start_ts or not title: continue
                        
                        start_xml = format_xmltv_date(start_ts)
                        end_xml = format_xmltv_date(end_ts) if end_ts else start_xml
                        
                        prog_el = ET.SubElement(root, "programme", channel=tr_id, start=start_xml, stop=end_xml)
                        ET.SubElement(prog_el, "title", lang="tr").text = title
                        
                        desc = prog.get("introduce") or prog.get("description")
                        if desc:
                            ET.SubElement(prog_el, "desc", lang="tr").text = desc
                            
                        category = prog.get("genres")
                        if category:
                            ET.SubElement(prog_el, "category", lang="tr").text = category
                    
                    print(f"[+] Uğurla çəkildi: {ch_name} ({tr_id})")
                    added_count += 1
            except Exception as e:
                print(f"[-] {ch_name} xəta: {e}")
                
        print(f"[TR] Bitti! {added_count} kanalın EPG-si yığıldı.")

    except Exception as e:
        print(f"[TR] Ümumi Xəta: {e}")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write("epg_tr.xml", encoding="utf-8", xml_declaration=True)

    with open("epg_tr.xml", "rb") as f_in, gzip.open("epg_tr.xml.gz", "wb") as f_out:
        f_out.writelines(f_in)

if __name__ == "__main__":
    main()
