from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any


GRANTS_FILE = (
    Path(__file__).resolve().parent
    / "json_data"
    / "grants.json"
)

BACKUP_FILE = (
    Path(__file__).resolve().parent
    / "json_data"
    / "grants_before_startup_curation.json"
)

TODAY = date.today()


def funding(
    funding_type: str,
    *,
    maximum_amount: int | None = None,
    minimum_amount: int | None = None,
    currency: str | None = "INR",
) -> dict[str, Any]:
    return {
        "minimum_amount": minimum_amount,
        "maximum_amount": maximum_amount,
        "currency": currency,
        "funding_type": funding_type,
    }


def eligibility(
    *,
    stages: list[str],
    industries: list[str],
    locations: list[str],
    company: list[str] | None = None,
    applicant: list[str] | None = None,
    exclusions: list[str] | None = None,
) -> dict[str, list[str]]:
    return {
        "startup_stages": stages,
        "industries": industries,
        "allowed_locations": locations,
        "company_requirements": company or [],
        "applicant_requirements": applicant or [],
        "exclusions": exclusions or [],
    }


def application(
    *,
    url: str | None,
    open_date: str | None = None,
    deadline: str | None = None,
    documents: list[str] | None = None,
    steps: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "open_date": open_date,
        "deadline": deadline,
        "application_url": url,
        "required_documents": documents or [],
        "application_steps": steps or [],
    }


def normalized_status(
    status: str,
    *,
    open_date: str | None,
    deadline: str | None,
) -> str:
    if deadline and date.fromisoformat(deadline) < TODAY:
        return "inactive"

    if open_date and date.fromisoformat(open_date) > TODAY:
        return "upcoming"

    return status


def opportunity(
    *,
    grant_id: str,
    name: str,
    provider_name: str,
    provider_type: str,
    description: str,
    funding_details: dict[str, Any],
    eligibility_details: dict[str, list[str]],
    application_details: dict[str, Any],
    status: str,
    source: str,
) -> dict[str, Any]:
    return {
        "_id": grant_id,
        "type": "funding_opportunity",
        "grant_name": name,
        "provider": {
            "name": provider_name,
            "type": provider_type,
        },
        "description": description,
        "funding": funding_details,
        "eligibility": eligibility_details,
        "application": application_details,
        "status": normalized_status(
            status,
            open_date=application_details["open_date"],
            deadline=application_details["deadline"],
        ),
        "source": source,
    }


COMMON_STARTUP_DOCS = [
    "Company incorporation certificate or registration proof",
    "Founder identity and address proof",
    "Pitch deck or business plan",
    "Product or prototype description",
    "Use-of-funds plan",
    "Financial projections or recent financial statements",
]


CURATED_GRANTS = [
    opportunity(
        grant_id="startup-india-seed-fund-scheme",
        name="Startup India Seed Fund Scheme (SISFS)",
        provider_name="Department for Promotion of Industry and Internal Trade (DPIIT)",
        provider_type="government",
        description=(
            "Seed support through approved incubators for proof of concept, prototype "
            "development, product trials, market entry, and commercialization."
        ),
        funding_details=funding(
            "seed_funding",
            maximum_amount=5000000,
        ),
        eligibility_details=eligibility(
            stages=["idea", "prototype", "mvp", "early-stage"],
            industries=[
                "technology",
                "deep technology",
                "healthcare",
                "agriculture",
                "education",
                "financial inclusion",
                "energy",
                "mobility",
                "defence",
                "space",
                "waste management",
                "water management",
            ],
            locations=["India"],
            company=[
                "Startup must be recognized by DPIIT.",
                "Startup must generally be incorporated not more than two years before application.",
                "Startup should use technology in its product, service, business model, distribution model, or methodology.",
                "Indian promoters should hold at least 51 percent shareholding at the time of application.",
                "Startup should not have received more than INR 10 lakh of monetary support under another Central or State Government scheme, excluding permitted non-cash or prize support.",
            ],
            applicant=[
                "Founders should apply through the Startup India Seed Fund portal and select eligible incubators.",
            ],
            exclusions=[
                "Physical application submission is not required.",
                "Incubators should not charge application, selection, disbursement, incubation, or monitoring fees to selected startups.",
            ],
        ),
        application_details=application(
            url="https://seedfund.startupindia.gov.in/",
            open_date="2021-04-19",
            deadline="2026-05-31",
            documents=COMMON_STARTUP_DOCS
            + [
                "DPIIT recognition certificate",
                "PAN and GST details, if applicable",
                "Startup video describing product, service, or business model, if requested",
            ],
            steps=[
                "Register or log in on the Startup India Seed Fund portal.",
                "Complete the online startup application.",
                "Choose up to three approved incubators in preference order.",
                "Submit team, problem, product, market, business model, funding need, and utilization details.",
                "Track incubator evaluation and selection status online.",
            ],
        ),
        status="active",
        source="https://seedfund.startupindia.gov.in/",
    ),
    opportunity(
        grant_id="startup-india-credit-guarantee-scheme",
        name="Credit Guarantee Scheme for Startups (CGSS)",
        provider_name="Department for Promotion of Industry and Internal Trade (DPIIT)",
        provider_type="government",
        description=(
            "Credit guarantee support for loans extended by member institutions to "
            "eligible DPIIT-recognized startups."
        ),
        funding_details=funding(
            "loan",
            maximum_amount=200000000,
        ),
        eligibility_details=eligibility(
            stages=["early-stage", "growth", "scale-up"],
            industries=["all sectors", "technology", "manufacturing", "services"],
            locations=["India"],
            company=[
                "Startup must be recognized by DPIIT.",
                "Startup must not be in default to any lending or investing institution.",
                "Startup must not be classified as a non-performing asset under RBI guidelines.",
                "Eligibility must be certified by the member institution providing credit.",
            ],
        ),
        application_details=application(
            url="https://www.startupindia.gov.in/content/sih/en/credit-guarantee-scheme-for-startups.html",
            documents=COMMON_STARTUP_DOCS
            + [
                "DPIIT recognition certificate",
                "Loan application and lender-requested credit documents",
                "Bank statements and financial statements",
            ],
            steps=[
                "Check eligibility with a participating member institution.",
                "Submit startup and credit details to the lender.",
                "Lender evaluates credit and certifies eligibility for guarantee cover.",
                "Loan is processed under the applicable CGSS framework.",
            ],
        ),
        status="active",
        source="https://www.startupindia.gov.in/content/sih/en/credit-guarantee-scheme-for-startups.html",
    ),
    opportunity(
        grant_id="startup-india-investor-connect",
        name="Startup India Investor Connect",
        provider_name="Startup India",
        provider_type="government",
        description=(
            "National platform that helps startups connect with investors for equity "
            "and growth funding conversations."
        ),
        funding_details=funding(
            "equity_investment",
            currency="INR",
        ),
        eligibility_details=eligibility(
            stages=["seed", "early-stage", "growth", "scale-up"],
            industries=["all sectors", "technology", "deep technology", "consumer", "enterprise"],
            locations=["India"],
            company=[
                "Startup should maintain a complete profile and fundraising information.",
                "DPIIT recognition is preferred for Startup India ecosystem benefits.",
            ],
            applicant=[
                "Founder should be ready with investor-facing materials and traction details.",
            ],
        ),
        application_details=application(
            url="https://investorconnect.startupindia.gov.in/",
            documents=[
                "Pitch deck",
                "Company profile",
                "Cap table summary",
                "Fundraising ask and use-of-funds plan",
                "Traction metrics",
            ],
            steps=[
                "Create or update the startup profile.",
                "Upload investor-facing material.",
                "Submit interest through the Investor Connect platform.",
                "Respond to investor screening and follow-up requests.",
            ],
        ),
        status="active",
        source="https://investorconnect.startupindia.gov.in/",
    ),
    opportunity(
        grant_id="birac-biotechnology-ignition-grant",
        name="Biotechnology Ignition Grant (BIG)",
        provider_name="Biotechnology Industry Research Assistance Council (BIRAC)",
        provider_type="government",
        description=(
            "Early-stage grant-in-aid for biotech startups and innovators to translate "
            "innovative ideas into proof of concept."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=5000000,
        ),
        eligibility_details=eligibility(
            stages=["idea", "prototype", "proof-of-concept"],
            industries=[
                "biotechnology",
                "healthcare",
                "medtech",
                "agriculture",
                "life sciences",
                "bioindustrial",
            ],
            locations=["India"],
            company=[
                "Proposal should have biotechnology or life-sciences innovation with commercialization potential.",
                "Startup or innovator should be able to work with a BIG partner for mentoring and monitoring.",
            ],
            applicant=[
                "Applicant should be able to submit a technical proposal and commercialization plan.",
            ],
        ),
        application_details=application(
            url="https://birac.nic.in/big.php",
            documents=[
                "BIG proposal format",
                "Technical project plan",
                "Commercialization plan",
                "Budget and milestone plan",
                "Founder or team credentials",
                "IP or novelty statement, if applicable",
            ],
            steps=[
                "Watch for the regular January and July BIRAC BIG calls.",
                "Register or log in on the BIRAC application system.",
                "Prepare the BIG proposal using the official format.",
                "Submit the proposal before the call closes.",
                "Selected applicants work with BIG partners for mentoring and monitoring.",
            ],
        ),
        status="active",
        source="https://birac.nic.in/big.php",
    ),
    opportunity(
        grant_id="birac-seed-fund",
        name="BIRAC Sustainable Entrepreneurship and Enterprise Development (SEED) Fund",
        provider_name="Biotechnology Industry Research Assistance Council (BIRAC)",
        provider_type="government",
        description=(
            "Post-proof-of-concept seed support through BioNEST incubator partners to "
            "help biotech startups become angel-investment ready."
        ),
        funding_details=funding(
            "equity_investment",
            maximum_amount=3000000,
        ),
        eligibility_details=eligibility(
            stages=["post-proof-of-concept", "mvp", "early-stage"],
            industries=["biotechnology", "life sciences", "healthcare", "agritech", "medtech"],
            locations=["India"],
            company=[
                "Startup should be a biotech or life-sciences startup at post-proof-of-concept stage.",
                "Startup should apply through a BIRAC SEED Fund Partner BioNEST incubator.",
                "Startup should need bridge capital before angel or venture investment.",
            ],
        ),
        application_details=application(
            url="https://birac.nic.in/seedFundNew.php",
            documents=COMMON_STARTUP_DOCS
            + [
                "Proof-of-concept evidence",
                "Incubator recommendation or partner process documents",
                "Milestone-based utilization plan",
            ],
            steps=[
                "Identify an eligible BIRAC SEED Fund Partner BioNEST incubator.",
                "Submit startup and project details through the partner process.",
                "Complete screening, pitching, and due diligence.",
                "Execute investment and monitoring documents after selection.",
            ],
        ),
        status="active",
        source="https://birac.nic.in/seedFundNew.php",
    ),
    opportunity(
        grant_id="birac-leap-fund",
        name="BIRAC Launching Entrepreneurial Driven Affordable Products (LEAP) Fund",
        provider_name="Biotechnology Industry Research Assistance Council (BIRAC)",
        provider_type="government",
        description=(
            "Equity-linked support through selected BioNEST partners for biotech "
            "startups moving from proof of concept to pilot and commercialization."
        ),
        funding_details=funding(
            "equity_investment",
        ),
        eligibility_details=eligibility(
            stages=["proof-of-concept", "pilot", "commercialization", "early-stage"],
            industries=["biotechnology", "life sciences", "healthcare", "agritech", "medtech"],
            locations=["India"],
            company=[
                "Startup should have a biotech product or technology ready for pilot or commercialization.",
                "Startup should apply through a BIRAC LEAP Fund partner.",
                "Startup should be suitable for follow-on angel or venture funding.",
            ],
        ),
        application_details=application(
            url="https://birac.nic.in/leapFundNew.php",
            documents=COMMON_STARTUP_DOCS
            + [
                "Pilot or commercialization plan",
                "Customer validation or product-readiness evidence",
                "Financial and investment-readiness details",
            ],
            steps=[
                "Contact an eligible BIRAC LEAP Fund partner.",
                "Submit startup, technology, and commercialization details.",
                "Complete partner screening and investment due diligence.",
                "Execute investment and milestone-monitoring documents after selection.",
            ],
        ),
        status="active",
        source="https://birac.nic.in/leapFundNew.php",
    ),
    opportunity(
        grant_id="birac-sbiri",
        name="Small Business Innovation Research Initiative (SBIRI)",
        provider_name="Biotechnology Industry Research Assistance Council (BIRAC)",
        provider_type="government",
        description=(
            "Support for early-stage and pre-proof-of-concept biotechnology research "
            "by companies, LLPs, and eligible industry-academia collaborations."
        ),
        funding_details=funding("grant"),
        eligibility_details=eligibility(
            stages=["research", "pre-proof-of-concept", "prototype"],
            industries=["biotechnology", "healthcare", "food and nutrition", "agriculture", "life sciences"],
            locations=["India"],
            company=[
                "Applicant may be a company incorporated under the Companies Act, 2013.",
                "Applicant may be an LLP incorporated under the Limited Liability Partnership Act, 2008.",
                "Company should have at least 51 percent ownership by Indian citizens where applicable.",
                "Applicant should have adequate in-house facilities or be incubated at a recognized incubation facility.",
            ],
            applicant=[
                "Academic collaborators may include Indian universities, colleges, national research laboratories, or eligible not-for-profit research institutions.",
            ],
        ),
        application_details=application(
            url="https://birac.nic.in/desc_new.php?id=217",
            open_date="2026-09-01",
            deadline="2026-10-15",
            documents=[
                "SBIRI proposal",
                "Company or LLP incorporation documents",
                "Shareholding certificate",
                "Project budget",
                "In-house R&D or incubation proof",
                "Collaborator documents, if applicable",
            ],
            steps=[
                "Use the regular SBIRI call window when open.",
                "Prepare the proposal and supporting documents using BIRAC formats.",
                "Submit through the BIRAC proposal system.",
                "Complete technical, financial, and eligibility review.",
            ],
        ),
        status="active",
        source="https://birac.nic.in/desc_new.php?id=217",
    ),
    opportunity(
        grant_id="idex-disc-12-re-open-2026",
        name="iDEX Defence India Startup Challenge DISC 12 Re Open",
        provider_name="Defence Innovation Organisation - iDEX",
        provider_type="government",
        description=(
            "Challenge grant for startups, MSMEs, and innovators building defence and "
            "national-security prototypes or commercialization-ready solutions."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=15000000,
        ),
        eligibility_details=eligibility(
            stages=["prototype", "mvp", "early-stage", "commercialization"],
            industries=["defence", "aerospace", "security", "deep technology", "robotics", "artificial intelligence"],
            locations=["India"],
            company=[
                "Applicant should be a startup, MSME, or innovator eligible under iDEX challenge rules.",
                "Solution should address the listed defence problem statement.",
            ],
        ),
        application_details=application(
            url="https://idex.gov.in/challenges",
            deadline="2026-07-15",
            documents=[
                "Challenge proposal",
                "Pitch deck",
                "Prototype or technology description",
                "Team details",
                "Budget and milestone plan",
                "Company registration documents, if applicable",
            ],
            steps=[
                "Open the iDEX challenges portal.",
                "Select DISC 12 Re Open.",
                "Review the problem statement and grant terms.",
                "Submit the proposal and supporting documents before the deadline.",
            ],
        ),
        status="active",
        source="https://idex.gov.in/challenges",
    ),
    opportunity(
        grant_id="idex-open-challenge-2026",
        name="iDEX Open Challenge 2026",
        provider_name="Defence Innovation Organisation - iDEX",
        provider_type="government",
        description=(
            "Open challenge route for startups, MSMEs, and innovators proposing "
            "defence and security solutions outside a narrow predefined problem statement."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=15000000,
        ),
        eligibility_details=eligibility(
            stages=["prototype", "mvp", "early-stage", "commercialization"],
            industries=["defence", "aerospace", "security", "deep technology", "robotics", "artificial intelligence"],
            locations=["India"],
            company=[
                "Applicant should be a startup, MSME, or innovator eligible under iDEX challenge rules.",
                "Solution should be relevant to national defence or security use cases.",
            ],
        ),
        application_details=application(
            url="https://idex.gov.in/challenges",
            deadline="2026-06-30",
            documents=[
                "Open challenge proposal",
                "Pitch deck",
                "Prototype or technology description",
                "Team details",
                "Budget and milestone plan",
                "Company registration documents, if applicable",
            ],
            steps=[
                "Open the iDEX challenges portal.",
                "Select Open Challenge.",
                "Review the instructions and eligibility criteria.",
                "Submit the proposal before the deadline.",
            ],
        ),
        status="active",
        source="https://idex.gov.in/challenges",
    ),
    opportunity(
        grant_id="ksum-innovation-grant",
        name="Kerala Startup Mission Innovation Grant",
        provider_name="Kerala Startup Mission",
        provider_type="government",
        description=(
            "Stage-wise grant support for idea, productization, scale-up, market "
            "acceleration, student innovators, and women or transgender founders."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=1500000,
        ),
        eligibility_details=eligibility(
            stages=["idea", "prototype", "mvp", "early-stage", "scale-up"],
            industries=["technology", "deep technology", "hardware", "software", "social impact"],
            locations=["Kerala", "India"],
            company=[
                "For idea grants, the innovator may be based in or outside Kerala, but incorporation and KSUM unique ID are mandatory for fund disbursement.",
                "For other grants, startup should have completed company incorporation and KSUM unique ID certification.",
            ],
        ),
        application_details=application(
            url="https://grants.startupmission.in/",
            documents=COMMON_STARTUP_DOCS
            + [
                "KSUM unique ID, where required",
                "Company incorporation documents, where required",
            ],
            steps=[
                "Apply through the KSUM grant portal when the grant round is open.",
                "Submit complete application and supporting documents.",
                "KSUM screens applications and may run pre-evaluation if volume is high.",
                "Shortlisted startups attend final evaluation.",
            ],
        ),
        status="active",
        source="https://startupmission.kerala.gov.in/schemes/innovation-grant",
    ),
    opportunity(
        grant_id="ksum-seed-fund",
        name="Kerala Startup Mission Seed Fund",
        provider_name="Kerala Startup Mission",
        provider_type="government",
        description=(
            "Soft loan seed support for Kerala startups to support product development, "
            "customer development, marketing, and scale-up."
        ),
        funding_details=funding(
            "loan",
            maximum_amount=1500000,
        ),
        eligibility_details=eligibility(
            stages=["prototype", "mvp", "early-stage"],
            industries=["technology", "hardware", "software", "deep technology"],
            locations=["Kerala"],
            company=[
                "Startup should be registered in Kerala as an LLP or Private Limited Company.",
                "Startup should have an active KSUM Unique ID.",
                "Startup should have DPIIT registration and active or active-compliant MCA status.",
                "Startup should work on an innovative product or technology.",
            ],
            exclusions=[
                "The scheme is generally not for service startups or SMEs working only in trade and commerce.",
                "The fund cannot be used for founders' salaries, costly assets, or patenting expenses.",
            ],
        ),
        application_details=application(
            url="https://startups.startupmission.in/",
            documents=COMMON_STARTUP_DOCS
            + [
                "KSUM Unique ID",
                "DPIIT registration",
                "Final pitch deck",
                "Fund utilization plan",
                "Project milestones and timeline",
            ],
            steps=[
                "Submit the online seed fund application through KSUM.",
                "Complete initial evaluation and one-to-one screening call.",
                "Attend initial and final pitching rounds.",
                "Submit requested documents and execute agreements after selection.",
                "Receive disbursement in installments based on milestones.",
            ],
        ),
        status="active",
        source="https://startupmission.kerala.gov.in/schemes/seed-fund",
    ),
    opportunity(
        grant_id="ksum-rd-grant",
        name="Kerala Startup Mission R&D Grant",
        provider_name="Kerala Startup Mission",
        provider_type="government",
        description=(
            "Grant support for hardware startups with significant R&D components and "
            "working prototypes."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=3000000,
        ),
        eligibility_details=eligibility(
            stages=["prototype", "mvp", "early-stage", "scale-up"],
            industries=["hardware", "deep technology", "electronics", "iot", "medtech", "manufacturing"],
            locations=["Kerala"],
            company=[
                "Startup should have a working prototype.",
                "Startup should be a member of at least one approved incubator in Kerala.",
                "At least 50 percent of the grant should be used for hardware.",
                "Not more than 20 percent should be used for marketing expenses.",
            ],
            exclusions=[
                "R&D grants cannot be used to cover manpower or hiring costs.",
            ],
        ),
        application_details=application(
            url="https://startupmission.kerala.gov.in/schemes/rd-grant",
            documents=[
                "Business plan",
                "Prototype details",
                "Incubator membership proof",
                "R&D budget",
                "Patent details, if applicable",
                "Scale-up or product plan",
            ],
            steps=[
                "Apply through the KSUM process when intake is open.",
                "Submit business plan and R&D budget.",
                "Complete screening and final evaluation.",
                "Use funds according to hardware and marketing limits after approval.",
            ],
        ),
        status="active",
        source="https://startupmission.kerala.gov.in/schemes/rd-grant",
    ),
    opportunity(
        grant_id="ksum-technology-commercialisation-support",
        name="Kerala Startup Mission Technology Transfer and Commercialisation Support",
        provider_name="Kerala Startup Mission",
        provider_type="government",
        description=(
            "Reimbursement support for startups that license technology from Indian "
            "government research institutions and develop it into a commercial product."
        ),
        funding_details=funding(
            "financial_assistance",
            maximum_amount=1000000,
        ),
        eligibility_details=eligibility(
            stages=["technology-transfer", "product-development", "commercialization"],
            industries=["technology", "deep technology", "research commercialization"],
            locations=["Kerala"],
            company=[
                "Startup should be registered in Kerala as an LLP or Private Limited Company.",
                "Startup should have active KSUM registration.",
                "Startup should have DPIIT registration and active or active-compliant MCA status.",
                "Startup should have purchased or sourced a technology license from a Government research institution in India.",
            ],
            applicant=[
                "Startup is expected to commercialize the licensed product within two years.",
            ],
            exclusions=[
                "Support is limited to eligible technology transfer costs.",
                "Startup should not have pending dues with government agencies, KSUM, or incubators.",
            ],
        ),
        application_details=application(
            url="https://startupmission.kerala.gov.in/schemes/technology-commercialisation",
            documents=[
                "Invoice and receipt from research organization",
                "Bank statement showing technology fee transfer",
                "Technology transfer agreement",
                "Company incorporation documents",
                "Director or applicant residence proof",
                "No-duplicate-reimbursement undertaking",
                "Canceled cheque and company bank details",
            ],
            steps=[
                "Submit online application.",
                "Submit required hard-copy documents where requested.",
                "Complete KSUM review and documentation.",
                "Receive reimbursement support after approval.",
            ],
        ),
        status="active",
        source="https://startupmission.kerala.gov.in/schemes/technology-commercialisation",
    ),
    opportunity(
        grant_id="startup-odisha-monthly-allowance",
        name="Startup Odisha Monthly Allowance for Recognized Startups",
        provider_name="Startup Odisha",
        provider_type="government",
        description=(
            "Monthly allowance for recognized Odisha startups that meet innovation, "
            "funding, patent, grant, or revenue criteria."
        ),
        funding_details=funding(
            "financial_assistance",
            maximum_amount=264000,
        ),
        eligibility_details=eligibility(
            stages=["prototype", "mvp", "early-stage"],
            industries=["all sectors", "social impact", "clean energy", "agriculture", "healthcare", "financial inclusion"],
            locations=["Odisha"],
            company=[
                "Startup must be recognized under Startup Odisha.",
                "If not registered in Odisha, startup should employ at least 50 percent of its qualified workforce in Odisha.",
                "Startup should satisfy one of the listed financing, patent, grant, or revenue conditions.",
            ],
            applicant=[
                "Women, transgender, SC, ST, SEBC, or PH founder categories with at least 50 percent equity may receive enhanced support.",
            ],
        ),
        application_details=application(
            url="https://startupodisha.gov.in/startup-incentives/",
            documents=COMMON_STARTUP_DOCS
            + [
                "Startup Odisha recognition proof",
                "Proof of qualifying equity funding, patent, grant, or revenue run rate",
                "Founder category proof, if claiming enhanced allowance",
            ],
            steps=[
                "Apply for Startup Odisha recognition.",
                "After recognition, submit the monetary benefit application online.",
                "Nodal agency reviews and forwards recommendation.",
                "Startup Secretariat conducts due diligence and places the case before the Task Force.",
                "Approved allowance is paid to the startup bank account.",
            ],
        ),
        status="active",
        source="https://startupodisha.gov.in/startup-incentives/",
    ),
    opportunity(
        grant_id="startup-odisha-product-development-marketing-assistance",
        name="Startup Odisha Product Development and Marketing Assistance",
        provider_name="Startup Odisha",
        provider_type="government",
        description=(
            "Grant assistance for recognized Odisha startups introducing innovative "
            "products into the market."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=1600000,
        ),
        eligibility_details=eligibility(
            stages=["mvp", "early-stage", "market-entry"],
            industries=["all sectors", "social impact", "clean energy", "agriculture", "healthcare", "financial inclusion"],
            locations=["Odisha"],
            company=[
                "Startup must be recognized under Startup Odisha.",
                "Startup should meet qualifying funding, grant, or revenue conditions.",
                "Assistance should be for product development, marketing, or publicity of an innovative product.",
            ],
            applicant=[
                "Women, transgender, SC, ST, SEBC, or PH founder categories with at least 50 percent equity may receive enhanced support.",
            ],
        ),
        application_details=application(
            url="https://startupodisha.gov.in/startup-incentives/",
            documents=COMMON_STARTUP_DOCS
            + [
                "Startup Odisha recognition proof",
                "Product development plan",
                "Marketing or publicity plan",
                "Proof of qualifying funding, grant, or revenue run rate",
                "Utilization certificate and bills after disbursement",
            ],
            steps=[
                "Apply online for financial benefit after Startup Odisha recognition.",
                "Submit product development and marketing plan.",
                "Complete nodal agency review and Startup Secretariat due diligence.",
                "Receive approval from the Task Force.",
                "Submit utilization documents for advance and final payment milestones.",
            ],
        ),
        status="active",
        source="https://startupodisha.gov.in/startup-incentives/",
    ),
    opportunity(
        grant_id="startup-odisha-need-based-assistance",
        name="Startup Odisha Need-Based Assistance",
        provider_name="Startup Odisha",
        provider_type="government",
        description=(
            "Case-by-case support for raw materials, components, equipment, and other "
            "inputs needed for innovative product development or product improvement."
        ),
        funding_details=funding("financial_assistance"),
        eligibility_details=eligibility(
            stages=["prototype", "mvp", "product-development", "early-stage"],
            industries=["all sectors", "manufacturing", "hardware", "deep technology", "agriculture", "clean energy"],
            locations=["Odisha"],
            company=[
                "Startup must be recognized under Startup Odisha.",
                "Assistance must relate to an innovation-dependent requirement for raw material, components, or equipment.",
                "Support is subject to Startup Council approval.",
            ],
        ),
        application_details=application(
            url="https://startupodisha.gov.in/startup-incentives/",
            documents=[
                "Startup Odisha recognition proof",
                "Self-contained need and utilization plan",
                "Quotations or cost estimates",
                "Innovation justification",
                "Utilization certificate and bills after support is received",
            ],
            steps=[
                "Apply online with a need-based assistance plan.",
                "Explain the innovation dependency and proposed utilization.",
                "Complete review and council approval.",
                "Submit utilization documents within the required period after support.",
            ],
        ),
        status="active",
        source="https://startupodisha.gov.in/startup-incentives/",
    ),
    opportunity(
        grant_id="nsf-americas-seed-fund-sbir-sttr",
        name="America's Seed Fund powered by NSF (SBIR/STTR)",
        provider_name="U.S. National Science Foundation",
        provider_type="government",
        description=(
            "Non-dilutive seed funding for U.S. startups developing deep technologies "
            "with commercial potential."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=2000000,
            currency="USD",
        ),
        eligibility_details=eligibility(
            stages=["research", "prototype", "mvp", "early-stage"],
            industries=[
                "artificial intelligence",
                "energy",
                "medical devices",
                "robotics",
                "semiconductors",
                "deep technology",
                "advanced manufacturing",
            ],
            locations=["United States"],
            company=[
                "Company should be a for-profit entity located in the United States.",
                "Company should meet SBIR/STTR small-business eligibility rules.",
                "Technology should be innovative, technically risky, and commercially promising.",
            ],
        ),
        application_details=application(
            url="https://seedfund.nsf.gov/",
            documents=[
                "Project pitch",
                "Full proposal, if invited",
                "Company registration and ownership details",
                "Technical work plan",
                "Commercialization plan",
                "Budget and biosketches",
            ],
            steps=[
                "Review NSF funding topic areas.",
                "Submit a Project Pitch.",
                "If invited, prepare and submit the full proposal.",
                "Complete NSF review and award process.",
            ],
        ),
        status="active",
        source="https://seedfund.nsf.gov/",
    ),
    opportunity(
        grant_id="us-sbir-sttr-federal-program",
        name="U.S. SBIR/STTR Federal Program",
        provider_name="U.S. Small Business Administration",
        provider_type="government",
        description=(
            "Federal small-business R&D funding program across participating U.S. "
            "agencies, with Phase I proof-of-concept and Phase II R&D awards."
        ),
        funding_details=funding(
            "grant",
            minimum_amount=50000,
            maximum_amount=1800000,
            currency="USD",
        ),
        eligibility_details=eligibility(
            stages=["research", "proof-of-concept", "prototype", "early-stage"],
            industries=["deep technology", "healthcare", "energy", "defence", "space", "education", "environment"],
            locations=["United States"],
            company=[
                "Company should be a for-profit entity located in the United States.",
                "Company should generally have fewer than 500 employees.",
                "Company should meet U.S. ownership and control requirements.",
                "Company needs a Unique Entity ID from SAM.gov to receive awards.",
            ],
        ),
        application_details=application(
            url="https://www.sbir.gov/apply",
            documents=[
                "Agency-specific solicitation response",
                "Technical proposal",
                "Commercialization plan",
                "Budget",
                "SAM.gov and UEI registration details",
                "Company ownership and employee details",
            ],
            steps=[
                "Search topics and solicitations on SBIR.gov or agency sites.",
                "Read the full agency solicitation.",
                "Confirm eligibility and registration requirements.",
                "Submit proposal through the agency's SBIR/STTR process before the closing date.",
            ],
        ),
        status="active",
        source="https://www.sbir.gov/apply",
    ),
    opportunity(
        grant_id="grants-gov-federal-opportunities",
        name="Grants.gov Federal Grant Opportunities",
        provider_name="Grants.gov",
        provider_type="government",
        description=(
            "Search portal for U.S. federal grant opportunities across agencies, useful "
            "for startups, nonprofits, research teams, and small businesses where eligible."
        ),
        funding_details=funding(
            "grant",
            currency="USD",
        ),
        eligibility_details=eligibility(
            stages=["idea", "research", "prototype", "early-stage", "growth"],
            industries=["all sectors", "research", "technology", "healthcare", "environment", "education"],
            locations=["United States"],
            company=[
                "Eligibility depends on each federal funding opportunity announcement.",
                "Applicant should verify whether small businesses or for-profit entities are eligible.",
                "Applicant may need SAM.gov registration and Grants.gov workspace access.",
            ],
        ),
        application_details=application(
            url="https://www.grants.gov/search-grants",
            documents=[
                "Opportunity-specific forms",
                "SAM.gov registration",
                "Budget",
                "Project narrative",
                "Eligibility and organization documents",
            ],
            steps=[
                "Search Grants.gov by keyword, agency, category, and eligibility.",
                "Read the full funding opportunity announcement.",
                "Confirm applicant eligibility and deadline.",
                "Apply through Grants.gov Workspace or the specified agency process.",
            ],
        ),
        status="active",
        source="https://www.grants.gov/search-grants",
    ),
    opportunity(
        grant_id="eic-accelerator-2026",
        name="EIC Accelerator 2026",
        provider_name="European Innovation Council",
        provider_type="international",
        description=(
            "European deep-tech and breakthrough-innovation funding for startups and "
            "SMEs, combining grant funding with possible equity investment."
        ),
        funding_details=funding(
            "grant",
            maximum_amount=2500000,
            currency="EUR",
        ),
        eligibility_details=eligibility(
            stages=["prototype", "pilot", "scale-up", "growth"],
            industries=["deep technology", "healthcare", "climate", "energy", "digital", "industrial technology"],
            locations=["European Union", "Horizon Europe associated countries"],
            company=[
                "Single startups and SMEs may apply.",
                "Individuals intending to launch an SME may apply under the programme rules.",
                "Small mid-caps may apply for equity-only support where eligible.",
                "Innovation should be high-risk, high-potential, and capable of creating or disrupting markets.",
            ],
        ),
        application_details=application(
            url="https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en",
            documents=[
                "Short proposal or platform submission",
                "Full proposal",
                "Pitch deck",
                "Business plan",
                "Financial information",
                "Freedom-to-operate or IP details, if applicable",
            ],
            steps=[
                "Review EIC Accelerator Open or Challenge fit.",
                "Submit the short application where required.",
                "Prepare the full proposal and pitch materials if invited or eligible.",
                "Complete remote evaluation and interview stages.",
            ],
        ),
        status="active",
        source="https://eic.ec.europa.eu/eic-funding-opportunities/eic-accelerator_en",
    ),
    opportunity(
        grant_id="stand-up-india-loan",
        name="Stand-Up India Loan Scheme",
        provider_name="Small Industries Development Bank of India and participating banks",
        provider_type="government",
        description=(
            "Bank loan support for SC, ST, and women entrepreneurs setting up greenfield "
            "enterprises in manufacturing, services, trading, or agri-allied activities."
        ),
        funding_details=funding(
            "loan",
            minimum_amount=1000000,
            maximum_amount=10000000,
        ),
        eligibility_details=eligibility(
            stages=["idea", "early-stage"],
            industries=["manufacturing", "services", "trading", "agri-allied"],
            locations=["India"],
            company=[
                "Enterprise should be a greenfield venture.",
                "For non-individual enterprises, at least 51 percent shareholding and controlling stake should be held by SC, ST, or woman entrepreneur.",
            ],
            applicant=[
                "Applicant should be an SC, ST, or woman entrepreneur above 18 years.",
            ],
        ),
        application_details=application(
            url="https://www.standupmitra.in/",
            documents=[
                "Applicant identity and category proof",
                "Business plan",
                "Project cost and loan requirement",
                "Bank-requested KYC and financial documents",
                "Enterprise registration documents, if already incorporated",
            ],
            steps=[
                "Apply through the Stand-Up India portal or participating bank branch.",
                "Complete borrower and project details.",
                "Coordinate with the selected bank and handholding agency, if needed.",
                "Complete bank appraisal and sanction process.",
            ],
        ),
        status="active",
        source="https://www.standupmitra.in/",
    ),
    opportunity(
        grant_id="ambedkar-social-innovation-incubation-mission",
        name="Ambedkar Social Innovation and Incubation Mission (ASIIM)",
        provider_name="Ministry of Social Justice and Empowerment",
        provider_type="government",
        description=(
            "Equity-style support and handholding for SC youth, SC differently abled "
            "entrepreneurs, and social-innovation startups identified through incubators, "
            "hackathons, or CSR-supported pathways."
        ),
        funding_details=funding(
            "equity_investment",
            maximum_amount=3000000,
        ),
        eligibility_details=eligibility(
            stages=["idea", "prototype", "mvp", "early-stage"],
            industries=["social impact", "technology", "education", "healthcare", "livelihoods"],
            locations=["India"],
            company=[
                "Selected venture may need to incorporate as a Private Limited or Public Limited company before receiving support.",
                "SC entrepreneur should hold at least 51 percent shareholding and management control where applicable.",
            ],
            applicant=[
                "SC students, SC differently abled youth, or SC entrepreneurs identified through eligible incubators, hackathons, or CSR-supported pathways.",
            ],
            exclusions=[
                "Investments in RBI negative sectors are not eligible.",
            ],
        ),
        application_details=application(
            url="https://www.myscheme.gov.in/schemes/asiim",
            documents=[
                "Proof of SC or SC differently abled status",
                "Company incorporation documents, where applicable",
                "Shareholding pattern",
                "Incubator or selection proof",
                "Innovation proposal",
            ],
            steps=[
                "Apply through the official process or eligible incubator route.",
                "Submit proof of category, selection pathway, and startup idea.",
                "Complete selection and incubation review.",
                "Incorporate or restructure the entity if required before disbursement.",
            ],
        ),
        status="unknown",
        source="https://www.myscheme.gov.in/schemes/asiim",
    ),
    opportunity(
        grant_id="uttarakhand-startup-policy-2023",
        name="Uttarakhand Startup Policy 2023 Incentives",
        provider_name="Startup Uttarakhand",
        provider_type="government",
        description=(
            "State startup policy portal for recognition, policy benefits, seed funding "
            "events, IP support, public procurement support, and startup challenges."
        ),
        funding_details=funding("seed_funding"),
        eligibility_details=eligibility(
            stages=["idea", "prototype", "mvp", "early-stage", "growth"],
            industries=["technology", "tourism", "agriculture", "healthcare", "sustainability", "manufacturing"],
            locations=["Uttarakhand"],
            company=[
                "Startup should meet Uttarakhand Startup Policy and Government of India startup definition requirements.",
                "Startup should have or establish office and substantial operations in Uttarakhand where required.",
            ],
        ),
        application_details=application(
            url="https://startuputtarakhand.uk.gov.in/",
            documents=COMMON_STARTUP_DOCS
            + [
                "Startup recognition details",
                "Policy benefit or challenge-specific documents",
            ],
            steps=[
                "Register on the Startup Uttarakhand portal.",
                "Apply for recognition or the relevant policy benefit.",
                "Submit required documents for the chosen incentive, challenge, or support program.",
                "Track application status through the portal.",
            ],
        ),
        status="active",
        source="https://startuputtarakhand.uk.gov.in/",
    ),
]


def main() -> None:
    if not GRANTS_FILE.exists():
        raise FileNotFoundError(f"Missing grants file: {GRANTS_FILE}")

    if not BACKUP_FILE.exists():
        shutil.copy2(GRANTS_FILE, BACKUP_FILE)

    sorted_grants = sorted(
        CURATED_GRANTS,
        key=lambda grant: grant["grant_name"].lower(),
    )

    dataset = {
        "docs": sorted_grants,
    }

    temporary_file = GRANTS_FILE.with_suffix(".json.tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            dataset,
            file,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        file.write("\n")

    temporary_file.replace(GRANTS_FILE)

    print(f"Curated records: {len(sorted_grants)}")
    print(f"Updated: {GRANTS_FILE}")
    print(f"Backup: {BACKUP_FILE}")


if __name__ == "__main__":
    main()
