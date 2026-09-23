# Copyright (c) 2026, Functional Demo Team and Contributors
# License: GNU General Public License (v3). See LICENSE

import frappe
from frappe import _

from functional_demo.portal import consultant_of_user, portal_context

MODULES = [
	"", "Law Management", "Hospitality", "Medical Store", "Retail & Supermarket",
	"Manufacturing", "Education", "Healthcare", "Real Estate", "Logistics & Transport",
	"Agriculture", "IT Services", "Banking & Finance", "Food & Beverage",
	"Construction", "Energy & Utilities", "Other",
]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
DEMO_TYPES = ["Standard Demo", "Customized Demo", "Walkthrough", "Deep Dive", "Follow-up Demo"]

# Lead Location: each state lists its districts. Tamil Nadu is fully listed
# (38 districts); other states include their major districts.
STATES_DISTRICTS = {
	"Tamil Nadu": [
		"Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
		"Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kanchipuram",
		"Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai",
		"Nagapattinam", "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai",
		"Ramanathapuram", "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur",
		"Theni", "Thiruvallur", "Thiruvarur", "Thoothukudi", "Tiruchirappalli",
		"Tirunelveli", "Tirupathur", "Tiruppur", "Tiruvannamalai", "Vellore",
		"Villupuram", "Virudhunagar",
	],
	"Andhra Pradesh": [
		"Anantapur", "Chittoor", "East Godavari", "Guntur", "Krishna", "Kurnool",
		"Prakasam", "Srikakulam", "Sri Potti Sriramulu Nellore", "Visakhapatnam",
		"Vizianagaram", "West Godavari", "YSR Kadapa",
	],
	"Karnataka": [
		"Bagalkot", "Ballari", "Belagavi", "Bengaluru Rural", "Bengaluru Urban",
		"Bidar", "Chamarajanagar", "Chikkaballapur", "Chikkamagaluru",
		"Chitradurga", "Dakshina Kannada", "Davanagere", "Dharwad", "Gadag",
		"Hassan", "Haveri", "Kalaburagi", "Kodagu", "Kolar", "Koppal", "Mandya",
		"Mysuru", "Raichur", "Ramanagara", "Shivamogga", "Tumakuru", "Udupi",
		"Uttara Kannada", "Vijayapura", "Yadgir",
	],
	"Kerala": [
		"Alappuzha", "Ernakulam", "Idukki", "Kannur", "Kasaragod", "Kollam",
		"Kottayam", "Kozhikode", "Malappuram", "Palakkad", "Pathanamthitta",
		"Thiruvananthapuram", "Thrissur", "Wayanad",
	],
	"Telangana": [
		"Adilabad", "Bhadradri Kothagudem", "Hanumakonda", "Hyderabad",
		"Jagtial", "Jangaon", "Jayashankar Bhupalpally", "Jogulamba Gadwal",
		"Kamareddy", "Karimnagar", "Khammam", "Kumaram Bheem Asifabad",
		"Mahabubabad", "Mahabubnagar", "Mancherial", "Medak",
		"Medchal-Malkajgiri", "Mulugu", "Nagarkurnool", "Nalgonda", "Narayanpet",
		"Nirmal", "Nizamabad", "Peddapalli", "Rajanna Sircilla", "Ranga Reddy",
		"Sangareddy", "Siddipet", "Suryapet", "Vikarabad", "Wanaparthy",
		"Warangal", "Yadadri Bhuvanagiri",
	],
	"Maharashtra": [
		"Ahmednagar", "Akola", "Amravati", "Aurangabad", "Beed", "Bhandara",
		"Buldhana", "Chandrapur", "Dhule", "Gadchiroli", "Gondia", "Hingoli",
		"Jalgaon", "Jalna", "Kolhapur", "Latur", "Mumbai City",
		"Mumbai Suburban", "Nagpur", "Nanded", "Nandurbar", "Nashik", "Osmanabad",
		"Palghar", "Parbhani", "Pune", "Raigad", "Ratnagiri", "Sangli", "Satara",
		"Sindhudurg", "Solapur", "Thane", "Wardha", "Washim", "Yavatmal",
	],
	"Delhi": [
		"Central Delhi", "East Delhi", "New Delhi", "North Delhi",
		"North East Delhi", "North West Delhi", "Shahdara", "South Delhi",
		"South East Delhi", "South West Delhi", "West Delhi",
	],
	"Gujarat": [
		"Ahmedabad", "Amreli", "Anand", "Aravalli", "Banaskantha", "Bharuch",
		"Bhavnagar", "Botad", "Chhota Udaipur", "Dahod", "Dangs", "Devbhoomi Dwarka",
		"Gandhinagar", "Gir Somnath", "Jamnagar", "Junagadh", "Kheda", "Kutch",
		"Mahisagar", "Mehsana", "Morbi", "Narmada", "Navsari", "Panchmahal",
		"Patan", "Porbandar", "Rajkot", "Sabarkantha", "Surat", "Surendranagar",
		"Tapi", "Vadodara", "Valsad",
	],
	"Rajasthan": [
		"Ajmer", "Alwar", "Banswara", "Baran", "Barmer", "Bharatpur", "Bhilwara",
		"Bikaner", "Bundi", "Chittorgarh", "Churu", "Dausa", "Dholpur",
		"Dungarpur", "Hanumangarh", "Jaipur", "Jaisalmer", "Jalore", "Jhalawar",
		"Jhunjhunu", "Jodhpur", "Karauli", "Kota", "Nagaur", "Pali", "Pratapgarh",
		"Rajsamand", "Sawai Madhopur", "Sikar", "Sirohi", "Sri Ganganagar",
		"Tonk", "Udaipur",
	],
	"Uttar Pradesh": [
		"Agra", "Aligarh", "Ambedkar Nagar", "Amethi", "Amroha", "Auraiya",
		"Azamgarh", "Baghpat", "Bahraich", "Ballia", "Balrampur", "Banda",
		"Barabanki", "Bareilly", "Basti", "Bhadohi", "Bijnor", "Budaun",
		"Bulandshahr", "Chandauli", "Chitrakoot", "Deoria", "Etah", "Etawah",
		"Ayodhya", "Farrukhabad", "Fatehpur", "Firozabad", "Gautam Buddha Nagar",
		"Ghaziabad", "Ghazipur", "Gonda", "Gorakhpur", "Hamirpur", "Hapur",
		"Hardoi", "Hathras", "Jalaun", "Jaunpur", "Jhansi", "Kannauj",
		"Kanpur Dehat", "Kanpur Nagar", "Kasganj", "Kaushambi", "Kheri",
		"Kushinagar", "Lalitpur", "Lucknow", "Maharajganj", "Mahoba", "Mainpuri",
		"Mathura", "Mau", "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar",
		"Pilibhit", "Pratapgarh", "Prayagraj", "Raebareli", "Rampur", "Saharanpur",
		"Sambhal", "Sant Kabir Nagar", "Shahjahanpur", "Shamli", "Shravasti",
		"Siddharthnagar", "Sitapur", "Sonbhadra", "Sultanpur", "Unnao", "Varanasi",
	],
	"Madhya Pradesh": [
		"Alirajpur", "Anuppur", "Ashoknagar", "Balaghat", "Barwani", "Betul",
		"Bhind", "Bhopal", "Burhanpur", "Chhatarpur", "Chhindwara", "Damoh",
		"Datia", "Dewas", "Dhar", "Dindori", "Guna", "Gwalior", "Harda",
		"Hoshangabad", "Indore", "Jabalpur", "Jhabua", "Katni", "Khandwa",
		"Khargone", "Mandla", "Mandsaur", "Morena", "Narsinghpur", "Neemuch",
		"Niwari", "Panna", "Raisen", "Rajgarh", "Ratlam", "Rewa", "Sagar",
		"Satna", "Sehore", "Seoni", "Shahdol", "Shajapur", "Sheopur", "Shivpuri",
		"Sidhi", "Singrauli", "Tikamgarh", "Ujjain", "Umaria", "Vidisha",
	],
	"West Bengal": [
		"Alipurduar", "Bankura", "Birbhum", "Cooch Behar", "Dakshin Dinajpur",
		"Darjeeling", "Hooghly", "Howrah", "Jalpaiguri", "Jhargram", "Kalimpong",
		"Kolkata", "Malda", "Murshidabad", "Nadia", "North 24 Parganas",
		"Paschim Bardhaman", "Paschim Medinipur", "Purba Bardhaman",
		"Purba Medinipur", "Purulia", "South 24 Parganas", "Uttar Dinajpur",
	],
	"Bihar": [
		"Araria", "Arwal", "Aurangabad", "Banka", "Begusarai", "Bhagalpur",
		"Bhojpur", "Buxar", "Darbhanga", "East Champaran", "Gaya", "Gopalganj",
		"Jamui", "Jehanabad", "Kaimur", "Katihar", "Khagaria", "Kishanganj",
		"Lakhisarai", "Madhepura", "Madhubani", "Munger", "Muzaffarpur",
		"Nalanda", "Nawada", "Patna", "Purnia", "Rohtas", "Saharsa", "Samastipur",
		"Saran", "Sheikhpura", "Sheohar", "Sitamarhi", "Siwan", "Supaul",
		"Vaishali", "West Champaran",
	],
	"Punjab": [
		"Amritsar", "Barnala", "Bathinda", "Faridkot", "Fatehgarh Sahib",
		"Fazilka", "Ferozepur", "Gurdaspur", "Hoshiarpur", "Jalandhar",
		"Kapurthala", "Ludhiana", "Mansa", "Moga", "Mohali", "Muktsar",
		"Pathankot", "Patiala", "Rupnagar", "Sangrur", "Shaheed Bhagat Singh Nagar",
		"Tarn Taran",
	],
	"Haryana": [
		"Ambala", "Bhiwani", "Charkhi Dadri", "Faridabad", "Fatehabad", "Gurugram",
		"Hisar", "Jhajjar", "Jind", "Kaithal", "Karnal", "Kurukshetra", "Mahendragarh",
		"Nuh", "Palwal", "Panchkula", "Panipat", "Rewari", "Rohtak", "Sirsa",
		"Sonipat", "Yamunanagar",
	],
	"Odisha": [
		"Angul", "Balangir", "Balasore", "Bargarh", "Bhadrak", "Boudh", "Cuttack",
		"Deogarh", "Dhenkanal", "Gajapati", "Ganjam", "Jagatsinghpur", "Jajpur",
		"Jharsuguda", "Kalahandi", "Kandhamal", "Kendrapara", "Kendujhar",
		"Khordha", "Koraput", "Malkangiri", "Mayurbhanj", "Nabarangpur",
		"Nayagarh", "Nuapada", "Puri", "Rayagada", "Sambalpur", "Subarnapur",
		"Sundargarh",
	],
	"Assam": [
		"Baksa", "Barpeta", "Biswanath", "Bongaigaon", "Cachar", "Charaideo",
		"Chirang", "Darrang", "Dhemaji", "Dhubri", "Dibrugarh", "Dima Hasao",
		"Goalpara", "Golaghat", "Hailakandi", "Hojai", "Jorhat", "Kamrup",
		"Kamrup Metropolitan", "Karbi Anglong", "Karimganj", "Kokrajhar",
		"Lakhimpur", "Majuli", "Morigaon", "Nagaon", "Nalbari", "Sivasagar",
		"Sonitpur", "South Salmara-Mankachar", "Tinsukia", "Udalguri", "West Karbi Anglong",
	],
	"Chhattisgarh": [
		"Balod", "Baloda Bazar", "Balrampur", "Bastar", "Bemetara", "Bijapur",
		"Bilaspur", "Dantewada", "Dhamtari", "Durg", "Gariaband", "Gaurela-Pendra-Marwahi",
		"Janjgir-Champa", "Jashpur", "Kabirdham", "Kanker", "Kondagaon", "Korba",
		"Korea", "Mahasamund", "Mungeli", "Narayanpur", "Raigarh", "Raipur",
		"Rajnandgaon", "Sukma", "Surajpur", "Surguja",
	],
	"Jharkhand": [
		"Bokaro", "Chatra", "Deoghar", "Dhanbad", "Dumka", "East Singhbhum",
		"Garhwa", "Giridih", "Godda", "Gumla", "Hazaribagh", "Jamtara", "Khunti",
		"Koderma", "Latehar", "Lohardaga", "Pakur", "Palamu", "Ramgarh",
		"Ranchi", "Sahebganj", "Seraikela-Kharsawan", "Simdega", "West Singhbhum",
	],
	"Goa": ["North Goa", "South Goa"],
	"Other": [],
}


def _consultants_with_templates():
	"""Active consultants with their templates (child table) for dropdowns."""
	_consultants = frappe.get_all(
		"Functional Consultant",
		fields=["name", "consultant_name", "specialization", "availability", "experience_years", "status"],
		order_by="consultant_name asc",
		ignore_permissions=True,
	) or []
	consultants = [c for c in _consultants if (c.get("status") or "") != "Inactive"]
	names = [c["name"] for c in consultants]
	if names:
		templates = {}
		for row in frappe.get_all(
			"Consultant Module",
			filters={"parent": ["in", names]},
			fields=["parent", "module"],
		):
			templates.setdefault(row.parent, []).append(row.module)
		for c in consultants:
			c["modules"] = templates.get(c["name"]) or []
	return consultants


def get_context(context):
	portal_context(
		context,
		_("Demo Request"),
		["Sales User", "Sales Manager", "Functional Team Manager"],
		active="requests",
		subtitle=_("Create or review a demo request"),
	)
	name = frappe.form_dict.get("name") or ""
	context.create_mode = bool(frappe.form_dict.get("new") == "1" or not name)
	context.modules = MODULES
	context.priorities = PRIORITIES
	context.demo_types = DEMO_TYPES
	context.states_districts = STATES_DISTRICTS

	if context.create_mode:
		context.lead_param = frappe.form_dict.get("lead") or ""
		# sales_person is auto-set to the logged-in user — no dropdown needed
		context.current_user = frappe.session.user
		context.current_user_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
		context.customers = frappe.get_all(
			"Customer",
			fields=["name", "customer_name"],
			order_by="creation desc",
			limit_page_length=200,
		) or []
		context.companies = frappe.get_all("Company", fields=["name"], order_by="name asc") or []
		# Functional Consultant is mandatory when creating a demo request
		# If the current user is Administrator, make sure at least one consultant
		# record exists (the auto-created admin profile) so the dropdown is never
		# empty for the site admin - a common cause of the recurring
		# 'Consultant Required' error when testing the portal.
		consultant_of_user()  # side effect: auto-creates the Administrator profile

		# Availability is filtered in Python: an unset status is stored as NULL
		# and SQL status filters would silently hide those consultants.
		context.consultants = _consultants_with_templates()
		# One-click pre-fill: arriving from My Leads (?lead=), a customer
		# (?customer=) or an ERPNext Opportunity (?opportunity=) pulls the
		# contact / company details from the CRM record into the form.
		context.prefill = _lead_opportunity_prefill()
		return context

	# get_doc applies the app's row-level + document-level permissions automatically
	doc = frappe.get_doc("Demo Request", name)
	context.doc = doc
	context.activity = doc.get("demo_request_activity") or []
	context.session_name = frappe.db.get_value(
		"Demo Session",
		{"demo_request": doc.name, "demo_status": ["in", ["Scheduled", "In Progress"]]},
		"name",
	)
	context.consultants = _consultants_with_templates()
	context.consultant_names = {c["name"]: c["consultant_name"] for c in context.consultants}
	# A follow-up already exists for this request - the Create Follow-up
	# button must not show again (no duplicate follow-ups).
	context.has_follow_up = bool(
		frappe.db.exists("Demo Follow Up", {"demo_request": doc.name})
	)
	# Resolve the functional consultant's display name and email so the
	# template can show "Consultant" instead of the raw sales_person link.
	if doc.functional_consultant:
		c_info = frappe.db.get_value(
			"Functional Consultant", doc.functional_consultant,
			["consultant_name", "email"], as_dict=True,
		)
		context.consultant_display = (
			(c_info.consultant_name or "") + (" \u2014 " + c_info.email if c_info and c_info.email else "")
			if c_info else context.consultant_names.get(doc.functional_consultant, "")
		)
	else:
		context.consultant_display = ""
	# Resolve the sales person's display name from the User record
	if doc.sales_person:
		context.sales_person_name = frappe.db.get_value("User", doc.sales_person, "full_name") or doc.sales_person
	else:
		context.sales_person_name = ""
	return context


def _lead_opportunity_prefill():
	"""Resolve the party + contact details to pre-fill when the create form is
	opened from a Customer or an Opportunity."""
	prefill = {
		"customer": "",
		"company": "",
		"contact_person": "",
		"contact_number": "",
		"email": "",
	}
	opportunity = frappe.form_dict.get("opportunity") or ""
	customer = frappe.form_dict.get("customer") or ""

	if opportunity and frappe.db.exists("Opportunity", opportunity):
		opp = frappe.db.get_value(
			"Opportunity",
			opportunity,
			["opportunity_from", "party_name", "lead", "contact_person", "contact_email", "contact_mobile", "company"],
			as_dict=True,
		)
		if opp:
			if opp.get("opportunity_from") == "Lead" and opp.get("lead"):
				# Opportunity linked to a Lead — skip lead prefill, just get company
				pass
			elif opp.get("party_name"):
				prefill["customer"] = opp.get("party_name")
			if frappe.db.exists("Company", opp.get("company") or ""):
				prefill["company"] = opp.get("company") or ""
			if opp.get("contact_person"):
				prefill["contact_person"] = opp.get("contact_person")
			if opp.get("contact_email"):
				prefill["email"] = opp.get("contact_email")
			if opp.get("contact_mobile"):
				prefill["contact_number"] = opp.get("contact_mobile")
	elif customer and frappe.db.exists("Customer", customer):
		prefill["customer"] = customer

	return prefill
