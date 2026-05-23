from __future__ import annotations

import fitz  # PyMuPDF
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

DOCUMENTS = {
    "it_act.pdf": [
        "The Information Technology Act, 2000 (Act No. 21 of 2000).",
        "Section 43: Penalty and compensation for damage to computer, computer system, etc. If any person, without permission of the owner or any other person who is incharge of a computer, computer system or computer network, accesses, downloads, copies or extracts any data, or introduces any computer contaminant or virus, he shall be liable to pay damages by way of compensation to the person so affected.",
        "Section 43A: Compensation for failure to protect data. Where a body corporate, possessing, dealing or handling any sensitive personal data or information in a computer resource which it owns, controls or operates, is negligent in implementing and maintaining reasonable security practices and procedures and thereby causes wrongful loss or wrongful gain to any person, such body corporate shall be liable to pay damages by way of compensation to the person so affected.",
        "Section 66A: Punishment for sending offensive messages through communication service. Any person who sends, by means of a computer resource or a communication device, any information that is grossly offensive or has menacing character, or any information which he knows to be false, but for the purpose of causing annoyance, inconvenience, danger, obstruction, insult, injury, criminal intimidation, enmity, hatred or ill will, persistently by making use of such computer resource or a communication device, shall be punishable with imprisonment for a term which may extend to three years and with fine."
    ],
    "constitution.pdf": [
        "The Constitution of India.",
        "Article 19: Protection of certain rights regarding freedom of speech, etc. (1) All citizens shall have the right (a) to freedom of speech and expression; (b) to assemble peaceably and without arms; (c) to form associations or unions or co-operative societies; (d) to move freely throughout the territory of India; (e) to reside and settle in any part of the territory of India.",
        "Article 21: Protection of life and personal liberty. No person shall be deprived of his life or personal liberty except according to procedure established by law. The right to life includes the right to privacy as a fundamental right under Article 21, protecting personal autonomy and data protection."
    ],
    "dpdp.pdf": [
        "The Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023).",
        "Section 2(t): Definition of personal data. 'personal data' means any data about an individual who is identifiable by or in relation to such data.",
        "Section 6: Consent. (1) Consent given by the Data Principal shall be free, specific, informed, unconditional and unambiguous with a clear affirmative action, signifying agreement to the processing of her personal data for the specified purpose and be limited to such personal data as is necessary for such specified purpose.",
        "Section 8: General obligations of Data Fiduciary. (1) A Data Fiduciary shall be responsible for complying with the provisions of this Act in respect of any processing of digital personal data undertaken by it or on its behalf. (5) A Data Fiduciary shall protect personal data in its possession or under its control by taking reasonable security safeguards to prevent personal data breach."
    ]
}

def generate_pdf(filename: str, pages: list[str], output_dir: Path) -> None:
    dest = output_dir / filename
    logger.info(f"Generating {filename} with {len(pages)} pages at {dest}...")
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        # Use insert_textbox with a standard Rect to automatically wrap long paragraphs
        # A4/Letter size is roughly 612x792, so standard margins of 54pt (0.75 inch) work perfectly
        rect = fitz.Rect(54, 54, 558, 738)
        page.insert_textbox(rect, text, fontsize=11)
    doc.save(dest)
    doc.close()
    logger.info(f"Saved {filename} successfully.")

def main() -> None:
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    for filename, pages in DOCUMENTS.items():
        generate_pdf(filename, pages, raw_dir)
        
    print("\nSample legal documents successfully generated in data/raw/")

if __name__ == "__main__":
    main()
