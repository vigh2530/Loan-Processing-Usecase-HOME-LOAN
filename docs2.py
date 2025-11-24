import os
import random
from datetime import datetime, timedelta
from faker import Faker
from fpdf import FPDF, XPos, YPos
import qrcode

fake = Faker('en_IN')

# --- 5 USERS WITH STATUS ---
USERS = [
    ("Amit Gupta", "Approved"),
    ("Neha Kapoor", "Pending"),
    ("Suresh Naik", "Rejected"),
    ("Pooja Saxena", "Review"),
    ("Rohan Jadhav", "Done"),
]

BASE_OUTPUT = r"D:\homeloandemo1\users"


# ------------ CUSTOM PDF CLASS ------------
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')


# ------------ CREATE SALARY SLIP ------------
def create_salary_slip(profile, date, folder):
    pdf = PDF()
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, profile["company"], align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, "Salary Slip", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    fields = [
        ("Employee Name:", profile["name"]),
        ("PAN Number:", profile["pan"]),
        ("Month:", date.strftime("%B %Y")),
    ]

    for label, value in fields:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(40, 7, label)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)

    gross_salary = profile["net_salary"] * 1.15
    deductions = gross_salary - profile["net_salary"]

    data = [
        ["Earnings", "Amount (INR)", "Deductions", "Amount (INR)"],
        ["Basic Salary", f"{gross_salary*0.5:,.2f}", "PF", f"{deductions*0.6:,.2f}"],
        ["HRA", f"{gross_salary*0.3:,.2f}", "Professional Tax", f"{deductions*0.4:,.2f}"],
        ["Special Allowance", f"{gross_salary*0.2:,.2f}", "", ""],
        ["", "", "", ""],
        ["Gross Earnings", f"{gross_salary:,.2f}", "Total Deductions", f"{deductions:,.2f}"],
    ]

    with pdf.table(width=180, text_align="CENTER") as table:
        for row in data:
            tr = table.row()
            for cell in row:
                tr.cell(cell)

    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f"Net Salary: INR {profile['net_salary']:,.2f}", align='R')

    pdf.output(os.path.join(folder, f"salary_slip_{date.strftime('%b_%Y')}.pdf"))


# ------------ BANK STATEMENT ------------
def create_bank_statement(profile, folder, months=6):
    pdf = PDF()
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, profile["bank"], align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, "Bank Statement", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    fields = [
        ("Customer Name:", profile["name"]),
        ("Address:", profile["address"]),
        ("Account Number:", profile["account_no"]),
    ]

    for label, value in fields:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(40, 7, label)
        pdf.set_font('Helvetica', '', 10)
        pdf.multi_cell(0, 7, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    balance = random.uniform(80000, 200000)

    for i in range(months, 0, -1):
        month_date = datetime.now() - timedelta(days=i * 30)

        pdf.ln(4)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, f"Transactions - {month_date.strftime('%B %Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        headers = ["Date", "Description", "Debit", "Credit", "Balance"]

        with pdf.table(width=190, text_align="LEFT") as table:
            hr = table.row()
            for h in headers:
                hr.cell(h)

            row = table.row()
            row.cell(month_date.replace(day=1).strftime("%d-%m-%Y"))
            row.cell("Opening Balance")
            row.cell("")
            row.cell("")
            row.cell(f"{balance:,.2f}")

            salary_date = month_date.replace(day=random.randint(1, 5))
            balance += profile["net_salary"]

            row = table.row()
            row.cell(salary_date.strftime("%d-%m-%Y"))
            row.cell(f"Salary Credit - {profile['company']}")
            row.cell("")
            row.cell(f"{profile['net_salary']:,.2f}")
            row.cell(f"{balance:,.2f}")

            for _ in range(random.randint(5, 10)):
                debit = random.uniform(500, 6000)
                balance -= debit
                spend_date = salary_date + timedelta(days=random.randint(3, 25))

                row = table.row()
                row.cell(spend_date.strftime("%d-%m-%Y"))
                row.cell(fake.bs().upper())
                row.cell(f"{debit:,.2f}")
                row.cell("")
                row.cell(f"{balance:,.2f}")

    pdf.output(os.path.join(folder, "bank_statement_last_6_months.pdf"))


# ------------ KYC DOCUMENT ------------
def create_kyc_document(profile, folder):
    pdf = FPDF(orientation="L", unit="mm", format=[148, 105])
    pdf.add_page()
    pdf.rect(5, 5, pdf.w - 10, pdf.h - 10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 10, "GOVERNMENT OF INDIA", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    qr_text = f"{profile['name']} | {profile['aadhar']} | {profile['pan']}"
    qr_path = os.path.join(folder, "temp_qr.png")
    qrcode.make(qr_text).save(qr_path)
    pdf.image(qr_path, x=10, y=25, w=30)
    os.remove(qr_path)

    pdf.set_xy(45, 30)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Name: {profile['name']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(45)
    pdf.cell(0, 7, f"PAN: {profile['pan']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Aadhar: {profile['aadhar']}", align="C")

    pdf.output(os.path.join(folder, "kyc_document.pdf"))


# ------------ PROPERTY REPORT ------------
def create_property_report(profile, folder):
    pdf = PDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Property Valuation Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        7,
        f"Applicant: {profile['name']}\n"
        f"Property Address: {profile['property_address']}\n\n"
        f"Assessed Market Value: INR {profile['property_value']:,.2f}",
    )

    pdf.output(os.path.join(folder, "property_valuation_report.pdf"))


# ------------ LEGAL CLEARANCE ------------
def create_legal_clearance(profile, folder):
    pdf = PDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Legal Clearance Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        7,
        f"The property located at {profile['property_address']} belonging to {profile['name']} "
        f"is legally verified and clear for mortgage.",
    )

    pdf.output(os.path.join(folder, "legal_clearance_document.pdf"))


# ------------ NA PERMISSION ------------
def create_na_certificate(profile, folder):
    pdf = PDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "NA Permission Certificate", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        7,
        f"This certifies that the land located at {profile['property_address']} "
        f"owned by {profile['name']} is approved for Non-Agricultural usage.",
    )

    pdf.output(os.path.join(folder, "na_permission_certificate.pdf"))


# ------------ ADVANCED TXT FILE (EXACT FORMAT YOU WANT) ------------
def create_details_txt(profile, status, folder):
    first, last = profile["name"].split(" ", 1)

    txt = f"""
Applicant Details
First Name: {first}
Last Name: {last}
Gender: {profile['gender']}
Email: {profile['email']}
Aadhar Number: {profile['aadhar']}
PAN Number: {profile['pan']}
Current Residential Address: {profile['address']}
Current Residence Status: {profile['residence_status']}
Do you own any other properties?: {profile['owns_other_property']}

Financial & Employment Details
Monthly Salary (INR): {profile['net_salary']}
Company Name: {profile['company']}
Existing EMI (if any, INR): {profile['existing_emi']}
CIBIL Score: {profile['cibil']}

Property & Loan Details
Loan Amount Requested (INR): {profile['loan_amount']}
Property Valuation (INR): {profile['property_value']}
Full Property Address (for loan): {profile['property_address']}
Is the property Non-Agricultural?: {profile['is_na']}
Is there an existing mortgage on this property?: {profile['is_mortgaged']}
Loan Status: {status}
""".strip()

    with open(os.path.join(folder, f"{profile['username']}_details.txt"), "w", encoding="utf-8") as f:
        f.write(txt)


# ------------ MAIN FUNCTION ------------
if __name__ == "__main__":
    print("\n--- Starting Full Multi-User Document Generation ---\n")

    for user_name, status in USERS:
        username = user_name.lower().replace(" ", "_")
        folder = os.path.join(BASE_OUTPUT, username)
        os.makedirs(folder, exist_ok=True)

        # Generate full profile
        profile = {
            "username": username,
            "name": user_name,
            "gender": random.choice(["Male", "Female"]),
            "email": username + "@example.com",

            "dob": fake.date_of_birth(minimum_age=25, maximum_age=50).strftime("%d-%b-%Y"),
            "address": fake.address().replace("\n", ", "),
            "residence_status": random.choice(["Owned", "Rented"]),
            "owns_other_property": random.choice(["Yes", "No"]),

            "pan": fake.bothify(text="?????####?").upper(),
            "aadhar": fake.bothify(text="#### #### ####"),

            "company": fake.company(),
            "designation": fake.job(),
            "net_salary": random.randint(35000, 150000),
            "existing_emi": random.randint(0, 20000),
            "cibil": random.randint(680, 830),

            "loan_amount": random.randint(1500000, 3500000),

            "bank": random.choice(["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank"]),
            "account_no": fake.bban(),

            "property_address": fake.address().replace("\n", ", "),
            "property_value": random.randint(8000000, 20000000),
            "is_na": "Yes",
            "is_mortgaged": random.choice(["Yes", "No"]),
        }

        print(f"Generating docs for: {user_name} ({status})")

        # Salary Slips (3 months)
        for i in range(3, 0, -1):
            slip_date = datetime.now() - timedelta(days=i * 30)
            create_salary_slip(profile, slip_date, folder)

        create_bank_statement(profile, folder)
        create_kyc_document(profile, folder)
        create_property_report(profile, folder)
        create_legal_clearance(profile, folder)
        create_na_certificate(profile, folder)

        create_details_txt(profile, status, folder)

    print("\n--- ALL DOCUMENTS GENERATED SUCCESSFULLY ---")
    print(f"Base Folder: {BASE_OUTPUT}")
