import os
import random
from datetime import datetime, timedelta
from faker import Faker
from fpdf import FPDF, XPos, YPos
import qrcode

# Initialize Faker for realistic data
fake = Faker('en_IN')

# --- MASTER PROFILE (fake applicant data) ---
profile = {
    "name": "Rahul Sharma",
    "dob": "25-Jul-1991",
    "address": "Flat 1101, Pinnacle Towers, Gurugram, Haryana, 122002",
    "pan": "FGHIJ5678K",
    "aadhar": "9876 5432 1098",
    "company": "NextGen Analytics",
    "designation": "Data Scientist",
    "bank": "Axis Bank",
    "account_no": "919020012345678",
    "net_monthly_salary": 115000.00,
    "property_address": "Plot 42, Sector 57, Gurugram, Haryana, 122003",
    "property_valuation": 11000000.00
}

# --- OUTPUT DIRECTORY ---
OUTPUT_DIR = r"D:\casaflow-ml\rahulsharma"

class PDF(FPDF):
    """Custom PDF class for consistent headers/footers."""
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

# ---------------------- SALARY SLIP ----------------------
def create_salary_slip(profile, date):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, profile["company"], align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, 'Salary Slip', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'Employee Name:')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, profile["name"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'PAN Number:')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, profile["pan"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'Month:')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, date.strftime('%B %Y'), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    gross_salary = profile["net_monthly_salary"] * 1.15
    deductions = gross_salary - profile["net_monthly_salary"]

    data = [
        ["Earnings", "Amount (INR)", "Deductions", "Amount (INR)"],
        ["Basic Salary", f"{gross_salary*0.5:,.2f}", "Provident Fund", f"{deductions*0.6:,.2f}"],
        ["HRA", f"{gross_salary*0.3:,.2f}", "Professional Tax", f"{deductions*0.4:,.2f}"],
        ["Special Allowance", f"{gross_salary*0.2:,.2f}", "", ""],
        ["", "", "", ""],
        ["Gross Earnings", f"{gross_salary:,.2f}", "Total Deductions", f"{deductions:,.2f}"],
    ]

    with pdf.table(text_align="CENTER", width=180) as table:
        for row_data in data:
            row = table.row()
            for cell in row_data:
                row.cell(cell)

    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f'Net Salary Paid: INR {profile["net_monthly_salary"]:,.2f}', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    filename = os.path.join(OUTPUT_DIR, f"salary_slip_{date.strftime('%b_%Y')}.pdf")
    pdf.output(filename)
    print(f"✅ Created: {filename}")

# ---------------------- BANK STATEMENT ----------------------
def create_bank_statement(profile, months=6):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, profile["bank"], align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, 'Account Statement', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'Customer Name:')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, profile["name"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'Address:')
    pdf.set_font('Helvetica', '', 10)
    pdf.multi_cell(0, 7, profile["address"], align='L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'Account Number:')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, profile["account_no"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    opening_balance = random.uniform(70000, 200000)

    for i in range(months, 0, -1):
        current_date = datetime.now() - timedelta(days=i * 30)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, f"Transactions for {current_date.strftime('%B %Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        with pdf.table(width=190, text_align="LEFT") as table:
            header_row = table.row()
            for h in headers:
                header_row.cell(h)

            data_row = table.row()
            data_row.cell(current_date.replace(day=1).strftime('%d-%m-%Y'))
            data_row.cell("Opening Balance")
            data_row.cell("")
            data_row.cell("")
            data_row.cell(f"{opening_balance:,.2f}")

            salary_credit_date = current_date.replace(day=random.randint(1, 5))
            balance = opening_balance + profile["net_monthly_salary"]
            data_row = table.row()
            data_row.cell(salary_credit_date.strftime('%d-%m-%Y'))
            data_row.cell(f"SALARY CREDIT - {profile['company']}")
            data_row.cell("")
            data_row.cell(f"{profile['net_monthly_salary']:,.2f}")
            data_row.cell(f"{balance:,.2f}")

            for _ in range(random.randint(6, 12)):
                debit_amount = random.uniform(500, 8000)
                balance -= debit_amount
                debit_date = salary_credit_date + timedelta(days=random.randint(2, 28))
                data_row = table.row()
                data_row.cell(debit_date.strftime('%d-%m-%Y'))
                data_row.cell(fake.bs().upper())
                data_row.cell(f"{debit_amount:,.2f}")
                data_row.cell("")
                data_row.cell(f"{balance:,.2f}")

            opening_balance = balance

    filename = os.path.join(OUTPUT_DIR, "bank_statement_last_6_months.pdf")
    pdf.output(filename)
    print(f"✅ Created: {filename}")

# ---------------------- KYC DOCUMENT ----------------------
def create_kyc_document(profile):
    pdf = FPDF(orientation='L', unit='mm', format=[148, 105])
    pdf.add_page()
    pdf.set_line_width(0.5)
    pdf.rect(5, 5, pdf.w - 10, pdf.h - 10)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 10, 'GOVERNMENT OF INDIA', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    qr_data = f"Aadhar No: {profile['aadhar']}\nName: {profile['name']}\nPAN: {profile['pan']}"
    qr_img = qrcode.make(qr_data)
    qr_path = os.path.join(OUTPUT_DIR, "temp_qr.png")
    qr_img.save(qr_path)
    pdf.image(qr_path, x=10, y=25, w=30)
    os.remove(qr_path)

    pdf.set_xy(45, 30)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, f"Name: {profile['name']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(45)
    pdf.cell(0, 7, f"PAN: {profile['pan']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, f"Aadhar: {profile['aadhar']}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    filename = os.path.join(OUTPUT_DIR, "kyc_document.pdf")
    pdf.output(filename)
    print(f"✅ Created: {filename}")

# ---------------------- PROPERTY VALUATION ----------------------
def create_property_valuation_report(profile):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Property Valuation Report', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%d %B, %Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, "Ref: Loan application for " + profile["name"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', 'BU', 12)
    pdf.cell(0, 10, "Subject: Valuation of Property", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 11)
    text = f"As per your request, we have inspected the property located at:\n{profile['property_address']}.\n\n"
    pdf.multi_cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 15, f"Assessed Fair Market Value: INR {profile['property_valuation']:,.2f}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(20)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, "Sincerely, Certified Valuer", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    filename = os.path.join(OUTPUT_DIR, "property_valuation_report.pdf")
    pdf.output(filename)
    print(f"✅ Created: {filename}")

# ---------------------- LEGAL CLEARANCE ----------------------
def create_legal_clearance_document(profile):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Legal Opinion Report', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', 'BU', 12)
    pdf.cell(0, 10, "Title Search and Legal Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 11)
    text = (
        f"Regarding property at {profile['property_address']} for applicant {profile['name']} (PAN: {profile['pan']}).\n\n"
        f"We have examined the title deeds and encumbrance certificates. The title is clear, marketable, and free from all legal doubts. "
        f"The property is legally fit for mortgage."
    )
    pdf.multi_cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    filename = os.path.join(OUTPUT_DIR, "legal_clearance_document.pdf")
    pdf.output(filename)
    print(f"✅ Created: {filename}")

# ---------------------- NA PERMISSION DOCUMENT ----------------------
def create_na_permission_document(profile):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'NON-AGRICULTURAL (NA) PERMISSION CERTIFICATE', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%d %B, %Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, f"Ref No: NA/{random.randint(1000,9999)}/{datetime.now().year}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_font('Helvetica', 'BU', 12)
    pdf.cell(0, 10, "Subject: Conversion of Agricultural Land to Non-Agricultural Use", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 11)
    text = (
        f"This is to certify that the land located at {profile['property_address']}, "
        f"owned by {profile['name']} (PAN: {profile['pan']}), has been duly verified and approved "
        f"for Non-Agricultural (NA) use by the competent local authority.\n\n"
        f"The said property can be used for residential and commercial purposes. "
        f"No legal disputes or restrictions are found on the said land parcel."
    )
    pdf.multi_cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(15)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, "Authorized Signatory,", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, "Department of Urban Development", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, "Government of Haryana", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    filename = os.path.join(OUTPUT_DIR, "na_permission_certificate.pdf")
    pdf.output(filename)
    print(f"✅ Created: {filename}")

# ---------------------- MAIN SCRIPT ----------------------
if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"--- Starting Document Generation for {profile['name']} ---")

    for i in range(3, 0, -1):
        slip_date = datetime.now() - timedelta(days=i * 30)
        create_salary_slip(profile, slip_date)

    create_bank_statement(profile, months=6)
    create_kyc_document(profile)
    create_property_valuation_report(profile)
    create_legal_clearance_document(profile)
    create_na_permission_document(profile)

    print("\n--- Document Generation Complete ---")
    print(f"All files are saved in: {OUTPUT_DIR}")
