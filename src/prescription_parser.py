import re
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from src.gliner_ner import extract_entities  # GLiNER wrapper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PrescriptionParser:
    def __init__(self):
        """Initialize prescription parser with medical keywords and regex patterns"""
        self.medication_patterns = [
            r'(?i)(?:tablet|tab|capsule|syrup|injection|inj|drops|cream|ointment)\s+(\w+)',
            r'(?i)(\w+)\s*\d+\s*(?:mg|g|ml|iu)',
            r'(?i)(?:take|consume|apply)\s+(\w+)',
        ]

        self.dosage_patterns = [
            r'(?i)(\d+)\s*(?:mg|g|ml|iu)',
            r'(?i)(?:once|twice|thrice|three times)\s+(?:daily|a day)',
            r'(?i)(?:bd|tid|qid|od|hs|prn)',
        ]

        self.frequency_patterns = [
            r'(?i)(?:once|twice|thrice|three times)\s+(?:daily|a day|per day)',
            r'(?i)(?:every|q)\s*(\d+)\s*(?:hour|hr|h)',
            r'(?i)(?:bd|bid|twice daily)',
            r'(?i)(?:tid|three times daily)',
            r'(?i)(?:qid|four times daily)',
            r'(?i)(?:od|once daily)',
            r'(?i)(?:hs|at bedtime)',
            r'(?i)(?:prn|as needed)',
        ]

        self.duration_patterns = [
            r'(?i)for\s+(\d+)\s*(?:day|days|week|weeks|month|months)',
            r'(?i)(?:day|week|month)s?\s*(\d+)',
        ]

        self.doctor_patterns = [
            r'(?i)(?:dr|doctor|physician)[:.]\s*([a-zA-Z\s]+)',
            r'(?i)(?:prescribed by|written by)[:.]\s*([a-zA-Z\s]+)',
        ]

        self.date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}',
            r'(?:january|february|march|april|may|june|july|august|september|october|november)\s+\d{1,2},?\s+\d{2,4}',
        ]

        self.ner_labels = [
            "Drug", "Strength", "Dosage", "Frequency", "Duration",
            "Route", "Form", "Patient", "Doctor", "Date", "Age"
        ]

    def parse_prescription(self, extracted_text: Dict) -> Dict:
        try:
            if 'error' in extracted_text:
                return extracted_text

            full_text = extracted_text.get('full_text', '')
            lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

            # GLiNER NER
            ner_dict = self.extract_entities(lines)

            # Build prescription data
            prescription_data = {
                'raw_text': full_text,
                'ner': ner_dict,
                'medications': self._extract_medications(full_text),
                'dosages': self._extract_dosages(full_text),
                'frequencies': self._extract_frequencies(full_text),
                'durations': self._extract_durations(full_text),
                'doctor_name': self._extract_doctor_name(full_text),
                'prescription_date': self._extract_date(full_text),
                'patient_info': self._extract_patient_info(full_text),
                'parsed_at': datetime.utcnow().isoformat(),
            }

            if 'confidence' in extracted_text:
                prescription_data['confidence_score'] = extracted_text['confidence']

            logger.info("Successfully parsed prescription data")
            return prescription_data

        except Exception as e:
            logger.error(f"Error parsing prescription: {str(e)}")
            return {"error": f"Parsing failed: {str(e)}"}

    # GLiNER NER
    def extract_entities(self, lines: List[str]) -> Dict[str, List[Dict]]:
        text = "\n".join(lines)
        return extract_entities(text, self.ner_labels)

    # Regex helpers
    def _extract_medications(self, text: str) -> List[Dict]:
        meds = []
        for pattern in self.medication_patterns:
            for m in re.finditer(pattern, text):
                meds.append({'name': m.group(1).strip(), 'position': m.start(), 'confidence': 0.8})
        return list({med['name'].lower(): med for med in meds}.values())

    def _extract_dosages(self, text: str) -> List[Dict]:
        return [{'value': m.group(0), 'position': m.start(), 'confidence': 0.8}
                for p in self.dosage_patterns for m in re.finditer(p, text)]

    def _extract_frequencies(self, text: str) -> List[Dict]:
        return [{'value': m.group(0), 'position': m.start(), 'confidence': 0.8}
                for p in self.frequency_patterns for m in re.finditer(p, text)]

    def _extract_durations(self, text: str) -> List[Dict]:
        return [{'value': m.group(0), 'position': m.start(), 'confidence': 0.8}
                for p in self.duration_patterns for m in re.finditer(p, text)]

    def _extract_doctor_name(self, text: str) -> Optional[str]:
        for p in self.doctor_patterns:
            match = re.search(p, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        for p in self.date_patterns:
            match = re.search(p, text)
            if match:
                return match.group(0)
        return None

    def _extract_patient_info(self, text: str) -> Dict:
        info = {'name': None, 'age': None, 'gender': None}

        # Name
        match = re.search(r'(?i)(?:patient|pt|name)[:.\s]+([a-zA-Z\s]+)', text)
        if match:
            info['name'] = match.group(1).strip()

        # Age
        match = re.search(r'(?i)age[:.\s]+(\d+)', text)
        if match:
            info['age'] = int(match.group(1))

        # Gender
        match = re.search(r'(?i)\b(m|f|male|female)\b', text)
        if match:
            g = match.group(1).lower()
            if g in ['m', 'male']:
                info['gender'] = 'male'
            elif g in ['f', 'female']:
                info['gender'] = 'female'

        return info
