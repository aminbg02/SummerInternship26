"""Seed a realistic document corpus into the companies' Qdrant knowledge bases.

Unlike seed_kb.py (which indexes two tiny snippets to prove isolation), this loads
a full set of support documents per company, in the three formats the platform
accepts: **.txt, .pdf and .docx**. Each document is:
  1. AUTHORED as a real file in backend/sample_docs/<company>/ — a real PDF, a real
     Word file, not text with a misleading extension;
  2. read back off disk and pushed through services/extract.py, the same parser the
     /ingest endpoint uses, so what gets indexed is exactly what an admin uploading
     that file by hand would get (this is the point: it exercises pypdf and
     python-docx for real, rather than pretending);
  3. chunked + screened (Filter -> Classifier), like every other ingest;
  4. embedded and upserted into that company's kb_<id> Qdrant collection;
  5. recorded as a Document + KbIngestion row, so it shows up in the admin's
     ingestion history and can be previewed and removed like any real upload.

Idempotent: a document already ingested (same company + filename) is skipped, so
re-running won't create duplicate vectors.

Content is deliberately ASCII-only. The PDF writer uses fpdf2's core fonts, which
are latin-1; a stray curly quote or a euro sign would raise at write time. Say
"euros", not a symbol.

Run with:  python -m app.seed_docs   (from the backend/ dir, with Docker up)
"""
import os

from . import create_app
from .extensions import db
from .models import Company, Document, KbIngestion, User
from .services import chunking, extract, rag, screening

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_docs")

# company_key -> how to find its Company row (by name, or by email domain).
COMPANY_LOOKUP = {
    "telecom": {"domain": "telecom.com"},
    "ooredoo": {"domain": "ooredoo.tn"},
    "biat": {"domain": "biat.com.tn"},
    "topnet": {"domain": "topnet.com"},
    "fiat": {"domain": "fiat.com"},
    "utm": {"domain": "utm.com"},
    "globalnet": {"domain": "globalnet.com"},
}

# company_key -> {filename: document text}. The EXTENSION picks the writer, so the
# same source text becomes a real .pdf, .docx or .txt on disk.
#
# Deliberately concrete: "how much is Fiber Pro?", "what is the ATM limit?", "how
# long is the cancellation notice?" all have exact answers in here, so retrieval can
# be judged right or wrong instead of merely plausible. Each company's corpus is
# distinct (a telco vs. a bank vs. an ISP), which is what makes tenant isolation
# visible: ask two companies the same question, get different answers.
DOCS = {
    # ---------------------------------------------------------------- telecom --
    "telecom": {
        "telecom_plans.txt": (
            "Telecom Plans and Pricing.\n"
            "Mobile plans: Start (5 GB, 10 euros/month), Plus (30 GB, 20 euros/month), "
            "Unlimited (unlimited data, 35 euros/month). All mobile plans include "
            "unlimited calls and SMS within the country.\n"
            "Home internet: Fiber Lite (100 Mbps, 49 euros/month), Fiber Pro "
            "(500 Mbps, 79 euros/month), Fiber Max (1 Gbps, 99 euros/month). "
            "Fiber Pro and Fiber Max include a free Wi-Fi 6 router. Installation is "
            "free on a 12-month contract, otherwise a one-time 49 euro fee applies."
        ),
        "telecom_billing.txt": (
            "Telecom Billing.\n"
            "Invoices are issued on the first of each month and cover that month. "
            "Payment is due within 14 days. Accepted methods: credit card, SEPA "
            "direct debit, and bank transfer. Late payments incur a 5 percent fee "
            "after 14 days, and service may be suspended after 30 days overdue.\n"
            "Refunds: a customer may request a refund within 14 days of a new "
            "subscription (cooling-off period). Prorated refunds are issued when "
            "downgrading a plan mid-cycle."
        ),
        "telecom_support.txt": (
            "Telecom Technical Support.\n"
            "Support is available 24/7 for Fiber Pro and Fiber Max subscribers, and "
            "8am-8pm for other plans. Phone: 800-TELECOM. \n"
            "Router reset: hold the reset button for 10 seconds until the lights "
            "blink; the router reboots in about 2 minutes. The default Wi-Fi name and "
            "password are printed on the label on the underside of the router. \n"
            "If your internet is down, first check for outages in the Telecom app "
            "under Service Status. A blinking red light means no fiber signal - "
            "contact support to schedule a technician."
        ),
        "telecom_roaming.txt": (
            "Telecom International Roaming.\n"
            "Roaming within the EU is included at no extra cost on all mobile plans "
            "(fair-use cap of 25 GB/month). Outside the EU, a Travel Pass is "
            "required: 5 euros/day for 1 GB, or 25 euros/week for 5 GB. Roaming is "
            "disabled by default outside the EU and must be enabled in the Telecom "
            "app to avoid unexpected charges."
        ),
        "telecom_contract_terms.pdf": (
            "Telecom Contract Terms and Cancellation Policy.\n"
            "\n"
            "Contract length. Mobile plans are month-to-month unless a subsidised "
            "handset is included, in which case the minimum term is 24 months. Home "
            "internet plans are offered on a 12-month or 24-month commitment; the "
            "24-month commitment reduces the monthly price by 5 euros.\n"
            "\n"
            "Notice period. To cancel, give 30 days notice through the Telecom app, in "
            "writing, or by calling support. The service remains active, and billable, "
            "until the notice period ends. Cancellation takes effect at the end of the "
            "billing cycle in which the notice period expires.\n"
            "\n"
            "Early termination. Cancelling a committed contract before its term ends "
            "incurs an early termination fee equal to the remaining monthly payments, "
            "capped at 6 months of service. A subsidised handset must additionally be "
            "paid off in full. There is no early termination fee if the customer is "
            "moving to an address where Telecom cannot provide service; proof of "
            "address is required.\n"
            "\n"
            "Cooling-off period. A new contract can be cancelled without penalty within "
            "14 days of activation. Equipment must be returned undamaged within 14 days "
            "of cancellation, or it is charged at its full retail price.\n"
            "\n"
            "Price changes. Telecom may change prices with 30 days notice. If a price "
            "increase exceeds the rate of inflation, the customer may terminate the "
            "contract without an early termination fee within 30 days of the notice.\n"
            "\n"
            "Equipment return. Routers and set-top boxes remain the property of Telecom "
            "and must be returned within 14 days of cancellation. Return is free using a "
            "prepaid label available in the app. An unreturned router is charged at 120 "
            "euros and an unreturned set-top box at 80 euros."
        ),
        "telecom_devices.pdf": (
            "Telecom Devices, Handset Financing and Warranty.\n"
            "\n"
            "Handset financing. A handset can be paid upfront or spread over 24 monthly "
            "instalments at 0 percent interest, added to the monthly bill. The device is "
            "owned by the customer from day one; the instalments are a separate line on "
            "the invoice and survive a plan change. Settling the balance early is free "
            "and can be done at any time in the app.\n"
            "\n"
            "Upgrade policy. After 12 paid instalments, a customer may trade in the "
            "handset and upgrade. The remaining balance is cleared by the trade-in value "
            "if the device is in good condition, meaning it powers on, has no cracked "
            "screen and no liquid damage.\n"
            "\n"
            "Manufacturer warranty. All handsets carry a 24-month manufacturer warranty "
            "covering defects, but not accidental damage, liquid damage or a battery "
            "worn by normal use. A warranty repair takes 5 to 10 business days, and a "
            "loan device is provided free of charge for repairs expected to exceed 5 "
            "days.\n"
            "\n"
            "Device protection. Optional device insurance costs 7 euros/month and covers "
            "accidental damage, liquid damage and theft, with a 50 euro excess per claim "
            "and a maximum of two claims per 12 months. Insurance must be added within 30 "
            "days of purchasing the handset.\n"
            "\n"
            "Lost or stolen. Report a lost or stolen handset immediately so the SIM can "
            "be blocked. A replacement SIM keeping the same number costs 10 euros and is "
            "issued in store the same day. Instalments continue during any insurance "
            "claim."
        ),
        "telecom_business.docx": (
            "Telecom Business and Enterprise Services.\n"
            "\n"
            "Business plans. Business Mobile Start (20 GB, 18 euros/line/month), "
            "Business Mobile Pro (unlimited data, 30 euros/line/month), and Business "
            "Fiber (1 Gbps symmetric, 149 euros/month). Accounts with 5 or more lines "
            "receive a 10 percent discount; 20 or more lines receive 20 percent.\n"
            "\n"
            "Service level agreement. Business Fiber carries a 99.9 percent uptime SLA "
            "measured monthly. Faults are responded to within 4 hours and a technician "
            "is on site within 8 business hours. If monthly uptime falls below the SLA, "
            "the customer is credited 10 percent of the monthly fee per 0.1 percent "
            "below target, up to 50 percent of the monthly fee. Credits are requested "
            "through the business portal within 30 days of the incident.\n"
            "\n"
            "Static IP and networking. A static IPv4 address costs 10 euros/month. A "
            "block of 8 addresses costs 40 euros/month. Site-to-site VPN between two "
            "Business Fiber lines is included at no extra cost.\n"
            "\n"
            "Dedicated support. Business customers reach a dedicated queue 24/7 and are "
            "assigned an account manager at 10 or more lines. Priority fault handling "
            "places business tickets ahead of residential tickets on the same exchange.\n"
            "\n"
            "Billing. Business accounts are invoiced monthly in arrears with 30-day "
            "payment terms and can be consolidated into a single invoice across all "
            "sites. VAT invoices are available in the business portal."
        ),
        "telecom_privacy.docx": (
            "Telecom Privacy and Data Protection.\n"
            "\n"
            "What we collect. Telecom processes account data (name, address, contact "
            "details), traffic data (call and connection records needed to bill and "
            "route), and service data (device type, network diagnostics). We do not sell "
            "personal data to third parties.\n"
            "\n"
            "Retention. Traffic data required for billing is retained for 12 months and "
            "then deleted. Account data is retained for the life of the contract and for "
            "3 years after it ends, to meet accounting obligations. Support call "
            "recordings are kept for 6 months.\n"
            "\n"
            "Your rights. A customer may request a copy of their personal data, ask for "
            "an inaccuracy to be corrected, or request erasure of data that is no longer "
            "needed. Requests are made in the Telecom app under Privacy, or in writing, "
            "and are answered within 30 days at no cost.\n"
            "\n"
            "Marketing. Marketing messages are only sent with consent. Consent can be "
            "withdrawn at any time in the app under Communication Preferences; the change "
            "takes effect within 48 hours. Withdrawing marketing consent never affects "
            "the service itself.\n"
            "\n"
            "Data breaches. A breach that presents a risk to customers is reported to the "
            "supervisory authority within 72 hours, and affected customers are notified "
            "directly without undue delay.\n"
            "\n"
            "Contact. Privacy questions go to the Data Protection Officer through the "
            "Privacy section of the app or by post to the registered office."
        ),
    },
    # ---------------------------------------------------------------- ooredoo --
    "ooredoo": {
        "ooredoo_plans.txt": (
            "Ooredoo Mobile and Internet Plans.\n"
            "Prepaid mobile: Hayya (3 GB, 10 dinars/month), Hayya Plus (15 GB, "
            "25 dinars/month). Postpaid: Forsa (30 GB, 40 dinars/month) with "
            "unlimited national calls and SMS.\n"
            "Home fibre: Ooredoo Fibre 50 (50 Mbps, 60 dinars/month), Fibre 100 "
            "(100 Mbps, 80 dinars/month), Fibre 200 (200 Mbps, 120 dinars/month). "
            "All fibre plans include a free Wi-Fi router and unlimited data."
        ),
        "ooredoo_support.txt": (
            "Ooredoo Customer Support.\n"
            "Call center is available 24/7 on 1111 (free from an Ooredoo line). "
            "Check your balance and remaining data by dialing *100# or in the My "
            "Ooredoo app.\n"
            "To recharge, buy a scratch card and dial *120*<code>#, or top up in the "
            "app. If your 4G is slow, toggle airplane mode for 10 seconds to "
            "re-attach to the network; a persistent outage should be reported in the "
            "app under Network Status."
        ),
        "ooredoo_billing.txt": (
            "Ooredoo Billing and Payments.\n"
            "Postpaid invoices are issued on the 5th of each month and are due within "
            "10 days. Pay in the My Ooredoo app, at any Ooredoo shop, by bank card "
            "online, or at a post office.\n"
            "A postpaid line is suspended for outgoing calls and data after 15 days "
            "overdue, and fully suspended after 30 days. Reconnection after a full "
            "suspension costs 5 dinars and is applied within 2 hours of payment.\n"
            "Prepaid credit does not expire while the line is active, but a prepaid "
            "line with no recharge and no activity for 6 consecutive months is "
            "deactivated and the number is returned to the pool.\n"
            "Detailed call and data records for the last 6 months are available free of "
            "charge in the app. A printed invoice requested at a shop costs 1 dinar."
        ),
        "ooredoo_roaming.pdf": (
            "Ooredoo International Roaming.\n"
            "\n"
            "Enabling roaming. Roaming is disabled by default on prepaid lines and "
            "enabled by default on postpaid lines. Enable or disable it at any time in "
            "the My Ooredoo app under Roaming, or by calling 1111. The change takes "
            "effect within 15 minutes.\n"
            "\n"
            "Roaming passes. Maghreb Pass: 20 dinars for 1 GB and 30 minutes of calls, "
            "valid 7 days across Algeria, Morocco and Libya. Europe Pass: 50 dinars for "
            "3 GB and 60 minutes, valid 15 days. World Pass: 90 dinars for 5 GB and 60 "
            "minutes, valid 15 days. A pass is activated in the app before or during "
            "travel and starts on first use abroad.\n"
            "\n"
            "Pay as you go. Without a pass, data abroad is charged at 1 dinar per MB in "
            "Europe and 2 dinars per MB elsewhere, so a pass is strongly recommended. "
            "Incoming calls while roaming are charged; outgoing calls to Tunisia cost 2 "
            "dinars per minute in Europe.\n"
            "\n"
            "Spending cap. A roaming spending cap of 100 dinars is applied by default. "
            "When the cap is reached, roaming data stops and an SMS is sent; the cap can "
            "be raised or removed in the app.\n"
            "\n"
            "Coverage. Roaming works on partner networks in more than 150 countries. If "
            "the phone does not register abroad, select the operator manually in the "
            "phone's network settings and make sure data roaming is switched on in the "
            "device as well as in the app."
        ),
        "ooredoo_business.pdf": (
            "Ooredoo Business Solutions.\n"
            "\n"
            "Business mobile. Forsa Business (50 GB, 55 dinars/line/month) with "
            "unlimited national calls, and Forsa Business Plus (unlimited data, 75 "
            "dinars/line/month). Fleets of 10 or more lines receive a 15 percent "
            "discount and a shared data pool, so unused data on one line is available to "
            "the others.\n"
            "\n"
            "Business fibre. Ooredoo Business Fibre 200 (200 Mbps, 200 dinars/month) and "
            "Business Fibre 500 (500 Mbps symmetric, 350 dinars/month), both with a fixed "
            "public IP address included and a 99.5 percent uptime commitment.\n"
            "\n"
            "Fault handling. Business faults are answered on a dedicated line, and a "
            "technician is dispatched within one business day. A fault open for more than "
            "48 hours is credited at one thirtieth of the monthly fee per day of outage.\n"
            "\n"
            "Value-added services. Cloud PBX starts at 15 dinars per extension per month. "
            "Bulk SMS for customer notifications costs 30 millimes per message with "
            "volume discounts above 100000 messages. A managed Wi-Fi hotspot for cafes "
            "and hotels costs 40 dinars/month including the access point.\n"
            "\n"
            "Contracts and billing. Business contracts run for 12 or 24 months, are "
            "invoiced monthly in arrears, and can be paid by bank transfer or standing "
            "order. A single consolidated invoice covers all lines and sites."
        ),
        "ooredoo_sim_esim.docx": (
            "Ooredoo SIM Cards, eSIM and Number Portability.\n"
            "\n"
            "Getting a SIM. A new prepaid SIM costs 5 dinars including 5 dinars of "
            "credit, and requires a national ID card or passport, as registration is "
            "mandatory. A SIM is activated within 30 minutes of registration.\n"
            "\n"
            "eSIM. eSIM is supported on compatible phones on both prepaid and postpaid. "
            "Request an eSIM in the My Ooredoo app or at a shop; a QR code is issued and "
            "scanned once on the device. Converting a physical SIM to an eSIM is free the "
            "first time and costs 10 dinars thereafter. An eSIM can be moved to a new "
            "phone by re-issuing the QR code in the app.\n"
            "\n"
            "Replacing a SIM. A lost, stolen or damaged SIM is replaced at any shop for "
            "10 dinars, keeping the same number and balance. Bring the ID document used "
            "to register the line, as the replacement is only issued to the registered "
            "owner.\n"
            "\n"
            "Number portability. Keeping an existing number when moving to Ooredoo takes "
            "one business day. Bring the ID document and the number to be ported; do not "
            "cancel the old line first, as the port fails if the number is already "
            "deactivated. Porting is free and the service is briefly interrupted during "
            "the switch, usually for a few minutes.\n"
            "\n"
            "PIN and PUK. After three wrong PIN attempts the SIM locks and requires the "
            "PUK code, which is printed on the plastic card the SIM came in and is also "
            "shown in the app. After ten wrong PUK attempts the SIM is permanently "
            "blocked and must be replaced."
        ),
    },
    # ------------------------------------------------------------------- biat --
    "biat": {
        "biat_accounts.txt": (
            "BIAT Bank Accounts and Fees.\n"
            "Account types: Compte Cheque (current account, 5 dinars/month), Compte "
            "Epargne (savings, no monthly fee, 3 percent annual interest), and Compte "
            "Devise (foreign-currency account for expatriates).\n"
            "Opening an account requires a national ID or passport, proof of address, "
            "and a minimum deposit of 20 dinars. Account statements are free in the "
            "BIAT Net app; a paper statement by post costs 2 dinars per request."
        ),
        "biat_cards.txt": (
            "BIAT Bank Cards.\n"
            "Card options: CIB national debit card (40 dinars/year), Visa "
            "Classic international (90 dinars/year), and Visa Gold (180 dinars/year "
            "with travel insurance). \n"
            "Default limits on a Visa Classic: 1000 dinars/day for ATM withdrawals "
            "and 3000 dinars/day for payments; limits can be raised temporarily in "
            "the app. If your card is lost or stolen, block it immediately in the "
            "BIAT Net app or call 71 340 733, then request a replacement at any "
            "branch (issued within 5 business days)."
        ),
        "biat_transfers.txt": (
            "BIAT Transfers and Foreign Exchange.\n"
            "Domestic transfers between BIAT accounts are instant and free in the BIAT "
            "Net app. A transfer to another Tunisian bank costs 1 dinar and arrives the "
            "same business day if ordered before 3pm, otherwise the next business day.\n"
            "International transfers cost 20 dinars plus 0.3 percent of the amount, with "
            "a minimum of 25 dinars, and take 2 to 5 business days. The IBAN and the SWIFT "
            "or BIC code of the beneficiary bank are required; a missing BIC is the most "
            "common cause of a delayed transfer.\n"
            "Foreign exchange is applied at the daily rate published each morning. A "
            "Compte Devise may be credited by international transfer without conversion. "
            "Currency allowances for travel are set by the central bank and require the "
            "travel document to be presented at a branch.\n"
            "Standing orders for a fixed amount can be set up in the app at no charge and "
            "are executed on the chosen day of each month."
        ),
        "biat_loans.pdf": (
            "BIAT Loans and Credit.\n"
            "\n"
            "Personal loan. Amounts from 1000 to 30000 dinars over 12 to 60 months, at a "
            "fixed annual rate from 9.5 percent depending on the term and the customer's "
            "profile. A file fee of 1 percent of the amount applies, with a minimum of 30 "
            "dinars.\n"
            "\n"
            "Eligibility. The applicant must be a BIAT customer with a salary domiciled at "
            "BIAT for at least 3 months, hold a permanent employment contract or show 2 "
            "years of self-employed accounts, and be under 65 at the end of the loan. "
            "Total monthly repayments across all credit may not exceed 40 percent of net "
            "monthly income.\n"
            "\n"
            "Documents required. National ID, the last 3 payslips, an employer "
            "certificate, the last 3 months of account statements, and proof of address. "
            "A decision is given within 5 business days of a complete file, and funds are "
            "released within 2 business days of signature.\n"
            "\n"
            "Home loan. Amounts up to 80 percent of the property value over 5 to 25 "
            "years. A property valuation, the sale agreement and a mortgage registration "
            "are required. Loan insurance covering death and disability is mandatory and "
            "is paid monthly with the instalment.\n"
            "\n"
            "Car loan. Up to 80 percent of the vehicle price over 12 to 60 months, for "
            "new vehicles and for used vehicles less than 5 years old, secured against the "
            "vehicle.\n"
            "\n"
            "Early repayment. A loan may be repaid early in whole or in part. An early "
            "repayment fee of 1 percent of the amount repaid ahead of schedule applies, "
            "and is waived in the final 12 months of the term.\n"
            "\n"
            "Missed payments. A missed instalment incurs late interest and is reported to "
            "the central bank's credit register after 90 days, which affects future "
            "borrowing. Customers in difficulty should contact their branch before the "
            "instalment is missed, as a rescheduling is often possible."
        ),
        "biat_security.pdf": (
            "BIAT Security and Fraud Prevention.\n"
            "\n"
            "BIAT will never ask for your password. Bank staff will never ask, by phone, "
            "SMS, email or in person, for your BIAT Net password, your card PIN, or a "
            "one-time code sent to your phone. Any such request is fraud. End the call and "
            "report it.\n"
            "\n"
            "Phishing. Fraudulent messages imitate BIAT and ask you to click a link to "
            "unblock your account or confirm a payment. Check the sender, never open links "
            "in unexpected messages, and reach BIAT Net only through the official app or by "
            "typing the address yourself. BIAT never sends links that ask you to log in.\n"
            "\n"
            "Card safety. Cover the keypad when entering your PIN. Never write your PIN on "
            "the card or keep it with the card. Inspect an ATM for anything unusual around "
            "the card slot or the keypad, and prefer ATMs inside branches. Enable payment "
            "notifications in the app so every transaction alerts you immediately.\n"
            "\n"
            "If you suspect fraud. Block the card immediately in the BIAT Net app, which "
            "is instant and reversible, or call the 24/7 opposition line. Then report the "
            "disputed transactions at your branch within 13 months, or within 70 days for "
            "transactions outside the country. A card blocked by mistake can be unblocked "
            "in the app.\n"
            "\n"
            "Liability. Transactions made before you report a lost, stolen or misused card "
            "are your responsibility up to a limit of 150 dinars, unless you acted "
            "fraudulently or with gross negligence, such as writing the PIN on the card. "
            "After you report it, you are not liable for further transactions.\n"
            "\n"
            "Strong authentication. Online card payments require confirmation in the BIAT "
            "Net app or a one-time SMS code. Never share that code, even with someone who "
            "says they are from the bank."
        ),
        "biat_net_banking.docx": (
            "BIAT Net Online and Mobile Banking.\n"
            "\n"
            "Enrolment. BIAT Net is free for all account holders. Request access at your "
            "branch or in the app with your account number and national ID. Activation "
            "codes are sent by SMS to the phone number registered on the account, so keep "
            "that number up to date at your branch.\n"
            "\n"
            "What you can do. Check balances and up to 24 months of history, download "
            "statements as PDF, make instant transfers between BIAT accounts, transfer to "
            "other banks, set up standing orders, top up a mobile line, request a "
            "chequebook, block and unblock a card, and adjust card limits.\n"
            "\n"
            "Logging in. Log in with your customer number and password, then confirm with "
            "biometrics or a one-time code. After five failed attempts, access is locked "
            "for 24 hours; it can be unlocked immediately at a branch. A password can be "
            "reset in the app using the registered phone number.\n"
            "\n"
            "Limits. Transfers to a new beneficiary are held for 30 minutes as a fraud "
            "protection, and the beneficiary must be confirmed with a one-time code. The "
            "default daily transfer limit in the app is 5000 dinars and can be raised at a "
            "branch.\n"
            "\n"
            "Availability. BIAT Net is available 24/7 except during a maintenance window "
            "on Sunday between 2am and 4am. Transfers ordered outside business hours are "
            "queued and executed on the next business day, though transfers between two "
            "BIAT accounts are always instant.\n"
            "\n"
            "Support. For a problem with BIAT Net, contact your branch or the support line "
            "during business hours. Never share your screen or install remote-access "
            "software at the request of someone claiming to be from the bank."
        ),
        "biat_branches.docx": (
            "BIAT Branches, ATMs and Opening Hours.\n"
            "\n"
            "Opening hours. Branches are open Monday to Friday, 8am to 4pm, with a break "
            "from 1pm to 2pm at smaller branches. Saturday opening, from 8am to noon, is "
            "offered at selected branches in Tunis, Sfax and Sousse. Branches are closed on "
            "public holidays.\n"
            "\n"
            "Summer hours. During July and August, branches operate a single session from "
            "7:30am to 1:30pm, and during Ramadan from 8am to 2pm. The exact hours for each "
            "branch are published in the BIAT Net app.\n"
            "\n"
            "ATMs. ATMs are available 24/7, including at branches that are closed. "
            "Withdrawals at a BIAT ATM are free. Withdrawing at another bank's ATM in "
            "Tunisia costs 1 dinar per withdrawal. Withdrawing abroad costs 10 dinars plus "
            "2 percent of the amount.\n"
            "\n"
            "If an ATM keeps your card. If the machine retains the card, contact the branch "
            "that owns the ATM during business hours and bring your ID. A retained card is "
            "held for 10 days and then destroyed; after that a replacement must be "
            "requested. If the ATM does not dispense the cash but the account is debited, "
            "report it at your branch, as the amount is credited back after verification, "
            "usually within 7 business days.\n"
            "\n"
            "Appointments. An appointment with an advisor can be booked in the BIAT Net "
            "app and is recommended for loans, account opening and estate matters, which "
            "cannot be completed at a counter."
        ),
    },
    # ----------------------------------------------------------------- topnet --
    "topnet": {
        "topnet_plans.txt": (
            "Topnet Internet Plans.\n"
            "ADSL: 4 Mbps for 30 dinars/month. Fibre: 50 Mbps (60 dinars/month), "
            "100 Mbps (80 dinars/month), 200 Mbps (120 dinars/month). All fibre plans "
            "include a free modem and unlimited data. A 12-month commitment waives the "
            "installation fee."
        ),
        "topnet_support.txt": (
            "Topnet Installation and Support.\n"
            "New fibre installations are scheduled within 5 business days and take "
            "about 2 hours. Support is available daily from 8am to midnight on 1298.\n"
            "If your connection drops, restart the modem by unplugging it for 30 "
            "seconds. A steady red PON light indicates a fibre fault that requires a "
            "technician visit."
        ),
        "topnet_billing.txt": (
            "Topnet Billing and Subscription Changes.\n"
            "Invoices are issued on the 1st of each month and are due within 15 days. Pay "
            "in the Topnet app, online by card, by bank standing order, at a Topnet agency, "
            "or at a post office.\n"
            "Service is throttled to 1 Mbps after 20 days overdue and suspended after 30 "
            "days. Reconnection costs 10 dinars and the line is restored within 4 hours of "
            "payment. A line suspended for more than 90 days is terminated and a new "
            "installation is required.\n"
            "Upgrading a plan takes effect immediately and the difference is prorated on "
            "the next invoice. Downgrading takes effect at the start of the next billing "
            "cycle. Moving home is free within a covered area and takes 5 business days.\n"
            "A subscription can be paused once per year for up to 3 months, for example "
            "during a long absence, at 10 dinars/month to keep the line reserved."
        ),
        "topnet_troubleshooting.pdf": (
            "Topnet Connection Troubleshooting Guide.\n"
            "\n"
            "Read the modem lights first. The PON light shows the fibre link and the LOS "
            "light shows a loss of signal. Steady green PON with no LOS means the fibre is "
            "fine and the fault is elsewhere. A red or blinking LOS light means the fibre "
            "signal is lost, which is a line fault and needs a technician.\n"
            "\n"
            "No internet, lights normal. Restart the modem by unplugging it for 30 seconds "
            "and waiting 3 minutes for it to re-synchronise. If devices connect to Wi-Fi "
            "but have no internet, connect a computer directly to the modem with an "
            "ethernet cable: if that works, the problem is the Wi-Fi, not the line.\n"
            "\n"
            "Slow speeds. Test speed on a wired connection before reporting it, as Wi-Fi "
            "speed depends on distance, walls and interference. Move the modem away from "
            "walls, mirrors and other electronics, keep it off the floor, and use the 5 GHz "
            "band for devices close to it and the 2.4 GHz band for those further away. "
            "Streaming, downloads and other devices on the same line share the bandwidth.\n"
            "\n"
            "Wi-Fi keeps dropping. Change the Wi-Fi channel in the modem interface, which "
            "is reached at 192.168.1.1 with the credentials printed on the modem label. "
            "Neighbouring networks on the same channel are the most common cause in "
            "apartment buildings.\n"
            "\n"
            "Intermittent drops at the same time each day. This usually indicates "
            "congestion or a faulty cable. Note the times and report them, as the pattern "
            "helps the technician find the cause.\n"
            "\n"
            "Before calling support. Note the modem light pattern, whether a wired "
            "connection also fails, when the problem started, and whether it affects all "
            "devices. This lets support skip the basics and diagnose faster."
        ),
        "topnet_business.pdf": (
            "Topnet Business Offers.\n"
            "\n"
            "Business fibre. Topnet Pro 100 (100 Mbps, 150 dinars/month), Pro 200 (200 "
            "Mbps, 220 dinars/month) and Pro 500 (500 Mbps symmetric, 400 dinars/month). "
            "All Pro plans include a fixed public IP address, priority fault handling and "
            "a business-grade router.\n"
            "\n"
            "Uptime commitment. Pro plans carry a 99.5 percent monthly uptime commitment. "
            "A fault is answered within 2 hours and a technician is on site within one "
            "business day. Each full day of outage beyond that is credited at one thirtieth "
            "of the monthly fee.\n"
            "\n"
            "Backup line. A 4G backup that fails over automatically when the fibre drops "
            "costs 40 dinars/month and includes 100 GB. It is recommended for businesses "
            "taking card payments, since a card terminal is unusable without a connection.\n"
            "\n"
            "Hosting and domains. A .tn domain costs 40 dinars/year and a .com 60 "
            "dinars/year. Shared web hosting starts at 15 dinars/month with 10 GB of "
            "storage and business email. A virtual private server starts at 90 "
            "dinars/month.\n"
            "\n"
            "Installation. Business installation is scheduled within 5 business days and is "
            "free on a 24-month commitment. A survey is carried out first where the "
            "building is not already connected, which can add 10 business days.\n"
            "\n"
            "Billing. Business accounts are invoiced monthly with 30-day terms, and a VAT "
            "invoice is issued for every payment. Payment is by bank transfer, standing "
            "order or card."
        ),
        "topnet_installation.docx": (
            "Topnet Installation and Moving Home.\n"
            "\n"
            "Booking an installation. After subscribing, an installation slot is offered "
            "within 5 business days. The appointment is a half-day window, morning or "
            "afternoon, confirmed by SMS the day before. Someone over 18 must be present, "
            "as the technician needs access and a signature.\n"
            "\n"
            "What happens on the day. Installation takes about 2 hours. The technician "
            "runs the fibre from the street cabinet to the property, installs an optical "
            "socket, connects the modem, and tests the line. Where the building already has "
            "an optical socket, the visit takes under an hour.\n"
            "\n"
            "What you need to provide. The technician needs access to the electrical "
            "supply near where the modem will sit, and permission from the building manager "
            "if cabling passes through common areas, which is the most common reason an "
            "installation has to be rescheduled.\n"
            "\n"
            "Where to put the modem. Place it central, high, and in the open. A modem in a "
            "cupboard, behind a television, on the floor or next to a mirror will give poor "
            "Wi-Fi throughout the property regardless of the subscribed speed.\n"
            "\n"
            "Rescheduling and no-shows. Reschedule free of charge up to 24 hours before "
            "the appointment. If nobody is present for the visit, a missed-appointment fee "
            "of 20 dinars applies and a new slot is offered.\n"
            "\n"
            "Moving home. A move within a covered area is free and takes 5 business days; "
            "book it at least 10 days ahead. Take the modem to the new address, as the same "
            "equipment is reused. If the new address has no fibre coverage, the contract can "
            "be cancelled without penalty on proof of the move."
        ),
    },
    # ------------------------------------------------------------------- fiat --
    # A car maker's dealer/aftersales handbook: warranties, servicing, parts.
    "fiat": {
        "fiat_warranty.pdf": (
            "FIAT Vehicle Warranty.\n"
            "Every new FIAT carries a manufacturer warranty of 2 years with unlimited "
            "mileage, starting from the date of delivery to the first owner.\n"
            "The anti-perforation (body corrosion) warranty runs for 8 years. The paint "
            "warranty runs for 3 years.\n"
            "\n"
            "The warranty covers manufacturing and material defects. It does not cover wear "
            "items: brake pads and discs, clutch linings, wiper blades, tyres, bulbs and "
            "filters. It does not cover damage from an accident, misuse, or a modification "
            "not approved by FIAT.\n"
            "\n"
            "The warranty transfers to a new owner free of charge for the remainder of its "
            "term, provided the service book is complete and stamped.\n"
            "\n"
            "An extended warranty may be purchased before the second year expires: 1 extra "
            "year costs 900 dinars, 2 extra years cost 1600 dinars. It cannot be bought "
            "after the original warranty has ended."
        ),
        "fiat_servicing.txt": (
            "FIAT Scheduled Servicing.\n"
            "Petrol engines are serviced every 15000 km or 12 months, whichever comes first. "
            "Diesel engines are serviced every 20000 km or 12 months.\n"
            "\n"
            "An intermediate service costs 180 dinars and covers the engine oil, the oil "
            "filter, and a 20-point inspection. A full service costs 350 dinars and adds the "
            "air filter, the cabin filter, the spark plugs and a brake fluid check.\n"
            "\n"
            "The timing belt must be replaced at 120000 km or after 5 years. This is not "
            "optional: a broken belt destroys the engine and is not covered by the warranty.\n"
            "\n"
            "Missing a scheduled service does not automatically void the warranty, but a "
            "failure caused by the missed maintenance will not be covered. Keep the service "
            "book stamped at every visit.\n"
            "\n"
            "A courtesy car is provided free for any service booked to last more than one day."
        ),
        "fiat_parts_and_repairs.docx": (
            "FIAT Parts and Repairs.\n"
            "Genuine FIAT parts carry their own 2-year warranty when fitted by an authorised "
            "workshop. A part fitted elsewhere carries a 1-year warranty on the part only, "
            "with no cover for the labour.\n"
            "\n"
            "Common parts, indicative prices: front brake pads 140 dinars, brake discs 260 "
            "dinars the pair, clutch kit 780 dinars, alternator 620 dinars, starter motor 540 "
            "dinars, windscreen 480 dinars.\n"
            "\n"
            "Standard workshop labour is 45 dinars per hour. Diagnostics cost 60 dinars, and "
            "this is refunded against the bill if the repair is carried out with us.\n"
            "\n"
            "A part not held in stock is ordered from the central warehouse and arrives within "
            "5 working days. An urgent order arrives in 48 hours for a 90 dinar surcharge.\n"
            "\n"
            "Every repair is guaranteed for 12 months or 20000 km, covering both the part and "
            "the labour."
        ),
        "fiat_roadside_assistance.txt": (
            "FIAT Roadside Assistance.\n"
            "Roadside assistance is included free for the 2 years of the manufacturer "
            "warranty and can be renewed afterwards for 120 dinars per year.\n"
            "\n"
            "Call 80 100 200, free, 24 hours a day and every day of the year. The target "
            "arrival time is 45 minutes in an urban area and 90 minutes elsewhere.\n"
            "\n"
            "It covers: roadside repair, towing to the nearest authorised workshop, a flat "
            "battery, a puncture, a lost key, and running out of fuel (the call-out is "
            "covered, the fuel itself is not).\n"
            "\n"
            "If the vehicle cannot be repaired the same day and you are more than 100 km from "
            "home, a hotel night or the onward journey is covered up to 200 dinars.\n"
            "\n"
            "Assistance is refused for a vehicle being driven without a valid inspection "
            "certificate, or for repeated call-outs for the same unrepaired fault."
        ),
        "fiat_purchase_and_financing.pdf": (
            "FIAT Purchase, Financing and Delivery.\n"
            "A vehicle in stock is delivered within 7 days. A factory order takes 8 to 12 "
            "weeks depending on the model and the options chosen.\n"
            "\n"
            "The order deposit is 10 percent of the price. It is refundable in full if the "
            "delivery deadline given at the order is missed by more than 30 days. It is not "
            "refundable if the customer cancels for their own reasons.\n"
            "\n"
            "Financing runs from 12 to 60 months, with a minimum deposit of 20 percent. The "
            "rate is 7.5 percent per year over 12 to 36 months, and 8.9 percent over 48 to 60 "
            "months. Approval takes 48 hours and requires an ID, the last 3 payslips and a "
            "bank statement.\n"
            "\n"
            "A trade-in is valued free of charge and the offer is held for 15 days.\n"
            "\n"
            "The legal right of withdrawal does not apply to a vehicle ordered to a customer's "
            "own specification."
        ),
    },
    # -------------------------------------------------------------------- utm --
    # A university, not a telco or a bank — so "how much does it cost?" has a
    # different right answer per tenant, and a leak reads as obviously foreign.
    "utm": {
        "utm_programs.pdf": (
            "Universite de Tunis El Manar - Degree Programmes.\n"
            "Undergraduate (Licence) programmes run for 3 years, 6 semesters, 180 ECTS credits.\n"
            "Offered: Computer Science, Electrical Engineering, Mathematics, Physics, Biology, "
            "Economics and Management, Law.\n"
            "\n"
            "Master programmes run for 2 years, 120 ECTS credits, and are split into "
            "research (Master de Recherche) and professional (Master Professionnel) tracks. "
            "The research track requires a thesis defended before a jury; the professional "
            "track requires a 6-month internship and an internship report.\n"
            "\n"
            "Doctoral programmes run for 3 to 5 years and require an enrolled supervisor and "
            "at least one published article before the defence.\n"
            "\n"
            "The academic year runs from mid-September to the end of June, in two semesters. "
            "A semester is 14 teaching weeks plus 3 weeks of examinations."
        ),
        "utm_admissions.txt": (
            "Universite de Tunis El Manar - Admissions.\n"
            "Undergraduate admission is through the national orientation system after the "
            "baccalaureate. Applications open on 1 July and close on 31 July. The minimum "
            "score depends on the programme and is published each year in August.\n"
            "\n"
            "Master admission is by file. The application window is 1 June to 15 July. A file "
            "contains: the Licence diploma, transcripts for all 6 semesters, a CV, and a "
            "motivation letter. Shortlisted candidates are interviewed in early September.\n"
            "\n"
            "International students apply through the Ministry of Higher Education and must "
            "provide an equivalence certificate for their diploma. The equivalence takes "
            "about 8 weeks, so applying before 1 June is strongly advised.\n"
            "\n"
            "Re-enrolment for continuing students runs from 1 September to 30 September and "
            "is done online. A student who misses re-enrolment loses their place for the year."
        ),
        "utm_fees_and_scholarships.docx": (
            "Universite de Tunis El Manar - Fees and Scholarships.\n"
            "Annual registration fees: Licence 60 dinars, Master 80 dinars, Doctorate 100 "
            "dinars. Fees include student insurance and library access.\n"
            "International students pay a supplementary fee of 1000 dinars per year.\n"
            "\n"
            "Payment is made online or at the university treasury during re-enrolment. "
            "Registration is not confirmed until the fee is paid.\n"
            "\n"
            "Scholarships. A merit scholarship of 1200 dinars per year is awarded to students "
            "in the top 10 percent of their cohort. A social scholarship of 800 dinars per "
            "year is available on proof of family income below 800 dinars per month. "
            "Applications for both close on 15 October.\n"
            "\n"
            "University accommodation costs 180 dinars per year and is allocated by distance "
            "from home and family income. Priority goes to students living more than 100 km "
            "from campus."
        ),
        "utm_library.txt": (
            "Universite de Tunis El Manar - Library Rules.\n"
            "Opening hours: Monday to Friday 8am to 6pm, Saturday 9am to 1pm. Closed Sunday "
            "and on public holidays. During the examination period the library stays open "
            "until 10pm on weekdays.\n"
            "\n"
            "Borrowing. A Licence student may borrow 3 books for 14 days. A Master student "
            "may borrow 5 books for 21 days. A doctoral student or member of staff may borrow "
            "10 books for 30 days.\n"
            "\n"
            "A loan can be renewed twice online unless another reader has reserved the book. "
            "Late returns are fined 500 millimes per book per day, capped at 20 dinars. "
            "Borrowing is suspended while a fine is outstanding.\n"
            "\n"
            "Reference works, theses and periodicals are consultation-only and cannot leave "
            "the reading room. A lost book is charged at its replacement cost plus a 10 dinar "
            "processing fee."
        ),
        "utm_it_support.pdf": (
            "Universite de Tunis El Manar - IT Services.\n"
            "Every student receives an account in the form firstname.lastname@utm.com at "
            "enrolment. The initial password must be changed within 7 days or the account is "
            "locked. A locked account is reopened at the IT desk on presentation of a student card.\n"
            "\n"
            "Wi-Fi. The campus network is eduroam. Connect with the full university address "
            "and the account password. Coverage includes all lecture halls, the library and "
            "the student restaurant, but not the residences.\n"
            "\n"
            "Each student has 15 GB of cloud storage and a mailbox of 2 GB. Exceeding the "
            "mailbox quota blocks incoming mail until space is freed.\n"
            "\n"
            "Off-campus access to the digital library requires the university VPN. Request it "
            "from the IT desk; it is granted to Master and doctoral students only.\n"
            "\n"
            "The IT desk is in Building C, room 12, open 9am to 4pm on weekdays. Password "
            "resets are done in person only, never by telephone or email."
        ),
        "utm_examinations.docx": (
            "Universite de Tunis El Manar - Examination Rules.\n"
            "Each semester has a main session and a resit session (session de rattrapage). "
            "A module is passed with a mark of 10 out of 20 or above. A semester is validated "
            "by an overall average of 10 out of 20, with compensation between modules.\n"
            "\n"
            "A student who fails the main session sits the resit session in the same academic "
            "year. The resit mark replaces the original mark only if it is higher.\n"
            "\n"
            "Attendance. More than 3 unjustified absences from a tutorial or practical class "
            "bars the student from the main session for that module; the resit session remains "
            "open to them. A medical certificate must be produced within 48 hours to justify "
            "an absence.\n"
            "\n"
            "Cheating in an examination leads to a disciplinary council and, if confirmed, "
            "exclusion from all sessions for the current year. A second offence leads to "
            "exclusion from the university.\n"
            "\n"
            "Results are published on the student portal within 15 days of the last "
            "examination. A student may request a re-read of their script within 8 days of "
            "publication; only the arithmetic of the mark is rechecked, not the grading itself."
        ),
    },
    # -------------------------------------------------------------- globalnet --
    # An international ISP, priced in dollars rather than dinars/euros like the
    # other tenants — deliberately a different market/currency for isolation.
    "globalnet": {
        "globalnet_plans.txt": (
            "GlobalNet Internet Plans.\n"
            "Home fiber: Home 100 (100 Mbps, 35 dollars/month), Home 300 (300 Mbps, "
            "50 dollars/month), Home Gig (1000 Mbps, 75 dollars/month). All home plans "
            "include a free dual-band Wi-Fi 6 router and unlimited data.\n"
            "A 12-month term waives the 60 dollar installation fee; without a term, "
            "installation costs 60 dollars and the plan is billed month-to-month.\n"
            "Students and seniors qualify for a 15 percent discount on any Home plan "
            "with proof of eligibility submitted through the customer portal."
        ),
        "globalnet_billing.txt": (
            "GlobalNet Billing and Payments.\n"
            "Invoices are issued on the 1st of each month and cover the month ahead. "
            "Payment is due within 14 days, by credit card, bank transfer, or autopay "
            "enrolled in the customer portal.\n"
            "A late payment incurs a 5 dollar fee after 10 days overdue. Service is "
            "suspended after 21 days overdue and fully disconnected after 45 days, at "
            "which point a new installation is required to reconnect.\n"
            "A new subscription can be cancelled for a full refund within 14 days of "
            "activation, provided the router is returned undamaged."
        ),
        "globalnet_support.txt": (
            "GlobalNet Technical Support.\n"
            "Support is available 24/7 by chat in the customer portal and by phone at "
            "1-800-GLOBALNET. Average wait time is under 3 minutes.\n"
            "To reset the router, hold the reset button for 10 seconds until all lights "
            "blink, then wait 3 minutes for it to reconnect. The default network name "
            "and password are printed on the underside of the router.\n"
            "A steady red status light means the fiber signal is down and requires a "
            "technician visit, scheduled within 2 business days at no charge for active "
            "subscribers."
        ),
        "globalnet_installation.pdf": (
            "GlobalNet Installation and Contract Terms.\n"
            "\n"
            "Installation. A standard installation is scheduled within 5 business days "
            "of signup and takes about 90 minutes. The technician runs the fiber line, "
            "installs the router, and tests the connection before leaving.\n"
            "\n"
            "Contract term. Home plans are offered month-to-month or on a 12-month "
            "term. The 12-month term includes free installation and a 5 dollar monthly "
            "discount compared to the month-to-month price.\n"
            "\n"
            "Cancellation notice. Cancelling a month-to-month plan requires 14 days "
            "notice through the customer portal. Cancelling a 12-month term early "
            "incurs an early termination fee of 10 dollars per month remaining, capped "
            "at 100 dollars.\n"
            "\n"
            "Equipment return. The router remains GlobalNet property and must be "
            "returned within 14 days of cancellation using the prepaid shipping label "
            "provided in the portal. An unreturned router is billed at 90 dollars.\n"
            "\n"
            "Moving. A move to a new address within the coverage area is free and "
            "takes 5 business days to reschedule. If the new address is outside "
            "GlobalNet's coverage area, the contract is cancelled without penalty on "
            "proof of the move."
        ),
        "globalnet_business.docx": (
            "GlobalNet Business Internet.\n"
            "\n"
            "Business plans. Business 200 (200 Mbps, 90 dollars/month), Business 500 "
            "(500 Mbps symmetric, 150 dollars/month), and Business Gig (1000 Mbps "
            "symmetric, 220 dollars/month). Every business plan includes a static IP "
            "address and priority support.\n"
            "\n"
            "Service level agreement. Business plans carry a 99.9 percent monthly "
            "uptime commitment. A fault is acknowledged within 1 hour and a technician "
            "is dispatched within 4 business hours. Downtime beyond the SLA is "
            "credited at 5 percent of the monthly fee per hour, up to a full month's "
            "fee.\n"
            "\n"
            "Backup connectivity. An optional 4G failover connection costs 25 "
            "dollars/month and switches over automatically within 60 seconds of a "
            "fiber outage, keeping card payment terminals and point-of-sale systems "
            "online.\n"
            "\n"
            "Billing and contracts. Business accounts are invoiced monthly in arrears "
            "with 30-day payment terms and can be paid by bank transfer or card. "
            "Contracts run 12 or 24 months; the 24-month term reduces the monthly "
            "price by 10 percent."
        ),
    },
}


# A second wave of documents, merged into DOCS below. Kept as its own dict purely so
# the two batches stay readable; the seeder treats them identically. Same rules apply:
# ASCII only (the PDF writer's core fonts are latin-1), and every fact is concrete
# enough that a retrieved answer can be judged right or wrong.
EXTRA_DOCS = {
    # ---------------------------------------------------------------- telecom --
    "telecom": {
        "telecom_coverage.txt": (
            "Telecom Network Coverage and Outages.\n"
            "4G covers 98 percent of the population and 5G covers 62 percent, concentrated in "
            "Tunis, Sfax, Sousse and Nabeul. Rural coverage is guaranteed at a minimum of "
            "3 Mbps under the universal service obligation.\n"
            "Planned maintenance runs between 2am and 5am and is announced 48 hours ahead by "
            "SMS. If an unplanned outage exceeds 24 continuous hours, affected subscribers "
            "receive an automatic credit of one thirtieth of the monthly fee per full day lost. "
            "The credit appears on the next invoice and does not need to be claimed.\n"
            "Outage status is published at status.telecom.com and updated every 30 minutes."
        ),
        "telecom_cancellation.txt": (
            "Telecom Cancellation and Notice Periods.\n"
            "Monthly rolling plans require 30 days written notice. Fixed 12-month and 24-month "
            "contracts may be cancelled early on payment of the remaining monthly fees, capped "
            "at 6 months of the plan price.\n"
            "Cancellation without penalty is possible in three cases: a move to an address with "
            "no coverage, a documented long-term hospital stay, or a price increase applied "
            "mid-contract. In the last case the customer has 30 days from the price change "
            "notice to leave.\n"
            "Number portability to another operator takes 3 working days and is free. The "
            "outgoing operator may not delay it."
        ),
        "telecom_complaints.docx": (
            "Telecom Complaints and Escalation.\n"
            "A complaint may be raised by phone, in a store, or via the mobile app. Every "
            "complaint receives a reference number of the form CMP-YYYY-NNNNNN.\n"
            "Service levels: first response within 2 working days, resolution within 10 working "
            "days. If the 10-day deadline is missed, the complaint escalates automatically to a "
            "supervisor and the customer is credited 10 euros.\n"
            "If the customer is unsatisfied with the outcome, they may escalate to the national "
            "telecoms regulator, but only after 30 days have passed since the complaint was "
            "first raised. Telecom must provide the case file to the regulator within 5 days of "
            "a request."
        ),
        "telecom_app.txt": (
            "Telecom Mobile App.\n"
            "The app allows a customer to view their invoice, check remaining data, top up a "
            "prepaid line, change plan, and report a fault.\n"
            "Data usage in the app is refreshed every 15 minutes and may lag real usage "
            "slightly; the invoice is always authoritative. A plan change made in the app takes "
            "effect on the first day of the next billing cycle, except for an upgrade, which "
            "takes effect immediately with the difference prorated.\n"
            "The app requires the SIM to be active. If a customer is locked out, an SMS reset "
            "code is sent to the registered number and is valid for 10 minutes."
        ),
        "telecom_loyalty.pdf": (
            "Telecom Loyalty Programme.\n"
            "Customers earn 1 point per euro spent on their monthly bill. Points expire 24 "
            "months after they are earned.\n"
            "Redemption: 500 points is worth 5 euros off an invoice, 2000 points can be "
            "exchanged for a handset accessory, and 5000 points for a 50 euro device discount. "
            "Points cannot be exchanged for cash and are not transferable between accounts.\n"
            "Customers on a contract of 24 months or longer earn double points in their first "
            "3 months. A closed account loses its unredeemed points 60 days after closure."
        ),
        "telecom_prepaid.txt": (
            "Telecom Prepaid Top-up.\n"
            "Prepaid credit can be topped up in a store, in the app, or with a scratch card. "
            "The minimum top-up is 5 euros and the maximum single top-up is 100 euros.\n"
            "Credit is valid for 6 months from the last top-up. If no top-up occurs for 6 "
            "months, the line is suspended; the number is released after a further 3 months "
            "and cannot be recovered.\n"
            "Prepaid data packs: 1 GB for 2 euros valid 7 days, 5 GB for 7 euros valid 30 days, "
            "20 GB for 18 euros valid 30 days. Unused pack data does not roll over."
        ),
        "telecom_accessibility.docx": (
            "Telecom Accessibility Services.\n"
            "Customers with a certified disability may request a 20 percent discount on any "
            "mobile plan. The certificate must be renewed every 3 years.\n"
            "A text relay service for deaf and hard-of-hearing customers is available free of "
            "charge on 800-RELAY, 8am to 10pm daily. Invoices can be supplied in large print or "
            "in braille on request, at no cost, with 10 working days notice.\n"
            "Store staff at every location in Tunis, Sfax and Sousse are trained in basic sign "
            "language. A home visit for installation or fault repair can be requested at no "
            "extra charge by customers with reduced mobility."
        ),
    },
    # ---------------------------------------------------------------- ooredoo --
    "ooredoo": {
        "ooredoo_coverage.txt": (
            "Ooredoo Coverage and Network.\n"
            "Ooredoo operates 4G across 96 percent of the population and 5G in Tunis, Ariana, "
            "Sousse and Monastir. Indoor coverage in dense urban areas is supported by small "
            "cells.\n"
            "A customer reporting weak indoor signal may request a free signal booster, subject "
            "to a technical survey. The survey takes up to 10 working days. If the survey finds "
            "no fault on the network side, the booster is offered at 39 dinars instead of free.\n"
            "Network status is available in the My Ooredoo app under Network, refreshed every "
            "hour."
        ),
        "ooredoo_mobile_money.pdf": (
            "Ooredoo Mobile Money.\n"
            "Mobile money lets a customer send and receive funds from their phone. The wallet "
            "limit is 5000 dinars, and the maximum single transfer is 1000 dinars.\n"
            "Fees: transfers to another Ooredoo wallet are free. Transfers to a bank account "
            "cost 1 percent, minimum 0.5 dinars. Cash withdrawal at an agent costs 2 dinars.\n"
            "Identity verification is required above 500 dinars held in the wallet: a national "
            "ID card and a selfie in the app. Verification is normally completed within 24 "
            "hours. A wallet that is inactive for 12 months is frozen and requires a branch "
            "visit to reopen."
        ),
        "ooredoo_family.txt": (
            "Ooredoo Family Plans.\n"
            "A family plan groups up to 5 lines under one invoice. The first line pays full "
            "price, and each additional line receives a 30 percent discount.\n"
            "Data is shared from a single pool: Family 50 (50 GB shared, 45 dinars/month) and "
            "Family 100 (100 GB shared, 70 dinars/month). Any line may be capped individually "
            "by the account owner, which is the standard way to control a child's usage.\n"
            "Adding or removing a line takes effect at the next billing cycle. The account "
            "owner must be over 18 and is legally responsible for the whole invoice."
        ),
        "ooredoo_device_care.docx": (
            "Ooredoo Device Care and Insurance.\n"
            "Device Care costs 7 dinars per month and covers accidental damage, liquid damage "
            "and theft. It must be taken out within 30 days of buying the device.\n"
            "Claims: the excess is 50 dinars for a screen repair and 120 dinars for a full "
            "replacement. Theft claims require a police report filed within 48 hours. A maximum "
            "of 2 claims are allowed in any 12-month period.\n"
            "Repairs are completed within 5 working days, and a loan handset is provided free "
            "while the repair is in progress. Devices older than 36 months are not eligible."
        ),
        "ooredoo_customer_care.txt": (
            "Ooredoo Customer Care Standards.\n"
            "Call centre hours are 8am to 10pm, 7 days a week, on 1200 from an Ooredoo line and "
            "free of charge. Average answer time is targeted at under 90 seconds.\n"
            "In-store appointments can be booked in the app and are held for 15 minutes past "
            "the booked time.\n"
            "A fault reported on a fixed line is diagnosed remotely within 4 hours. If an "
            "engineer visit is needed, it is offered within 3 working days, in a 4-hour window "
            "chosen by the customer. A missed engineer appointment is compensated at 20 dinars."
        ),
        "ooredoo_youth.txt": (
            "Ooredoo Youth and Student Offers.\n"
            "Customers aged 16 to 25 with a valid student card qualify for the Youth plan: "
            "40 GB of data, unlimited calls and SMS, for 22 dinars per month.\n"
            "The plan includes free data for study platforms and campus Wi-Fi roaming at "
            "partner universities. Proof of enrolment must be re-submitted every academic year, "
            "by 31 October; if it lapses, the line reverts to the standard plan at 32 dinars "
            "and the customer is notified 14 days beforehand.\n"
            "A Youth line cannot be part of a family plan pool at the same time."
        ),
        "ooredoo_esim_transfer.docx": (
            "Ooredoo eSIM Transfer Between Devices.\n"
            "An eSIM profile can be moved to a new device up to 3 times per year at no charge. "
            "Additional transfers cost 10 dinars each.\n"
            "The transfer is done in the app: select Manage eSIM, choose Transfer, and scan the "
            "QR code shown on the new device. The old profile is deactivated automatically "
            "after 15 minutes. Both devices must have an internet connection for the transfer.\n"
            "If the old device is lost or broken, the profile can instead be reissued in a "
            "store on presentation of ID. A reissue takes about 20 minutes."
        ),
    },
    # ------------------------------------------------------------------- biat --
    "biat": {
        "biat_mortgages.pdf": (
            "BIAT Mortgages.\n"
            "BIAT lends up to 80 percent of a property's value over a maximum term of 25 years. "
            "The applicant's total monthly repayments may not exceed 40 percent of net income.\n"
            "Rates: fixed at 8.4 percent, or variable at the central bank rate plus 2.1 points. "
            "A rate switch from variable to fixed is allowed once during the life of the loan "
            "for a fee of 300 dinars.\n"
            "Fees: arrangement fee of 1 percent of the amount borrowed, and a mandatory property "
            "valuation costing 400 dinars. Early repayment carries a penalty of 2 percent of the "
            "amount repaid early, waived entirely after year 10."
        ),
        "biat_fees.txt": (
            "BIAT Schedule of Fees.\n"
            "Current account maintenance: 6 dinars per quarter, waived if the average balance "
            "stays above 2000 dinars.\n"
            "Domestic transfer: free in the app, 3 dinars in a branch. International transfer: "
            "0.4 percent of the amount, minimum 25 dinars.\n"
            "Card replacement: 20 dinars, or free if the card was faulty. Emergency replacement "
            "abroad is 90 dinars. A returned direct debit costs 15 dinars. An unarranged "
            "overdraft is charged at 18 percent annually plus a 25 dinar fee, applied once per "
            "month at most.\n"
            "A statement older than 12 months, requested on paper, costs 5 dinars per statement."
        ),
        "biat_business_banking.docx": (
            "BIAT Business Banking.\n"
            "A business account requires the company registration certificate, the tax "
            "identification number, and identification for every director holding more than 25 "
            "percent.\n"
            "Account opening takes 5 to 10 working days. The monthly fee is 25 dinars, and "
            "includes 50 free domestic transfers per month; further transfers cost 1 dinar each.\n"
            "Business overdraft is available up to 3 months of average turnover, subject to "
            "approval, at 11 percent annually. A dedicated relationship manager is assigned to "
            "any business with turnover above 500,000 dinars per year, contactable directly and "
            "with a 1-working-day response commitment."
        ),
        "biat_kyc.txt": (
            "BIAT Know Your Customer Requirements.\n"
            "To open a personal account BIAT requires a valid national ID card or passport, "
            "proof of address dated within the last 3 months, and proof of income or employment.\n"
            "Documents must be re-verified every 5 years, or immediately if the customer's "
            "address, name or employment changes. Failure to update within 60 days of a written "
            "request leads to restrictions: outgoing transfers are blocked, though the account "
            "is not closed and card payments continue.\n"
            "A non-resident account requires additional proof of the source of funds for any "
            "deposit above 20,000 dinars."
        ),
        "biat_travel_forex.pdf": (
            "BIAT Travel and Foreign Exchange.\n"
            "Cards work abroad by default, but BIAT recommends registering travel dates in the "
            "app to avoid a fraud block. A block triggered abroad can be cleared by calling the "
            "24-hour line on 71 340 733.\n"
            "Foreign purchases carry a 2.5 percent currency conversion fee. Cash withdrawal "
            "abroad costs 2.5 percent plus 8 dinars per withdrawal.\n"
            "The travel allowance for tourism is set by the central bank and is 6000 dinars per "
            "adult per calendar year, recorded in the passport. A business travel allowance is "
            "separate and requires a letter from the employer."
        ),
        "biat_savings.txt": (
            "BIAT Savings and Investment.\n"
            "The standard savings account pays 5.2 percent annually, calculated daily and paid "
            "quarterly. There is no minimum balance and withdrawals are unrestricted.\n"
            "A fixed-term deposit pays 7.1 percent for 12 months or 7.8 percent for 24 months, "
            "with a minimum of 5000 dinars. Breaking a fixed term early forfeits all interest "
            "accrued in the current period, though the capital is always returned in full.\n"
            "A youth savings account for under-18s pays 6 percent and requires a parent or "
            "guardian as co-signatory. It converts automatically to a standard account on the "
            "holder's 18th birthday."
        ),
        "biat_complaints.docx": (
            "BIAT Complaints Procedure.\n"
            "Complaints can be made in a branch, by phone, or in writing. BIAT acknowledges a "
            "complaint within 2 working days and responds substantively within 15 working days.\n"
            "A disputed card transaction must be reported within 60 days of the statement on "
            "which it appears. BIAT provisionally re-credits a disputed amount within 10 working "
            "days while it investigates, unless there is reasonable suspicion of fraud by the "
            "customer.\n"
            "If the customer remains unsatisfied after the final response, they may refer the "
            "case to the banking ombudsman at no cost, within 12 months of that response."
        ),
    },
    # ----------------------------------------------------------------- topnet --
    "topnet": {
        "topnet_fair_use.txt": (
            "Topnet Fair Use Policy.\n"
            "Unlimited home plans are subject to fair use. Above 2 TB of traffic in a calendar "
            "month, speeds may be shaped during peak hours, 7pm to 11pm, to protect other users. "
            "Shaping is never applied outside peak hours.\n"
            "Topnet notifies a customer by email once they pass 1.5 TB in a month, as a warning. "
            "Fewer than 1 percent of customers ever reach the threshold.\n"
            "Running a public server on a residential line is not permitted; a business plan "
            "with a static IP is required for that. Repeated breaches after two written warnings "
            "may lead to termination with 30 days notice."
        ),
        "topnet_static_ip.txt": (
            "Topnet Static IP and Business Options.\n"
            "A static IPv4 address costs 15 dinars per month on a residential plan and is "
            "included free on all business plans. A block of 5 static addresses costs 45 dinars "
            "per month.\n"
            "Provisioning takes 2 working days. Reverse DNS can be configured on request at no "
            "charge; the request is handled within 5 working days.\n"
            "Business plans include a service level agreement: 99.7 percent monthly uptime, with "
            "a 4-hour response to a reported fault and a credit of 5 percent of the monthly fee "
            "for each full hour beyond the agreed restoration time, capped at one month's fee."
        ),
        "topnet_tv.docx": (
            "Topnet TV Bundles.\n"
            "TV Basic (80 channels) costs 15 dinars per month, and TV Plus (150 channels, "
            "including sport and cinema) costs 30 dinars per month. Both require an active "
            "internet plan of at least 50 Mbps.\n"
            "The set-top box is loaned free of charge and must be returned within 14 days of "
            "cancellation; an unreturned box is billed at 120 dinars.\n"
            "Recordings are stored in the cloud for 30 days, up to 50 hours. Up to 3 devices may "
            "stream at the same time on TV Plus, and 1 device on TV Basic. Channel line-ups may "
            "change; a customer losing more than 10 percent of channels may cancel TV without "
            "penalty within 30 days."
        ),
        "topnet_moving.txt": (
            "Topnet Moving Home.\n"
            "A move should be notified at least 15 working days in advance, in the app or by "
            "phone. The transfer fee is 40 dinars, waived for customers of more than 24 months.\n"
            "If the new address has fibre coverage, the service is transferred with no change to "
            "the plan or the contract term. If it has only ADSL, the customer may downgrade to "
            "the equivalent ADSL plan and pay the lower price, with no penalty.\n"
            "If the new address has no Topnet coverage at all, the contract is cancelled without "
            "penalty on proof of the move, such as a lease or a deed. The router must be "
            "returned within 14 days."
        ),
        "topnet_hosting.pdf": (
            "Topnet Hosting and Domains.\n"
            "Domain registration for a .tn domain costs 40 dinars per year, and .com costs 45 "
            "dinars per year. Registration is completed within 24 hours of payment.\n"
            "Shared hosting: Starter (10 GB storage, 5 mailboxes, 90 dinars/year) and Pro "
            "(50 GB storage, unlimited mailboxes, 220 dinars/year). Both include a free SSL "
            "certificate renewed automatically.\n"
            "Backups are taken nightly and kept for 14 days. A restore from backup is free once "
            "per month, and 30 dinars for each additional restore. Hosting uptime is targeted at "
            "99.9 percent measured monthly."
        ),
        "topnet_security.docx": (
            "Topnet Account Security.\n"
            "The customer portal supports two-factor authentication by SMS or an authenticator "
            "app. Topnet strongly recommends enabling it; it is mandatory for business accounts.\n"
            "Topnet will never ask for a password, a full card number or a one-time code by "
            "phone or email. Any message doing so is fraudulent and should be reported to "
            "abuse@topnet.tn.\n"
            "A password reset link is valid for 30 minutes and can be used once. After 5 failed "
            "login attempts the account is locked for 15 minutes. A customer who believes their "
            "account is compromised should call 71 234 000, where the account can be frozen "
            "immediately."
        ),
        "topnet_speed.txt": (
            "Topnet Speed and Line Quality.\n"
            "Advertised speeds are the maximum achievable on the line. Topnet guarantees a "
            "minimum of 80 percent of the advertised download speed on fibre, measured over a "
            "wired connection.\n"
            "If a wired speed test taken 3 times on separate days shows less than 80 percent, "
            "the customer may report a fault. If Topnet cannot restore the speed within 30 days, "
            "the customer may downgrade to the matching lower plan and be refunded the "
            "difference for the affected period, or leave without penalty.\n"
            "Wi-Fi speeds are not guaranteed, as they depend on the device, distance and "
            "interference."
        ),
    },
}

# Merge wave two into the main corpus. The seeder is idempotent (it skips a
# company+filename already ingested), so re-running only picks up what is new.
for _company_key, _files in EXTRA_DOCS.items():
    DOCS[_company_key].update(_files)


# --------------------------------------------------------------------------- #
# Writers — author a REAL file of each type (not text with a fake extension)
# --------------------------------------------------------------------------- #
def _write_txt(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _write_docx(path: str, text: str) -> None:
    """One Word paragraph per line; the first line becomes a heading."""
    import docx

    document = docx.Document()
    lines = text.split("\n")
    document.add_heading(lines[0], level=1)
    for line in lines[1:]:
        document.add_paragraph(line)
    document.save(path)


def _write_pdf(path: str, text: str) -> None:
    """A real PDF, laid out with fpdf2's core fonts.

    Core fonts are latin-1 encoded, so the corpus above is kept ASCII — a curly
    quote or a euro symbol would raise here rather than silently mangling the text.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # multi_cell(0, ...) means "as wide as the space to the right margin", and it
    # leaves the cursor at the RIGHT margin afterwards. So the next multi_cell would
    # get roughly zero width and fpdf raises "Not enough horizontal space to render a
    # single character". Reset x to the left margin before every line — previously
    # this only worked by accident, on documents whose blank lines happened to call
    # ln() (which resets x for you).
    def _para(line: str, height: float) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, height, line)

    lines = text.split("\n")
    pdf.set_font("Helvetica", style="B", size=14)
    _para(lines[0], 8)
    pdf.ln(2)

    pdf.set_font("Helvetica", size=11)
    for line in lines[1:]:
        if not line.strip():
            pdf.ln(3)
            continue
        _para(line, 6)
    pdf.output(path)


_WRITERS = {".txt": _write_txt, ".docx": _write_docx, ".pdf": _write_pdf}


def _write_source_file(path: str, text: str) -> None:
    ext = os.path.splitext(path)[1].lower()
    writer = _WRITERS.get(ext)
    if writer is None:
        raise ValueError(f"no writer for extension {ext!r} ({path})")
    writer(path, text)


def _resolve_company(key: str):
    lookup = COMPANY_LOOKUP[key]
    if "name" in lookup:
        return Company.query.filter_by(name=lookup["name"]).first()
    return Company.query.filter_by(domain=lookup["domain"]).first()


def seed_docs():
    # Attribute these seeded ingestions to the super_admin (audit trail needs a
    # real user id — KbIngestion.user_id is a non-null FK).
    actor = User.query.filter_by(role="super_admin").first()
    if actor is None:
        actor = User.query.first()
    if actor is None:
        print("  ! no users found — run app.seed first; aborting")
        return

    total_docs = 0
    total_chunks = 0
    by_ext = {}
    for key, files in DOCS.items():
        company = _resolve_company(key)
        if company is None:
            print(f"  ! no company for '{key}' — run app.seed first; skipping")
            continue

        out_dir = os.path.join(SAMPLE_DIR, key)
        os.makedirs(out_dir, exist_ok=True)

        for filename, text in files.items():
            path = os.path.join(out_dir, filename)
            # Always (re)write the readable source file, in its real format.
            _write_source_file(path, text)

            # Skip if this file is already in this company's KB (idempotent).
            already = Document.query.filter_by(
                company_id=company.id, filename=filename, scope="kb"
            ).first()
            if already is not None:
                print(f"  = {company.name}: '{filename}' already ingested — skipping")
                continue

            # Read the file back off disk and parse it with the SAME extractor the
            # /ingest endpoint uses. This is the point of writing real PDFs and Word
            # files: what lands in Qdrant is what pypdf / python-docx actually
            # recover, not the pristine string above. A PDF's text comes back with
            # its own line breaks, so the indexed chunks are honest.
            with open(path, "rb") as fh:
                raw = fh.read()
            try:
                extracted = extract.extract_text(filename, raw)
            except extract.ExtractionError as e:
                print(f"  ! {company.name}: '{filename}' could not be parsed ({e}) — skipping")
                continue

            # Screen every chunk — never index unfiltered content.
            passing, blocked = [], 0
            for chunk in chunking.chunk_text(extracted):
                verdict = screening.screen_chunk(chunk, company_id=company.id)
                if verdict["action"] == "blocked":
                    blocked += 1
                    continue
                passing.append(verdict["text"])
            if not passing:
                print(f"  ! {company.name}: '{filename}' fully blocked — skipping")
                continue

            document = Document(
                company_id=company.id, filename=filename,
                scope="kb", status="ingested",
            )
            db.session.add(document)
            db.session.flush()

            indexed = rag.index_chunks(
                company.id, passing,
                base_payload={"filename": filename, "document_id": document.id, "source": "kb"},
            )
            db.session.add(KbIngestion(
                company_id=company.id, document_id=document.id, user_id=actor.id,
                filename=filename, chunks_indexed=indexed, chunks_blocked=blocked,
            ))
            db.session.commit()

            ext = os.path.splitext(filename)[1].lower()
            by_ext[ext] = by_ext.get(ext, 0) + 1
            total_docs += 1
            total_chunks += indexed
            note = f" ({blocked} blocked)" if blocked else ""
            print(f"  + {company.name} ({company.qdrant_collection}): '{filename}' -> {indexed} chunk(s){note}")

    formats = ", ".join(f"{n} {ext}" for ext, n in sorted(by_ext.items())) or "none"
    print(f"\nDone: ingested {total_docs} document(s) [{formats}], {total_chunks} chunk(s) into Qdrant.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_docs()
