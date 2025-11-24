import re
import json
from datetime import datetime
import requests
from flask import current_app

class AnomalyDetector:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def detect_document_anomalies(self, extracted_content, document_type, application_data):
        """Detect anomalies in document content"""
        try:
            anomalies = []
            
            # Basic content validation
            basic_anomalies = self._basic_content_checks(extracted_content, document_type)
            anomalies.extend(basic_anomalies)
            
            # Pattern-based anomaly detection
            pattern_anomalies = self._pattern_based_detection(extracted_content, document_type)
            anomalies.extend(pattern_anomalies)
            
            # Consistency checks with application data
            consistency_anomalies = self._consistency_checks(extracted_content, application_data, document_type)
            anomalies.extend(consistency_anomalies)
            
            # AI-powered anomaly detection
            ai_anomalies = self._ai_anomaly_detection(extracted_content, document_type, application_data)
            anomalies.extend(ai_anomalies)
            
            # Calculate anomaly score
            anomaly_score = self._calculate_anomaly_score(anomalies)
            
            return {
                'anomalies': anomalies,
                'anomaly_score': anomaly_score,
                'risk_level': self._determine_risk_level(anomaly_score),
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            current_app.logger.error(f"Anomaly detection error: {str(e)}")
            return {
                'anomalies': [{'type': 'SYSTEM_ERROR', 'description': f'Anomaly detection failed: {str(e)}', 'severity': 'MEDIUM'}],
                'anomaly_score': 50,
                'risk_level': 'MEDIUM',
                'timestamp': datetime.utcnow()
            }
    
    def _basic_content_checks(self, content, doc_type):
        """Perform basic content validation checks"""
        anomalies = []
        
        if not content or len(content.strip()) < 10:
            anomalies.append({
                'type': 'EMPTY_CONTENT',
                'description': 'Document appears to be empty or has very little content',
                'severity': 'HIGH'
            })
            return anomalies
        
        # Check for gibberish text (repeated characters, random strings)
        if self._is_gibberish(content):
            anomalies.append({
                'type': 'GIBBERISH_TEXT',
                'description': 'Document contains nonsensical or garbled text',
                'severity': 'HIGH'
            })
        
        # Check for duplicate lines (potential template issues)
        duplicate_anomalies = self._check_duplicate_content(content)
        anomalies.extend(duplicate_anomalies)
        
        # Check for suspicious patterns
        suspicious_patterns = self._detect_suspicious_patterns(content)
        anomalies.extend(suspicious_patterns)
        
        return anomalies
    
    def _is_gibberish(self, text):
        """Detect gibberish text patterns"""
        # Check for repeated characters (e.g., "aaaaaa", "xxxxx")
        if re.search(r'(.)\1{5,}', text):
            return True
        
        # Check for random character sequences without spaces
        if re.search(r'[a-zA-Z]{20,}', text):  # Very long words
            return True
            
        # Check for lack of meaningful words
        words = text.split()
        meaningful_words = [w for w in words if len(w) > 2 and w.isalpha()]
        if len(meaningful_words) < len(words) * 0.3:  # Less than 30% meaningful words
            return True
            
        return False
    
    def _check_duplicate_content(self, content):
        """Check for duplicate lines or sections"""
        anomalies = []
        lines = content.split('\n')
        line_counts = {}
        
        for line in lines:
            clean_line = line.strip()
            if len(clean_line) > 20:  # Only check substantial lines
                line_counts[clean_line] = line_counts.get(clean_line, 0) + 1
        
        duplicate_lines = [line for line, count in line_counts.items() if count > 2]
        if duplicate_lines:
            anomalies.append({
                'type': 'DUPLICATE_CONTENT',
                'description': f'Found {len(duplicate_lines)} lines repeated multiple times',
                'severity': 'MEDIUM',
                'details': duplicate_lines[:3]  # Show first 3 duplicates
            })
        
        return anomalies
    
    def _detect_suspicious_patterns(self, content):
        """Detect suspicious patterns in document content"""
        anomalies = []
        
        # Check for placeholder text
        placeholders = ['lorem ipsum', 'sample text', 'enter text here', 'xxx', '---']
        for placeholder in placeholders:
            if placeholder in content.lower():
                anomalies.append({
                    'type': 'PLACEHOLDER_TEXT',
                    'description': f'Found placeholder text: "{placeholder}"',
                    'severity': 'HIGH'
                })
        
        # Check for inconsistent formatting
        if self._has_inconsistent_formatting(content):
            anomalies.append({
                'type': 'INCONSISTENT_FORMATTING',
                'description': 'Document has inconsistent formatting or styling',
                'severity': 'MEDIUM'
            })
        
        # Check for suspicious date patterns
        date_anomalies = self._check_date_anomalies(content)
        anomalies.extend(date_anomalies)
        
        # Check for amount inconsistencies
        amount_anomalies = self._check_amount_anomalies(content)
        anomalies.extend(amount_anomalies)
        
        return anomalies
    
    def _has_inconsistent_formatting(self, content):
        """Check for inconsistent text formatting"""
        lines = content.split('\n')
        
        # Check for mixed case patterns
        upper_case_lines = sum(1 for line in lines if line.isupper())
        lower_case_lines = sum(1 for line in lines if line.islower())
        
        if upper_case_lines > 0 and lower_case_lines > 0:
            return True
        
        # Check for inconsistent spacing
        if re.search(r'[a-zA-Z]{2,}\s{2,}[a-zA-Z]{2,}', content):
            return True
            
        return False
    
    def _check_date_anomalies(self, content):
        """Check for date-related anomalies"""
        anomalies = []
        
        # Find all dates in the document
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # DD-MM-YYYY, MM/DD/YYYY
            r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]
        
        all_dates = []
        for pattern in date_patterns:
            dates = re.findall(pattern, content, re.IGNORECASE)
            all_dates.extend(dates)
        
        # Check for future dates
        current_year = datetime.now().year
        for date_str in all_dates:
            try:
                # Simple year extraction
                year_matches = re.findall(r'\d{4}', date_str)
                if year_matches:
                    year = int(year_matches[0])
                    if year > current_year + 1:  # More than 1 year in future
                        anomalies.append({
                            'type': 'FUTURE_DATE',
                            'description': f'Document contains future date: {date_str}',
                            'severity': 'HIGH'
                        })
            except:
                continue
        
        return anomalies
    
    def _check_amount_anomalies(self, content):
        """Check for amount-related anomalies"""
        anomalies = []
        
        # Find all monetary amounts
        amount_patterns = [
            r'₹\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # ₹ format
            r'Rs\.\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Rs. format
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:rupees|RS|₹)'  # Various formats
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean the amount string
                    clean_amount = match.replace(',', '')
                    amount = float(clean_amount)
                    amounts.append(amount)
                except:
                    continue
        
        # Check for unrealistic amounts
        for amount in amounts:
            if amount > 100000000:  # 10 crore
                anomalies.append({
                    'type': 'UNREALISTIC_AMOUNT',
                    'description': f'Unusually large amount detected: ₹{amount:,.2f}',
                    'severity': 'MEDIUM'
                })
        
        return anomalies
    
    def _pattern_based_detection(self, content, doc_type):
        """Document-type specific pattern detection"""
        anomalies = []
        
        if doc_type == 'BANK_STATEMENT':
            anomalies.extend(self._analyze_bank_statement(content))
        elif doc_type == 'SALARY_SLIP':
            anomalies.extend(self._analyze_salary_slip(content))
        elif doc_type in ['PAN_CARD', 'AADHAAR']:
            anomalies.extend(self._analyze_kyc_document(content, doc_type))
        elif doc_type == 'PROPERTY_DOCUMENT':
            anomalies.extend(self._analyze_property_document(content))
        
        return anomalies
    
    def _analyze_bank_statement(self, content):
        """Analyze bank statement specific anomalies"""
        anomalies = []
        
        # Check for minimum transaction count
        transaction_indicators = ['withdrawal', 'deposit', 'transfer', 'balance', 'debit', 'credit']
        transaction_count = sum(1 for indicator in transaction_indicators if indicator in content.lower())
        
        if transaction_count < 3:
            anomalies.append({
                'type': 'INSUFFICIENT_TRANSACTIONS',
                'description': 'Bank statement shows very few transactions',
                'severity': 'MEDIUM'
            })
        
        # Check for negative balances
        if 'overdraft' in content.lower() or '-₹' in content or '(₹' in content:
            anomalies.append({
                'type': 'NEGATIVE_BALANCE',
                'description': 'Potential overdraft or negative balance detected',
                'severity': 'HIGH'
            })
        
        return anomalies
    
    def _analyze_salary_slip(self, content):
        """Analyze salary slip specific anomalies"""
        anomalies = []
        
        # Check for salary components
        expected_components = ['basic', 'hra', 'da', 'ta', 'pf', 'tax', 'net', 'gross']
        found_components = [comp for comp in expected_components if comp in content.lower()]
        
        if len(found_components) < 3:
            anomalies.append({
                'type': 'INCOMPLETE_SALARY_SLIP',
                'description': 'Salary slip missing standard components',
                'severity': 'MEDIUM'
            })
        
        # Check for round numbers (might indicate fabricated amounts)
        amount_pattern = r'₹\s*(\d+)'
        amounts = re.findall(amount_pattern, content)
        round_numbers = [amt for amt in amounts if amt.endswith('000') or amt.endswith('500')]
        
        if len(round_numbers) > len(amounts) * 0.5:  # More than 50% round numbers
            anomalies.append({
                'type': 'SUSPICIOUS_ROUND_NUMBERS',
                'description': 'Unusual number of round figure amounts',
                'severity': 'LOW'
            })
        
        return anomalies
    
    def _analyze_kyc_document(self, content, doc_type):
        """Analyze KYC document anomalies"""
        anomalies = []
        
        if doc_type == 'PAN_CARD':
            # Check PAN format
            pan_pattern = r'[A-Z]{5}\d{4}[A-Z]'
            if not re.search(pan_pattern, content):
                anomalies.append({
                    'type': 'INVALID_PAN_FORMAT',
                    'description': 'PAN card number format appears invalid',
                    'severity': 'HIGH'
                })
        
        elif doc_type == 'AADHAAR':
            # Check Aadhaar format (12 digits, possibly with spaces)
            aadhaar_pattern = r'\d{4}\s?\d{4}\s?\d{4}'
            if not re.search(aadhaar_pattern, content):
                anomalies.append({
                    'type': 'INVALID_AADHAAR_FORMAT',
                    'description': 'Aadhaar number format appears invalid',
                    'severity': 'HIGH'
                })
        
        return anomalies
    
    def _analyze_property_document(self, content):
        """Analyze property document anomalies"""
        anomalies = []
        
        # Check for property measurement units
        area_units = ['sq.ft', 'sq ft', 'square feet', 'sq.m', 'square meters', 'acres', 'hectares']
        found_units = [unit for unit in area_units if unit in content.lower()]
        
        if not found_units:
            anomalies.append({
                'type': 'MISSING_PROPERTY_DETAILS',
                'description': 'Property document missing area measurements',
                'severity': 'MEDIUM'
            })
        
        return anomalies
    
    def _consistency_checks(self, content, application_data, doc_type):
        """Check consistency with application data"""
        anomalies = []
        
        applicant_name = application_data.get('applicant_name', '').lower()
        if applicant_name and applicant_name not in content.lower():
            anomalies.append({
                'type': 'NAME_MISMATCH',
                'description': 'Applicant name not found in document',
                'severity': 'HIGH'
            })
        
        # Check for amount consistency
        if doc_type == 'SALARY_SLIP':
            monthly_salary = application_data.get('monthly_salary')
            if monthly_salary:
                salary_pattern = r'₹\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
                amounts = re.findall(salary_pattern, content)
                for amount_str in amounts:
                    try:
                        doc_amount = float(amount_str.replace(',', ''))
                        # Check if document amount is significantly different
                        if abs(doc_amount - monthly_salary) > monthly_salary * 0.3:  # 30% difference
                            anomalies.append({
                                'type': 'SALARY_MISMATCH',
                                'description': f'Document salary (₹{doc_amount:,.2f}) differs from application (₹{monthly_salary:,.2f})',
                                'severity': 'HIGH'
                            })
                    except:
                        continue
        
        return anomalies
    
    def _ai_anomaly_detection(self, content, doc_type, application_data):
        """Use AI for advanced anomaly detection"""
        try:
            prompt = f"""
            Analyze this {doc_type} document for anomalies and suspicious patterns:
            
            Document Content: {content[:2000]}
            
            Application Context:
            - Applicant: {application_data.get('applicant_name', 'N/A')}
            - Expected Salary: {application_data.get('monthly_salary', 'N/A')}
            - Loan Amount: {application_data.get('loan_amount', 'N/A')}
            
            Look for:
            1. Inconsistencies in dates, amounts, or personal information
            2. Suspicious patterns indicating document tampering
            3. Formatting anomalies
            4. Logical inconsistencies
            5. Signs of document fabrication
            
            Respond with JSON format:
            {{
                "anomalies_found": [
                    {{
                        "type": "anomaly_type",
                        "description": "detailed description",
                        "confidence": "HIGH|MEDIUM|LOW",
                        "severity": "HIGH|MEDIUM|LOW"
                    }}
                ],
                "overall_risk": "LOW|MEDIUM|HIGH",
                "analysis_summary": "brief summary"
            }}
            """
            
            response = requests.post(
                self.ollama_url,
                json={
                    'model': 'mistral',
                    'prompt': prompt,
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return self._parse_ai_anomaly_response(response.json().get('response', ''))
            else:
                return []
                
        except Exception as e:
            current_app.logger.error(f"AI anomaly detection error: {str(e)}")
            return []
    
    def _parse_ai_anomaly_response(self, ai_response):
        """Parse AI anomaly detection response"""
        try:
            import json
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                anomalies = result.get('anomalies_found', [])
                
                # Convert AI anomalies to our format
                formatted_anomalies = []
                for anomaly in anomalies:
                    formatted_anomalies.append({
                        'type': f"AI_DETECTED_{anomaly.get('type', 'UNKNOWN').upper()}",
                        'description': anomaly.get('description', 'AI detected anomaly'),
                        'severity': anomaly.get('severity', 'MEDIUM')
                    })
                
                return formatted_anomalies
            return []
        except:
            return []
    
    def _calculate_anomaly_score(self, anomalies):
        """Calculate overall anomaly score (0-100)"""
        if not anomalies:
            return 0
        
        severity_weights = {
            'HIGH': 3,
            'MEDIUM': 2, 
            'LOW': 1
        }
        
        total_weight = sum(severity_weights.get(anomaly.get('severity', 'LOW'), 1) for anomaly in anomalies)
        max_possible = len(anomalies) * 3  # All high severity
        
        return min(100, (total_weight / max_possible) * 100) if max_possible > 0 else 0
    
    def _determine_risk_level(self, anomaly_score):
        """Determine risk level based on anomaly score"""
        if anomaly_score >= 70:
            return 'HIGH'
        elif anomaly_score >= 30:
            return 'MEDIUM'
        else:
            return 'LOW'