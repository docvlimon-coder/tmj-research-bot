import os, textwrap
import requests

TOPIC_QUERY = (
    '(temporomandibular disorders[Title/Abstract] OR TMJ[Title/Abstract] OR '
    'temporomandibular joint[Title/Abstract] OR "splint therapy"[Title/Abstract] OR '
    '"stabilization splint"[Title/Abstract] OR "Michigan splint"[Title/Abstract] OR '
    'occlusal splint[Title/Abstract])'
)

PUBMED_QUERY = f'({TOPIC_QUERY}) AND (("randomized controlled trial"[Publication Type]) ' \
               f'OR ("systematic review"[Publication Type]) OR ("meta-analysis"[Publication Type])) ' \
               f'AND (humans[MeSH Terms]) AND ("last 7 days"[PDat])'

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def pubmed_search(max_n=10):
    r = requests.get(ESEARCH, params={
        "db": "pubmed",
        "term": PUBMED_QUERY,
        "retmode": "json",
        "retmax": str(max_n),
        "sort": "pub date",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["esearchresult"].get("idlist", [])

def pubmed_fetch(pmids):
    if not pmids:
        return ""
    r = requests.get(EFETCH, params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }, timeout=30)
    r.raise_for_status()
    return r.text

def extract_titles(xml):
    items = []
    parts = xml.split("<PubmedArticle>")
    for p in parts[1:]:
        if "<PMID" not in p or "<ArticleTitle>" not in p:
            continue
        pmid = p.split("<PMID",1)[1].split(">",1)[1].split("</PMID>",1)[0]
        title = p.split("<ArticleTitle>",1)[1].split("</ArticleTitle>",1)[0]
        items.append((pmid.strip(), title.replace("\n"," ").strip()))
    return items

def send_telegram(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in textwrap.wrap(text, 3500):
        requests.post(url, json={
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": True
        }, timeout=30)

def main():
    pmids = pubmed_search()
    if not pmids:
        send_telegram("За последние 7 дней новых РКИ/обзоров по теме не найдено.")
        return
    xml = pubmed_fetch(pmids)
    items = extract_titles(xml)

    msg = "🧠 Новые статьи за неделю (ВНЧС / сплинты)\n\n"
    for i, (pmid, title) in enumerate(items, 1):
        msg += f"{i}) {title}\nhttps://pubmed.ncbi.nlm.nih.gov/{pmid}/\n\n"

    send_telegram(msg)

if __name__ == "__main__":
    main()
