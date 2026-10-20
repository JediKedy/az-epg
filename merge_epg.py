import xml.etree.ElementTree as ET
import urllib.request
import gzip

# Mənbə XML linkləri
EPG_URLS = [
    "https://azepg.ddns.net/aztv/15_days_archive__aztv_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__xezer_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__itv_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__bakutv_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__idman_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__arb_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__gunesh_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__madaniyyet_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__space_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__atv_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__biznestv_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__nxtv_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__qafkaz_desc.xml",
    "https://azepg.ddns.net/aztv/15_days_archive__eltv_desc.xml"
]

def main():
    root = ET.Element("tv")
    root.set("generator-info-name", "CustomAzEPG")

    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in EPG_URLS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                # Gzip sıxılmış olarsa açırıq
                if url.endswith('.gz') or content[:2] == b'\x1f\x8b':
                    content = gzip.decompress(content)
                
                sub_root = ET.fromstring(content)
                for element in sub_root:
                    if element.tag in ("channel", "programme"):
                        root.append(element)
            print(f"Uğurla çəkildi: {url}")
        except Exception as e:
            print(f"Xəta baş verdi ({url}): {e}")

    # Birləşmiş faylı saxlayırıq
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    
    # Həcmi kiçiltmək üçün .gz variantını da yaradırıq (IPTV pleyerlər üçün daha sürətlidir)
    with open("epg.xml", "rb") as f_in, gzip.open("epg.xml.gz", "wb") as f_out:
        f_out.writelines(f_in)

if __name__ == "__main__":
    main()
