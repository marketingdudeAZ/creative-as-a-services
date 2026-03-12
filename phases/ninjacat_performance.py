"""Phase 3 — NinjaCat Performance Reports (Gmail IMAP).

Tier gating: Standard and Premium only. Starter skips.
Connects to Gmail, searches for most recent NinjaCat report by SFID.
Extracts PDF/CSV attachment, parses performance metrics.
"""

import csv
import email
import imaplib
import io
import logging
import tempfile
from email.header import decode_header

from config import GMAIL_USER, GMAIL_APP_PASSWORD, GMAIL_IMAP_HOST

logger = logging.getLogger(__name__)


def connect_imap() -> imaplib.IMAP4_SSL:
    """Connect and login to Gmail via IMAP."""
    mail = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    return mail


def search_ninjacat_report(mail: imaplib.IMAP4_SSL, sfid: str, ninjacat_id: str = None) -> bytes | None:
    """Search for most recent NinjaCat report matching SFID or NinjaCat System ID."""
    mail.select("INBOX")

    # Try SFID first
    search_terms = [sfid]
    if ninjacat_id:
        search_terms.append(ninjacat_id)

    for term in search_terms:
        status, data = mail.search(None, f'(FROM "ninjacat" SUBJECT "{term}")')
        if status == "OK" and data[0]:
            msg_ids = data[0].split()
            return msg_ids[-1]  # Most recent

        # Also try body search
        status, data = mail.search(None, f'(FROM "ninjacat" BODY "{term}")')
        if status == "OK" and data[0]:
            msg_ids = data[0].split()
            return msg_ids[-1]

    return None


def extract_attachment(mail: imaplib.IMAP4_SSL, msg_id: bytes) -> tuple[str, bytes] | None:
    """Extract the first PDF or CSV attachment from an email."""
    status, msg_data = mail.fetch(msg_id, "(RFC822)")
    if status != "OK":
        return None

    msg = email.message_from_bytes(msg_data[0][1])

    for part in msg.walk():
        content_disp = str(part.get("Content-Disposition", ""))
        if "attachment" not in content_disp:
            continue

        filename = part.get_filename()
        if filename:
            decoded_name, charset = decode_header(filename)[0]
            if isinstance(decoded_name, bytes):
                filename = decoded_name.decode(charset or "utf-8")

        if not filename:
            continue

        lower = filename.lower()
        if lower.endswith(".pdf") or lower.endswith(".csv"):
            return filename, part.get_payload(decode=True)

    return None


def parse_csv_report(content: bytes) -> dict:
    """Parse a NinjaCat CSV report into structured metrics."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    metrics = {
        "channel_performance": [],
        "total_impressions": 0,
        "total_leads": 0,
        "total_spend": 0,
    }

    for row in reader:
        channel = row.get("channel") or row.get("Channel") or row.get("source") or ""
        channel_data = {
            "channel": channel,
            "impressions": _safe_int(row.get("impressions") or row.get("Impressions")),
            "clicks": _safe_int(row.get("clicks") or row.get("Clicks")),
            "leads": _safe_int(row.get("leads") or row.get("Leads") or row.get("conversions")),
            "spend": _safe_float(row.get("spend") or row.get("Spend") or row.get("cost")),
            "ctr": _safe_float(row.get("ctr") or row.get("CTR")),
            "cpl": _safe_float(row.get("cpl") or row.get("CPL") or row.get("cost_per_lead")),
            "cpm": _safe_float(row.get("cpm") or row.get("CPM")),
        }
        metrics["channel_performance"].append(channel_data)
        metrics["total_impressions"] += channel_data["impressions"]
        metrics["total_leads"] += channel_data["leads"]
        metrics["total_spend"] += channel_data["spend"]

    # Compute aggregate CPL and CPM
    if metrics["total_leads"] > 0:
        metrics["aggregate_cpl"] = round(metrics["total_spend"] / metrics["total_leads"], 2)
    if metrics["total_impressions"] > 0:
        metrics["aggregate_cpm"] = round((metrics["total_spend"] / metrics["total_impressions"]) * 1000, 2)

    return metrics


def parse_pdf_report(content: bytes) -> dict:
    """Parse a NinjaCat PDF report using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed — cannot parse PDF reports")
        return {}

    metrics = {
        "channel_performance": [],
        "total_impressions": 0,
        "total_leads": 0,
        "total_spend": 0,
        "raw_text": "",
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()

        with pdfplumber.open(tmp.name) as pdf:
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

                # Try extracting tables
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    headers = [str(h).lower().strip() for h in table[0] if h]
                    for row in table[1:]:
                        if len(row) != len(table[0]):
                            continue
                        row_dict = dict(zip(headers, row))
                        channel_data = {
                            "channel": row_dict.get("channel", ""),
                            "impressions": _safe_int(row_dict.get("impressions")),
                            "clicks": _safe_int(row_dict.get("clicks")),
                            "leads": _safe_int(row_dict.get("leads") or row_dict.get("conversions")),
                            "spend": _safe_float(row_dict.get("spend") or row_dict.get("cost")),
                            "ctr": _safe_float(row_dict.get("ctr")),
                            "cpl": _safe_float(row_dict.get("cpl") or row_dict.get("cost_per_lead")),
                            "cpm": _safe_float(row_dict.get("cpm")),
                        }
                        if channel_data["channel"]:
                            metrics["channel_performance"].append(channel_data)
                            metrics["total_impressions"] += channel_data["impressions"]
                            metrics["total_leads"] += channel_data["leads"]
                            metrics["total_spend"] += channel_data["spend"]

            metrics["raw_text"] = "\n".join(all_text)

    if metrics["total_leads"] > 0:
        metrics["aggregate_cpl"] = round(metrics["total_spend"] / metrics["total_leads"], 2)
    if metrics["total_impressions"] > 0:
        metrics["aggregate_cpm"] = round((metrics["total_spend"] / metrics["total_impressions"]) * 1000, 2)

    return metrics


def _safe_int(val) -> int:
    if val is None:
        return 0
    try:
        return int(str(val).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return 0


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("$", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return 0.0


def run(property_data: dict) -> dict | None:
    """Execute Phase 3 for a single property."""
    tier = (property_data.get("video_creative_package_tier") or "").strip()
    if tier not in ("Standard", "Premium"):
        logger.info("Skipping NinjaCat for %s (tier: %s)", property_data.get("name"), tier)
        return None

    sfid = property_data.get("sfid", "")
    ninjacat_id = property_data.get("ninjacat_system_id", "")

    if not sfid and not ninjacat_id:
        logger.warning("No SFID or NinjaCat ID for %s — skipping", property_data.get("name"))
        return None

    try:
        mail = connect_imap()
        msg_id = search_ninjacat_report(mail, sfid, ninjacat_id)

        if not msg_id:
            logger.warning("No NinjaCat report found for %s (SFID: %s)", property_data.get("name"), sfid)
            mail.logout()
            return None

        attachment = extract_attachment(mail, msg_id)
        mail.logout()

        if not attachment:
            logger.warning("No PDF/CSV attachment in NinjaCat email for %s", property_data.get("name"))
            return None

        filename, content = attachment
        logger.info("Found NinjaCat report: %s for %s", filename, property_data.get("name"))

        if filename.lower().endswith(".csv"):
            metrics = parse_csv_report(content)
        elif filename.lower().endswith(".pdf"):
            metrics = parse_pdf_report(content)
        else:
            logger.warning("Unsupported attachment format: %s", filename)
            return None

        return metrics

    except Exception as e:
        logger.error("NinjaCat pull failed for %s: %s", property_data.get("name"), e)
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_property = {
        "name": "Test Property",
        "sfid": "SF001",
        "video_creative_package_tier": "Standard",
    }
    result = run(test_property)
    print(f"Performance context: {result}")
