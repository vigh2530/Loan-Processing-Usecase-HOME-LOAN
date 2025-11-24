# services/autofill_service.py - Enhanced version

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AutoFillService:
    def __init__(self):
        self.field_mappings = {
            'first_name': ['first name', 'firstname', 'fname', 'given name'],
            'last_name': ['last name', 'lastname', 'lname', 'surname', 'family name'],
            'gender': ['gender', 'sex'],
            'email': ['email', 'email address', 'email id'],
            'aadhaar': ['aadhaar', 'aadhaar number', 'aadhar', 'aadhar number', 'uid'],
            'pan': ['pan', 'pan number', 'pan card', 'permanent account number'],
            'address': ['address', 'residential address', 'current address', 'home address', 'current residential address'],
            'residence_status': ['residence status', 'residency status', 'living status', 'current residence status'],
            'other_properties': ['other properties', 'own other properties', 'additional properties', 'do you own any other properties'],
            'salary': ['salary', 'monthly salary', 'income', 'monthly income', 'earnings', 'monthly salary (inr)'],
            'company': ['company', 'company name', 'employer', 'organization', 'employer name'],
            'existing_loan': ['existing loan', 'current loan', 'loan amount', 'existing emi', 'current emi', 'existing emi (if any, inr)'],
            'cibil': ['cibil', 'cibil score', 'credit score', 'credit rating'],
            'loan_amount': ['loan amount required', 'requested loan', 'loan needed', 'required amount', 'loan amount requested (inr)'],
            'property_value': ['property valuation', 'property value', 'property worth', 'property valuation (INRS)'],
            'property_address': ['property address', 'loan property address', 'collateral address', 'full property address (for loan)'],
            'non_agricultural': ['non agricultural', 'property type', 'agricultural', 'is the property non-agricultural'],
            'mortgage': ['mortgage', 'existing mortgage', 'current mortgage', 'is there an existing mortgage on this property']
        }
    
    def parse_text_data(self, content: str) -> Dict[str, Any]:
        """Parse text content and extract structured data"""
        data = {}
        lines = content.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
                
            # Skip section headers
            if any(header in line.lower() for header in ['applicant details', 'financial', 'property', 'loan details']):
                continue
                
            # Try different separators: colon, dash, pipe, equals
            separators = [':', '-', '|', '=']
            found_separator = None
            separator_index = -1
            
            for sep in separators:
                idx = line.find(sep)
                if idx != -1:
                    found_separator = sep
                    separator_index = idx
                    break
            
            if found_separator is None:
                continue
                
            key = line[:separator_index].strip().lower()
            value = line[separator_index + 1:].strip()
            
            # Map to standard field names
            field_name = self._map_field_name(key)
            if field_name:
                data[field_name] = self._clean_value(field_name, value)
        
        logger.info(f"Parsed {len(data)} fields from text data: {list(data.keys())}")
        return data
    
    def _map_field_name(self, key: str) -> str:
        """Map various key formats to standard field names"""
        # Remove common prefixes/suffixes and clean the key
        key = re.sub(r'[^a-zA-Z0-9\s]', '', key).strip()
        
        for field_name, variations in self.field_mappings.items():
            for variation in variations:
                # Exact match or contains match
                if key == variation or variation in key:
                    return field_name
        
        return ""
    
    def _clean_value(self, field_name: str, value: str) -> Any:
        """Clean and convert values based on field type"""
        if field_name in ['salary', 'existing_loan', 'loan_amount', 'property_value']:
            return self._extract_number(value)
        elif field_name == 'cibil':
            return int(self._extract_number(value)) if self._extract_number(value) else None
        elif field_name in ['other_properties', 'non_agricultural', 'mortgage']:
            # Handle various yes/no formats
            value_lower = value.lower()
            if any(word in value_lower for word in ['yes', 'true', '1', 'y', 'have', 'own']):
                return True
            elif any(word in value_lower for word in ['no', 'false', '0', 'n', 'none', "don't"]):
                return False
            return None
        elif field_name == 'residence_status':
            value_lower = value.lower()
            if 'rent' in value_lower:
                return 'Rent'
            elif 'own' in value_lower:
                return 'Owned'
            return value
        elif field_name == 'gender':
            value_lower = value.lower()
            if 'male' in value_lower or 'm' in value_lower:
                return 'Male'
            elif 'female' in value_lower or 'f' in value_lower:
                return 'Female'
            return value
        else:
            return value
    
    def _extract_number(self, text: str) -> float:
        """Extract numeric value from text"""
        # Remove currency symbols, commas, and other non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', text)
        return float(cleaned) if cleaned else 0.0