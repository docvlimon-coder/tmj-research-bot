# coding: utf-8
import os
import textwrap
import requests

TOPIC_QUERY = (
    '(temporomandibular disorders[Title/Abstract] OR TMJ[Title/Abstract] OR '
    'temporomandibular joint[Title/Abstract] OR "splint therapy"[Title/Abstract] OR '
    '"stabilization splint"[Title/Abstract] OR "Michigan splint"[Title/Abstract] OR '
    'occlusal splint[Title/Abstract])'
)

PUBMED_QUERY = (
    f'({TOPIC_QUERY}) AND '
    f'(("randomized controlled trial"[Publication Type]) OR '
    f'("systematic review"[Publication Type]) OR '
    f'("meta-analysis"[Publication Type])) AND '
    f'(humans[MeSH Terms]) AND ("last 7 days"[PDat])'
)

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def pubmed_search(max_n: int = 10) -> list[str]:
    r = requests.get(
        ESEARCH,
        params={
            "db": "pubmed",
            "term": PUBMED_QUERY,
            "retmode": "json",
            "retmax": str(max_n),
            "sort": "pub date",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["esearchresult"].get("idlist", [])

def pubmed_fetch_xml(pmids: list[str]) -> str:
    if not pmids:
        return ""
    r = requests.get(
        EFETCH,
        params={"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        timeout=30,
    )
    r.raise_for_status()
    return r.text

def extract_titles(xml: str) -> list[tuple[str, str]]:
    items = []
    parts = xml.split("<PubmedArticle>")
    for p in parts[1:]:
        if "<PMID" not in p or "<ArticleTitle>" not in p:
            continue
        pmid = p.split("<PMID", 1)[1].split(">", 1)[1].split("</PMID>", 1)[0].strip()
        title = p.split("<ArticleTitle>", 1)[1].split("</ArticleTitle>", 1)[0]
        title = title.replace("\n", " ").strip()
        items.append((pmid, title))
    return items

def send_telegram(text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for chunk in textwrap.wrap(text, width=3500, break_long_words=False):
        r = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        r.raise_for_status()

def main() -> None:
    pmids = pubmed_search(max_n=10)
    if not pmids:
        send_telegram("За последние 7 дней новых РКИ/обзоров по теме ВНЧС/сплинтов не найдено.")
        return

    xml = pubmed_fetch_xml(pmids)
    items = extract_titles(xml)

    msg = "🧠 Новые статьи за неделю (ВНЧС / сплинты)\n\n"
    for i, (pmid, title) in enumerate(items, 1):
        msg += f"{i}) {title}\nhttps://pubmed.ncbi.nlm.nih.gov/{pmid}/\n\n"

    send_telegram(msg)

if __name__ == "__main__":
    main()
