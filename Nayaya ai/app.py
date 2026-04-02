from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from thefuzz import process, fuzz
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId
from datetime import datetime
from flask_wtf.csrf import CSRFProtect, CSRFError

app = Flask(__name__)
app.secret_key = "nyaya_ai_ultra_secure_key"

# Initialize CSRF protection
# csrf = CSRFProtect(app)  # Disabled CSRF protection

# 2. DATABASE CONNECTIONS
DB_PATH = os.path.join(app.root_path, "IndiaLaw.db")
try:
    # Use 127.0.0.1 for local Python connection
    client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
    db = client["NyayaAI_DB"]
    users_collection = db["users"]
    client.server_info() 
except Exception as e:
    print(f"ERROR: MongoDB connection failed: {e}")

# 3. USER MODEL AND LOADER




# --- ROUTES ---



# --- FIR LOGIC (SQLite) ---

# Optional CORS support
try:
    from flask_cors import CORS
    CORS(app)
except ModuleNotFoundError:
    print("Warning: flask_cors not installed. API will still work from same origin.")

# Indian Districts and Police Stations
INDIAN_DISTRICTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Puducherry", "Chandigarh"
]

SAMPLE_POLICE_STATIONS = {
    "Delhi": ["North Delhi PS", "South Delhi PS", "East Delhi PS", "West Delhi PS", "Central Delhi PS"],
    "Maharashtra": ["Mumbai North PS", "Mumbai South PS", "Pune PS", "Nagpur PS"],
    "Karnataka": ["Bangalore PS", "Mysore PS", "Hubli PS"],
    "Tamil Nadu": ["Chennai PS", "Coimbatore PS", "Madurai PS"],
    "Uttar Pradesh": ["Lucknow PS", "Kanpur PS", "Varanasi PS"]
}

LEGAL_ACTS = ["IPC", "CRPC", "NIA", "IEA", "HMA", "CPC", "IDA", "MVA"]

def init_fir_table():
    """Initialize FIR records table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fir_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fir_no TEXT UNIQUE NOT NULL,
                dist TEXT NOT NULL,
                ps TEXT NOT NULL,
                year TEXT NOT NULL,
                fir_date TEXT NOT NULL,
                act_sections TEXT,
                occurrence_day TEXT,
                occurrence_date TEXT,
                occurrence_time TEXT,
                info_received_date TEXT,
                info_received_time TEXT,
                gdr_entry_no TEXT,
                type_of_information TEXT,
                place_of_occurrence TEXT,
                complainant_name TEXT,
                father_husband_name TEXT,
                dob TEXT,
                nationality TEXT,
                passport_no TEXT,
                date_of_issue TEXT,
                place_of_issue TEXT,
                occupation TEXT,
                address TEXT,
                details_of_accused TEXT,
                reasons_for_delay TEXT,
                property_particulars TEXT,
                statement TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Active'
            )
        ''')
        conn.commit()
        conn.close()
        print("FIR records table initialized successfully.")
    except Exception as e:
        print(f"Error initializing FIR table: {e}")

def init_user_table():
    """Initialize users table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'police',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print("Users table initialized successfully.")
    except Exception as e:
        print(f"Error initializing users table: {e}")
        
def init_evidence_table():
    """Create a table to store paths to uploaded evidence files."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
CREATE TABLE IF NOT EXISTS evidence_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fir_no TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fir_no) REFERENCES fir_records (fir_no)
    )
    ''')
    conn.commit()
    conn.close()

# Call this in your if __name__ == '__main__': block
        

def analyze_complaint_for_sections(complaint_text):
    """AI-powered analysis to suggest relevant legal sections based on complaint."""
    if not complaint_text:
        return []

    complaint_lower = complaint_text.lower()

    # Special override: stolen documents are treated differently
    # 1. Define 'Smart' Categories for Fuzzy Matching
    categories = {
    "theft robbery stealing snatched pickpocket burglary": 
        ["IPC Section 378", "IPC Section 379", "IPC Section 380", "IPC Section 381", "IPC Section 392"],

    "assault beaten hit slapped attack injured fight": 
        ["IPC Section 319", "IPC Section 321", "IPC Section 323", "IPC Section 324", "IPC Section 325", "IPC Section 352"],

    "fraud cheating scam forged fake money deception": 
        ["IPC Section 415", "IPC Section 417", "IPC Section 418", "IPC Section 420", "IPC Section 468", "IPC Section 471"],

    "threaten kill intimidation scary criminal intimidation": 
        ["IPC Section 503", "IPC Section 506", "IPC Section 507"],

    "harassment abuse molestation insult woman stalking": 
        ["IPC Section 354", "IPC Section 354A", "IPC Section 354D", "IPC Section 509"],

    "kidnap kidnapping abduct missing child": 
        ["IPC Section 359", "IPC Section 360", "IPC Section 361", "IPC Section 363"],

    "rape sexual assault force sex": 
        ["IPC Section 375", "IPC Section 376"],

    "murder kill homicide death": 
        ["IPC Section 299", "IPC Section 300", "IPC Section 302"],

    "attempt murder try kill attack weapon": 
        ["IPC Section 307"],

    "dowry cruelty husband family harassment": 
        ["IPC Section 498A", "IPC Section 304B"],

    "property damage vandalism destroy property": 
        ["IPC Section 425", "IPC Section 426", "IPC Section 427"],

    "trespass illegal entry house breaking": 
        ["IPC Section 441", "IPC Section 447", "IPC Section 448"],

    "cyber fraud online scam hacking identity theft": 
        ["IT Act Section 43", "IT Act Section 66", "IT Act Section 66C", "IT Act Section 66D"],

    "defamation insult reputation false statement": 
        ["IPC Section 499", "IPC Section 500"],

    "bribery corruption public servant illegal money": 
        ["Prevention of Corruption Act Section 7", "Prevention of Corruption Act Section 13"]
}

    suggested_sections = []

    # 2. Run Fuzzy Logic (Tolerance for typos/synonyms)
    for category_keywords, sections in categories.items():
        # Score of 100 is exact, 70+ is a strong likely match
        if fuzz.partial_ratio(category_keywords, complaint_lower) > 70:
            suggested_sections.extend(sections)

    # 3. Handle Lost Documents (Special Case)
    doc_keywords = "passport aadhar license id card certificate voter"
    if fuzz.partial_ratio(doc_keywords, complaint_lower) > 80 and not suggested_sections:
        return ['Non-criminal matter (lost/stolen documents) - Administrative Report']

    # 4. Clean up results
    unique_sections = list(dict.fromkeys(suggested_sections))
    
    # Return top 3, or a default if no match is found
    return unique_sections[:3] if unique_sections else ['IPC Section 323 (General Investigation)']  # Default to simple hurt if nothing matches

def get_sections_for_act(act_code):
    """Get all sections for a specific act from database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"SELECT Section, section_title FROM {act_code} ORDER BY Section LIMIT 50")
        rows = cursor.fetchall()
        conn.close()
        return [{"section": row[0], "title": row[1]} for row in rows]
    except Exception as e:
        print(f"Error getting sections for act {act_code}: {e}")
        return []

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Nyaya AI engine reachable"}), 200

@app.route('/api/districts', methods=['GET'])
def get_districts():
    """Return list of Indian districts."""
    return jsonify(sorted(INDIAN_DISTRICTS))

@app.route('/api/police-stations/<district>', methods=['GET'])
def get_police_stations(district):
    """Return police stations for a district."""
    stations = SAMPLE_POLICE_STATIONS.get(district, [f"{district} PS"])
    return jsonify(stations)

@app.route('/api/acts', methods=['GET'])
def get_acts():
    """Return available legal acts."""
    return jsonify(LEGAL_ACTS)

@app.route('/api/sections/<act>', methods=['GET'])
def get_sections(act):
    """Return sections for a specific act."""
    sections = get_sections_for_act(act)
    return jsonify(sections)

@app.route('/api/search-sections', methods=['GET'])
def search_sections():
    """Search sections across all acts by keyword."""
    query = request.args.get('q', '').lower()
    if not query or len(query) < 2:
        return jsonify([])
    
    results = []
    for act in LEGAL_ACTS:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT Section, section_title FROM {act} WHERE lower(section_title) LIKE ? OR lower(section_desc) LIKE ? LIMIT 10",
                (f"%{query}%", f"%{query}%")
            )
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    "act": act,
                    "section": row[0],
                    "title": row[1]
                })
            conn.close()
        except Exception as e:
            print(f"Error searching sections: {e}")
    
    return jsonify(results[:20])

@app.route('/api/fir-records', methods=['GET'])
def get_fir_records():
    """Get all FIR records from police database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fir_records ORDER BY fir_no ASC")
        rows = cursor.fetchall()
        conn.close()

        # Convert to list of dictionaries
        columns = ['id', 'fir_no', 'dist', 'ps', 'year', 'fir_date', 'act_sections',
                  'occurrence_day', 'occurrence_date', 'occurrence_time',
                  'info_received_date', 'info_received_time', 'gdr_entry_no',
                  'type_of_information', 'place_of_occurrence', 'complainant_name',
                  'father_husband_name', 'dob', 'nationality', 'passport_no',
                  'date_of_issue', 'place_of_issue', 'occupation', 'address',
                  'details_of_accused', 'reasons_for_delay', 'property_particulars',
                  'statement', 'created_at', 'status']

        fir_records = []
        for row in rows:
            fir_records.append(dict(zip(columns, row)))

        return jsonify(fir_records)

    except Exception as e:
        return jsonify({"error": "Failed to retrieve FIR records", "details": str(e)}), 500

@app.route('/api/fir-records/<fir_no>', methods=['GET'])
def get_fir_record(fir_no):
    """Get a specific FIR record by FIR number."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fir_records WHERE fir_no = ?", (fir_no,))
        row = cursor.fetchone()
        conn.close()

        if row:
            columns = ['id', 'fir_no', 'dist', 'ps', 'year', 'fir_date', 'act_sections',
                      'occurrence_day', 'occurrence_date', 'occurrence_time',
                      'info_received_date', 'info_received_time', 'gdr_entry_no',
                      'type_of_information', 'place_of_occurrence', 'complainant_name',
                      'father_husband_name', 'dob', 'nationality', 'passport_no',
                      'date_of_issue', 'place_of_issue', 'occupation', 'address',
                      'details_of_accused', 'reasons_for_delay', 'property_particulars',
                      'statement', 'created_at', 'status']

            return jsonify(dict(zip(columns, row)))
        else:
            return jsonify({"error": f"FIR record {fir_no} not found"}), 404

    except Exception as e:
        return jsonify({"error": "Failed to retrieve FIR record", "details": str(e)}), 500

@app.route('/generate_fir', methods=['POST'])
def generate_fir():
    data = request.json

    # AI-powered section suggestion based on complaint
    complaint_text = data.get("statement", "")
    if not data.get("act_sections"):  # Only auto-generate if user didn't specify
        ai_suggested_sections = analyze_complaint_for_sections(complaint_text)
        data["act_sections"] = ", ".join(ai_suggested_sections)

    # Save FIR to database
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO fir_records (fir_no, dist, ps, year, fir_date, act_sections, occurrence_day, occurrence_date, occurrence_time, info_received_date, info_received_time, gdr_entry_no, type_of_information, place_of_occurrence, complainant_name, father_husband_name, dob, nationality, passport_no, date_of_issue, place_of_issue, occupation, address, details_of_accused, reasons_for_delay, property_particulars, statement) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (data.get("fir_no", ""), data.get("dist", ""), data.get("ps", ""), data.get("year", ""), data.get("fir_date", ""), data.get("act_sections", ""), data.get("occurrence_day", ""), data.get("occurrence_date", ""), data.get("occurrence_time", ""), data.get("info_received_date", ""), data.get("info_received_time", ""), data.get("gdr_entry_no", ""), data.get("type_of_information", ""), data.get("place_of_occurrence", ""), data.get("complainant_name", ""), data.get("father_husband_name", ""), data.get("dob", ""), data.get("nationality", ""), data.get("passport_no", ""), data.get("date_of_issue", ""), data.get("place_of_issue", ""), data.get("occupation", ""), data.get("address", ""), data.get("details_of_accused", ""), data.get("reasons_for_delay", ""), data.get("property_particulars", ""), data.get("statement", "")))
            fir_id = cursor.lastrowid
        # Generate formatted FIR text
        formatted_fir = f"""
FIR ID: {fir_id}
FIR NO: {data.get("fir_no", "")}
DISTRICT: {data.get("dist", "")}
POLICE STATION: {data.get("ps", "")}
YEAR: {data.get("year", "")}
FIR DATE: {data.get("fir_date", "")}
ACT SECTIONS: {data.get("act_sections", "")}
OCCURRENCE DAY: {data.get("occurrence_day", "")}
OCCURRENCE DATE: {data.get("occurrence_date", "")}
OCCURRENCE TIME: {data.get("occurrence_time", "")}
INFO RECEIVED DATE: {data.get("info_received_date", "")}
INFO RECEIVED TIME: {data.get("info_received_time", "")}
GDR ENTRY NO: {data.get("gdr_entry_no", "")}
TYPE OF INFORMATION: {data.get("type_of_information", "")}
PLACE OF OCCURRENCE: {data.get("place_of_occurrence", "")}
COMPLAINANT NAME: {data.get("complainant_name", "")}
FATHER/HUSBAND NAME: {data.get("father_husband_name", "")}
DOB: {data.get("dob", "")}
NATIONALITY: {data.get("nationality", "")}
PASSPORT NO: {data.get("passport_no", "")}
DATE OF ISSUE: {data.get("date_of_issue", "")}
PLACE OF ISSUE: {data.get("place_of_issue", "")}
OCCUPATION: {data.get("occupation", "")}
ADDRESS: {data.get("address", "")}
DETAILS OF ACCUSED: {data.get("details_of_accused", "")}
REASONS FOR DELAY: {data.get("reasons_for_delay", "")}
PROPERTY PARTICULARS: {data.get("property_particulars", "")}
STATEMENT: {data.get("statement", "")}
STATUS: Saved to Police Records
MESSAGE: FIR has been successfully registered and saved to police records.
"""
        # Return response with database confirmation
        fir_response = {
            "fir_id": fir_id,
            "fir_no": data.get("fir_no", ""),
            "dist": data.get("dist", ""),
            "ps": data.get("ps", ""),
            "year": data.get("year", ""),
            "fir_date": data.get("fir_date", ""),
            "act_sections": data.get("act_sections", ""),
            "occurrence_day": data.get("occurrence_day", ""),
            "occurrence_date": data.get("occurrence_date", ""),
            "occurrence_time": data.get("occurrence_time", ""),
            "info_received_date": data.get("info_received_date", ""),
            "info_received_time": data.get("info_received_time", ""),
            "gdr_entry_no": data.get("gdr_entry_no", ""),
            "type_of_information": data.get("type_of_information", ""),
            "place_of_occurrence": data.get("place_of_occurrence", ""),
            "complainant_name": data.get("complainant_name", ""),
            "father_husband_name": data.get("father_husband_name", ""),
            "dob": data.get("dob", ""),
            "nationality": data.get("nationality", ""),
            "passport_no": data.get("passport_no", ""),
            "date_of_issue": data.get("date_of_issue", ""),
            "place_of_issue": data.get("place_of_issue", ""),
            "occupation": data.get("occupation", ""),
            "address": data.get("address", ""),
            "details_of_accused": data.get("details_of_accused", ""),
            "reasons_for_delay": data.get("reasons_for_delay", ""),
            "property_particulars": data.get("property_particulars", ""),
            "statement": data.get("statement", ""),
            "formatted_fir": formatted_fir.strip(),
            "status": "Saved to Police Records",
            "message": "FIR has been successfully registered and saved to police records."
        }
        return jsonify(fir_response)
    except sqlite3.IntegrityError as e:
        return jsonify({"error": f"FIR number {data.get('fir_no')} already exists", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to save FIR to database", "details": str(e)}), 500

import os
from werkzeug.utils import secure_filename

# Configuration
UPLOAD_FOLDER = 'static/uploads/evidence'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Creates folder automatically

@app.route('/upload_evidence/<fir_no>', methods=['POST'])
def upload_evidence(fir_no):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    # Secure the filename and save it
    filename = secure_filename(f"{fir_no}_{file.filename}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    # Return success response
    return jsonify({"message": f"Evidence uploaded successfully for FIR {fir_no}", "file_path": file_path})

def generate_unique_id(role):
    """Generate unique ID based on role."""
    role_prefixes = {
        'police': 'POL',
        'citizen': 'CIT',
        'lawyer': 'LAW',
        'judge': 'JUD'
    }
    prefix = role_prefixes.get(role, 'USR')
    
    # Find the highest existing ID for this role
    try:
        existing_users = users_collection.find({'role': role}).sort('unique_id', -1).limit(1)
        last_user = list(existing_users)
        if last_user:
            last_id = last_user[0]['unique_id']
            # Extract number and increment
            try:
                num = int(last_id[3:]) + 1
            except:
                num = 1
        else:
            num = 1
    except:
        num = 1
    
    return f"{prefix}{num:03d}"

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        fullname = data.get('fullname')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        
        if not all([fullname, email, password, role]):
            return jsonify({"error": "All fields are required"}), 400
        
        if role not in ['police', 'citizen', 'lawyer', 'judge']:
            return jsonify({"error": "Invalid role"}), 400
        
        # Check if user already exists
        if users_collection.find_one({'email': email}):
            return jsonify({"error": "Email already registered"}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Generate unique ID
        unique_id = generate_unique_id(role)
        
        # Create user document
        user = {
            'fullname': fullname,
            'email': email,
            'password_hash': password_hash,
            'role': role,
            'unique_id': unique_id,
            'created_at': datetime.utcnow()
        }
        
        try:
            users_collection.insert_one(user)
            return jsonify({
                "message": "User registered successfully",
                "unique_id": unique_id,
                "role": role
            }), 201
        except Exception as e:
            return jsonify({"error": f"Registration failed: {str(e)}"}), 500
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({"error": "Email and password are required"}), 400
        
        user = users_collection.find_one({'email': email})
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Store user in session
        session['user_id'] = str(user['_id'])
        session['role'] = user['role']
        session['unique_id'] = user['unique_id']
        
        return jsonify({
            "message": "Login successful",
            "role": user['role'],
            "unique_id": user['unique_id']
        }), 200
    
    return render_template('login.html')