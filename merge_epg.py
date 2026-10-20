import xml.etree.ElementTree as ET
import urllib.request
import gzip
from datetime import datetime, timezone, timedelta

# Bakı vaxtı: UTC+4
AZ_TZ = timezone(timedelta(hours=4))

# Hər XML linkinə uyğun M3U-dakı tvg-id xəritəsi
CHANNELS = [
    {"id": "azertv", "url": "https://azepg.ddns.net/aztv/15_days_archive__aztv_desc.xml"},
    {"id": "xazartv", "url": "https://azepg.ddns.net/aztv/15_days_archive__xezer_desc.xml"},
    {"id": "ictimaitele", "url": "https://azepg.ddns.net/aztv/15_days_archive__itv_desc.xml"},
    {"id": "bakutv", "url": "https://azepg.ddns.net/aztv/15_days_archive__bakutv_desc.xml"},
    {"id": "idmantele", "url": "https://azepg.ddns.net/aztv/15_days_archive__idman_desc.xml"},
    {"id": "arb", "url": "https://azepg.ddns.net/aztv/15_days_archive__arb_desc.xml"},
    {"id": "arbgunesh", "url": "https://azepg.ddns.net/aztv/15_days_archive__gunesh_desc.xml"},
    {"id": "medeniyyettele", "url": "https://azepg.ddns.net/aztv/15_days_archive__madaniyyet_desc.xml"},
    {"id": "space", "url": "https://azepg.ddns.net/aztv/15_days_archive__space_desc.xml"},
    {"id": "atv", "url": "https://azepg.ddns.net/aztv/15_days_archive__atv_desc.xml"},
    {"id": "biznestv", "url": "https://azepg.ddns.net/aztv/15_days_archive__biznestv_desc.xml"},
    {"id": "ntv", "url": "https://azepg.ddns.net/aztv/15_days_archive__nxtv_desc.xml"},
    {"id": "qafkaz", "url": "https://azepg.ddns.net/aztv/15_days_archive__qafkaz_desc.xml"},
    {"id": "eltv", "url": "https://azepg.ddns.net/aztv/15_days_archive__eltv_desc.xml"}
]

def format_xmltv_date(timestamp_str):
    """Unix timestamp-i XMLTV YYYYMMDDhhmmss +0400 formatına çevirir"""
    try:
        ts = int(timestamp_str)
        dt = datetime.fromtimestamp(ts, tz=AZ_TZ)
        return dt.strftime("%Y%m%d%H%M%S +0400")
    except (ValueError, TypeError):
        return timestamp_str

def main():
    root = ET.Element("tv")
    root.set("generator-info-name", "CustomAzEPG")

    headers = {'User-Agent': 'Mozilla/5.0'}

    for item in CHANNELS:
        ch_id = item["id"]
        url = item["url"]
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
                    content = gzip.decompress(content)

                sub_root = ET.fromstring(content)

                for element in sub_root:
                    if element.tag == "channel":
                        # id="1" əvəzinə M3U-dakı tvg-id-ni yazırıq
                        element.set("id", ch_id)
                        root.append(element)
                    elif element.tag == "programme":
                        # programme channel="1" əvəzinə tvg-id yazırıq
                        element.set("channel", ch_id)

                        # Unix Timestamp-i XMLTV standartına çeviririk
                        if "start" in element.attrib:
                            element.set("start", format_xmltv_date(element.get("start")))
                        if "stop" in element.attrib:
                            element.set("stop", format_xmltv_date(element.get("stop")))

                        root.append(element)

            print(f"Uğurla emal edildi: {ch_id}")
        except Exception as e:
            print(f"Xəta ({ch_id}): {e}")

    # XML faylı saxlayırıq
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)

    # .gz arxivini yaradırıq
    with open("epg.xml", "rb") as f_in, gzip.open("epg.xml.gz", "wb") as f_out:
        f_out.writelines(f_in)

if __name__ == "__main__":
    main()
