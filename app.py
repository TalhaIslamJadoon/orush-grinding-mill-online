# -*- coding: utf-8 -*-
"""
Phosphate Grinding Mill System - Local (PC) Edition - FINAL
------------------------------------------------------------
Runs 100% on this computer using ONLY the Python 3 standard library.
No internet is needed for daily work and no data ever leaves this PC
(except backups YOU choose to sync, and WhatsApp/SMS alerts YOU set up).

Start: double-click Start-Mill-System.bat  (or run:  python app.py)
Then open:  http://127.0.0.1:8765

Biometric devices on the factory LAN push attendance to a SEPARATE
small listener (port shown in Settings) that accepts ONLY device
punches (/iclock/*). The main system stays on 127.0.0.1 only.
"""
import os, sys, json, sqlite3, hashlib, secrets, zipfile, io, csv, time, base64, socket
import webbrowser, threading, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
STATIC_DIR = os.path.join(BASE, "static")
APP_NAME = "Phosphate Grinding Mill System"
# Edition switch (packaging item H): "online" (hosted) is the default;
# the PC package launcher sets MILL_EDITION=pc. The PC edition removes
# what cannot work on a local database: the client portal and WhatsApp /
# SMS auto-send config + sending. Everything else is exactly the same
# code and behaviour. (The old FBR/IRN layer was removed from BOTH
# editions entirely — sales.irn stays in the schema, data preserved,
# but nothing asks for, stores or renders it any more.)
EDITION = (os.environ.get("MILL_EDITION") or "online").strip().lower()
IS_PC = EDITION == "pc"

# Font & Print settings (owner-controlled, mill-wide). Stacks combine a
# Latin face with an Arabic-script face so Urdu text picks the chosen
# Urdu face and Latin text the chosen Latin face automatically.
FONT_STACKS = {
    "default": "system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans Arabic', Arial, sans-serif",
    "serif": "Georgia, 'Times New Roman', 'Noto Naskh Arabic', 'Noto Sans Arabic', serif",
    "rounded": "ui-rounded, 'SF Pro Rounded', 'Segoe UI Rounded', system-ui, 'Noto Sans Arabic', sans-serif",
    "naskh": "'Noto Naskh Arabic', 'Noto Sans Arabic', system-ui, serif",
    "nastaliq": "'Noto Nastaliq Urdu', 'Noto Sans Arabic', system-ui, sans-serif",
}
FONT_SIZES = ("small", "normal", "large")
ACCENT_HEX = {"green": "#0c7a4e", "blue": "#1565c0", "teal": "#0e7a7b",
              "maroon": "#8e2434", "purple": "#6a3ec9", "slate": "#4a6076",
              "bronze": "#a06a1c", "sky": "#2b78b8", "mint": "#18825f",
              "peach": "#bf5a11", "lavender": "#7d5fc0", "rose": "#c74e74"}

def voice_settings(con):
    return {"voice_alerts": int(meta_get(con, "voice_alerts", "0") or 0),
            "voice_vehicles": int(meta_get(con, "voice_vehicles", "1") or 0),
            "voice_payments": int(meta_get(con, "voice_payments", "1") or 0)}


def font_settings(con):
    _vc = str(meta_get(con, "print_voucher_copies", "2") or "2")
    if _vc not in ("1", "2", "3"):
        _vc = "2"
    return {"ui_font": meta_get(con, "ui_font", "default") or "default",
            "ui_text_size": meta_get(con, "ui_text_size", "normal") or "normal",
            "print_font": meta_get(con, "print_font", "default") or "default",
            "print_text_size": meta_get(con, "print_text_size", "normal") or "normal",
            "print_bold_headings": int(meta_get(con, "print_bold_headings", "1") or 1),
            "print_voucher_copies": int(_vc)}

# Vehicle voucher / gate-pass prints: the owner can print 2 or 3 copies
# of the slip side by side in bank-challan-style columns on ONE A4
# sheet (Font & Print -> print_voucher_copies, default 2). Copy labels
# are named in the print language (the print link carries &lang=; the
# voucher page itself is otherwise English).
VOUCHER_COPY_LABELS = {
    "en": ("Driver Copy", "Office Copy", "Client Copy"),
    "ur": ("ڈرائیور کاپی", "دفتر کاپی", "کلائنٹ کاپی"),
    "hi": ("ड्राइवर प्रति", "कार्यालय प्रति", "ग्राहक प्रति"),
}

# Print CSS for the multi-copy voucher page, appended after the shared
# print CSS so its @page rule wins for this document alone.
# Layout (Talha's redesign 2026-10-28): bank-challan-style COLUMNS —
# the copies sit side by side in a flex row across the A4 portrait
# sheet, replacing the vertically STACKED boxes of the first build.
# The stacked build spilled onto a second page on Talha's real
# printer (his screenshot: page 2 carried only a footer line) because
# the browser's own print header/footer eats vertical room no CSS
# budget can switch off. In a row the copies no longer stack, so the
# sheet height is ONE column's content height:
#   printable A4 at 9mm margins = 192mm wide x 279mm high;
#   copies=2 (column ~96mm): label ~6 + compact band ~18 (with logo)
#     + sliphead ~19 (64px QR) + table (<=10 rows, wrapped) ~69
#     + tail ~23 + wrap padding ~5 = ~140mm worst case;
#   copies=3 (column ~64mm): smaller fonts, values wrap more = ~122mm.
# Both leave >130mm of slack under the 279mm printable height (the
# computer-generated foot adds ~7mm), so browser print chrome cannot
# push the print to a second sheet — and each column is additionally
# capped (max-height + overflow:hidden) with page-break-inside:avoid
# on the row, making a spill structurally impossible.
# Every column is fully self-contained like a bank challan slip: copy
# label, a COMPACT mill band (same branding as the page band — accent,
# logo, name, phone, address), the slip title with the QR in its
# header row (.sliphead/.slipqr — kept from the previous build, same
# payload), the full table, and the Verified-by tail with the mill
# name + legal line. The tall once-per-page band is NOT printed in
# multi-copy mode: the per-column bands carry every branding field it
# had, so nothing is lost by dropping it.
# Narrow-column safety: the table is table-layout:fixed with a 36%
# label column and overflow-wrap:break-word, so long party names wrap
# inside their cell instead of widening the column.
VOUCHER_PRINT_CSS = (
    "<style>"
    ".copylabel{display:inline-block;font-weight:bold;font-size:12px;"
    "border:1.5px solid #333;border-radius:10px;padding:1px 10px;margin-bottom:6px}"
    ".cband{color:#fff;padding:5px 6px;border-radius:4px;text-align:center;margin-bottom:6px}"
    ".cband img{background:#fff;border-radius:3px;padding:1px}"
    ".cbname{font-size:14px;font-weight:bold;line-height:1.25}"
    ".cbsub{font-size:9.5px;opacity:.92;line-height:1.3}"
    ".vcols{display:flex;align-items:stretch}"
    ".vcol{flex:1 1 0;min-width:0;padding:0 7px;display:flex;flex-direction:column}"
    ".vcol .slipwrap{max-width:none;margin:0;flex:1 1 auto}"
    ".vcol.cut{border-left:2px dashed #999;position:relative}"
    ".vcol.cut:before{content:'✂';position:absolute;top:0;left:1px;"
    "background:#fff;padding:0 2px;font-size:11px;line-height:1}"
    ".vcol table{table-layout:fixed}"
    ".vcol td,.vcol th{overflow-wrap:break-word}"
    ".vcol th{width:36%}"
    "@media print{"
    "@page{size:A4;margin:9mm}"
    ".vcols{page-break-inside:avoid}"
    ".vcol{max-height:262mm;overflow:hidden}"
    ".copies2 .slipwrap{padding:9px}"
    ".copies2 .slipwrap td,.copies2 .slipwrap th{padding:4px 6px;font-size:12px}"
    ".copies2 .sliptitle h2{font-size:15px}"
    ".copies2 .slipqr svg{height:64px;width:64px}"
    ".copies2 .slipfoot{margin-top:10px}"
    ".copies2 .slipfoot p{margin:3px 0}"
    ".copies3 .slipwrap{padding:6px;font-size:11px}"
    ".copies3 .slipwrap td,.copies3 .slipwrap th{padding:2px 4px;font-size:10.5px}"
    ".copies3 .sliptitle h2{font-size:13px}"
    ".copies3 .sliphead{margin-bottom:4px}"
    ".copies3 .slipqr svg{height:56px;width:56px}"
    ".copies3 .cbname{font-size:12px}"
    ".copies3 .cbsub{font-size:8.5px}"
    ".copies3 .copylabel{font-size:10px;margin-bottom:4px;padding:0 8px}"
    ".copies3 .slipfoot{margin-top:8px}"
    ".copies3 .slipfoot p{margin:2px 0}"
    "}"
    "</style>")
DEVICE_PORT_OFFSET = 100          # device listener = main port + 100

# ---------------------------------------------------------------- config ----
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

CONFIG = load_config()

def db_path():
    return CONFIG.get("db_path")

def get_db():
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con

def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

# ---------------------------------------------------------------- schema ----
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  salt TEXT NOT NULL, pass_hash TEXT NOT NULL,
  role TEXT NOT NULL,            -- owner | manager | client | staff | demo
  party_id INTEGER,              -- set for client logins
  email TEXT DEFAULT '',         -- round 12: login-by-email + password reset + notifications (unique across logins when set)
  display_name TEXT DEFAULT '',  -- round 12: self-service profile
  phone TEXT DEFAULT '',         -- round 12: own phone / WhatsApp number (self-service profile)
  avatar_b64 TEXT DEFAULT '', avatar_mime TEXT DEFAULT '',  -- round 12: profile picture (logo pattern)
  avatar_ver INTEGER DEFAULT 0,
  perms TEXT DEFAULT '[]',       -- staff only: JSON array of permission keys
  lang TEXT DEFAULT 'en', theme TEXT DEFAULT 'light', unit TEXT DEFAULT 't',
  fail_count INTEGER DEFAULT 0, locked_until REAL DEFAULT 0,
  created TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS parties(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT DEFAULT '', whatsapp TEXT DEFAULT '',
  email TEXT DEFAULT '',         -- round 12: statements / payment receipts by email
  address TEXT DEFAULT '',
  roles TEXT DEFAULT '',         -- comma list: supplier,buyer,grinding
  credit_limit REAL DEFAULT 0,
  opening_balance REAL DEFAULT 0, -- + = party owes us, - = we owe party
  open_date TEXT DEFAULT ''      -- account opening date (YYYY-MM-DD)
);
CREATE TABLE IF NOT EXISTS vehicle_tares(
  vehicle_no TEXT PRIMARY KEY, tare_kg REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS trips(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, direction TEXT NOT NULL,   -- IN | OUT
  party_id INTEGER,
  buy_from_party_id INTEGER,   -- IN: seller when != trip party (NULL = trip party)
  vehicle_no TEXT DEFAULT '', driver TEXT DEFAULT '',
  driver_phone TEXT DEFAULT '', entered_by TEXT DEFAULT '',
  gross_kg REAL DEFAULT 0, tare_kg REAL DEFAULT 0, net_kg REAL DEFAULT 0,
  bags INTEGER DEFAULT 0, grade_pct REAL DEFAULT 0,
  freight REAL DEFAULT 0, freight_payer TEXT DEFAULT 'mill', -- mill | party
  kind TEXT DEFAULT 'local',                 -- local | export
  loading REAL DEFAULT 0, unloading REAL DEFAULT 0,
  grind_rate REAL DEFAULT 0, grind_charge REAL DEFAULT 0,  -- OUT: optional grinding charge
  rock_rate REAL DEFAULT 0,                  -- IN: optional rock purchase rate /ton
  rate_type TEXT DEFAULT '',                 -- IN: factory (ponch) | mine
  rent REAL DEFAULT 0,                       -- IN: vehicle rent (mine rate only)
  rent_to TEXT DEFAULT 'seller',             -- IN mine rent: seller (khata credit) | driver (mill cash cost)
  charge_bearer TEXT DEFAULT 'party',        -- party | mill (loading/unloading)
  order_id INTEGER,
  sale_buyer_id INTEGER,                     -- OUT (Own only): powder sold to this party
  sale_rate REAL DEFAULT 0,                  -- OUT (Own only): sale rate /ton (0 = no sale on trip)
  note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS grinding_jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  party_id INTEGER,              -- NULL = mill's own rock
  tons REAL NOT NULL, rate_per_ton REAL NOT NULL,
  grade_pct REAL DEFAULT 0, bags INTEGER DEFAULT 0,
  kind TEXT DEFAULT 'local',
  shift TEXT DEFAULT 'Day',      -- Day | Night (owner's explicit shift pick)
  amount REAL NOT NULL, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS grind_sessions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  party_id INTEGER, started TEXT NOT NULL, ended TEXT DEFAULT '',
  note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS purchases(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, party_id INTEGER NOT NULL,
  tons REAL NOT NULL, grade_pct REAL DEFAULT 0,
  rate_per_ton REAL NOT NULL, deduction_pct REAL DEFAULT 0,
  billed_tons REAL NOT NULL, amount REAL NOT NULL, note TEXT DEFAULT '',
  item TEXT DEFAULT 'rock', item_name TEXT DEFAULT '', qty REAL DEFAULT 0,
  unit TEXT DEFAULT '', unit_rate REAL DEFAULT 0, bags INTEGER DEFAULT 0,
  source TEXT DEFAULT 'ledger', deal_id TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sales(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, party_id INTEGER NOT NULL,
  tons REAL NOT NULL, bags INTEGER DEFAULT 0,
  rate_per_ton REAL NOT NULL, amount REAL NOT NULL,
  order_id INTEGER, invoice_no TEXT DEFAULT '', irn TEXT DEFAULT '',
  note TEXT DEFAULT '',
  item TEXT DEFAULT 'powder', item_name TEXT DEFAULT '', qty REAL DEFAULT 0,
  unit TEXT DEFAULT '', unit_rate REAL DEFAULT 0,
  source TEXT DEFAULT 'ledger', trip_id INTEGER, deal_id TEXT DEFAULT '',
  og_factory_id INTEGER              -- source='outside': the outside mill the powder was sold from
);
CREATE TABLE IF NOT EXISTS outside_grinding(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, kind TEXT NOT NULL,          -- sent | bill | received (legacy progress)
  party_id INTEGER NOT NULL,                       -- the outside mill (factory)
  tons REAL DEFAULT 0, grade_pct REAL DEFAULT 0,
  rate_per_ton REAL DEFAULT 0, amount REAL DEFAULT 0,
  bags REAL DEFAULT 0, bag_kg REAL DEFAULT 50,     -- bill/received: stamped per-bag kg
  vehicle_no TEXT DEFAULT '', note TEXT DEFAULT '',
  from_party_id INTEGER,                           -- sent: the mine/seller the rock was bought from
  rock_rate REAL DEFAULT 0, rock_amount REAL DEFAULT 0,  -- sent: seller payable (tons x rock rate)
  rock_used_t REAL,                                -- bill: actual rock consumed (NULL = legacy, derive)
  wastage_t REAL                                   -- bill: rock_used_t - powder tons, stamped
);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, party_id INTEGER NOT NULL,
  tons REAL DEFAULT 0, bags INTEGER DEFAULT 0,
  rate_per_ton REAL NOT NULL, expected_date TEXT DEFAULT '',
  status TEXT DEFAULT 'open',    -- open | closed
  note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS production(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, bags INTEGER NOT NULL,
  party_id INTEGER,              -- NULL = mill's own
  job_id INTEGER, kind TEXT DEFAULT 'local',
  bag_source TEXT DEFAULT 'mill',  -- mill | client (export bags)
  entered_by TEXT DEFAULT '',    -- username of the login that entered it
  start_time TEXT DEFAULT '',    -- shift start (bags packing), HH:MM
  end_time TEXT DEFAULT '',      -- shift end, HH:MM
  filter_kg REAL DEFAULT 0,      -- filter powder from the plant filters (kg, legacy rows)
  powder_bag_kg REAL,            -- kg in ONE powder bag, stamped at save time (NULL = legacy, reads as 50)
  filter_bags REAL DEFAULT 0,    -- filter powder counted in BAGS (the mill counts both outputs in bags)
  filter_bag_kg REAL,            -- kg in ONE filter bag, stamped at save time (NULL = legacy, reads as 50)
  note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS bag_movements(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, direction TEXT NOT NULL,  -- in = bardana bought/received | out = damaged/returned
  bags INTEGER NOT NULL, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS client_bags(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, party_id INTEGER NOT NULL,
  direction TEXT NOT NULL,       -- received | returned
  bags INTEGER NOT NULL, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS departments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  in_time TEXT DEFAULT '08:00', out_time TEXT DEFAULT '17:00',
  off_days TEXT DEFAULT '6',     -- python weekdays off, comma list (Mon=0 .. Sun=6)
  overtime_allowed INTEGER DEFAULT 0, overtime_rate REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS workers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, kind TEXT NOT NULL,  -- theka | salary
  rate_per_ton REAL DEFAULT 0, rate_per_bag REAL DEFAULT 0,
  monthly_salary REAL DEFAULT 0, phone TEXT DEFAULT '',
  department_id INTEGER, device_code TEXT DEFAULT '',
  start_date TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS worker_payouts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worker_id INTEGER NOT NULL, date TEXT NOT NULL,
  amount REAL NOT NULL, kind TEXT DEFAULT 'payment', -- payment | advance
  method TEXT DEFAULT 'cash', note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS attendance(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worker_id INTEGER NOT NULL, date TEXT NOT NULL,
  present INTEGER DEFAULT 1,
  check_in TEXT DEFAULT '', check_out TEXT DEFAULT '',
  overtime_hours REAL DEFAULT 0,
  UNIQUE(worker_id, date)
);
CREATE TABLE IF NOT EXISTS leaves(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worker_id INTEGER NOT NULL, from_date TEXT NOT NULL, to_date TEXT NOT NULL,
  kind TEXT DEFAULT 'unpaid',    -- paid | unpaid
  status TEXT DEFAULT 'pending', -- pending | approved | rejected
  note TEXT DEFAULT '', decided_by TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,            -- overtime | att_correction
  payload TEXT DEFAULT '{}', requested_by TEXT DEFAULT '',
  status TEXT DEFAULT 'pending', decided_by TEXT DEFAULT '',
  created TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS payments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, party_id INTEGER NOT NULL,
  direction TEXT NOT NULL,       -- in = received from party | out = paid to party
  amount REAL NOT NULL,
  method TEXT DEFAULT 'cash',    -- cash | bank | online | cheque
  bank_name TEXT DEFAULT '', online_channel TEXT DEFAULT '',
  ref_no TEXT DEFAULT '',        -- bank transfer ref / online TID (cheques use the cheque register)
  note TEXT DEFAULT '',
  og_bill_id INTEGER             -- set when this payment is a Grinding Bill's paid-now leg
);
CREATE TABLE IF NOT EXISTS cash_handovers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  holder_key TEXT NOT NULL,      -- 'user:<id>' system user | 'name:<text>' other person
  holder_name TEXT DEFAULT '',
  amount REAL NOT NULL, note TEXT DEFAULT '',
  entered_by TEXT DEFAULT '',
  status TEXT DEFAULT 'confirmed',  -- pending | confirmed (holder acknowledgement)
  ack_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS cash_counts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  holder_key TEXT NOT NULL, holder_name TEXT DEFAULT '',
  counted REAL NOT NULL, book REAL NOT NULL, diff REAL NOT NULL,
  note TEXT DEFAULT '', entered_by TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS cheques(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id INTEGER, party_id INTEGER,
  cheque_no TEXT DEFAULT '', bank TEXT DEFAULT '',
  due_date TEXT DEFAULT '', amount REAL DEFAULT 0,
  status TEXT DEFAULT 'pending'  -- pending | cleared | bounced
);
CREATE TABLE IF NOT EXISTS expense_heads(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, parent_id INTEGER  -- NULL = main head
);
CREATE TABLE IF NOT EXISTS expenses(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, category TEXT DEFAULT '',
  head_id INTEGER, sub_head_id INTEGER,
  amount REAL NOT NULL,
  paid_by TEXT DEFAULT '', paid_to TEXT DEFAULT '',
  method TEXT DEFAULT 'cash', note TEXT DEFAULT '',
  paid_kind TEXT DEFAULT 'other',     -- owner | manager | other (who physically paid)
  paid_by_holder TEXT DEFAULT '',     -- cash-in-hand holder key: 'user:<id>' | 'name:<text>' | '' (owner)
  pay_channel TEXT DEFAULT '',        -- bank name (method=bank) or online channel (method=online)
  pay_ref TEXT DEFAULT '',            -- cheque no / ref no / TID for bank & online
  status TEXT DEFAULT 'approved'      -- approved | pending | rejected (expense approval)
);
CREATE TABLE IF NOT EXISTS maintenance(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, machine TEXT DEFAULT '',
  detail TEXT DEFAULT '', cost REAL DEFAULT 0, downtime_hours REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS stock_counts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, item TEXT DEFAULT '',
  counted_qty REAL DEFAULT 0, book_qty REAL DEFAULT 0, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS day_costs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL UNIQUE, diesel_litres REAL DEFAULT 0, elec_units REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS attachments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name TEXT NOT NULL, record_id INTEGER NOT NULL,
  filename TEXT DEFAULT '', mime TEXT DEFAULT '', size INTEGER DEFAULT 0,
  data BLOB, uploaded_by TEXT DEFAULT '', created TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS payment_proofs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  party_id INTEGER NOT NULL, date TEXT NOT NULL, amount REAL DEFAULT 0,
  attachment_id INTEGER, status TEXT DEFAULT 'pending', -- pending | confirmed | rejected
  payment_id INTEGER, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS biometric_devices(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT DEFAULT '', serial TEXT UNIQUE NOT NULL, pin TEXT DEFAULT '',
  last_seen TEXT DEFAULT '', last_punch TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS device_punches(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_serial TEXT DEFAULT '', device_code TEXT DEFAULT '',
  punch_time TEXT DEFAULT '', raw TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS alerts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL, kind TEXT DEFAULT '',  -- vehicle_in | vehicle_out | payment_reminder | owner_summary | day_end | deletion
  party_id INTEGER, target TEXT DEFAULT '',     -- phone number target
  channel TEXT DEFAULT '',                      -- whatsapp_api | sms | wame
  status TEXT DEFAULT 'pending',                -- pending | sent | failed
  message TEXT DEFAULT '', detail TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL, type TEXT DEFAULT '',
  message TEXT DEFAULT '', is_read INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS recycle(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL, table_name TEXT NOT NULL, record_id INTEGER,
  data_json TEXT DEFAULT '', deleted_by TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created TEXT NOT NULL, username TEXT DEFAULT '',
  action TEXT DEFAULT '', detail TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS machines(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS machine_entries(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, machine_id INTEGER,
  work_type TEXT DEFAULT 'Service',  -- Service | Repair | Part Change | Other
  detail TEXT DEFAULT '', cost REAL DEFAULT 0,
  next_due TEXT DEFAULT '',
  expense_id INTEGER,               -- linked Expense Ledger row (head "Machine")
  created_by TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS godam_counts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, party_id INTEGER,   -- NULL = mill's own bags
  counted_bags INTEGER NOT NULL, book_bags INTEGER NOT NULL,
  diff INTEGER NOT NULL,                  -- counted - book (snapshot at count time)
  note TEXT DEFAULT '', created_by TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS bag_adjustments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, party_id INTEGER,   -- NULL = own
  bags INTEGER NOT NULL,                  -- delta applied to book bags on approval
  count_id INTEGER,                       -- godam_counts row it came from
  status TEXT DEFAULT 'pending',          -- pending | approved | rejected
  created_by TEXT DEFAULT '', decided_by TEXT DEFAULT '',
  note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS daily_remarks(
  date TEXT PRIMARY KEY,                  -- one register remark per day
  remark TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS shift_closures(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, shift TEXT NOT NULL,  -- Day | Night, the shift's own date
  reason TEXT NOT NULL,          -- technical | power (preset keys, UI translates)
  note TEXT DEFAULT '',
  by_user TEXT DEFAULT '',
  created TEXT DEFAULT '',
  UNIQUE(date, shift)
);
CREATE TABLE IF NOT EXISTS alert_dismissals(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL,
  kind TEXT NOT NULL,            -- shift | vehicle_in | vehicle_out
  date TEXT NOT NULL,            -- the shift's date / the day's date
  shift TEXT DEFAULT '',         -- Day | Night for kind='shift', '' otherwise
  created TEXT DEFAULT '',
  UNIQUE(username, kind, date, shift)
);
CREATE TABLE IF NOT EXISTS factory_closures(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  closed_from TEXT NOT NULL,     -- first closed day
  closed_to TEXT,                -- reopening day (first OPEN day); NULL = still closed
  reason TEXT NOT NULL,          -- power_outage | breakdown | maintenance_work | no_material | other
  reason_text TEXT DEFAULT '',   -- free text, required when reason='other'
  note TEXT DEFAULT '',
  closed_by TEXT DEFAULT '',
  reopened_by TEXT DEFAULT '',
  created TEXT DEFAULT '',
  updated TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS password_resets(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  token_hash TEXT NOT NULL,      -- SHA-256 of the emailed token; the token itself is never stored
  created REAL DEFAULT 0,        -- epoch seconds
  expires REAL DEFAULT 0,        -- epoch seconds (created + 60 min)
  used INTEGER DEFAULT 0         -- 0 open | 1 used | 2 superseded by a newer request
);
"""

# columns added to tables that already existed in the first PC build
MIGRATIONS = {
    "users": [("lang", "TEXT DEFAULT 'en'"), ("theme", "TEXT DEFAULT 'light'"),
              ("unit", "TEXT DEFAULT 't'"), ("fail_count", "INTEGER DEFAULT 0"),
              ("locked_until", "REAL DEFAULT 0"), ("created", "TEXT DEFAULT ''"),
              ("perms", "TEXT DEFAULT '[]'"), ("email", "TEXT DEFAULT ''"),
              ("display_name", "TEXT DEFAULT ''"), ("phone", "TEXT DEFAULT ''"),
              ("avatar_b64", "TEXT DEFAULT ''"), ("avatar_mime", "TEXT DEFAULT ''"),
              ("avatar_ver", "INTEGER DEFAULT 0")],
    "parties": [("open_date", "TEXT DEFAULT ''"), ("email", "TEXT DEFAULT ''")],
    "trips": [("kind", "TEXT DEFAULT 'local'"), ("loading", "REAL DEFAULT 0"),
              ("unloading", "REAL DEFAULT 0"), ("charge_bearer", "TEXT DEFAULT 'party'"),
              ("order_id", "INTEGER"), ("grind_rate", "REAL DEFAULT 0"),
              ("grind_charge", "REAL DEFAULT 0"), ("rock_rate", "REAL DEFAULT 0"),
              ("rate_type", "TEXT DEFAULT ''"), ("rent", "REAL DEFAULT 0"),
              ("driver_phone", "TEXT DEFAULT ''"), ("entered_by", "TEXT DEFAULT ''"),
              ("buy_from_party_id", "INTEGER"),
              ("rent_to", "TEXT DEFAULT 'seller'"),
              ("fx", "TEXT DEFAULT ''"),
              ("sale_buyer_id", "INTEGER"), ("sale_rate", "REAL DEFAULT 0")],
    "grinding_jobs": [("kind", "TEXT DEFAULT 'local'"), ("shift", "TEXT DEFAULT 'Day'")],
    "sales": [("order_id", "INTEGER"), ("invoice_no", "TEXT DEFAULT ''"), ("irn", "TEXT DEFAULT ''"),
              ("item", "TEXT DEFAULT 'powder'"), ("item_name", "TEXT DEFAULT ''"),
              ("qty", "REAL DEFAULT 0"), ("unit", "TEXT DEFAULT ''"),
              ("unit_rate", "REAL DEFAULT 0"), ("source", "TEXT DEFAULT 'ledger'"),
              ("trip_id", "INTEGER"), ("deal_id", "TEXT DEFAULT ''"),
              ("og_factory_id", "INTEGER")],
    "outside_grinding": [("from_party_id", "INTEGER"),
                         ("rock_rate", "REAL DEFAULT 0"), ("rock_amount", "REAL DEFAULT 0"),
                         ("rock_used_t", "REAL"), ("wastage_t", "REAL")],
    "purchases": [("item", "TEXT DEFAULT 'rock'"), ("item_name", "TEXT DEFAULT ''"),
                  ("qty", "REAL DEFAULT 0"), ("unit", "TEXT DEFAULT ''"),
                  ("unit_rate", "REAL DEFAULT 0"), ("bags", "INTEGER DEFAULT 0"),
                  ("source", "TEXT DEFAULT 'ledger'"), ("deal_id", "TEXT DEFAULT ''")],
    "production": [("party_id", "INTEGER"), ("job_id", "INTEGER"),
                   ("kind", "TEXT DEFAULT 'local'"), ("bag_source", "TEXT DEFAULT 'mill'"),
                   ("entered_by", "TEXT DEFAULT ''"),
                   ("start_time", "TEXT DEFAULT ''"), ("end_time", "TEXT DEFAULT ''"),
                   ("filter_kg", "REAL DEFAULT 0"),
                   ("powder_bag_kg", "REAL"), ("filter_bags", "REAL DEFAULT 0"),
                   ("filter_bag_kg", "REAL")],
    "workers": [("department_id", "INTEGER"), ("device_code", "TEXT DEFAULT ''"),
                ("start_date", "TEXT DEFAULT ''")],
    "worker_payouts": [("method", "TEXT DEFAULT 'cash'")],
    "attendance": [("check_in", "TEXT DEFAULT ''"), ("check_out", "TEXT DEFAULT ''"),
                   ("overtime_hours", "REAL DEFAULT 0")],
    "payments": [("method", "TEXT DEFAULT 'cash'"), ("bank_name", "TEXT DEFAULT ''"),
                 ("online_channel", "TEXT DEFAULT ''"), ("ref_no", "TEXT DEFAULT ''"),
                 ("og_bill_id", "INTEGER")],
    "expenses": [("head_id", "INTEGER"), ("sub_head_id", "INTEGER"),
                 ("paid_by", "TEXT DEFAULT ''"), ("paid_to", "TEXT DEFAULT ''"),
                 ("method", "TEXT DEFAULT 'cash'"),
                 ("paid_kind", "TEXT DEFAULT 'other'"), ("paid_by_holder", "TEXT DEFAULT ''"),
                 ("pay_channel", "TEXT DEFAULT ''"), ("pay_ref", "TEXT DEFAULT ''"),
                 ("status", "TEXT DEFAULT 'approved'")],
}

DEFAULT_HEADS = {
    "Utilities": ["Electricity", "Diesel", "Gas", "Water"],
    "Maintenance": ["Parts", "Mechanic", "Grinding Plates", "Oil & Grease"],
    "Factory Operations": ["Loading Labour", "Packing Material", "Cleaning"],
    "Transport": ["Vehicle Fuel", "Vehicle Repair", "Freight"],
    "Office": ["Stationery", "Mobile/Internet", "Tea & Food"],
    "Workers Welfare": ["Food", "Medical", "Advance Adjustment"],
    "Miscellaneous": ["Other"],
}

# ------------------------------------------------------- public demo login --
# Owner's order (28 Oct 2026): a PUBLIC view-only demo login whose
# credentials are published (YouTube description) so anyone can look
# inside and check the system. Every guarantee is enforced on the
# SERVER (perm_ok + api_post + api_get guards below) — the UI hiding
# buttons is never the barrier. The seeded account can never be
# re-roled; the owner may change its password, or delete it — a
# tombstone (meta 'demo_seed_off') then stops the startup re-seed.
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo12345"
DEMO_MSG = "demo login sirf dekhne ke liye hai — is se entry nahi ho sakti"

def init_db():
    con = get_db()
    con.executescript(SCHEMA)
    # migrations for older databases
    for table, cols in MIGRATIONS.items():
        existing = [r[1] for r in con.execute("PRAGMA table_info(%s)" % table)]
        for name, typ in cols:
            if name not in existing:
                con.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, name, typ))
    # one-time backfill: legacy free-text expenses.paid_by -> attribution
    # fields (old text preserved as an Other-holder name; "owner" -> Owner)
    try:
        if not meta_get(con, "exp_attrib_v1"):
            for r in con.execute("SELECT id, paid_by FROM expenses").fetchall():
                by = (r["paid_by"] or "").strip()
                if not by:
                    continue
                if by.lower() in ("owner", "malik", "self", "owner (self)"):
                    con.execute("UPDATE expenses SET paid_kind='owner' WHERE id=?", (r["id"],))
                else:
                    con.execute(
                        "UPDATE expenses SET paid_by_holder=? WHERE id=?",
                        ("name:" + by, r["id"]))
            meta_set(con, "exp_attrib_v1", "1")
    except sqlite3.OperationalError:
        pass
    # one-time backfill: party account opening dates. The parties table
    # never had a created-at stamp, so a legacy party's opening date is
    # its earliest dated activity (trip / payment / job / trade); a party
    # with no activity at all opens on the migration day — never blank.
    try:
        if not meta_get(con, "party_open_date_v1"):
            import datetime as _d
            _today = _d.date.today().isoformat()
            for r in con.execute(
                    "SELECT id FROM parties WHERE open_date IS NULL OR open_date=''").fetchall():
                pid = r["id"]
                row = con.execute(
                    "SELECT MIN(d) AS d FROM ("
                    " SELECT date AS d FROM trips WHERE party_id=?"
                    " UNION ALL SELECT date FROM payments WHERE party_id=?"
                    " UNION ALL SELECT date FROM grinding_jobs WHERE party_id=?"
                    " UNION ALL SELECT date FROM purchases WHERE party_id=?"
                    " UNION ALL SELECT date FROM sales WHERE party_id=?)",
                    (pid, pid, pid, pid, pid)).fetchone()
                od = (row["d"] if row else None) or _today
                con.execute("UPDATE parties SET open_date=? WHERE id=?", (od, pid))
            meta_set(con, "party_open_date_v1", "1")
    except sqlite3.OperationalError:
        pass
    # default expense heads (once)
    if con.execute("SELECT COUNT(*) c FROM expense_heads").fetchone()["c"] == 0:
        for main, subs in DEFAULT_HEADS.items():
            cur = con.execute("INSERT INTO expense_heads(name,parent_id) VALUES(?,NULL)", (main,))
            for s in subs:
                con.execute("INSERT INTO expense_heads(name,parent_id) VALUES(?,?)", (s, cur.lastrowid))
    # public demo login (once): seeded only while no 'demo' user
    # exists AND the owner has not deleted it before (tombstone) — a
    # deleted demo login never resurrects on its own, and a password
    # the owner changed is never overwritten by the seed.
    if not meta_get(con, "demo_seed_off"):
        if not con.execute("SELECT 1 FROM users WHERE username=?",
                           (DEMO_USERNAME,)).fetchone():
            _dsalt, _dhash = hash_pw(DEMO_PASSWORD)
            con.execute("INSERT INTO users(username,salt,pass_hash,role,party_id,created)"
                        " VALUES(?,?,?,'demo',NULL,?)",
                        (DEMO_USERNAME, _dsalt, _dhash, today()))
    con.commit(); con.close()

# ------------------------------------------------------- staff perms ------
# Fixed permission keys for the custom 'staff' role (the owner ticks these
# when creating/editing a staff login). Owner bypasses all; manager keeps
# its historic full operational access; client never reaches these routes.
PERMS_ALL = ["dashboard", "vehicles", "grinding", "production", "trade",
             "parties", "payments", "expenses", "cashbook", "workers",
             "reports", "orders"]
ACCENTS = ["green", "blue", "teal", "maroon", "purple", "slate", "bronze",
           "sky", "mint", "peach", "lavender", "rose"]

def parse_perms(raw):
    """Normalise a stored/submitted perms value to a clean list of keys."""
    if isinstance(raw, list):
        return [p for p in raw if p in PERMS_ALL]
    try:
        v = json.loads(raw or "[]")
    except Exception:
        return []
    if isinstance(v, list):
        return [p for p in v if p in PERMS_ALL]
    return []

def clean_perms(raw):
    return parse_perms(raw)

def user_perms(u):
    return parse_perms((u or {}).get("perms"))

def perm_ok(u, need):
    """need: None = any non-client login - 'owner' = owner only -
    'om' = owner+manager - a perm key or tuple of keys (any-of) = staff
    must hold it (owner/manager always pass non-owner needs)."""
    role = (u or {}).get("role")
    if role == "owner":
        return True
    if need == "owner":
        return False
    if role == "manager":
        return True
    if role == "demo":
        # public view-only login: every named business permission
        # passes for READS; the 'om' marker never does, so settings,
        # backups and the raw-table CSV export stay shut (the
        # 'owner' marker already returned False above). Writes are
        # rejected wholesale in api_post — this governs GETs only.
        return need != "om"
    if role != "staff":
        return False
    if need is None:
        return True
    if need == "om":
        return False
    perms = user_perms(u)
    if isinstance(need, (list, tuple)):
        return any(n in perms for n in need)
    return need in perms

def fmt_weight(kg, unit):
    """Format a kg weight in the chosen display unit (print pages)."""
    kg = float(kg or 0)
    if unit == "t":
        return "%.3f t" % (kg / 1000.0)
    if unit == "maund":
        return "%.2f md" % (kg / 40.0)
    return "%s kg" % format(kg, ",.0f")

# ------------------------------------------------- shared create paths -----
# The single creation path for every record the UI forms can make. The
# POST handlers call these, and the Excel importer calls the SAME helpers
# (after resolving friendly names to ids), so imported rows get exactly the
# same validation and derived amounts as form entries — never parallel SQL.
def _clean_open_date(v):
    """Normalise an account-opening date to YYYY-MM-DD; '' when unusable."""
    import datetime as _d
    s = str(v or "").strip()
    if not s:
        return ""
    try:
        return _d.date.fromisoformat(s[:10]).isoformat()
    except Exception:
        return ""


def create_party(con, d, u):
    import datetime as _d
    roles = ",".join(d.get("roles") or [])
    od = _clean_open_date(d.get("open_date")) or _d.date.today().isoformat()
    cur = con.execute(
        "INSERT INTO parties(name,phone,whatsapp,email,address,roles,credit_limit,opening_balance,open_date)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (d["name"].strip(), d.get("phone", ""), d.get("whatsapp", ""),
         (d.get("email") or "").strip(),
         d.get("address", ""), roles, float(d.get("credit_limit") or 0),
         float(d.get("opening_balance") or 0), od))
    audit(con, u["username"], "create", "party " + d["name"])
    con.commit()
    return {"ok": True, "id": cur.lastrowid}

LEGAL_LINE = "This is a computerized entry. No need of sign and stamp of company."

def _user_role(con, username):
    if not username:
        return ""
    r = con.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
    return r["role"] if r else ""

def voucher_text(con, t):
    """The vehicle IN/OUT voucher as plain text — the same content the
    printed voucher carries, ending with Verified by / mill name / the
    legal line (kept in English on every language version). Used for the
    WhatsApp alerts, the SMS fallback and the wa.me one-tap links."""
    mill = meta_get(con, "mill_name", APP_NAME)
    role = _user_role(con, t.get("entered_by") or "")
    lines = ["*%s*" % mill,
             "Vehicle %s Voucher #%s" % (t["direction"], t["id"]),
             "Date: %s" % t["date"],
             "Party: %s" % (t.get("party_name") or "Own / Apna"),
             "Vehicle: %s" % t["vehicle_no"],
             "Driver: %s%s" % (t.get("driver") or "",
                               (" (%s)" % t["driver_phone"]) if t.get("driver_phone") else ""),
             "Net Weight: %s kg (%.3f t)" % (format(float(t["net_kg"]), ",.0f"),
                                             float(t["net_kg"]) / 1000.0)]
    if t["direction"] == "OUT":
        # Bags ride only on a dispatch — rock arriving IN is weighed,
        # never bagged, so an IN voucher carries no Bags line at all.
        lines.append("Bags: %d" % int(t.get("bags") or 0))
    lines.append("Grade: %g%%" % float(t.get("grade_pct") or 0))
    if t["direction"] == "IN" and float(t.get("rock_rate") or 0) > 0:
        lines.append("Rock purchase: %.3f t @ Rs %g (%s) = Rs %s"
                     % (float(t["net_kg"]) / 1000.0, float(t["rock_rate"]),
                        "mine rate" if t.get("rate_type") == "mine" else "factory ponch rate",
                        format(float(t["net_kg"]) / 1000.0 * float(t["rock_rate"]), ",.0f")))
        if t.get("rate_type") == "mine" and float(t.get("rent") or 0) > 0:
            if (t.get("rent_to") or "seller") == "driver":
                lines.append("Vehicle rent to driver: Rs %s (cash)"
                             % format(float(t["rent"]), ",.0f"))
            else:
                lines.append("Vehicle rent: Rs %s" % format(float(t["rent"]), ",.0f"))
    if t["direction"] == "OUT" and float(t.get("grind_charge") or 0) > 0:
        lines.append("Grinding charge: %.3f t @ Rs %g = Rs %s"
                     % (float(t["net_kg"]) / 1000.0, float(t.get("grind_rate") or 0),
                        format(float(t["grind_charge"]), ",.0f")))
    if t["direction"] == "OUT" and t.get("id"):
        _sr = con.execute("SELECT * FROM sales WHERE trip_id=?", (t["id"],)).fetchone()
        if _sr:
            lines.append("Powder sale: %g t @ Rs %g = Rs %s [%s]"
                         % (float(_sr["tons"] or 0), float(_sr["rate_per_ton"] or 0),
                            format(float(_sr["amount"] or 0), ",.0f"),
                            _sr["invoice_no"] or ""))
        elif _trip_sale_amount(t) > 0:
            # Own-dispatch sale recorded on this trip (no sales row,
            # no invoice): the same line, closed with the buyer
            _bn = con.execute("SELECT name FROM parties WHERE id=?",
                              (int(t["sale_buyer_id"]),)).fetchone()
            lines.append("Powder sale: %g t @ Rs %g = Rs %s (sold to %s)"
                         % (float(t["net_kg"]) / 1000.0, float(t["sale_rate"]),
                            format(_trip_sale_amount(t), ",.0f"),
                            _bn["name"] if _bn else ""))
    _bf = t.get("buy_from_party_id")
    if _bf and int(_bf) != (t.get("party_id") or 0):
        _bfr = con.execute("SELECT name FROM parties WHERE id=?",
                           (int(_bf),)).fetchone()
        if _bfr:
            lines.append("Bought from: %s" % _bfr["name"])
    lines.append("Verified by: %s%s" % (t.get("entered_by") or "-",
                                        (" (%s)" % role) if role else ""))
    lines.append(mill)
    lines.append(LEGAL_LINE)
    return "\n".join(lines)

def _wa_me_url(num, text):
    n = re_clean_phone(num)
    if not n:
        return ""
    return "https://wa.me/%s?text=%s" % (n, quote(text))

def _trip_fx(con, direction, pid):
    """Stock effect stamped on an OUT trip at save time (owner,
    28 Oct 2026: Vehicle Out is DISPATCH-ONLY — a powder sale is
    entered in the Party Ledger, never on the trip):
      'party' — the party's OWN powder is leaving (toll return: the
                party has production), the trip deducts their stock;
      'own'   — no party (Own / Apna): the trip deducts OWN stock;
      'none'  — a BUYER's gate pass: the Ledger powder Sell entry
                carries the receivable AND the own-stock-out, so
                this trip moves NO stock and NO money anywhere.
    Legacy rows (fx '') keep the pre-change read semantics exactly:
    party trips count as party dispatch, and a legacy gate sale's
    money/stock rides on its linked sale row, as it always did."""
    if direction != "OUT":
        return ""
    if not pid:
        return "own"
    made = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production "
                       "WHERE party_id=?", (int(pid),)).fetchone()["s"]
    return "party" if made > 0 else "none"


def _t3(v):
    """A tons figure printed the system's way: 3 decimals with the
    trailing zeros trimmed (40 -> '40', 44.999 -> '44.999')."""
    s = ("%.3f" % float(v or 0)).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


class StockConfirmRequired(Exception):
    """Raised by the trip save paths when a Vehicle Out dispatch
    exceeds the ground powder actually lying in the stock pool it
    deducts from, and the payload carries no explicit confirm flag.
    No trip is saved when this raises. The API layer turns it
    into a confirm-required JSON response (HTTP 409) so the UI can
    ask "phir bhi save karein?"; the Excel importer shares
    create_trip, so the same raise lands in its per-row error list —
    the row is flagged, never silently imported."""
    def __init__(self, pool, party_id, available_t, net_t):
        self.pool = pool
        self.party_id = party_id
        self.available_t = available_t
        self.net_t = net_t
        super().__init__(
            "powder stock kam hai: stock me sirf %s t powder hai, %s t out ho raha hai"
            % (_t3(available_t), _t3(net_t)))

    def payload(self):
        return {"ok": False, "confirm_required": True,
                "reason": "powder_stock", "pool": self.pool,
                "party_id": self.party_id,
                "available_t": self.available_t, "net_t": self.net_t,
                "error": str(self)}


def _trip_old_pool(old):
    """The powder pool a stored trip's dispatch deducted from, in
    party_stock / own_stock read semantics (None = it moved no
    stock): a party trip counts unless its fx stamp is 'none'
    (legacy '' party trips count too — powder_out sums fx<>'none');
    an Own trip counts only with the fx='own' stamp, which is
    exactly the set own_stock's dispatch sum reads."""
    if old is None or old["direction"] != "OUT":
        return None
    ofx = (old["fx"] or "") if "fx" in old.keys() else ""
    if ofx == "none":
        return None
    if old["party_id"]:
        return ("party", int(old["party_id"]))
    if ofx == "own":
        return ("own", None)
    return None


def _powder_pool(con, fx, pid, old=None):
    """(pool_key, available powder tons) for an OUT dispatch, or None
    when the dispatch moves NO stock (fx 'none' — a buyer's gate
    pass). Reuses the canonical stock views — NO parallel formula:
    party_stock(...)['powder_ready_t'] for a toll party (powder made
    by grinding jobs: production bags x each record's stamped
    per-bag kg, minus dispatched net, minus ledger powder sales) and
    own_stock(...)['powder_left_t'] for Own. Filter powder is a
    separate stock in both views and never counts here.
    `old` = the trip being edited: when it deducted from THIS pool,
    its own previous net is added back, so re-saving an unchanged
    trip never trips the check (the same add-back the bags warning
    below has always done)."""
    if fx == "party" and pid:
        key = ("party", int(pid))
        avail = party_stock(con, int(pid))["powder_ready_t"]
    elif fx == "own":
        key = ("own", None)
        avail = own_stock(con)["powder_left_t"]
    elif fx == "" and pid:
        # legacy unstamped party trip (an edit with unchanged party):
        # party_stock counts its dispatch, so the pool is the party's
        key = ("party", int(pid))
        avail = party_stock(con, int(pid))["powder_ready_t"]
    else:
        return None
    if _trip_old_pool(old) == key:
        avail = round(avail + round(float(old["net_kg"] or 0) / 1000.0, 3), 3)
    return key, avail


def _powder_stock_gate(con, direction, fx, pid, net_kg, d, old=None):
    """Talha's stock check (28 Oct 2026): a Vehicle Out dispatch may
    not SILENTLY exceed the ground powder lying in its pool.
    Returns an override-info dict when the dispatch exceeds stock
    but the payload carries the explicit confirm flag (the caller
    saves, then writes the audit trace); returns None when the
    dispatch is within stock, stock-free (gate pass / IN), or zero.
    Raises StockConfirmRequired otherwise. The comparison is exact
    at the system's 3-decimal ton precision: both sides are rounded
    to 3 decimals first, so 45.000 never passes against 44.999 of
    stock and float dust can never false-trigger either."""
    if direction != "OUT":
        return None
    pool = _powder_pool(con, fx, pid, old)
    if pool is None:
        return None
    key, avail = pool
    net_t = round(float(net_kg or 0) / 1000.0, 3)
    if net_t <= 0 or net_t <= avail:
        return None
    if not d.get("confirm_stock"):
        raise StockConfirmRequired(key[0], pid if key[0] == "party" else None,
                                   avail, net_t)
    return {"pool": key[0], "party_id": pid if key[0] == "party" else None,
            "available_t": avail, "net_t": net_t}


class DuplicateSaleConfirmRequired(Exception):
    """Raised when a powder sale looks like it repeats a sale already
    recorded the OTHER way — a Ledger Sell for goods an Own Vehicle
    Out trip already sold, or an Own-dispatch sale for goods already
    in the buyer's khata as a Ledger Sell (owner's duplicate guard,
    28 Oct 2026). Same contract as the stock gate: HTTP 409, NOTHING
    is saved, and only a re-post carrying confirm_duplicate proceeds
    (the caller then writes a duplicate_sale_override audit row).
    Stateless by design: no matching/consumption table — a repeated
    legitimate sale inside the window warns again, which the owner
    accepted (it is a warning, not a block)."""
    def __init__(self, match_kind, match, buyer_name):
        self.match_kind = match_kind          # "trip" | "sale"
        self.match = match
        if match_kind == "trip":
            self.date = match["date"]
            self.vehicle = match["vehicle_no"] or ""
            self.tons = round(float(match["net_kg"] or 0) / 1000.0, 3)
            self.rate = float(match["sale_rate"] or 0)
            msg = ("ye powder is buyer ko %s ki Vehicle Out trip (gari %s) par "
                   "pehle bik chuka hai — dobara entry roki gayi"
                   % (self.date, self.vehicle))
        else:
            self.date = match["date"]
            self.vehicle = ""
            self.tons = round(float(match["tons"] or 0), 3)
            self.rate = float(match["rate_per_ton"] or 0)
            msg = ("is buyer ke khatay mein is powder ki Ledger Sell %s ko "
                   "pehle se lagi hai — dobara entry roki gayi" % self.date)
        self.buyer_name = buyer_name or ""
        super().__init__(msg)

    def payload(self):
        return {"ok": False, "confirm_required": True,
                "reason": "duplicate_sale", "match_kind": self.match_kind,
                "date": self.date, "vehicle": self.vehicle,
                "tons": self.tons, "rate": self.rate,
                "buyer_name": self.buyer_name, "error": str(self)}


def _trip_sale_amount(t):
    """Rs receivable of an Own dispatch's recorded sale — 0 when the
    trip carries none. The sale lives ON the trip row (sale_buyer_id
    + sale_rate, Own OUT trips only) and every reader DERIVES the
    amount from the row: net tons x rate, exactly like the rock
    purchase on a Vehicle In. No sales-table row ever exists for it."""
    try:
        if t["direction"] == "OUT" and t["sale_buyer_id"] \
                and float(t["sale_rate"] or 0) > 0:
            return round(float(t["net_kg"] or 0) / 1000.0
                         * float(t["sale_rate"]), 2)
    except Exception:
        pass
    return 0.0


def _dup_window_start(date_str):
    """First day of the duplicate-sale window: 7 days before the
    entry's own date (the window is [date-7d, date], inclusive)."""
    import datetime as _d
    try:
        dd = _d.date.fromisoformat(str(date_str)[:10])
    except Exception:
        dd = _d.date.today()
    return (dd - _d.timedelta(days=7)).isoformat()


def _dup_trip_match(con, buyer_id, date_str, tons):
    """An Own OUT trip that already sold >= `tons` of powder to this
    buyer inside the window — a Ledger Sell for the same goods would
    post the receivable (and the stock-out) a second time."""
    if not buyer_id:
        return None
    want = round(float(tons or 0), 3)
    for r in con.execute(
            "SELECT * FROM trips WHERE direction='OUT' AND party_id IS NULL "
            "AND sale_buyer_id=? AND sale_rate>0 AND date>=? AND date<=? "
            "ORDER BY date DESC, id DESC",
            (int(buyer_id), _dup_window_start(date_str), str(date_str)[:10])):
        if round(float(r["net_kg"] or 0) / 1000.0, 3) >= want:
            return r
    return None


def _dup_sale_match(con, buyer_id, date_str, tons):
    """A Ledger powder Sell already recorded for this buyer covering
    >= `tons` inside the window — an Own-dispatch sale for the same
    goods would double-count. Direct-trade legs and outside-factory
    sales never match (different goods, different stock)."""
    if not buyer_id:
        return None
    want = round(float(tons or 0), 3)
    for r in con.execute(
            "SELECT * FROM sales WHERE party_id=? "
            "AND COALESCE(item,'powder')='powder' AND trip_id IS NULL "
            "AND COALESCE(source,'ledger') NOT IN ('direct','outside') "
            "AND date>=? AND date<=? ORDER BY date DESC, id DESC",
            (int(buyer_id), _dup_window_start(date_str), str(date_str)[:10])):
        if round(float(r["tons"] or 0), 3) >= want:
            return r
    return None


def _dup_guard_trip_side(con, d, buyer_id, date_str, tons):
    """Guard for an Own-dispatch sale being saved on a trip. Returns
    the matched Ledger Sell when the payload confirms (the caller
    audits it); raises DuplicateSaleConfirmRequired when it does not;
    returns None when nothing matches."""
    m = _dup_sale_match(con, buyer_id, date_str, tons)
    if m is None:
        return None
    if d.get("confirm_duplicate"):
        return m
    nm = con.execute("SELECT name FROM parties WHERE id=?",
                     (int(buyer_id),)).fetchone()
    raise DuplicateSaleConfirmRequired("sale", m, nm[0] if nm else "")


def _dup_guard_sale_side(con, d, buyer_id, date_str, tons):
    """Mirror guard for a Ledger powder Sell being saved. Returns the
    matched Own OUT trip when the payload confirms; raises
    DuplicateSaleConfirmRequired when it does not."""
    m = _dup_trip_match(con, buyer_id, date_str, tons)
    if m is None:
        return None
    if d.get("confirm_duplicate"):
        return m
    nm = con.execute("SELECT name FROM parties WHERE id=?",
                     (int(buyer_id),)).fetchone()
    raise DuplicateSaleConfirmRequired("trip", m, nm[0] if nm else "")


def create_trip(con, d, u, notify=True):
    # The entry form now collects ONLY the net weight: when a positive
    # net_kg arrives on its own it is stored as gross = net, tare = 0 so
    # every report/stock figure that reads net keeps working unchanged.
    # Legacy payloads (form history, Excel files with Gross/Tare columns)
    # still derive net = gross - tare exactly as before.
    _net_in = d.get("net_kg")
    if _net_in is not None and float(_net_in or 0) > 0 \
            and not float(d.get("gross_kg") or 0):
        net = float(_net_in); gross = net; tare = 0.0
    else:
        gross = float(d.get("gross_kg") or 0); tare = float(d.get("tare_kg") or 0)
        net = gross - tare if gross else float(d.get("net_kg") or 0)
    veh = (d.get("vehicle_no") or "").strip()
    if veh and tare:
        con.execute("INSERT INTO vehicle_tares(vehicle_no,tare_kg) VALUES(?,?)"
                    " ON CONFLICT(vehicle_no) DO UPDATE SET tare_kg=excluded.tare_kg",
                    (veh, tare))
    # warehouse guard: OUT bags must not exceed party's ready bags
    warning = ""
    pid = d.get("party_id") or None
    bags_out = int(d.get("bags") or 0)
    if d["direction"] == "IN":
        # Rock NEVER arrives in bags — it is weighed in tons on the
        # kanta; bags exist only on powder dispatch (OUT) and in the
        # Warehouse bags module. An IN save stores 0 whatever the
        # payload carries (the IN form has no Bags field, and an Excel
        # file's Bags column is ignored for IN rows the same way).
        bags_out = 0
    _fx = _trip_fx(con, d["direction"], pid)
    # Powder-stock gate (Talha, 28 Oct 2026): an OUT dispatch that
    # deducts stock (toll party / Own) may not silently exceed the
    # ground powder lying in that pool — see _powder_stock_gate.
    # A gate pass (fx 'none') is never checked.
    _stock_ovr = _powder_stock_gate(con, d["direction"], _fx, pid, net, d)
    if d["direction"] == "OUT" and pid and bags_out and _fx == "party":
        st = party_stock(con, int(pid))
        if bags_out > st["bags_ready"]:
            warning = ("WARNING: %d bags bheje ja rahe hain lekin party ke ready bags sirf %d hain "
                       "(godam stock ka hisaab bigar sakta hai)" % (bags_out, st["bags_ready"]))
    # Loading/unloading (owner's rule): a rock vehicle coming IN is never
    # loaded/unloaded at the factory, so an IN save stores NEITHER charge
    # (any values in the payload are ignored); an OUT save keeps Loading
    # only — Unloading is gone from entry, new saves always store 0 for
    # it. Old records keep whatever they already hold.
    if d["direction"] == "IN":
        _loading = 0.0; _unloading = 0.0
    else:
        _loading = float(d.get("loading") or 0); _unloading = 0.0
    # Optional charges posted to the party khata by party_ledger, from
    # this same trip row (the freight/loading mechanism):
    # - OUT + grind_rate > 0  -> grinding charge = net tons x rate (debit).
    #   Blank/0 rate posts nothing, so lots already charged on a grinding
    #   record are never charged twice.
    # - IN + rock_rate > 0    -> rock purchase = net tons x rate (credit /
    #   payable). rate_type 'factory' = ponch (delivered) rate, rent AND
    #   freight are dropped even if sent; 'mine' = rate at the mine, the
    #   vehicle rent posts as an extra payable. Blank/0 rate posts
    #   nothing (toll clients bringing their own rock are unaffected).
    _grind_rate = float(d.get("grind_rate") or 0) if d["direction"] == "OUT" else 0.0
    _grind_charge = round(net / 1000.0 * _grind_rate, 2) if _grind_rate > 0 else 0.0
    if d["direction"] == "OUT" and not pid:
        # Own dispatch = our OWN material (owner, 28 Oct 2026): the
        # grinding charge only ever applies to toll parties, so an Own
        # trip can NEVER carry one — a rate value in the payload is
        # ignored/zeroed here, server-side, whatever the form sent.
        _grind_rate = 0.0
        _grind_charge = 0.0
    _rock_rate = float(d.get("rock_rate") or 0) if d["direction"] == "IN" else 0.0
    _rate_type = ""
    _rent = 0.0
    if _rock_rate > 0:
        _rate_type = "mine" if d.get("rate_type") == "mine" else "factory"
        if _rate_type == "mine":
            _rent = float(d.get("rent") or 0)
    # WHO receives the Mine-rate rent (owner's clarification): the
    # SELLER (default — the seller arranged the vehicle, so the rent is
    # a payable credited to the seller's khata under the Rent head), or
    # the DRIVER in cash — then NO khata credit posts at all and the
    # rent is the mill's own transport cost (P&L / Day-End rent_mill).
    _rent_to = "driver" if (_rate_type == "mine" and d.get("rent_to") == "driver") else "seller"
    _freight = float(d.get("freight") or 0)
    if _rate_type == "factory":
        # Factory ponch rate is the DELIVERED rate: no separate freight
        # exists on such a purchase, so a stray freight value is dropped
        # here exactly like the rent above.
        _freight = 0.0
    # An order link belongs to a dispatch only: an IN trip never carries
    # one, whatever the payload says.
    _order_id = (d.get("order_id") or None) if d["direction"] == "OUT" else None
    # Buy-from (seller): an IN trip's rock can be bought from a party
    # OTHER than the one the stock is credited to — classically the
    # stock is Own (Apna) while a supplier sold the rock. Stored ONLY
    # when it differs from the trip party: NULL means "the trip party
    # itself", so every default posting stays byte-identical to before.
    # party_ledger credits the purchase (and Mine-rate rent) to the
    # seller; the rock stock always stays with the trip party.
    _buy_from = None
    if d["direction"] == "IN":
        _bf_in = d.get("buy_from_party_id") or None
        if _bf_in is not None and int(_bf_in) != (pid or 0):
            _buy_from = int(_bf_in)
    if d["direction"] == "IN" and pid:
        # Purchase block is Own-only (owner, 28 Oct 2026): a client
        # party's Vehicle In is a GRINDING arrival — the client brings
        # its own rock to be ground; the mill never buys at the gate in
        # a client's name. A gate purchase is always the mill buying
        # for ITSELF: Party = Own (Mine), with the seller named in
        # "Buy from". So any purchase values submitted for a
        # client-party IN trip (rock rate / rate type / buy-from /
        # rent) are ignored here and stored zeroed — no purchase
        # credit and no rent credit can ever post from such a trip.
        # This is a SAVE-time rule (like the Own grinding-rate guard
        # above): read-time derivations are deliberately untouched, so
        # a historical client row that still carries a stored rate
        # keeps posting until the row itself is re-saved.
        _rock_rate = 0.0
        _rate_type = ""
        _rent = 0.0
        _rent_to = "seller"
        _buy_from = None
    # Own-dispatch sale (owner, 28 Oct 2026): an Own (Mine) OUT trip
    # may carry the sale of its own powder — "Powder sold to" (an
    # existing party) + "Sale rate /ton", BOTH or NEITHER; exactly one
    # filled is a validation error and nothing saves. The sale is
    # stored ON this row and its receivable is DERIVED from the row
    # at read time (party_ledger / party_business / day_end / pnl /
    # trade history), exactly like the rock purchase on a Vehicle In
    # — no sales row is ever created, so a trip edit re-derives it
    # and a trip delete removes it. On any other trip (toll / gate
    # pass / IN) the fields are dropped, as before. The duplicate
    # guard runs AFTER the stock gate above on purpose: the
    # dispatch's physical validity is decided first; only then does
    # this accounting warning get its turn (a re-post carrying
    # confirm_stock reaches it next).
    _sale_buyer = None
    _sale_rate = 0.0
    _dup_match = None
    if d["direction"] == "OUT" and not pid:
        _sb = d.get("sale_buyer_id") or None
        _sr = float(d.get("sale_rate") or 0)
        if (_sb is None) != (_sr <= 0):
            raise ValueError("Powder sale ke DONO khane bharein — 'Powder sold to' "
                             "aur 'Sale rate /ton' — ya dono khali chhorein")
        if _sb is not None:
            if not con.execute("SELECT 1 FROM parties WHERE id=?",
                               (int(_sb),)).fetchone():
                raise ValueError("'Powder sold to' wali party system mein nahi mili")
            _sale_buyer = int(_sb)
            _sale_rate = _sr
            _dup_match = _dup_guard_trip_side(con, d, _sale_buyer,
                                              d.get("date") or today(), net / 1000.0)
    cur = con.execute(
        "INSERT INTO trips(date,direction,party_id,vehicle_no,driver,gross_kg,tare_kg,net_kg,"
        "bags,grade_pct,freight,freight_payer,kind,loading,unloading,charge_bearer,order_id,note,"
        "grind_rate,grind_charge,rock_rate,rate_type,rent,driver_phone,entered_by,buy_from_party_id,rent_to,sale_buyer_id,sale_rate,fx)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), d["direction"], pid,
         veh, d.get("driver", ""), gross, tare, net,
         bags_out, float(d.get("grade_pct") or 0),
         _freight, d.get("freight_payer") or "mill",
         d.get("kind") or "local", _loading,
         _unloading, d.get("charge_bearer") or "party",
         _order_id, d.get("note", ""),
         _grind_rate, _grind_charge, _rock_rate, _rate_type, _rent,
         (d.get("driver_phone") or "").strip(), u["username"], _buy_from, _rent_to,
         _sale_buyer, _sale_rate, _fx))
    tid = cur.lastrowid
    audit(con, u["username"], "create", "trip %s %s net %g kg" % (d["direction"], veh, net))
    if _stock_ovr:
        # the confirmed stock override leaves its trace in the same
        # audit history as every other entry action
        audit(con, u["username"], "stock_override",
              "trip OUT %s: powder stock %s t tha, %s t confirm karke dispatch hua"
              % (veh, _t3(_stock_ovr["available_t"]), _t3(_stock_ovr["net_t"])))
        warning = (warning + " " if warning else "") + (
            "⚠ Stock me sirf %s t powder tha — %s t confirm karke dispatch hua"
            % (_t3(_stock_ovr["available_t"]), _t3(_stock_ovr["net_t"])))
    if _dup_match is not None:
        # a confirmed duplicate-sale override leaves the same kind of
        # audit trace as a stock override
        audit(con, u["username"], "duplicate_sale_override",
              "trip OUT %s: party %d ki sale ledger sell #%d se milti thi — "
              "confirm karke save hui" % (veh, _sale_buyer, _dup_match["id"]))
    con.commit()
    # The ONLY sale a trip itself can carry is the narrow Own-dispatch
    # sale resolved above (owner, 28 Oct 2026): stored on this row and
    # derived at read time — still NO sales-table row and NO invoice
    # is ever made from a trip, so the Ledger's powder Sell remains
    # the single door for every other sale. A sale_rate arriving on a
    # party trip (old form history, API clients) is ignored, as
    # before. The trip's fx stamp (above) decides its stock effect.
    sale_info = None
    if _sale_buyer:
        sale_info = {"buyer_id": _sale_buyer, "rate": _sale_rate,
                     "amount": round(net / 1000.0 * _sale_rate, 2)}
    wa = {"wa_auto": False, "wa_party_url": "", "wa_driver_url": "",
          "wa_owner_url": "", "voucher_url": "/print/trip/%d" % tid}
    if notify:
        # The voucher goes to party + driver + owner through the existing
        # alert machinery (Cloud template auto-send when configured, SMS
        # fallback, otherwise the save response carries one-tap wa.me
        # links and the UI offers those buttons — it never claims an
        # auto-send that did not happen: wa_auto is read back from the
        # alerts' real statuses). Bulk Excel imports pass notify=False
        # so hundreds of historical trips never fire hundreds of alerts.
        prow = con.execute("SELECT * FROM parties WHERE id=?", (pid,)).fetchone() if pid else None
        pname = prow["name"] if prow else "Own / Apna"
        trow = con.execute("SELECT * FROM trips WHERE id=?", (tid,)).fetchone()
        tdict = dict(trow); tdict["party_name"] = pname
        vtext = voucher_text(con, tdict)
        params = [pname, veh, "%.2f" % (net / 1000.0), str(bags_out)]
        kind = "vehicle_in" if d["direction"] == "IN" else "vehicle_out"
        owner_num = meta_get(con, "owner_whatsapp") or meta_get(con, "mill_phone")
        party_num = (prow["whatsapp"] or prow["phone"]) if prow else ""
        driver_num = (d.get("driver_phone") or "").strip()
        legs = []
        for num in (party_num, driver_num, owner_num):
            if num:
                aid = make_alert(con, kind, pid, num, vtext, params)
                st = con.execute("SELECT status FROM alerts WHERE id=?", (aid,)).fetchone()
                legs.append(st["status"] if st else "failed")
        wa["wa_auto"] = bool(legs) and all(s == "sent" for s in legs)
        if not wa["wa_auto"]:
            wa["wa_party_url"] = _wa_me_url(party_num, vtext)
            wa["wa_driver_url"] = _wa_me_url(driver_num, vtext)
            wa["wa_owner_url"] = _wa_me_url(owner_num, vtext)
        # round 12: email copy of the voucher to the party — its own
        # toggle (mail_ev_voucher, default OFF: a busy gate would
        # otherwise mail every movement; the owner opts in)
        try:
            _pem = party_email_addr(con, pid) if pid else ""
            if _pem:
                _mill = meta_get(con, "mill_name", APP_NAME)
                _subj = "Vehicle %s — %s (%s t) — %s" % (
                    d["direction"], veh, "%.2f" % (net / 1000.0), _mill)
                email_notify(con, "mail_ev_voucher", "email_voucher", pid,
                             _pem, _subj, vtext, _email_html(_mill, vtext))
        except Exception:
            pass
    return {"ok": True, "id": tid, "net_kg": net, "warning": warning,
            "grind_charge": _grind_charge,
            "purchase_amount": round(net / 1000.0 * _rock_rate, 2) if _rock_rate > 0 else 0,
            "rent": _rent, "rent_to": _rent_to,
            "buy_from_party_id": _buy_from, "sale": sale_info, **wa}

BAG_TONS = 0.05   # one bag = 50 kg — the standard conversion, still used
                  # where a record carries no weight of its own (dispatch /
                  # balance bag counts). Production records stamp their own
                  # per-bag weights (see _bagw / bag_weights).

def _bagw(v):
    """Per-bag weight (kg) stamped on a production record. NULL / legacy
    rows (saved before per-bag weights existed) read as the standard
    50 kg; a stored value <= 0 is impossible (validated at save) and
    also falls back to 50."""
    try:
        w = float(v)
    except (TypeError, ValueError):
        return 50.0
    return w if w > 0 else 50.0

def production_powder_t(con, where="", params=()):
    """Powder tons from production rows: every row's bags x ITS OWN
    stamped per-bag weight (legacy NULL = 50 kg)."""
    tot = 0.0
    for r in con.execute("SELECT bags, powder_bag_kg FROM production " + where, params):
        tot += float(r["bags"] or 0) * _bagw(r["powder_bag_kg"])
    return tot / 1000.0

def production_filter_kg(con, where="", params=()):
    """Filter powder in kg from production rows. New rows count filter
    powder in BAGS (bags x the row's stamped filter-bag weight); legacy
    rows stored the amount directly in filter_kg and count as kg. A row
    never carries both (the save path writes one or the other)."""
    tot = 0.0
    for r in con.execute("SELECT filter_kg, filter_bags, filter_bag_kg FROM production "
                         + where, params):
        tot += float(r["filter_kg"] or 0) \
            + float(r["filter_bags"] or 0) * _bagw(r["filter_bag_kg"])
    return tot

def production_filter_bags(con, where="", params=()):
    """Filter powder in BAGS from production rows (the bag-count twin
    of production_filter_kg): bag rows count their bags; legacy
    kg-stored rows convert at their own stamped filter-bag weight."""
    tot = 0.0
    for r in con.execute("SELECT filter_kg, filter_bags, filter_bag_kg FROM production "
                         + where, params):
        fb = float(r["filter_bags"] or 0)
        if fb > 0:
            tot += fb
        elif float(r["filter_kg"] or 0) > 0:
            tot += float(r["filter_kg"]) / _bagw(r["filter_bag_kg"])
    return tot

def own_filter_stock(con):
    """The mill's OWN filter-powder stock — the ONE canonical filter
    pool (Talha's rule, 28 Oct 2026): the filter bags thrown out by
    ANY grinding job are the MILL's property, never the job party's —
    for a toll client they are wastage (his recovery is powder only),
    and they credit the mill's own stock. So this pool sums filter
    output over EVERY production row, whatever party the job was for.
    Nothing ever leaves it in the system's records: filter powder has
    no sale item, no dispatch path and no adjustment path (sales items
    are rock / powder / other; trips carry powder), so the pool is
    simply everything ever produced. Read-time derivation — rows
    entered before this rule re-derive to it with no migration."""
    kg = production_filter_kg(con)
    return {"filter_bags": round(production_filter_bags(con), 3),
            "filter_kg": round(kg, 3),
            "filter_t": round(kg / 1000.0, 3)}

def _job_powder_kg(con, job):
    """Powder kg produced by ONE grinding job, from its linked
    production rows (bags x each row's stamped per-bag weight). A job
    with no production row (legacy / Excel import) counts its own bags
    column at the standard 50 kg."""
    rows = con.execute("SELECT bags, powder_bag_kg FROM production WHERE job_id=?",
                       (job["id"],)).fetchall()
    if rows:
        return sum(float(r["bags"] or 0) * _bagw(r["powder_bag_kg"]) for r in rows)
    return float(job["bags"] or 0) * 50.0

def create_job(con, d, u):
    # Quantity may arrive as tons ("tons" / "weight_tons") or as a bag
    # count ("bags" — legacy/import payloads only: the merged entry form
    # no longer collects a ground-rock weight at all, because the mill's
    # paper register never weighs ground rock — rock consumption is
    # derived from the powder produced, see jobs_ground_t). In the
    # legacy bags case the tons are derived HERE on the server from the
    # owner's bag_kg setting, never trusted from a client-side
    # calculation. When tons are supplied they win and "bags" keeps its
    # old meaning (the lot's powder bags, e.g. from Excel import). A
    # bags-derived entry stores bags=0 in that column — exactly like a
    # tons entry — so stock, grinding-loss, reports and theka figures
    # are untouched. The merged form sends neither tons nor bags, so its
    # jobs store tons 0 and consumption is derived per record.
    # Rate: the entry form no longer collects one. A rate is stored only
    # when the payload carries it (Excel import may); otherwise rate 0 /
    # amount 0 — no charge posts from this form and no last rate is ever
    # applied silently. The kind column is no longer written (its schema
    # default stands; old records keep their values).
    # MERGED Grinding & Production entry: when the payload carries
    # "out_bags" (the merged form and the merged Excel module always send
    # it), the powder bags produced are written through ONE path — the
    # job row (bags column, its long-standing meaning) PLUS exactly one
    # production row linked by job_id carrying the same count, the bag
    # source, the shift times and any filter powder. Every bag
    # total in the system reads exactly one of the two tables (warehouse
    # / split / register / theka read production; powder tons + loss %
    # read jobs), so a merged save can never double count. Payloads
    # without "out_bags" (old API calls, demo data) keep the exact
    # legacy behaviour: job only. The production row is written when
    # there are powder bags OR filter powder (a filter-only output is
    # still production output).
    # BOTH outputs are counted in BAGS at this mill: filter powder
    # arrives as "filter_bags"; older payloads / Excel files may still
    # send the amount in kg ("filter_kg") — accepted and stored as kg
    # on the row. A row carries one or the other, never both.
    # The per-bag weights are STAMPED on the production row at save
    # time: an explicit payload weight wins (the Excel module carries
    # the weights with the file), otherwise the mill's current
    # bag-weight defaults apply — so changing a default later never
    # rewrites a saved record's tons. No weight is ever collected
    # per-entry on the form itself.
    merged = "out_bags" in d
    filter_bags = 0.0
    filter_kg = 0.0
    pb_kg = fb_kg = 50.0
    if merged:
        _fb = float(d.get("filter_bags") or 0)
        _fkg = float(d.get("filter_kg") or 0)
        if _fb > 0:
            filter_bags = _fb
        elif _fkg > 0:
            filter_kg = _fkg
        _bw = bag_weights(con)
        pb_kg = _resolve_bagw(d.get("powder_bag_kg"), _bw["powder_bag_kg"])
        fb_kg = _resolve_bagw(d.get("filter_bag_kg"), _bw["filter_bag_kg"])
    wt = d.get("tons", d.get("weight_tons"))
    if wt is not None:
        tons = float(wt)
        out_bags = int(d.get("bags") or 0)
    else:
        tons = round(int(float(d.get("bags") or 0)) * bag_kg(con) / 1000.0, 3)
        out_bags = 0
    if merged:
        out_bags = int(d.get("out_bags") or 0)
    rate = float(d.get("rate_per_ton") or 0)
    shift = d.get("shift") if d.get("shift") in ("Day", "Night") else "Day"
    cur = con.execute(
        "INSERT INTO grinding_jobs(date,party_id,tons,rate_per_ton,grade_pct,bags,shift,amount,note)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), d.get("party_id") or None, tons, rate,
         float(d.get("grade_pct") or 0), out_bags, shift,
         tons * rate, d.get("note", "")))
    jid = cur.lastrowid
    prod_id = None
    if merged and (out_bags > 0 or filter_bags > 0 or filter_kg > 0):
        src = d.get("bag_source") if d.get("bag_source") in ("mill", "client") else "mill"
        pc = con.execute(
            "INSERT INTO production(date,bags,party_id,job_id,kind,bag_source,entered_by,"
            "start_time,end_time,filter_kg,powder_bag_kg,filter_bags,filter_bag_kg,note)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (d.get("date") or today(), out_bags, d.get("party_id") or None,
             jid, "local", src, (u or {}).get("username", ""),
             d.get("start_time", "") or "", d.get("end_time", "") or "",
             filter_kg, pb_kg, filter_bags, fb_kg, d.get("note", "")))
        prod_id = pc.lastrowid
    con.commit()
    return {"ok": True, "id": jid, "amount": tons * rate,
            "production_id": prod_id}

def _trade_item(d, default):
    it = d.get("item")
    return it if it in ("rock", "powder", "other") else default


def _trade_source(d, default="ledger"):
    src = d.get("source")
    return src if src in ("ledger", "excel", "direct", "gate", "outside") else default


def _purchase_figures(item, d):
    """Derived money/weight figures for a purchase row of the given item
    kind. Rock keeps the legacy billed logic EXACTLY (deduction on the
    weighed tons); powder bills the full tons; 'other' bills qty x
    unit rate and carries no weight at all."""
    if item == "other":
        qty = float(d.get("qty") or 0); urate = float(d.get("unit_rate") or 0)
        return {"tons": 0.0, "grade_pct": 0.0, "rate_per_ton": 0.0,
                "deduction_pct": 0.0, "billed_tons": 0.0,
                "amount": round(qty * urate, 2), "bags": 0,
                "qty": qty, "unit_rate": urate}
    tons = float(d.get("tons") or 0); rate = float(d.get("rate_per_ton") or 0)
    if item == "powder":
        return {"tons": tons, "grade_pct": float(d.get("grade_pct") or 0),
                "rate_per_ton": rate, "deduction_pct": 0.0,
                "billed_tons": tons, "amount": round(tons * rate, 2),
                "bags": int(d.get("bags") or 0), "qty": 0.0, "unit_rate": 0.0}
    ded = float(d.get("deduction_pct") or 0)
    billed = round(tons * (1 - ded / 100.0), 3)
    return {"tons": tons, "grade_pct": float(d.get("grade_pct") or 0),
            "rate_per_ton": rate, "deduction_pct": ded,
            "billed_tons": billed, "amount": billed * rate,
            "bags": 0, "qty": 0.0, "unit_rate": 0.0}


def _sale_figures(item, d):
    """Derived figures for a sale row. Powder (and rock) bill tons x
    rate; 'other' bills qty x unit rate with no weight."""
    if item == "other":
        qty = float(d.get("qty") or 0); urate = float(d.get("unit_rate") or 0)
        return {"tons": 0.0, "bags": 0, "rate_per_ton": 0.0,
                "amount": round(qty * urate, 2), "qty": qty, "unit_rate": urate}
    tons = float(d.get("tons") or 0); rate = float(d.get("rate_per_ton") or 0)
    return {"tons": tons, "bags": int(d.get("bags") or 0) if item == "powder" else 0,
            "rate_per_ton": rate, "amount": round(tons * rate, 2),
            "qty": 0.0, "unit_rate": 0.0}


def create_purchase(con, d, u):
    item = _trade_item(d, "rock")
    src = _trade_source(d)
    f = _purchase_figures(item, d)
    cur = con.execute(
        "INSERT INTO purchases(date,party_id,tons,grade_pct,rate_per_ton,deduction_pct,"
        "billed_tons,amount,note,item,item_name,qty,unit,unit_rate,bags,source,deal_id)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), int(d["party_id"]), f["tons"], f["grade_pct"],
         f["rate_per_ton"], f["deduction_pct"], f["billed_tons"], f["amount"],
         d.get("note", ""), item, (d.get("item_name") or "").strip(),
         f["qty"], (d.get("unit") or "").strip(), f["unit_rate"], f["bags"],
         src, d.get("deal_id") or ""))
    con.commit()
    return {"ok": True, "id": cur.lastrowid, "billed_tons": f["billed_tons"],
            "amount": f["amount"], "item": item, "source": src}


def create_sale(con, d, u):
    item = _trade_item(d, "powder")
    src = _trade_source(d)
    og_fac = None
    if src == "outside":
        # powder sold FROM an outside factory: it draws on that
        # factory's powder-at-factory balance (bills), never on godam
        og_fac = d.get("og_factory_id") or d.get("factory_id")
        if not og_fac:
            raise ValueError("outside sale ke liye factory lazmi hai")
        og_fac = int(og_fac)
        bags_req = float(d.get("bags") or 0)
        if bags_req <= 0:
            raise ValueError("outside sale ke liye bags lazmi hain")
        if bags_req > _og_powder_left_bags(con, og_fac) + 0.0011:
            raise ValueError("is factory ke paas itna powder baqi nahi hai")
        if not float(d.get("tons") or 0):
            d = dict(d)
            d["tons"] = _og_powder_t(bags_req, bag_weights(con)["powder_bag_kg"])
    f = _sale_figures(item, d)
    _dup_match = None
    if item == "powder" and src not in ("direct", "outside"):
        # Duplicate-sale guard (owner, 28 Oct 2026): this powder may
        # already have been sold to the same buyer on an Own Vehicle
        # Out trip (sale recorded on the trip) inside the window —
        # saving would post the receivable + stock-out twice. The
        # Excel importer shares this function, so a matching import
        # row lands in its error list instead of double-posting.
        _dup_match = _dup_guard_sale_side(con, d, int(d["party_id"]),
                                          d.get("date") or today(), f["tons"])
    cur = con.execute(
        "INSERT INTO sales(date,party_id,tons,bags,rate_per_ton,amount,order_id,irn,note,"
        "item,item_name,qty,unit,unit_rate,source,trip_id,deal_id,og_factory_id)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), int(d["party_id"]), f["tons"], f["bags"],
         f["rate_per_ton"], f["amount"], d.get("order_id") or None, "",
         d.get("note", ""), item, (d.get("item_name") or "").strip(),
         f["qty"], (d.get("unit") or "").strip(), f["unit_rate"], src,
         d.get("trip_id") or None, d.get("deal_id") or "", og_fac))
    sid = cur.lastrowid
    inv = "INV-%04d" % sid
    con.execute("UPDATE sales SET invoice_no=? WHERE id=?", (inv, sid))
    if _dup_match is not None:
        audit(con, u["username"], "duplicate_sale_override",
              "ledger sell #%d party %d: powder own OUT trip #%d par pehle bik "
              "chuka tha — confirm karke save hui"
              % (sid, int(d["party_id"]), _dup_match["id"]))
    con.commit()
    return {"ok": True, "id": sid, "amount": f["amount"], "invoice_no": inv,
            "item": item, "source": src}


# ------------------------------------------------------- outside grinding --
# FINAL model (owner redesign, 28 Oct 2026): rock travels DIRECTLY from
# a mine/seller to an OUTSIDE factory — it never enters our godam, and
# the powder never comes back either; it is sold from there.
#   * 'sent' rows: the movement (mine -> factory) + the AGREED grinding
#     rate. A rock rate, when given, posts a Purchase payable to the
#     SELLER (synthesised in party_ledger). NO grinding charge posts at
#     send time — the rate on the row is just the agreement.
#   * 'bill' rows ("Grinding Bill"): recorded when settling with the
#     factory — powder ground (bags, stamped kg; tons derived), the
#     ACTUAL rock used (prefilled with a suggestion, editable), and the
#     rate (auto from the latest send agreement). The charge (powder
#     tons x rate) accrues HERE, as a payable CREDIT under the Grinding
#     head in the factory's khata — OUR payable, the factory's earnings,
#     exactly like a Purchase credit sits for a seller. An optional
#     paid-now leg posts a normal money-out payment in the same save
#     (payments.og_bill_id links it to the bill).
#   * 'received' rows are round-9 legacy: progress only (powder at the
#     factory; consumed derived read-time). Round-9 send rows stored a
#     charge in `amount` that the old code posted at send time; the new
#     readers NEVER post a send-row amount, so legacy charges cannot
#     double with bills — charges read bills only.
# Stock at a factory is derived read-time from sends + bills + outside
# sales; every godam reader excludes outside figures entirely.

def _og_powder_t(bags, bag_kg):
    return round(float(bags or 0) * float(bag_kg or 50) / 1000.0, 3)

def _og_suggest_used(con, powder_t):
    """Prefill for a bill's rock-used: powder grossed up by the mill's
    default wastage % — powder / (1 - wastage%). Editable to actuals."""
    pct = wastage_pct(con)
    if not powder_t or pct >= 100:
        return round(float(powder_t or 0), 3)
    return round(float(powder_t) / (1 - pct / 100.0), 3)

def _og_consumed(con, r):
    """Rock consumed by one progress row (bill / legacy received)."""
    if r["rock_used_t"] is not None:
        return float(r["rock_used_t"])
    return _og_suggest_used(con, float(r["tons"] or 0))

def _og_sent_upto(con, factory_id, date_str):
    return con.execute("SELECT COALESCE(SUM(tons),0) s FROM outside_grinding "
                       "WHERE party_id=? AND kind='sent' AND date<=?",
                       (factory_id, date_str)).fetchone()["s"] or 0

def _og_remaining_at(con, factory_id, date_str, exclude_id=None):
    """Rock still lying at the factory as of a date: sent - used."""
    used = 0.0
    for r in con.execute("SELECT * FROM outside_grinding WHERE party_id=? "
                         "AND kind IN ('bill','received') AND date<=?",
                         (factory_id, date_str)):
        if exclude_id is not None and r["id"] == exclude_id:
            continue
        used += _og_consumed(con, r)
    return round(_og_sent_upto(con, factory_id, date_str) - used, 3)

def _og_first_send(con, factory_id):
    r = con.execute("SELECT MIN(date) m FROM outside_grinding "
                    "WHERE party_id=? AND kind='sent'", (factory_id,)).fetchone()
    return r["m"] if r else None

def _og_agreement_rate(con, factory_id):
    r = con.execute("SELECT rate_per_ton FROM outside_grinding "
                    "WHERE party_id=? AND kind='sent' ORDER BY date DESC, id DESC",
                    (factory_id,)).fetchone()
    return float(r["rate_per_ton"] or 0) if r else 0.0

def _og_powder_left_bags(con, factory_id, exclude_sale_id=None):
    made = con.execute("SELECT COALESCE(SUM(bags),0) s FROM outside_grinding "
                       "WHERE party_id=? AND kind IN ('bill','received')",
                       (factory_id,)).fetchone()["s"] or 0
    sold = 0.0
    for r in con.execute("SELECT id, bags FROM sales WHERE "
                         "COALESCE(source,'')='outside' AND og_factory_id=?",
                         (factory_id,)):
        if exclude_sale_id is not None and r["id"] == exclude_sale_id:
            continue
        sold += float(r["bags"] or 0)
    return round(float(made) - sold, 3)

def _og_bill_payment(con, bill_id):
    return con.execute("SELECT * FROM payments WHERE og_bill_id=?",
                       (bill_id,)).fetchone()

def _og_sync_bill_payment(con, bill_id, date, factory_id, paid_now, method, u):
    """Keep a bill's paid-now payment leg exactly in step with the bill:
    created / amount-updated / recycled-away in the bill's own save, so
    an edit moves the payment exactly once."""
    pay = _og_bill_payment(con, bill_id)
    paid_now = float(paid_now or 0)
    if paid_now > 0:
        if pay:
            con.execute("UPDATE payments SET date=?, amount=?, method=? WHERE id=?",
                        (date, paid_now, method or pay["method"] or "cash", pay["id"]))
        else:
            con.execute("INSERT INTO payments(date,party_id,direction,amount,method,note,og_bill_id)"
                        " VALUES(?,?,'out',?,?,?,?)",
                        (date, factory_id, paid_now, method or "cash",
                         "Outside grinding bill #%d" % bill_id, bill_id))
    elif pay:
        pd = {k: pay[k] for k in pay.keys()}
        con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                    " VALUES(?,?,?,?,?)", (now_str(), "payments", pay["id"],
                                          json.dumps(pd), u["username"]))
        con.execute("DELETE FROM payments WHERE id=?", (pay["id"],))

def outside_stock(con):
    """Per-factory position at outside mills + grand totals. Every
    figure derives read-time from sends + bills + outside sales."""
    names = {p["id"]: p["name"] for p in con.execute("SELECT id, name FROM parties")}
    facs = {}
    def F(fid):
        return facs.setdefault(fid, {
            "factory_id": fid, "factory": names.get(fid, "?"),
            "sent_t": 0.0, "rock_bought": 0.0, "ground_used_t": 0.0,
            "powder_bags": 0.0, "powder_t": 0.0, "wastage_t": 0.0,
            "sold_bags": 0.0, "sold_t": 0.0, "sold_amount": 0.0,
            "charges": 0.0, "paid": 0.0})
    for r in con.execute("SELECT * FROM outside_grinding ORDER BY date, id"):
        f = F(r["party_id"])
        if r["kind"] == "sent":
            f["sent_t"] += float(r["tons"] or 0)
            f["rock_bought"] += float(r["rock_amount"] or 0)
        elif r["kind"] in ("bill", "received"):
            used = _og_consumed(con, r)
            f["ground_used_t"] += used
            f["powder_bags"] += float(r["bags"] or 0)
            f["powder_t"] += float(r["tons"] or 0)
            f["wastage_t"] += used - float(r["tons"] or 0)
            if r["kind"] == "bill":
                f["charges"] += float(r["amount"] or 0)
    for r in con.execute("SELECT * FROM sales WHERE COALESCE(source,'')='outside' "
                         "AND og_factory_id IS NOT NULL"):
        f = F(int(r["og_factory_id"]))
        f["sold_bags"] += float(r["bags"] or 0)
        f["sold_t"] += float(r["tons"] or 0)
        f["sold_amount"] += float(r["amount"] or 0)
    for r in con.execute("SELECT party_id, COALESCE(SUM(amount),0) s FROM payments "
                         "WHERE direction='out' GROUP BY party_id"):
        if r["party_id"] in facs:
            facs[r["party_id"]]["paid"] += float(r["s"] or 0)
    out = []
    for f in facs.values():
        f["sent_t"] = round(f["sent_t"], 3)
        f["ground_used_t"] = round(f["ground_used_t"], 3)
        f["powder_t"] = round(f["powder_t"], 3)
        f["remaining_t"] = round(f["sent_t"] - f["ground_used_t"], 3)
        f["wastage_t"] = round(f["wastage_t"], 3)
        f["wastage_pct"] = (round(f["wastage_t"] / f["ground_used_t"] * 100, 2)
                            if f["ground_used_t"] else 0.0)
        f["powder_left_bags"] = round(f["powder_bags"] - f["sold_bags"], 3)
        f["powder_left_t"] = round(f["powder_t"] - f["sold_t"], 3)
        f["rock_bought"] = round(f["rock_bought"], 2)
        f["charges"] = round(f["charges"], 2)
        f["paid"] = round(f["paid"], 2)
        _e, bal = party_ledger(con, f["factory_id"])
        f["balance"] = round(bal, 2)
        out.append(f)
    tot = {"sent_t": 0.0, "ground_used_t": 0.0, "remaining_t": 0.0,
           "powder_bags": 0.0, "powder_t": 0.0, "powder_left_bags": 0.0,
           "powder_left_t": 0.0, "wastage_t": 0.0, "sold_bags": 0.0,
           "sold_amount": 0.0, "charges": 0.0}
    for f in out:
        for k in tot:
            tot[k] = round(tot[k] + float(f.get(k) or 0), 3)
    return {"factories": out, "totals": tot}

def create_outside(con, d, u):
    """Outside Grinding entries (see the model note above).
    kind 'sent': mine -> factory movement + agreed rate (+ optional
    rock rate posting a Purchase payable to the seller). NO charge.
    kind 'bill': a Grinding Bill — powder ground + actual rock used +
    rate; the charge accrues here (Grinding-head payable CREDIT in the
    factory's khata: OUR payable, never a receivable from them), plus an
    optional paid-now payment leg in the same save.
    kind 'received': round-9 legacy progress rows (imports only)."""
    kind = d.get("kind") if d.get("kind") in ("sent", "bill", "received") else "sent"
    pid = int(d["party_id"])
    date = d.get("date") or today()
    if kind == "sent":
        tons = float(d.get("tons") or 0)
        rate = float(d.get("rate_per_ton") or 0)
        rock_rate = float(d.get("rock_rate") or 0)
        from_pid = d.get("from_party_id") or None
        if from_pid:
            from_pid = int(from_pid)
        rock_amount = round(tons * rock_rate, 2) if (rock_rate > 0 and from_pid) else 0.0
        cur = con.execute(
            "INSERT INTO outside_grinding(date,kind,party_id,tons,grade_pct,rate_per_ton,"
            "amount,bags,bag_kg,vehicle_no,note,from_party_id,rock_rate,rock_amount)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (date, kind, pid, tons, float(d.get("grade_pct") or 0), rate, 0, 0, 50,
             d.get("vehicle_no", ""), d.get("note", ""), from_pid, rock_rate, rock_amount))
        audit(con, u["username"], "create", "outside grinding #%d (sent)" % cur.lastrowid)
        con.commit()
        return {"ok": True, "id": cur.lastrowid, "kind": "sent", "amount": 0,
                "rock_amount": rock_amount}
    bags = float(d.get("bags") or 0)
    kg = _resolve_bagw(d.get("bag_kg"), bag_weights(con)["powder_bag_kg"])
    tons = _og_powder_t(bags, kg)
    if kind == "received":
        cur = con.execute(
            "INSERT INTO outside_grinding(date,kind,party_id,tons,grade_pct,rate_per_ton,"
            "amount,bags,bag_kg,vehicle_no,note) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (date, kind, pid, tons, 0, 0, 0, bags, kg,
             d.get("vehicle_no", ""), d.get("note", "")))
        audit(con, u["username"], "create", "outside grinding #%d (received)" % cur.lastrowid)
        con.commit()
        return {"ok": True, "id": cur.lastrowid, "kind": "received", "amount": 0}
    # ---- Grinding Bill ------------------------------------------------
    first = _og_first_send(con, pid)
    if first and date < first:
        raise ValueError("bill ki date is factory ki pehli Rock Sent se pehle nahi ho sakti")
    if d.get("rock_used_t") in (None, ""):
        used = _og_suggest_used(con, tons)
    else:
        used = float(d["rock_used_t"])
    if used < tons - 0.0011:
        raise ValueError("rock used powder se kam nahi ho sakta — wastage hamesha plus hoti hai")
    if used > _og_remaining_at(con, pid, date) + 0.0011:
        raise ValueError("is factory ke paas bill se pehle itna rock baqi nahi hai")
    rate = d.get("rate_per_ton")
    rate = float(rate) if rate not in (None, "") else _og_agreement_rate(con, pid)
    charge = round(tons * rate, 2)
    cur = con.execute(
        "INSERT INTO outside_grinding(date,kind,party_id,tons,grade_pct,rate_per_ton,"
        "amount,bags,bag_kg,vehicle_no,note,rock_used_t,wastage_t)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (date, "bill", pid, tons, 0, rate, charge, bags, kg,
         d.get("vehicle_no", ""), d.get("note", ""), used, round(used - tons, 3)))
    bid = cur.lastrowid
    _og_sync_bill_payment(con, bid, date, pid, d.get("paid_now"),
                          d.get("pay_method") or d.get("method"), u)
    audit(con, u["username"], "create", "outside grinding bill #%d" % bid)
    con.commit()
    return {"ok": True, "id": bid, "kind": "bill", "amount": charge,
            "rock_used_t": used, "wastage_t": round(used - tons, 3),
            "paid_now": float(d.get("paid_now") or 0)}


def create_direct_deal(con, d, u):
    """DIRECT TRADE: buy from party A, sell the SAME goods to party B —
    the goods never enter the mill. Two rows (purchase for A, sale for
    B) linked by one deal_id, both source='direct'; stock readers
    exclude direct rows, so neither leg moves any stock. Profit =
    sale amount - purchase (billed) amount."""
    import time as _t
    deal_id = "D%d" % int(_t.time() * 1000)
    item = _trade_item(d, "rock")
    base = {"date": d.get("date") or today(), "item": item,
            "item_name": d.get("item_name") or "", "unit": d.get("unit") or "",
            "tons": d.get("tons"), "bags": d.get("bags"),
            "grade_pct": d.get("grade_pct"), "qty": d.get("qty"),
            "note": d.get("note", ""), "source": "direct", "deal_id": deal_id}
    buy = dict(base, party_id=int(d["buy_party_id"]),
               rate_per_ton=d.get("buy_rate"), unit_rate=d.get("buy_unit_rate"),
               deduction_pct=d.get("deduction_pct"))
    sell = dict(base, party_id=int(d["sell_party_id"]),
                rate_per_ton=d.get("sell_rate"), unit_rate=d.get("sell_unit_rate"))
    pr = create_purchase(con, buy, u)
    sr = create_sale(con, sell, u)
    audit(con, u["username"], "create", "direct deal %s" % deal_id)
    con.commit()
    return {"ok": True, "deal_id": deal_id, "purchase_id": pr["id"],
            "sale_id": sr["id"], "purchase_amount": pr["amount"],
            "sale_amount": sr["amount"],
            "profit": round(sr["amount"] - pr["amount"], 2)}

def create_order(con, d, u):
    cur = con.execute(
        "INSERT INTO orders(date,party_id,tons,bags,rate_per_ton,expected_date,note)"
        " VALUES(?,?,?,?,?,?,?)",
        (d.get("date") or today(), int(d["party_id"]), float(d.get("tons") or 0),
         int(d.get("bags") or 0), float(d["rate_per_ton"]), d.get("expected_date", ""),
         d.get("note", "")))
    con.commit()
    return {"ok": True, "id": cur.lastrowid}

def create_production(con, d, u):
    # Same stamping rule as the merged entry: an explicit per-bag weight
    # in the payload wins, else the mill's current bag-weight defaults;
    # filter powder may arrive as bags ("filter_bags") or, from older
    # payloads, directly in kg ("filter_kg").
    _bw = bag_weights(con)
    pb_kg = _resolve_bagw(d.get("powder_bag_kg"), _bw["powder_bag_kg"])
    fb_kg = _resolve_bagw(d.get("filter_bag_kg"), _bw["filter_bag_kg"])
    _fb = float(d.get("filter_bags") or 0)
    _fkg = float(d.get("filter_kg") or 0)
    if _fb > 0:
        f_bags, f_kg = _fb, 0.0
    elif _fkg > 0:
        f_bags, f_kg = 0.0, _fkg
    else:
        f_bags, f_kg = 0.0, 0.0
    cur = con.execute(
        "INSERT INTO production(date,bags,party_id,job_id,kind,bag_source,entered_by,"
        "start_time,end_time,filter_kg,powder_bag_kg,filter_bags,filter_bag_kg,note)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), int(d["bags"]), d.get("party_id") or None,
         d.get("job_id") or None, d.get("kind") or "local",
         d.get("bag_source") or "mill", u["username"],
         d.get("start_time", "") or "", d.get("end_time", "") or "",
         f_kg, pb_kg, f_bags, fb_kg, d.get("note", "")))
    con.commit()
    return {"ok": True, "id": cur.lastrowid}

def create_worker(con, d, u):
    cur = con.execute(
        "INSERT INTO workers(name,kind,rate_per_ton,rate_per_bag,monthly_salary,phone,"
        "department_id,device_code,start_date) VALUES(?,?,?,?,?,?,?,?,?)",
        (d["name"].strip(), d.get("kind") or "theka",
         float(d.get("rate_per_ton") or 0), float(d.get("rate_per_bag") or 0),
         float(d.get("monthly_salary") or 0), d.get("phone", ""),
         d.get("department_id") or None, d.get("device_code", ""),
         d.get("start_date") or today()))
    con.commit()
    return {"ok": True, "id": cur.lastrowid}

def create_payment(con, d, u):
    cur = con.execute(
        "INSERT INTO payments(date,party_id,direction,amount,method,bank_name,online_channel,ref_no,note)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), int(d["party_id"]), d["direction"],
         float(d["amount"]), d.get("method") or "cash", d.get("bank_name", ""),
         d.get("online_channel", ""), (d.get("ref_no") or "").strip(), d.get("note", "")))
    pay_id = cur.lastrowid
    if (d.get("method") or "") == "cheque":
        con.execute(
            "INSERT INTO cheques(payment_id,party_id,cheque_no,bank,due_date,amount,status)"
            " VALUES(?,?,?,?,?,?,'pending')",
            (pay_id, int(d["party_id"]), d.get("cheque_no", ""), d.get("bank_name", ""),
             d.get("due_date", ""), float(d["amount"])))
    con.commit()
    return {"ok": True, "id": pay_id}

def create_expense(con, d, u):
    """Expense with payment attribution. paid_kind: owner | manager | other.
    A manager/staff-paid CASH expense above the approval limit is saved as
    'pending' (still in P&L + holder spent until the owner rejects it) and
    raises exactly one owner alert. Warnings never block the save."""
    method = (d.get("method") or "cash").strip().lower()
    if method == "cheque":          # new UI expresses cheque as Bank + ref
        method = "bank"
    if method not in ("cash", "bank", "online"):
        method = "cash"
    amount = float(d["amount"])
    # ---- who physically paid (attribution) ----
    paid_kind = (d.get("paid_kind") or "").strip().lower()
    holder = (d.get("paid_by_holder") or "").strip()
    paid_name = (d.get("paid_name") or "").strip()
    legacy_by = (d.get("paid_by") or "").strip()
    if paid_kind not in ("owner", "manager", "other"):
        if holder.startswith("user:"):
            paid_kind = "manager"
        elif legacy_by.lower() in ("owner", "malik", "self", "owner (self)"):
            paid_kind = "owner"
        elif legacy_by:
            paid_kind, paid_name = "other", paid_name or legacy_by
        else:
            paid_kind = "other"
    if paid_kind == "owner":
        holder, paid_by = "", "Owner"
    elif paid_kind == "manager":
        uid = None
        if holder.startswith("user:"):
            try:
                uid = int(holder.split(":", 1)[1])
            except ValueError:
                uid = None
        w = con.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone() if uid else None
        if not w:
            raise ValueError("Paid By wala user (manager/staff) nahi mila")
        holder, paid_by = "user:%d" % uid, w["username"]
    else:
        nm = paid_name or legacy_by
        holder = ("name:" + nm) if nm else ""
        paid_by = nm
    # ---- cash-in-hand link + approval status ----
    rules = cash_rules(con)
    status, warning, big = "approved", "", False
    if method == "cash" and holder:
        bal = holder_balance(con, holder)
        if amount > bal:
            warning = ("balance se zyada kharcha — %s ke paas Rs %s thay, kharcha Rs %s"
                       % (paid_by, "{:,.0f}".format(bal), "{:,.0f}".format(amount)))
    if method == "cash" and paid_kind == "manager" and amount > rules["approval_limit"]:
        status, big = "pending", True
    cur = con.execute(
        "INSERT INTO expenses(date,category,head_id,sub_head_id,amount,paid_by,paid_to,method,note,"
        "paid_kind,paid_by_holder,pay_channel,pay_ref,status)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), d.get("category", ""),
         d.get("head_id") or None, d.get("sub_head_id") or None,
         amount, paid_by, d.get("paid_to", ""), method, d.get("note", ""),
         paid_kind, holder, (d.get("pay_channel") or "").strip(),
         (d.get("pay_ref") or "").strip(), status))
    exp_id = cur.lastrowid
    if big:
        msg = ("Manager %s ne Rs %s ka kharcha kiya (approval pending)"
               % (paid_by, "{:,.0f}".format(amount)))
        try:
            notify_owner(con, "big_expense", msg)
        except Exception:
            pass
    con.commit()
    if big:
        try:
            owa = meta_get(con, "owner_whatsapp", "")
            if owa:
                make_alert(con, "big_expense", None, owa, msg, [])
        except Exception:
            pass
    return {"ok": True, "id": exp_id, "status": status, "warning": warning}

# --------------------------------------------------- owner edits ---------
# The edit paths behind the owner-only gate (_entry_mutation). Every
# ledger / stock figure in this system is DERIVED from the entry rows
# at read time — party_ledger computes a trip's freight / loading /
# grinding / purchase / rent lines from the trips row itself, and the
# warehouse, day-night split, register and theka figures read the
# grinding job + its linked production row. An edit therefore never
# writes reversal entries: it updates the stored row(s) in ONE
# transaction, which reposts the world exactly as if the corrected
# entry had been made once — no duplicate or orphan lines can exist,
# and moving an entry to another party (or another buy-from seller)
# moves its postings with it.

def _pick(d, row, key):
    """Edit merge: a field the payload carries wins; an absent field
    keeps its stored value."""
    return d[key] if key in d else row[key]

def _row_or_404(con, table, rid):
    r = con.execute("SELECT * FROM %s WHERE id=?" % table, (int(rid),)).fetchone()
    if not r:
        raise LookupError("record nahi mila")
    return r

def _upd_row(con, table, rid, sets):
    con.execute("UPDATE %s SET %s WHERE id=?" % (
        table, ",".join("%s=?" % k for k in sets)),
        tuple(sets.values()) + (int(rid),))

def update_trip(con, d, u):
    """Edit a stored vehicle trip. The direction and the entered_by
    stamp never change (the IN / OUT pages are separate; the voucher
    keeps naming who made the entry — the audit log names the editor).
    Every charge derivation mirrors create_trip, run on the merged
    (payload-over-stored) values, so the khata lines are recomputed
    from the corrected row alone. No voucher alerts are re-fired for a
    correction; the response carries fresh one-tap links for the
    corrected voucher instead."""
    old = _row_or_404(con, "trips", d["id"])
    tid = old["id"]
    direction = old["direction"]
    keys = ("date", "party_id", "vehicle_no", "driver", "driver_phone",
            "bags", "grade_pct", "freight", "freight_payer", "kind",
            "loading", "charge_bearer", "order_id", "note", "grind_rate",
            "rock_rate", "rate_type", "rent", "buy_from_party_id", "rent_to",
            "sale_buyer_id", "sale_rate")
    m = {k: _pick(d, old, k) for k in keys}
    pid = m["party_id"] or None
    veh = (m["vehicle_no"] or "").strip()
    # weights: a payload carrying gross/tare derives net from them
    # (legacy style); otherwise the payload's net IS the weight (the
    # form's way — stored gross = net, tare = 0, exactly as on create)
    if "gross_kg" in d or "tare_kg" in d:
        gross = float(_pick(d, old, "gross_kg") or 0)
        tare = float(_pick(d, old, "tare_kg") or 0)
        net = gross - tare if gross else float(_pick(d, old, "net_kg") or 0)
    else:
        net = float(_pick(d, old, "net_kg") or 0)
        gross, tare = net, 0.0
    if veh and tare:
        con.execute("INSERT INTO vehicle_tares(vehicle_no,tare_kg) VALUES(?,?)"
                    " ON CONFLICT(vehicle_no) DO UPDATE SET tare_kg=excluded.tare_kg",
                    (veh, tare))
    bags_out = int(m["bags"] or 0)
    if direction == "IN":
        bags_out = 0   # rock never arrives in bags — see create_trip
    # fx (stock effect): legacy rows (fx '') keep their stamp on an
    # ordinary edit — a legacy gate-sale trip's money/stock keeps
    # riding on its linked sale row, and no legacy read changes. The
    # stamp is recomputed only for new-model rows, or when the party
    # itself changes (the dispatch then belongs to the new party's
    # world). IN trips never carry an fx.
    _old_fx = (old["fx"] or "") if "fx" in old.keys() else ""
    if direction == "OUT" and (_old_fx != "" or int(old["party_id"] or 0) != int(pid or 0)):
        _fx = _trip_fx(con, direction, pid)
    elif direction == "OUT":
        _fx = _old_fx
    else:
        _fx = ""
    # Powder-stock gate (Talha, 28 Oct 2026) — the same check as
    # create_trip, with this trip's own previous net added back
    # inside the gate when it deducted from the same pool, so an
    # unchanged re-save can never trip it.
    _stock_ovr = _powder_stock_gate(con, direction, _fx, pid, net, d, old=old)
    warning = ""
    if direction == "OUT" and pid and bags_out and _fx in ("party", ""):
        ready = party_stock(con, int(pid))["bags_ready"]
        if int(old["party_id"] or 0) == int(pid):
            ready += int(old["bags"] or 0)   # this trip's own dispatch is being replaced
        if bags_out > ready:
            warning = ("WARNING: %d bags bheje ja rahe hain lekin party ke ready bags sirf %d hain "
                       "(godam stock ka hisaab bigar sakta hai)" % (bags_out, ready))
    if direction == "IN":
        _loading = 0.0; _unloading = 0.0
    else:
        _loading = float(m["loading"] or 0)
        # unloading is no longer collected; an edit preserves what an
        # old record already holds unless a value is explicitly sent
        _unloading = float(d["unloading"] or 0) if "unloading" in d else float(old["unloading"] or 0)
    _grind_rate = float(m["grind_rate"] or 0) if direction == "OUT" else 0.0
    _grind_charge = round(net / 1000.0 * _grind_rate, 2) if _grind_rate > 0 else 0.0
    if direction == "OUT" and not pid:
        # Own dispatch: no grinding charge can ever post (see
        # create_trip) — an edit zeroes a stored/submitted rate too.
        _grind_rate = 0.0
        _grind_charge = 0.0
    _rock_rate = float(m["rock_rate"] or 0) if direction == "IN" else 0.0
    _rate_type = ""
    _rent = 0.0
    if _rock_rate > 0:
        _rate_type = "mine" if m["rate_type"] == "mine" else "factory"
        if _rate_type == "mine":
            _rent = float(m["rent"] or 0)
    # rent receiver follows the same rule as create: driver only on a
    # Mine rate; flipping it reposts the rent exactly once, because
    # both the seller khata and the mill totals derive from this row
    _rent_to = "driver" if (_rate_type == "mine" and m["rent_to"] == "driver") else "seller"
    _freight = float(m["freight"] or 0)
    if _rate_type == "factory":
        _freight = 0.0
    _order_id = (m["order_id"] or None) if direction == "OUT" else None
    _buy_from = None
    if direction == "IN":
        _bf_in = m["buy_from_party_id"] or None
        if _bf_in is not None and int(_bf_in) != (pid or 0):
            _buy_from = int(_bf_in)
    if direction == "IN" and pid:
        # Purchase block is Own-only (owner, 28 Oct 2026 — see
        # create_trip): a client-party IN trip is a grinding arrival
        # only. The guard runs on the MERGED values, so re-saving a
        # client IN trip that somehow still carries a stored rate
        # zeroes the whole purchase block on the row — from then on
        # no purchase/rent credit posts from it anywhere.
        _rock_rate = 0.0
        _rate_type = ""
        _rent = 0.0
        _rent_to = "seller"
        _buy_from = None
    # Own-dispatch sale on edit — same rule as create_trip, run on the
    # merged values: only an Own OUT trip may carry buyer + rate
    # (BOTH or NEITHER); because the receivable is derived from this
    # row at read time, the corrected buyer/rate/tons simply re-derive
    # everywhere — no sync, no second row. A LEGACY linked sale row
    # (round-9 gate sale) is a different mechanism and is left exactly
    # as it stands.
    _sale_buyer = None
    _sale_rate = 0.0
    _dup_match = None
    if direction == "OUT" and not pid:
        _sb = m["sale_buyer_id"] or None
        _sr = float(m["sale_rate"] or 0)
        if (_sb is None) != (_sr <= 0):
            raise ValueError("Powder sale ke DONO khane bharein — 'Powder sold to' "
                             "aur 'Sale rate /ton' — ya dono khali chhorein")
        if _sb is not None:
            if not con.execute("SELECT 1 FROM parties WHERE id=?",
                               (int(_sb),)).fetchone():
                raise ValueError("'Powder sold to' wali party system mein nahi mili")
            _sale_buyer = int(_sb)
            _sale_rate = _sr
            _dup_match = _dup_guard_trip_side(con, d, _sale_buyer,
                                              m["date"] or old["date"], net / 1000.0)
    con.execute(
        "UPDATE trips SET date=?,party_id=?,vehicle_no=?,driver=?,gross_kg=?,tare_kg=?,net_kg=?,"
        "bags=?,grade_pct=?,freight=?,freight_payer=?,kind=?,loading=?,unloading=?,charge_bearer=?,"
        "order_id=?,note=?,grind_rate=?,grind_charge=?,rock_rate=?,rate_type=?,rent=?,driver_phone=?,"
        "buy_from_party_id=?,rent_to=?,sale_buyer_id=?,sale_rate=?,fx=? WHERE id=?",
        (m["date"] or old["date"], pid, veh, m["driver"] or "", gross, tare, net,
         bags_out, float(m["grade_pct"] or 0), _freight, m["freight_payer"] or "mill",
         m["kind"] or "local", _loading, _unloading, m["charge_bearer"] or "party",
         _order_id, m["note"] or "", _grind_rate, _grind_charge, _rock_rate,
         _rate_type, _rent, (m["driver_phone"] or "").strip(), _buy_from,
         _rent_to, _sale_buyer, _sale_rate, _fx, tid))
    audit(con, u["username"], "update", "trip %s #%d %s net %g kg" % (direction, tid, veh, net))
    if _stock_ovr:
        audit(con, u["username"], "stock_override",
              "trip OUT #%d %s: powder stock %s t tha, %s t confirm karke edit hua"
              % (tid, veh, _t3(_stock_ovr["available_t"]), _t3(_stock_ovr["net_t"])))
        warning = (warning + " " if warning else "") + (
            "⚠ Stock me sirf %s t powder tha — %s t confirm karke edit hua"
            % (_t3(_stock_ovr["available_t"]), _t3(_stock_ovr["net_t"])))
    if _dup_match is not None:
        audit(con, u["username"], "duplicate_sale_override",
              "trip OUT #%d %s: party %d ki sale ledger sell #%d se milti thi — "
              "confirm karke edit hui" % (tid, veh, _sale_buyer, _dup_match["id"]))
    con.commit()
    sale_info = None
    if _sale_buyer:
        sale_info = {"buyer_id": _sale_buyer, "rate": _sale_rate,
                     "amount": round(net / 1000.0 * _sale_rate, 2)}
    trow = con.execute("SELECT * FROM trips WHERE id=?", (tid,)).fetchone()
    prow = con.execute("SELECT * FROM parties WHERE id=?", (pid,)).fetchone() if pid else None
    pname = prow["name"] if prow else "Own / Apna"
    tdict = dict(trow); tdict["party_name"] = pname
    vtext = voucher_text(con, tdict)
    owner_num = meta_get(con, "owner_whatsapp") or meta_get(con, "mill_phone")
    party_num = (prow["whatsapp"] or prow["phone"]) if prow else ""
    wa = {"wa_auto": False,
          "wa_party_url": _wa_me_url(party_num, vtext),
          "wa_driver_url": _wa_me_url((trow["driver_phone"] or "").strip(), vtext),
          "wa_owner_url": _wa_me_url(owner_num, vtext),
          "voucher_url": "/print/trip/%d" % tid}
    return {"ok": True, "id": tid, "net_kg": net, "warning": warning,
            "grind_charge": _grind_charge,
            "purchase_amount": round(net / 1000.0 * _rock_rate, 2) if _rock_rate > 0 else 0,
            "rent": _rent, "rent_to": _rent_to,
            "buy_from_party_id": _buy_from, "sale": sale_info, **wa}

def update_job(con, d, u):
    """Edit a Grinding & Production entry: the job row and its linked
    production row are updated as ONE entry (the production row is
    created when the corrected output rises from zero, and removed
    when it falls to zero), so the pair can never split and no total
    can count the bags twice. The production row keeps its stamped
    per-bag weights unless the payload carries explicit ones — an
    edit of counts never silently re-stamps weights."""
    old = _row_or_404(con, "grinding_jobs", d["id"])
    jid = old["id"]
    prod = con.execute("SELECT * FROM production WHERE job_id=?", (jid,)).fetchone()
    if "out_bags" not in d:
        # legacy-style edit (tons / rate payloads): job fields only
        tons = float(_pick(d, old, "tons") or 0)
        rate = float(_pick(d, old, "rate_per_ton") or 0)
        _sh = _pick(d, old, "shift")
        _upd_row(con, "grinding_jobs", jid, {
            "date": _pick(d, old, "date") or old["date"],
            "party_id": _pick(d, old, "party_id") or None,
            "tons": tons, "rate_per_ton": rate, "amount": tons * rate,
            "grade_pct": float(_pick(d, old, "grade_pct") or 0),
            "bags": int(_pick(d, old, "bags") or 0),
            "shift": _sh if _sh in ("Day", "Night") else old["shift"],
            "note": _pick(d, old, "note") or ""})
        audit(con, u["username"], "update", "grinding job #%d" % jid)
        con.commit()
        return {"ok": True, "id": jid, "amount": tons * rate,
                "production_id": prod["id"] if prod else None}
    out_bags = int(d.get("out_bags") or 0)
    _fb = float(d.get("filter_bags") or 0)
    _fkg = float(d.get("filter_kg") or 0)
    filter_bags = _fb if _fb > 0 else 0.0
    filter_kg = 0.0 if _fb > 0 else _fkg
    date = d.get("date") or old["date"]
    pid = d["party_id"] if "party_id" in d else old["party_id"]
    pid = pid or None
    _upd_row(con, "grinding_jobs", jid, {
        "date": date, "party_id": pid,
        "grade_pct": float(d["grade_pct"]) if "grade_pct" in d else float(old["grade_pct"] or 0),
        "bags": out_bags,
        "shift": d["shift"] if d.get("shift") in ("Day", "Night") else old["shift"],
        "note": d["note"] if "note" in d else (old["note"] or "")})
    prod_id = prod["id"] if prod else None
    if out_bags > 0 or filter_bags > 0 or filter_kg > 0:
        src = d.get("bag_source") if d.get("bag_source") in ("mill", "client") \
            else (prod["bag_source"] if prod else "mill")
        start = d["start_time"] if "start_time" in d else (prod["start_time"] if prod else "")
        end = d["end_time"] if "end_time" in d else (prod["end_time"] if prod else "")
        note = d["note"] if "note" in d else (old["note"] or "")
        if prod:
            _upd_row(con, "production", prod["id"], {
                "date": date, "bags": out_bags, "party_id": pid,
                "bag_source": src, "start_time": start or "", "end_time": end or "",
                "filter_kg": filter_kg, "filter_bags": filter_bags,
                "powder_bag_kg": _resolve_bagw(d.get("powder_bag_kg"), prod["powder_bag_kg"]),
                "filter_bag_kg": _resolve_bagw(d.get("filter_bag_kg"), prod["filter_bag_kg"]),
                "note": note})
        else:
            _bw = bag_weights(con)
            pc = con.execute(
                "INSERT INTO production(date,bags,party_id,job_id,kind,bag_source,entered_by,"
                "start_time,end_time,filter_kg,powder_bag_kg,filter_bags,filter_bag_kg,note)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (date, out_bags, pid, jid, "local", src, u["username"],
                 start or "", end or "", filter_kg,
                 _resolve_bagw(d.get("powder_bag_kg"), _bw["powder_bag_kg"]),
                 filter_bags,
                 _resolve_bagw(d.get("filter_bag_kg"), _bw["filter_bag_kg"]), note))
            prod_id = pc.lastrowid
    elif prod:
        # corrected to no output at all: the linked row goes with it
        con.execute("DELETE FROM production WHERE id=?", (prod["id"],))
        prod_id = None
    audit(con, u["username"], "update",
          "grinding & production #%d (%d bags)" % (jid, out_bags))
    con.commit()
    return {"ok": True, "id": jid, "production_id": prod_id}

def update_production(con, d, u):
    """Edit a production row directly. When the row is linked to a
    grinding job, the job's bags column (the same count, read by the
    powder-tons / loss figures) follows the correction, so the pair
    stays one entry."""
    old = _row_or_404(con, "production", d["id"])
    rid = old["id"]
    sets = {
        "date": _pick(d, old, "date") or old["date"],
        "bags": int(_pick(d, old, "bags") or 0),
        "party_id": _pick(d, old, "party_id") or None,
        "kind": _pick(d, old, "kind") or "local",
        "bag_source": _pick(d, old, "bag_source") or "mill",
        "start_time": _pick(d, old, "start_time") or "",
        "end_time": _pick(d, old, "end_time") or "",
        "note": _pick(d, old, "note") or "",
        "powder_bag_kg": _resolve_bagw(d.get("powder_bag_kg"), old["powder_bag_kg"]),
        "filter_bag_kg": _resolve_bagw(d.get("filter_bag_kg"), old["filter_bag_kg"]),
    }
    if "filter_bags" in d or "filter_kg" in d:
        _fb = float(d.get("filter_bags") or 0)
        _fkg = float(d.get("filter_kg") or 0)
        sets["filter_bags"] = _fb if _fb > 0 else 0.0
        sets["filter_kg"] = 0.0 if _fb > 0 else _fkg
    _upd_row(con, "production", rid, sets)
    if old["job_id"]:
        js = {"bags": sets["bags"]}
        if "date" in d:
            js["date"] = sets["date"]
        if "party_id" in d:
            js["party_id"] = sets["party_id"]
        _upd_row(con, "grinding_jobs", old["job_id"], js)
    audit(con, u["username"], "update", "production #%d" % rid)
    con.commit()
    return {"ok": True, "id": rid}

def update_party(con, d, u):
    old = _row_or_404(con, "parties", d["id"])
    roles = d.get("roles")
    _upd_row(con, "parties", old["id"], {
        "name": (d["name"].strip() if d.get("name") else old["name"]),
        "phone": _pick(d, old, "phone") or "",
        "whatsapp": _pick(d, old, "whatsapp") or "",
        "email": (_pick(d, old, "email") or "").strip(),
        "address": _pick(d, old, "address") or "",
        "roles": ",".join(roles) if isinstance(roles, list) else old["roles"],
        "credit_limit": float(_pick(d, old, "credit_limit") or 0),
        "opening_balance": float(_pick(d, old, "opening_balance") or 0),
        "open_date": _clean_open_date(d.get("open_date"))
                     or (old["open_date"] if "open_date" in old.keys() else "") or ""})
    # round 12: a party email also fills its client login's empty
    # email field, so both doors reach the same inbox
    _sync_party_user_email(con, old["id"], (_pick(d, old, "email") or ""),
                           from_user=False)
    audit(con, u["username"], "update", "party #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_purchase(con, d, u):
    old = _row_or_404(con, "purchases", d["id"])
    item = _trade_item(d, old["item"] or "rock")
    merged = {"tons": _pick(d, old, "tons"), "rate_per_ton": _pick(d, old, "rate_per_ton"),
              "deduction_pct": _pick(d, old, "deduction_pct"),
              "grade_pct": _pick(d, old, "grade_pct"), "bags": _pick(d, old, "bags"),
              "qty": _pick(d, old, "qty"), "unit_rate": _pick(d, old, "unit_rate")}
    f = _purchase_figures(item, merged)
    _upd_row(con, "purchases", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "party_id": int(_pick(d, old, "party_id")),
        "tons": f["tons"], "grade_pct": f["grade_pct"],
        "rate_per_ton": f["rate_per_ton"], "deduction_pct": f["deduction_pct"],
        "billed_tons": f["billed_tons"], "amount": f["amount"],
        "item": item, "item_name": _pick(d, old, "item_name") or "",
        "qty": f["qty"], "unit": _pick(d, old, "unit") or "",
        "unit_rate": f["unit_rate"], "bags": f["bags"],
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "purchase #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"], "billed_tons": f["billed_tons"],
            "amount": f["amount"], "item": item}

def update_sale(con, d, u):
    old = _row_or_404(con, "sales", d["id"])
    item = _trade_item(d, old["item"] or "powder")
    if (old["source"] or "") == "outside":
        item = "powder"          # factory sales are always powder
    merged = {"tons": _pick(d, old, "tons"), "rate_per_ton": _pick(d, old, "rate_per_ton"),
              "bags": _pick(d, old, "bags"), "qty": _pick(d, old, "qty"),
              "unit_rate": _pick(d, old, "unit_rate")}
    f = _sale_figures(item, merged)
    if (old["source"] or "") == "outside" and old["og_factory_id"]:
        if float(f["bags"] or 0) > _og_powder_left_bags(
                con, int(old["og_factory_id"]), exclude_sale_id=old["id"]) + 0.0011:
            raise ValueError("is factory ke paas itna powder baqi nahi hai")
    _dup_match = None
    if item == "powder" and (old["source"] or "ledger") not in ("direct", "outside"):
        # duplicate-sale guard on the merged values (see create_sale)
        _dup_match = _dup_guard_sale_side(con, d, int(_pick(d, old, "party_id")),
                                          _pick(d, old, "date") or old["date"],
                                          f["tons"])
    _upd_row(con, "sales", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "party_id": int(_pick(d, old, "party_id")),
        "tons": f["tons"], "bags": f["bags"],
        "rate_per_ton": f["rate_per_ton"], "amount": f["amount"],
        "order_id": _pick(d, old, "order_id") or None,
        "item": item, "item_name": _pick(d, old, "item_name") or "",
        "qty": f["qty"], "unit": _pick(d, old, "unit") or "",
        "unit_rate": f["unit_rate"],
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "sale #%d" % old["id"])
    if _dup_match is not None:
        audit(con, u["username"], "duplicate_sale_override",
              "ledger sell #%d party %d: powder own OUT trip #%d par pehle bik "
              "chuka tha — confirm karke edit hui"
              % (old["id"], int(_pick(d, old, "party_id")), _dup_match["id"]))
    con.commit()
    return {"ok": True, "id": old["id"], "amount": f["amount"],
            "invoice_no": old["invoice_no"], "item": item}


def update_outside(con, d, u):
    old = _row_or_404(con, "outside_grinding", d["id"])
    kind = old["kind"]
    pid = int(_pick(d, old, "party_id"))
    date = _pick(d, old, "date") or old["date"]
    if kind == "sent":
        tons = float(_pick(d, old, "tons") or 0)
        rate = float(_pick(d, old, "rate_per_ton") or 0)
        rock_rate = float(_pick(d, old, "rock_rate") or 0)
        from_pid = (d["from_party_id"] or None) if "from_party_id" in d \
            else old["from_party_id"]
        if from_pid:
            from_pid = int(from_pid)
        rock_amount = round(tons * rock_rate, 2) if (rock_rate > 0 and from_pid) else 0.0
        _upd_row(con, "outside_grinding", old["id"], {
            "date": date, "party_id": pid,
            "tons": tons, "grade_pct": float(_pick(d, old, "grade_pct") or 0),
            "rate_per_ton": rate, "amount": 0,
            "from_party_id": from_pid, "rock_rate": rock_rate,
            "rock_amount": rock_amount,
            "vehicle_no": _pick(d, old, "vehicle_no") or "",
            "note": _pick(d, old, "note") or ""})
        audit(con, u["username"], "update", "outside grinding #%d" % old["id"])
        con.commit()
        return {"ok": True, "id": old["id"], "kind": kind, "amount": 0,
                "rock_amount": rock_amount}
    if kind == "received":
        bags = float(_pick(d, old, "bags") or 0)
        kg = float(old["bag_kg"] or 50)
        _upd_row(con, "outside_grinding", old["id"], {
            "date": date, "party_id": pid,
            "bags": bags, "bag_kg": kg, "tons": _og_powder_t(bags, kg),
            "vehicle_no": _pick(d, old, "vehicle_no") or "",
            "note": _pick(d, old, "note") or ""})
        audit(con, u["username"], "update", "outside grinding #%d" % old["id"])
        con.commit()
        return {"ok": True, "id": old["id"], "kind": kind, "amount": 0}
    # ---- Grinding Bill edit: charge + progress + payment move once ---
    first = _og_first_send(con, pid)
    if first and date < first:
        raise ValueError("bill ki date is factory ki pehli Rock Sent se pehle nahi ho sakti")
    bags = float(_pick(d, old, "bags") or 0)
    kg = float(old["bag_kg"] or 50)
    tons = _og_powder_t(bags, kg)
    if "rock_used_t" in d and d["rock_used_t"] not in (None, ""):
        used = float(d["rock_used_t"])
    elif old["rock_used_t"] is not None:
        used = float(old["rock_used_t"])
    else:
        used = _og_suggest_used(con, tons)
    if used < tons - 0.0011:
        raise ValueError("rock used powder se kam nahi ho sakta — wastage hamesha plus hoti hai")
    if used > _og_remaining_at(con, pid, date, exclude_id=old["id"]) + 0.0011:
        raise ValueError("is factory ke paas bill se pehle itna rock baqi nahi hai")
    rate = float(_pick(d, old, "rate_per_ton") or 0)
    charge = round(tons * rate, 2)
    _upd_row(con, "outside_grinding", old["id"], {
        "date": date, "party_id": pid, "tons": tons,
        "rate_per_ton": rate, "amount": charge, "bags": bags, "bag_kg": kg,
        "rock_used_t": used, "wastage_t": round(used - tons, 3),
        "vehicle_no": _pick(d, old, "vehicle_no") or "",
        "note": _pick(d, old, "note") or ""})
    if "paid_now" in d:
        paid_now = d.get("paid_now")
    else:
        _cur = _og_bill_payment(con, old["id"])
        paid_now = _cur["amount"] if _cur else 0
    _og_sync_bill_payment(con, old["id"], date, pid, paid_now,
                          d.get("pay_method") or d.get("method"), u)
    audit(con, u["username"], "update", "outside grinding bill #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"], "kind": "bill", "amount": charge,
            "rock_used_t": used, "wastage_t": round(used - tons, 3)}


def _deal_legs(con, deal_id):
    pr = con.execute("SELECT * FROM purchases WHERE deal_id=?", (deal_id,)).fetchone()
    sr = con.execute("SELECT * FROM sales WHERE deal_id=?", (deal_id,)).fetchone()
    if not pr or not sr:
        raise LookupError("direct deal nahi mila")
    return pr, sr


def update_direct_deal(con, d, u):
    """Edit a direct-trade deal as ONE unit: both legs are re-posted
    from the merged payload exactly once (rows are updated in place,
    never duplicated)."""
    deal_id = d.get("deal_id") or d.get("id")
    pr, sr = _deal_legs(con, deal_id)
    item = _trade_item(d, pr["item"] or "rock")
    base = {"date": _pick(d, pr, "date"), "item": item,
            "item_name": _pick(d, pr, "item_name"), "unit": _pick(d, pr, "unit"),
            "tons": _pick(d, pr, "tons"), "bags": _pick(d, pr, "bags"),
            "grade_pct": _pick(d, pr, "grade_pct"), "qty": _pick(d, pr, "qty"),
            "note": _pick(d, pr, "note")}
    upd_p = dict(base, id=pr["id"],
                 party_id=int(d.get("buy_party_id") or pr["party_id"]),
                 rate_per_ton=d.get("buy_rate", pr["rate_per_ton"]),
                 unit_rate=d.get("buy_unit_rate", pr["unit_rate"]),
                 deduction_pct=d.get("deduction_pct", pr["deduction_pct"]))
    upd_s = dict(base, id=sr["id"],
                 party_id=int(d.get("sell_party_id") or sr["party_id"]),
                 rate_per_ton=d.get("sell_rate", sr["rate_per_ton"]),
                 unit_rate=d.get("sell_unit_rate", sr["unit_rate"]))
    rp = update_purchase(con, upd_p, u)
    rs = update_sale(con, upd_s, u)
    audit(con, u["username"], "update", "direct deal %s" % deal_id)
    con.commit()
    return {"ok": True, "deal_id": deal_id, "purchase_amount": rp["amount"],
            "sale_amount": rs["amount"],
            "profit": round(rs["amount"] - rp["amount"], 2)}

def update_order(con, d, u):
    old = _row_or_404(con, "orders", d["id"])
    _upd_row(con, "orders", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "party_id": int(_pick(d, old, "party_id")),
        "tons": float(_pick(d, old, "tons") or 0),
        "bags": int(_pick(d, old, "bags") or 0),
        "rate_per_ton": float(_pick(d, old, "rate_per_ton") or 0),
        "expected_date": _pick(d, old, "expected_date") or "",
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "order #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_payment(con, d, u):
    old = _row_or_404(con, "payments", d["id"])
    pid = int(_pick(d, old, "party_id"))
    amount = float(_pick(d, old, "amount") or 0)
    method = _pick(d, old, "method") or "cash"
    _upd_row(con, "payments", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "party_id": pid,
        "direction": _pick(d, old, "direction") or old["direction"],
        "amount": amount, "method": method,
        "bank_name": _pick(d, old, "bank_name") or "",
        "online_channel": _pick(d, old, "online_channel") or "",
        "ref_no": str(_pick(d, old, "ref_no") or "").strip(),
        "note": _pick(d, old, "note") or ""})
    # keep the cheque register in step with the payment's method: a
    # payment corrected to cheque gains its pending cheque row, one
    # corrected away from cheque loses it
    chq = con.execute("SELECT * FROM cheques WHERE payment_id=?",
                      (old["id"],)).fetchone()
    if method == "cheque":
        cno = d.get("cheque_no", chq["cheque_no"] if chq else "")
        due = d.get("due_date", chq["due_date"] if chq else "")
        bank = _pick(d, old, "bank_name") or ""
        if chq:
            con.execute("UPDATE cheques SET party_id=?,cheque_no=?,bank=?,due_date=?,amount=?"
                        " WHERE id=?", (pid, cno, bank, due, amount, chq["id"]))
        else:
            con.execute("INSERT INTO cheques(payment_id,party_id,cheque_no,bank,due_date,amount,status)"
                        " VALUES(?,?,?,?,?,?,'pending')",
                        (old["id"], pid, cno, bank, due, amount))
    elif chq:
        con.execute("DELETE FROM cheques WHERE id=?", (chq["id"],))
    audit(con, u["username"], "update", "payment #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_expense(con, d, u):
    old = _row_or_404(con, "expenses", d["id"])
    sets = {
        "date": _pick(d, old, "date") or old["date"],
        "head_id": _pick(d, old, "head_id") or None,
        "sub_head_id": _pick(d, old, "sub_head_id") or None,
        "amount": float(_pick(d, old, "amount") or 0),
        "paid_to": _pick(d, old, "paid_to") or "",
        "note": _pick(d, old, "note") or "",
        "pay_channel": str(_pick(d, old, "pay_channel") or "").strip(),
        "pay_ref": str(_pick(d, old, "pay_ref") or "").strip(),
    }
    if "category" in d:
        sets["category"] = d.get("category") or ""
    if "method" in d:
        mm = str(d.get("method") or "cash").strip().lower()
        if mm == "cheque":
            mm = "bank"
        sets["method"] = mm if mm in ("cash", "bank", "online") else "cash"
    if any(k in d for k in ("paid_kind", "paid_by_holder", "paid_name", "paid_by")):
        # re-derive the paid-by attribution exactly as create_expense
        paid_kind = (d.get("paid_kind") or "").strip().lower()
        holder = (d.get("paid_by_holder") or "").strip()
        paid_name = (d.get("paid_name") or "").strip()
        legacy_by = (d.get("paid_by") or "").strip()
        if paid_kind not in ("owner", "manager", "other"):
            if holder.startswith("user:"):
                paid_kind = "manager"
            elif legacy_by.lower() in ("owner", "malik", "self", "owner (self)"):
                paid_kind = "owner"
            elif legacy_by:
                paid_kind, paid_name = "other", paid_name or legacy_by
            else:
                paid_kind = "other"
        if paid_kind == "owner":
            holder, paid_by = "", "Owner"
        elif paid_kind == "manager":
            uid = None
            if holder.startswith("user:"):
                try:
                    uid = int(holder.split(":", 1)[1])
                except ValueError:
                    uid = None
            w = con.execute("SELECT username FROM users WHERE id=?",
                            (uid,)).fetchone() if uid else None
            if not w:
                raise ValueError("Paid By wala user (manager/staff) nahi mila")
            holder, paid_by = "user:%d" % uid, w["username"]
        else:
            nm = paid_name or legacy_by
            holder = ("name:" + nm) if nm else ""
            paid_by = nm
        sets.update({"paid_kind": paid_kind, "paid_by_holder": holder,
                     "paid_by": paid_by})
    # status is NOT touched: an edit never re-opens or re-approves
    _upd_row(con, "expenses", old["id"], sets)
    audit(con, u["username"], "update", "expense #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"], "status": old["status"]}

def update_worker(con, d, u):
    old = _row_or_404(con, "workers", d["id"])
    _upd_row(con, "workers", old["id"], {
        "name": (d["name"].strip() if d.get("name") else old["name"]),
        "kind": _pick(d, old, "kind") or "theka",
        "rate_per_ton": float(_pick(d, old, "rate_per_ton") or 0),
        "rate_per_bag": float(_pick(d, old, "rate_per_bag") or 0),
        "monthly_salary": float(_pick(d, old, "monthly_salary") or 0),
        "phone": _pick(d, old, "phone") or "",
        "department_id": _pick(d, old, "department_id") or None,
        "device_code": _pick(d, old, "device_code") or "",
        "start_date": _pick(d, old, "start_date") or old["start_date"]})
    audit(con, u["username"], "update", "worker #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_payout(con, d, u):
    old = _row_or_404(con, "worker_payouts", d["id"])
    _upd_row(con, "worker_payouts", old["id"], {
        "worker_id": int(_pick(d, old, "worker_id")),
        "date": _pick(d, old, "date") or old["date"],
        "amount": float(_pick(d, old, "amount") or 0),
        "kind": _pick(d, old, "kind") or "payment",
        "method": _pick(d, old, "method") or "cash",
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "payout #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_bag_move(con, d, u):
    old = _row_or_404(con, "bag_movements", d["id"])
    _upd_row(con, "bag_movements", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "direction": _pick(d, old, "direction") or old["direction"],
        "bags": int(_pick(d, old, "bags") or 0),
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "bag movement #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_client_bag(con, d, u):
    old = _row_or_404(con, "client_bags", d["id"])
    _upd_row(con, "client_bags", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "party_id": int(_pick(d, old, "party_id")),
        "direction": _pick(d, old, "direction") or old["direction"],
        "bags": int(_pick(d, old, "bags") or 0),
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "client bags #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_head(con, d, u):
    old = _row_or_404(con, "expense_heads", d["id"])
    _upd_row(con, "expense_heads", old["id"], {
        "name": (d["name"].strip() if d.get("name") else old["name"]),
        "parent_id": _pick(d, old, "parent_id") or None})
    audit(con, u["username"], "update", "expense head #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_machine(con, d, u):
    old = _row_or_404(con, "machines", d["id"])
    _upd_row(con, "machines", old["id"], {
        "name": (d["name"].strip() if d.get("name") else old["name"]),
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "machine #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_maintenance(con, d, u):
    old = _row_or_404(con, "maintenance", d["id"])
    _upd_row(con, "maintenance", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "machine": _pick(d, old, "machine") or "",
        "detail": _pick(d, old, "detail") or "",
        "cost": float(_pick(d, old, "cost") or 0),
        "downtime_hours": float(_pick(d, old, "downtime_hours") or 0)})
    audit(con, u["username"], "update", "maintenance #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_stock_count(con, d, u):
    old = _row_or_404(con, "stock_counts", d["id"])
    _upd_row(con, "stock_counts", old["id"], {
        "date": _pick(d, old, "date") or old["date"],
        "item": _pick(d, old, "item") or "",
        "counted_qty": float(_pick(d, old, "counted_qty") or 0),
        "book_qty": float(_pick(d, old, "book_qty") or 0),
        "note": _pick(d, old, "note") or ""})
    audit(con, u["username"], "update", "stock count #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"]}

def update_machine_entry(con, d, u):
    """Owner edit of a maintenance-diary entry. The linked Expense
    Ledger row is kept in step exactly like create: cost > 0 keeps one
    Machine-head expense (updated in place, created if missing, paid_to
    follows the machine), cost 0 removes it — never a second expense."""
    old = _row_or_404(con, "machine_entries", d["id"])
    mid = int(_pick(d, old, "machine_id"))
    m = con.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
    if not m:
        raise ValueError("machine nahi mila")
    date = _pick(d, old, "date") or old["date"]
    work_type = _pick(d, old, "work_type") or "Service"
    detail = _pick(d, old, "detail") or ""
    cost = float(_pick(d, old, "cost") or 0)
    next_due = _pick(d, old, "next_due") or ""
    exp_id = old["expense_id"]
    if cost > 0:
        note = "Machine maintenance: %s — %s" % (work_type, detail)
        if exp_id:
            _upd_row(con, "expenses", exp_id, {
                "date": date, "amount": cost, "paid_to": m["name"],
                "note": note})
        else:
            r = create_expense(con, {
                "date": date, "head_id": machine_head_id(con),
                "amount": cost, "paid_kind": "owner", "method": "cash",
                "paid_to": m["name"], "note": note}, u)
            exp_id = r["id"]
    elif exp_id:
        con.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
        exp_id = None
    _upd_row(con, "machine_entries", old["id"], {
        "date": date, "machine_id": mid, "work_type": work_type,
        "detail": detail, "cost": cost, "next_due": next_due,
        "expense_id": exp_id})
    audit(con, u["username"], "update", "machine_entry #%d" % old["id"])
    con.commit()
    return {"ok": True, "id": old["id"], "expense_id": exp_id}


_EDIT_ROUTES = {"/api/parties": update_party, "/api/trips": update_trip,
                "/api/jobs": update_job, "/api/production": update_production,
                "/api/purchases": update_purchase, "/api/sales": update_sale,
                "/api/outside-grinding": update_outside,
                "/api/direct-deals": update_direct_deal,
                "/api/payments": update_payment,
                "/api/expenses": update_expense, "/api/workers": update_worker,
                "/api/payouts": update_payout,
                "/api/bag-moves": update_bag_move,
                "/api/client-bags": update_client_bag,
                "/api/heads": update_head, "/api/machines": update_machine,
                "/api/machine-entries": update_machine_entry,
                "/api/maintenance": update_maintenance,
                "/api/stock-counts": update_stock_count}

_MIGRATED = [False]

def ensure_migrated():
    """init_db() historically only ran at first setup; run it once per
    process so column migrations also land on older databases."""
    if _MIGRATED[0]:
        return
    _MIGRATED[0] = True
    try:
        if db_path() and os.path.exists(db_path()):
            init_db()
    except Exception:
        pass

# ------------------------------------------------------------------ meta ----
def meta_get(con, key, default=""):
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default

def meta_set(con, key, value):
    con.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value))

def audit(con, username, action, detail=""):
    con.execute("INSERT INTO audit_log(created,username,action,detail) VALUES(?,?,?,?)",
                (now_str(), username or "", action, detail))

def notify_owner(con, ntype, message):
    con.execute("INSERT INTO notifications(created,type,message) VALUES(?,?,?)",
                (now_str(), ntype, message))

# ------------------------------------------------------------------ auth ----
SESSIONS = {}  # token -> user dict

def _drop_sessions(user_id):
    """Forget live sessions of one user (after role/perms/password change)."""
    for tok in [t for t, s in SESSIONS.items() if s.get("id") == user_id]:
        SESSIONS.pop(tok, None)

def _refresh_session_user(con, user_id):
    """Round 12: after a self-service profile/avatar change, refresh the
    cached display fields of every live session of that user so the
    header chip updates everywhere without a re-login."""
    r = con.execute("SELECT display_name, avatar_b64, avatar_ver FROM users WHERE id=?",
                    (user_id,)).fetchone()
    if not r:
        return
    for s in SESSIONS.values():
        if s.get("id") == user_id:
            s["display_name"] = r["display_name"] or ""
            s["has_avatar"] = bool(r["avatar_b64"])
            s["avatar_ver"] = r["avatar_ver"] or 0

def _rget(r, key, default=None):
    try:
        v = r[key]
    except Exception:
        return default
    return default if v is None else v

def htmlesc(s):
    return (str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def hash_pw(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                            bytes.fromhex(salt), 200_000).hex()
    return salt, h

def check_pw(password, salt, expected):
    _, h = hash_pw(password, salt)
    return secrets.compare_digest(h, expected)

def today():
    return time.strftime("%Y-%m-%d")

def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def now_ts():
    return time.time()

# ------------------------------------------------------------- QR code ------
# Minimal pure-python QR encoder (byte mode, EC level M, versions 1-10)
# producing an SVG string. Reed-Solomon + format/version bits follow the
# classic Nayuki formulation. No external libraries.
_QR_EC_TABLE = {  # version: (ec_codewords_per_block, [(num_blocks, data_cw_per_block), ...])
    1: (10, [(1, 16)]), 2: (16, [(1, 28)]), 3: (26, [(1, 44)]),
    4: (18, [(2, 32)]), 5: (24, [(2, 43)]), 6: (16, [(4, 27)]),
    7: (18, [(4, 31)]), 8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]), 10: (26, [(4, 43), (1, 44)]),
}
_QR_ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
             7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
_QR_REM = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7, 7: 0, 8: 0, 9: 0, 10: 0}

def _gf_mul(x, y):
    z = 0
    for i in range(7, -1, -1):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        if ((y >> i) & 1) != 0:
            z ^= x
    return z

def _rs_divisor(degree):
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(len(result)):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < len(result):
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 0x02)
    return result

def _rs_remainder(data, divisor):
    result = [0] * len(divisor)
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor):
            result[i] ^= _gf_mul(coef, factor)
    return result

def qr_svg(text, scale=4, border=2):
    data = text.encode("utf-8")
    version = None
    for v in range(1, 11):
        _ec, groups = _QR_EC_TABLE[v]
        cap = sum(n * d for n, d in groups)
        if 4 + (8 if v < 10 else 16) + 8 * len(data) <= cap * 8:
            version = v
            break
    if version is None:
        data = data[:213]
        version = 10
    ec_len, groups = _QR_EC_TABLE[version]
    total_data = sum(n * d for n, d in groups)
    bits = []
    def put(val, n):
        for i in range(n - 1, -1, -1):
            bits.append((val >> i) & 1)
    put(0b0100, 4)
    put(len(data), 8 if version < 10 else 16)
    for b in data:
        put(b, 8)
    cap_bits = total_data * 8
    bits += [0] * min(4, cap_bits - len(bits))
    while len(bits) % 8:
        bits.append(0)
    i = 0
    while len(bits) < cap_bits:
        put((0xEC, 0x11)[i % 2], 8)
        i += 1
    data_cw = []
    for i in range(0, len(bits), 8):
        b = 0
        for bit in bits[i:i + 8]:
            b = (b << 1) | bit
        data_cw.append(b)
    divisor = _rs_divisor(ec_len)
    blocks = []
    pos = 0
    for nblocks, dcw in groups:
        for _ in range(nblocks):
            blk = data_cw[pos:pos + dcw]
            pos += dcw
            blocks.append((blk, _rs_remainder(blk, divisor)))
    final = []
    for i in range(max(len(b[0]) for b in blocks)):
        for blk, _e in blocks:
            if i < len(blk):
                final.append(blk[i])
    for i in range(ec_len):
        for _blk, ecc in blocks:
            final.append(ecc[i])
    # ---- matrix ----
    size = version * 4 + 17
    m = [[None] * size for _ in range(size)]
    def finder(cx, cy):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < size and 0 <= y < size:
                    d = max(abs(dx), abs(dy))
                    m[y][x] = 1 if (d == 3 or d <= 1) else 0
    finder(3, 3); finder(size - 4, 3); finder(3, size - 4)
    for i in range(size):
        if m[6][i] is None:
            m[6][i] = 1 if i % 2 == 0 else 0
        if m[i][6] is None:
            m[i][6] = 1 if i % 2 == 0 else 0
    coords = _QR_ALIGN[version]
    for ai, ax in enumerate(coords):
        for aj, ay in enumerate(coords):
            if (ai == 0 and aj == 0) or (ai == 0 and aj == len(coords) - 1) or \
               (ai == len(coords) - 1 and aj == 0):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    d = max(abs(dx), abs(dy))
                    m[ay + dy][ax + dx] = 1 if (d == 2 or d == 0) else 0
    # reserve format-info cells (value 2 = reserved)
    for i in range(9):
        if m[8][i] is None: m[8][i] = 2
        if m[i][8] is None: m[i][8] = 2
    for i in range(8):
        if m[8][size - 1 - i] is None: m[8][size - 1 - i] = 2
        if m[size - 1 - i][8] is None: m[size - 1 - i][8] = 2
    m[size - 8][8] = 1  # dark module
    if version >= 7:
        for i in range(6):
            for j in range(3):
                m[i][size - 11 + j] = 2
                m[size - 11 + j][i] = 2
    # place data (mask 0)
    fb = []
    for cw in final:
        for i in range(7, -1, -1):
            fb.append((cw >> i) & 1)
    fb += [0] * _QR_REM[version]
    idx = 0
    right = size - 1
    while right >= 1:
        if right == 6:
            right = 5
        for vert in range(size):
            # direction alternates per column pair; pairs counted from right
            y = (size - 1 - vert) if (((size - 1 - right) // 2) % 2 == 0) else vert
            for dx in (0, -1):
                x = right + dx
                if m[y][x] is None:
                    bit = fb[idx] if idx < len(fb) else 0
                    idx += 1
                    if (x + y) % 2 == 0:
                        bit ^= 1
                    m[y][x] = bit
        right -= 2
    # format bits (EC level M formatBits = 0, mask 0)
    fdata = (0 << 3) | 0
    rem = fdata
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    fmt = ((fdata << 10) | rem) ^ 0x5412
    def gbit(v, i):
        return (v >> i) & 1
    for i in range(6):
        m[i][8] = gbit(fmt, i)
    m[7][8] = gbit(fmt, 6)
    m[8][8] = gbit(fmt, 7)
    m[8][7] = gbit(fmt, 8)
    for i in range(9, 15):
        m[8][14 - i] = gbit(fmt, i)
    for i in range(8):
        m[8][size - 1 - i] = gbit(fmt, i)
    for i in range(8, 15):
        m[size - 15 + i][8] = gbit(fmt, i)
    m[size - 8][8] = 1
    if version >= 7:
        rem = version
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        vbits = (version << 12) | rem
        for i in range(18):
            bit = gbit(vbits, i)
            m[i // 3][size - 11 + i % 3] = bit
            m[size - 11 + i % 3][i // 3] = bit
    total = size + border * 2
    rects = []
    for y in range(size):
        for x in range(size):
            if m[y][x] == 1:
                rects.append("M%d %dh1v1h-1z" % (x + border, y + border))
    return ("<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
            "viewBox='0 0 %d %d'><rect width='%d' height='%d' fill='#fff'/>"
            "<path d='%s' fill='#000'/></svg>"
            % (total * scale, total * scale, total, total, total, total, "".join(rects)))

# -------------------------------------------------------------- business ----
def party_ledger(con, party_id):
    """Return (entries, balance). Balance > 0 means the party owes us.
    Payments made by a cheque that later BOUNCED are excluded (the
    balance reopens automatically when a cheque is marked bounced)."""
    p = con.execute("SELECT * FROM parties WHERE id=?", (party_id,)).fetchone()
    if p is None:
        return [], 0
    entries = []
    bal = float(p["opening_balance"] or 0)
    if bal != 0:
        entries.append({"date": "", "type": "Opening", "desc": "Opening balance",
                        "debit": bal if bal > 0 else 0,
                        "credit": -bal if bal < 0 else 0, "balance": bal})
    ev = []
    for r in con.execute("SELECT * FROM grinding_jobs WHERE party_id=?", (party_id,)):
        if float(r["tons"] or 0) > 0:
            _gdesc = "Grinding %g t @ Rs %g (grade %g%%)" % (r["tons"], r["rate_per_ton"], r["grade_pct"])
        else:
            # new merged entries store no ground-rock weight (the
            # register never weighs it) — describe by powder produced
            _gdesc = "Grinding — %d powder bags (grade %g%%)" % (r["bags"], r["grade_pct"])
        ev.append((r["date"], r["id"], "Grinding", _gdesc,
                   float(r["amount"]), 0))
    for r in con.execute("SELECT s.*, t.vehicle_no AS _veh, f.name AS _fname FROM sales s "
                         "LEFT JOIN trips t ON t.id=s.trip_id "
                         "LEFT JOIN parties f ON f.id=s.og_factory_id WHERE s.party_id=?", (party_id,)):
        _it = r["item"] or "powder"
        if _it == "other":
            desc = "%s sale %g %s @ Rs %g" % (r["item_name"] or "Item", r["qty"],
                                              r["unit"] or "", r["unit_rate"])
        elif _it == "rock":
            desc = "Rock sale %g t @ Rs %g" % (r["tons"], r["rate_per_ton"])
        else:
            desc = "Powder sale %g t @ Rs %g" % (r["tons"], r["rate_per_ton"])
        if r["trip_id"]:
            desc += " (vehicle %s, gate)" % (r["_veh"] or "")
        if (r["source"] or "") == "direct":
            desc += " — direct trade"
        if (r["source"] or "") == "outside":
            desc += " — sold from %s (outside mill)" % (r["_fname"] or "outside mill")
        if r["invoice_no"]:
            desc += " [%s]" % r["invoice_no"]
        ev.append((r["date"], r["id"], "Sale", desc, float(r["amount"]), 0))
    for r in con.execute("SELECT * FROM purchases WHERE party_id=?", (party_id,)):
        _it = r["item"] or "rock"
        if _it == "other":
            desc = "%s bought %g %s @ Rs %g" % (r["item_name"] or "Item", r["qty"],
                                                r["unit"] or "", r["unit_rate"])
        elif _it == "powder":
            desc = "Powder bought %g t (%d bags) @ Rs %g" % (r["tons"], r["bags"],
                                                             r["rate_per_ton"])
        else:
            desc = ("Rock bought %g t, billed %g t after %g%% deduction @ Rs %g"
                    % (r["tons"], r["billed_tons"], r["deduction_pct"], r["rate_per_ton"]))
        if (r["source"] or "") == "direct":
            desc += " — direct trade"
        ev.append((r["date"], r["id"], "Purchase", desc, 0, float(r["amount"])))
    bounced_payments = {r["payment_id"] for r in con.execute(
        "SELECT payment_id FROM cheques WHERE status='bounced' AND payment_id IS NOT NULL")}
    for r in con.execute("SELECT * FROM payments WHERE party_id=?", (party_id,)):
        if r["id"] in bounced_payments:
            continue
        m = (" [%s]" % r["method"]) if r["method"] else ""
        if r["direction"] == "in":
            ev.append((r["date"], r["id"], "Payment", "Payment received%s %s" % (m, r["note"] or ""), 0, float(r["amount"])))
        else:
            ev.append((r["date"], r["id"], "Payment", "Payment paid%s %s" % (m, r["note"] or ""), float(r["amount"]), 0))
    def _trip_purchase_ev(r):
        # rock bought at vehicle IN: purchase payable + (mine rate)
        # rent, as khata events. These credits belong to the SELLER —
        # buy_from_party_id when set, else the trip party.
        out = []
        if r["direction"] == "IN" and float(r["rock_rate"] or 0) > 0:
            _pra = round(r["net_kg"] / 1000.0 * float(r["rock_rate"]), 2)
            _rlab = "mine rate" if r["rate_type"] == "mine" else "factory ponch rate"
            out.append((r["date"], r["id"], "Purchase",
                        "Rock purchase at vehicle IN (%s) %g t @ Rs %g (%s)"
                        % (r["vehicle_no"], r["net_kg"] / 1000.0, float(r["rock_rate"]), _rlab),
                        0, _pra))
            # rent credits the seller ONLY when it is payable to the
            # seller; rent_to='driver' is paid in cash by the mill and
            # posts NO khata line (it lands in the mill's own totals)
            if r["rate_type"] == "mine" and float(r["rent"] or 0) > 0 \
                    and (r["rent_to"] or "seller") == "seller":
                out.append((r["date"], r["id"], "Rent",
                            "Vehicle rent (vehicle IN %s, mine rate)" % r["vehicle_no"],
                            0, float(r["rent"])))
        return out
    for r in con.execute("SELECT * FROM trips WHERE party_id=?", (party_id,)):
        if r["direction"] == "OUT" and r["freight_payer"] == "party" and float(r["freight"] or 0) > 0:
            ev.append((r["date"], r["id"], "Freight",
                       "Freight charged (vehicle %s)" % r["vehicle_no"], float(r["freight"]), 0))
        ch = float(r["loading"] or 0) + float(r["unloading"] or 0)
        if ch > 0 and r["charge_bearer"] == "party":
            ev.append((r["date"], r["id"], "Loading",
                       "Loading/unloading (%s, vehicle %s)" % (r["direction"], r["vehicle_no"]), ch, 0))
        # grinding charged at vehicle OUT (optional rate on the OUT form;
        # the same "Grinding" head the grinding records post under)
        if r["direction"] == "OUT" and float(r["grind_charge"] or 0) > 0:
            ev.append((r["date"], r["id"], "Grinding",
                       "Grinding charge at vehicle OUT (%s) %g t @ Rs %g"
                       % (r["vehicle_no"], r["net_kg"] / 1000.0, float(r["grind_rate"] or 0)),
                       float(r["grind_charge"]), 0))
        # purchase + rent post to the SELLER's khata: from this loop
        # only when the seller IS the party being viewed (buy_from
        # empty means the trip party itself sold the rock)
        if not r["buy_from_party_id"] or int(r["buy_from_party_id"]) == party_id:
            ev.extend(_trip_purchase_ev(r))
    # trips whose STOCK belongs to another party (or to Own) but whose
    # rock was bought from THIS party: only the purchase / rent credits
    # land here — never their freight / loading / grinding lines.
    for r in con.execute("SELECT * FROM trips WHERE buy_from_party_id=? "
                         "AND (party_id IS NULL OR party_id<>?)",
                         (party_id, party_id)):
        ev.extend(_trip_purchase_ev(r))
    # Own-dispatch sales recorded ON a Vehicle Out trip (owner, 28 Oct
    # 2026): Party = Own (Mine) + "Powder sold to" + sale rate on the
    # trip row itself. The receivable is DERIVED from the trip row —
    # no sales row exists — so it appears in this khata (and the
    # printed statement built on it) exactly once, follows trip
    # edits, and vanishes with a trip delete.
    for r in con.execute("SELECT * FROM trips WHERE direction='OUT' "
                         "AND sale_buyer_id=? AND sale_rate>0", (party_id,)):
        _amt = _trip_sale_amount(r)
        if _amt > 0:
            ev.append((r["date"], r["id"], "Sale",
                       "Powder sale %g t @ Rs %g (vehicle %s, gate)"
                       % (r["net_kg"] / 1000.0, float(r["sale_rate"]),
                          r["vehicle_no"]), _amt, 0))
    # outside grinding, seller side: rock THIS party sold us at the
    # mine for an outside factory — a Purchase payable CREDIT,
    # synthesised exactly like the vehicle-IN purchase lines.
    _og_names = {p2["id"]: p2["name"] for p2 in con.execute("SELECT id, name FROM parties")}
    for r in con.execute("SELECT * FROM outside_grinding WHERE from_party_id=? "
                         "AND kind='sent' AND rock_amount>0", (party_id,)):
        ev.append((r["date"], r["id"], "Purchase",
                   "Rock bought for outside grinding (%s) %g t @ Rs %g"
                   % (_og_names.get(r["party_id"], "outside mill"), r["tons"], r["rock_rate"]),
                   0, float(r["rock_amount"])))
    # outside grinding, factory side: a Grinding Bill's charge is OUR
    # PAYABLE to the factory — a CREDIT under the same "Grinding" head
    # (the factory's earnings from us, never a receivable from them;
    # toll customers' grinding debits above stay exactly as they were).
    for r in con.execute("SELECT * FROM outside_grinding WHERE party_id=? AND kind='bill'",
                         (party_id,)):
        ev.append((r["date"], r["id"], "Grinding",
                   "Outside grinding bill — charges (hamaray denay) — %g t powder @ Rs %g"
                   % (r["tons"], r["rate_per_ton"]),
                   0, float(r["amount"])))
    ev.sort(key=lambda x: (x[0], x[1]))
    for d, _i, t, desc, dr, cr in ev:
        if dr == 0 and cr == 0:
            # KHATA = MONEY ONLY (owner, 29 Oct 2026): a merged
            # Grinding & Production record posts no charge from the
            # job row itself (the grinding charge lands at vehicle
            # OUT), so its khata line was a zero-amount information
            # row — "Grinding — 500 powder bags (grade 31%)" — that
            # only cluttered the statement. Skipping zero rows here,
            # at the single assembly point, cleans every surface at
            # once (screen ledger, printed statement, client-portal
            # my-khata, WhatsApp statement). Balances are untouched:
            # a zero row never moved them. Production detail stays in
            # Grinding & Production / Warehouse, and the stock line on
            # the khata comes from party_stock, not from these rows.
            continue
        bal += dr - cr
        entries.append({"date": d, "type": t, "desc": desc,
                        "debit": dr, "credit": cr, "balance": bal})
    return entries, bal

def jobs_ground_t(con, where="", params=()):
    """Rock consumed by grinding jobs (tons), per record. A job WITH
    stored tons (legacy entries, Excel imports) counts those tons. A
    job WITHOUT stored tons (tons 0/NULL — the merged Grinding &
    Production form no longer weighs ground rock: the mill's paper
    register never did) derives its consumption the register way:
    powder tons + wastage, where powder tons = the job's powder bags
    x each linked production row's stamped per-bag weight (legacy
    NULL = 50 kg) and wastage is the mill's wastage_pct of the powder."""
    pct = wastage_pct(con)
    tot = 0.0
    for r in con.execute("SELECT id, tons, bags FROM grinding_jobs " + where, params):
        t = float(r["tons"] or 0)
        if t > 0:
            tot += t
        else:
            tot += _job_powder_kg(con, r) / 1000.0 * (1.0 + pct / 100.0)
    return tot

def _jobs_powder_t(con, where="", params=()):
    """Powder tons made by grinding jobs (per-record bag weights via
    _job_powder_kg — the same source jobs_ground_t derives from)."""
    tot = 0.0
    for r in con.execute("SELECT id, bags FROM grinding_jobs " + where, params):
        tot += _job_powder_kg(con, r)
    return tot / 1000.0

def party_stock(con, party_id):
    """Rock waiting / powder ready + grinding loss % for one party.
    FILTER POWDER IS NEVER THE PARTY'S (Talha's rule, 28 Oct 2026):
    the filter bags from this party's jobs are the mill's own stock
    (see own_filter_stock) and count on the party's WASTAGE side —
    the party's recovery here is powder only, so "filter_ready_t"
    is 0 by rule, not by measurement."""
    rock_in = con.execute("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE party_id=? AND direction='IN'",
                          (party_id,)).fetchone()["s"] / 1000.0
    bought = con.execute("SELECT COALESCE(SUM(tons),0) s FROM purchases WHERE party_id=? "
                         "AND COALESCE(item,'rock')='rock' AND COALESCE(source,'ledger')<>'direct'",
                         (party_id,)).fetchone()["s"]
    ground = jobs_ground_t(con, "WHERE party_id=?", (party_id,))
    powder_made = _jobs_powder_t(con, "WHERE party_id=?", (party_id,))
    powder_out = con.execute("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE party_id=? AND direction='OUT' "
                             "AND COALESCE(fx,'')<>'none'",
                             (party_id,)).fetchone()["s"] / 1000.0
    sold = con.execute("SELECT COALESCE(SUM(tons),0) s FROM sales WHERE party_id=? "
                       "AND COALESCE(item,'powder')='powder' AND trip_id IS NULL "
                       "AND COALESCE(source,'ledger')<>'direct'",
                       (party_id,)).fetchone()["s"]
    bags_made = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production WHERE party_id=?",
                             (party_id,)).fetchone()["s"]
    bags_out = con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips WHERE party_id=? AND direction='OUT' "
                           "AND COALESCE(fx,'')<>'none'",
                           (party_id,)).fetchone()["s"]
    bags_adj = bag_adj_sum(con, party_id)
    loss = ((ground - powder_made) / ground * 100.0) if ground > 0 else 0.0
    return {
        "rock_in_t": round(rock_in + bought, 3),
        "ground_t": round(ground, 3),
        "rock_waiting_t": round(rock_in + bought - ground, 3),
        "powder_made_t": round(powder_made, 3),
        "powder_out_t": round(powder_out + sold, 3),
        "powder_ready_t": round(powder_made - powder_out - sold, 3),
        "filter_ready_t": 0.0,   # by rule: filter output is the mill's
                                 # own stock (own_filter_stock), never
                                 # the job party's — see party_stock docs
        "grinding_loss_pct": round(loss, 2),
        "bags_made": bags_made, "bags_out": bags_out, "bags_adj": bags_adj,
        "bags_ready": bags_made - bags_out + bags_adj,
    }

def own_stock(con):
    """Own stock position. Every sum is gated on item kind + source so
    each physical movement counts exactly once: rock purchases feed
    rock only, powder purchases feed powder only, 'other' trades feed
    neither, direct-trade rows feed NEITHER leg (goods never entered).
    Powder leaves own stock through SALE rows (ledger sales — and
    legacy round-9 gate sales, whose trip_id rows still count here,
    their trips never fed this view) and, since the dispatch-only
    Vehicle Out (28 Oct 2026), through fx='own' dispatch trips.
    Legacy rows (item/source defaults) reduce to the old totals
    exactly. Rock enters own stock through ledger rock purchases AND
    Own Vehicle In trips (party-less IN rows) — two disjoint sources,
    counted once each. The FILTER figures are the mill's own filter
    pool (own_filter_stock): filter output from EVERY job — own and
    toll alike — is the mill's property (Talha's rule, 28 Oct 2026)."""
    rock_bought = con.execute(
        "SELECT COALESCE(SUM(tons),0) s FROM purchases WHERE COALESCE(item,'rock')='rock' "
        "AND COALESCE(source,'ledger')<>'direct'").fetchone()["s"]
    # Own Vehicle In rock (bug fix, 28 Oct 2026): rock that arrived on
    # an Own (party-less) Vehicle In trip is OURS, but it was never
    # counted — only ledger purchases fed rock_bought, so Own gate
    # arrivals silently missed own stock (party_stock has always
    # counted its own trips' rock_in term the same way). The stock
    # lands on Own whatever buy_from_party_id says: the purchase
    # CREDIT goes to the seller, the ROCK stays with the trip party —
    # here, Own. No double count is possible: saving a trip never
    # writes a purchases row (create_purchase holds the system's only
    # insert into the purchases table), so the two inflows are disjoint.
    rock_bought += con.execute(
        "SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='IN' "
        "AND party_id IS NULL").fetchone()["s"] / 1000.0
    powder_bought = con.execute(
        "SELECT COALESCE(SUM(tons),0) s FROM purchases WHERE item='powder' "
        "AND COALESCE(source,'ledger')<>'direct'").fetchone()["s"]
    ground = jobs_ground_t(con, "WHERE party_id IS NULL")
    powder_made = _jobs_powder_t(con, "WHERE party_id IS NULL")
    rock_sold = con.execute(
        "SELECT COALESCE(SUM(tons),0) s FROM sales WHERE item='rock' "
        "AND COALESCE(source,'ledger') NOT IN ('direct','outside')").fetchone()["s"]
    powder_sold = con.execute(
        "SELECT COALESCE(SUM(tons),0) s FROM sales WHERE COALESCE(item,'powder')='powder' "
        "AND COALESCE(source,'ledger') NOT IN ('direct','outside')").fetchone()["s"]
    own_disp_t = con.execute(
        "SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='OUT' "
        "AND party_id IS NULL AND fx='own'").fetchone()["s"] / 1000.0
    # outside grinding NEVER touches godam stock (the rock goes mine ->
    # factory, the powder is sold from there): the two outside figures
    # below are informational totals only and enter NO stock formula.
    out_sent = con.execute(
        "SELECT COALESCE(SUM(tons),0) s FROM outside_grinding WHERE kind='sent'").fetchone()["s"]
    out_prod = con.execute(
        "SELECT COALESCE(SUM(tons),0) s FROM outside_grinding "
        "WHERE kind IN ('bill','received')").fetchone()["s"]
    _flt = own_filter_stock(con)
    return {"rock_bought_t": round(rock_bought, 3),
            "filter_bags": _flt["filter_bags"],
            "filter_kg": _flt["filter_kg"],
            "filter_t": _flt["filter_t"],
            "powder_bought_t": round(powder_bought, 3),
            "ground_t": round(ground, 3),
            "rock_left_t": round(rock_bought - ground - rock_sold, 3),
            "powder_made_t": round(powder_made, 3),
            "rock_sold_t": round(rock_sold, 3),
            "sold_t": round(powder_sold, 3),
            "dispatched_t": round(own_disp_t, 3),
            "outside_sent_t": round(out_sent, 3),
            "outside_received_t": round(out_prod, 3),
            "powder_left_t": round(powder_made + powder_bought - powder_sold - own_disp_t, 3)}

def trade_history(con):
    """The Own page's combined trade history: every own-goods buy/sell
    however it entered — gate (Vehicle In purchase sections + legacy
    Vehicle Out sale rows), party-ledger entries, Excel imports —
    plus direct trades rendered as ONE deal line each. A buyer gate
    pass (dispatch-only trip) creates NO row here: it is a dispatch,
    not a sale. Rows carry everything the UI needs to route an owner
    edit to the right door."""
    names = {p["id"]: p["name"] for p in con.execute("SELECT id, name FROM parties")}
    rows = []
    for r in con.execute("SELECT * FROM purchases WHERE COALESCE(source,'ledger')<>'direct' "
                         "ORDER BY date DESC, id DESC"):
        rows.append({"kind": "buy", "id": r["id"], "date": r["date"],
                     "party_id": r["party_id"], "party": names.get(r["party_id"], "?"),
                     "item": r["item"] or "rock", "item_name": r["item_name"] or "",
                     "tons": r["tons"], "bags": r["bags"], "qty": r["qty"],
                     "unit": r["unit"] or "", "amount": float(r["amount"] or 0),
                     "source": r["source"] or "ledger", "trip_id": None,
                     "invoice_no": "", "note": r["note"] or ""})
    for r in con.execute("SELECT * FROM sales WHERE COALESCE(source,'ledger')<>'direct' "
                         "ORDER BY date DESC, id DESC"):
        rows.append({"kind": "sell", "id": r["id"], "date": r["date"],
                     "party_id": r["party_id"], "party": names.get(r["party_id"], "?"),
                     "item": r["item"] or "powder", "item_name": r["item_name"] or "",
                     "tons": r["tons"], "bags": r["bags"], "qty": r["qty"],
                     "unit": r["unit"] or "", "amount": float(r["amount"] or 0),
                     "source": "gate" if r["trip_id"] else (r["source"] or "ledger"),
                     "trip_id": r["trip_id"], "invoice_no": r["invoice_no"] or "",
                     "note": r["note"] or ""})
    for r in con.execute("SELECT * FROM trips WHERE direction='IN' AND rock_rate>0 "
                         "ORDER BY date DESC, id DESC"):
        seller = r["buy_from_party_id"] or r["party_id"]
        rows.append({"kind": "buy", "id": None, "date": r["date"],
                     "party_id": seller,
                     "party": names.get(seller, "Own / Apna") if seller else "Own / Apna",
                     "item": "rock", "item_name": "",
                     "tons": round(float(r["net_kg"] or 0) / 1000.0, 3), "bags": 0,
                     "qty": 0, "unit": "",
                     "amount": round(float(r["net_kg"] or 0) / 1000.0 * float(r["rock_rate"] or 0), 2),
                     "source": "gate", "trip_id": r["id"], "invoice_no": "",
                     "note": "Vehicle %s" % (r["vehicle_no"] or "")})
    # Own-dispatch sales stored on the OUT trip itself (owner, 28 Oct
    # 2026): no sales row exists, so the sell line is derived from the
    # trip row — tagged Gate and routed to the trip's own edit door,
    # exactly like the gate purchases above.
    for r in con.execute("SELECT * FROM trips WHERE direction='OUT' "
                         "AND sale_buyer_id IS NOT NULL AND sale_rate>0 "
                         "ORDER BY date DESC, id DESC"):
        rows.append({"kind": "sell", "id": None, "date": r["date"],
                     "party_id": r["sale_buyer_id"],
                     "party": names.get(r["sale_buyer_id"], "?"),
                     "item": "powder", "item_name": "",
                     "tons": round(float(r["net_kg"] or 0) / 1000.0, 3),
                     "bags": r["bags"], "qty": 0, "unit": "",
                     "amount": _trip_sale_amount(r),
                     "source": "gate", "trip_id": r["id"], "invoice_no": "",
                     "note": "Vehicle %s" % (r["vehicle_no"] or "")})
    deals = {}
    for r in con.execute("SELECT * FROM purchases WHERE source='direct' AND deal_id<>''"):
        deals.setdefault(r["deal_id"], {})["buy"] = r
    for r in con.execute("SELECT * FROM sales WHERE source='direct' AND deal_id<>''"):
        deals.setdefault(r["deal_id"], {})["sell"] = r
    for did, legs in deals.items():
        b, s = legs.get("buy"), legs.get("sell")
        if not b or not s:
            continue
        rows.append({"kind": "deal", "id": None, "deal_id": did,
                     "date": b["date"], "item": b["item"] or "rock",
                     "item_name": b["item_name"] or "",
                     "tons": b["tons"], "bags": b["bags"], "qty": b["qty"],
                     "unit": b["unit"] or "",
                     "buy_party_id": b["party_id"],
                     "buy_party": names.get(b["party_id"], "?"),
                     "sell_party_id": s["party_id"],
                     "sell_party": names.get(s["party_id"], "?"),
                     "purchase_id": b["id"], "sale_id": s["id"],
                     "buy_amount": float(b["amount"] or 0),
                     "sell_amount": float(s["amount"] or 0),
                     "amount": float(s["amount"] or 0),
                     "profit": round(float(s["amount"] or 0) - float(b["amount"] or 0), 2),
                     "source": "direct", "trip_id": None,
                     "invoice_no": s["invoice_no"] or "", "note": b["note"] or ""})
    rows.sort(key=lambda x: (x["date"], x.get("id") or 0), reverse=True)
    return rows[:200]


def warehouse(con):
    """Godam reconciliation: bags per party + own, client export bags, bardana."""
    def ready_tons(pid, bags_ready):
        # Tons value of the ready bags: production kg is exact per
        # record (bags x stamped per-bag weight), so the ready bags are
        # valued at that party's own production-weighted average kg/bag
        # (exact whenever the weight was uniform, the normal case).
        if pid is None:
            made_b = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production "
                                 "WHERE party_id IS NULL").fetchone()["s"]
            made_kg = production_powder_t(con, "WHERE party_id IS NULL") * 1000.0
            # own average also blends powder bought off-gate (its tons
            # are exact). Powder at OUTSIDE factories never enters the
            # godam, so it is NOT blended here.
            _pb = con.execute("SELECT COALESCE(SUM(bags),0) b, COALESCE(SUM(tons),0) t "
                              "FROM purchases WHERE item='powder' "
                              "AND COALESCE(source,'ledger')<>'direct'").fetchone()
            made_b += (_pb["b"] or 0)
            made_kg += (_pb["t"] or 0) * 1000.0
        else:
            made_b = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production "
                                 "WHERE party_id=?", (pid,)).fetchone()["s"]
            made_kg = production_powder_t(con, "WHERE party_id=?", (pid,)) * 1000.0
        avg = (made_kg / made_b) if made_b else 50.0
        return round(bags_ready * avg / 1000.0, 3)
    rows = []
    for p in con.execute("SELECT * FROM parties ORDER BY name"):
        made = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production WHERE party_id=?",
                           (p["id"],)).fetchone()["s"]
        out = con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips WHERE party_id=? AND direction='OUT' "
                          "AND COALESCE(fx,'')<>'none'",
                          (p["id"],)).fetchone()["s"]
        cb_recv = con.execute("SELECT COALESCE(SUM(bags),0) s FROM client_bags WHERE party_id=? AND direction='received'",
                              (p["id"],)).fetchone()["s"]
        cb_ret = con.execute("SELECT COALESCE(SUM(bags),0) s FROM client_bags WHERE party_id=? AND direction='returned'",
                             (p["id"],)).fetchone()["s"]
        cb_used = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production WHERE party_id=? AND bag_source='client'",
                              (p["id"],)).fetchone()["s"]
        adj = bag_adj_sum(con, p["id"])
        if made or out or cb_recv or adj:
            rows.append({"party_id": p["id"], "party": p["name"], "bags_made": made,
                         "bags_out": out, "bags_adj": adj,
                         "bags_ready": made - out + adj,
                         "bags_ready_t": ready_tons(p["id"], made - out + adj),
                         "powder_made_t": round(production_powder_t(
                             con, "WHERE party_id=?", (p["id"],)), 3),
                         "client_bags_received": cb_recv, "client_bags_used": cb_used,
                         "client_bags_returned": cb_ret,
                         "client_bags_left": cb_recv - cb_used - cb_ret})
    own_made = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production WHERE party_id IS NULL").fetchone()["s"]
    own_sold_bags = con.execute("SELECT COALESCE(SUM(bags),0) s FROM sales "
                                "WHERE COALESCE(item,'powder')='powder' "
                                "AND COALESCE(source,'ledger') NOT IN ('direct','outside')").fetchone()["s"]
    own_bought_bags = con.execute("SELECT COALESCE(SUM(bags),0) s FROM purchases "
                                  "WHERE item='powder' "
                                  "AND COALESCE(source,'ledger')<>'direct'").fetchone()["s"]
    # Own dispatches on Vehicle Out (fx='own' trips — dispatch-only
    # since 28 Oct 2026) take their bags out of the godam too; legacy
    # gate-sale bags already leave through own_sold_bags (their sale
    # rows), so the two never double-count.
    own_trip_bags = con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips "
                                "WHERE direction='OUT' AND party_id IS NULL "
                                "AND fx='own'").fetchone()["s"]
    # powder sitting at outside factories (informational only — it is
    # NOT godam stock and never enters bags_ready)
    own_outside_bags = outside_stock(con)["totals"]["powder_left_bags"]
    own_adj = bag_adj_sum(con, None)
    bardana_in = con.execute("SELECT COALESCE(SUM(bags),0) s FROM bag_movements WHERE direction='in'").fetchone()["s"]
    bardana_out = con.execute("SELECT COALESCE(SUM(bags),0) s FROM bag_movements WHERE direction='out'").fetchone()["s"]
    mill_used = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production WHERE bag_source='mill'").fetchone()["s"]
    bardana_left = bardana_in - bardana_out - mill_used
    _flt = own_filter_stock(con)
    return {"parties": rows,
            "own": {"bags_made": own_made, "bags_sold": own_sold_bags,
                    "bags_bought": own_bought_bags, "bags_outside": own_outside_bags,
                    "bags_dispatched": own_trip_bags,
                    "bags_adj": own_adj,
                    "bags_ready": own_made + own_bought_bags
                                  - own_sold_bags - own_trip_bags + own_adj,
                    "bags_ready_t": ready_tons(None, own_made + own_bought_bags
                                               - own_sold_bags - own_trip_bags + own_adj),
                    "powder_made_t": round(production_powder_t(
                        con, "WHERE party_id IS NULL"), 3),
                    # the mill's OWN filter pool (own_filter_stock):
                    # filter output of EVERY job, own and toll alike —
                    # never any party's stock (Talha, 28 Oct 2026)
                    "filter_bags": _flt["filter_bags"],
                    "filter_kg": _flt["filter_kg"]},
            "bardana": {"in": bardana_in, "out": bardana_out, "used": mill_used,
                        "left": bardana_left, "low": bardana_left < 100},
            # the same own pool under its long-standing top-level name
            # (assistant + older readers use it) — one source, so the
            # two can never drift apart
            "filter_powder_kg": _flt["filter_kg"],
            "ageing": powder_ageing(con)}

def bag_adj_sum(con, party_id):
    """Approved godam-ginti adjustments for one party (NULL = own bags).
    Only 'approved' rows ever touch book stock; pending/rejected are inert."""
    if party_id is None:
        r = con.execute("SELECT COALESCE(SUM(bags),0) s FROM bag_adjustments "
                        "WHERE party_id IS NULL AND status='approved'").fetchone()
    else:
        r = con.execute("SELECT COALESCE(SUM(bags),0) s FROM bag_adjustments "
                        "WHERE party_id=? AND status='approved'", (party_id,)).fetchone()
    return r["s"] or 0

def powder_ageing(con):
    """Ground powder / bags sitting ready longer than the setting
    powder_age_days (default 3) without dispatch. FIFO: production lots
    (by date) are consumed by dispatch — party lots by vehicle-OUT bags,
    own lots by sale bags (the same sources party_stock/own_stock use).
    Returns [{party_id(None=own), party, bags, tons, days}] — empty when
    everything moved within the limit."""
    import datetime as _d
    try:
        limit = int(meta_get(con, "powder_age_days", "3") or 3)
    except ValueError:
        limit = 3
    tday = _d.date.today()
    out = []
    def _aged(pid, label):
        if pid is None:
            lots = con.execute("SELECT date, bags, powder_bag_kg FROM production "
                               "WHERE party_id IS NULL ORDER BY date, id").fetchall()
            lots = [dict(r) for r in lots]
            lots.sort(key=lambda x: (x["date"],))
            gone = con.execute("SELECT COALESCE(SUM(bags),0) s FROM sales "
                               "WHERE COALESCE(item,'powder')='powder' "
                               "AND COALESCE(source,'ledger') NOT IN ('direct','outside')").fetchone()["s"]
            gone += con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips "
                                "WHERE party_id IS NULL AND direction='OUT' "
                                "AND fx='own'").fetchone()["s"]
        else:
            lots = con.execute("SELECT date, bags, powder_bag_kg FROM production "
                               "WHERE party_id=? ORDER BY date, id", (pid,)).fetchall()
            gone = con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips "
                               "WHERE party_id=? AND direction='OUT' "
                               "AND COALESCE(fx,'')<>'none'", (pid,)).fetchone()["s"]
        bags = 0
        kg = 0.0
        oldest = None
        for lot in lots:
            left = lot["bags"]
            if gone > 0:
                take = min(left, gone)
                left -= take
                gone -= take
            if left <= 0:
                continue
            try:
                age = (tday - _d.date.fromisoformat(lot["date"])).days
            except ValueError:
                continue
            if age > limit:
                bags += left
                kg += left * _bagw(lot["powder_bag_kg"])
                if oldest is None or age > oldest:
                    oldest = age
        if bags > 0:
            out.append({"party_id": pid, "party": label, "bags": bags,
                        "tons": round(kg / 1000.0, 3), "days": oldest,
                        "limit_days": limit})
    _aged(None, "Own")
    for p in con.execute("SELECT id, name FROM parties ORDER BY name"):
        _aged(p["id"], p["name"])
    return out

# ============================================================ ITEM I
_WA_TXT = {
 "en": {
  "greets": ["Assalam-o-Alaikum {party}, this is {mill}.",
             "Hello {party}, a message from {mill}.",
             "Dear {party}, here is your account update from {mill}.",
             "Assalam-o-Alaikum {party} — {mill} ki taraf se pegham.",
             "Greetings {party}, {mill} se aap ka hisaab:"],
  "before": "Rock already in stock: {v}", "came": "Just arrived by vehicle: {v}",
  "rock_now": "Total rock now: {v}", "ground": "Ground so far: {v}",
  "dispatched": "Powder dispatched: {v}", "powder_left": "Powder left: {bags} bags ({v})",
  "bal_you": "Your balance: Rs {amt} — you owe us (payable at your convenience)",
  "bal_we": "Your balance: Rs {amt} — we owe you",
  "bal_clear": "Your balance: Rs 0 — account is clear",
  "paid": "Total paid by you so far: Rs {amt}",
  "payline": "Payment numbers: {nums}",
  "closes": ["Thank you for your trust. — {mill}", "Thank you! Any question, please call us. — {mill}",
             "We value your business. Thank you. — {mill}", "Shukriya for working with us. — {mill}",
             "Thank you, and take care. — {mill}"]},
 "ur": {
  "greets": ["السلام علیکم {party}، یہ {mill} کی طرف سے پیغام ہے۔",
             "محترم {party}، {mill} سے آپ کے کھاتے کی تازہ صورتحال:",
             "{party} صاحب/صاحبہ، السلام علیکم — {mill} سے آپ کا حساب حاضر ہے۔",
             "السلام علیکم {party}، {mill} کی طرف سے:",
             "محترم {party}، آپ کے کھاتے کی تفصیل یہ ہے — {mill}"],
  "before": "پہلے سے پڑا ہوا مال: {v}", "came": "نئی گاڑی سے آیا: {v}",
  "rock_now": "اب کل راک: {v}", "ground": "پسائی ہو گئی: {v}",
  "dispatched": "پیسا ہوا مال نکل گیا: {v}", "powder_left": "پاؤڈر باقی: {bags} تھیلے ({v})",
  "bal_you": "آپ کا بیلنس: Rs {amt} — آپ نے دینے ہیں",
  "bal_we": "آپ کا بیلنس: Rs {amt} — ہم نے دینے ہیں",
  "bal_clear": "آپ کا بیلنس: Rs 0 — کھاتہ صاف ہے",
  "paid": "آپ اب تک بھیج چکے ہیں: Rs {amt} (کل ادائیگی)",
  "payline": "ادائیگی کے نمبر: {nums}",
  "closes": ["آپ کے اعتماد کا شکریہ۔ — {mill}", "شکریہ! کوئی سوال ہو تو فون کر لیں۔ — {mill}",
             "آپ کے کاروبار کی قدر کرتے ہیں، شکریہ۔ — {mill}", "ہمارے ساتھ کام کرنے کا شکریہ۔ — {mill}",
             "بہت شکریہ، اللہ حافظ۔ — {mill}"]},
 "hi": {
  "greets": ["नमस्ते {party}, यह संदेश {mill} की ओर से है।",
             "प्रिय {party}, {mill} से आपके खाते की ताज़ा जानकारी:",
             "{party} जी, नमस्ते — {mill} से आपका हिसाब:",
             "नमस्ते {party}, {mill} की ओर से:",
             "प्रिय {party}, आपके खाते का विवरण यह है — {mill}"],
  "before": "पहले से रखा माल: {v}", "came": "नई गाड़ी से आया: {v}",
  "rock_now": "अब कुल रॉक: {v}", "ground": "पिसाई हो गई: {v}",
  "dispatched": "पिसा माल निकल गया: {v}", "powder_left": "पाउडर बाकी: {bags} बोरे ({v})",
  "bal_you": "आपका बैलेंस: Rs {amt} — आपको देने हैं",
  "bal_we": "आपका बैलेंस: Rs {amt} — हमें देने हैं",
  "bal_clear": "आपका बैलेंस: Rs 0 — खाता साफ़ है",
  "paid": "आप अब तक भेज चुके हैं: Rs {amt} (कुल अदायगी)",
  "payline": "भुगतान नंबर: {nums}",
  "closes": ["आपके भरोसे का धन्यवाद। — {mill}", "धन्यवाद! कोई सवाल हो तो फ़ोन करें। — {mill}",
             "आपके व्यापार की कद्र करते हैं, धन्यवाद। — {mill}", "हमारे साथ काम करने का धन्यवाद। — {mill}",
             "बहुत धन्यवाद, अलविदा। — {mill}"]},
}
_WA_TXT["roman"] = _WA_TXT["en"]


def wa_compose(con, party_id, lang="en", unit="t", trip=None, style_no=None):
    """One composer for every client-bound WhatsApp text (Item I2).
    Returns {text, style_no}; >=5 rotating styles, numbers identical."""
    import random as _rnd
    p = con.execute("SELECT * FROM parties WHERE id=?", (party_id,)).fetchone()
    if not p:
        return None
    T = _WA_TXT.get(lang) or _WA_TXT["en"]
    mill = meta_get(con, "mill_name", APP_NAME)
    st = party_stock(con, party_id)
    _e, bal = party_ledger(con, party_id)
    bounced = {r[0] for r in con.execute(
        "SELECT payment_id FROM cheques WHERE status='bounced' AND payment_id IS NOT NULL")}
    paid = 0.0
    for r in con.execute("SELECT id,amount FROM payments WHERE party_id=? AND direction='in'",
                         (party_id,)):
        if r["id"] not in bounced:
            paid += r["amount"]
    nums = []
    for k in ("mill_phone", "owner_whatsapp"):
        v = meta_get(con, k)
        if v:
            nums.append(v)
    try:
        for b in json.loads(meta_get(con, "banks", "[]") or "[]"):
            if isinstance(b, str) and b.strip():
                nums.append(b.strip())
            elif isinstance(b, dict) and b.get("account"):
                nums.append("%s: %s" % (b.get("name", "Bank"), b["account"]))
    except Exception:
        pass
    W = lambda tons: fmt_weight(tons * 1000.0, unit)
    stock = []
    if trip:
        net_t = float(trip.get("net_t") or 0)
        stock.append(T["before"].format(v=W(st["rock_waiting_t"] - net_t)))
        stock.append(T["came"].format(v=W(net_t)))
    stock.append(T["rock_now"].format(v=W(st["rock_waiting_t"])))
    stock.append(T["ground"].format(v=W(st["ground_t"])))
    stock.append(T["dispatched"].format(v=W(st["powder_out_t"])))
    stock.append(T["powder_left"].format(bags=st["bags_ready"], v=W(st["powder_ready_t"])))
    if bal > 0:
        bal_line = T["bal_you"].format(amt=format(bal, ",.0f"))
    elif bal < 0:
        bal_line = T["bal_we"].format(amt=format(-bal, ",.0f"))
    else:
        bal_line = T["bal_clear"]
    money = [bal_line, T["paid"].format(amt=format(paid, ",.0f"))]
    if nums:
        money.append(T["payline"].format(nums=" · ".join(nums)))
    if style_no is None:
        style_no = _rnd.randint(1, 5)
    i = (style_no - 1) % 5
    blocks = [stock, money] if i not in (1, 3) else [money, stock]
    lines = [T["greets"][i].format(party=p["name"], mill=mill)]
    for b in blocks:
        lines.extend(b)
    close = T["closes"][i].format(mill=mill)
    if i in (0, 2, 4):
        close = "🙏 " + close
    lines.append(close)
    return {"text": "\\n".join(lines), "style_no": style_no}


def recent_events(con, since):
    """Item I1: activity events for voice alerts (derived, no new table)."""
    names = {r["id"]: r["name"] for r in con.execute("SELECT id,name FROM parties")}
    evs = []
    for r in con.execute("SELECT * FROM trips ORDER BY id DESC LIMIT 80"):
        evs.append({"eid": "trip:%d" % r["id"],
                    "kind": "vehicle_in" if r["direction"] == "IN" else "vehicle_out",
                    "date": r["date"], "party": names.get(r["party_id"]) or "Own",
                    "tons": round((r["net_kg"] or 0) / 1000.0, 3), "bags": r["bags"] or 0,
                    "vehicle_no": r["vehicle_no"] or "",
                    "_k": (r["date"], 1, r["id"])})
    for r in con.execute("SELECT * FROM payments ORDER BY id DESC LIMIT 80"):
        evs.append({"eid": "pay:%d" % r["id"],
                    "kind": "payment_in" if r["direction"] == "in" else "payment_out",
                    "date": r["date"], "party": names.get(r["party_id"]) or "Own",
                    "amount": r["amount"], "_k": (r["date"], 2, r["id"])})
    heads = {r["id"]: r["name"] for r in con.execute("SELECT id,name FROM expense_heads")}
    for r in con.execute("SELECT * FROM expenses WHERE status='pending' ORDER BY id DESC LIMIT 40"):
        evs.append({"eid": "exp:%d" % r["id"], "kind": "expense_pending",
                    "date": r["date"], "party": heads.get(r["head_id"]) or "",
                    "amount": r["amount"], "_k": (r["date"], 3, r["id"])})
    evs.sort(key=lambda e: e["_k"])
    for e in evs:
        e.pop("_k", None)
    # Watermark = per-table max ids ("t<trips>.p<payments>.e<expenses>"):
    # a single merged sort order can hide same-day events across tables,
    # so "new" is judged per table by row id (monotonic per table).
    mx = {"trip": 0, "pay": 0, "exp": 0}
    for tbl, key in (("trips", "trip"), ("payments", "pay"), ("expenses", "exp")):
        r = con.execute("SELECT COALESCE(MAX(id),0) m FROM " + tbl).fetchone()
        mx[key] = r["m"]
    token = "t%d.p%d.e%d" % (mx["trip"], mx["pay"], mx["exp"])
    if since:
        import re as _re
        m = _re.match(r"t(\d+)\.p(\d+)\.e(\d+)$", since.strip())
        if m:
            wm = {"trip": int(m.group(1)), "pay": int(m.group(2)), "exp": int(m.group(3))}
            new = [e for e in evs
                   if int(e["eid"].split(":")[1]) > wm[e["eid"].split(":")[0]]]
            return {"events": new, "latest": token}
    return {"events": [], "latest": token}


def machine_head_id(con):
    """Expense Ledger main head 'Machine' — auto-created once (E6)."""
    r = con.execute("SELECT id FROM expense_heads WHERE name='Machine' AND parent_id IS NULL").fetchone()
    if r:
        return r["id"]
    cur = con.execute("INSERT INTO expense_heads(name,parent_id) VALUES('Machine',NULL)")
    con.commit()
    return cur.lastrowid

def create_machine_entry(con, d, u):
    """Maintenance diary entry. Its cost posts ONCE into the Expense
    Ledger under the 'Machine' head (expense_id stored on the entry);
    deleting the entry voids that expense through the recycle path."""
    mid = int(d["machine_id"])
    m = con.execute("SELECT * FROM machines WHERE id=?", (mid,)).fetchone()
    if not m:
        raise ValueError("machine nahi mila")
    cost = float(d.get("cost") or 0)
    exp_id = None
    if cost > 0:
        r = create_expense(con, {
            "date": d.get("date") or today(), "head_id": machine_head_id(con),
            "amount": cost, "paid_kind": "owner", "method": "cash",
            "paid_to": m["name"],
            "note": "Machine maintenance: %s — %s" % (d.get("work_type") or "Service",
                                                       d.get("detail", ""))}, u)
        exp_id = r["id"]
    cur = con.execute(
        "INSERT INTO machine_entries(date,machine_id,work_type,detail,cost,next_due,"
        "expense_id,created_by) VALUES(?,?,?,?,?,?,?,?)",
        (d.get("date") or today(), mid, d.get("work_type") or "Service",
         d.get("detail", ""), cost, d.get("next_due", "") or "",
         exp_id, u["username"]))
    con.commit()
    return {"ok": True, "id": cur.lastrowid, "expense_id": exp_id}

def create_godam_count(con, d, u):
    """Physical bags count. Book bags are snapshotted from warehouse()
    at count time; a count NEVER changes stock by itself."""
    pid = d.get("party_id") or None
    if pid is not None:
        pid = int(pid)
    counted = int(d["counted_bags"])
    wh = warehouse(con)
    if pid is None:
        book = wh["own"]["bags_ready"]
    else:
        row = next((r for r in wh["parties"] if r["party_id"] == pid), None)
        book = row["bags_ready"] if row else 0
    cur = con.execute(
        "INSERT INTO godam_counts(date,party_id,counted_bags,book_bags,diff,note,created_by)"
        " VALUES(?,?,?,?,?,?,?)",
        (d.get("date") or today(), pid, counted, book, counted - book,
         d.get("note", ""), u["username"]))
    con.commit()
    return {"ok": True, "id": cur.lastrowid, "book_bags": book,
            "counted_bags": counted, "diff": counted - book}

def cost_per_ton(con, d_from, d_to):
    """E1: period cost/income per ton ground. Sources match P&L exactly:
    expenses = ledger rows with status!='rejected'; grinding income =
    SUM(grinding_jobs.amount); tons = jobs_ground_t (stored tons where
    a job has them, register-derived consumption where it does not) —
    the same figure day-end reports per day."""
    def s(sql, a=()):
        return con.execute(sql, a).fetchone()["s"] or 0
    tons = jobs_ground_t(con, "WHERE date>=? AND date<=?", (d_from, d_to))
    exp = s("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date>=? AND date<=? "
            "AND status!='rejected'", (d_from, d_to))
    inc = s("SELECT COALESCE(SUM(amount),0) s FROM grinding_jobs WHERE date>=? AND date<=?",
            (d_from, d_to))
    by_head = {}
    for r in con.execute(
            "SELECT e.amount amt, h.name hname, p.name pname FROM expenses e "
            "LEFT JOIN expense_heads h ON h.id=e.head_id "
            "LEFT JOIN expense_heads p ON p.id=h.parent_id "
            "WHERE e.date>=? AND e.date<=? AND e.status!='rejected'", (d_from, d_to)):
        main = r["pname"] or r["hname"] or "Other"
        by_head[main] = round(by_head.get(main, 0.0) + r["amt"], 2)
    ept = round(exp / tons, 2) if tons else None
    ipt = round(inc / tons, 2) if tons else None
    return {"from": d_from, "to": d_to, "tons_ground": round(tons, 3),
            "expenses": round(exp, 2), "expenses_by_head": by_head,
            "grinding_income": round(inc, 2),
            "expense_per_ton": ept, "income_per_ton": ipt,
            "margin_per_ton": (round(ipt - ept, 2) if (ept is not None and ipt is not None) else None)}

def party_business(con):
    """E2: per-party business summary — grinding income + trip charges
    billed to the party (freight when the party pays it, loading/unloading
    when the party bears it) + own-trade sales to the party − own-trade
    purchases from the party. A summary of business done, NOT a balance."""
    rows = []
    for p in con.execute("SELECT id, name FROM parties ORDER BY name"):
        pid = p["id"]
        def s(sql, a=(pid,)):
            return con.execute(sql, a).fetchone()["s"] or 0
        grind = s("SELECT COALESCE(SUM(amount),0) s FROM grinding_jobs WHERE party_id=?")
        fr = s("SELECT COALESCE(SUM(freight),0) s FROM trips WHERE party_id=? AND freight_payer='party'")
        lu = s("SELECT COALESCE(SUM(loading+unloading),0) s FROM trips WHERE party_id=? AND charge_bearer='party'")
        sales = s("SELECT COALESCE(SUM(amount),0) s FROM sales WHERE party_id=?")
        # Own-dispatch sales ride on the OUT trip row (no sales row):
        # the buyer is the sale_buyer — count them here exactly once.
        sales += s("SELECT COALESCE(SUM(net_kg/1000.0*sale_rate),0) s FROM trips "
                   "WHERE direction='OUT' AND sale_buyer_id=? AND sale_rate>0")
        purch = s("SELECT COALESCE(SUM(amount),0) s FROM purchases WHERE party_id=?")
        # vehicle-IN rock purchases are purchases from the SELLER too
        # (buy_from when set, else the trip party) — the same
        # attribution the party khata uses
        purch += s("SELECT COALESCE(SUM(net_kg/1000.0*rock_rate),0) s FROM trips "
                   "WHERE direction='IN' AND rock_rate>0 "
                   "AND COALESCE(buy_from_party_id, party_id)=?")
        # outside grinding, both directions of business with this
        # party: rock they sold us at the mine counts as a purchase
        # from them, and Grinding Bill charges at their factory are a
        # COST we pay them — never grinding income.
        purch += s("SELECT COALESCE(SUM(rock_amount),0) s FROM outside_grinding "
                   "WHERE from_party_id=? AND kind='sent'")
        purch += s("SELECT COALESCE(SUM(amount),0) s FROM outside_grinding "
                   "WHERE party_id=? AND kind='bill'")
        charges = fr + lu
        rows.append({"party_id": pid, "party": p["name"],
                     "grinding": round(grind, 2), "charges": round(charges, 2),
                     "sales": round(sales, 2), "purchases": round(purch, 2),
                     "net": round(grind + charges + sales - purch, 2)})
    rows.sort(key=lambda r: -r["net"])
    return rows

def demo_load(con, u):
    """One-click DEMO dataset (owner only, item F). Every created row is
    tracked as [table, id] in meta 'demo_ids' so demo_remove() deletes
    exactly those rows — children before parents — and nothing else.
    Returns the tracked list, or None when demo data is already loaded."""
    if meta_get(con, "demo_ids"):
        return None
    import datetime as _d
    base = _d.date.today()
    def ds(n):
        return (base - _d.timedelta(days=n)).isoformat()
    ids = []
    def track(tbl, r):
        ids.append([tbl, r["id"]])
    ahmed = create_party(con, {"name": "DEMO — Ahmed Traders", "phone": "0300-1111111",
                               "whatsapp": "0300-1111111", "address": "Demo address",
                               "roles": ["supplier", "buyer"], "credit_limit": 0,
                               "opening_balance": 15000}, u)
    track("parties", ahmed)
    bilal = create_party(con, {"name": "DEMO — Bilal Stone Co", "phone": "0300-2222222",
                               "whatsapp": "", "address": "", "roles": ["grinding"],
                               "credit_limit": 0, "opening_balance": -5000}, u)
    track("parties", bilal)
    A, B = ahmed["id"], bilal["id"]
    track("trips", create_trip(con, {"date": ds(3), "direction": "IN", "party_id": A,
        "vehicle_no": "DEMO-101", "driver": "Demo Driver", "gross_kg": 30000,
        "tare_kg": 5000, "net_kg": 25000, "bags": 0, "grade_pct": 28,
        "kind": "local", "note": "DEMO rock arrival"}, u, notify=False))
    track("grinding_jobs", create_job(con, {"date": ds(2), "party_id": A, "tons": 20,
        "rate_per_ton": 1200, "grade_pct": 28, "bags": 380, "note": "DEMO grinding"}, u))
    track("trips", create_trip(con, {"date": ds(2), "direction": "IN", "party_id": B,
        "vehicle_no": "DEMO-202", "driver": "Demo Driver", "gross_kg": 23000,
        "tare_kg": 5000, "net_kg": 18000, "bags": 0, "grade_pct": 26,
        "kind": "local", "note": "DEMO rock arrival"}, u, notify=False))
    track("production", create_production(con, {"date": ds(1), "bags": 300, "party_id": B,
        "bag_source": "mill", "kind": "local", "start_time": "08:00",
        "end_time": "16:00", "note": "DEMO production"}, u))
    # confirm_stock: Bilal's demo production above is a standalone
    # production row (no grinding job), so the canonical stock view
    # credits him 0 t of ready powder — the powder-stock gate
    # (28 Oct 2026) would stop this seeded dispatch; the demo seed
    # itself confirms the override, exactly like an owner would.
    track("trips", create_trip(con, {"date": ds(0), "direction": "OUT", "party_id": B,
        "vehicle_no": "DEMO-303", "driver": "Demo Driver", "gross_kg": 10000,
        "tare_kg": 5000, "net_kg": 5000, "bags": 100, "kind": "local",
        "note": "DEMO dispatch", "confirm_stock": True}, u, notify=False))
    track("payments", create_payment(con, {"date": ds(1), "party_id": A, "direction": "in",
        "amount": 50000, "method": "cash", "note": "DEMO payment"}, u))
    track("payments", create_payment(con, {"date": ds(0), "party_id": A, "direction": "out",
        "amount": 20000, "method": "cash", "note": "DEMO payment"}, u))
    diesel = con.execute("SELECT id FROM expense_heads WHERE name='Diesel'").fetchone()
    track("expenses", create_expense(con, {"date": ds(1),
        "head_id": diesel["id"] if diesel else None, "amount": 18000,
        "paid_kind": "owner", "method": "cash", "paid_to": "Demo Pump",
        "note": "DEMO diesel"}, u))
    track("cash_handovers", create_handover(con, {"date": ds(0), "amount": 30000,
        "holder_name": "Demo Manager", "note": "DEMO handover"}, u))
    order = create_order(con, {"date": ds(0), "party_id": A, "tons": 10, "bags": 200,
                                "rate_per_ton": 9000, "expected_date": ds(0),
                                "note": "DEMO order"}, u)
    track("orders", order)
    w1 = create_worker(con, {"name": "DEMO Theka Worker", "kind": "theka",
                             "rate_per_ton": 150, "rate_per_bag": 5}, u)
    track("workers", w1)
    w2 = create_worker(con, {"name": "DEMO Salary Worker", "kind": "salary",
                             "monthly_salary": 45000}, u)
    track("workers", w2)
    for w in (w1, w2):
        cur = con.execute("INSERT INTO attendance(worker_id,date,present,check_in,"
                          "check_out,overtime_hours) VALUES(?,?,1,'08:00','17:00',0)",
                          (w["id"], ds(0)))
        ids.append(["attendance", cur.lastrowid])
    con.commit()
    track("purchases", create_purchase(con, {"date": ds(3), "party_id": A, "tons": 40,
        "rate_per_ton": 3000, "grade_pct": 27, "deduction_pct": 0,
        "note": "DEMO own purchase"}, u))
    track("grinding_jobs", create_job(con, {"date": ds(2), "party_id": None, "tons": 30,
        "rate_per_ton": 0, "grade_pct": 27, "bags": 550, "note": "DEMO own grinding"}, u))
    track("production", create_production(con, {"date": ds(1), "bags": 500, "party_id": None,
        "bag_source": "mill", "kind": "local", "start_time": "08:00",
        "end_time": "20:00", "note": "DEMO own production"}, u))
    track("sales", create_sale(con, {"date": ds(0), "party_id": A, "tons": 10, "bags": 200,
        "rate_per_ton": 9000, "order_id": order["id"], "note": "DEMO own sale"}, u))
    meta_set(con, "demo_ids", json.dumps(ids))
    con.commit()
    return ids

_DEMO_CHILD_ORDER = ["attendance", "cash_handovers", "payments", "expenses",
                     "orders", "production", "trips", "grinding_jobs",
                     "purchases", "sales", "workers", "parties"]

def demo_remove(con, u):
    """Delete exactly the demo-tracked rows (children before parents) and
    clear the tracking key. Balances/stock are all derived live, so the
    prior state is restored exactly."""
    raw = meta_get(con, "demo_ids")
    if not raw:
        return 0
    by = {}
    for tbl, rid in json.loads(raw):
        by.setdefault(tbl, []).append(rid)
    n = 0
    for tbl in _DEMO_CHILD_ORDER + [t for t in by if t not in _DEMO_CHILD_ORDER]:
        for rid in by.get(tbl, []):
            con.execute("DELETE FROM %s WHERE id=?" % tbl, (rid,))
            n += 1
    meta_set(con, "demo_ids", "")
    con.commit()
    return n

def dept_of(con, worker):
    if worker["department_id"]:
        d = con.execute("SELECT * FROM departments WHERE id=?", (worker["department_id"],)).fetchone()
        if d:
            return d
    return None

def _mins(t):
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None

def compute_overtime(con, worker, date_str, check_in, check_out):
    """Overtime hours for one attendance day, from the department policy."""
    dept = dept_of(con, worker)
    if not dept or not dept["overtime_allowed"]:
        return 0.0
    ci, co = _mins(check_in or ""), _mins(check_out or "")
    if ci is None or co is None:
        return 0.0
    worked = (co - ci) / 60.0
    if worked < 0:
        worked += 24
    import datetime as _dt
    wd = _dt.date.fromisoformat(date_str).weekday()
    off = [int(x) for x in (dept["off_days"] or "").split(",") if x.strip() != ""]
    if wd in off:
        ot = worked
    else:
        shift = (_mins(dept["out_time"]) - _mins(dept["in_time"])) / 60.0
        ot = max(0.0, worked - shift)
    return round(ot * 4) / 4.0

def unpaid_leave_days(con, worker_id, month):
    """Approved unpaid leave days inside 'YYYY-MM'."""
    total = 0.0
    import datetime as _dt
    for r in con.execute("SELECT * FROM leaves WHERE worker_id=? AND status='approved' AND kind='unpaid'",
                         (worker_id,)):
        d1 = _dt.date.fromisoformat(r["from_date"])
        d2 = _dt.date.fromisoformat(r["to_date"])
        ms = _dt.date.fromisoformat(month + "-01")
        me = (_dt.date(ms.year + (1 if ms.month == 12 else 0), 1 if ms.month == 12 else ms.month + 1, 1)
              - _dt.timedelta(days=1))
        a, b = max(d1, ms), min(d2, me)
        if a <= b:
            total += (b - a).days + 1
    return total

def worker_dues(con, worker_id):
    w = con.execute("SELECT * FROM workers WHERE id=?", (worker_id,)).fetchone()
    if w is None:
        return {}
    dept = dept_of(con, w)
    ot_hours = con.execute("SELECT COALESCE(SUM(overtime_hours),0) s FROM attendance WHERE worker_id=?",
                           (worker_id,)).fetchone()["s"]
    ot_rate = float(dept["overtime_rate"] or 0) if dept else 0
    ot_earned = ot_hours * ot_rate
    paid = con.execute("SELECT COALESCE(SUM(amount),0) s FROM worker_payouts WHERE worker_id=?",
                       (worker_id,)).fetchone()["s"]
    out = {"worker_id": worker_id, "overtime_hours": ot_hours,
           "overtime_earned": ot_earned, "paid": paid}
    if w["kind"] == "theka":
        out_t = con.execute("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='OUT'").fetchone()["s"] / 1000.0
        bags = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production").fetchone()["s"]
        earned_ton = out_t * float(w["rate_per_ton"] or 0)
        earned_bag = bags * float(w["rate_per_bag"] or 0)
        earned = earned_ton + earned_bag + ot_earned
        out.update({"powder_out_t": out_t, "production_bags": bags,
                    "earned_per_ton": earned_ton, "earned_per_bag": earned_bag,
                    "earned": earned, "due": earned - paid})
    else:
        # salary accrual: one monthly salary per month from start month to
        # current month, minus approved unpaid leave (salary/30 per day)
        import datetime as _dt
        start = w["start_date"] or today()
        try:
            sd = _dt.date.fromisoformat(start)
        except Exception:
            sd = _dt.date.today()
        td = _dt.date.today()
        accrued = 0.0
        months = 0
        y, mth = sd.year, sd.month
        while (y, mth) <= (td.year, td.month):
            key = "%04d-%02d" % (y, mth)
            uld = unpaid_leave_days(con, worker_id, key)
            accrued += float(w["monthly_salary"] or 0) - uld * float(w["monthly_salary"] or 0) / 30.0
            months += 1
            mth += 1
            if mth > 12:
                mth, y = 1, y + 1
        earned = accrued + ot_earned
        out.update({"months_accrued": months, "salary_accrued": round(accrued, 2),
                    "earned": round(earned, 2), "due": round(earned - paid, 2)})
    return out

# ------------------------------------------------- cash in hand ---------
def _today():
    import datetime as _dt
    return _dt.date.today().isoformat()

def cash_rules(con):
    def _num(key, default):
        try:
            return float(meta_get(con, key, "") or default)
        except (TypeError, ValueError):
            return float(default)
    return {"holder_limit": _num("cash_holder_limit", 200000),
            "approval_limit": _num("cash_approval_limit", 25000)}

def holder_received(con, key):
    r = con.execute("SELECT COALESCE(SUM(amount),0) s FROM cash_handovers WHERE holder_key=?",
                    (key,)).fetchone()
    return float(r["s"] or 0)

def holder_spent(con, key):
    """Cash expenses linked to this holder; rejected expenses never count
    (the cash is treated as still with the holder)."""
    r = con.execute(
        "SELECT COALESCE(SUM(amount),0) s FROM expenses "
        "WHERE paid_by_holder=? AND LOWER(method)='cash' AND status!='rejected'",
        (key,)).fetchone()
    return float(r["s"] or 0)

def holder_balance(con, key):
    return holder_received(con, key) - holder_spent(con, key)

def holder_name_for(con, key, fallback=""):
    if key.startswith("user:"):
        try:
            uid = int(key.split(":", 1)[1])
        except ValueError:
            return fallback or key
        r = con.execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
        return (r["username"] if r else fallback) or key
    if key.startswith("name:"):
        return key.split(":", 1)[1]
    return fallback or key

def holder_summaries(con):
    """Per-holder cash-in-hand summary, derived live (no stored balances)."""
    names, order = {}, []
    def _see(key, nm=""):
        if key and key not in names:
            names[key] = nm or ""
            order.append(key)
        elif key and nm and not names.get(key):
            names[key] = nm
    for usr in con.execute(
            "SELECT id, username FROM users WHERE role IN ('manager','staff') ORDER BY id"):
        _see("user:%d" % usr["id"], usr["username"])
    for h in con.execute("SELECT holder_key, holder_name FROM cash_handovers ORDER BY id"):
        _see(h["holder_key"], h["holder_name"])
    for e in con.execute(
            "SELECT DISTINCT paid_by_holder FROM expenses WHERE paid_by_holder!=''"):
        _see(e["paid_by_holder"])
    out = []
    for key in order:
        received = holder_received(con, key)
        spent = holder_spent(con, key)
        pending_ack = con.execute(
            "SELECT COUNT(*) c FROM cash_handovers WHERE holder_key=? AND status='pending'",
            (key,)).fetchone()["c"]
        hist = []
        for h in con.execute("SELECT * FROM cash_handovers WHERE holder_key=? ORDER BY date, id",
                             (key,)):
            hist.append({"type": "in", "id": h["id"], "date": h["date"],
                         "amount": float(h["amount"] or 0), "note": h["note"] or "",
                         "status": h["status"]})
        for e in con.execute(
                "SELECT e.*, h.name head_name FROM expenses e "
                "LEFT JOIN expense_heads h ON h.id=e.head_id "
                "WHERE e.paid_by_holder=? AND LOWER(e.method)='cash' AND e.status!='rejected' "
                "ORDER BY e.date, e.id", (key,)):
            hist.append({"type": "out", "id": e["id"], "date": e["date"],
                         "amount": float(e["amount"] or 0),
                         "note": ((e["head_name"] or "") + (" — " if e["head_name"] and e["note"] else "") + (e["note"] or "")),
                         "status": e["status"]})
        hist.sort(key=lambda x: (x["date"], 0 if x["type"] == "in" else 1, x["id"]))
        counts = [dict(c) for c in con.execute(
            "SELECT * FROM cash_counts WHERE holder_key=? ORDER BY date DESC, id DESC",
            (key,))]
        out.append({"key": key, "name": holder_name_for(con, key, names.get(key, "")),
                    "is_user": key.startswith("user:"),
                    "received": received, "spent": spent,
                    "balance": received - spent,
                    "over": (received - spent) < 0,
                    "pending_ack": pending_ack,
                    "history": hist[-120:], "counts": counts})
    return out

def create_handover(con, d, u):
    """A cash handover: a TRANSFER to a holder — never an expense, never
    in P&L. User-holders start 'pending' until they acknowledge receipt."""
    date = (d.get("date") or _today()).strip() or _today()
    amount = _v_num(d.get("amount"), "Amount", required=True)
    if amount <= 0:
        raise ValueError("amount sahi likhein (0 se zyada)")
    uid = d.get("holder_user_id")
    if uid not in (None, "", 0):
        row = con.execute("SELECT id, username, role FROM users WHERE id=?", (int(uid),)).fetchone()
        if not row or row["role"] not in ("manager", "staff"):
            raise ValueError("holder user nahi mila (manager/staff hi ho sakta hai)")
        key, name, status = "user:%d" % row["id"], row["username"], "pending"
    else:
        nm = (d.get("holder_name") or "").strip()
        if not nm:
            raise ValueError("kisko cash diya — naam likhein ya user chunein")
        key, name, status = "name:" + nm, nm, "confirmed"
    before = holder_balance(con, key)
    cur = con.execute(
        "INSERT INTO cash_handovers(date,holder_key,holder_name,amount,note,entered_by,status) "
        "VALUES(?,?,?,?,?,?,?)",
        (date, key, name, amount, (d.get("note") or "").strip(), u["username"], status))
    con.commit()
    rules = cash_rules(con)
    warning = ""
    if before + amount > rules["holder_limit"]:
        warning = ("holder limit cross — %s ke paas ab Rs %s hain, limit Rs %s hai"
                   % (name, "{:,.0f}".format(before + amount), "{:,.0f}".format(rules["holder_limit"])))
    return {"ok": True, "id": cur.lastrowid, "status": status,
            "holder_key": key, "holder_name": name, "warning": warning}

def create_cash_count(con, d, u):
    """Physical cash count (ginti): a verification record only — it never
    changes the book balance."""
    key = (d.get("holder_key") or "").strip()
    if not key:
        raise ValueError("holder chunein")
    counted = _v_num(d.get("counted"), "Counted", required=True)
    book = holder_balance(con, key)
    diff = round(counted - book, 2)
    name = holder_name_for(con, key)
    cur = con.execute(
        "INSERT INTO cash_counts(date,holder_key,holder_name,counted,book,diff,note,entered_by) "
        "VALUES(?,?,?,?,?,?,?,?)",
        ((d.get("date") or _today()).strip() or _today(), key, name,
         counted, book, diff, (d.get("note") or "").strip(), u["username"]))
    con.commit()
    return {"ok": True, "id": cur.lastrowid, "book": book, "diff": diff, "counted": counted}

def bank_book(con):
    """Per-bank balances derived live from bank-method payments/expenses:
    opening + payments IN - payments OUT - expenses = current balance."""
    try:
        banks = json.loads(meta_get(con, "banks", "[]") or "[]")
    except Exception:
        banks = []
    try:
        openings = json.loads(meta_get(con, "bank_opening", "{}") or "{}")
    except Exception:
        openings = {}
    out = []
    for b in banks:
        opening = float(openings.get(b) or 0)
        pin = float(con.execute(
            "SELECT COALESCE(SUM(amount),0) s FROM payments WHERE LOWER(method)='bank' "
            "AND bank_name=? AND direction='in'", (b,)).fetchone()["s"] or 0)
        pout = float(con.execute(
            "SELECT COALESCE(SUM(amount),0) s FROM payments WHERE LOWER(method)='bank' "
            "AND bank_name=? AND direction='out'", (b,)).fetchone()["s"] or 0)
        exp = float(con.execute(
            "SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE LOWER(method) IN ('bank','cheque') "
            "AND pay_channel=? AND status!='rejected'", (b,)).fetchone()["s"] or 0)
        txns = []
        for p in con.execute(
                "SELECT p.*, pt.name party_name FROM payments p LEFT JOIN parties pt "
                "ON pt.id=p.party_id WHERE LOWER(p.method)='bank' AND p.bank_name=? "
                "ORDER BY p.date, p.id", (b,)):
            ref = p["ref_no"] or ""
            if not ref:
                ch = con.execute("SELECT cheque_no FROM cheques WHERE payment_id=?",
                                 (p["id"],)).fetchone()
                ref = (ch["cheque_no"] if ch else "") or ""
            txns.append({"date": p["date"],
                         "kind": "Payment IN" if p["direction"] == "in" else "Payment OUT",
                         "detail": (p["party_name"] or "") + ((" — " + p["note"]) if p["note"] else ""),
                         "ref": ref,
                         "amount": float(p["amount"] or 0) * (1 if p["direction"] == "in" else -1)})
        for e in con.execute(
                "SELECT e.*, h.name head_name FROM expenses e LEFT JOIN expense_heads h "
                "ON h.id=e.head_id WHERE LOWER(e.method) IN ('bank','cheque') "
                "AND e.pay_channel=? AND e.status!='rejected' ORDER BY e.date, e.id", (b,)):
            txns.append({"date": e["date"], "kind": "Expense",
                         "detail": (e["head_name"] or "") + ((" — " + (e["paid_to"] or "")) if e["paid_to"] else ""),
                         "ref": e["pay_ref"] or "",
                         "amount": -float(e["amount"] or 0)})
        txns.sort(key=lambda x: x["date"])
        out.append({"bank": b, "opening": opening, "in": pin, "out": pout,
                    "expenses": exp, "balance": opening + pin - pout - exp,
                    "txns": txns[-200:]})
    return {"banks": out}

def pnl(con, month):
    """month = 'YYYY-MM'. Expense-ledger entries are counted ONCE here
    (the single `expenses` table feeds both Cash Book and P&L)."""
    def s(sql, args=()):
        return con.execute(sql, args).fetchone()["s"] or 0
    like = month + "%"
    grind_inc = s("SELECT COALESCE(SUM(amount),0) s FROM grinding_jobs WHERE date LIKE ?", (like,))
    sales_inc = s("SELECT COALESCE(SUM(amount),0) s FROM sales WHERE date LIKE ?", (like,))
    # Own-dispatch sales (stored on the OUT trip, no sales row) are
    # sales income too — counted here exactly once, from the trip row.
    sales_inc += s("SELECT COALESCE(SUM(net_kg/1000.0*sale_rate),0) s FROM trips "
                   "WHERE direction='OUT' AND sale_buyer_id IS NOT NULL AND sale_rate>0 "
                   "AND date LIKE ?", (like,))
    purch = s("SELECT COALESCE(SUM(amount),0) s FROM purchases WHERE date LIKE ?", (like,))
    exp = s("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date LIKE ? AND status!='rejected'", (like,))
    payouts = s("SELECT COALESCE(SUM(amount),0) s FROM worker_payouts WHERE date LIKE ?", (like,))
    maint = s("SELECT COALESCE(SUM(cost),0) s FROM maintenance WHERE date LIKE ?", (like,))
    freight_mill = s("SELECT COALESCE(SUM(freight),0) s FROM trips WHERE date LIKE ? AND freight_payer='mill'", (like,))
    loading_mill = s("SELECT COALESCE(SUM(loading+unloading),0) s FROM trips WHERE date LIKE ? AND charge_bearer='mill'", (like,))
    # Mine-rate rent paid to the DRIVER in cash is a mill transport
    # cost like mill-borne freight; rent payable to the seller is a
    # khata payable instead and stays out of the mill's own costs
    rent_mill = s("SELECT COALESCE(SUM(rent),0) s FROM trips WHERE date LIKE ? AND direction='IN' AND rent_to='driver'", (like,))
    # Outside grinding (our rock ground by another mill) is its OWN
    # cost line — deliberately NOT folded into cost-per-ton of own
    # production (that figure reads expenses + grinding income only).
    outside_g = s("SELECT COALESCE(SUM(amount),0) s FROM outside_grinding "
                  "WHERE kind='bill' AND date LIKE ?", (like,))
    income = grind_inc + sales_inc
    costs = purch + exp + payouts + maint + freight_mill + loading_mill + rent_mill + outside_g
    _fm = factory_month(con, month)
    return {"month": month, "grinding_income": grind_inc, "sales_income": sales_inc,
            "income": income, "purchases": purch, "expenses": exp,
            "worker_payouts": payouts, "maintenance": maint,
            "freight_mill": freight_mill, "loading_mill": loading_mill,
            "rent_mill": rent_mill, "outside_grinding": outside_g,
            "costs": costs, "profit": income - costs,
            # factory Band din of the month (round 11): count in the
            # summary, the per-period list under it
            "factory_closed_days": _fm["closed_days"],
            "factory_periods": _fm["periods"]}

def cashbook(con, date_str):
    """Money in/out for one day, split by payment method."""
    methods = ["cash", "bank", "online", "cheque"]
    out = {"date": date_str, "methods": {}}
    tot_in = tot_out = 0.0
    for mth in methods:
        pin = con.execute("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE date=? AND direction='in' AND method=?",
                          (date_str, mth)).fetchone()["s"]
        pout = con.execute("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE date=? AND direction='out' AND method=?",
                           (date_str, mth)).fetchone()["s"]
        exp = con.execute("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date=? AND method=? AND status!='rejected'",
                          (date_str, mth)).fetchone()["s"]
        pay = con.execute("SELECT COALESCE(SUM(amount),0) s FROM worker_payouts WHERE date=? AND method=?",
                          (date_str, mth)).fetchone()["s"]
        o = pout + exp + pay
        out["methods"][mth] = {"in": pin, "out": o, "net": pin - o}
        tot_in += pin
        tot_out += o
    out["total_in"] = tot_in
    out["total_out"] = tot_out
    out["net"] = tot_in - tot_out
    out["total"] = out["net"]   # alias: cashbook UI + day-end text read .total
    return out

def _day_direct_trades(con, date_str):
    """Direct-trade deals closed on one day: count + total profit
    (sale legs minus purchase legs, grouped by deal)."""
    deals = {}
    for r in con.execute("SELECT deal_id, amount FROM purchases WHERE date=? "
                         "AND source='direct' AND deal_id<>''", (date_str,)):
        deals.setdefault(r["deal_id"], [0.0, 0.0])[0] += float(r["amount"] or 0)
    for r in con.execute("SELECT deal_id, amount FROM sales WHERE date=? "
                         "AND source='direct' AND deal_id<>''", (date_str,)):
        deals.setdefault(r["deal_id"], [0.0, 0.0])[1] += float(r["amount"] or 0)
    return {"count": len(deals),
            "profit": round(sum(s - p for p, s in deals.values()), 2)}


def _day_outside(con, date_str):
    """Outside Grinding for one day, new semantics: rock sent direct
    (mine -> factory, incl. the seller payable it created), powder
    ground per Grinding Bills, powder sold from the factories, and the
    bill charges accrued — totals + a per-mill breakdown."""
    mills = {}
    def M(fid, name):
        return mills.setdefault(fid, {"party_id": fid, "party": name or "",
                                       "party_name": name or "",
                                       "sent_t": 0.0, "rock_bought": 0.0,
                                       "produced_bags": 0.0, "produced_t": 0.0,
                                       "sold_bags": 0.0, "sold_amount": 0.0,
                                       "charges": 0.0})
    for r in con.execute(
            "SELECT og.party_id, p.name, og.kind, og.tons, og.bags, og.amount, og.rock_amount "
            "FROM outside_grinding og LEFT JOIN parties p ON p.id=og.party_id "
            "WHERE og.date=? ORDER BY og.id", (date_str,)):
        m = M(r["party_id"], r["name"])
        if r["kind"] == "sent":
            m["sent_t"] += float(r["tons"] or 0)
            m["rock_bought"] += float(r["rock_amount"] or 0)
        elif r["kind"] in ("bill", "received"):
            m["produced_bags"] += float(r["bags"] or 0)
            m["produced_t"] += float(r["tons"] or 0)
            if r["kind"] == "bill":
                m["charges"] += float(r["amount"] or 0)
    for r in con.execute(
            "SELECT s.og_factory_id, p.name, s.bags, s.amount FROM sales s "
            "LEFT JOIN parties p ON p.id=s.og_factory_id "
            "WHERE COALESCE(s.source,'')='outside' AND s.date=?", (date_str,)):
        m = M(r["og_factory_id"], r["name"])
        m["sold_bags"] += float(r["bags"] or 0)
        m["sold_amount"] += float(r["amount"] or 0)
    per = []
    for m in mills.values():
        per.append({"party_id": m["party_id"], "party": m["party"],
                    "party_name": m["party_name"],
                    "sent_t": round(m["sent_t"], 3),
                    "rock_bought": round(m["rock_bought"], 2),
                    "produced_bags": m["produced_bags"],
                    "produced_t": round(m["produced_t"], 3),
                    "sold_bags": m["sold_bags"],
                    "sold_amount": round(m["sold_amount"], 2),
                    "charges": round(m["charges"], 2)})
    def T(k, dec=3):
        return round(sum(m[k] for m in per), dec)
    return {"sent_t": T("sent_t"), "rock_bought": T("rock_bought", 2),
            "produced_bags": T("produced_bags", 0), "produced_t": T("produced_t"),
            "sold_bags": T("sold_bags", 0), "sold_amount": T("sold_amount", 2),
            "charges": T("charges", 2), "mills": per}


def day_end(con, date_str):
    def one(sql, a=()):
        return con.execute(sql, a).fetchone()["s"] or 0
    now = [dict(r) for r in con.execute(
        "SELECT gs.*, p.name party_name FROM grind_sessions gs LEFT JOIN parties p ON p.id=gs.party_id "
        "WHERE gs.ended='' ORDER BY gs.id DESC")]
    _split = production_split(con, date_str)
    _pct = wastage_pct(con)
    _powder_t = production_powder_t(con, "WHERE date=?", (date_str,))
    return {
        "date": date_str,
        "trips_in": one("SELECT COUNT(*) s FROM trips WHERE direction='IN' AND date=?", (date_str,)),
        "trips_out": one("SELECT COUNT(*) s FROM trips WHERE direction='OUT' AND date=?", (date_str,)),
        "rock_in_t": one("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='IN' AND date=?", (date_str,)) / 1000.0,
        "powder_out_t": one("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='OUT' AND date=?", (date_str,)) / 1000.0,
        "ground_t": round(jobs_ground_t(con, "WHERE date=?", (date_str,)), 3),
        "bags": one("SELECT COALESCE(SUM(bags),0) s FROM production WHERE date=?", (date_str,)),
        "filter_powder_kg": round(production_filter_kg(con, "WHERE date=?", (date_str,)), 3),
        # register figures: Day/Night split + wastage (reporting only);
        # powder tons use each record's stamped per-bag weight
        "bags_day": _split["day"], "bags_night": _split["night"],
        "bags_unclassified": _split["unclassified"],
        "powder_t": round(_powder_t, 3),
        "wastage_pct": _pct,
        "wastage_t": round(_powder_t * _pct / 100.0, 3),
        "cashbook": cashbook(con, date_str),
        "freight_mill": one("SELECT COALESCE(SUM(freight),0) s FROM trips WHERE date=? AND freight_payer='mill'", (date_str,)),
        "rent_mill": one("SELECT COALESCE(SUM(rent),0) s FROM trips WHERE date=? AND direction='IN' AND rent_to='driver'", (date_str,)),
        "expenses": one("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date=? AND status!='rejected'", (date_str,)),
        # ---- completeness pass: every daily activity, exactly once --
        # gate purchases (rock bought at Vehicle IN, incl. buy-from
        # sellers): count, tons and payable amount for the day
        "gate_purchases": {
            "count": one("SELECT COUNT(*) s FROM trips WHERE direction='IN' AND date=? AND rock_rate>0", (date_str,)),
            "tons": round(one("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='IN' AND date=? AND rock_rate>0", (date_str,)) / 1000.0, 3),
            "amount": round(one("SELECT COALESCE(SUM(net_kg/1000.0*rock_rate),0) s FROM trips WHERE direction='IN' AND date=? AND rock_rate>0", (date_str,)), 2),
            "rent_seller": one("SELECT COALESCE(SUM(rent),0) s FROM trips WHERE direction='IN' AND date=? AND rate_type='mine' AND rent_to='seller'", (date_str,))},
        # grinding earned today: grinding records + charges at Vehicle OUT
        "grinding_earned": round(one("SELECT COALESCE(SUM(amount),0) s FROM grinding_jobs WHERE date=?", (date_str,))
                                 + one("SELECT COALESCE(SUM(grind_charge),0) s FROM trips WHERE direction='OUT' AND date=?", (date_str,)), 2),
        # Gate sales at Vehicle Out: LEGACY round-9 sale rows linked
        # to trips (kept readable) PLUS Own-dispatch sales recorded on
        # the OUT trip itself (owner, 28 Oct 2026 — stored on the trip
        # row, no sales row). Each counted exactly once, here only.
        "gate_sales": {
            "count": one("SELECT COUNT(*) s FROM sales WHERE trip_id IS NOT NULL AND date=?", (date_str,))
                     + one("SELECT COUNT(*) s FROM trips WHERE direction='OUT' AND sale_buyer_id IS NOT NULL AND sale_rate>0 AND date=?", (date_str,)),
            "tons": round(one("SELECT COALESCE(SUM(tons),0) s FROM sales WHERE trip_id IS NOT NULL AND date=?", (date_str,))
                     + one("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='OUT' AND sale_buyer_id IS NOT NULL AND sale_rate>0 AND date=?", (date_str,)) / 1000.0, 3),
            "amount": round(one("SELECT COALESCE(SUM(amount),0) s FROM sales WHERE trip_id IS NOT NULL AND date=?", (date_str,))
                     + one("SELECT COALESCE(SUM(net_kg/1000.0*sale_rate),0) s FROM trips WHERE direction='OUT' AND sale_buyer_id IS NOT NULL AND sale_rate>0 AND date=?", (date_str,)), 2)},
        # off-gate own trades (ledger + Excel rows; direct deals apart)
        "trade_purchases": {
            "count": one("SELECT COUNT(*) s FROM purchases WHERE date=? AND COALESCE(source,'ledger')<>'direct'", (date_str,)),
            "amount": round(one("SELECT COALESCE(SUM(amount),0) s FROM purchases WHERE date=? AND COALESCE(source,'ledger')<>'direct'", (date_str,)), 2)},
        "trade_sales": {
            "count": one("SELECT COUNT(*) s FROM sales WHERE date=? AND trip_id IS NULL AND COALESCE(source,'ledger') NOT IN ('direct','outside')", (date_str,)),
            "amount": round(one("SELECT COALESCE(SUM(amount),0) s FROM sales WHERE date=? AND trip_id IS NULL AND COALESCE(source,'ledger') NOT IN ('direct','outside')", (date_str,)), 2)},
        "direct_trades": _day_direct_trades(con, date_str),
        "payments_in": round(one("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE date=? AND direction='in'", (date_str,)), 2),
        "payments_out": round(one("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE date=? AND direction='out'", (date_str,)), 2),
        "worker_payouts": round(one("SELECT COALESCE(SUM(amount),0) s FROM worker_payouts WHERE date=?", (date_str,)), 2),
        "cash_handovers": round(one("SELECT COALESCE(SUM(amount),0) s FROM cash_handovers WHERE date=?", (date_str,)), 2),
        "attendance_present": one("SELECT COUNT(*) s FROM attendance WHERE date=? AND present=1", (date_str,)),
        "outside_grinding": _day_outside(con, date_str),
        # aliases the UI reads (it showed "undefined"/NaN without them):
        # total vehicle trips today + expense total under its UI name
        "trips": one("SELECT COUNT(*) s FROM trips WHERE date=?", (date_str,)),
        "expense_total": one("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date=? AND status!='rejected'", (date_str,)),
        "now_grinding": now,
        # factory-closed shifts of the day (round 11): the Day-End
        # card names them next to the Day/Night bags split
        "shift_closures": shift_closures_for(con, date_str),
        # whole-day factory closure covering this date, if any
        "factory_closure": factory_closed_on(con, date_str),
    }

# ------------------------------------------- phosphate detail (register) --
def wastage_pct(con):
    """Mill setting: wastage % applied to the day's powder in the register
    report (Settings, owner-editable, default 5). Reporting figure only —
    it never changes warehouse/stock numbers."""
    try:
        v = float(meta_get(con, "wastage_pct", "5") or 5)
    except (TypeError, ValueError):
        v = 5.0
    return min(100.0, max(0.0, v))

def bag_kg(con):
    """Mill setting: kg in ONE bag for the GRINDING entry's Bags mode
    (owner-editable on the Grinding page, default 50). Scope is only the
    grinding entry conversion + its readout — production/warehouse
    packing keeps the standard 50 kg (BAG_TONS)."""
    try:
        v = float(meta_get(con, "bag_kg", "50") or 50)
    except (TypeError, ValueError):
        v = 50.0
    if v <= 0 or v > 1000:
        v = 50.0
    return v

def _save_bag_kg(con, raw):
    """Validate + store the bag_kg setting. Returns an error string or
    None. Shared by the owner Settings save and the Grinding page card
    (owner/manager endpoint)."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return "bag ka wazan number likhein"
    if v <= 0 or v > 1000:
        return "bag ka wazan 0 se zyada aur 1000 kg tak rakhein"
    meta_set(con, "bag_kg", str(v))
    return None

def bag_weights(con):
    """Mill settings: kg in ONE bag for each production output — powder
    bags and filter-powder bags (owner/manager editable on the
    Grinding & Production page's 'Bag weight defaults' card; defaults
    50 / 50). These are DEFAULTS only: every production save stamps the
    weights in effect at that moment onto its own row, so changing a
    default never rewrites an old record's tons."""
    def _one(key):
        try:
            v = float(meta_get(con, key, "50") or 50)
        except (TypeError, ValueError):
            v = 50.0
        return v if 0 < v <= 1000 else 50.0
    return {"powder_bag_kg": _one("powder_bag_kg"),
            "filter_bag_kg": _one("filter_bag_kg")}

def _save_bag_weights(con, praw, fraw):
    """Validate + store both bag-weight defaults. Returns an error
    string or None. Shared by the defaults-card endpoint (owner /
    manager) and the owner Settings save."""
    vals = {}
    for key, raw in (("powder_bag_kg", praw), ("filter_bag_kg", fraw)):
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return "bag ka wazan number likhein"
        if v <= 0 or v > 1000:
            return "bag ka wazan 0 se zyada aur 1000 kg tak rakhein"
        vals[key] = v
    for key, v in vals.items():
        meta_set(con, key, str(v))
    return None

def _resolve_bagw(raw, default):
    """Per-bag weight for a save: an explicit payload value wins (the
    Excel module carries the weights in the file); a missing/invalid
    value falls back to the given default (the current setting)."""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return default
    return v if 0 < v <= 1000 else default

def _shift_class(start_time):
    """Day = shift start in [06:00, 18:00); Night = any other start time;
    '' when the entry has no usable start time (counts in the day total
    but in neither class)."""
    st = (start_time or "").strip()
    if len(st) < 5:
        return ""
    try:
        h = int(st[:2])
    except (TypeError, ValueError):
        return ""
    return "day" if 6 <= h < 18 else "night"

def _entry_shift(r):
    """Shift class of one production row. Precedence: the linked grinding
    job's explicit Shift (Day/Night picked on the Grinding entry) wins;
    otherwise the production entry's own start_time decides (Day =
    06:00-18:00); no time and no job shift -> '' (counts in the day
    total only, never in either class)."""
    js = (r["job_shift"] or "") if "job_shift" in r.keys() else ""
    if js in ("Day", "Night"):
        return js.lower()
    return _shift_class(r["start_time"])

def production_split(con, date_str):
    """Bags for one day split by shift class (see _entry_shift)."""
    out = {"day": 0, "night": 0, "unclassified": 0, "total": 0}
    for r in con.execute(
            "SELECT p.bags, p.start_time, gj.shift AS job_shift FROM production p "
            "LEFT JOIN grinding_jobs gj ON gj.id = p.job_id WHERE p.date=?",
            (date_str,)):
        cls = _entry_shift(r)
        if cls == "day":
            out["day"] += r["bags"]
        elif cls == "night":
            out["night"] += r["bags"]
        else:
            out["unclassified"] += r["bags"]
        out["total"] += r["bags"]
    return out

# ------------------------------------------------ daily alerts (round 11) --
# Two reminder families share ONE check (GET /api/shift-alert), ONE
# popup flow and ONE dismissal table:
#  * SHIFT alerts (Manager/Staff who can open Grinding & Production):
#    after a shift ends, if its production entry is still missing, the
#    next app open asks for it — Enter Now (prefilled form), Later
#    (per-user dismissal), or Factory Closed (a shift_closures row
#    clears the shift for everyone).
#  * VEHICLE alerts (Owner + Manager + Staff): after the daily review
#    time, a day with no Vehicle In and/or no Vehicle Out recorded yet
#    gets a "so far today" notice, acknowledged per user per day.
# Candidates are always the LAST ENDED Day shift and the LAST ENDED
# Night shift, so at most two shift alerts can ever be due — the
# twice-a-day rhythm the owner asked for, with no stale build-up.

def _hhmm(value, default):
    """Validate an 'HH:MM' setting value; default when unusable."""
    parts = str(value or "").strip().split(":")
    if len(parts) == 2:
        try:
            h, m = int(parts[0]), int(parts[1])
        except ValueError:
            return default
        if 0 <= h <= 23 and 0 <= m <= 59:
            return "%02d:%02d" % (h, m)
    return default

def shift_end_settings(con):
    """Owner-editable alert timings (Settings -> Mill Profile).
    day_shift_end 19:00 / night_shift_end 07:00: when each shift ends
    and its missing-entry alert becomes due. vehicle_alert_time 20:00:
    the daily review time for the vehicle movement notices."""
    return {"day_shift_end": _hhmm(meta_get(con, "day_shift_end", "19:00"), "19:00"),
            "night_shift_end": _hhmm(meta_get(con, "night_shift_end", "07:00"), "07:00"),
            "vehicle_alert_time": _hhmm(meta_get(con, "vehicle_alert_time", "20:00"), "20:00")}

def _shift_entry_exists(con, date_str, shift):
    """A production entry exists for (date, shift) when a production
    row of that date classifies to the shift (the codebase's
    _entry_shift rule), or a grinding job of that date+shift carries
    bags (legacy job-only entries)."""
    for r in con.execute(
            "SELECT p.start_time, gj.shift AS job_shift FROM production p "
            "LEFT JOIN grinding_jobs gj ON gj.id = p.job_id WHERE p.date=?",
            (date_str,)):
        if _entry_shift(r) == shift.lower():
            return True
    r = con.execute("SELECT COUNT(*) c FROM grinding_jobs "
                    "WHERE date=? AND shift=? AND bags>0",
                    (date_str, shift)).fetchone()
    return bool(r and r["c"])

def _alert_dismissed(con, username, kind, date_str, shift=""):
    r = con.execute("SELECT COUNT(*) c FROM alert_dismissals WHERE "
                    "username=? AND kind=? AND date=? AND shift=?",
                    (username, kind, date_str, shift)).fetchone()
    return bool(r and r["c"])

def shift_closures_for(con, date_str):
    """Factory-closed records for one date (Grinding page + Day-End)."""
    return [dict(r) for r in con.execute(
        "SELECT date, shift, reason, note, by_user, created "
        "FROM shift_closures WHERE date=? ORDER BY id", (date_str,))]

def daily_alerts(con, u, now=None):
    """Due alerts for one login. Eligibility lives here (the route's
    generic perm is None): shift alerts — manager, or staff holding
    the grinding/production perm; the OWNER is deliberately not
    nagged about entries (veto-able, owner's call). Vehicle alerts —
    owner + manager, or staff holding the vehicles perm. Client and
    demo logins never receive either family."""
    import datetime as _dt
    out = {"shift_alerts": [], "vehicle_alerts": [],
           "settings": shift_end_settings(con)}
    if not u:
        return out
    role = u.get("role")
    perms = user_perms(u)
    now = now or _dt.datetime.now()
    today_d = now.date()
    now_min = now.hour * 60 + now.minute

    def _min(hhmm):
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)

    if role == "manager" or (role == "staff"
                             and ("grinding" in perms or "production" in perms)):
        cfg = out["settings"]
        # Day shift of date D ends on D at day_shift_end; Night shift
        # of date D (the register's date convention: the night belongs
        # to the date it started) ends on D+1 at night_shift_end.
        day_date = today_d if now_min >= _min(cfg["day_shift_end"]) \
            else today_d - _dt.timedelta(days=1)
        night_date = today_d - _dt.timedelta(days=1) \
            if now_min >= _min(cfg["night_shift_end"]) \
            else today_d - _dt.timedelta(days=2)
        for d, shift in ((day_date, "Day"), (night_date, "Night")):
            ds = d.isoformat()
            if _shift_entry_exists(con, ds, shift):
                continue
            if con.execute("SELECT COUNT(*) c FROM shift_closures "
                           "WHERE date=? AND shift=?",
                           (ds, shift)).fetchone()["c"]:
                continue
            if factory_closed_on(con, ds):
                continue   # whole-day factory closure covers this date
            if _alert_dismissed(con, u["username"], "shift", ds, shift):
                continue
            out["shift_alerts"].append({"date": ds, "shift": shift})
        out["shift_alerts"].sort(key=lambda a: a["date"])
    if role in ("owner", "manager") or (role == "staff" and "vehicles" in perms):
        if now_min >= _min(out["settings"]["vehicle_alert_time"]):
            ds = today_d.isoformat()
            # NOTE (Talha's correction, 29 Oct 2026): a factory
            # closure does NOT suppress vehicle alerts — rock still
            # arrives and ready powder still dispatches while
            # grinding is stopped. Only the shift alerts above are
            # closure-suppressed.
            dispatchable = None   # lazy: computed only if OUT is due
            for kind, direction in (("vehicle_in", "IN"), ("vehicle_out", "OUT")):
                n = con.execute("SELECT COUNT(*) c FROM trips "
                                "WHERE date=? AND direction=?",
                                (ds, direction)).fetchone()["c"]
                if n:
                    continue
                if kind == "vehicle_out":
                    # Stock-aware on EVERY day: a loaded departure is
                    # only possible when dispatchable ready powder
                    # exists — own ready powder plus every party's
                    # ready powder, via the canonical stock helpers.
                    # Filter powder never counts (no dispatch path).
                    if dispatchable is None:
                        dispatchable = own_stock(con)["powder_left_t"] + sum(
                            party_stock(con, p["id"])["powder_ready_t"]
                            for p in con.execute("SELECT id FROM parties"))
                    if dispatchable <= 0:
                        continue
                if _alert_dismissed(con, u["username"], kind, ds):
                    continue
                out["vehicle_alerts"].append({"type": kind, "date": ds})
    return out

# ------------------------------------------- factory open/closed status --
# A closure PERIOD (round 11): the factory is closed for whole days,
# [closed_from, closed_to) — closed_to is the REOPENING day (the
# first open day), NULL while still closed. One press reopens:
# closed_to = today. Whole-day periods sit ABOVE the single-shift
# closures: they suppress that date's SHIFT-entry alerts only
# (vehicle alerts keep working on closed days — Talha's correction),
# appear in Day-End and are totalled in the monthly P&L. Toggling
# is Owner + Manager only.
FACTORY_REASONS = ("power_outage", "breakdown", "maintenance_work",
                   "no_material", "other")

def factory_closed_on(con, date_str):
    """The closure period covering date_str, or None. A date counts
    as closed when a period starts on/before it and reopens after
    it (or has not reopened yet)."""
    r = con.execute(
        "SELECT * FROM factory_closures WHERE closed_from<=? "
        "AND (closed_to IS NULL OR closed_to>?) "
        "ORDER BY closed_from DESC, id DESC LIMIT 1",
        (date_str, date_str)).fetchone()
    return dict(r) if r else None

def factory_status(con):
    """Current status for the sidebar button / banner: closed when a
    period covers TODAY; 'days' = closed days so far, today counted."""
    import datetime as _dt
    cur = factory_closed_on(con, today())
    if cur:
        try:
            cur["days"] = (_dt.date.today()
                           - _dt.date.fromisoformat(cur["closed_from"])).days + 1
        except ValueError:
            cur["days"] = 1
    return {"closed": bool(cur), "current": cur}

def factory_month(con, month):
    """Closed days inside one 'YYYY-MM' month + the periods touching
    it, each with its IN-MONTH day count (a period spanning a month
    boundary counts only its in-month days). An open period counts
    up to today (inclusive) until it is reopened."""
    import datetime as _dt
    try:
        y, m = int(month[:4]), int(month[5:7])
        first = _dt.date(y, m, 1)
    except (ValueError, IndexError):
        return {"month": month, "closed_days": 0, "periods": []}
    nxt = _dt.date(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
    today_d = _dt.date.today()
    periods, total = [], 0
    for r in con.execute(
            "SELECT * FROM factory_closures WHERE closed_from<? "
            "AND (closed_to IS NULL OR closed_to>?) ORDER BY closed_from",
            (nxt.isoformat(), first.isoformat())):
        row = dict(r)
        try:
            start = max(_dt.date.fromisoformat(row["closed_from"]), first)
            if row["closed_to"]:
                end = min(_dt.date.fromisoformat(row["closed_to"]), nxt)
            else:
                end = min(today_d + _dt.timedelta(days=1), nxt)
        except ValueError:
            continue
        days = (end - start).days
        if days > 0:
            row["days_in_month"] = days
            # Gate activity inside the SAME in-month slice of the
            # period: the gate keeps working while grinding is
            # stopped (rock still arrives, ready powder still
            # dispatches), so the monthly reader sees the mill was
            # not fully idle on those days. Powder counts only
            # stock-moving OUT trips (fx='none' gate passes excluded,
            # the same rule party_stock uses).
            row["gate_rock_t"] = round((con.execute(
                "SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE "
                "direction='IN' AND date>=? AND date<?",
                (start.isoformat(), end.isoformat())).fetchone()["s"]
                or 0) / 1000.0, 3)
            row["gate_powder_t"] = round((con.execute(
                "SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE "
                "direction='OUT' AND COALESCE(fx,'')<>'none' "
                "AND date>=? AND date<?",
                (start.isoformat(), end.isoformat())).fetchone()["s"]
                or 0) / 1000.0, 3)
            periods.append(row)
            total += days
    return {"month": month, "closed_days": total, "periods": periods}

def phosphate_detail(con, date_str):
    """The paper register ("Phosphate Detail") for one day, whole mill.

    Register definitions (documented in the view + assistant guide):
    - Rock In (day)     = vehicle IN net tons + own-rock purchase tons.
    - Total Stock       = the register rock position at the START of the day.
    - Total Rock        = Total Stock + Rock In.
    - Powder In Ton     = bags produced that day x each record's stamped
      per-bag weight (the standard 50 kg on legacy records).
    - Wastage           = Powder In Ton x wastage_pct / 100 (reporting only).
    - Balance Rock      = Total Rock - (Powder In Ton + Wastage). The
      register treats PRODUCTION as the rock consumption, so the position
      runs cumulatively day by day from the first recorded day, starting
      from the rock stock before that day (0 in a fresh system).
    - Previous Powder   = godam powder balance (bags x 50 kg) at day start,
      from production - dispatch (vehicle OUT bags + own sale bags)
      + powder bought off-gate (bags) + approved ginti adjustments,
      cumulative from the first record.
    - Dispatched        = powder that left the GODAM today: vehicle OUT
      bags (gate passes excluded) + own-stock sale bags (ledger / Excel).
      Powder sold from an OUTSIDE factory is NEVER dispatched here — it
      was never in the godam (every godam reader excludes source=
      'outside' sales; the register now does the same — before this fix
      an outside sale wrongly dropped Balance Powder while the Warehouse
      stood still).
    - Balance Powder    = Previous + Powder In Ton - dispatched today
      (+ the day's bought bags and approved adjustments) — reconciles
      with the Warehouse powder balance at day end.
    - Filter powder     = NEVER in this register. Powder In Ton counts
      powder bags only, so a client's recovery in the register is its
      powder alone; the filter output of a job is the mill's own stock
      (own_filter_stock, Talha's rule 28 Oct 2026) and sits on the
      client's wastage side of the story, inside the same loss the
      register's wastage % reports. NO formula changed for this rule:
      the wastage figure stays the mill's wastage_pct of the powder
      (the agreed reporting %, which already covers total grinding
      loss) — adding filter tons on top would double-count the loss
      and break the paper-register reconciliation.
    """
    pct = wastage_pct(con)

    def day_map(sql, args=()):
        m = {}
        for r in con.execute(sql, args):
            m[r["d"]] = r["s"] or 0
        return m

    rock_in = day_map("SELECT date d, SUM(net_kg)/1000.0 s FROM trips "
                      "WHERE direction='IN' AND date<=? GROUP BY date", (date_str,))
    for d, s in day_map("SELECT date d, SUM(tons) s FROM purchases "
                        "WHERE date<=? AND COALESCE(item,'rock')='rock' "
                        "AND COALESCE(source,'ledger')<>'direct' GROUP BY date",
                        (date_str,)).items():
        rock_in[d] = rock_in.get(d, 0) + s
    made = day_map("SELECT date d, SUM(bags) s FROM production "
                   "WHERE date<=? GROUP BY date", (date_str,))
    made_kg = day_map("SELECT date d, SUM(bags * COALESCE(powder_bag_kg, 50)) s "
                      "FROM production WHERE date<=? GROUP BY date", (date_str,))
    disp = day_map("SELECT date d, SUM(bags) s FROM trips "
                   "WHERE direction='OUT' AND COALESCE(fx,'')<>'none' AND date<=? GROUP BY date", (date_str,))
    # Own-stock sale bags leave the godam too — but NEVER the powder
    # sold from an outside factory (source='outside'): that powder sat
    # at the factory, not in the godam, and every godam reader excludes
    # it. (Fix, 28 Oct 2026: the old '<>direct' filter let outside
    # sales drain this register's Balance Powder.)
    for d, s in day_map("SELECT date d, SUM(bags) s FROM sales "
                        "WHERE date<=? AND COALESCE(item,'powder')='powder' "
                        "AND trip_id IS NULL AND COALESCE(source,'ledger') NOT IN ('direct','outside') "
                        "GROUP BY date", (date_str,)).items():
        disp[d] = disp.get(d, 0) + s
    adj = day_map("SELECT date d, SUM(bags) s FROM bag_adjustments "
                  "WHERE status='approved' AND date<=? GROUP BY date", (date_str,))
    # Powder BOUGHT off-gate enters the godam in bags (the Warehouse
    # own view counts it in bags_ready), so the register chain carries
    # it too — shown on the day's row as a side figure (bought_bags),
    # exactly like the ginti adjustments.
    bought = day_map("SELECT date d, SUM(bags) s FROM purchases "
                     "WHERE date<=? AND item='powder' "
                     "AND COALESCE(source,'ledger')<>'direct' GROUP BY date", (date_str,))

    days = sorted(set(rock_in) | set(made) | set(disp) | set(adj) | set(bought))
    rock_pos = 0.0          # register rock position (end of previous day)
    powder_bags = 0         # godam powder bags (end of previous day)
    row = None
    for d in days:
        if d > date_str:
            break
        powder_t = made_kg.get(d, 0) / 1000.0
        waste_t = powder_t * pct / 100.0
        if d == date_str:
            row = {"total_stock_rock_t": rock_pos,
                   "rock_in_t": rock_in.get(d, 0),
                   "total_rock_t": rock_pos + rock_in.get(d, 0),
                   "powder_in_t": powder_t, "wastage_t": waste_t,
                   "prev_powder_bags": powder_bags,
                   "balance_rock_t": rock_pos + rock_in.get(d, 0) - powder_t - waste_t}
        rock_pos = rock_pos + rock_in.get(d, 0) - powder_t - waste_t
        powder_bags = (powder_bags + made.get(d, 0) - disp.get(d, 0)
                       + adj.get(d, 0) + bought.get(d, 0))
    if row is None:
        # the chosen day itself has no stock activity at all
        row = {"total_stock_rock_t": rock_pos, "rock_in_t": 0.0,
               "total_rock_t": rock_pos, "powder_in_t": 0.0, "wastage_t": 0.0,
               "prev_powder_bags": powder_bags, "balance_rock_t": rock_pos}
    split = production_split(con, date_str)
    dispatched_bags = disp.get(date_str, 0)
    adj_bags = adj.get(date_str, 0)
    bought_bags = bought.get(date_str, 0)
    balance_bags = (row["prev_powder_bags"] + split["total"] - dispatched_bags
                    + adj_bags + bought_bags)

    # ---- per-party breakdown for the chosen day ----
    names = {p["id"]: p["name"] for p in con.execute("SELECT id, name FROM parties")}

    def prow(pid):
        if pid is None:
            rin = (con.execute("SELECT COALESCE(SUM(net_kg),0)/1000.0 s FROM trips "
                               "WHERE direction='IN' AND party_id IS NULL AND date=?",
                               (date_str,)).fetchone()["s"] or 0)
            out_b = (con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips "
                                 "WHERE direction='OUT' AND party_id IS NULL AND date=? "
                                 "AND COALESCE(fx,'')<>'none'",
                                 (date_str,)).fetchone()["s"] or 0)
            out_b += (con.execute("SELECT COALESCE(SUM(bags),0) s FROM sales WHERE date=? "
                                  "AND COALESCE(item,'powder')='powder' AND trip_id IS NULL "
                                  "AND COALESCE(source,'ledger') NOT IN ('direct','outside')",
                                  (date_str,)).fetchone()["s"] or 0)
        else:
            rin = (con.execute("SELECT COALESCE(SUM(net_kg),0)/1000.0 s FROM trips "
                               "WHERE direction='IN' AND party_id=? AND date=?",
                               (pid, date_str)).fetchone()["s"] or 0)
            rin += (con.execute("SELECT COALESCE(SUM(tons),0) s FROM purchases "
                                "WHERE party_id=? AND date=? "
                                "AND COALESCE(item,'rock')='rock' "
                                "AND COALESCE(source,'ledger')<>'direct'",
                                (pid, date_str)).fetchone()["s"] or 0)
            out_b = (con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips "
                                 "WHERE direction='OUT' AND party_id=? AND date=? "
                                 "AND COALESCE(fx,'')<>'none'",
                                 (pid, date_str)).fetchone()["s"] or 0)
        sp = {"day": 0, "night": 0, "total": 0, "kg": 0.0}
        if pid is None:
            prows = con.execute("SELECT p.bags, p.powder_bag_kg, p.start_time, gj.shift AS job_shift "
                                "FROM production p LEFT JOIN grinding_jobs gj "
                                "ON gj.id = p.job_id "
                                "WHERE p.party_id IS NULL AND p.date=?", (date_str,))
        else:
            prows = con.execute("SELECT p.bags, p.powder_bag_kg, p.start_time, gj.shift AS job_shift "
                                "FROM production p LEFT JOIN grinding_jobs gj "
                                "ON gj.id = p.job_id "
                                "WHERE p.party_id=? AND p.date=?", (pid, date_str))
        for r in prows:
            cls = _entry_shift(r)
            if cls in ("day", "night"):
                sp[cls] += r["bags"]
            sp["total"] += r["bags"]
            sp["kg"] += float(r["bags"] or 0) * _bagw(r["powder_bag_kg"])
        # powder balance at day end (bags, cumulative) for this party
        if pid is None:
            bal = (con.execute("SELECT COALESCE(SUM(bags),0) s FROM production "
                               "WHERE party_id IS NULL AND date<=?", (date_str,)).fetchone()["s"] or 0)
            bal -= (con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips "
                                "WHERE direction='OUT' AND party_id IS NULL AND date<=? "
                                "AND COALESCE(fx,'')<>'none'",
                                (date_str,)).fetchone()["s"] or 0)
            bal -= (con.execute("SELECT COALESCE(SUM(bags),0) s FROM sales WHERE date<=? "
                                "AND COALESCE(item,'powder')='powder' AND trip_id IS NULL "
                                "AND COALESCE(source,'ledger') NOT IN ('direct','outside')",
                                (date_str,)).fetchone()["s"] or 0)
            # powder bought off-gate is Own godam stock (its seller is
            # just the khata party) — same term as the Warehouse own view
            bal += (con.execute("SELECT COALESCE(SUM(bags),0) s FROM purchases "
                                "WHERE item='powder' AND date<=? "
                                "AND COALESCE(source,'ledger')<>'direct'",
                                (date_str,)).fetchone()["s"] or 0)
            bal += (con.execute("SELECT COALESCE(SUM(bags),0) s FROM bag_adjustments "
                                "WHERE status='approved' AND party_id IS NULL AND date<=?",
                                (date_str,)).fetchone()["s"] or 0)
        else:
            bal = (con.execute("SELECT COALESCE(SUM(bags),0) s FROM production "
                               "WHERE party_id=? AND date<=?", (pid, date_str)).fetchone()["s"] or 0)
            bal -= (con.execute("SELECT COALESCE(SUM(bags),0) s FROM trips "
                                "WHERE direction='OUT' AND party_id=? AND date<=? "
                                "AND COALESCE(fx,'')<>'none'",
                                (pid, date_str)).fetchone()["s"] or 0)
            bal += (con.execute("SELECT COALESCE(SUM(bags),0) s FROM bag_adjustments "
                                "WHERE status='approved' AND party_id=? AND date<=?",
                                (pid, date_str)).fetchone()["s"] or 0)
        return {"party_id": pid,
                "party": names.get(pid, "Own / Apna") if pid is not None else "Own / Apna",
                "rock_in_t": round(rin, 3), "bags_day": sp["day"],
                "bags_night": sp["night"], "bags_total": sp["total"],
                "powder_t": round(sp["kg"] / 1000.0, 3),
                "dispatched_t": round(out_b * 0.05, 3),
                "powder_balance_t": round(bal * 0.05, 3)}

    rows = [prow(p["id"]) for p in con.execute("SELECT id FROM parties ORDER BY name")]
    rows.append(prow(None))
    rows = [r for r in rows if r["party_id"] is None or r["rock_in_t"] or r["bags_total"]
            or r["dispatched_t"] or r["powder_balance_t"]]

    rk = con.execute("SELECT remark FROM daily_remarks WHERE date=?",
                     (date_str,)).fetchone()
    return {
        "date": date_str,
        "mill_name": meta_get(con, "mill_name", APP_NAME),
        "wastage_pct": pct,
        "total_stock_rock_t": round(row["total_stock_rock_t"], 3),
        "rock_in_t": round(row["rock_in_t"], 3),
        "total_rock_t": round(row["total_rock_t"], 3),
        "bags_day": split["day"], "bags_night": split["night"],
        "bags_unclassified": split["unclassified"], "bags_total": split["total"],
        "wastage_t": round(row["wastage_t"], 3),
        "powder_in_t": round(row["powder_in_t"], 3),
        "prev_powder_t": round(row["prev_powder_bags"] * 0.05, 3),
        "dispatched_t": round(dispatched_bags * 0.05, 3),
        "adj_bags": adj_bags,
        "bought_bags": bought_bags,
        "balance_powder_t": round(balance_bags * 0.05, 3),
        "balance_rock_t": round(row["balance_rock_t"], 3),
        "remark": rk["remark"] if rk else "",
        "rows": rows,
    }

def order_progress(con, order):
    done_t = con.execute("SELECT COALESCE(SUM(tons),0) s FROM sales WHERE order_id=?",
                         (order["id"],)).fetchone()["s"]
    return {"ordered_t": order["tons"], "done_t": done_t,
            "remaining_t": round(float(order["tons"] or 0) - done_t, 3)}

def pending_counts(con, u):
    """Sidebar pending-count badges (Talha's order, 28 Oct 2026): for
    each sidebar section, how many things are waiting for an action
    THERE — keyed by VIEW name, zero counts omitted (no badge at zero).
    Role-aware, mirroring the decide endpoints' own gates:
      alerts     — client payment proofs awaiting confirm/reject
                   (decide perm: payments) + alerts still unsent
                   (send perm: vehicles), each counted only for users
                   holding that perm (owner/manager hold both).
      warehouse  — godam stock adjustments awaiting approval
                   (owner only — /api/stock-adjustments/decide).
      cheques    — pending cheques whose due date has ARRIVED
                   (due_date <= today; future post-dated ones wait).
      expenses   — expenses awaiting owner approval (owner only).
      leaves     — leave requests + overtime / attendance-correction
                   approvals awaiting the owner (owner only; both are
                   decided on the Leaves page).
      cashinhand — handovers awaiting THIS user's own acknowledgement.
    NOT badged, deliberately: open grinding sessions (a live state,
    not a pending decision — the badge would sit lit all day) and
    unread notifications (already the top bell's dot). Client-portal
    logins and the view-only demo get no badges at all."""
    if not u or u.get("role") in ("client", "demo"):
        return {}
    role = u.get("role")
    perms = set(u.get("perms") or [])
    om = role in ("owner", "manager")

    def cnt(sql, args=()):
        return con.execute(sql, args).fetchone()["c"]

    out = {}
    alerts_n = 0
    if om or "payments" in perms:
        alerts_n += cnt("SELECT COUNT(*) c FROM payment_proofs "
                        "WHERE status='pending'")
    if om or "vehicles" in perms:
        alerts_n += cnt("SELECT COUNT(*) c FROM alerts WHERE status='pending'")
    if alerts_n:
        out["alerts"] = alerts_n
    if role == "owner":
        n = cnt("SELECT COUNT(*) c FROM bag_adjustments WHERE status='pending'")
        if n:
            out["warehouse"] = n
        n = cnt("SELECT COUNT(*) c FROM expenses WHERE status='pending'")
        if n:
            out["expenses"] = n
        n = (cnt("SELECT COUNT(*) c FROM leaves WHERE status='pending'")
             + cnt("SELECT COUNT(*) c FROM approvals WHERE status='pending'"))
        if n:
            out["leaves"] = n
    if om or "cashbook" in perms:
        n = cnt("SELECT COUNT(*) c FROM cheques WHERE status='pending' "
                "AND due_date!='' AND due_date<=?", (today(),))
        if n:
            out["cheques"] = n
    n = cnt("SELECT COUNT(*) c FROM cash_handovers WHERE status='pending' "
            "AND holder_key=?", ("user:%d" % int(u.get("id") or 0),))
    if n:
        out["cashinhand"] = n
    return out

# ------------------------------------------------------- alerts / notify ----
WA_TEMPLATES = ["vehicle_in_alert", "vehicle_out_alert", "payment_reminder",
                "owner_weekly_summary", "day_end_summary", "owner_deletion_alert",
                "login_credentials"]

def _http_post_json(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **(headers or {})},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return True, r.read().decode("utf-8", "replace")[:400]
    except urllib.error.HTTPError as e:
        try:
            return False, "HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:300])
        except Exception:
            return False, "HTTP %s" % e.code
    except Exception as e:
        return False, str(e)[:300]

def send_whatsapp_api(con, to, template, params):
    if IS_PC:
        return False, "PC edition: WhatsApp auto-send off hai (wa.me button use karein)"
    pid = meta_get(con, "wa_phone_id")
    token = meta_get(con, "wa_token")
    if not pid or not token:
        return False, "WhatsApp API not configured (Settings mein Phone Number ID + Token dalein)"
    url = "https://graph.facebook.com/v21.0/%s/messages" % pid
    payload = {"messaging_product": "whatsapp", "to": re_clean_phone(to),
               "type": "template",
               "template": {"name": template, "language": {"code": "en"},
                            "components": [{"type": "body", "parameters":
                                            [{"type": "text", "text": str(p)} for p in params]}]}}
    return _http_post_json(url, payload, {"Authorization": "Bearer " + token})

def re_clean_phone(num):
    d = "".join(ch for ch in (num or "") if ch.isdigit())
    if d.startswith("0"):
        d = "92" + d[1:]
    return d

def send_sms(con, to, message):
    if IS_PC:
        return False, "PC edition: SMS auto-send off hai"
    base = meta_get(con, "sms_url")
    if not base:
        return False, "SMS gateway not configured"
    url = (base.replace("{to}", quote(re_clean_phone(to)))
               .replace("{msg}", quote(message))
               .replace("{key}", quote(meta_get(con, "sms_key")))
               .replace("{sender}", quote(meta_get(con, "sms_sender"))))
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return True, r.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return False, str(e)[:300]

def dispatch_alert(con, alert):
    """Try WhatsApp API, then SMS. Returns final status and updates the row."""
    if (alert["channel"] or "") == "email":
        # round 12: email rows in this table are a send LOG, not a
        # WhatsApp queue item — never push them through WhatsApp/SMS
        return alert["status"] or "sent"
    msg = alert["message"]
    to = alert["target"]
    kind = alert["kind"]
    params = []
    try:
        params = json.loads(alert["detail"] or "[]")
        if not isinstance(params, list):
            params = []
    except Exception:
        params = []
    template = {"vehicle_in": "vehicle_in_alert", "vehicle_out": "vehicle_out_alert",
                "payment_reminder": "payment_reminder", "owner_summary": "owner_weekly_summary",
                "day_end": "day_end_summary", "deletion": "owner_deletion_alert"}.get(kind)
    status, detail = "pending", ""
    if template and to:
        ok, detail = send_whatsapp_api(con, to, template, params or [msg])
        if ok:
            status = "sent"
            con.execute("UPDATE alerts SET status='sent', channel='whatsapp_api', detail=? WHERE id=?",
                        (detail, alert["id"]))
            con.commit()
            return status
    if to:
        ok, sdetail = send_sms(con, to, msg)
        if ok:
            con.execute("UPDATE alerts SET status='sent', channel='sms', detail=? WHERE id=?",
                        (sdetail, alert["id"]))
            con.commit()
            return "sent"
        detail = (detail + " | SMS: " + sdetail).strip(" |")
    con.execute("UPDATE alerts SET status='failed', detail=? WHERE id=?",
                (detail or "no channel configured", alert["id"]))
    con.commit()
    return "failed"

def make_alert(con, kind, party_id, target, message, params=None):
    cur = con.execute(
        "INSERT INTO alerts(created,kind,party_id,target,message,detail) VALUES(?,?,?,?,?,?)",
        (now_str(), kind, party_id, target or "", message, json.dumps(params or [])))
    con.commit()
    row = con.execute("SELECT * FROM alerts WHERE id=?", (cur.lastrowid,)).fetchone()
    if target:
        try:
            dispatch_alert(con, row)
        except Exception:
            pass
    return cur.lastrowid

# ------------------------------------------------------------- email ------
# Round 12 (Talha, 29 Oct 2026): email integration — SMTP settings,
# login by email, password reset by email, and email copies of the
# notifications WhatsApp already carries. Every send is best-effort:
# a dead SMTP server is logged (alerts table, channel 'email', plus
# the audit log) and NEVER blocks or breaks the business save that
# triggered it. Transport is plain smtplib — portable on purpose: the
# same code works on the hosted build and on the PC edition, no
# hosted-only email API. NOTE (live-verification item): PythonAnywhere
# free-plan outbound rules may restrict SMTP from the hosted account;
# the Settings "Send test email" button is the live check after deploy.
import smtplib as _smtplib
import ssl as _sslmod
from email.message import EmailMessage as _EmailMessage
from email.utils import formataddr as _formataddr

def _valid_email(v):
    v = (v or "").strip()
    if not v or " " in v or v.count("@") != 1:
        return False
    local, dom = v.split("@")
    return bool(local) and "." in dom and not dom.startswith(".") \
        and not dom.endswith(".")

def mail_settings(con):
    """SMTP + notification settings (meta table). smtp_pass rides
    along for the sender only — the settings API masks it."""
    try:
        port = int(meta_get(con, "smtp_port", "587") or 587)
    except (TypeError, ValueError):
        port = 587
    sec = meta_get(con, "smtp_security", "starttls") or "starttls"
    if sec not in ("starttls", "ssl", "none"):
        sec = "starttls"
    # round 15: the Email-service preset label the owner last picked
    # in Settings (a filler for host/port/security + mini-guide key,
    # never a lock — the stored smtp_* values are what sending uses).
    preset = meta_get(con, "mail_preset", "custom") or "custom"
    if preset not in ("custom", "gmail", "brevo", "smtp2go",
                      "hostinger", "outlook"):
        preset = "custom"
    return {"mail_preset": preset,
            "smtp_host": meta_get(con, "smtp_host", ""),
            "smtp_port": port, "smtp_security": sec,
            "smtp_user": meta_get(con, "smtp_user", ""),
            "smtp_pass": meta_get(con, "smtp_pass", ""),
            "smtp_from_name": meta_get(con, "smtp_from_name", ""),
            "smtp_from_email": meta_get(con, "smtp_from_email", ""),
            "mail_enabled": meta_get(con, "mail_enabled", "0") == "1",
            "mail_ev_proof": meta_get(con, "mail_ev_proof", "1") == "1",
            "mail_ev_payment": meta_get(con, "mail_ev_payment", "1") == "1",
            "mail_ev_voucher": meta_get(con, "mail_ev_voucher", "0") == "1",
            "mail_ev_dayend": meta_get(con, "mail_ev_dayend", "0") == "1",
            "system_address": (meta_get(con, "system_address", "") or "").rstrip("/")}

def mail_configured(con):
    ms = mail_settings(con)
    return bool(ms["smtp_host"] and ms["smtp_user"])

def mail_public_settings(con):
    """The settings-API view: the SMTP password is NEVER echoed back
    in full — only whether it is set, plus a masked hint (the same
    pattern as the WhatsApp token)."""
    ms = mail_settings(con)
    pw = ms["smtp_pass"]
    return {"mail_preset": ms["mail_preset"],
            "smtp_host": ms["smtp_host"], "smtp_port": ms["smtp_port"],
            "smtp_security": ms["smtp_security"], "smtp_user": ms["smtp_user"],
            "smtp_pass_set": bool(pw),
            "smtp_pass_hint": ("••••" + pw[-4:]) if pw else "",
            "smtp_from_name": ms["smtp_from_name"],
            "smtp_from_email": ms["smtp_from_email"],
            "mail_enabled": 1 if ms["mail_enabled"] else 0,
            "mail_ev_proof": 1 if ms["mail_ev_proof"] else 0,
            "mail_ev_payment": 1 if ms["mail_ev_payment"] else 0,
            "mail_ev_voucher": 1 if ms["mail_ev_voucher"] else 0,
            "mail_ev_dayend": 1 if ms["mail_ev_dayend"] else 0,
            "system_address": ms["system_address"],
            "mail_configured": mail_configured(con)}

def _email_html(mill, text_body):
    """Simple HTML twin of a plain-text email body: mill band on top,
    the text in a pre-wrap block (numbers/tables keep their shape)."""
    return ("<div style='font-family:Arial,sans-serif;max-width:640px;margin:auto'>"
            "<div style='background:#0c7a4e;color:#fff;padding:10px 14px;"
            "border-radius:6px 6px 0 0'><b>%s</b></div>"
            "<div style='border:1px solid #ddd;border-top:none;padding:14px'>"
            "<pre style='font-family:inherit;white-space:pre-wrap;margin:0;"
            "font-size:14px;line-height:1.6'>%s</pre></div></div>"
            % (htmlesc(mill), htmlesc(text_body or "")))

def send_email(con, to, subject, text_body, html_body=None):
    """One best-effort SMTP send. Returns (ok, detail); never raises.
    Supports STARTTLS (587), implicit SSL (465) and plain SMTP."""
    to = (to or "").strip()
    if not _valid_email(to):
        return False, "recipient email missing/invalid"
    ms = mail_settings(con)
    if not ms["smtp_host"] or not ms["smtp_user"]:
        return False, ("Email is not set up yet (Settings -> Email: "
                       "SMTP host + username dalein)")
    from_email = ms["smtp_from_email"] or ms["smtp_user"]
    from_name = ms["smtp_from_name"] or meta_get(con, "mill_name", APP_NAME)
    msg = _EmailMessage()
    msg["From"] = _formataddr((from_name, from_email))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body or "")
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    try:
        if ms["smtp_security"] == "ssl":
            ctx = _sslmod.create_default_context()
            with _smtplib.SMTP_SSL(ms["smtp_host"], ms["smtp_port"],
                                   timeout=20, context=ctx) as s:
                if ms["smtp_user"]:
                    s.login(ms["smtp_user"], ms["smtp_pass"])
                s.send_message(msg)
        else:
            with _smtplib.SMTP(ms["smtp_host"], ms["smtp_port"], timeout=20) as s:
                s.ehlo()
                if ms["smtp_security"] == "starttls":
                    s.starttls(context=_sslmod.create_default_context())
                    s.ehlo()
                if ms["smtp_user"]:
                    s.login(ms["smtp_user"], ms["smtp_pass"])
                s.send_message(msg)
    except Exception as e:
        return False, str(e)[:300]
    return True, "sent to " + to

def log_email(con, kind, party_id, to, subject, ok, detail):
    """Every email attempt lands in the alerts table (channel
    'email') so the Alerts page shows email sends beside the WhatsApp
    ones, with their real status. These rows are a LOG — the
    dispatcher never pushes them through WhatsApp/SMS."""
    try:
        con.execute(
            "INSERT INTO alerts(created,kind,party_id,target,channel,status,message,detail)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (now_str(), kind, party_id, to or "", "email",
             "sent" if ok else "failed", subject or "", (detail or "")[:300]))
        con.commit()
    except Exception:
        pass

def email_notify(con, event_key, kind, party_id, to, subject, text_body,
                 html_body=None):
    """Notification-email policy wrapper: master switch + the
    per-event toggle must both be on. A skipped send (switch off / no
    address / not configured) simply does not happen and is not
    logged as a failure; a real SMTP failure is logged + audited."""
    ms = mail_settings(con)
    if not ms["mail_enabled"] or not ms.get(event_key):
        return False, "email notifications off"
    if not mail_configured(con):
        return False, "email not configured"
    ok, detail = send_email(con, to, subject, text_body, html_body)
    log_email(con, kind, party_id, to, subject, ok, detail)
    if not ok:
        try:
            audit(con, "system", "email_failed",
                  "%s to %s: %s" % (kind, to, detail))
            con.commit()
        except Exception:
            pass
    return ok, detail

def owner_email_addr(con):
    """The first owner login (by creation) that carries an email."""
    r = con.execute("SELECT email FROM users WHERE role='owner' AND email<>''"
                    " ORDER BY id LIMIT 1").fetchone()
    return (r["email"] if r else "") or ""

def owner_lang(con):
    r = con.execute("SELECT lang FROM users WHERE role='owner' AND email<>''"
                    " ORDER BY id LIMIT 1").fetchone()
    lg = (r["lang"] if r else "") or "en"
    return lg if lg in ("en", "ur", "hi") else "en"

def party_email_addr(con, party_id):
    """Where a party's statements/receipts go: the party's own email
    field first, then its client login's email."""
    if not party_id:
        return ""
    p = con.execute("SELECT email FROM parties WHERE id=?",
                    (party_id,)).fetchone()
    if p and (p["email"] or "").strip():
        return p["email"].strip()
    u = con.execute("SELECT email FROM users WHERE party_id=? AND role='client'"
                    " AND email<>'' ORDER BY id LIMIT 1", (party_id,)).fetchone()
    return (u["email"] if u else "") or ""

def party_lang(con, party_id, default="ur"):
    """Recipient-facing language for party emails: the party's client
    login language when one exists (the WhatsApp reminder composer
    defaults to Urdu for the same customers)."""
    u = con.execute("SELECT lang FROM users WHERE party_id=? AND role='client'"
                    " ORDER BY id LIMIT 1", (party_id,)).fetchone()
    lg = (u["lang"] if u else "") or default
    return lg if lg in ("en", "ur", "hi") else default

def _user_email_error(con, email, exclude_id=None):
    """Round 12: a login's email must be well-formed and UNIQUE across
    logins — login-by-email and reset-by-email both depend on one
    email pointing at exactly one account. '' = acceptable."""
    email = (email or "").strip()
    if not email:
        return ""
    if not _valid_email(email):
        return "email address theek likhein"
    sql = "SELECT id FROM users WHERE email<>'' AND LOWER(email)=LOWER(?)"
    args = [email]
    if exclude_id:
        sql += " AND id<>?"
        args.append(int(exclude_id))
    if con.execute(sql, args).fetchone():
        return ("ye email pehle se ek login par hai — har login ka email "
                "alag hona chahiye (password reset isi se hota hai)")
    return ""

def _sync_party_user_email(con, party_id, email, from_user):
    """Keep a party and its client login reachable at ONE address:
    whichever side gains an email first fills the OTHER side's empty
    field (the WhatsApp 'Same as Phone' convenience, at the data
    level). A value already set on the other side is never
    overwritten, and party_email_addr() prefers the party's own
    field, so the two can still differ deliberately."""
    email = (email or "").strip()
    if not party_id or not email:
        return
    if from_user:
        con.execute("UPDATE parties SET email=? WHERE id=? AND "
                    "(email IS NULL OR email='')", (email, party_id))
    else:
        con.execute("UPDATE users SET email=? WHERE party_id=? AND "
                    "role='client' AND (email IS NULL OR email='')",
                    (email, party_id))

def system_base_url(con, handler=None):
    """Base for emailed links: the owner's 'System address' setting
    when set; otherwise the address this very request arrived on
    (hosted build = its public HTTPS host; PC build = its LAN
    address, which is exactly where a LAN reset link can work)."""
    addr = mail_settings(con)["system_address"]
    if addr:
        return addr
    host = ""
    if handler is not None:
        host = handler.headers.get("Host") or ""
    if not host:
        host = "%s:%d" % (lan_ip(), MAIN_PORT[0])
    return "%s://%s" % ("http" if IS_PC else "https", host)

# Email subjects/bodies per recipient language. Subjects always carry
# the mill name (appended by the composers where the template does
# not already include it).
MAIL_TXT = {
 "en": {
  "pay_subj": "Payment received — Rs {amt}",
  "pay_body": ("Assalamu alaikum {party},\n\nWe have received your payment of "
               "Rs {amt} ({method}) on {date}.\nYour remaining balance is "
               "Rs {bal} ({dir}).\n\nThank you,\n{mill}"),
  "proof_subj": "Client payment proof received — {party} Rs {amt}",
  "proof_body": ("Client {party} has submitted a payment proof of Rs {amt} "
                 "(date {date}).\nIt is pending on the Alerts page — confirm "
                 "it there to post the payment."),
  "stmt_subj": "Your khata statement — {party}",
  "inv_subj": "Invoice {inv} — Rs {amt}",
  "inv_body": ("Invoice {inv}\nDate: {date}\nBuyer: {party}\nItem: {item}\n"
               "Weight: {wt}\nBags: {bags}\nRate: Rs {rate}\n"
               "Total: Rs {amt}\n\n{mill}"),
  "reset_subj": "Password reset — {mill}",
  "reset_body": ("Assalamu alaikum {name},\n\nA password reset was requested "
                 "for your {mill} login.\nOpen this link within 60 minutes "
                 "to set a new password:\n\n{link}\n\nIf you did not request "
                 "this, ignore this email — your password stays unchanged."),
  "dayend_subj": "Day-End Summary {date} — {mill}",
  "test_subj": "Test email — {mill}",
  "test_body": ("This is a test email from {mill}.\n"
                "Your email settings are working."),
  "cred_subj": "Your {mill} login",
  "cred_body": ("Assalamu alaikum {name},\n\nYour {mill} login is ready.\n"
                "Username: {user}\nPassword: {pw}\nLogin page: {link}\n\n"
                "For safety, change this password after your first login — "
                "use 'Forgot password?' on the login page, or ask the owner.\n\n{mill}"),
  "to_receive": "to receive", "to_pay": "to pay", "clear": "clear"},
 "ur": {
  "pay_subj": "ادائیگی موصول — Rs {amt}",
  "pay_body": ("السلام علیکم {party}،\n\nآپ کی Rs {amt} کی ادائیگی ({method}) "
               "مورخہ {date} کو موصول ہو گئی ہے۔\nآپ کا باقی بیلنس Rs {bal} "
               "ہے ({dir})۔\n\nشکریہ،\n{mill}"),
  "proof_subj": "کلائنٹ ادائیگی ثبوت موصول — {party} Rs {amt}",
  "proof_body": ("کلائنٹ {party} نے Rs {amt} کی ادائیگی کا ثبوت بھیجا ہے "
                 "(تاریخ {date})۔\nیہ الرٹس صفحے پر زیر التوا ہے — ادائیگی "
                 "درج کرنے کے لیے وہاں تصدیق کریں۔"),
  "stmt_subj": "آپ کے کھاتے کی تفصیل — {party}",
  "inv_subj": "انوائس {inv} — Rs {amt}",
  "inv_body": ("انوائس {inv}\nتاریخ: {date}\nخریدار: {party}\nشے: {item}\n"
               "وزن: {wt}\nتھیلے: {bags}\nریٹ: Rs {rate}\nکل: Rs {amt}\n\n{mill}"),
  "reset_subj": "پاس ورڈ ری سیٹ — {mill}",
  "reset_body": ("السلام علیکم {name}،\n\nآپ کے {mill} لاگ ان کے لیے پاس ورڈ "
                 "ری سیٹ کی درخواست آئی ہے۔\nنیا پاس ورڈ لگانے کے لیے 60 منٹ "
                 "کے اندر یہ لنک کھولیں:\n\n{link}\n\nاگر آپ نے یہ درخواست "
                 "نہیں کی تو اس ای میل کو نظر انداز کر دیں — آپ کا پاس ورڈ "
                 "تبدیل نہیں ہوگا۔"),
  "dayend_subj": "دن اختتام خلاصہ {date} — {mill}",
  "test_subj": "ٹیسٹ ای میل — {mill}",
  "test_body": "یہ {mill} کی طرف سے ٹیسٹ ای میل ہے۔\nآپ کی ای میل ترتیبات درست کام کر رہی ہیں۔",
  "cred_subj": "آپ کا {mill} لاگ ان",
  "cred_body": ("السلام علیکم {name}،\n\nآپ کا {mill} لاگ ان تیار ہے۔\n"
                "صارف نام: {user}\nپاس ورڈ: {pw}\nلاگ ان صفحہ: {link}\n\n"
                "حفاظت کے لیے پہلے لاگ ان کے بعد یہ پاس ورڈ بدل لیں — لاگ ان "
                "صفحے پر 'پاس ورڈ بھول گئے؟' استعمال کریں یا مالک سے کہیں۔\n\n{mill}"),
  "to_receive": "لینے ہیں", "to_pay": "دینے ہیں", "clear": "حساب صاف"},
 "hi": {
  "pay_subj": "भुगतान प्राप्त — Rs {amt}",
  "pay_body": ("नमस्ते {party},\n\nआपका Rs {amt} का भुगतान ({method}) दिनांक "
               "{date} को प्राप्त हो गया है।\nआपका शेष बैलेंस Rs {bal} है "
               "({dir})।\n\nधन्यवाद,\n{mill}"),
  "proof_subj": "ग्राहक भुगतान प्रमाण प्राप्त — {party} Rs {amt}",
  "proof_body": ("ग्राहक {party} ने Rs {amt} के भुगतान का प्रमाण भेजा है "
                 "(तिथि {date})।\nयह अलर्ट पृष्ठ पर लंबित है — भुगतान दर्ज "
                 "करने के लिए वहाँ पुष्टि करें।"),
  "stmt_subj": "आपके खाते का विवरण — {party}",
  "inv_subj": "इनवॉइस {inv} — Rs {amt}",
  "inv_body": ("इनवॉइस {inv}\nतिथि: {date}\nख़रीदार: {party}\nवस्तु: {item}\n"
               "वज़न: {wt}\nबोरे: {bags}\nदर: Rs {rate}\nकुल: Rs {amt}\n\n{mill}"),
  "reset_subj": "पासवर्ड रीसेट — {mill}",
  "reset_body": ("नमस्ते {name},\n\nआपके {mill} लॉगिन के लिए पासवर्ड रीसेट "
                 "का अनुरोध आया है।\nनया पासवर्ड लगाने के लिए 60 मिनट के "
                 "अंदर यह लिंक खोलें:\n\n{link}\n\nयदि आपने यह अनुरोध नहीं "
                 "किया है तो इस ईमेल को अनदेखा करें — आपका पासवर्ड नहीं "
                 "बदलेगा।"),
  "dayend_subj": "दिन अंत सारांश {date} — {mill}",
  "test_subj": "टेस्ट ईमेल — {mill}",
  "test_body": "यह {mill} की ओर से टेस्ट ईमेल है।\nआपकी ईमेल सेटिंग्स सही काम कर रही हैं।",
  "cred_subj": "आपका {mill} लॉगिन",
  "cred_body": ("नमस्ते {name},\n\nआपका {mill} लॉगिन तैयार है।\n"
                "उपयोगकर्ता नाम: {user}\nपासवर्ड: {pw}\nलॉगिन पृष्ठ: {link}\n\n"
                "सुरक्षा के लिए पहले लॉगिन के बाद यह पासवर्ड बदल लें — लॉगिन "
                "पृष्ठ पर 'पासवर्ड भूल गए?' उपयोग करें या मालिक से कहें।\n\n{mill}"),
  "to_receive": "लेने हैं", "to_pay": "देने हैं", "clear": "हिसाब साफ़"},
}

def _party_avatar_map(con):
    """Round 12: party_id -> linked client login's avatar info, so
    owner-side party/proof rows can show the client's picture (or the
    initial-letter fallback) next to their name."""
    out = {}
    for r in con.execute("SELECT id, party_id, avatar_ver, "
                         "CASE WHEN avatar_b64<>'' THEN 1 ELSE 0 END has_avatar "
                         "FROM users WHERE role='client' AND party_id IS NOT NULL"):
        out[r["party_id"]] = {"cuid": r["id"], "cavatar": bool(r["has_avatar"]),
                              "caver": r["avatar_ver"] or 0}
    return out


def deliver_credentials(con, handler, user_rec, password):
    """Round 12: when the owner creates a login or sets a NEW password,
    send the new user their username + the JUST-SET password + the login
    link on WhatsApp and email where available (client-portal logins
    fall back to the party's WhatsApp/email). Best-effort: never raises,
    never blocks the save, and the password is NEVER stored — the log
    rows carry only the delivery outcome. Returns a per-channel result
    dict for the owner's result line."""
    out = {"whatsapp": {"sent": False, "detail": "not tried"},
           "email": {"sent": False, "detail": "not tried"}}
    try:
        uname = user_rec["username"]
        pid = user_rec["party_id"] or None
        mill = meta_get(con, "mill_name", APP_NAME)
        link = system_base_url(con, handler)
        wa_num, disp = "", uname
        # the login's own profile phone/WhatsApp wins; client logins
        # fall back to their party's number (brief's party-side rule)
        try:
            wa_num = (user_rec["phone"] or "").strip()
        except Exception:
            wa_num = ""
        if pid:
            prow = con.execute("SELECT name, phone, whatsapp FROM parties WHERE id=?",
                               (pid,)).fetchone()
            if prow:
                disp = prow["name"] or uname
                if not wa_num:
                    wa_num = (prow["whatsapp"] or prow["phone"] or "").strip()
        # ---- WhatsApp leg (approved template, like every other auto-send)
        if not wa_num:
            out["whatsapp"] = {"sent": False, "detail": "is login ka WhatsApp number nahi hai"}
        else:
            ok, detail = send_whatsapp_api(con, wa_num, "login_credentials",
                                            [mill, uname, password, link])
            ch = "whatsapp_api"
            if not ok:
                lang = party_lang(con, pid) if pid else "en"
                T = MAIL_TXT.get(lang) or MAIL_TXT["en"]
                text = T["cred_body"].format(name=disp, mill=mill, user=uname,
                                             pw=password, link=link)
                ok2, d2 = send_sms(con, wa_num, text)
                if ok2:
                    ok, detail, ch = True, d2, "sms"
                elif detail:
                    detail = detail + " | SMS: " + d2
                else:
                    detail = d2
            try:
                con.execute("INSERT INTO alerts(created,kind,party_id,target,channel,status,message,detail)"
                            " VALUES(?,?,?,?,?,?,?,?)",
                            (now_str(), "credentials", pid, wa_num,
                             ch if ok else "whatsapp_api", "sent" if ok else "failed",
                             "Login credentials for " + uname, (detail or "")[:300]))
                con.commit()
            except Exception:
                pass
            out["whatsapp"] = {"sent": bool(ok), "detail": "sent" if ok else (detail or "failed")}
        # ---- Email leg (functional send like reset/test: not toggle-gated)
        to = (user_rec["email"] or "").strip() or (party_email_addr(con, pid) if pid else "")
        if not to:
            out["email"] = {"sent": False, "detail": "is login par email nahi hai"}
        elif not mail_configured(con):
            out["email"] = {"sent": False, "detail": "Email (SMTP) set up nahi hai"}
            log_email(con, "email_credentials", pid, to, "Login credentials — " + mill,
                      False, "SMTP not configured")
        else:
            lang = party_lang(con, pid) if pid else "en"
            T = MAIL_TXT.get(lang) or MAIL_TXT["en"]
            subj = T["cred_subj"].format(mill=mill)
            body = T["cred_body"].format(name=disp, mill=mill, user=uname,
                                         pw=password, link=link)
            ok, detail = send_email(con, to, subj, body, _email_html(mill, body))
            log_email(con, "email_credentials", pid, to, subj, ok, detail)
            out["email"] = {"sent": bool(ok), "detail": "sent" if ok else (detail or "failed")}
    except Exception as e:
        for k in out:
            if out[k]["detail"] == "not tried":
                out[k] = {"sent": False, "detail": str(e)[:120]}
    return out


def email_payment_to_party(con, party_id, amount, method, date_str):
    """Payment received -> email the party (proof confirmation and a
    manual payment share this one door). Best-effort; never raises."""
    try:
        to = party_email_addr(con, party_id)
        if not to:
            return
        prow = con.execute("SELECT name FROM parties WHERE id=?",
                           (party_id,)).fetchone()
        lang = party_lang(con, party_id)
        T = MAIL_TXT.get(lang) or MAIL_TXT["en"]
        _e, bal = party_ledger(con, party_id)
        dir_word = T["to_receive"] if bal > 0 else \
            T["to_pay"] if bal < 0 else T["clear"]
        mill = meta_get(con, "mill_name", APP_NAME)
        subj = T["pay_subj"].format(amt=format(amount, ",.0f")) + " — " + mill
        body = T["pay_body"].format(
            party=prow["name"] if prow else "", amt=format(amount, ",.0f"),
            method=method or "cash", date=date_str,
            bal=format(abs(bal), ",.0f"), dir=dir_word, mill=mill)
        email_notify(con, "mail_ev_payment", "email_payment", party_id, to,
                     subj, body, _email_html(mill, body))
    except Exception:
        pass

def email_proof_to_owner(con, party_id, amount, date_str):
    """Client payment proof submitted -> email the owner (the bell
    notification's email twin). Best-effort; never raises."""
    try:
        to = owner_email_addr(con)
        if not to:
            return
        prow = con.execute("SELECT name FROM parties WHERE id=?",
                           (party_id,)).fetchone()
        T = MAIL_TXT.get(owner_lang(con)) or MAIL_TXT["en"]
        mill = meta_get(con, "mill_name", APP_NAME)
        subj = T["proof_subj"].format(party=prow["name"] if prow else "",
                                      amt=format(amount, ",.0f")) + " — " + mill
        body = T["proof_body"].format(party=prow["name"] if prow else "",
                                      amt=format(amount, ",.0f"), date=date_str)
        email_notify(con, "mail_ev_proof", "email_proof", party_id, to,
                     subj, body, _email_html(mill, body))
    except Exception:
        pass

def dayend_email_text(con, de):
    """The Day-End figures as plain email lines (same figures the
    Day-End page shows; English labels, as on the printed registers)."""
    cb = de.get("cashbook") or {}
    return "\n".join([
        "Day-End Summary — %s" % de.get("date", ""),
        "Vehicles: %s (IN %s rock · OUT %s powder)"
        % (de.get("trips", 0), fmt_weight((de.get("rock_in_t") or 0) * 1000.0, "t"),
           fmt_weight((de.get("powder_out_t") or 0) * 1000.0, "t")),
        "Ground: %s · Bags packed: %s"
        % (fmt_weight((de.get("ground_t") or 0) * 1000.0, "t"), de.get("bags", 0)),
        "Grinding earned: Rs %s" % format(de.get("grinding_earned") or 0, ",.0f"),
        "Payments in / out: Rs %s / Rs %s"
        % (format(de.get("payments_in") or 0, ",.0f"),
           format(de.get("payments_out") or 0, ",.0f")),
        "Cash net: Rs %s" % format(cb.get("total") or 0, ",.0f"),
        "Expenses: Rs %s" % format(de.get("expense_total") or 0, ",.0f"),
    ])

def maybe_email_dayend(con, de):
    """Day-End page hook (toggle mail_ev_dayend, default OFF): email
    today's summary to the owner — once per day on success; a failed
    send may retry on a later view, at most every 30 minutes.
    Best-effort: never raises, never blocks the page."""
    try:
        ms = mail_settings(con)
        if not ms["mail_enabled"] or not ms["mail_ev_dayend"]:
            return
        if not mail_configured(con):
            return
        to = owner_email_addr(con)
        if not to:
            return
        td = today()
        if meta_get(con, "mail_dayend_sent", "") == td:
            return
        try:
            last_try = float(meta_get(con, "mail_dayend_try", "0") or 0)
        except (TypeError, ValueError):
            last_try = 0
        if now_ts() - last_try < 1800:
            return
        meta_set(con, "mail_dayend_try", str(now_ts()))
        con.commit()
        mill = meta_get(con, "mill_name", APP_NAME)
        T = MAIL_TXT.get(owner_lang(con)) or MAIL_TXT["en"]
        subj = T["dayend_subj"].format(date=td, mill=mill)
        text = dayend_email_text(con, de)
        ok, detail = send_email(con, to, subj, text, _email_html(mill, text))
        log_email(con, "email_dayend", None, to, subj, ok, detail)
        if ok:
            meta_set(con, "mail_dayend_sent", td)
            con.commit()
    except Exception:
        pass

# ------------------------------------------------------------- assistant ----
# AI Assistant v2: rule-based over the mill's OWN records only (numbers are
# never invented). Understands Roman Urdu, Urdu script, English, Hindi and
# mixtures: the query is normalised (Urdu/Arabic letter variants unified,
# diacritics stripped) and matched against generous keyword sets per intent.
# The reply is given in the same language/script the question was asked in.
_URDU_FIX = {"ي": "ی", "ك": "ک", "ة": "ہ", "ه": "ہ", "ھ": "ہ", "ؤ": "و",
             "ئ": "ی", "أ": "ا", "إ": "ا", "ٱ": "ا", "آ": "ا"}
_URDU_STRIP = set(range(0x064B, 0x0653)) | {0x0670, 0x0640}

def _norm_urdu(s):
    out = []
    for ch in s or "":
        if ord(ch) in _URDU_STRIP:
            continue
        out.append(_URDU_FIX.get(ch, ch))
    return "".join(out)

def _has_ar(s):
    return any("\u0600" <= ch <= "\u06FF" for ch in s or "")

def _has_dev(s):
    return any("\u0900" <= ch <= "\u097F" for ch in s or "")

_ASST = {
    "en": {"profit_month": "Profit for {month}: income Rs {income:,.0f} (grinding Rs {gi:,.0f} + sales Rs {si:,.0f}), costs Rs {costs:,.0f}, profit Rs {profit:,.0f}.",
           "profit_today": "Today's profit so far: income Rs {income:,.0f} (grinding Rs {gi:,.0f} + sales Rs {si:,.0f}), costs Rs {costs:,.0f}, profit Rs {profit:,.0f}.",
           "stock": "Stock position — Own rock: bought {rb:g} t, ground {g:g} t, left {rl:g} t. Own powder: made {pm:g} t, sold {s:g} t, left {pl:g} t. Godam: own bags ready {ob}, bardana (empty bags) left {bd}.",
           "vehicles": "Today: {ti} vehicles IN ({rit:g} t rock), {to} vehicles OUT ({pot:g} t powder).",
           "production": "Today's production: {bags} bags packed, {gt:g} t ground.",
           "cash": "Today cash: IN Rs {tin:,.0f}, OUT Rs {tout:,.0f}, net Rs {net:,.0f}.",
           "dues": "Total worker dues: Rs {due:,.0f}.{lst}",
           "theka": " Theka workers have earned Rs {earned:,.0f} in total so far.",
           "unknown": "I answer only from your mill records — I never make up numbers. Try asking, for example:\n• How many vehicles came today?\n• What is the stock position?\n• <party name> balance?\n• This month's profit?\n• Today's expenses?\n• Worker dues?\n• Pending orders?",
           "debtors": "Parties who owe us: {lst}. Total to receive: Rs {tot:,.0f}.",
           "debtors_none": "No party owes us anything right now. Total to receive: Rs 0.",
           "payables": "Parties we owe: {lst}. Total to pay: Rs {tot:,.0f}.",
           "payables_none": "We do not owe any party right now. Total to pay: Rs 0.",
           "biggest": "Biggest balance: {name} owes us Rs {bal:,.0f}.",
           "biggest_none": "No party owes us anything right now.",
           "balance": "{name}: balance Rs {bal:,.0f} ({who}). Rock waiting {rw:g} t, powder ready {pr:g} t ({bags} bags).",
           "owes_us": "party owes us", "we_owe": "we owe the party", "clear": "clear",
           "expenses_today": "Today's expenses (ledger): Rs {amt:,.0f}.",
           "expenses_month": "Total expenses this month ({month}): Rs {amt:,.0f}.",
           "orders": "Pending powder orders:\n{lst}",
           "orders_none": "No powder orders are pending.",
           "order_line": "• {party}: {rem:g} t remaining (of {tot:g} t @ Rs {rate:,.0f})",
           "worker_line": "\n• {name}: Rs {due:,.0f} due",
           "party_line": "{name} Rs {bal:,.0f}",
           "summary": "Day summary ({date}): {ti} vehicles IN ({rit:g} t rock), {to} OUT ({pot:g} t powder), ground {gt:g} t, {bags} bags packed. Cash IN Rs {tin:,.0f}, OUT Rs {tout:,.0f}. Expenses Rs {exp:,.0f}.",
           "pay_in_head": "Payments received ({range}) — total Rs {tot:,.0f}:\n{lst}",
           "pay_out_head": "Payments made ({range}) — total Rs {tot:,.0f}:\n{lst}",
           "pay_in_none": "No payments were received ({range}).",
           "pay_out_none": "No payments were made ({range}).",
           "pay_line": "• {name}: Rs {amt:,.0f} ({method})",
           "pay_pin_head": "Payments from {name} ({range}) — total Rs {tot:,.0f}:\n{lst}",
           "pay_pout_head": "Payments to {name} ({range}) — total Rs {tot:,.0f}:\n{lst}",
           "worker_one": "{name} ({kind}): earned Rs {earned:,.0f}, paid Rs {paid:,.0f}, due Rs {due:,.0f}.",
           "exp_head": "{head} expenses ({range}): Rs {amt:,.0f}.",
           "prod_split": " Day shift {bd} bags, night shift {bn} bags.",
           "prod_party": "{name}: ground {gt:g} t, {bags} bags produced (avg grade {gr:g}%).",
           "veh_party": "{name}: {ti} vehicles IN ({rit:g} t rock), {to} OUT ({pot:g} t powder) today.",
           "filter_s": "Filter powder in godam (the mill's own stock — it comes out of clients' grinding but is never theirs): {kg:,.0f} kg.",
           "grind_range": "Grinding earned ({range}): Rs {amt:,.0f}.",
           "cih_h": "Cash in hand — total Rs {tot:,.0f}:\n{lst}",
           "cih_line": "• {name}: Rs {amt:,.0f}",
           "cih_none": "No cash is recorded in anyone's hand.",
           "trade_tot": "{range}: purchases Rs {pu:,.0f}, sales Rs {sa:,.0f}.",
           "direct_t": "Direct trades ({range}): {n} deals — bought Rs {buy:,.0f}, sold Rs {sell:,.0f}, profit Rs {profit:,.0f}.",
           "og_factory": "{name} (outside mill): rock sent {sent:g} t, ground {used:g} t, powder {pbags:g} bags ({pt:g} t), wastage {wt:g} t ({wp:g}%), rock still there {rem:g} t, powder left {plb:g} bags, sold {sb:g} bags (Rs {sa:,.0f}), grinding charges Rs {ch:,.0f} (our payable), balance Rs {bal:,.0f} ({who}).",
           "og_total": "All outside mills: rock sent {sent:g} t, still lying there {rem:g} t, powder left {plb:g} bags ({plt:g} t), wastage {wt:g} t, sold Rs {sa:,.0f}, grinding charges Rs {ch:,.0f}.",
           "og_none": "No outside grinding is recorded yet.",
           "cheques_h": "Pending cheques: {n} — total Rs {tot:,.0f}:\n{lst}",
           "cheque_line": "• {name}: Rs {amt:,.0f} — {no} ({bank}), due {due}",
           "cheques_none": "No cheques are pending.",
           "daycost": "{date} day costs: diesel {dl:g} litres, electricity {eu:g} units.",
           "daycost_none": "No day-cost readings are recorded for {date}.",
           "cpt_t": "Cost per ton this month: expenses Rs {exp:,.0f} over {tons:g} t ground = Rs {ept:,.0f}/ton; grinding income Rs {ipt:,.0f}/ton; margin Rs {mpt:,.0f}/ton.",
           "cpt_none": "No grinding this month yet, so no cost per ton.",
           "backup_s": "Last backup: {when}.",
           "backup_none": "No backup has been taken yet — use the Backup button in Settings."},
    "roman": {"profit_month": "Is mahine ({month}) ka munafa: aamdani Rs {income:,.0f} (pisai Rs {gi:,.0f} + farokht Rs {si:,.0f}), kharche Rs {costs:,.0f}, munafa Rs {profit:,.0f}.",
           "profit_today": "Aaj ka munafa ab tak: aamdani Rs {income:,.0f} (pisai Rs {gi:,.0f} + farokht Rs {si:,.0f}), kharche Rs {costs:,.0f}, munafa Rs {profit:,.0f}.",
           "stock": "Stock ki position — Apna pathar: khareeda {rb:g} t, pisa {g:g} t, baqi {rl:g} t. Apna powder: bana {pm:g} t, bika {s:g} t, baqi {pl:g} t. Godam: apne bag tayyar {ob}, bardana (khali bag) baqi {bd}.",
           "vehicles": "Aaj: {ti} gariyan andar aayin ({rit:g} t pathar), {to} gariyan bahar gayin ({pot:g} t powder).",
           "production": "Aaj ki production: {bags} bag bane, {gt:g} t pisai hui.",
           "cash": "Aaj ka cash: aaya Rs {tin:,.0f}, gaya Rs {tout:,.0f}, net Rs {net:,.0f}.",
           "dues": "Mazdooron ka kul baqaya: Rs {due:,.0f}.{lst}",
           "theka": " Theka mazdooron ki kul kamai ab tak Rs {earned:,.0f} hai.",
           "unknown": "Mein sirf aap ke mill record se jawab deta hoon — number khud nahi banata. Masalan is tarah poochhein:\n• Aaj kitni gariyan aayin?\n• Stock kitna hai?\n• <party ka naam> ka baqaya kitna hai?\n• Is mahine ka munafa?\n• Aaj ka kharcha?\n• Mazdooron ke due kitne hain?\n• Pending orders kon se hain?",
           "debtors": "Jin partiyon ne dene hain: {lst}. Kul lena hai: Rs {tot:,.0f}.",
           "debtors_none": "Is waqt kisi party ne kuch nahi dena. Kul lena hai: Rs 0.",
           "payables": "Jin partiyon ko hum ne dene hain: {lst}. Kul dena hai: Rs {tot:,.0f}.",
           "payables_none": "Is waqt hum ne kisi party ko kuch nahi dena. Kul dena hai: Rs 0.",
           "biggest": "Sab se zyada baqaya: {name} ne Rs {bal:,.0f} dene hain.",
           "biggest_none": "Is waqt kisi party ne kuch nahi dena.",
           "balance": "{name}: baqaya Rs {bal:,.0f} ({who}). Pathar intezaar mein {rw:g} t, powder tayyar {pr:g} t ({bags} bag).",
           "owes_us": "party ne dene hain", "we_owe": "hum ne dene hain", "clear": "khata saaf hai",
           "expenses_today": "Aaj ka kharcha (ledger): Rs {amt:,.0f}.",
           "expenses_month": "Is mahine ({month}) ka kul kharcha: Rs {amt:,.0f}.",
           "orders": "Pending powder orders:\n{lst}",
           "orders_none": "Koi powder order pending nahi hai.",
           "order_line": "• {party}: {rem:g} t baqi (kul {tot:g} t @ Rs {rate:,.0f})",
           "worker_line": "\n• {name}: Rs {due:,.0f} baqaya",
           "party_line": "{name} Rs {bal:,.0f}",
           "summary": "Aaj ka khulasa ({date}): {ti} gariyan IN ({rit:g} t pathar), {to} OUT ({pot:g} t powder), pisai {gt:g} t, {bags} bag bane. Cash aaya Rs {tin:,.0f}, gaya Rs {tout:,.0f}. Kharcha Rs {exp:,.0f}.",
           "pay_in_head": "Aaye hue paisay ({range}) — kul Rs {tot:,.0f}:\n{lst}",
           "pay_out_head": "Diye gaye paisay ({range}) — kul Rs {tot:,.0f}:\n{lst}",
           "pay_in_none": "({range}) koi payment nahi aayi.",
           "pay_out_none": "({range}) koi payment nahi di gayi.",
           "pay_line": "• {name}: Rs {amt:,.0f} ({method})",
           "pay_pin_head": "{name} se aaye paisay ({range}) — kul Rs {tot:,.0f}:\n{lst}",
           "pay_pout_head": "{name} ko diye paisay ({range}) — kul Rs {tot:,.0f}:\n{lst}",
           "worker_one": "{name} ({kind}): kamai Rs {earned:,.0f}, ada Rs {paid:,.0f}, baqaya Rs {due:,.0f}.",
           "exp_head": "{head} ka kharcha ({range}): Rs {amt:,.0f}.",
           "prod_split": " Din ki shift {bd} bag, raat ki shift {bn} bag.",
           "prod_party": "{name}: pisai {gt:g} t, {bags} bag bane (average grade {gr:g}%).",
           "veh_party": "{name}: aaj {ti} gariyan IN ({rit:g} t pathar), {to} OUT ({pot:g} t powder).",
           "filter_s": "Godam mein filter powder (mill ka apna stock — clients ki pisai se nikalta hai magar un ka nahi hota): {kg:,.0f} kg.",
           "grind_range": "Pisai ki kamai ({range}): Rs {amt:,.0f}.",
           "cih_h": "Cash in hand — kul Rs {tot:,.0f}:\n{lst}",
           "cih_line": "• {name}: Rs {amt:,.0f}",
           "cih_none": "Is waqt kisi ke paas cash record nahi hai.",
           "trade_tot": "{range}: khareed Rs {pu:,.0f}, farokht Rs {sa:,.0f}.",
           "direct_t": "Direct sodday ({range}): {n} deals — khareed Rs {buy:,.0f}, farokht Rs {sell:,.0f}, munafa Rs {profit:,.0f}.",
           "og_factory": "{name} (bahir mill): rock bheja {sent:g} t, pisa {used:g} t, powder {pbags:g} bag ({pt:g} t), wastage kati {wt:g} t ({wp:g}%), rock abhi wahan para {rem:g} t, powder baqi {plb:g} bag, bika {sb:g} bag (Rs {sa:,.0f}), grinding charges Rs {ch:,.0f} (hamaray denay), baqaya Rs {bal:,.0f} ({who}).",
           "og_total": "Tamam bahir mills: rock bheja {sent:g} t, abhi wahan para {rem:g} t, powder baqi {plb:g} bag ({plt:g} t), wastage {wt:g} t, farokht Rs {sa:,.0f}, grinding charges Rs {ch:,.0f}.",
           "og_none": "Abhi tak koi bahir grinding record nahi hai.",
           "cheques_h": "Pending cheques: {n} — kul Rs {tot:,.0f}:\n{lst}",
           "cheque_line": "• {name}: Rs {amt:,.0f} — {no} ({bank}), due {due}",
           "cheques_none": "Koi cheque pending nahi hai.",
           "daycost": "{date} day costs: diesel {dl:g} litre, bijli {eu:g} unit.",
           "daycost_none": "{date} ki day-cost readings record nahi hain.",
           "cpt_t": "Is mahine cost per ton: kharche Rs {exp:,.0f}, pisai {tons:g} t — Rs {ept:,.0f}/ton; pisai aamdani Rs {ipt:,.0f}/ton; margin Rs {mpt:,.0f}/ton.",
           "cpt_none": "Is mahine abhi pisai nahi hui, cost per ton nahi banta.",
           "backup_s": "Aakhri backup: {when}.",
           "backup_none": "Abhi tak koi backup nahi liya gaya — Settings mein Backup button use karein."},
    "ur": {"profit_month": "{month} کا منافع: آمدنی Rs {income:,.0f} (پسائی Rs {gi:,.0f} + فروخت Rs {si:,.0f})، اخراجات Rs {costs:,.0f}، منافع Rs {profit:,.0f}۔",
           "profit_today": "آج کا منافع اب تک: آمدنی Rs {income:,.0f} (پسائی Rs {gi:,.0f} + فروخت Rs {si:,.0f})، اخراجات Rs {costs:,.0f}، منافع Rs {profit:,.0f}۔",
           "stock": "اسٹاک کی صورتحال — اپنا پتھر: خریدا {rb:g} ٹن، پسا {g:g} ٹن، باقی {rl:g} ٹن۔ اپنا پاؤڈر: بنا {pm:g} ٹن، بکا {s:g} ٹن، باقی {pl:g} ٹن۔ گودام: اپنے تھیلے تیار {ob}، باردانہ (خالی تھیلے) باقی {bd}۔",
           "vehicles": "آج: {ti} گاڑیاں اندر آئیں ({rit:g} ٹن پتھر)، {to} گاڑیاں باہر گئیں ({pot:g} ٹن پاؤڈر)۔",
           "production": "آج کی پیداوار: {bags} تھیلے بنے، {gt:g} ٹن پسائی ہوئی۔",
           "cash": "آج کا کیش: آیا Rs {tin:,.0f}، گیا Rs {tout:,.0f}، خالص Rs {net:,.0f}۔",
           "dues": "مزدوروں کا کل بقایا: Rs {due:,.0f}۔{lst}",
           "theka": " ٹھیکہ مزدوروں کی کل کمائی اب تک Rs {earned:,.0f} ہے۔",
           "unknown": "میں صرف آپ کے مل کے ریکارڈ سے جواب دیتا ہوں — نمبر خود نہیں بناتا۔ مثال کے طور پر یوں پوچھیں:\n• آج کتنی گاڑیاں آئیں؟\n• اسٹاک کتنا ہے؟\n• <پارٹی کا نام> کا بقایا کتنا ہے؟\n• اس مہینے کا منافع؟\n• آج کا خرچہ؟\n• مزدوروں کے بقایا کتنے ہیں؟\n• پینڈنگ آرڈر کون سے ہیں؟",
           "debtors": "جن پارٹیوں نے دینے ہیں: {lst}۔ کل لینا ہے: Rs {tot:,.0f}۔",
           "debtors_none": "اس وقت کسی پارٹی نے کچھ نہیں دینا۔ کل لینا ہے: Rs 0۔",
           "payables": "جن پارٹیوں کو ہم نے دینے ہیں: {lst}۔ کل دینا ہے: Rs {tot:,.0f}۔",
           "payables_none": "اس وقت ہم نے کسی پارٹی کو کچھ نہیں دینا۔ کل دینا ہے: Rs 0۔",
           "biggest": "سب سے زیادہ بقایا: {name} نے Rs {bal:,.0f} دینے ہیں۔",
           "biggest_none": "اس وقت کسی پارٹی نے کچھ نہیں دینا۔",
           "balance": "{name}: بقایا Rs {bal:,.0f} ({who})۔ پتھر انتظار میں {rw:g} ٹن، پاؤڈر تیار {pr:g} ٹن ({bags} تھیلے)۔",
           "owes_us": "پارٹی نے دینے ہیں", "we_owe": "ہم نے دینے ہیں", "clear": "کھاتہ صاف ہے",
           "expenses_today": "آج کا خرچہ (لیجر): Rs {amt:,.0f}۔",
           "expenses_month": "اس مہینے ({month}) کا کل خرچہ: Rs {amt:,.0f}۔",
           "orders": "پینڈنگ پاؤڈر آرڈرز:\n{lst}",
           "orders_none": "کوئی پاؤڈر آرڈر پینڈنگ نہیں ہے۔",
           "order_line": "• {party}: {rem:g} ٹن باقی (کل {tot:g} ٹن @ Rs {rate:,.0f})",
           "worker_line": "\n• {name}: Rs {due:,.0f} بقایا",
           "party_line": "{name} Rs {bal:,.0f}",
           "summary": "آج کا خلاصہ ({date}): {ti} گاڑیاں اندر ({rit:g} ٹن پتھر)، {to} باہر ({pot:g} ٹن پاؤڈر)، پسائی {gt:g} ٹن، {bags} تھیلے بنے۔ کیش آیا Rs {tin:,.0f}، گیا Rs {tout:,.0f}۔ خرچہ Rs {exp:,.0f}۔",
           "pay_in_head": "آئے ہوئے پیسے ({range}) — کل Rs {tot:,.0f}:\n{lst}",
           "pay_out_head": "دیے گئے پیسے ({range}) — کل Rs {tot:,.0f}:\n{lst}",
           "pay_in_none": "({range}) کوئی ادائیگی نہیں آئی۔",
           "pay_out_none": "({range}) کوئی ادائیگی نہیں دی گئی۔",
           "pay_line": "• {name}: Rs {amt:,.0f} ({method})",
           "pay_pin_head": "{name} سے آئے پیسے ({range}) — کل Rs {tot:,.0f}:\n{lst}",
           "pay_pout_head": "{name} کو دیے پیسے ({range}) — کل Rs {tot:,.0f}:\n{lst}",
           "worker_one": "{name} ({kind}): کمائی Rs {earned:,.0f}، ادا Rs {paid:,.0f}، بقایا Rs {due:,.0f}۔",
           "exp_head": "{head} کا خرچہ ({range}): Rs {amt:,.0f}۔",
           "prod_split": " دن کی شفٹ {bd} تھیلے، رات کی شفٹ {bn} تھیلے۔",
           "prod_party": "{name}: پسائی {gt:g} ٹن، {bags} تھیلے بنے (اوسط گریڈ {gr:g}%)۔",
           "veh_party": "{name}: آج {ti} گاڑیاں اندر ({rit:g} ٹن پتھر)، {to} باہر ({pot:g} ٹن پاؤڈر)۔",
           "filter_s": "گودام میں فلٹر پاؤڈر (مل کا اپنا اسٹاک — گاہکوں کی پسائی سے نکلتا ہے مگر ان کا نہیں ہوتا): {kg:,.0f} کلو۔",
           "grind_range": "پسائی کی کمائی ({range}): Rs {amt:,.0f}۔",
           "cih_h": "کیش ان ہینڈ — کل Rs {tot:,.0f}:\n{lst}",
           "cih_line": "• {name}: Rs {amt:,.0f}",
           "cih_none": "اس وقت کسی کے پاس کیش ریکارڈ نہیں ہے۔",
           "trade_tot": "{range}: خرید Rs {pu:,.0f}، فروخت Rs {sa:,.0f}۔",
           "direct_t": "ڈائریکٹ سودے ({range}): {n} سودے — خرید Rs {buy:,.0f}، فروخت Rs {sell:,.0f}، منافع Rs {profit:,.0f}۔",
           "og_factory": "{name} (باہر مل): راک بھیجا {sent:g} ٹن، پسا {used:g} ٹن، پاؤڈر {pbags:g} تھیلے ({pt:g} ٹن)، ویسٹیج کٹی {wt:g} ٹن ({wp:g}%)، راک ابھی وہاں پڑا {rem:g} ٹن، پاؤڈر باقی {plb:g} تھیلے، بکا {sb:g} تھیلے (Rs {sa:,.0f})، گرائنڈنگ چارجز Rs {ch:,.0f} (ہمارے دینے)، بقایا Rs {bal:,.0f} ({who})۔",
           "og_total": "تمام باہر ملز: راک بھیجا {sent:g} ٹن، ابھی وہاں پڑا {rem:g} ٹن، پاؤڈر باقی {plb:g} تھیلے ({plt:g} ٹن)، ویسٹیج {wt:g} ٹن، فروخت Rs {sa:,.0f}، گرائنڈنگ چارجز Rs {ch:,.0f}۔",
           "og_none": "ابھی تک کوئی باہر گرائنڈنگ ریکارڈ نہیں ہے۔",
           "cheques_h": "پینڈنگ چیک: {n} — کل Rs {tot:,.0f}:\n{lst}",
           "cheque_line": "• {name}: Rs {amt:,.0f} — {no} ({bank})، واجب {due}",
           "cheques_none": "کوئی چیک پینڈنگ نہیں ہے۔",
           "daycost": "{date} ڈے کاسٹ: ڈیزل {dl:g} لیٹر، بجلی {eu:g} یونٹ۔",
           "daycost_none": "{date} کی ڈے کاسٹ ریڈنگز ریکارڈ نہیں ہیں۔",
           "cpt_t": "اس مہینے کاسٹ فی ٹن: اخراجات Rs {exp:,.0f}، پسائی {tons:g} ٹن — Rs {ept:,.0f}/ٹن؛ پسائی آمدنی Rs {ipt:,.0f}/ٹن؛ مارجن Rs {mpt:,.0f}/ٹن۔",
           "cpt_none": "اس مہینے ابھی پسائی نہیں ہوئی، کاسٹ فی ٹن نہیں بنتا۔",
           "backup_s": "آخری بیک اپ: {when}۔",
           "backup_none": "ابھی تک کوئی بیک اپ نہیں لیا گیا — سیٹنگز میں بیک اپ بٹن استعمال کریں۔"},
    "hi": {"profit_month": "{month} का मुनाफ़ा: आय Rs {income:,.0f} (ग्राइंडिंग Rs {gi:,.0f} + बिक्री Rs {si:,.0f}), खर्च Rs {costs:,.0f}, मुनाफ़ा Rs {profit:,.0f}।",
           "profit_today": "आज का मुनाफ़ा अब तक: आय Rs {income:,.0f} (ग्राइंडिंग Rs {gi:,.0f} + बिक्री Rs {si:,.0f}), खर्च Rs {costs:,.0f}, मुनाफ़ा Rs {profit:,.0f}।",
           "stock": "स्टॉक की स्थिति — अपना रॉक: ख़रीदा {rb:g} टन, ग्राइंड {g:g} टन, बाकी {rl:g} टन। अपना पाउडर: बना {pm:g} टन, बिका {s:g} टन, बाकी {pl:g} टन। गोदाम: अपने बोरे तैयार {ob}, बरदाना बाकी {bd}।",
           "vehicles": "आज: {ti} गाड़ियाँ अंदर ({rit:g} टन रॉक), {to} गाड़ियाँ बाहर ({pot:g} टन पाउडर)।",
           "production": "आज का उत्पादन: {bags} बोरे बने, {gt:g} टन ग्राइंड हुआ।",
           "cash": "आज कैश: आया Rs {tin:,.0f}, गया Rs {tout:,.0f}, शुद्ध Rs {net:,.0f}।",
           "dues": "वर्करों का कुल बकाया: Rs {due:,.0f}।{lst}",
           "theka": " ठेका वर्करों की कुल कमाई अब तक Rs {earned:,.0f} है।",
           "unknown": "मैं सिर्फ़ आपके मिल रिकॉर्ड से जवाब देता हूँ — नंबर ख़ुद नहीं बनाता। उदाहरण के लिए ऐसे पूछें:\n• आज कितनी गाड़ियाँ आईं?\n• स्टॉक कितना है?\n• <पार्टी का नाम> का बकाया कितना है?\n• इस महीने का मुनाफ़ा?\n• आज का खर्च?\n• वर्करों के बकाया कितने हैं?\n• पेंडिंग ऑर्डर कौन से हैं?",
           "debtors": "जिन पार्टियों ने देने हैं: {lst}। कुल लेना है: Rs {tot:,.0f}।",
           "debtors_none": "इस समय किसी पार्टी ने कुछ नहीं देना। कुल लेना है: Rs 0।",
           "payables": "जिन पार्टियों को हमें देने हैं: {lst}। कुल देना है: Rs {tot:,.0f}।",
           "payables_none": "इस समय हमें किसी पार्टी को कुछ नहीं देना। कुल देना है: Rs 0।",
           "biggest": "सबसे ज़्यादा बकाया: {name} ने Rs {bal:,.0f} देने हैं।",
           "biggest_none": "इस समय किसी पार्टी ने कुछ नहीं देना।",
           "balance": "{name}: बैलेंस Rs {bal:,.0f} ({who})। रॉक प्रतीक्षारत {rw:g} टन, पाउडर तैयार {pr:g} टन ({bags} बोरे)।",
           "owes_us": "पार्टी ने देने हैं", "we_owe": "हमें देने हैं", "clear": "साफ़",
           "expenses_today": "आज का खर्च (लेजर): Rs {amt:,.0f}।",
           "expenses_month": "इस महीने ({month}) का कुल खर्च: Rs {amt:,.0f}।",
           "orders": "पेंडिंग पाउडर ऑर्डर:\n{lst}",
           "orders_none": "कोई पाउडर ऑर्डर पेंडिंग नहीं है।",
           "order_line": "• {party}: {rem:g} टन बाकी (कुल {tot:g} टन @ Rs {rate:,.0f})",
           "worker_line": "\n• {name}: Rs {due:,.0f} बकाया",
           "party_line": "{name} Rs {bal:,.0f}",
           "summary": "आज का सारांश ({date}): {ti} गाड़ियाँ अंदर ({rit:g} टन रॉक), {to} बाहर ({pot:g} टन पाउडर), ग्राइंड {gt:g} टन, {bags} बोरे बने। कैश आया Rs {tin:,.0f}, गया Rs {tout:,.0f}। खर्च Rs {exp:,.0f}।",
           "pay_in_head": "आए हुए पैसे ({range}) — कुल Rs {tot:,.0f}:\n{lst}",
           "pay_out_head": "दिए गए पैसे ({range}) — कुल Rs {tot:,.0f}:\n{lst}",
           "pay_in_none": "({range}) कोई भुगतान नहीं आया।",
           "pay_out_none": "({range}) कोई भुगतान नहीं दिया गया।",
           "pay_line": "• {name}: Rs {amt:,.0f} ({method})",
           "pay_pin_head": "{name} से आए पैसे ({range}) — कुल Rs {tot:,.0f}:\n{lst}",
           "pay_pout_head": "{name} को दिए पैसे ({range}) — कुल Rs {tot:,.0f}:\n{lst}",
           "worker_one": "{name} ({kind}): कमाई Rs {earned:,.0f}, दिया Rs {paid:,.0f}, बकाया Rs {due:,.0f}।",
           "exp_head": "{head} का खर्च ({range}): Rs {amt:,.0f}।",
           "prod_split": " दिन की शिफ्ट {bd} बोरे, रात की शिफ्ट {bn} बोरे।",
           "prod_party": "{name}: पिसाई {gt:g} टन, {bags} बोरे बने (औसत ग्रेड {gr:g}%)।",
           "veh_party": "{name}: आज {ti} गाड़ियाँ अंदर ({rit:g} टन रॉक), {to} बाहर ({pot:g} टन पाउडर)।",
           "filter_s": "गोदाम में फ़िल्टर पाउडर (मिल का अपना स्टॉक — ग्राहकों की पिसाई से निकलता है मगर उनका नहीं होता): {kg:,.0f} किलो।",
           "grind_range": "पिसाई की कमाई ({range}): Rs {amt:,.0f}।",
           "cih_h": "कैश इन हैंड — कुल Rs {tot:,.0f}:\n{lst}",
           "cih_line": "• {name}: Rs {amt:,.0f}",
           "cih_none": "इस समय किसी के पास कैश रिकॉर्ड नहीं है।",
           "trade_tot": "{range}: ख़रीद Rs {pu:,.0f}, बिक्री Rs {sa:,.0f}।",
           "direct_t": "डायरेक्ट सौदे ({range}): {n} सौदे — ख़रीद Rs {buy:,.0f}, बिक्री Rs {sell:,.0f}, मुनाफ़ा Rs {profit:,.0f}।",
           "og_factory": "{name} (बाहर मिल): रॉक भेजा {sent:g} टन, पिसा {used:g} टन, पाउडर {pbags:g} बोरे ({pt:g} टन), वेस्टेज कटी {wt:g} टन ({wp:g}%), रॉक अभी वहाँ पड़ा {rem:g} टन, पाउडर बाकी {plb:g} बोरे, बिका {sb:g} बोरे (Rs {sa:,.0f}), ग्राइंडिंग शुल्क Rs {ch:,.0f} (हमारे देने), बकाया Rs {bal:,.0f} ({who})।",
           "og_total": "सभी बाहर मिलें: रॉक भेजा {sent:g} टन, अभी वहाँ पड़ा {rem:g} टन, पाउडर बाकी {plb:g} बोरे ({plt:g} टन), वेस्टेज {wt:g} टन, बिक्री Rs {sa:,.0f}, ग्राइंडिंग शुल्क Rs {ch:,.0f}।",
           "og_none": "अभी तक कोई बाहर ग्राइंडिंग रिकॉर्ड नहीं है।",
           "cheques_h": "पेंडिंग चेक: {n} — कुल Rs {tot:,.0f}:\n{lst}",
           "cheque_line": "• {name}: Rs {amt:,.0f} — {no} ({bank}), देय {due}",
           "cheques_none": "कोई चेक पेंडिंग नहीं है।",
           "daycost": "{date} डे कॉस्ट: डीज़ल {dl:g} लीटर, बिजली {eu:g} यूनिट।",
           "daycost_none": "{date} की डे कॉस्ट रीडिंग रिकॉर्ड नहीं हैं।",
           "cpt_t": "इस महीने लागत प्रति टन: ख़र्च Rs {exp:,.0f}, पिसाई {tons:g} टन — Rs {ept:,.0f}/टन; पिसाई आय Rs {ipt:,.0f}/टन; मार्जिन Rs {mpt:,.0f}/टन।",
           "cpt_none": "इस महीने अभी पिसाई नहीं हुई, लागत प्रति टन नहीं बनता।",
           "backup_s": "आख़िरी बैकअप: {when}।",
           "backup_none": "अभी तक कोई बैकअप नहीं लिया गया — सेटिंग्स में बैकअप बटन इस्तेमाल करें।"},
}

# keyword sets per intent: "lat" is matched on the lower-cased query,
# "ur" on the normalised Urdu text, "hi" on the raw query.
_ASST_KW = {
    "today":      {"lat": ["aaj", "today", "aj "], "ur": ["آج"], "hi": ["आज"]},
    "month":      {"lat": ["mahine", "mahina", "month", "maah", "maheene"], "ur": ["مہینے", "مہینہ", "ماہ"], "hi": ["महीने", "महीना", "माह"]},
    "profit":     {"lat": ["profit", "munafa", "nafa", "faida", "kamai hui"], "ur": ["منافع", "نفع", "فائدہ"], "hi": ["मुनाफ़ा", "मुनाफा", "लाभ"]},
    "stock":      {"lat": ["stock", "maal", "godam", "pathar kitna", "powder kitna", "rock kitna",
                            "kitna bacha", "kitna para", "kitna pada", "bacha hai", "reh gaya"],
                   "ur": ["اسٹاک", "مال", "گودام", "پتھر کتنا", "پاوڈر کتنا", "کتنا بچا", "کتنا پڑا", "بچا ہے", "رہ گیا"],
                   "hi": ["स्टॉक", "माल", "गोदाम", "कितना बचा"]},
    "vehicles":   {"lat": ["gari", "gariyan", "gariyon", "vehicle", "vehicles", "truck", "trucks",
                            "aayin", "aayi", "aaya", "aayen", "gayin", "gayi", "nikli"],
                   "ur": ["گاڑی", "گاڑیاں", "ٹرک", "آئیں", "آئی", "آئے", "گئیں", "نکلیں"],
                   "hi": ["गाड़ी", "गाड़ियाँ", "वाहन", "ट्रक", "आईं", "आई"]},
    "production": {"lat": ["production", "prod", "bag bane", "bags bane", "kitne bag", "bori", "boriyan", "borian"],
                   "ur": ["پیداوار", "بوریاں", "بوری", "تھیلے بنے", "کتنے تھیلے", "کتنے بوری"],
                   "hi": ["उत्पादन", "बोरियाँ", "बोरी", "कितने बोरे"]},
    "expenses":   {"lat": ["kharcha", "kharche", "kharch", "expense", "expenses", "akhrajat"],
                   "ur": ["خرچہ", "خرچے", "خرچ", "اخراجات"], "hi": ["खर्च", "खर्चा", "खर्चे"]},
    "cash":       {"lat": ["cash", "roznamcha", "rokra", "naqdi"], "ur": ["کیش", "نقد", "روزنامچہ"], "hi": ["कैश", "नकद"]},
    "workers":    {"lat": ["mazdoor", "mazdooron", "mazdur", "worker", "workers", "theka", "thekay",
                            "tankhwah", "ujrat", "labour", "labor", "staff"],
                   "ur": ["مزدور", "مزدوروں", "ٹھیکہ", "ٹھیکے", "تنخواہ", "اجرت", "لیبر"],
                   "hi": ["मज़दूर", "मजदूर", "ठेका", "ठेके", "तनख्वाह", "मज़दूरी"]},
    "dues":       {"lat": ["due", "dues", "baqaya", "baqiya", "bakaya", "dena hai", "dene hain", "dene hen"],
                   "ur": ["بقایا", "دینے ہیں", "دینا ہے", "دینے"], "hi": ["बकाया", "देना है", "देने हैं"]},
    "receivable": {"lat": ["lena hai", "lene hain", "receivable", "receivables", "debtor", "debtors",
                            "udhaar", "udhar", "kis ne dene", "kin ne dene", "kis kis ne", "kon kon"],
                   "ur": ["لینا ہے", "لینے ہیں", "ادھار", "کس نے دینے", "کن کن نے", "کون کون"],
                   "hi": ["लेना है", "लेने हैं", "उधार", "किसने देने"]},
    "payable":    {"lat": ["hum ne dene", "ham ne dene", "humne dene", "hum ne dena", "payable", "payables", "dena hai hum",
                            "kis ko dene", "kis ko dena", "ko dene hain", "dene hain kis",
                            "paisay dene", "paisay dena", "paisy dene"],
                   "ur": ["ہم نے دینے", "ہم نے دینا", "ہمیں دینے"], "hi": ["हमें देना", "हमें देने", "हमने देने"]},
    "biggest":    {"lat": ["sab se zyada", "sabse zyada", "sab say zyada", "sab se bara", "sabse bara",
                            "biggest", "maximum", "most"], "ur": ["سب سے زیادہ", "سب سے بڑا"],
                   "hi": ["सबसे ज़्यादा", "सबसे ज्यादा", "सबसे बड़ा"]},
    "balance":    {"lat": ["balance", "khata", "khaata", "hisab", "hisaab", "hisab kitab", "baqaya", "baqiya"],
                   "ur": ["بیلنس", "کھاتہ", "کھاتا", "حساب", "بقایا"], "hi": ["बैलेंस", "खाता", "हिसाब", "बकाया"]},
    "summary":    {"lat": ["summary", "khulasa", "day end", "dayend", "din ka hisab", "aaj ka din", "poora din"],
                   "ur": ["خلاصہ", "دن کا حساب", "آج کا دن"], "hi": ["सारांश", "दिन का हिसाब"]},
    "phosdetail": {"lat": ["phosphate detail", "phosphate report", "register report", "roz ka register",
                            "phosphate ki detail", "detail report"],
                   "ur": ["فاسفیٹ تفصیل", "رجسٹر رپورٹ", "فاسفیٹ رپورٹ"],
                   "hi": ["फॉस्फेट विवरण", "रजिस्टर रिपोर्ट", "फॉस्फेट रिपोर्ट"]},
}
_ASST_ROMAN_MARKERS = {"kitna", "kitni", "kitne", "hai", "hain", "aaj", "ka", "ki", "ke", "mera",
                       "meri", "mere", "batao", "btao", "dikhao", "kis", "kisne", "kon", "kya",
                       "hua", "hue", "hui", "gaya", "gayi", "gaye", "aaya", "aayi", "aayin",
                       "baqaya", "khata", "mazdoor", "gari", "gariyan", "maal", "bacha",
                       "pooch", "wala", "wali", "kar", "bana", "bane", "chahiye", "abhi",
                       "kahan", "kidhar", "kdr", "kaise", "kesay", "mujhe", "mujy", "nai",
                       "jaga", "jagah"}

# Roman-Urdu function words: two or more of these in a question also
# classify it as Roman Urdu even when no strong marker word appears —
# a short loose question must NEVER fall through to an English reply.
_ASST_ROMAN_FUNC = {"aaj", "aj", "kal", "ko", "sy", "se", "ne", "han", "ha",
                    "kisi", "kia", "aaye", "aaya", "diye", "diya", "paisay",
                    "lena", "lene", "dena", "dene", "bhi", "kab", "tha", "thi",
                    "wala", "wali", "kar", "hua", "hue", "maine"}

def _asst_hit(lat, urn, raw, group):
    kw = _ASST_KW[group]
    return (any(k in lat for k in kw["lat"]) or any(k in urn for k in kw["ur"])
            or any(k in raw for k in kw["hi"]))

# ------------------------------------------------- loose typing tolerance --
# The owner types Roman Urdu loosely ("gari kis ki the jo i ha" =
# "gari kis ki thi jo aayi hai"). A word-level normalization pass maps
# the common variant spellings onto the canonical tokens the matchers
# use, BEFORE any matching; token-level fuzzy matching (edit distance
# <= 1) covers the rest for the key intent vocabulary.
_LOOSE_MAP = {
    "the": "thi", "teh": "thi", "thy": "thi", "thi": "thi",
    "i": "aayi", "ayi": "aayi", "aai": "aayi", "ai": "aayi", "aay": "aayi",
    "gai": "gayi", "gyi": "gayi", "kiski": "kis ki", "kiska": "kis ka",
    "mari": "meri", "chayea": "chahiye", "chahye": "chahiye",
    "smj": "samajh", "samj": "samajh", "ha": "hai", "han": "hain",
    "btao": "batao", "bta": "batao", "bata": "batao", "bad": "baad",
    "kitny": "kitne", "kitni": "kitni", "hisab": "hisaab",
    "khaata": "khata", "katha": "khata", "gariya": "gariyan",
    "gariyon": "gariyan", "garia": "gariyan", "gaddi": "gari",
    "aya": "aaya", "aen": "aayen", "krna": "karna", "kr": "kar",
    "mujy": "mujhe", "mujhy": "mujhe", "tm": "tum", "hy": "hai",
    "hen": "hain", "hyn": "hain", "puch": "pooch", "pouch": "pooch",
    "raha": "raha", "rha": "raha", "rhi": "rahi", "thi": "thi",
    "bahi": "khata", "baki": "baqi", "baqya": "baqaya",
    "adaigi": "adaigi", "tankha": "tankhwah", "ujrt": "ujrat",
    "mulazim": "mazdoor", "bnda": "banda",
    # money + function words (owner's live test, 28 Oct 2026)
    "aj": "aaj", "pasy": "paisay", "paisy": "paisay", "pese": "paisay",
    "paisa": "paisay", "rakam": "raqam", "dea": "diye", "dia": "diya",
    "daina": "dena", "denay": "dene", "lenay": "lene", "laina": "lena",
    "ay": "aayi", "aye": "aayi", "many": "maine", "sy": "se",
    "bhejay": "bheje", "kisko": "kis ko", "kisny": "kis ne",
}

def _norm_loose(lat):
    """Map loose Roman-Urdu spellings to canonical tokens (word level;
    a map value may itself be two tokens, e.g. kiski -> 'kis ki')."""
    out = []
    for tok in (lat or "").split():
        t = tok.strip("?.,!;:")
        out.append(_LOOSE_MAP.get(t, tok))
    return " ".join(out)

def _ed1(a, b):
    """True when a and b are within edit distance 1 (both len >= 3)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1 or la < 3 or lb < 3:
        return False
    if la == lb:
        return sum(1 for x, y in zip(a, b) if x != y) <= 1
    if la > lb:
        a, b, la, lb = b, a, lb, la
    i = j = diff = 0
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1; j += 1
        else:
            diff += 1; j += 1
            if diff > 1:
                return False
    return True

def _fuzzy_any(lat, vocab):
    """Any token of lat within edit distance 1 of any vocab word."""
    toks = [t.strip("?.,!;:") for t in (lat or "").split()]
    return any(_ed1(t, v) for t in toks for v in vocab if len(t) >= 3 and len(v) >= 3)

# ------------------------------------------------------------ social layer --
_SOCIAL = {
 "greet": {"en": "Hello {name}! Good to see you. Ask me anything about the mill - today's vehicles, a party's khata, stock, or where any entry goes.", "roman": "Salam {name}! Khush aamdeed. Mill ke baare mein kuch bhi poochein - aaj ki gariyan, kisi party ka khata, stock, ya koi entry kahan jati hai.", "ur": "سلام {name}! خوش آمدید۔ مل کے بارے میں کچھ بھی پوچھیں - آج کی گاڑیاں، کسی پارٹی کا کھاتہ، اسٹاک، یا کوئی انٹری کہاں جاتی ہے۔", "hi": "नमस्ते {name}! स्वागत है। मिल के बारे में कुछ भी पूछें - आज की गाड़ियाँ, किसी पार्टी का खाता, स्टॉक, या कोई एंट्री कहाँ जाती है।"},
 "howru": {"en": "All well here, {name} - the mill's records are at my fingertips. What shall we look at?", "roman": "Alhamdulillah, sab theek hai {name} - mill ka saara record meri ungliyon par hai. Kya dekhna hai?", "ur": "الحمدللہ، سب ٹھیک ہے {name} - مل کا سارا ریکارڈ میری انگلیوں پر ہے۔ کیا دیکھنا ہے؟", "hi": "सब ठीक है {name} - मिल का सारा रिकॉर्ड मेरी उंगलियों पर है। क्या देखना है?"},
 "thanks": {"en": "Any time, {name} - that is what I am here for. Anything else?", "roman": "Koi baat nahi {name} - mein isi liye hoon. Aur kuch?", "ur": "کوئی بات نہیں {name} - میں اسی لیے ہوں۔ اور کچھ؟", "hi": "कोई बात नहीं {name} - मैं इसी लिए हूँ। और कुछ?"},
 "bye": {"en": "Allah Hafiz, {name}! Whenever you need the mill's figures, I am right here.", "roman": "Allah Hafiz, {name}! Jab bhi mill ke numbers chahiyein, mein yaheen hoon.", "ur": "اللہ حافظ، {name}! جب بھی مل کے اعداد چاہیے ہوں، میں یہیں ہوں۔", "hi": "अल्लाह हाफ़िज़, {name}! जब भी मिल के आँकड़े चाहिए, मैं यहीं हूँ।"},
 "praise": {"en": "That made my day, {name}! I will keep the answers just as sharp. What next?", "roman": "Dil khush kar diya, {name}! Jawab isi tarah tez rakhoon ga. Agla sawal?", "ur": "دل خوش کر دیا، {name}! جواب اسی طرح تیز رکھوں گا۔ اگلا سوال؟", "hi": "दिल खुश कर दिया, {name}! जवाब इसी तरह तेज़ रखूँगा। अगला सवाल?"},
 "sorry": {"en": "Sorry about that, {name} - let me try to do better. These are the closest topics I know; tap one, or say it in other words.", "roman": "Maazrat, {name} - dobara koshish karta hoon. Ye rahe sab se qareebi topics; kisi par tap karein, ya sawal doosray lafzon mein kah dein.", "ur": "معذرت، {name} - دوبارہ کوشش کرتا ہوں۔ یہ رہے سب سے قریبی موضوعات; کسی پر ٹیپ کریں، یا سوال دوسرے لفظوں میں کہہ دیں۔", "hi": "माफ़ करना, {name} - दोबारा कोशिश करता हूँ। ये रहे सबसे क़रीबी विषय; किसी पर टैप करें, या सवाल दूसरे शब्दों में कह दें।"},
 "whoami": {"en": "I am this mill's own assistant - I know the whole system: every page, every setting, every khata head, and where each entry goes after saving. I can also pull live figures: today's vehicles, balances, stock, profit and more. Try me.", "roman": "Mein is mill ka apna assistant hoon - mujhe poora system pata hai: har page, har setting, har khata head, aur har entry save ke baad kahan jati hai. Live numbers bhi nikal deta hoon: aaj ki gariyan, balance, stock, munafa aur boht kuch. Aazma kar dekhein.", "ur": "میں اس مل کا اپنا اسسٹنٹ ہوں - مجھے پورا سسٹم پتا ہے: ہر صفحہ، ہر ترتیب، ہر کھاتہ ہیڈ، اور ہر انٹری محفوظ کے بعد کہاں جاتی ہے۔ زندہ اعداد بھی نکال دیتا ہوں: آج کی گاڑیاں، بیلنس، اسٹاک، منافع اور بہت کچھ۔ آزما کر دیکھیں۔", "hi": "मैं इस मिल का अपना असिस्टेंट हूँ - मुझे पूरा सिस्टम पता है: हर पृष्ठ, हर सेटिंग, हर खाता हेड, और हर एंट्री सेव के बाद कहाँ जाती है। लाइव आँकड़े भी निकाल देता हूँ: आज की गाड़ियाँ, बैलेंस, स्टॉक, मुनाफ़ा और बहुत कुछ। आज़मा कर देखें।"},
}
_GREET_TOKENS = {"hi", "hello", "hey", "salam", "salaam", "aoa", "assalamualaikum",
                 "assalam", "alaikum", "walekum", "kya", "haal", "kaise", "ho",
                 "khairiyat", "hai", "hain", "theek", "aap", "sunao", "aur",
                 "ji", "bhai", "sahib", "subah", "bakhair", "good", "morning",
                 "evening", "assalamualaikum", "adaab", "adab"}

_ROMAN_MARKERS = {"salam", "aoa", "assalamualaikum", "assalam", "walaikum",
                  "shukria", "shukriya", "mehrbani", "kaise", "kaisay",
                  "khairiyat", "haal", "allah", "khuda", "hafiz", "theek",
                  "acha", "bohat", "tumhara", "tum", "mera", "meri", "bhai",
                  "kya", "kia", "hai", "ho", "nahi", "nai"}


def _social_answer(raw, lat, urn, lang, user):
    """Greetings, thanks, goodbyes, praise, complaints, 'who are you' —
    answered socially, in the question's language, BEFORE any topic
    matching, so a plain 'hi' never lands on the bare fallback. A
    greeting that carries a real question is NOT swallowed: only
    messages made purely of greeting words get the greeting reply."""
    if lang == "en":
        # Roman-Urdu social words get Roman-Urdu replies even when the
        # language detector defaulted to English on a short message.
        toks0 = {t.strip("?.,!;:") for t in lat.split()}
        if toks0 & _ROMAN_MARKERS:
            lang = "roman"
    name = ""
    if user and user.get("username"):
        name = str(user["username"]).split()[0].capitalize()
    toks = [t.strip("?.,!;:") for t in lat.split() if t.strip("?.,!;:")]
    tset = set(toks)
    _fill = lambda key: {"answer": _SOCIAL[key][lang].replace("{name}", (" " + name) if name else "")}
    # complaint / miss — apology + closest topics as chips
    if (any(k in lat for k in ("samajh nahi", "samajh nai", "smj nahi", "nahi samajh",
                                "nai samajh", "samjh nahi", "galat jawab",
                               "ghalat jawab", "wrong answer", "tum nahi samajhte",
                               "samajh nahi aata", "samajh nahi ata"))
            or "سمجھ نہیں" in urn or "गलत जवाब" in raw or "समझ नहीं" in raw):
        out = _fill("sorry")
        out["suggest"] = _kb_suggest(lat, urn, raw, lang)
        return out
    # identity / capability
    if (any(k in lat for k in ("tum kaun", "tum kon", "tumhara naam", "tumhara name",
                               "who are you", "tum kaun ho", "tum kon ho"))
            or "تم کون" in urn or "तुम कौन" in raw):
        return _fill("whoami")
    if (any(k in lat for k in ("kya kar sakte", "kia kar sakte", "kya kar sakta",
                               "tum kya kar", "what can you do", "madad kaise",
                               "tumhari madad"))
            or "کیا کر سکتے" in urn or "क्या कर सकते" in raw):
        return _fill("whoami")
    # bye
    if (tset & {"bye"}) or any(k in lat for k in ("allah hafiz", "khuda hafiz",
                                                  "allah hafiz", "phir milenge")) \
            or "اللہ حافظ" in urn or "अल्लाह हाफ़िज़" in raw:
        if len(toks) <= 6:
            return _fill("bye")
    # thanks
    if (tset & {"shukria", "shukriya", "thanks", "thank", "mehrbani", "meharbani"}) \
            or "شکریہ" in urn or "धन्यवाद" in raw or "शुक्रिया" in raw:
        if len(toks) <= 6:
            return _fill("thanks")
    # praise
    if (tset & {"zabardast", "kamal", "great", "awesome", "excellent", "superb",
                "wah", "shandar", "shaandar"}) or "زبردست" in urn or "कामाल" in raw:
        if len(toks) <= 6:
            return _fill("praise")
    # how are you
    if (any(k in lat for k in ("kya haal", "kaise ho", "kaisay ho", "khairiyat",
                               "how are you", "haal kya", "kya hal"))
            or "کیا حال" in urn or "کیسے ہو" in urn or "कैसे हो" in raw):
        if len(toks) <= 7:
            return _fill("howru")
    # pure greeting (only greeting words, short)
    if toks and len(toks) <= 6 and tset <= _GREET_TOKENS:
        return _fill("greet")
    if ("سلام" in urn or "علیکم" in urn) and len(toks) <= 4:
        return _fill("greet")
    if ("नमस्ते" in raw or "सलाम" in raw) and len(toks) <= 4:
        return _fill("greet")
    return None

# ------------------------------------------------------- vehicle identity --
def _trip_day(lat, urn, raw):
    """Day a trip question points at: parso (-2), kal/yesterday (-1),
    else today. (Urdu کل reads as yesterday for these past-tense
    questions, matching _range_of.)"""
    import datetime as _d
    toks = {t.strip("?.,!;:") for t in lat.split()}
    if "parso" in toks or "parson" in toks or "परसों" in raw or "پرسوں" in urn:
        return (_d.date.today() - _d.timedelta(days=2)).isoformat()
    if "kal" in toks or "yesterday" in lat or "کل" in urn or "कल" in raw:
        return (_d.date.today() - _d.timedelta(days=1)).isoformat()
    return today()

def _trip_rows(con, date_str, direction=None, party_id=None):
    sql = ("SELECT t.*, p.name AS pname FROM trips t LEFT JOIN parties p "
           "ON p.id=t.party_id WHERE t.date=?")
    args = [date_str]
    if direction:
        sql += " AND t.direction=?"; args.append(direction)
    if party_id:
        sql += " AND t.party_id=?"; args.append(party_id)
    sql += " ORDER BY t.id"
    return [dict(r) for r in con.execute(sql, args)]

_TRIP_TXT = {
 "en":    {"head": "Vehicles on {date}:", "none": "No vehicles came or went on {date}.",
           "more": "… and {n} more (Vehicles pages show all)."},
 "roman": {"head": "{date} ki gariyan:", "none": "{date} ko koi gari nahi aayi gayi.",
           "more": "… aur {n} more (Vehicles pages par sab hain)."},
 "ur":    {"head": "{date} کی گاڑیاں:", "none": "{date} کو کوئی گاڑی نہیں آئی گئی۔",
           "more": "… اور {n} مزید (گاڑیاں صفحات پر سب ہیں)۔"},
 "hi":    {"head": "{date} की गाड़ियाँ:", "none": "{date} को कोई गाड़ी नहीं आई गई।",
           "more": "… और {n} और (वाहन पृष्ठों पर सब हैं)।"},
}

def _fmt_trips(rows, lang, limit=15):
    T = _TRIP_TXT[lang]
    lines = []
    for r in rows[:limit]:
        s = "%s · %s · %s · %g t" % (
            r["direction"], r["pname"] or "Own / Apna", r["vehicle_no"] or "-",
            float(r["net_kg"] or 0) / 1000.0)
        if r.get("driver"):
            s += " · %s" % r["driver"]
        if r.get("direction") == "OUT" and int(r.get("bags") or 0):
            s += " · %d bags" % int(r["bags"])
        lines.append(s)
    if len(rows) > limit:
        lines.append(T["more"].format(n=len(rows) - limit))
    return "\n".join(lines)

def _identity_answer(con, lat, urn, raw, lang, user):
    """WHOSE vehicle: identity words (kis/kon/konsi/whose/which) beat
    count words — the answer LISTS the day's trips (party, vehicle,
    driver, weight) instead of counting them. Returns the full reply
    dict (with conversation ctx for follow-ups) or None."""
    toks = {t.strip("?.,!;:") for t in lat.split()}
    veh = ("gari" in lat or "vehicle" in lat or "truck" in lat
           or _fuzzy_any(lat, ("gari", "gariyan", "vehicle", "truck"))
           or "گاڑی" in urn or "ٹرک" in urn or "गाड़ी" in raw or "वाहन" in raw)
    if not veh:
        return None
    ident = (toks & {"kis", "kon", "konsi", "whose", "which", "who"}
             or "kis ki" in lat or "kis ka" in lat or "kon si" in lat
             or _fuzzy_any(lat, ("kis", "konsi"))
             or "کس" in urn or "کون" in urn or "किस" in raw or "कौन" in raw)
    past = (toks & {"thi", "tha", "the", "aayi", "gayi", "aaya", "gaya"}
            or "aayi" in lat or "gayi" in lat)
    if not (ident and past):
        return None
    is_client = bool(user and user.get("role") == "client")
    pid = user.get("party_id") if is_client else None
    direction = None
    if any(k in lat for k in ("bahar", "gayi", "dispatch", "rawana", "out gayi")) \
            or "باہر" in urn or "बाहर" in raw:
        direction = "OUT"
    elif any(k in lat for k in ("andar", "aayi", "dakhil", "in aayi")) \
            or "اندر" in urn or "अंदर" in raw:
        direction = "IN"
    ds = _trip_day(lat, urn, raw)
    rows = _trip_rows(con, ds, direction, pid)
    T = _TRIP_TXT[lang]
    if not rows:
        return {"answer": T["none"].format(date=ds),
                "ctx": {"lastIntent": "trips", "lastDay": ds}}
    first_party = next((r["pname"] for r in rows if r["pname"]), None)
    return {"answer": T["head"].format(date=ds) + "\n" + _fmt_trips(rows, lang),
            "ctx": {"lastIntent": "trips", "lastDay": ds,
                    "lastParty": first_party or ""}}

def _asst_lang(raw):
    """Reply language = the script the question was asked in."""
    lat = raw.lower()
    urn = _norm_urdu(raw)
    ur_hit = any(any(k in urn for k in kw["ur"]) for kw in _ASST_KW.values())
    ar_tokens = sum(1 for tok in raw.split() if _has_ar(tok))
    if _has_dev(raw):
        return "hi"
    if ur_hit or (ar_tokens and ar_tokens >= max(1, len(raw.split()) // 2)):
        return "ur"
    toks = {t.strip("?.,!") for t in lat.split()}
    if toks & _ASST_ROMAN_MARKERS:
        return "roman"
    # loose-normalised tokens ("aj" -> "aaj", "pasy" -> "paisay") also
    # count — but English "i"/"the"/"a" are skipped: they normalise to
    # Roman words ("i" -> "aayi") and would misclassify plain English
    lo = set()
    for t0 in lat.split():
        t = t0.strip("?.,!;:")
        if t in ("i", "the", "a"):
            continue
        lo.update(_LOOSE_MAP.get(t, t).split())
    if lo & _ASST_ROMAN_MARKERS:
        return "roman"
    if len(toks & _ASST_ROMAN_FUNC) >= 2 or len(lo & _ASST_ROMAN_FUNC) >= 2:
        return "roman"
    return "en"

def _pnl_day(con, date_str):
    """Same aggregation as pnl() but for one exact day (read-only helper
    for the assistant; pnl() itself is untouched)."""
    def s(sql, a=()):
        return con.execute(sql, a).fetchone()["s"] or 0
    a = (date_str,)
    gi = s("SELECT COALESCE(SUM(amount),0) s FROM grinding_jobs WHERE date=?", a)
    si = s("SELECT COALESCE(SUM(amount),0) s FROM sales WHERE date=?", a)
    si += s("SELECT COALESCE(SUM(net_kg/1000.0*sale_rate),0) s FROM trips "
            "WHERE direction='OUT' AND sale_buyer_id IS NOT NULL AND sale_rate>0 "
            "AND date=?", a)
    pu = s("SELECT COALESCE(SUM(amount),0) s FROM purchases WHERE date=?", a)
    ex = s("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date=? AND status!='rejected'", a)
    po = s("SELECT COALESCE(SUM(amount),0) s FROM worker_payouts WHERE date=?", a)
    ma = s("SELECT COALESCE(SUM(cost),0) s FROM maintenance WHERE date=?", a)
    fm = s("SELECT COALESCE(SUM(freight),0) s FROM trips WHERE date=? AND freight_payer='mill'", a)
    lm = s("SELECT COALESCE(SUM(loading+unloading),0) s FROM trips WHERE date=? AND charge_bearer='mill'", a)
    og = s("SELECT COALESCE(SUM(amount),0) s FROM outside_grinding WHERE kind='bill' AND date=?", a)
    income = gi + si
    costs = pu + ex + po + ma + fm + lm + og
    return {"income": income, "grinding_income": gi, "sales_income": si,
            "costs": costs, "profit": income - costs}

def _pay_range(lat, urn, raw, lang):
    """Date list + label for payment/trade questions: an explicit
    engine range (yesterday / last 7 / this week / last month) wins,
    then 'this month', then parso (day before yesterday), else today."""
    import datetime as _d
    L = _L2[lang]
    rk = _range_of(lat, urn, raw)
    if rk:
        return [d.isoformat() for d in _range_dates(rk)], L["range_" + rk]
    if _asst_hit(lat, urn, raw, "month"):
        td = _d.date.today()
        first = td.replace(day=1)
        return [(first + _d.timedelta(days=i)).isoformat()
                for i in range((td - first).days + 1)], L["range_month"]
    if "parso" in lat or "parson" in lat:
        d2 = _d.date.today() - _d.timedelta(days=2)
        return [d2.isoformat()], d2.isoformat()
    return [today()], L["range_today"]

def _assistant_data(con, q, user):
    raw = (q or "").strip()
    lat = _norm_loose(raw.lower())
    urn = _norm_urdu(raw)
    month = today()[:7]
    is_client = bool(user and user.get("role") == "client")

    # ---- reply language: same script the question was asked in ----
    lang = _asst_lang(raw)
    T = _ASST[lang]

    def hit(group):
        return _asst_hit(lat, urn, raw, group)

    # ---- visible parties (client sees only his own) ----
    parties = con.execute("SELECT * FROM parties ORDER BY LENGTH(name) DESC").fetchall()
    if is_client:
        parties = [p for p in parties if p["id"] == user.get("party_id")]

    def balance_answer(p):
        _e, bal = party_ledger(con, p["id"])
        st = party_stock(con, p["id"])
        who = T["owes_us"] if bal > 0 else (T["we_owe"] if bal < 0 else T["clear"])
        return T["balance"].format(name=p["name"], bal=abs(bal), who=who,
                                   rw=st["rock_waiting_t"], pr=st["powder_ready_t"],
                                   bags=st["bags_ready"])

    # ---- payment movement detection (owner's live test, 28 Oct) ----
    # arrived (aaye/bheje) and given (diye) are MOVEMENTS; lenay/denay
    # without a movement verb are OUTSTANDING balances, answered by the
    # receivables/payables branches below.
    _toks = set(lat.split())
    _money = bool(_toks & {"paisay", "raqam", "payment", "payments"}) \
        or "پیسے" in urn or "ادائیگی" in urn or "पैसे" in raw or "भुगतान" in raw
    _out_v = bool(_toks & {"diye", "diya", "bheja"}) or "paid" in lat \
        or "gave" in lat or "ada kiye" in lat
    _in_v = bool(_toks & {"aaye", "aaya", "aayi", "aayen", "mile", "mila"}) \
        or "received" in lat or "got money" in lat
    if _toks & {"bheje"}:
        # "kis ne bheje" = money came IN to us; "maine bheje" = we sent
        if _toks & {"maine", "hum", "humne"}:
            _out_v = True
        else:
            _in_v = True
    # Urdu / Hindi script verbs are checked on the RAW text (the
    # normalised Urdu form strips the very letters these verbs carry)
    _in_v = _in_v or any(k in raw for k in ("آئے", "آیا", "آئی", "आए", "आया", "आई"))
    _out_v = _out_v or any(k in raw for k in ("دیے", "دیا", "بھیجے", "दिए", "दिया", "भेजे"))
    if "pay out" in lat or "paid out" in lat:
        _out_v = True
    if "paid me" in lat or "paid us" in lat or "who paid" in lat:
        _in_v, _out_v = True, False
    _pay_move = (_out_v or _in_v) and (_money or "kitna" in lat or "kitne" in lat
                                      or "how much" in lat or "kis" in _toks
                                      or "who" in _toks or hit("workers"))
    _og_ctx = any(k in lat for k in ("bahir", "bahar", "outside", "doosri mill",
                                     "dusri mill")) or "باہر" in urn or "बाहर" in raw
    _og_q = _og_ctx and any(k in lat for k in ("rock", "pathar", "powder", "pisai",
                                               "grinding", "wastage", "para", "parha",
                                               "bill", "bika", "bikaa", "maal"))
    L = _L2[lang]

    # ---- named party first (balance / khata questions name the party) ----
    matched = None
    for p in parties:
        name_lat = (p["name"] or "").lower()
        name_urn = _norm_urdu(p["name"] or "")
        if (name_lat and name_lat in lat) or (name_urn and _has_ar(name_urn) and name_urn in urn):
            matched = p
            break
    if matched is None:
        # partial match: any distinctive name word (>=3 chars) in the
        # question; the first word of the name counts double
        best, best_score = None, 0
        for p in parties:
            _nm = "".join(ch if ch.isalnum() else " " for ch in (p["name"] or "").lower())
            words = [w for w in _nm.split() if len(w) >= 3]
            if not words:
                continue
            hits = sum(1 for w in words if w in lat)
            score = hits + (1 if words[0] in lat else 0)
            if hits and score > best_score:
                best, best_score = p, score
        matched = best
    if matched is not None:
        # a party name with a balance/khata question — or with no other
        # clear global intent — is answered with that party's position.
        # Two escapes: a payment MOVEMENT question goes to the payments
        # block (per-party list), and an outside-grinding question
        # (bill / wastage / rock lying at a mill) goes to its block.
        global_hit = any(hit(g) for g in ("profit", "expenses", "vehicles", "production",
                                          "cash", "summary"))
        _esc = _og_q or any(k in lat for k in ("bill", "wastage")) \
            or ("mill" in lat and any(k in lat for k in ("para", "parha", "rock", "powder")))
        if (hit("balance") or hit("dues") or hit("stock") or not global_hit) \
                and not _pay_move and not _esc:
            return balance_answer(matched)
    if is_client:
        # clients only ever see their own khata/stock (role limit)
        if parties:
            return balance_answer(parties[0])
        return None

    # ---- payments in / out: who paid us, who we paid (movements) ----
    if _pay_move:
        _dates, _rlabel = _pay_range(lat, urn, raw, lang)
        _multi = len(_dates) > 1
        _ph = ",".join("?" for _ in _dates)

        def _pay_list(direction):
            _sql = ("SELECT p.date, p.amount, p.method, pa.name FROM payments p "
                    "LEFT JOIN parties pa ON pa.id=p.party_id WHERE p.direction=? "
                    "AND p.date IN (%s)" % _ph)
            _args = [direction] + list(_dates)
            if matched is not None:
                _sql += " AND p.party_id=?"
                _args.append(matched["id"])
            _sql += " ORDER BY p.date, p.id"
            _lines, _tot = [], 0.0
            for r in con.execute(_sql, _args):
                _nm = r["name"] or "—"
                if _multi:
                    _nm = "%s · %s" % (r["date"], _nm)
                _lines.append(T["pay_line"].format(name=_nm, amt=r["amount"],
                                                   method=r["method"] or "cash"))
                _tot += float(r["amount"] or 0)
            if direction == "out" and matched is None:
                # worker payouts are money out too — same ledger truth
                for r in con.execute(
                        "SELECT wp.date, wp.amount, wp.method, w.name FROM worker_payouts wp "
                        "JOIN workers w ON w.id=wp.worker_id WHERE wp.date IN (%s) "
                        "ORDER BY wp.date, wp.id" % _ph, list(_dates)):
                    _nm = r["name"]
                    if _multi:
                        _nm = "%s · %s" % (r["date"], _nm)
                    _lines.append(T["pay_line"].format(name=_nm, amt=r["amount"],
                                                       method=r["method"] or "cash"))
                    _tot += float(r["amount"] or 0)
            return _lines, _tot

        if _out_v and not _in_v:
            _lines, _tot = _pay_list("out")
            if not _lines:
                return T["pay_out_none"].format(range=_rlabel)
            if matched is not None:
                return T["pay_pout_head"].format(name=matched["name"], range=_rlabel,
                                                 tot=_tot, lst="\n".join(_lines))
            return T["pay_out_head"].format(range=_rlabel, tot=_tot,
                                            lst="\n".join(_lines))
        if _in_v:
            _lines, _tot = _pay_list("in")
            if not _lines:
                return T["pay_in_none"].format(range=_rlabel)
            if matched is not None:
                return T["pay_pin_head"].format(name=matched["name"], range=_rlabel,
                                                tot=_tot, lst="\n".join(_lines))
            return T["pay_in_head"].format(range=_rlabel, tot=_tot,
                                           lst="\n".join(_lines))

    # ---- who owes the most ----
    if (hit("biggest") and (hit("dues") or hit("receivable") or hit("balance") or "owes" in lat)) \
            or ("zyada" in lat and hit("balance") and ("kis" in _toks or "kon" in _toks)):
        best, best_bal = None, 0.0
        for p in con.execute("SELECT * FROM parties"):
            _e, bal = party_ledger(con, p["id"])
            if bal > best_bal:
                best, best_bal = p, bal
        if best is None:
            return T["biggest_none"]
        return T["biggest"].format(name=best["name"], bal=best_bal)

    # ---- receivables / payables ----
    if hit("payable") and not hit("receivable"):
        lst, tot = [], 0.0
        for p in con.execute("SELECT * FROM parties ORDER BY name"):
            _e, bal = party_ledger(con, p["id"])
            if bal < 0:
                lst.append(T["party_line"].format(name=p["name"], bal=abs(bal)))
                tot += -bal
        if not lst:
            return T["payables_none"]
        return T["payables"].format(lst="; ".join(lst), tot=tot)
    if hit("receivable"):
        lst, tot = [], 0.0
        for p in con.execute("SELECT * FROM parties ORDER BY name"):
            _e, bal = party_ledger(con, p["id"])
            if bal > 0:
                lst.append(T["party_line"].format(name=p["name"], bal=bal))
                tot += bal
        if not lst:
            return T["debtors_none"]
        return T["debtors"].format(lst="; ".join(lst), tot=tot)

    # ---- workers: dues + theka earnings ----
    if hit("workers"):
        # a NAMED worker gets his own figures first
        _wn = None
        for w in con.execute("SELECT * FROM workers ORDER BY LENGTH(name) DESC"):
            _wnm = (w["name"] or "").lower()
            if _wnm and (" " + _wnm + " ") in (" " + lat + " ") or \
                    any(len(x) >= 3 and x in _toks for x in _wnm.split()):
                _wn = w
                break
        if _wn is not None:
            _d = worker_dues(con, _wn["id"])
            return T["worker_one"].format(name=_wn["name"], kind=_wn["kind"],
                                          earned=_d.get("earned", 0) or 0,
                                          paid=_d.get("paid", 0) or 0,
                                          due=_d.get("due", 0) or 0)
        tot_due, theka_earned, lines = 0.0, 0.0, []
        for w in con.execute("SELECT * FROM workers ORDER BY name"):
            d = worker_dues(con, w["id"])
            due = d.get("due", 0) or 0
            tot_due += due
            if w["kind"] == "theka":
                theka_earned += d.get("earned", 0) or 0
            if due:
                lines.append((due, T["worker_line"].format(name=w["name"], due=due)))
        lines.sort(key=lambda x: -x[0])
        ans = T["dues"].format(due=tot_due, lst="".join(x[1] for x in lines[:5]))
        if theka_earned:
            ans += T["theka"].format(earned=theka_earned)
        return ans

    # ---- outside grinding (Bahir stock) ------------------------------
    if _og_ctx or (matched is not None and any(
            k in lat for k in ("para", "parha", "wastage", "bill"))):
        _ost = outside_stock(con)
        if matched is not None:
            _f = next((f for f in _ost["factories"]
                       if f["factory_id"] == matched["id"]), None)
            if _f is not None:
                _e2, _bal = party_ledger(con, matched["id"])
                _who = T["owes_us"] if _bal > 0 else (T["we_owe"] if _bal < 0 else T["clear"])
                return T["og_factory"].format(
                    name=matched["name"], sent=_f["sent_t"], used=_f["ground_used_t"],
                    pbags=_f["powder_bags"], pt=_f["powder_t"], wt=_f["wastage_t"],
                    wp=_f["wastage_pct"], rem=_f["remaining_t"],
                    plb=_f["powder_left_bags"], sb=_f["sold_bags"],
                    sa=_f["sold_amount"], ch=_f["charges"],
                    bal=abs(_bal), who=_who)
        if matched is None:
            if not _ost["factories"]:
                return T["og_none"]
            _t = _ost["totals"]
            return T["og_total"].format(sent=_t["sent_t"], rem=_t["remaining_t"],
                                        plb=_t["powder_left_bags"], plt=_t["powder_left_t"],
                                        wt=_t["wastage_t"], sa=_t["sold_amount"],
                                        ch=_t["charges"])
        # a named NON-factory party: not an outside question after all
        # — fall through to the normal branches below

    # ---- grinding earned over a range (week / last 7 / last month) --
    _rk = _range_of(lat, urn, raw)
    if _rk in ("last7", "week", "lastmonth") and (
            "pisai" in lat or "grinding" in lat or "پسائی" in urn or "पिसाई" in raw):
        _amt = sum(_pnl_day(con, d.isoformat())["grinding_income"]
                   for d in _range_dates(_rk))
        return T["grind_range"].format(range=L["range_" + _rk], amt=_amt)

    # ---- profit (today / this month) ----
    if hit("profit"):
        if hit("today") and not hit("month"):
            r = _pnl_day(con, today())
            return T["profit_today"].format(income=r["income"], gi=r["grinding_income"],
                                            si=r["sales_income"], costs=r["costs"], profit=r["profit"])
        r = pnl(con, month)
        return T["profit_month"].format(month=month, income=r["income"], gi=r["grinding_income"],
                                         si=r["sales_income"], costs=r["costs"], profit=r["profit"])

    # ---- expenses (today / this month) ----
    if hit("expenses"):
        # a NAMED expense head/sub-head gets its own total first
        _eh = None
        for h in con.execute("SELECT * FROM expense_heads ORDER BY LENGTH(name) DESC"):
            _hn = (h["name"] or "").lower()
            _hnu = _norm_urdu(h["name"] or "")
            if (_hn and len(_hn) >= 3 and _hn in lat) or \
                    (_hnu and _has_ar(_hnu) and _hnu in urn):
                _eh = h
                break
        if _eh is not None:
            if hit("month") and not hit("today"):
                _amt = con.execute(
                    "SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE "
                    "(head_id=? OR sub_head_id=?) AND date LIKE ? AND status!='rejected'",
                    (_eh["id"], _eh["id"], month + "%")).fetchone()["s"]
                return T["exp_head"].format(head=_eh["name"], range=L["range_month"], amt=_amt)
            _amt = con.execute(
                "SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE "
                "(head_id=? OR sub_head_id=?) AND date=? AND status!='rejected'",
                (_eh["id"], _eh["id"], today())).fetchone()["s"]
            return T["exp_head"].format(head=_eh["name"], range=L["range_today"], amt=_amt)
        if hit("today") and not hit("month"):
            amt = con.execute("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date=? AND status!='rejected'",
                              (today(),)).fetchone()["s"]
            return T["expenses_today"].format(amt=amt)
        amt = con.execute("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date LIKE ? AND status!='rejected'",
                          (month + "%",)).fetchone()["s"]
        return T["expenses_month"].format(month=month, amt=amt)

    # ---- day summary ----
    if hit("summary"):
        d = day_end(con, today())
        cb = d["cashbook"]
        return T["summary"].format(date=d["date"], ti=d["trips_in"], rit=d["rock_in_t"],
                                   to=d["trips_out"], pot=d["powder_out_t"], gt=d["ground_t"],
                                   bags=d["bags"], tin=cb["total_in"], tout=cb["total_out"],
                                   exp=d["expense_total"])

    # ---- vehicles today (count; when the day is small, the list
    # rides along so a 'whose' phrasing is satisfied too) ----
    if hit("vehicles"):
        if matched is not None:
            _rows = _trip_rows(con, today(), None, matched["id"])
            _ti = [r for r in _rows if r["direction"] == "IN"]
            _to = [r for r in _rows if r["direction"] == "OUT"]
            return T["veh_party"].format(
                name=matched["name"], ti=len(_ti),
                rit=sum(float(r["net_kg"] or 0) for r in _ti) / 1000.0,
                to=len(_to),
                pot=sum(float(r["net_kg"] or 0) for r in _to) / 1000.0)
        d = day_end(con, today())
        ans = T["vehicles"].format(ti=d["trips_in"], rit=d["rock_in_t"],
                                   to=d["trips_out"], pot=d["powder_out_t"])
        rows = _trip_rows(con, today(), None, None)
        if 0 < len(rows) <= 8:
            ans += "\n" + _fmt_trips(rows, lang)
        return ans

    # ---- production today ----
    if hit("production"):
        if matched is not None:
            _pb = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production "
                              "WHERE party_id=? AND date=?",
                              (matched["id"], today())).fetchone()["s"]
            _gt = jobs_ground_t(con, "WHERE party_id=? AND date=?",
                                (matched["id"], today()))
            _gr = con.execute("SELECT COALESCE(SUM(tons*grade_pct),0) n, "
                              "COALESCE(SUM(tons),0) d FROM grinding_jobs "
                              "WHERE party_id=? AND date=?",
                              (matched["id"], today())).fetchone()
            _avg = (_gr["n"] / _gr["d"]) if _gr["d"] else 0
            return T["prod_party"].format(name=matched["name"], gt=_gt,
                                          bags=int(_pb or 0), gr=_avg)
        d = day_end(con, today())
        ans = T["production"].format(bags=d["bags"], gt=d["ground_t"])
        _pd = phosphate_detail(con, today())
        if _pd["bags_total"]:
            ans += T["prod_split"].format(bd=_pd["bags_day"], bn=_pd["bags_night"])
        return ans

    # ---- filter powder on its own ----
    if "filter" in lat or "فلٹر" in urn or "फ़िल्टर" in raw:
        return T["filter_s"].format(kg=warehouse(con)["filter_powder_kg"])

    # ---- stock position ----
    if hit("stock"):
        o = own_stock(con)
        wh = warehouse(con)
        return T["stock"].format(rb=o["rock_bought_t"], g=o["ground_t"], rl=o["rock_left_t"],
                                 pm=o["powder_made_t"], s=o["sold_t"], pl=o["powder_left_t"],
                                 ob=wh["own"]["bags_ready"], bd=wh["bardana"]["left"])

    # ---- cash in hand (per holder; owner/manager only, like the page)
    if ("cash in hand" in lat or "haath" in lat or "hath" in lat
            or (("kis ke paas" in lat or "kis k paas" in lat) and hit("cash"))) \
            and user.get("role") in ("owner", "manager"):
        _hs = [h for h in holder_summaries(con) if float(h.get("balance") or 0) != 0]
        if not _hs:
            return T["cih_none"]
        _lines = [T["cih_line"].format(name=h.get("name") or h.get("key") or "?",
                                       amt=h["balance"]) for h in _hs]
        return T["cih_h"].format(tot=sum(float(h["balance"]) for h in _hs),
                                 lst="\n".join(_lines))

    # ---- cash today ----
    if hit("cash") and not hit("dues"):
        cb = cashbook(con, today())
        return T["cash"].format(tin=cb["total_in"], tout=cb["total_out"], net=cb["net"])

    # ---- direct trades (seedha soda): count + profit over a range ---
    if "direct" in lat or "seedha" in lat or "سیدھا" in urn:
        _dates, _rlabel = _pay_range(lat, urn, raw, lang)
        _ph = ",".join("?" for _ in _dates)
        _buy = con.execute("SELECT COALESCE(SUM(amount),0) s FROM purchases "
                           "WHERE deal_id IS NOT NULL AND deal_id<>'' AND date IN (%s)"
                           % _ph, list(_dates)).fetchone()["s"]
        _sell = con.execute("SELECT COALESCE(SUM(amount),0) s FROM sales "
                            "WHERE deal_id IS NOT NULL AND deal_id<>'' AND date IN (%s)"
                            % _ph, list(_dates)).fetchone()["s"]
        _ids = {r["deal_id"] for r in con.execute(
            "SELECT deal_id FROM purchases WHERE deal_id IS NOT NULL AND deal_id<>'' "
            "AND date IN (%s)" % _ph, list(_dates))} | {r["deal_id"] for r in con.execute(
            "SELECT deal_id FROM sales WHERE deal_id IS NOT NULL AND deal_id<>'' "
            "AND date IN (%s)" % _ph, list(_dates))}
        return T["direct_t"].format(range=_rlabel, n=len(_ids), buy=_buy, sell=_sell,
                                    profit=float(_sell or 0) - float(_buy or 0))

    # ---- own purchases / sales totals over a range ------------------
    if (any(k in lat for k in ("khareed", "kharid", "purchase", "purchases", "farokht",
                                "farokhat", "sale", "sales", "bika", "becha", "sold",
                                "bought"))
            and any(k in lat for k in ("kitna", "kitni", "kitne", "total", "kul"))):
        _dates, _rlabel = _pay_range(lat, urn, raw, lang)
        _ph = ",".join("?" for _ in _dates)
        _pu = con.execute("SELECT COALESCE(SUM(amount),0) s FROM purchases "
                          "WHERE date IN (%s)" % _ph, list(_dates)).fetchone()["s"]
        _pu += con.execute("SELECT COALESCE(SUM(net_kg/1000.0*rock_rate),0) s FROM trips "
                           "WHERE direction='IN' AND rock_rate>0 AND date IN (%s)"
                           % _ph, list(_dates)).fetchone()["s"]
        _sa = con.execute("SELECT COALESCE(SUM(amount),0) s FROM sales "
                          "WHERE date IN (%s)" % _ph, list(_dates)).fetchone()["s"]
        _sa += con.execute("SELECT COALESCE(SUM(net_kg/1000.0*sale_rate),0) s FROM trips "
                           "WHERE direction='OUT' AND sale_buyer_id IS NOT NULL "
                           "AND sale_rate>0 AND date IN (%s)"
                           % _ph, list(_dates)).fetchone()["s"]
        return T["trade_tot"].format(range=_rlabel, pu=_pu, sa=_sa)

    # ---- pending cheques ----------------------------------------------
    if "cheque" in lat or "check" in lat or "چیک" in urn or "चेक" in raw:
        _rows = con.execute(
            "SELECT c.*, p.name FROM cheques c LEFT JOIN parties p ON p.id=c.party_id "
            "WHERE c.status='pending' ORDER BY c.due_date, c.id").fetchall()
        if not _rows:
            return T["cheques_none"]
        _lines = [T["cheque_line"].format(name=r["name"] or "?", amt=r["amount"],
                                          no=r["cheque_no"] or "-", bank=r["bank"] or "-",
                                          due=r["due_date"] or "-") for r in _rows]
        return T["cheques_h"].format(n=len(_rows),
                                     tot=sum(float(r["amount"] or 0) for r in _rows),
                                     lst="\n".join(_lines))

    # ---- day costs (diesel / electricity readings) --------------------
    if "day cost" in lat or "daycost" in lat or (
            ("diesel" in lat or "bijli" in lat or "electric" in lat)
            and any(k in lat for k in ("litre", "liter", "unit", "units"))):
        _ds = _trip_day(lat, urn, raw)
        _dc = con.execute("SELECT * FROM day_costs WHERE date=?", (_ds,)).fetchone()
        if _dc is None:
            return T["daycost_none"].format(date=_ds)
        return T["daycost"].format(date=_ds, dl=_dc["diesel_litres"] or 0,
                                   eu=_dc["elec_units"] or 0)

    # ---- cost per ton (this month) ------------------------------------
    if "cost per ton" in lat or "fi ton" in lat or "per ton" in lat \
            or ("lagat" in lat and "ton" in lat):
        _c = cost_per_ton(con, month + "-01", today())
        if not _c["tons_ground"]:
            return T["cpt_none"]
        return T["cpt_t"].format(exp=_c["expenses"], tons=_c["tons_ground"],
                                 ept=_c["expense_per_ton"] or 0,
                                 ipt=_c["income_per_ton"] or 0,
                                 mpt=_c["margin_per_ton"] or 0)

    # ---- generic dues -> total receivables ----
    if hit("dues"):
        lst, tot = [], 0.0
        for p in con.execute("SELECT * FROM parties ORDER BY name"):
            _e, bal = party_ledger(con, p["id"])
            if bal > 0:
                lst.append(T["party_line"].format(name=p["name"], bal=bal))
                tot += bal
        if not lst:
            return T["debtors_none"]
        return T["debtors"].format(lst="; ".join(lst), tot=tot)

    return None


# ------------------------------------------------- assistant v2 (item G) ---
# G1: system-guide brain — every view/feature, its sidebar home, what it
# is for and how to use it, in the asker's language/script.
_ASST_GROUPS = {
    "top": {"en": "Top of the sidebar", "roman": "Sidebar ke oopar", "ur": "سائیڈبار کے اوپر", "hi": "साइडबार के ऊपर"},
    "g_clients": {"en": "Clients", "roman": "Clients", "ur": "گاہک", "hi": "ग्राहक"},
    "g_daily": {"en": "Daily Work", "roman": "Daily Work", "ur": "روز کا کام", "hi": "रोज़ का काम"},
    "g_own": {"en": "Own Goods", "roman": "Own Goods", "ur": "اپنا مال", "hi": "अपना माल"},
    "g_accounts": {"en": "Accounts", "roman": "Accounts", "ur": "اکاؤنٹس", "hi": "खाते"},
    "g_workers": {"en": "Workers & Attendance", "roman": "Workers & Attendance", "ur": "مزدور و حاضری", "hi": "मज़दूर व हाज़िरी"},
    "g_system": {"en": "Setup & System", "roman": "Setup & System", "ur": "سیٹ اپ و سسٹم", "hi": "सेटअप व सिस्टम"},
}

def _vg(view, group, lat, ur, hi, en, roman, urt, hit):
    return {"view": view, "group": group, "lat": lat, "ur": ur, "hi": hi,
            "en": en, "roman": roman, "urt": urt, "hit": hit}

_VIEW_GUIDE = [
 _vg("dashboard", "top", ["dashboard", "home"], ["ڈیش بورڈ"], ["डैशबोर्ड"],
     "Dashboard — the mill at a glance: today's figures, totals, own vs clients stock, daily progress chart and pending approvals. It is the first screen after login.",
     "Dashboard — mill ki poori surat-e-haal ek nazar mein: aaj ke numbers, kul totals, apna vs gahakon ka stock, roz ki progress chart aur pending approvals. Login ke baad pehli screen yahi hai.",
     "ڈیش بورڈ — مل کی پوری صورتحال ایک نظر میں: آج کے اعداد، کل مجموعے، اپنا بمقابلہ گاہکوں کا اسٹاک، روز کی پیش رفت چارٹ اور زیر التوا منظوریاں۔ لاگ ان کے بعد پہلی اسکرین یہی ہے۔",
     "डैशबोर्ड — मिल की पूरी स्थिति एक नज़र में: आज के आँकड़े, कुल योग, अपना बनाम ग्राहकों का स्टॉक, रोज़ की प्रगति चार्ट और लंबित स्वीकृतियाँ। लॉगिन के बाद पहली स्क्रीन यही है।"),
 _vg("guide", "top", ["guide", "step by step", "rehnumai"], ["رہنمائی"], ["गाइड"],
     "Step-by-Step Guide — the 12 steps of daily work in order, each with a button to that page. Open it from the top of the sidebar.",
     "Step-by-Step Guide — roz ke kaam ke 12 steps tartib se, har step par us page ka button. Sidebar ke oopar se khulta hai.",
     "قدم بہ قدم رہنمائی — روز کے کام کے 12 اقدامات ترتیب سے، ہر قدم پر اس صفحے کا بٹن۔ سائیڈبار کے اوپر سے کھلتا ہے۔",
     "चरण-दर-चरण गाइड — रोज़ के काम के 12 चरण क्रम से, हर चरण पर उस पृष्ठ का बटन। साइडबार के ऊपर से खुलता है।"),
 _vg("parties", "g_clients", ["parties", "party", "clients", "client", "customers", "gahak", "khata kholna", "new party"], ["پارٹیاں", "گاہک", "کھاتہ"], ["पार्टियाँ", "ग्राहक", "खाता"],
     "Parties (Clients) — register every client, supplier and buyer with roles and opening balance. Steps: 1) write the name and phone, 2) tick the roles (Supplier / Buyer / Grinding), 3) set the opening balance direction and amount, 4) press Add. A party's ledger opens from the Ledger button in its row.",
     "Parties (Clients) — har client, supplier aur buyer yahan roles aur opening balance ke saath register hota hai. Steps: 1) naam aur phone likhein, 2) roles tick karein (Supplier / Buyer / Grinding), 3) opening balance ki direction aur raqam chunein, 4) Add dabayein. Party ka khata us ki row ke Ledger button se khulta hai.",
     "پارٹیاں (گاہک) — ہر گاہک، سپلائر اور خریدار یہاں رول اور ابتدائی بیلنس کے ساتھ درج ہوتا ہے۔ اقدامات: 1) نام اور فون لکھیں، 2) رول نشان لگائیں (سپلائر / خریدار / پسائی)، 3) ابتدائی بیلنس کی سمت اور رقم منتخب کریں، 4) شامل دبائیں۔ پارٹی کا کھاتہ اس کی قطار کے کھاتہ بٹن سے کھلتا ہے۔",
     "पार्टियाँ (ग्राहक) — हर ग्राहक, सप्लायर और ख़रीदार यहाँ भूमिकाओं और प्रारंभिक शेष के साथ दर्ज होता है। चरण: 1) नाम और फ़ोन लिखें, 2) भूमिकाएँ टिक करें (सप्लायर / ख़रीदार / पिसाई), 3) प्रारंभिक शेष की दिशा और राशि चुनें, 4) जोड़ें दबाएँ। पार्टी का खाता उसकी पंक्ति के खाता बटन से खुलता है।"),
 _vg("vehicle_in", "g_daily", ["vehicle in", "vehicles", "vehicle", "weighbridge", "kanta", "gate entry", "gari entry", "gari in", "maal in", "rock in"], ["گاڑیاں", "کانٹا", "گاڑی اندر"], ["वाहन", "कांटा", "गाड़ी अंदर"],
     "Vehicle In — its own page in Daily Work, for every vehicle bringing rock into the factory. Steps: 1) pick the party (suppliers + grinding customers) and write the vehicle number, 2) write the Net Weight only (no gross/tare), plus grade % if any, 3) Save and print the voucher. Money on the same entry (optional, Own entries only): the Rock purchase block appears ONLY when the Party is Own (Mine) — a client party's Vehicle In is a grinding arrival only (the client brings its own rock; no rate, no buy-from, no credit). On an Own entry, if the rock was BOUGHT, write the Rock rate /ton — the purchase (net x rate) posts as a payable to the khata of the 'Buy from' seller you pick (Buy from = Own (Mine) itself, rock from your own mine, posts no credit). 'Factory ponch rate' is the delivered rate: no rent and no separate freight. 'Mine rate' is the rate at the mine: the vehicle rent you write posts as an extra payable to the seller — or, if you set the rent to Driver, it is a mill cash cost and never touches a khata — and freight can be recorded. A Vehicle In entry never has loading charges.",
     "Vehicle In — Daily Work mein is ka apna page hai, factory mein pathar lane wali har gari ke liye. Steps: 1) party chunein (supplier + grinding customers) aur gari number likhein, 2) sirf Net Weight likhein (gross/tare nahi), grade ho to woh bhi, 3) Save karein aur voucher print karein. Isi entry par raqam (optional, sirf Own entry par): Rock purchase wala hissa SIRF tab nazar ata hai jab Party Own (Mine) ho — client party ki Vehicle In sirf pisai ke liye ayi hui gari hai (client apna pathar khud lata hai; na rate, na buy-from, na koi credit). Own entry par agar pathar KHARIDA gaya hai to Rock rate /ton likhein — khareed (net x rate) 'Buy from' seller ke khatay mein dena (payable) ban jati hai (Buy from = Own (Mine) khud ho, yani apni mine ka pathar, to koi credit nahi lagta). 'Factory ponch rate' delivered rate hai: na rent, na alag freight. 'Mine rate' mine par rate hai: jo gari ka rent likhein ge wo seller ke khatay mein alag dena ban jata hai — ya agar rent Driver par set ho to wo mill ka cash kharcha hai, kisi khatay mein nahi jata — aur freight bhi likha ja sakta hai. Vehicle In entry par loading charges kabhi nahi hote.",
     "گاڑی اندر — روز کے کام میں اس کا اپنا صفحہ ہے، فیکٹری میں پتھر لانے والی ہر گاڑی کے لیے۔ اقدامات: 1) پارٹی منتخب کریں (سپلائر + پسائی گاہک) اور گاڑی نمبر لکھیں، 2) صرف خالص وزن لکھیں، گریڈ ہو تو وہ بھی، 3) محفوظ کریں اور واؤچر پرنٹ کریں۔ اسی انٹری پر رقم (اختیاری، صرف اپنی انٹری پر): خرید والا حصہ صرف تب نظر آتا ہے جب پارٹی اپنا ہو — گاہک پارٹی کی گاڑی اندر صرف پسائی کی آمد ہے (گاہک اپنا پتھر خود لاتا ہے؛ نہ ریٹ، نہ کس سے خریدا، نہ کوئی کریڈٹ)۔ اپنی انٹری پر پتھر خریدا گیا ہو تو پتھر ریٹ لکھیں — خرید 'کس سے خریدا' بیچنے والے کے کھاتے میں دینی رقم بن جاتی ہے (کس سے خریدا = اپنا خود ہو، یعنی اپنی کان کا پتھر، تو کوئی کریڈٹ نہیں لگتا)۔ فیکٹری پہنچ ریٹ = پہنچا ہوا ریٹ (نہ کرایہ، نہ الگ فریٹ)؛ مائن ریٹ پر گاڑی کا کرایہ بیچنے والے کے کھاتے میں الگ دینی رقم بنتا ہے — یا اگر کرایہ ڈرائیور پر رکھا جائے تو وہ مل کا نقد خرچ ہے، کسی کھاتے میں نہیں جاتا۔ گاڑی اندر انٹری پر لوڈنگ چارجز کبھی نہیں ہوتے۔",
     "गाड़ी अंदर — रोज़ के काम में इसका अपना पृष्ठ है, फैक्टरी में रॉक लाने वाली हर गाड़ी के लिए। चरण: 1) पार्टी चुनें (सप्लायर + पिसाई ग्राहक) और गाड़ी नंबर लिखें, 2) केवल शुद्ध वज़न लिखें, ग्रेड हो तो वह भी, 3) सहेजें और वाउचर प्रिंट करें। इसी एंट्री पर राशि (वैकल्पिक, केवल अपनी एंट्री पर): ख़रीद वाला भाग केवल तब दिखता है जब पार्टी अपनी हो — ग्राहक पार्टी की गाड़ी अंदर केवल पिसाई की आमद है (ग्राहक अपना रॉक ख़ुद लाता है; न दर, न किससे ख़रीदा, न कोई क्रेडिट)। अपनी एंट्री पर रॉक ख़रीदा गया हो तो रॉक दर लिखें — ख़रीद 'किससे ख़रीदा' विक्रेता के खाते में देय बन जाती है (किससे ख़रीदा = अपना ख़ुद हो, यानी अपनी खदान का रॉक, तो कोई क्रेडिट नहीं लगता)। फ़ैक्टरी पहुँच दर = पहुँची हुई दर (न किराया, न अलग फ्रेट); माइन दर पर गाड़ी का किराया विक्रेता के खाते में अलग देय बनता है — या किराया ड्राइवर पर रखा जाए तो वह मिल का नकद खर्च है, किसी खाते में नहीं जाता। गाड़ी अंदर एंट्री पर लोडिंग शुल्क कभी नहीं होता।"),
 _vg("vehicle_out", "g_daily", ["vehicle out", "dispatch", "gari out", "maal out", "rawangi"], ["روانگی", "گاڑی باہر"], ["रवानगी", "गाड़ी बाहर"],
     "Vehicle Out — its own page in Daily Work, for every dispatch when powder leaves the factory. Steps: 1) pick the party (buyers + grinding customers) and write the vehicle number, 2) write the Net Weight and bags, 3) Save and print the voucher. For a party trip, Vehicle Out is DISPATCH-ONLY - it never makes a sale: if this vehicle carries your own powder to a BUYER, first enter the powder Sell in that buyer's Party Ledger (the receivable, the invoice and the own-stock-out all happen there, exactly once), then record the trip here as the gate pass - for a buyer the trip itself moves no stock and no money. A toll return (a client collecting his own powder) deducts that client's powder stock from this trip; an Own dispatch (no party) deducts own stock. EXCEPTION - an Own dispatch may record the sale right on the trip: fill 'Powder sold to' + 'Sale rate /ton' and the receivable (net tons x rate) posts in that buyer's khata from this trip, exactly once - with the sale on the trip, do NOT enter the same sale again in the Ledger (the system also warns when a sale looks duplicated). Money on the same entry (optional): a Grinding rate /ton posts the grinding charge (net x rate) to the party khata — leave it blank when the lot was already charged; on an Own dispatch the Grinding rate is hidden and never charges, because it is our own material. Loading charges are entered here (a Vehicle In never has them), and freight with its payer can be recorded too. Stock check: the form shows the powder available for the picked party (or Own stock), and a dispatch bigger than that stock asks for confirmation before it saves — a confirmed over-stock dispatch is noted in the History (audit).",
     "Vehicle Out — Daily Work mein is ka apna page hai, powder factory se rawana hone wali har gari ke liye. Steps: 1) party chunein (buyer + grinding customers) aur gari number likhein, 2) Net Weight aur bag likhein, 3) Save karein aur voucher print karein. Party wali trip par Vehicle Out SIRF rawangi (dispatch) hai - wahan sale NAHI banti: agar ye gari apna powder kisi BUYER ko le ja rahi hai to pehle us buyer ke Party Ledger mein powder Sell entry lagayein (udhaar, invoice aur apna stock-out - teeno wahi lagte hain, sirf ek dafa), phir yahan trip sirf gate pass ke tor par likhein - buyer ki trip se na stock move hota hai na raqam. Toll wapis (client apna powder le jaye) par trip usi client ke powder stock se kam karti hai; Own rawangi (koi party nahi) par apna stock kam hota hai. EK RIYAYAT - Own rawangi par sale ISI trip par likhi ja sakti hai: 'Powder sold to' aur 'Sale rate /ton' bharein to udhaar (net ton x rate) usi buyer ke khatay mein is trip se lag jata hai, sirf ek dafa - trip par sale likh di ho to wahi sale Ledger mein DOBARA na lagayein (system milti julti sale par warning bhi deta hai). Isi entry par raqam (optional): Grinding rate /ton se pisai charge (net x rate) party ke khatay mein lag jata hai — lot ka charge pehle lag chuka ho to khali chor dein; Own rawangi par Grinding rate nazar hi nahi ata aur charge kabhi nahi lagta, kyunke ye hamara apna maal hai. Loading charges yahin likhe jate hain (Vehicle In par kabhi nahi hote), aur freight bhi us ke dene wale ke saath likha ja sakta hai. Stock check: form par chuni party ka (ya apna) dastiyab powder stock nazar ata hai, aur us stock se bari rawangi save hone se pehle confirmation mangti hai — confirm ki hui zyada rawangi History (audit) mein note ho jati hai.",
     "گاڑی باہر — روز کے کام میں اس کا اپنا صفحہ ہے، فیکٹری سے پاؤڈر روانہ ہونے والی ہر گاڑی کے لیے۔ اقدامات: 1) پارٹی منتخب کریں (خریدار + پسائی گاہک) اور گاڑی نمبر لکھیں، 2) خالص وزن اور تھیلے لکھیں، 3) محفوظ کریں اور واؤچر پرنٹ کریں۔ اسی انٹری پر رقم (سب اختیاری): پسائی ریٹ سے چارج کھاتے میں لگ جاتا ہے — لاٹ کا چارج پہلے لگ چکا ہو تو خالی چھوڑیں۔ لوڈنگ چارجز یہیں لکھے جاتے ہیں، اور فریٹ بھی دینے والے کے ساتھ لکھا جا سکتا ہے۔ پارٹی والی ٹرپ پر گاڑی باہر صرف روانگی ہے — فروخت وہاں نہیں بنتی: اپنا پاؤڈر بیچنا ہو تو پہلے خریدار کے کھاتے میں پاؤڈر فروخت لگائیں، پھر یہ ٹرپ صرف گیٹ پاس ہے۔ البتہ اپنی روانگی پر فروخت اسی ٹرپ پر لکھی جا سکتی ہے: 'کس کو فروخت' اور فروخت ریٹ لکھنے سے ادھار اسی ٹرپ سے خریدار کے کھاتے میں لگ جاتا ہے، صرف ایک دفعہ — پھر وہی فروخت کھاتے میں دوبارہ نہ لگائیں۔ اپنی روانگی پر پسائی ریٹ نہیں لگتا کیونکہ یہ ہمارا اپنا مال ہے۔ اسٹاک جانچ: فارم پر منتخب پارٹی کا (یا اپنا) دستیاب پاؤڈر اسٹاک نظر آتا ہے، اور اس اسٹاک سے بڑی روانگی محفوظ ہونے سے پہلے تصدیق مانگتی ہے — تصدیق شدہ زیادہ روانگی تاریخ (آڈٹ) میں درج ہو جاتی ہے۔",
     "गाड़ी बाहर — रोज़ के काम में इसका अपना पृष्ठ है, फैक्टरी से पाउडर रवाना होने वाली हर गाड़ी के लिए। चरण: 1) पार्टी चुनें (ख़रीदार + पिसाई ग्राहक) और गाड़ी नंबर लिखें, 2) शुद्ध वज़न और बोरे लिखें, 3) सहेजें और वाउचर प्रिंट करें। इसी एंट्री पर राशि (सब वैकल्पिक): पिसाई दर से शुल्क खाते में लग जाता है — लॉट का शुल्क पहले लग चुका हो तो खाली छोड़ें। लोडिंग शुल्क यहीं लिखे जाते हैं, और फ्रेट भी देने वाले के साथ लिखा जा सकता है। पार्टी वाली ट्रिप पर गाड़ी बाहर केवल रवानगी है — बिक्री वहाँ नहीं बनती: अपना पाउडर बेचना हो तो पहले ख़रीदार के खाते में पाउडर बिक्री लगाएँ, फिर यह ट्रिप केवल गेट पास है। लेकिन अपनी रवानगी पर बिक्री इसी ट्रिप पर लिखी जा सकती है: 'किसे बेचा' और बिक्री दर लिखने से उधार इसी ट्रिप से ख़रीदार के खाते में लग जाता है, केवल एक बार — फिर वही बिक्री खाते में दोबारा न लगाएँ। अपनी रवानगी पर पिसाई दर नहीं लगती क्योंकि यह हमारा अपना माल है। स्टॉक जाँच: फ़ॉर्म पर चुनी पार्टी का (या अपना) उपलब्ध पाउडर स्टॉक दिखता है, और उस स्टॉक से बड़ी रवानगी सहेजने से पहले पुष्टि माँगती है — पुष्टि की हुई अधिक रवानगी इतिहास (ऑडिट) में दर्ज हो जाती है।"),
 _vg("grindprod", "g_daily", ["grinding", "pisai", "grind", "production", "bags entry", "bag packing", "packing", "boray", "thailay"], ["پسائی", "پیداوار", "تھیلے"], ["पिसाई", "उत्पादन", "बोरे"],
     "Grinding & Production — ONE entry for the whole job: which party's rock was ground, in the Day or Night shift, grade %, and how many powder bags were packed. Steps: 1) pick the party or Own, 2) pick the Shift (Day / Night) and the shift start/end times if you have them, 3) write the powder bags produced and the filter powder bags too (BOTH outputs are counted in bags — ground rock is not weighed here; the register works it out from the powder). The form shows the shift's total live as you type: bags x kg per bag = kg = tons, for powder, for filter powder and in total, 4) pick whose bags were used (mill bags or the party's own bags), 5) Save — one save records the grinding and the bags together: the POWDER bags credit that party's warehouse stock, while the FILTER powder bags are the mill's own — they credit the mill's Own filter stock (Warehouse + Own Stock), never the party's; for the party they are wastage. There is no rate field on this form. The kg in one bag is NOT asked on the entry: it comes from the 'Bag weight defaults' card at the end of this page (Powder bag kg and Filter bag kg, 50 each unless you change them) and every save stamps the weights in effect onto its own record, so old records never change. The Now-Grinding start/stop session is on this page too.",
     "Grinding & Production — poore kaam ki EK entry: kis party ki pisai hui, Day ya Night shift mein, grade %, aur kitne powder bag bane. Steps: 1) party ya Own chunein, 2) Shift (Day / Night) chunein aur shift ke start/end time hon to woh bhi, 3) bane hue powder bag likhein aur filter powder ke bag bhi (DONO output bag mein gine jate hain — pisa hua pathar yahan nahi tola jata; register usay powder se khud nikal leta hai). Form likhte hi shift ka total live dikhata hai: bag x fi bag kg = kg = ton, powder ka, filter powder ka aur kul, 4) ye chunein ke bag kis ke thay (mill ke ya party ke apne), 5) Save — ek save se pisai aur bag dono likhe jate hain: POWDER bag us party ke godam stock mein jama hote hain, jabke FILTER powder ke bag MILL ke apne hote hain — wo mill ke Own filter stock mein jama hote hain (Warehouse + Own Stock), party ke stock mein kabhi nahi; party ke liye wo wastage hain. Is form par rate ka khana nahi hai. Ek bag mein kitne kg hain ye entry par NAHI poochha jata: ye is page ke aakhir mein 'Bag weight defaults' card se ata hai (Powder bag kg aur Filter bag kg, badla na ho to 50/50) aur har save us waqt ke wazan apne record par stamp kar deta hai, is liye purane record kabhi nahi badalte. Now-Grinding start/stop session bhi is page par hai.",
     "پسائی و پیداوار — پورے کام کی ایک انٹری: کس پارٹی کی پسائی ہوئی، دن یا رات کی شفٹ میں، گریڈ %، اور کتنے پاؤڈر تھیلے بنے۔ اقدامات: 1) پارٹی یا اپنا منتخب کریں، 2) شفٹ (دن / رات) منتخب کریں اور شفٹ کے شروع و ختم اوقات ہوں تو وہ بھی، 3) بنے ہوئے پاؤڈر تھیلے لکھیں اور فلٹر پاؤڈر کے تھیلے بھی (دونوں پیداوار تھیلوں میں گنی جاتی ہیں — پسا ہوا پتھر یہاں نہیں تولا جاتا؛ رجسٹر اسے پاؤڈر سے خود نکال لیتا ہے)۔ فارم لکھتے ہی شفٹ کا کل زندہ دکھاتا ہے: تھیلے × فی تھیلا کلو = کلو = ٹن، پاؤڈر کا، فلٹر پاؤڈر کا اور کل، 4) یہ منتخب کریں کہ تھیلے کس کے تھے (مل کے یا پارٹی کے اپنے)، 5) محفوظ — ایک محفوظ سے پسائی اور تھیلے دونوں درج ہو جاتے ہیں: پاؤڈر تھیلے اس پارٹی کے گودام اسٹاک میں جمع ہوتے ہیں، جبکہ فلٹر پاؤڈر کے تھیلے مل کے اپنے ہوتے ہیں — وہ مل کے اپنے فلٹر اسٹاک میں جمع ہوتے ہیں (گودام + اپنا اسٹاک)، پارٹی کے اسٹاک میں کبھی نہیں؛ پارٹی کے لیے وہ ضیاع ہیں۔ اس فارم پر ریٹ کا خانہ نہیں ہے۔ ایک تھیلے میں کتنے کلو ہیں یہ انٹری پر نہیں پوچھا جاتا: یہ اس صفحے کے آخر میں 'تھیلے کے وزن کی طے شدہ قدریں' کارڈ سے آتا ہے (پاؤڈر تھیلا کلو اور فلٹر تھیلا کلو، بدلا نہ ہو تو 50/50) اور ہر محفوظ اس وقت کے وزن اپنے ریکارڈ پر مہر کر دیتا ہے، اس لیے پرانے ریکارڈ کبھی نہیں بدلتے۔ ابھی پسائی جاری کا شروع/روک سیشن بھی اس صفحے پر ہے۔",
     "पिसाई और उत्पादन — पूरे काम की एक एंट्री: किस पार्टी की पिसाई हुई, दिन या रात की शिफ़्ट में, ग्रेड %, और कितने पाउडर बोरे बने। चरण: 1) पार्टी या अपना चुनें, 2) शिफ़्ट (दिन / रात) चुनें और शिफ़्ट के शुरू व समाप्ति समय हों तो वे भी, 3) बने हुए पाउडर बोरे लिखें और फ़िल्टर पाउडर के बोरे भी (दोनों उत्पादन बोरों में गिने जाते हैं — पिसा हुआ रॉक यहाँ नहीं तौला जाता; रजिस्टर उसे पाउडर से ख़ुद निकाल लेता है)। फ़ॉर्म लिखते ही शिफ़्ट का योग लाइव दिखाता है: बोरे × प्रति बोरा किलो = किलो = टन, पाउडर का, फ़िल्टर पाउडर का और कुल, 4) यह चुनें कि बोरे किसके थे (मिल के या पार्टी के अपने), 5) सहेजें — एक सहेज से पिसाई और बोरे दोनों दर्ज हो जाते हैं: पाउडर बोरे उस पार्टी के गोदाम स्टॉक में जमा होते हैं, जबकि फ़िल्टर पाउडर के बोरे मिल के अपने होते हैं — वे मिल के अपने फ़िल्टर स्टॉक में जमा होते हैं (गोदाम + अपना स्टॉक), पार्टी के स्टॉक में कभी नहीं; पार्टी के लिए वे वेस्टेज हैं। इस फ़ॉर्म पर दर का खाना नहीं है। एक बोरे में कितने किलो हैं यह एंट्री पर नहीं पूछा जाता: यह इस पृष्ठ के अंत में 'बोरे के वज़न की डिफ़ॉल्ट' कार्ड से आता है (पाउडर बोरा किलो और फ़िल्टर बोरा किलो, बदला न हो तो 50/50) और हर सहेज उस समय के वज़न अपने रिकॉर्ड पर अंकित कर देता है, इसलिए पुराने रिकॉर्ड कभी नहीं बदलते। अभी पिसाई जारी का शुरू/रोक सेशन भी इस पृष्ठ पर है।"),
 _vg("warehouse", "g_daily", ["warehouse", "godam", "godown", "stock count", "ginti", "bardana"], ["گودام", "گنتی"], ["गोदाम", "गिनती"],
     "Warehouse / Godam — bags made, out and ready per party (with tons), physical stock counts and the Stock Count (Godam Ginti) with owner-approved adjustments. Old powder waiting is also shown here. ONE Bags card records the empty bags: pick the bag type at the top — Mill bags (bardana, the mill's own empty-bag stock) or Party bags (a party's own bags kept with the mill) — then direction, bags and note. The two balances stay separate: production uses mill bardana only, and party bags stay in that party's custody.",
     "Warehouse / Godam — har party ke bag bane, gaye aur tayyar (ton ke saath), physical ginti aur Stock Count (Godam Ginti) owner approval wale adjustments ke saath. Purana intezaar wala powder bhi yahan dikhta hai. Khali bag EK hi Bags card mein likhe jate hain: oopar bag ki qisam chunein — Mill bags (bardana, mill ke apne khali bag) ya Party bags (party ke apne bag jo mill ke paas rakhe hain) — phir direction, bag aur note. Dono balance alag rehte hain: production mein sirf mill ka bardana lagta hai, aur party ke bag usi party ki amanat rehte hain.",
     "گودام — ہر پارٹی کے تھیلے بنے، گئے اور تیار (ٹن کے ساتھ)، جسمانی گنتی اور گودام گنتی مالک منظوری والے ایڈجسٹمنٹ کے ساتھ۔ پرانا منتظر پاؤڈر بھی یہاں دکھتا ہے۔ خالی تھیلے ایک ہی تھیلے کارڈ میں درج ہوتے ہیں: اوپر تھیلے کی قسم منتخب کریں — مل کے تھیلے (باردانہ، مل کے اپنے خالی تھیلے) یا پارٹی کے تھیلے (پارٹی کے اپنے تھیلے جو مل کے پاس رکھے ہیں) — پھر سمت، تھیلے اور نوٹ۔ دونوں بیلنس الگ رہتے ہیں: پیداوار میں صرف مل کا باردانہ لگتا ہے، اور پارٹی کے تھیلے اسی پارٹی کی امانت رہتے ہیں۔",
     "गोदाम — हर पार्टी के बोरे बने, गए और तैयार (टन के साथ), भौतिक गिनती और गोदाम गिनती मालिक स्वीकृति वाले समायोजन के साथ। पुराना प्रतीक्षित पाउडर भी यहाँ दिखता है। खाली बोरे एक ही बोरे कार्ड में दर्ज होते हैं: ऊपर बोरे का प्रकार चुनें — मिल के बोरे (बरदाना, मिल के अपने खाली बोरे) या पार्टी के बोरे (पार्टी के अपने बोरे जो मिल के पास रखे हैं) — फिर दिशा, बोरे और नोट। दोनों शेष अलग रहते हैं: उत्पादन में केवल मिल का बरदाना लगता है, और पार्टी के बोरे उसी पार्टी की धरोहर रहते हैं।"),
 _vg("machines", "g_daily", ["machines", "machine", "maintenance diary", "service book"], ["مشینیں", "مشین"], ["मशीनें", "मशीन"],
     "Machines — the maintenance diary: register machines (e.g. Grinder 1), log Service / Repair / Part Change with cost and next due date. The cost posts once into the Expense Ledger under the Machine head, and due dates warn on the Dashboard.",
     "Machines — maintenance diary: machines register karein (masalan Grinder 1), Service / Repair / Part Change cost aur next due date ke saath likhein. Cost ek dafa Expense Ledger mein Machine head ke neeche lagta hai, aur due date Dashboard par warn karti hai.",
     "مشینیں — مرمت ڈائری: مشینیں درج کریں (مثلاً گرائنڈر 1)، سروس / مرمت / پرزہ تبدیلی لاگت اور اگلی تاریخ کے ساتھ لکھیں۔ لاگت ایک دفعہ اخراجات لیجر میں مشین ہیڈ کے نیچے لگتی ہے، اور واجب تاریخ ڈیش بورڈ پر خبردار کرتی ہے۔",
     "मशीनें — मरम्मत डायरी: मशीनें दर्ज करें (जैसे ग्राइंडर 1), सर्विस / मरम्मत / पुर्ज़ा बदलाव लागत और अगली तिथि के साथ लिखें। लागत एक बार खर्च लेजर में मशीन हेड के नीचे लगती है, और देय तिथि डैशबोर्ड पर चेतावनी देती है।"),
 _vg("ownstock", "g_own", ["own trade", "apni khareed", "apni farokht", "purchase", "sale own", "ledger buy", "ledger sell", "direct trade"], ["اپنی تجارت", "اپنی خرید", "براہ راست تجارت"], ["अपना व्यापार", "सीधा व्यापार"],
     "Own Stock & Trade — there is no separate Own Trade page any more: buying and selling happen where the goods move. Buy at the gate on Vehicle In, at the rock rate, or off-gate in the party's Ledger with Add Buy (step 1: pick the item — Rock, Powder or Other — then its fields). Sell in the party's Ledger with Add Sell — or record the sale on an Own Vehicle Out dispatch itself ('Powder sold to' + rate) instead; never both for the same goods (a party trip on Vehicle Out stays dispatch-only — the gate pass). A Direct Trade (buy from one party, sell to another, the goods never enter the mill) is added from this page. This page shows the own stock position plus the full trade history, every row tagged Gate / Ledger / Excel / Direct, with owner edit/delete.",
     "Own Stock & Trade — ab alag Own Trade page NAHI hai: khareed-farokht wohi hoti hai jahan maal move hota hai. Gate par khareed Vehicle In par (rock rate), ya gate ke baghair party ke Ledger mein Add Buy se (step 1: item chunein — Rock, Powder ya Other — phir us ke fields). Farokht party ke Ledger mein Add Sell se hoti hai — ya phir sale Own Vehicle Out rawangi par hi likh dein ('Powder sold to' + rate); ek hi maal ki sale dono jagah KABHI nahi (party wali trip Vehicle Out par sirf rawangi/gate pass hi rehti hai). Direct Trade (ek party se khareed, doosri ko farokht, maal mill mein NAHI ata) isi page se add hota hai. Ye page apna stock aur poori trade history dikhata hai, har row par source (Gate / Ledger / Excel / Direct) ke saath, owner edit/delete ke saath.",
     "اپنا اسٹاک و تجارت — اب الگ اپنی تجارت صفحہ نہیں ہے: خرید و فروخت وہیں ہوتی ہے جہاں مال حرکت کرتا ہے۔ گیٹ پر خرید گاڑی اندر پر (پتھر ریٹ)، یا گیٹ کے بغیر پارٹی کے کھاتے میں شامل خرید سے (قدم 1: شے منتخب کریں — پتھر، پاؤڈر یا دیگر — پھر اس کے خانے)۔ فروخت پارٹی کے کھاتے میں شامل فروخت سے ہوتی ہے — یا فروخت اپنی گاڑی باہر روانگی پر ہی لکھ دیں ('کس کو فروخت' + ریٹ)؛ ایک ہی مال کی فروخت دونوں جگہ کبھی نہیں (پارٹی والی ٹرپ گاڑی باہر پر صرف روانگی/گیٹ پاس ہی رہتی ہے)۔ براہ راست تجارت (ایک پارٹی سے خرید، دوسری کو فروخت، مال مل میں نہیں آتا) اسی صفحے سے شامل ہوتی ہے۔ یہ صفحہ اپنا اسٹاک اور پوری تجارت تاریخ دکھاتا ہے، ہر قطار پر ماخذ (گیٹ / کھاتہ / ایکسل / براہ راست) کے ساتھ، مالک تبدیل/حذف کے ساتھ۔",
     "अपना स्टॉक व व्यापार — अब अलग अपना व्यापार पृष्ठ नहीं है: ख़रीद-बिक्री वहीं होती है जहाँ माल चलता है। गेट पर ख़रीद गाड़ी अंदर पर (रॉक दर), या गेट के बिना पार्टी के खाते में ख़रीद जोड़ें से (चरण 1: वस्तु चुनें — रॉक, पाउडर या अन्य — फिर उसके फ़ील्ड)। बिक्री पार्टी के खाते में बिक्री जोड़ें से होती है — या बिक्री अपनी गाड़ी बाहर रवानगी पर ही लिख दें ('किसे बेचा' + दर); एक ही माल की बिक्री दोनों जगह कभी नहीं (पार्टी वाली ट्रिप गाड़ी बाहर पर केवल रवानगी/गेट पास ही रहती है)। सीधा व्यापार (एक पार्टी से ख़रीद, दूसरी को बिक्री, माल मिल में नहीं आता) इसी पृष्ठ से जुड़ता है। यह पृष्ठ अपना स्टॉक और पूरी व्यापार इतिहास दिखाता है, हर पंक्ति पर स्रोत (गेट / खाता / एक्सेल / सीधा) के साथ, मालिक एडिट/डिलीट के साथ।"),
 _vg("outside", "g_own", ["outside grinding", "bahir grinding", "bahar grinding", "bahar pisai", "doosri mill"], ["باہر پسائی", "دوسری مل"], ["बाहर पिसाई", "दूसरी मिल"],
     "Outside Grinding — our rock is ground by ANOTHER mill: the rock travels DIRECTLY from the mine to that factory (it never enters our godam) and the powder is sold FROM there. Three entries on this page: Rock Sent (from mine/seller, to factory, tons, grade, the AGREED grinding rate — no charge posts yet; an optional rock rate posts the purchase payable to the SELLER), a Grinding Bill when settling with the factory (powder ground in bags, the actual rock used, the rate — the charge = powder tons x rate accrues HERE as our payable CREDIT in the factory's khata, and an optional Amount Paid Now posts the payment in the same save), and Powder Sold from the factory (a normal sale + invoice from that factory's powder). Per-factory figures (sent / ground / powder / wastage / remaining / charges) and an all-factories overview sit on the page; godam stock never includes outside quantities.",
     "Outside Grinding — hamara pathar DOOSRI mill se pista hai: pathar SEEDHA khaan (mine) se us factory jata hai (hamare godam aata hi nahi) aur powder BHI wahin se bikta hai. Is page par teen entries: Rock Sent (khaan/seller se, factory ko, ton, grade, tay shuda pisai rate — abhi koi charge NAHI lagta; optional rock rate par khareed ki raqam SELLER ke khatay mein dena lag jati hai), Grinding Bill jab factory se hisaab ho (pisa hua powder bag mein, asal istemal shuda rock, rate — charge = powder ton x rate YAHIN banta hai, factory ke khatay mein hamara dena (payable) CREDIT, aur optional Abhi Ada raqam usi save mein payment bhi laga deti hai), aur Powder Sold (us factory ke powder ki aam farokht + invoice). Har factory ke figures (bheja / pisa / powder / wastage / baqi / charges) aur kul factories ka overview page par hai; godam stock mein bahir ki miqdar KABHI shamil nahi hoti.",
     "باہر پسائی — ہمارا پتھر دوسری مل سے پستا ہے: پتھر سیدھا کان سے اس فیکٹری جاتا ہے (ہمارے گودام آتا ہی نہیں) اور پاؤڈر بھی وہیں سے بکتا ہے۔ اس صفحے پر تین انٹریاں: پتھر بھیجا (کان/فروخت کنندہ سے، فیکٹری کو، ٹن، گریڈ، طے شدہ پسائی ریٹ — ابھی کوئی چارج نہیں لگتا؛ اختیاری پتھر ریٹ پر خرید کی رقم فروخت کنندہ کے کھاتے میں دینی لگ جاتی ہے)، گرائنڈنگ بل جب فیکٹری سے حساب ہو (پسا ہوا پاؤڈر تھیلوں میں، اصل استعمال شدہ پتھر، ریٹ — چارج = پاؤڈر ٹن × ریٹ یہیں بنتا ہے، فیکٹری کے کھاتے میں ہمارا دینا کریڈٹ، اور اختیاری ابھی ادا رقم اسی محفوظ میں ادائیگی بھی لگا دیتی ہے)، اور پاؤڈر فروخت (اس فیکٹری کے پاؤڈر کی عام فروخت + انوائس)۔ ہر فیکٹری کے اعداد (بھیجا / پسا / پاؤڈر / ضیاع / باقی / چارجز) اور کل فیکٹریوں کا جائزہ صفحے پر ہے؛ گودام اسٹاک میں باہر کی مقدار کبھی شامل نہیں ہوتی۔",
     "बाहर पिसाई — हमारा रॉक दूसरी मिल से पिसता है: रॉक सीधा खदान से उस फ़ैक्ट्री जाता है (हमारे गोदाम आता ही नहीं) और पाउडर भी वहीं से बिकता है। इस पृष्ठ पर तीन एंट्रियाँ: रॉक भेजा (खदान/विक्रेता से, फ़ैक्ट्री को, टन, ग्रेड, तय पिसाई दर — अभी कोई शुल्क नहीं लगता; वैकल्पिक रॉक दर पर ख़रीद की राशि विक्रेता के खाते में देय लग जाती है), ग्राइंडिंग बिल जब फ़ैक्ट्री से हिसाब हो (पिसा पाउडर बोरों में, असली इस्तेमाल रॉक, दर — शुल्क = पाउडर टन × दर यहीं बनता है, फ़ैक्ट्री के खाते में हमारा देय क्रेडिट, और वैकल्पिक अभी अदा राशि उसी सेव में भुगतान भी लगा देती है), और पाउडर बिक्री (उस फ़ैक्ट्री के पाउडर की सामान्य बिक्री + इनवॉइस)। हर फ़ैक्ट्री के आँकड़े (भेजा / पिसा / पाउडर / वेस्टेज / बाकी / शुल्क) और सभी फ़ैक्ट्रियों का अवलोकन पृष्ठ पर है; गोदाम स्टॉक में बाहर की मात्रा कभी शामिल नहीं होती।"),
 _vg("ownstock", "g_own", ["own stock", "own maal", "apna maal", "apna stock"], ["اپنا مال", "اپنا اسٹاک"], ["अपना माल", "अपना स्टॉक"],
     "Own Stock / Apna Maal — your own rock in stock at the factory, rock ground, powder in stock, bags and the own-trade summary (purchases, sales, receivable, payable). All figures are derived live from the gate entries, the party ledgers and Grinding & Production.",
     "Own Stock / Apna Maal — factory mein para apna pathar, pisa hua pathar, para powder, bag aur own-trade summary (khareed, farokht, lena, dena). Saare numbers gate entries, party khaton aur Grinding & Production se live bante hain.",
     "اپنا اسٹاک / اپنا مال — فیکٹری میں پڑا اپنا پتھر، پیسا گیا پتھر، پڑا پاؤڈر، تھیلے اور اپنی تجارت کا خلاصہ (خریداری، فروخت، لینا، دینا)۔ تمام اعداد اپنی تجارت، پسائی اور پیداوار سے زندہ بنتے ہیں۔",
     "अपना स्टॉक / अपना माल — फैक्टरी में पड़ा अपना रॉक, पिसा रॉक, पड़ा पाउडर, बोरे और अपने व्यापार का सारांश (ख़रीद, बिक्री, लेना, देना)। सभी आँकड़े अपने व्यापार, पिसाई और उत्पादन से लाइव बनते हैं।"),
 _vg("payments", "g_accounts", ["payments", "payment", "adaigi"], ["ادائیگیاں", "ادائیگی"], ["भुगतान"],
     "Payments — money IN (party paid us) and OUT (we paid the party) by cash, bank, online (JazzCash / Easypaisa / Raast) or cheque, with reference numbers. Steps: party, direction, amount, method, Save.",
     "Payments — raqam IN (party ne di) aur OUT (hum ne di) cash, bank, online (JazzCash / Easypaisa / Raast) ya cheque se, reference number ke saath. Steps: party, direction, amount, method, Save.",
     "ادائیگیاں — رقم اندر (پارٹی نے دی) اور باہر (ہم نے دی) نقد، بینک، آن لائن (JazzCash / Easypaisa / Raast) یا چیک سے، حوالہ نمبر کے ساتھ۔ اقدامات: پارٹی، سمت، رقم، طریقہ، محفوظ۔",
     "भुगतान — पैसा अंदर (पार्टी ने दिया) और बाहर (हमने दिया) नकद, बैंक, ऑनलाइन (JazzCash / Easypaisa / Raast) या चेक से, संदर्भ नंबर के साथ। चरण: पार्टी, दिशा, राशि, तरीका, सहेजें।"),
 _vg("expenses", "g_accounts", ["expenses", "expense ledger", "kharcha ledger"], ["اخراجات"], ["खर्च"],
     "Expense Ledger — factory expenses under Main/Sub heads (Tally-style), with Paid By (Owner / Manager / Other), method and approval flow for big manager cash expenses. Diesel and electricity amounts belong here.",
     "Expense Ledger — factory kharche Main/Sub heads ke neeche (Tally-style), Paid By (Owner / Manager / Other), method aur baray manager cash kharchon ki approval ke saath. Diesel aur bijli ki raqam yahin likhi jati hai.",
     "اخراجات لیجر — فیکٹری اخراجات مرکزی/ذیلی ہیڈز کے نیچے، ادا کنندہ (مالک / منیجر / دیگر)، طریقہ اور بڑے منیجر نقد اخراجات کی منظوری کے ساتھ۔ ڈیزل اور بجلی کی رقم یہیں لکھی جاتی ہے۔",
     "खर्च लेजर — फैक्टरी खर्च मुख्य/उप हेड के नीचे, देने वाला (मालिक / मैनेजर / अन्य), तरीका और बड़े मैनेजर नकद खर्चों की स्वीकृति के साथ। डीज़ल और बिजली की राशि यहीं लिखी जाती है।"),
 _vg("cashbook", "g_accounts", ["cash book", "cashbook", "day end", "day-end", "roznamcha"], ["کیش بک", "دن اختتام"], ["कैश बुक"],
     "Cash Book — the day's money by method (cash / bank / online / cheque), the Day-End Summary and the Bank Book with per-bank balances. Pick any date at the top.",
     "Cash Book — din ki raqam method ke hisaab se (cash / bank / online / cheque), Day-End Summary aur Bank Book har bank ke balance ke saath. Oopar se koi bhi date chunein.",
     "کیش بک — دن کی رقم طریقے کے حساب سے (نقد / بینک / آن لائن / چیک)، دن اختتام خلاصہ اور بینک بک ہر بینک کے بیلنس کے ساتھ۔ اوپر سے کوئی بھی تاریخ منتخب کریں۔",
     "कैश बुक — दिन का पैसा तरीके अनुसार (नकद / बैंक / ऑनलाइन / चेक), दिन अंत सारांश और बैंक बुक हर बैंक के शेष के साथ। ऊपर से कोई भी तिथि चुनें।"),
 _vg("cashinhand", "g_accounts", ["cash in hand", "cash in-hand", "handover", "holder cash"], ["ہاتھ میں نقد", "حوالگی"], ["हाथ में नकद"],
     "Cash in Hand — cash given to holders (manager/staff/others), what they spent, balance in hand, acknowledgements, cash counts (ginti), limits and approvals. A handover is a transfer, never an expense.",
     "Cash in Hand — holders (manager/staff/others) ko diya cash, un ka kharcha, haath mein balance, tasdeeq, cash ginti, limits aur approvals. Handover ek transfer hai, kharcha kabhi nahi.",
     "ہاتھ میں نقد — حاملین (منیجر/عملہ/دیگر) کو دیا نقد، ان کا خرچہ، ہاتھ میں بیلنس، تصدیق، نقد گنتی، حدیں اور منظوریاں۔ حوالگی ایک منتقلی ہے، خرچہ کبھی نہیں۔",
     "हाथ में नकद — धारकों (मैनेजर/स्टाफ़/अन्य) को दिया नकद, उनका खर्च, हाथ में शेष, पुष्टि, नकद गिनती, सीमाएँ और स्वीकृतियाँ। हैंडओवर एक स्थानांतरण है, खर्च कभी नहीं।"),
 _vg("cheques", "g_accounts", ["cheques", "cheque register", "cheque"], ["چیک رجسٹر", "چیک"], ["चेक"],
     "Cheque Register — post-dated cheques with due dates. Mark a cheque Cleared or Bounced — a bounce automatically reopens the party balance.",
     "Cheque Register — due date wale post-dated cheques. Cheque ko Cleared ya Bounced mark karein — bounce party ka balance khud dobara khol deta hai.",
     "چیک رجسٹر — تاریخ واجب والے مؤخر چیک۔ چیک کو کلیئر یا باؤنس نشان لگائیں — باؤنس پارٹی کا بیلنس خود دوبارہ کھول دیتا ہے۔",
     "चेक रजिस्टर — देय तिथि वाले पोस्ट-डेटेड चेक। चेक को क्लियर या बाउंस चिह्नित करें — बाउंस पार्टी का शेष ख़ुद दोबारा खोल देता है।"),
 _vg("reports", "g_accounts", ["reports", "report page", "p&l", "profit loss", "cost per ton"], ["رپورٹس", "رپورٹ"], ["रिपोर्ट"],
     "Reports — monthly Profit & Loss, Cost Per Ton (expenses and grinding income per ton, by head) and the Party Business Summary. Pick a period at the top of the Cost Per Ton section.",
     "Reports — mahana Profit & Loss, Cost Per Ton (fi ton kharcha aur pisai aamdani, head ke hisaab se) aur Party Business Summary. Cost Per Ton section ke oopar period chunein.",
     "رپورٹس — ماہانہ نفع نقصان، فی ٹن لاگت (فی ٹن خرچہ اور پسائی آمدنی، ہیڈ کے حساب سے) اور پارٹی کاروبار خلاصہ۔ فی ٹن لاگت حصے کے اوپر مدت منتخب کریں۔",
     "रिपोर्ट — मासिक लाभ-हानि, प्रति टन लागत (प्रति टन खर्च और पिसाई आय, हेड अनुसार) और पार्टी व्यापार सारांश। प्रति टन लागत भाग के ऊपर अवधि चुनें।"),
 _vg("phosdetail", "g_accounts", ["phosphate detail", "phosphate register", "register report", "roz ka register"], ["فاسفیٹ تفصیل", "رجسٹر"], ["फॉस्फेट विवरण", "रजिस्टर"],
     "Phosphate Detail — the daily paper register (Reports area): pick a date and see Rock In, Total Rock (its build-up — Previous Rock + Rock In — is shown under it), Day and Night bags (shift start 06:00-18:00 = Day, otherwise Night; entries without a start time count in the totals only), Wastage (the Settings wastage %, default 5% of the day's powder — a reporting figure, stock numbers do not change), Powder In Ton (bags x the kg per bag stamped on each record — the Bag weight defaults, 50 unless changed), Previous Powder, Dispatched (powder that left the godam that day), Balance Powder (= Previous + made - dispatched, matching the Warehouse) and Balance Rock (= Total Rock - Powder - Wastage: the register treats production as the rock consumption and runs day by day from the first record). Powder sold from an outside factory never appears here — it was never in the godam. A per-day Remark can be typed on the report, and a per-party table sits below. Print from the button on the page.",
     "Phosphate Detail — roz ka kagzi register (Reports wala hissa): date chunein aur dekhein Rock In, Total Rock (us ki tafseel — Pichla Pathar + Rock In — us ke neeche dikhti hai), Day aur Night bag (shift start 06:00-18:00 = Day, warna Night; jis entry ka start time na ho wo sirf totals mein ginti hai), Wastage (Settings ki wastage %, default powder ka 5% — ye sirf report ka number hai, stock numbers nahi badalte), Powder In Ton (bag x har record par lagi kg per bag — Bag weight defaults wali, 50 jab tak badli na ho), Pichla Powder, Rawana (us din godam se nikla powder), Balance Powder (= Pichla + bana - rawana, Warehouse se milta hai) aur Balance Rock (= Kul Pathar - Powder - Wastage: register production ko hi pathar ki khapat manta hai aur pehle record se roz-ba-roz chalta hai). Bahar wali factory se bika powder yahan kabhi nahi aata — wo godam mein tha hi nahi. Har din ka Remark report par likha ja sakta hai, neeche har party ki detail bhi hai. Page ke button se print hota hai.",
     "فاسفیٹ تفصیل — روز کا کاغذی رجسٹر (رپورٹس والا حصہ): تاریخ منتخب کریں اور دیکھیں پتھر اندر، کل پتھر (اس کی تفصیل — پچھلا پتھر + پتھر اندر — اس کے نیچے دکھتی ہے)، دن اور رات تھیلے (شفٹ شروع 06:00-18:00 = دن، ورنہ رات؛ جس انٹری کا شروع وقت نہ ہو وہ صرف کل میں گنتی ہے)، ضیاع (ترتیبات کی ضیاع %، پہلے سے پاؤڈر کا 5% — یہ صرف رپورٹ کا عدد ہے، اسٹاک اعداد نہیں بدلتے)، پاؤڈر ٹن (تھیلے × ہر ریکارڈ پر درج کلو فی تھیلا — تھیلے کے وزن کی طے شدہ قدر، 50 جب تک بدلی نہ ہو)، پچھلا پاؤڈر، روانہ (اس دن گودام سے نکلا پاؤڈر)، بیلنس پاؤڈر (= پچھلا + بنا − روانہ، گودام سے ملتا ہے) اور بیلنس پتھر (= کل پتھر − پاؤڈر − ضیاع: رجسٹر پیداوار کو ہی پتھر کی کھپت مانتا ہے اور پہلے ریکارڈ سے روز بہ روز چلتا ہے)۔ باہر والی فیکٹری سے بکا پاؤڈر یہاں کبھی نہیں آتا — وہ گودام میں تھا ہی نہیں۔ ہر دن کا تبصرہ رپورٹ پر لکھا جا سکتا ہے، نیچے ہر پارٹی کی تفصیل بھی ہے۔ صفحے کے بٹن سے پرنٹ ہوتا ہے۔",
     "फॉस्फेट विवरण — रोज़ का काग़ज़ी रजिस्टर (रिपोर्ट भाग): तिथि चुनें और देखें रॉक अंदर, कुल रॉक (उसका ब्योरा — पिछला रॉक + रॉक अंदर — उसके नीचे दिखता है), दिन और रात बोरे (शिफ़्ट शुरू 06:00-18:00 = दिन, वरना रात; जिस एंट्री का शुरू समय न हो वह केवल योग में गिनी जाती है), नुकसान (सेटिंग्स की नुकसान %, पहले से पाउडर का 5% — यह केवल रिपोर्ट का आँकड़ा है, स्टॉक आँकड़े नहीं बदलते), पाउडर टन (बोरे × हर रिकॉर्ड पर अंकित किलो प्रति बोरा — बोरे के वज़न की डिफ़ॉल्ट, 50 जब तक बदली न हो), पिछला पाउडर, रवाना (उस दिन गोदाम से निकला पाउडर), शेष पाउडर (= पिछला + बना − रवाना, गोदाम से मिलता है) और शेष रॉक (= कुल रॉक − पाउडर − नुकसान: रजिस्टर उत्पादन को ही रॉक की खपत मानता है और पहले रिकॉर्ड से रोज़-ब-रोज़ चलता है)। बाहर वाली फ़ैक्टरी से बिका पाउडर यहाँ कभी नहीं आता — वह गोदाम में था ही नहीं। हर दिन की टिप्पणी रिपोर्ट पर लिखी जा सकती है, नीचे हर पार्टी का विवरण भी है। पृष्ठ के बटन से प्रिंट होता है।"),
 _vg("workers", "g_workers", ["workers", "worker", "mazdoor", "theka worker"], ["مزدور"], ["मज़दूर"],
     "Workers — theka (per ton/bag) and salary workers, their earnings, payouts/advances and dues. Theka earning is automatic from powder OUT tons and production bags.",
     "Workers — theka (fi ton/bag) aur salary mazdoor, un ki kamai, payouts/advance aur due. Theka kamai powder OUT ton aur production bag se khud banti hai.",
     "مزدور — ٹھیکہ (فی ٹن/تھیلا) اور تنخواہ مزدور، ان کی کمائی، ادائیگیاں/ایڈوانس اور واجبات۔ ٹھیکہ کمائی پاؤڈر باہر ٹن اور پیداوار تھیلوں سے خود بنتی ہے۔",
     "मज़दूर — ठेका (प्रति टन/बोरा) और वेतन मज़दूर, उनकी कमाई, भुगतान/एडवांस और देय। ठेका कमाई पाउडर बाहर टन और उत्पादन बोरों से ख़ुद बनती है।"),
 _vg("departments", "g_workers", ["departments", "department", "shobay"], ["شعبے"], ["विभाग"],
     "Departments — shift times, weekend/off days and overtime rate per department. Overtime is added to worker dues automatically.",
     "Departments — har shobay ke shift time, weekend/off days aur overtime rate. Overtime mazdoor ke due mein khud shamil hota hai.",
     "شعبے — ہر شعبے کے شفٹ اوقات، ہفتہ وار چھٹی اور اوور ٹائم ریٹ۔ اوور ٹائم مزدور کے واجبات میں خود شامل ہوتا ہے۔",
     "विभाग — हर विभाग के शिफ़्ट समय, साप्ताहिक छुट्टी और ओवरटाइम दर। ओवरटाइम मज़दूर के देय में ख़ुद शामिल होता है।"),
 _vg("attendance", "g_workers", ["attendance", "hazri", "haazri", "biometric", "punch"], ["حاضری", "بایومیٹرک"], ["हाज़िरी", "बायोमेट्रिक"],
     "Attendance — daily presence, check-in/out and overtime, by hand or from biometric machines. Steps: 1) to enter by hand pick the worker, date and times and Save; 2) for a machine, register its serial here and set the shown address on the machine — punches then arrive by themselves; worker device codes are set on the Workers page.",
     "Attendance — roz ki hazri, check-in/out aur overtime, haath se ya biometric machines se. Steps: 1) haath se entry ke liye worker, date aur time chunein aur Save karein; 2) machine ke liye us ka serial yahan register karein aur diya gaya address machine par set karein — punches khud aati hain; worker ke device code Workers page par lagte hain.",
     "حاضری — روز کی حاضری، آمد/روانگی اور اوور ٹائم، ہاتھ سے یا بایومیٹرک مشینوں سے۔ اقدامات: 1) ہاتھ سے انٹری کے لیے مزدور، تاریخ اور وقت منتخب کریں اور محفوظ کریں؛ 2) مشین کے لیے اس کا سیریل یہاں درج کریں اور دیا گیا پتہ مشین پر مقرر کریں — حاضریاں خود آتی ہیں؛ مزدور کے ڈیوائس کوڈ مزدور صفحے پر لگتے ہیں۔",
     "हाज़िरी — रोज़ की हाज़िरी, आगमन/प्रस्थान और ओवरटाइम, हाथ से या बायोमेट्रिक मशीनों से। चरण: 1) हाथ से एंट्री के लिए मज़दूर, तिथि और समय चुनें और सहेजें; 2) मशीन के लिए उसका सीरियल यहाँ दर्ज करें और दिया गया पता मशीन पर सेट करें — हाज़िरियाँ ख़ुद आती हैं; मज़दूर के डिवाइस कोड मज़दूर पृष्ठ पर लगते हैं।"),
 _vg("leaves", "g_workers", ["leaves", "leave", "approvals", "chutti"], ["چھٹی", "منظوری"], ["छुट्टी", "स्वीकृति"],
     "Leave & Approvals — leave register (paid/unpaid) and owner approvals for overtime and attendance-correction requests. Approved unpaid leave cuts salary automatically.",
     "Leave & Approvals — chutti register (paid/unpaid) aur overtime / attendance correction darkhwaston ki owner approval. Approved unpaid chutti salary se khud katti hai.",
     "چھٹی و منظوری — چھٹی رجسٹر (معاوضہ/بلا معاوضہ) اور اوور ٹائم / حاضری درستگی درخواستوں کی مالک منظوری۔ منظور شدہ بلا معاوضہ چھٹی تنخواہ سے خود کٹتی ہے۔",
     "छुट्टी व स्वीकृति — छुट्टी रजिस्टर (वेतन/बिना वेतन) और ओवरटाइम / हाज़िरी सुधार अनुरोधों की मालिक स्वीकृति। स्वीकृत बिना वेतन छुट्टी वेतन से ख़ुद कटती है।"),
 _vg("alerts", "g_system", ["alerts", "whatsapp alerts", "reminders", "whatsapp"], ["الرٹس", "یاددہانی"], ["अलर्ट"],
     "Alerts — WhatsApp/SMS payment reminders and notifications. With the WhatsApp Cloud API set in Settings, alerts send by themselves; otherwise every alert has a one-tap wa.me button. Client payment proofs are confirmed here too. The sidebar shows a number badge on any section that has things waiting (proofs and unsent alerts here; the same badges sit on Warehouse, Cheques, Expenses, Leaves and Cash in Hand).",
     "Alerts — WhatsApp/SMS payment reminders aur notifications. Settings mein WhatsApp Cloud API laga ho to alerts khud jate hain; warna har alert ke saath one-tap wa.me button hai. Client payment proofs ki tasdeeq bhi yahin hoti hai. Sidebar mein jis section par kaam pending ho us par number wala badge aa jata hai (yahan proofs aur na-gaye alerts; waisay hi badge Warehouse, Cheques, Expenses, Leaves aur Cash in Hand par bhi lagte hain).",
     "الرٹس — واٹس ایپ/SMS ادائیگی یاددہانیاں اور اطلاعات۔ ترتیبات میں واٹس ایپ کلاؤڈ API لگا ہو تو الرٹ خود جاتے ہیں؛ ورنہ ہر الرٹ کے ساتھ ایک ٹیپ wa.me بٹن ہے۔ گاہک ادائیگی ثبوتوں کی تصدیق بھی یہیں ہوتی ہے۔",
     "अलर्ट — WhatsApp/SMS भुगतान रिमाइंडर और सूचनाएँ। सेटिंग्स में WhatsApp क्लाउड API लगा हो तो अलर्ट ख़ुद जाते हैं; वरना हर अलर्ट के साथ एक टैप wa.me बटन है। ग्राहक भुगतान सबूतों की पुष्टि भी यहीं होती है।"),
 _vg("recycle", "g_system", ["recycle", "deleted entries", "deleted", "restore"], ["حذف شدہ"], ["हटाई गई"],
     "Recycle / Deleted Entries — everything deleted anywhere lands here with an owner alert; restore brings it back. Notifications and the audit log are on this page too. Owner only.",
     "Recycle / Deleted Entries — kahin se bhi delete ki gayi har entry yahan aati hai, owner alert ke saath; restore se wapas aa jati hai. Notifications aur audit log bhi is page par hain. Sirf owner ke liye.",
     "ری سائیکل / حذف شدہ انٹریز — کہیں سے بھی حذف کی گئی ہر انٹری یہاں آتی ہے، مالک الرٹ کے ساتھ؛ بحال سے واپس آ جاتی ہے۔ اطلاعات اور آڈٹ لاگ بھی اس صفحے پر ہیں۔ صرف مالک کے لیے۔",
     "रीसायकल / हटाई गई एंट्री — कहीं से भी हटाई गई हर एंट्री यहाँ आती है, मालिक अलर्ट के साथ; बहाल से वापस आ जाती है। सूचनाएँ और ऑडिट लॉग भी इस पृष्ठ पर हैं। केवल मालिक के लिए।"),
 _vg("data", "g_system", ["data", "backup", "import export", "excel", "csv", "demo", "demo data"], ["ڈیٹا", "بیک اپ", "ڈیمو"], ["डेटा", "बैकअप", "डेमो"],
     "Data — one-click full backup (ZIP) and restore, CSV export/import, and Demo Data: load sample data to see every feature working, then delete it cleanly from the same card. Excel: every module page also has its own Excel bar (download / sample / upload with preview).",
     "Data — one-click full backup (ZIP) aur restore, CSV export/import, aur Demo Data: sample data load karke har feature chalta dekhein, phir usi card se saaf delete kar dein. Excel: har module page par us ki apni Excel bar bhi hai (download / sample / upload preview ke saath).",
     "ڈیٹا — ایک کلک مکمل بیک اپ (ZIP) اور بحالی، CSV برآمد/درآمد، اور ڈیمو ڈیٹا: نمونہ ڈیٹا لوڈ کر کے ہر فیچر چلتا دیکھیں، پھر اسی کارڈ سے صاف حذف کر دیں۔ ایکسل: ہر ماڈیول صفحے پر اس کی اپنی ایکسل بار بھی ہے (ڈاؤن لوڈ / نمونہ / پیش منظر کے ساتھ اپ لوڈ)۔",
     "डेटा — एक क्लिक पूर्ण बैकअप (ZIP) और बहाली, CSV निर्यात/आयात, और डेमो डेटा: नमूना डेटा लोड करके हर फ़ीचर चलता देखें, फिर उसी कार्ड से साफ़ हटा दें। एक्सेल: हर मॉड्यूल पृष्ठ पर उसकी अपनी एक्सेल बार भी है (डाउनलोड / नमूना / पूर्वावलोकन के साथ अपलोड)।"),
 _vg("logins", "g_system", ["logins", "users", "login banana", "staff access", "password"], ["لاگ ان", "صارفین"], ["लॉगिन", "उपयोगकर्ता"],
     "Logins & Users — create Owner / Manager / Staff (custom tick-box access) / Client logins. A client login sees only its own ledger, stock and balance. Owner only.",
     "Logins & Users — Owner / Manager / Staff (custom tick-box access) / Client logins banayein. Client login sirf apna khata, stock aur balance dekhta hai. Sirf owner ke liye.",
     "لاگ ان و صارفین — مالک / منیجر / عملہ (حسب مرضی نشان رسائی) / گاہک لاگ ان بنائیں۔ گاہک لاگ ان صرف اپنا کھاتہ، اسٹاک اور بیلنس دیکھتا ہے۔ صرف مالک کے لیے۔",
     "लॉगिन व उपयोगकर्ता — मालिक / मैनेजर / स्टाफ़ (कस्टम टिक पहुँच) / ग्राहक लॉगिन बनाएँ। ग्राहक लॉगिन केवल अपना खाता, स्टॉक और शेष देखता है। केवल मालिक के लिए।"),
 _vg("settings", "g_system", ["settings", "setting", "theme", "theme colour", "logo", "mill profile", "rang"], ["ترتیبات", "تھیم", "لوگو"], ["सेटिंग्स", "थीम", "लोगो"],
     "Settings — Mill Profile (name, phone, address, logo), theme colour for the whole system, WhatsApp/SMS keys, cash rules and limits, bank list with opening balances, powder-age limit and the database/backup folders. The logo and theme colour appear on the login screen too.",
     "Settings — Mill Profile (naam, phone, address, logo), poore system ka theme colour, WhatsApp/SMS keys, cash rules aur limits, bank list opening balances ke saath, powder-age limit aur database/backup folders. Logo aur theme colour login screen par bhi aata hai.",
     "ترتیبات — مل پروفائل (نام، فون، پتہ، لوگو)، پورے سسٹم کا تھیم رنگ، واٹس ایپ/SMS چابیاں، نقد اصول اور حدیں، بینک فہرست ابتدائی بیلنس کے ساتھ، پاؤڈر عمر حد اور ڈیٹابیس/بیک اپ فولڈر۔ لوگو اور تھیم رنگ لاگ ان اسکرین پر بھی آتا ہے۔",
     "सेटिंग्स — मिल प्रोफ़ाइल (नाम, फ़ोन, पता, लोगो), पूरे सिस्टम का थीम रंग, WhatsApp/SMS कुंजियाँ, नकद नियम और सीमाएँ, बैंक सूची प्रारंभिक शेष के साथ, पाउडर आयु सीमा और डेटाबेस/बैकअप फ़ोल्डर। लोगो और थीम रंग लॉगिन स्क्रीन पर भी आता है।"),
 _vg("help", "g_system", ["help", "madad"], ["مدد"], ["मदद"],
     "Help — short notes on starting the system, biometric machines, WhatsApp auto-send, voice entry, invoices and backups.",
     "Help — system start, biometric machines, WhatsApp auto-send, voice entry, invoice aur backup par mukhtasar notes.",
     "مدد — سسٹم شروع کرنا، بایومیٹرک مشینیں، واٹس ایپ خودکار بھیجنا، آواز انٹری، انوائس اور بیک اپ پر مختصر نوٹس۔",
     "मदद — सिस्टम शुरू करना, बायोमेट्रिक मशीनें, WhatsApp स्वतः भेजना, आवाज़ एंट्री, इनवॉइस और बैकअप पर संक्षिप्त नोट्स।"),
]

if IS_PC:
    # PC edition has no client portal — the guide must not offer it.
    for _e in _VIEW_GUIDE:
        if _e["view"] == "logins":
            _e["en"] = "Logins & Users — create Owner / Manager / Staff (custom tick-box access) logins. Owner only. (PC edition has no client portal.)"
            _e["roman"] = "Logins & Users — Owner / Manager / Staff (custom tick-box access) logins banayein. Sirf owner ke liye. (PC edition mein client portal nahi hota.)"
            _e["urt"] = "لاگ ان و صارفین — مالک / منیجر / عملہ (حسب مرضی نشان رسائی) لاگ ان بنائیں۔ صرف مالک کے لیے۔ (PC ایڈیشن میں گاہک پورٹل نہیں ہوتا۔)"
            _e["hit"] = "लॉगिन व उपयोगकर्ता — मालिक / मैनेजर / स्टाफ़ (कस्टम टिक पहुँच) लॉगिन बनाएँ। केवल मालिक के लिए। (PC संस्करण में ग्राहक पोर्टल नहीं होता।)"

_GUIDE_PAT = {
    "lat": ["kidhar", "kahan", "kaha hai", "kahan hai", "where is", "where does", "where",
            "ka page", "page kahan", "kaise use", "kaise istemal", "kaise kaam",
            "how to use", "how does", "use karun", "use karna", "istemal",
            "kholo", "open karo", "le jao", "dikhao", "dikha do", "kaise", "page", "entry",
            "banana", "banani", "banao", "rehnumai", "seekhna hai",
            "nahi mil", "nai mil", "mil nahi", "nahi mil raha", "nai mil raha",
            "nahi mil rahi", "dhoond", "dhund", "jaga", "jagah", "kahan se", "milega"],
    "ur": ["کدھر", "کہاں", "کہاں ہے", "کیسے استعمال", "کیسے کام", "کھولیں", "کیسے",
           "نہیں مل", "نہیں مل رہا", "نہیں مل رہی", "جگہ", "ڈھونڈ"],
    "hi": ["किधर", "कहाँ", "कहाँ है", "कैसे उपयोग", "कैसे काम", "खोलें",
           "नहीं मिल", "नहीं मिल रहा", "जगह", "ढूँढ"],
}

def _guide_match(lat, urn, raw):
    pat = (any(k in lat for k in _GUIDE_PAT["lat"])
           or any(k in urn for k in _GUIDE_PAT["ur"])
           or any(k in raw for k in _GUIDE_PAT["hi"]))
    if not pat:
        return None
    best, bl = None, -1
    for e in _VIEW_GUIDE:
        for a in e["lat"]:
            if a in lat and len(a) > bl:
                best, bl = e, len(a)
        for a in e["ur"]:
            if a and _norm_urdu(a) in urn and len(a) > bl:
                best, bl = e, len(a)
        for a in e["hi"]:
            if a and a in raw and len(a) > bl:
                best, bl = e, len(a)
    return best

_ASST_MENU = {
 "en": "I can help in 3 ways:\n\n1) Data questions — e.g. \"How many vehicles came today?\", \"Ahmed Traders balance?\", \"Last 7 days expenses?\", \"Who has the oldest unpaid balance?\", \"How many workers are present today?\"\n2) Reports — say \"Daily report bana do\", \"Monthly report\", \"Ahmed ki report\", \"Expense report\", \"Stock report\" or \"Workers report\" — I make a downloadable report.\n3) System guide — e.g. \"Attendance kidhar hai?\", \"Cash in Hand kaise use karun?\", \"Demo data kahan hai?\", \"Backup kaise lein?\"",
 "roman": "Mein 3 tarah se madad kar sakta hoon:\n\n1) Data ke sawal — masalan \"Aaj kitni gariyan aayin?\", \"Ahmed Traders ka baqaya?\", \"Pichle 7 din ka kharcha?\", \"Sab se purana udhaar kiska hai?\", \"Aaj kitne mazdoor hazir hain?\"\n2) Reports — kahein \"Daily report bana do\", \"Monthly report\", \"Ahmed ki report\", \"Expense report\", \"Stock report\" ya \"Workers report\" — mein download wali report bana deta hoon.\n3) System guide — masalan \"Attendance kidhar hai?\", \"Cash in Hand kaise use karun?\", \"Demo data kahan hai?\", \"Backup kaise lein?\"",
 "ur": "میں 3 طرح سے مدد کر سکتا ہوں:\n\n1) ڈیٹا کے سوالات — مثلاً \"آج کتنی گاڑیاں آئیں؟\"، \"احمد ٹریڈرز کا بقایا؟\"، \"پچھلے 7 دن کا خرچہ؟\"، \"سب سے پرانا ادھار کس کا ہے؟\"، \"آج کتنے مزدور حاضر ہیں؟\"\n2) رپورٹس — کہیں \"روزانہ رپورٹ بنا دو\"، \"ماہانہ رپورٹ\"، \"احمد کی رپورٹ\"، \"خرچہ رپورٹ\"، \"اسٹاک رپورٹ\" یا \"مزدور رپورٹ\" — میں ڈاؤن لوڈ والی رپورٹ بنا دیتا ہوں۔\n3) سسٹم رہنمائی — مثلاً \"حاضری کدھر ہے؟\"، \"کیش ان ہینڈ کیسے استعمال کروں؟\"، \"ڈیمو ڈیٹا کہاں ہے؟\"، \"بیک اپ کیسے لیں؟\"",
 "hi": "मैं 3 तरह से मदद कर सकता हूँ:\n\n1) डेटा के सवाल — जैसे \"आज कितनी गाड़ियाँ आईं?\", \"अहमद ट्रेडर्स का बकाया?\", \"पिछले 7 दिन का खर्च?\", \"सबसे पुराना उधार किसका है?\", \"आज कितने मज़दूर उपस्थित हैं?\"\n2) रिपोर्ट — कहें \"रोज़ाना रिपोर्ट बना दो\", \"मासिक रिपोर्ट\", \"अहमद की रिपोर्ट\", \"खर्च रिपोर्ट\", \"स्टॉक रिपोर्ट\" या \"मज़दूर रिपोर्ट\" — मैं डाउनलोड वाली रिपोर्ट बना देता हूँ।\n3) सिस्टम गाइड — जैसे \"हाज़िरी किधर है?\", \"कैश इन हैंड कैसे उपयोग करूँ?\", \"डेमो डेटा कहाँ है?\", \"बैकअप कैसे लें?\"",
}


# G2/G3 labels for reports and ranged answers (easy wording, 4 languages)
_L2 = {
 "en": {"balance": "Balance", "owes_us": "party owes us", "we_owe": "we owe the party", "clear": "clear",
        "rock_waiting": "Rock waiting", "powder_ready": "Powder ready", "bags_w": "bags",
        "last_entries": "Last entries", "r_daily": "Daily Report", "r_monthly": "Monthly Report",
        "r_party": "Party Report", "r_expense": "Expense Report", "r_stock": "Stock Report",
        "r_workers": "Workers Report", "vehicles": "Vehicles", "rock_in": "Rock IN",
        "powder_out": "Powder OUT", "ground": "Ground", "bags_l": "Bags",
        "cash_in": "Cash IN", "cash_out": "Cash OUT", "expenses_l": "Expenses",
        "income": "Income", "grinding_inc": "Grinding income", "sales_inc": "Sales income",
        "costs": "Costs", "profit": "Profit", "by_head": "Expenses by head",
        "top_parties": "Top parties by business", "total": "Total", "own": "Own",
        "clients": "Clients", "rock": "Rock", "powder": "Powder",
        "earned": "Earned", "paid": "Paid", "due": "Due",
        "range_today": "Today", "range_month": "This month",
        "range_yesterday": "Yesterday", "range_last7": "Last 7 days", "range_week": "This week",
        "range_lastmonth": "Last month", "pres_today": "Workers present today",
        "pres_none": "No attendance is marked for today yet.",
        "due_t": "Machine maintenance due", "no_due": "No machine service is due in the next 7 days.",
        "oldest": "Oldest unpaid balance", "days_w": "days", "top_stock": "Biggest powder stock",
        "no_stock": "No party has powder stock right now.", "month": "Month",
        "bags_made": "Bags made", "per_ton": "per ton", "kind_theka": "theka", "kind_salary": "salary",
        "pd_title": "Phosphate Detail", "total_stock": "Total Stock", "total_rock": "Total Rock",
        "day_w": "Day", "night_w": "Night", "wastage_w": "Wastage", "powder_in": "Powder In",
        "prev_powder": "Previous Powder", "bal_powder": "Balance Powder", "bal_rock": "Balance Rock",
        "dispatched_w": "Dispatched", "prev_rock": "Previous Rock",
        "powder_bought": "Powder bought"},
 "roman": {"balance": "Baqaya", "owes_us": "party ne dene hain", "we_owe": "hum ne dene hain", "clear": "khata saaf hai",
        "rock_waiting": "Pathar intezaar mein", "powder_ready": "Powder tayyar", "bags_w": "bag",
        "last_entries": "Aakhri entries", "r_daily": "Roz ki Report", "r_monthly": "Mahine ki Report",
        "r_party": "Party Report", "r_expense": "Kharcha Report", "r_stock": "Stock Report",
        "r_workers": "Mazdoor Report", "vehicles": "Gariyan", "rock_in": "Maal IN",
        "powder_out": "Maal OUT", "ground": "Pisai", "bags_l": "Bag",
        "cash_in": "Cash aaya", "cash_out": "Cash gaya", "expenses_l": "Kharcha",
        "income": "Aamdani", "grinding_inc": "Pisai aamdani", "sales_inc": "Farokht aamdani",
        "costs": "Kharche", "profit": "Munafa", "by_head": "Kharcha head ke hisaab se",
        "top_parties": "Top parties (business ke hisaab se)", "total": "Kul", "own": "Apna",
        "clients": "Gahak", "rock": "Pathar", "powder": "Powder",
        "earned": "Kamai", "paid": "Ada kiya", "due": "Due",
        "range_today": "Aaj", "range_month": "Is mahine",
        "range_yesterday": "Kal (guzishta)", "range_last7": "Pichle 7 din", "range_week": "Is hafte",
        "range_lastmonth": "Pichle mahine", "pres_today": "Aaj hazir mazdoor",
        "pres_none": "Aaj ki hazri abhi nahi lagi.",
        "due_t": "Machine service due", "no_due": "Agle 7 din mein koi machine service due nahi.",
        "oldest": "Sab se purana udhaar", "days_w": "din", "top_stock": "Sab se zyada powder stock",
        "no_stock": "Is waqt kisi party ke paas powder stock nahi.", "month": "Mahina",
        "bags_made": "Bag bane", "per_ton": "fi ton", "kind_theka": "theka", "kind_salary": "salary",
        "pd_title": "Phosphate Detail", "total_stock": "Kul Stock", "total_rock": "Kul Pathar",
        "day_w": "Din", "night_w": "Raat", "wastage_w": "Wastage", "powder_in": "Powder Aaya",
        "prev_powder": "Pichla Powder", "bal_powder": "Balance Powder", "bal_rock": "Balance Pathar",
        "dispatched_w": "Rawana", "prev_rock": "Pichla Pathar",
        "powder_bought": "Powder kharida"},
 "ur": {"balance": "بقایا", "owes_us": "پارٹی نے دینے ہیں", "we_owe": "ہم نے دینے ہیں", "clear": "کھاتہ صاف ہے",
        "rock_waiting": "پتھر انتظار میں", "powder_ready": "پاؤڈر تیار", "bags_w": "تھیلے",
        "last_entries": "آخری انٹریز", "r_daily": "روز کی رپورٹ", "r_monthly": "مہینے کی رپورٹ",
        "r_party": "پارٹی رپورٹ", "r_expense": "خرچہ رپورٹ", "r_stock": "اسٹاک رپورٹ",
        "r_workers": "مزدور رپورٹ", "vehicles": "گاڑیاں", "rock_in": "مال اندر",
        "powder_out": "مال باہر", "ground": "پسائی", "bags_l": "تھیلے",
        "cash_in": "نقد آیا", "cash_out": "نقد گیا", "expenses_l": "خرچہ",
        "income": "آمدنی", "grinding_inc": "پسائی آمدنی", "sales_inc": "فروخت آمدنی",
        "costs": "اخراجات", "profit": "منافع", "by_head": "خرچہ ہیڈ کے حساب سے",
        "top_parties": "بڑی پارٹیاں (کاروبار کے حساب سے)", "total": "کل", "own": "اپنا",
        "clients": "گاہک", "rock": "پتھر", "powder": "پاؤڈر",
        "earned": "کمائی", "paid": "ادا کیا", "due": "بقایا",
        "range_today": "آج", "range_month": "اس مہینے",
        "range_yesterday": "کل (گزشتہ)", "range_last7": "پچھلے 7 دن", "range_week": "اس ہفتے",
        "range_lastmonth": "پچھلے مہینے", "pres_today": "آج حاضر مزدور",
        "pres_none": "آج کی حاضری ابھی نہیں لگی۔",
        "due_t": "مشین سروس واجب", "no_due": "اگلے 7 دن میں کوئی مشین سروس واجب نہیں۔",
        "oldest": "سب سے پرانا ادھار", "days_w": "دن", "top_stock": "سب سے زیادہ پاؤڈر اسٹاک",
        "no_stock": "اس وقت کسی پارٹی کے پاس پاؤڈر اسٹاک نہیں۔", "month": "مہینہ",
        "bags_made": "تھیلے بنے", "per_ton": "فی ٹن", "kind_theka": "ٹھیکہ", "kind_salary": "تنخواہ",
        "pd_title": "فاسفیٹ تفصیل", "total_stock": "کل اسٹاک", "total_rock": "کل پتھر",
        "day_w": "دن", "night_w": "رات", "wastage_w": "ضیاع", "powder_in": "پاؤڈر آیا",
        "prev_powder": "پچھلا پاؤڈر", "bal_powder": "بیلنس پاؤڈر", "bal_rock": "بیلنس پتھر",
        "dispatched_w": "روانہ", "prev_rock": "پچھلا پتھر",
        "powder_bought": "پاؤڈر خریدا"},
 "hi": {"balance": "बकाया", "owes_us": "पार्टी को देने हैं", "we_owe": "हमें देने हैं", "clear": "खाता साफ़ है",
        "rock_waiting": "रॉक प्रतीक्षा में", "powder_ready": "पाउडर तैयार", "bags_w": "बोरे",
        "last_entries": "अंतिम एंट्रियाँ", "r_daily": "रोज़ की रिपोर्ट", "r_monthly": "महीने की रिपोर्ट",
        "r_party": "पार्टी रिपोर्ट", "r_expense": "खर्च रिपोर्ट", "r_stock": "स्टॉक रिपोर्ट",
        "r_workers": "मज़दूर रिपोर्ट", "vehicles": "वाहन", "rock_in": "माल अंदर",
        "powder_out": "माल बाहर", "ground": "पिसाई", "bags_l": "बोरे",
        "cash_in": "नकद आया", "cash_out": "नकद गया", "expenses_l": "खर्च",
        "income": "आय", "grinding_inc": "पिसाई आय", "sales_inc": "बिक्री आय",
        "costs": "लागत", "profit": "मुनाफ़ा", "by_head": "हेड अनुसार खर्च",
        "top_parties": "बड़ी पार्टियाँ (व्यापार अनुसार)", "total": "कुल", "own": "अपना",
        "clients": "ग्राहक", "rock": "रॉक", "powder": "पाउडर",
        "earned": "कमाई", "paid": "दिया", "due": "देय",
        "range_today": "आज", "range_month": "इस महीने",
        "range_yesterday": "कल (बीता)", "range_last7": "पिछले 7 दिन", "range_week": "इस हफ़्ते",
        "range_lastmonth": "पिछले महीने", "pres_today": "आज उपस्थित मज़दूर",
        "pres_none": "आज की हाज़िरी अभी नहीं लगी।",
        "due_t": "मशीन सेवा देय", "no_due": "अगले 7 दिनों में कोई मशीन सेवा देय नहीं।",
        "oldest": "सबसे पुराना उधार", "days_w": "दिन", "top_stock": "सबसे ज़्यादा पाउडर स्टॉक",
        "no_stock": "इस समय किसी पार्टी के पास पाउडर स्टॉक नहीं।", "month": "महीना",
        "bags_made": "बोरे बने", "per_ton": "प्रति टन", "kind_theka": "ठेका", "kind_salary": "वेतन",
        "pd_title": "फॉस्फेट विवरण", "total_stock": "कुल स्टॉक", "total_rock": "कुल रॉक",
        "day_w": "दिन", "night_w": "रात", "wastage_w": "नुकसान", "powder_in": "पाउडर आया",
        "prev_powder": "पिछला पाउडर", "bal_powder": "शेष पाउडर", "bal_rock": "शेष रॉक",
        "dispatched_w": "रवाना", "prev_rock": "पिछला रॉक",
        "powder_bought": "पाउडर ख़रीदा"},
}

def _match_party(con, lat, urn):
    """Full-name match first, then distinctive-word partial match
    (case/space-insensitive) — same rules as the data core."""
    parties = con.execute("SELECT * FROM parties ORDER BY LENGTH(name) DESC").fetchall()
    lat_pad = " " + lat + " "
    lat_toks = set(lat.split())
    for p in parties:
        name_lat = (p["name"] or "").lower()
        name_urn = _norm_urdu(p["name"] or "")
        if (name_lat and (" " + name_lat + " ") in lat_pad) or (name_urn and _has_ar(name_urn) and name_urn in urn):
            return p
    best, best_score = None, 0
    for p in parties:
        _nm = "".join(ch if ch.isalnum() else " " for ch in (p["name"] or "").lower())
        words = [w for w in _nm.split() if len(w) >= 3]
        if not words:
            continue
        hits = sum(1 for w in words if w in lat_toks)
        score = hits + (1 if words[0] in lat_toks else 0)
        if hits and score > best_score:
            best, best_score = p, score
    return best

def _rs(n):
    return "Rs " + format(float(n or 0), ",.0f")

# ------------------------------------------------------------- G2 reports ---
def _build_report(con, kind, party, lang):
    L = _L2[lang]
    import datetime as _d
    td = _d.date.today()
    if kind == "party":
        ents, bal = party_ledger(con, party["id"])
        st = party_stock(con, party["id"])
        who = L["owes_us"] if bal > 0 else (L["we_owe"] if bal < 0 else L["clear"])
        lines = ["%s: %s" % (L["r_party"], party["name"]),
                 "%s: %s (%s)" % (L["balance"], _rs(abs(bal)), who),
                 "%s: %g t · %s: %g t (%d %s)" % (L["rock_waiting"], st["rock_waiting_t"],
                                                  L["powder_ready"], st["powder_ready_t"],
                                                  st["bags_ready"], L["bags_w"]),
                 "", L["last_entries"] + ":"]
        for e in ents[-8:]:
            amt = float(e["debit"] or 0) - float(e["credit"] or 0)
            sign = "+" if amt > 0 else ("-" if amt < 0 else "")
            lines.append("%s  %s  %s%s  -> %s" % (e["date"] or "-", (e["desc"] or "")[:46],
                                                  sign, _rs(abs(amt)), _rs(e["balance"])))
        return "\n".join(lines), "party-report-%d.txt" % party["id"]
    if kind == "monthly":
        month = td.isoformat()[:7]
        p = pnl(con, month)
        bags = con.execute("SELECT COALESCE(SUM(bags),0) s FROM production WHERE date LIKE ?",
                           (month + "%",)).fetchone()["s"]
        first = td.replace(day=1).isoformat()
        c = cost_per_ton(con, first, td.isoformat())
        lines = ["%s — %s: %s" % (L["r_monthly"], L["month"], month),
                 "%s: %g t · %s: %d" % (L["ground"], c["tons_ground"], L["bags_made"], bags),
                 "%s: %s (%s %s + %s %s)" % (L["income"], _rs(p["income"]), L["grinding_inc"],
                                             _rs(p["grinding_income"]), L["sales_inc"], _rs(p["sales_income"])),
                 "%s: %s" % (L["costs"], _rs(p["costs"])),
                 "%s: %s" % (L["profit"], _rs(p["profit"])),
                 "", L["by_head"] + ":"]
        for h, v in sorted(c["expenses_by_head"].items(), key=lambda kv: -kv[1]):
            lines.append("  %s: %s" % (h, _rs(v)))
        lines += ["", L["top_parties"] + ":"]
        for b in party_business(con)[:5]:
            lines.append("  %s: %s" % (b["party"], _rs(b["net"])))
        return "\n".join(lines), "monthly-report-%s.txt" % month
    if kind == "expense":
        month = td.isoformat()[:7]
        first = td.replace(day=1).isoformat()
        c = cost_per_ton(con, first, td.isoformat())
        lines = ["%s — %s: %s" % (L["r_expense"], L["month"], month),
                 "%s: %s" % (L["total"], _rs(c["expenses"])), "", L["by_head"] + ":"]
        for h, v in sorted(c["expenses_by_head"].items(), key=lambda kv: -kv[1]):
            lines.append("  %s: %s" % (h, _rs(v)))
        return "\n".join(lines), "expense-report-%s.txt" % month
    if kind == "stock":
        o = own_stock(con)
        wh = warehouse(con)
        cr = cp = cb = 0.0
        for prow in con.execute("SELECT id FROM parties"):
            st = party_stock(con, prow["id"])
            cr += st["rock_waiting_t"]; cp += st["powder_ready_t"]; cb += st["bags_ready"]
        lines = ["%s" % L["r_stock"],
                 "%s — %s: %g t · %s: %g t · %s: %d" % (L["own"], L["rock"], o["rock_left_t"],
                                                        L["powder"], o["powder_left_t"],
                                                        L["bags_l"], wh["own"]["bags_ready"]),
                 "%s — %s: %g t · %s: %g t · %s: %d" % (L["clients"], L["rock"], round(cr, 3),
                                                       L["powder"], round(cp, 3),
                                                       L["bags_l"], int(cb))]
        return "\n".join(lines), "stock-report.txt"
    if kind == "workers":
        lines = ["%s" % L["r_workers"]]
        tot = 0.0
        for w in con.execute("SELECT * FROM workers ORDER BY name"):
            d = worker_dues(con, w["id"])
            due = float(d.get("due", 0) or 0)
            tot += due
            kind_l = L["kind_theka"] if w["kind"] == "theka" else L["kind_salary"]
            lines.append("%s (%s): %s %s · %s %s · %s %s" % (
                w["name"], kind_l, L["earned"], _rs(d.get("earned", 0)),
                L["paid"], _rs(d.get("paid", 0)), L["due"], _rs(due)))
        lines.append("%s %s: %s" % (L["total"], L["due"], _rs(tot)))
        return "\n".join(lines), "workers-report.txt"
    if kind == "phosdetail":
        pd = phosphate_detail(con, td.isoformat())
        lines = ["%s — %s" % (L["pd_title"], pd["date"]),
                 "%s: %g t · %s: %g t (%s %g + %s %g)" % (
                     L["rock_in"], pd["rock_in_t"],
                     L["total_rock"], pd["total_rock_t"],
                     L["prev_rock"], pd["total_stock_rock_t"],
                     L["rock_in"], pd["rock_in_t"]),
                 "%s: %d · %s: %d" % (L["day_w"], pd["bags_day"], L["night_w"],
                                      pd["bags_night"]),
                 "%s: %g t · %s: %g t (%g%%)" % (L["powder_in"], pd["powder_in_t"],
                                                 L["wastage_w"], pd["wastage_t"], pd["wastage_pct"]),
                 "%s: %g t · %s: %g t · %s: %g t" % (L["prev_powder"], pd["prev_powder_t"],
                                                     L["dispatched_w"], pd["dispatched_t"],
                                                     L["bal_powder"], pd["balance_powder_t"]),
                 "%s: %g t" % (L["bal_rock"], pd["balance_rock_t"])]
        if pd["bought_bags"]:
            lines.append("%s: %d %s" % (L["powder_bought"], pd["bought_bags"],
                                        L["bags_l"]))
        if pd["remark"]:
            lines.append("Remarks: " + pd["remark"])
        return "\n".join(lines), "phosphate-detail-%s.txt" % pd["date"]
    # daily
    d = day_end(con, td.isoformat())
    cbk = d["cashbook"]
    lines = ["%s — %s" % (L["r_daily"], d["date"]),
             "%s: IN %d · OUT %d" % (L["vehicles"], d["trips_in"], d["trips_out"]),
             "%s: %g t · %s: %g t" % (L["rock_in"], d["rock_in_t"], L["powder_out"], d["powder_out_t"]),
             "%s: %g t · %s: %d" % (L["ground"], d["ground_t"], L["bags_l"], d["bags"]),
             "%s: %s · %s: %s" % (L["cash_in"], _rs(cbk["total_in"]), L["cash_out"], _rs(cbk["total_out"])),
             "%s: %s" % (L["expenses_l"], _rs(d["expense_total"]))]
    return "\n".join(lines), "daily-report-%s.txt" % d["date"]

def _report_kind(con, lat, urn, raw):
    is_rep = ("report" in lat) or ("رپورٹ" in urn) or ("रिपोर्ट" in raw)
    if not is_rep:
        return None
    mp = _match_party(con, lat, urn)
    if mp is not None:
        return ("party", mp)
    def hit(g):
        return _asst_hit(lat, urn, raw, g)
    if hit("phosdetail"):
        return ("phosdetail", None)
    if hit("expenses"):
        return ("expense", None)
    if hit("stock"):
        return ("stock", None)
    if hit("workers"):
        return ("workers", None)
    if hit("month") or "monthly" in lat or "मासिक" in raw:
        return ("monthly", None)
    return ("daily", None)

# ------------------------------------------------------- G3 ranged/special ---
def _range_of(lat, urn, raw):
    toks = {t.strip("?.,!") for t in lat.split()}
    if (any(k in lat for k in ("pichle mahine", "pichla mahina", "last month"))
            or _norm_urdu("پچھلے مہینے") in urn or "पिछले महीने" in raw):
        return "lastmonth"
    if (any(k in lat for k in ("pichle 7 din", "pichlay 7 din", "last 7 days",
                               "pichle haftay", "pichle hafte", "pichla hafta", "last week"))
            or _norm_urdu("پچھلے 7 دن") in urn or _norm_urdu("پچھلے ہفتے") in urn
            or "पिछले 7 दिन" in raw or "पिछले हफ़्ते" in raw):
        return "last7"
    if (any(k in lat for k in ("is hafte", "is haftay", "this week"))
            or _norm_urdu("اس ہفتے") in urn or "इस हफ़्ते" in raw):
        return "week"
    if "yesterday" in lat or "kal" in toks or _norm_urdu("کل") in urn or "कल" in raw:
        return "yesterday"
    return None

def _range_dates(kind):
    import datetime as _d
    td = _d.date.today()
    if kind == "yesterday":
        return [td - _d.timedelta(days=1)]
    if kind == "last7":
        return [td - _d.timedelta(days=i) for i in range(6, -1, -1)]
    if kind == "week":
        mon = td - _d.timedelta(days=td.weekday())
        return [mon + _d.timedelta(days=i) for i in range((td - mon).days + 1)]
    if kind == "lastmonth":
        first_this = td.replace(day=1)
        last_prev = first_this - _d.timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        return [first_prev + _d.timedelta(days=i) for i in range((last_prev - first_prev).days + 1)]
    return [td]

def _special_answer(con, lat, urn, raw, lang):
    L = _L2[lang]
    def hit(g):
        return _asst_hit(lat, urn, raw, g)
    # oldest unpaid balance (ageing walk, same as the dashboard)
    if (any(k in lat for k in ("purana udhaar", "purana udhar", "oldest", "payment nahi ki",
                               "abhi tak payment nahi", "sab se purana"))
            or _norm_urdu("پرانا ادھار") in urn or _norm_urdu("ادائیگی نہیں کی") in urn
            or "पुराना उधार" in raw or "भुगतान नहीं किया" in raw):
        import datetime as _d
        best = None
        for p in con.execute("SELECT * FROM parties"):
            ents, bal = party_ledger(con, p["id"])
            if bal <= 0:
                continue
            oldest = None
            for e in ents:
                if e["balance"] > 0 and e["date"]:
                    oldest = e["date"]
                    break
            if oldest:
                try:
                    age = (_d.date.today() - _d.date.fromisoformat(oldest)).days
                except Exception:
                    continue
                if best is None or age > best[2]:
                    best = (p["name"], bal, age)
        if best is None:
            return _ASST[lang]["biggest_none"]
        return "%s: %s — %s (%d %s)" % (L["oldest"], best[0], _rs(best[1]), best[2], L["days_w"])
    # workers present today
    if hit("workers") and ("hazir" in lat or "present" in lat or "حاضر" in urn
                            or "उपस्थित" in raw or "हाज़िर" in raw):
        rows = con.execute(
            "SELECT w.name FROM attendance a JOIN workers w ON w.id=a.worker_id "
            "WHERE a.date=? AND a.present=1 ORDER BY w.name", (today(),)).fetchall()
        if not rows:
            return L["pres_none"]
        return "%s: %d — %s" % (L["pres_today"], len(rows), ", ".join(r["name"] for r in rows))
    # machine service due
    _mach = ("machine" in lat or "مشین" in urn or "मशीन" in raw)
    _dueq = (any(k in lat for k in ("due", "service", "kab", "next"))
             or "سروس" in urn or "सर्विस" in raw or "واجب" in urn)
    if _mach and _dueq:
        rows = con.execute(
            "SELECT me.next_due, me.work_type, m.name machine_name FROM machine_entries me "
            "LEFT JOIN machines m ON m.id=me.machine_id "
            "WHERE me.next_due!='' AND me.next_due<=date('now','+7 days') ORDER BY me.next_due").fetchall()
        if not rows:
            return L["no_due"]
        return L["due_t"] + ": " + "; ".join(
            "%s — %s (%s)" % (r["machine_name"] or "?", r["work_type"], r["next_due"]) for r in rows)
    # biggest powder stock holder
    if hit("stock") and hit("biggest"):
        best, bb = None, 0.0
        for p in con.execute("SELECT * FROM parties"):
            st = party_stock(con, p["id"])
            if st["powder_ready_t"] > bb:
                best, bb = (p["name"], st), st["powder_ready_t"]
        if best is None:
            return L["no_stock"]
        return "%s: %s — %g t (%d %s)" % (L["top_stock"], best[0], best[1]["powder_ready_t"],
                                          best[1]["bags_ready"], L["bags_w"])
    # phosphate detail (register) for today — or yesterday when asked
    if hit("phosdetail"):
        import datetime as _d2
        ds = today()
        if _range_of(lat, urn, raw) == "yesterday":
            ds = (_d2.date.today() - _d2.timedelta(days=1)).isoformat()
        pd = phosphate_detail(con, ds)
        ans = ("%s (%s): %s %g t · %s %g t (%s %g + %s %g) · %s %d / %s %d · "
               "%s %g t (%g%%) · %s %g t · %s %g t · %s %g t · %s %g t · %s %g t" % (
            L["pd_title"], ds,
            L["rock_in"], pd["rock_in_t"],
            L["total_rock"], pd["total_rock_t"],
            L["prev_rock"], pd["total_stock_rock_t"],
            L["rock_in"], pd["rock_in_t"],
            L["day_w"], pd["bags_day"], L["night_w"], pd["bags_night"],
            L["wastage_w"], pd["wastage_t"], pd["wastage_pct"],
            L["powder_in"], pd["powder_in_t"],
            L["prev_powder"], pd["prev_powder_t"],
            L["dispatched_w"], pd["dispatched_t"],
            L["bal_powder"], pd["balance_powder_t"],
            L["bal_rock"], pd["balance_rock_t"]))
        if pd["bought_bags"]:
            ans += " · %s %d %s" % (L["powder_bought"], pd["bought_bags"],
                                    L["bags_l"])
        return ans
    # ranged totals from day_end (identical sources as the Day-End Summary)
    rng = _range_of(lat, urn, raw)
    # a payment-MOVEMENT question ("kal kitne paisay aaye") is not a
    # ranged day summary — the payments intent in the data core owns it
    _pmv = (("paisay" in lat) or ("پیسے" in urn) or ("पैसे" in raw)) and any(
        v in lat for v in ("aayi", "aaye", "aaya", "diye", "diya", "bheje", "mile", "mila"))
    if rng and not _pmv and (hit("vehicles") or hit("production") or hit("expenses") or hit("cash") or hit("stock")):
        rin = rout = gr = 0.0
        bags = 0
        cin = cout = exp = 0.0
        for d in _range_dates(rng):
            de = day_end(con, d.isoformat())
            rin += de["rock_in_t"]; rout += de["powder_out_t"]; gr += de["ground_t"]
            bags += de["bags"]; exp += de["expense_total"]
            cin += de["cashbook"]["total_in"]; cout += de["cashbook"]["total_out"]
        return "%s: %s %g t · %s %g t · %s %g t · %s %d · %s %s · %s %s · %s %s" % (
            L["range_" + rng], L["rock_in"], rin, L["powder_out"], rout, L["ground"], gr,
            L["bags_l"], bags, L["cash_in"], _rs(cin), L["cash_out"], _rs(cout),
            L["expenses_l"], _rs(exp))
    return None

# ------------------------------------------------- assistant KB (full) ---
# Full-system knowledge base: the assistant knows the WHOLE software —
# every setting and exactly where it is set, every khata/expense head,
# the data flow of every entry (save ke baad kahan jati hai), and the
# standing rules. Texts are authored per language with Roman Urdu as a
# first-class, conversational variant: the reply mirrors the language
# and style of the question (script-based detection in _asst_lang).
_KB_FLOW_PAT = {
    "lat": ["kahan jati hai", "kahan jata hai", "kahan jati", "kahan jata",
            "kahan jay gi", "kahan jayegi", "kahan jay ga", "kidhar jati",
            "kidhar jata", "save ke baad", "save karne ke baad",
            "save honay ke baad", "save hone ke baad", "save kay baad", "save baad",
            "add hony", "add honay", "add hone ke baad", "entry ke baad",
            "entry kay baad", "kya hota hai", "kya hoga", "asar parta",
            "asar padta", "asar dalti", "asar dalta", "data flow",
            "kahan lagti hai", "kahan lagta hai", "kahan add hoti",
            "kahan show hoti", "kahan nazar ati", "kahan nazar ata",
            "kahan dikhti", "jati hai kahan", "jata hai kahan"],
    "ur": ["کہاں جاتی", "کہاں جاتا", "محفوظ کے بعد", "محفوظ کرنے کے بعد",
           "کیا ہوتا ہے", "کہاں لگتی", "کہاں لگتا", "اثر پڑتا"],
    "hi": ["कहाँ जाती", "कहाँ जाता", "सेव के बाद", "सेव करने के बाद",
           "क्या होता है", "कहाँ लगती", "असर पड़ता"],
}
_KB_DEF_PAT = {
    "lat": ["kya hai", "kya hota", "matlab kya", "kya matlab", "meaning",
            "kisay kehte", "kise kehte", "samjhao", "samjha do"],
    "ur": ["کیا ہے", "مطلب کیا", "کسے کہتے"],
    "hi": ["क्या है", "मतलब क्या", "किसे कहते"],
}
_KB_LOC_PAT = {
    "lat": ["kidhar", "kdr", "kahan", "kaha hai", "nahi mil", "nai mil",
            "mil nahi", "nahi mil raha", "nai mil raha", "nahi mil rahi",
            "nai mil rahi", "dhoond", "dhund", "jaga", "jagah",
            "page kahan", "milega", "kahan se", "where", "page"],
    "ur": ["کدھر", "کہاں", "نہیں مل", "جگہ", "ڈھونڈ"],
    "hi": ["किधर", "कहाँ", "नहीं मिल", "जगह", "ढूँढ"],
}

def _K(kid, kind, view, kw, label, q, text, dyn=None, need=None):
    return {"id": kid, "kind": kind, "view": view, "kw": kw,
            "label": label, "q": q, "text": text, "dyn": dyn, "need": need}

def _L(en, roman, ur, hi):
    return {"en": en, "roman": roman, "ur": ur, "hi": hi}

_KB = [
 # ---------------------------------------------------------- settings ---
 _K("set_wastage", "setting", "settings",
    {"lat": ["wastage", "waste percentage", "waste %", "zaya", "zaaya", "wastage kitna"],
     "ur": ["ضیاع", "ویسٹیج", "ضیاع فیصد"], "hi": ["वेस्टेज", "नुकसान प्रतिशत", "वेस्टेज प्रतिशत"]},
    _L("Wastage % setting", "Wastage % ki setting", "ضیاع % کی ترتیب", "वेस्टेज % सेटिंग"),
    _L("Where do I change the wastage %?", "wastage kahan se badlun",
       "ضیاع کہاں سے بدلوں؟", "वेस्टेज कहाँ से बदलूँ?"),
    _L("Wastage % is set in Settings -> the Mill Profile card (the 'Wastage %' field). Right now it is {v}%. It is a reporting figure only: the Phosphate Detail register and the Day-End show wastage = this % of the day's powder, and the register works out rock consumption as powder + wastage. Your stock numbers do not change when you change it.",
       "Wastage % yahan se badalta hai: Settings -> Mill Profile wale card mein 'Wastage %' ka khana. Abhi ye {v}% rakha hai. Ye sirf report ka number hai: Phosphate Detail register aur Day-End mein wastage = din ke powder ka ye % dikhta hai, aur register pathar ki khapat bhi powder + wastage se nikalta hai. Isay badalne se stock ke number NAHI badalte.",
       "ضیاع % یہاں سے بدلتا ہے: ترتیبات -> مل پروفائل والے کارڈ میں 'ضیاع %' کا خانہ۔ ابھی یہ {v}% رکھا ہے۔ یہ صرف رپورٹ کا عدد ہے: فاسفیٹ تفصیل رجسٹر اور دن اختتام میں ضیاع = دن کے پاؤڈر کا یہ % دکھتا ہے، اور رجسٹر پتھر کی کھپت بھی پاؤڈر + ضیاع سے نکالتا ہے۔ اسے بدلنے سے اسٹاک کے اعداد نہیں بدلتے۔",
       "वेस्टेज % यहाँ से बदलता है: सेटिंग्स -> मिल प्रोफ़ाइल वाले कार्ड में 'वेस्टेज %' का खाना। अभी यह {v}% रखा है। यह सिर्फ़ रिपोर्ट का आँकड़ा है: फ़ॉस्फेट विवरण रजिस्टर और दिन-अंत में वेस्टेज = दिन के पाउडर का यह % दिखता है, और रजिस्टर रॉक की खपत भी पाउडर + वेस्टेज से निकालता है। इसे बदलने से स्टॉक के आँकड़े नहीं बदलते।"),
    dyn="wastage"),
 _K("set_bagw", "setting", "grindprod",
    {"lat": ["bag weight", "bag weights", "bag ka wazan", "thailay ka wazan", "thaila wazan",
             "bori ka wazan", "per bag kg", "fi bag", "bag kg", "powder bag kg",
             "filter bag kg", "bag defaults", "bag wazan"],
     "ur": ["تھیلے کا وزن", "بوری کا وزن", "تھیلا وزن"], "hi": ["बोरे का वज़न", "बोरा वज़न", "प्रति बोरा"]},
    _L("Bag weight defaults", "Bag weight defaults", "تھیلے کے وزن کی طے شدہ قدریں", "बोरे के वज़न की डिफ़ॉल्ट"),
    _L("Where are the bag weights set?", "bag ka wazan kahan set hota hai",
       "تھیلے کا وزن کہاں مقرر ہوتا ہے؟", "बोरे का वज़न कहाँ सेट होता है?"),
    _L("Bag weights are NOT asked on the entry. They live in the 'Bag weight defaults' card at the END of the Grinding & Production page: Powder bag kg and Filter bag kg (right now {v}). The form's live totals use them (bags x kg per bag = kg = tons), and every save stamps the weights in effect onto its own record - so changing a default later never changes old records. Owner and Manager can save the card.",
       "Bag ka wazan entry par NAHI poochha jata. Ye Grinding & Production page ke AAKHIR mein 'Bag weight defaults' card mein hota hai: Powder bag kg aur Filter bag kg (abhi {v}). Form ka live total inhi se banta hai (bag x fi bag kg = kg = ton), aur har save us waqt ke wazan apne record par stamp kar deta hai - is liye baad mein default badalne se purane record NAHI badalte. Ye card Owner aur Manager save kar sakte hain.",
       "تھیلے کا وزن انٹری پر نہیں پوچھا جاتا۔ یہ پسائی و پیداوار صفحے کے آخر میں 'تھیلے کے وزن کی طے شدہ قدریں' کارڈ میں ہوتا ہے: پاؤڈر تھیلا کلو اور فلٹر تھیلا کلو (ابھی {v})۔ فارم کا زندہ کل انہی سے بنتا ہے (تھیلے × فی تھیلا کلو = کلو = ٹن)، اور ہر محفوظ اس وقت کے وزن اپنے ریکارڈ پر مہر کر دیتا ہے - اس لیے بعد میں طے شدہ قدر بدلنے سے پرانے ریکارڈ نہیں بدلتے۔ یہ کارڈ مالک اور منیجر محفوظ کر سکتے ہیں۔",
       "बोरे का वज़न एंट्री पर नहीं पूछा जाता। यह पिसाई व उत्पादन पृष्ठ के अंत में 'बोरे के वज़न की डिफ़ॉल्ट' कार्ड में होता है: पाउडर बोरा किलो और फ़िल्टर बोरा किलो (अभी {v})। फ़ॉर्म का लाइव योग इन्हीं से बनता है (बोरे × प्रति बोरा किलो = किलो = टन), और हर सहेज उस समय के वज़न अपने रिकॉर्ड पर अंकित कर देता है - इसलिए बाद में डिफ़ॉल्ट बदलने से पुराने रिकॉर्ड नहीं बदलते। यह कार्ड मालिक और मैनेजर सहेज सकते हैं।"),
    dyn="bagw"),
 _K("set_owawa", "setting", "settings",
    {"lat": ["owner whatsapp", "malik ka whatsapp", "owner number", "whatsapp number kahan", "owner ka number"],
     "ur": ["مالک واٹس ایپ", "مالک کا نمبر"], "hi": ["मालिक व्हाट्सएप", "मालिक का नंबर"]},
    _L("Owner WhatsApp number", "Owner ka WhatsApp number", "مالک کا واٹس ایپ نمبر", "मालिक का व्हाट्सएप नंबर"),
    _L("Where is the owner's WhatsApp number set?", "owner whatsapp number kahan likhun",
       "مالک کا واٹس ایپ نمبر کہاں لکھوں؟", "मालिक का व्हाट्सएप नंबर कहाँ लिखूँ?"),
    _L("The owner's WhatsApp number is in Settings -> the Mill Profile card (the 'Owner WhatsApp' field). Vehicle voucher copies go to this number - to the party, the driver and the owner. If the field is empty, the mill phone from the same card is used instead.",
       "Owner ka WhatsApp number Settings -> Mill Profile card mein 'Owner WhatsApp' wale khane mein likha jata hai. Gari ke voucher ki copy isi number par jati hai - party, driver aur owner, teenon ko. Ye khana khali ho to usi card wala mill phone use hota hai.",
       "مالک کا واٹس ایپ نمبر ترتیبات -> مل پروفائل کارڈ میں 'مالک واٹس ایپ' والے خانے میں لکھا جاتا ہے۔ گاڑی کے واؤچر کی نقل اسی نمبر پر جاتی ہے - پارٹی، ڈرائیور اور مالک، تینوں کو۔ یہ خانہ خالی ہو تو اسی کارڈ والا مل فون استعمال ہوتا ہے۔",
       "मालिक का व्हाट्सएप नंबर सेटिंग्स -> मिल प्रोफ़ाइल कार्ड में 'मालिक व्हाट्सएप' वाले खाने में लिखा जाता है। गाड़ी के वाउचर की कॉपी इसी नंबर पर जाती है - पार्टी, ड्राइवर और मालिक, तीनों को। यह खाना खाली हो तो उसी कार्ड वाला मिल फ़ोन उपयोग होता है।")),
 _K("set_msg", "setting", "settings",
    {"lat": ["whatsapp api", "cloud api", "phone number id", "access token", "auto send",
             "whatsapp template", "templates", "sms api", "sms setting", "sender id"],
     "ur": ["واٹس ایپ اے پی آئی", "ایس ایم ایس"], "hi": ["व्हाट्सएप API", "एसएमएस"]},
    _L("WhatsApp / SMS auto-send settings", "WhatsApp / SMS auto-send ki setting",
       "واٹس ایپ / SMS خودکار بھیجنے کی ترتیب", "व्हाट्सएप / SMS ऑटो-सेंड सेटिंग"),
    _L("Where is WhatsApp auto-send set?", "whatsapp auto send kahan set hota hai",
       "واٹس ایپ خودکار بھیجنا کہاں مقرر ہوتا ہے؟", "व्हाट्सएप ऑटो-सेंड कहाँ सेट होता है?"),
    _L("WhatsApp auto-send is set in Settings -> the WhatsApp card: Phone Number ID + Access Token, with Meta-approved templates (vehicle in/out, payment reminder, day-end summary, owner alerts). When it is set, alerts and vouchers send by themselves; when it is not, every send shows a one-tap wa.me button instead. SMS (API URL, key, Sender ID) is on the same card, below WhatsApp. This card is in the online edition; the PC edition works with print and one-tap buttons.",
       "WhatsApp auto-send Settings -> WhatsApp wale card mein set hota hai: Phone Number ID + Access Token, aur Meta ke approved templates (gari in/out, payment reminder, day-end summary, owner alerts). Ye laga ho to alerts aur voucher khud chale jate hain; na laga ho to har send par one-tap wa.me button ata hai. SMS (API URL, key, Sender ID) bhi isi card mein WhatsApp ke neeche hai. Ye card online edition mein hota hai; PC edition mein print aur one-tap button se kaam chalta hai.",
       "واٹس ایپ خودکار بھیجنا ترتیبات -> واٹس ایپ والے کارڈ میں مقرر ہوتا ہے: فون نمبر ID + رسائی ٹوکن، اور میٹا کے منظور شدہ سانچے (گاڑی اندر/باہر، ادائیگی یاددہانی، دن اختتام خلاصہ، مالک الرٹ)۔ یہ لگا ہو تو الرٹ اور واؤچر خود چلے جاتے ہیں؛ نہ لگا ہو تو ہر بھیجنے پر ایک ٹیپ wa.me بٹن آتا ہے۔ SMS (API پتہ، چابی، بھیجنے والا ID) بھی اسی کارڈ میں واٹس ایپ کے نیچے ہے۔ یہ کارڈ آن لائن ایڈیشن میں ہوتا ہے؛ PC ایڈیشن میں پرنٹ اور ایک ٹیپ بٹن سے کام چلتا ہے۔",
       "व्हाट्सएप ऑटो-सेंड सेटिंग्स -> व्हाट्सएप वाले कार्ड में सेट होता है: फ़ोन नंबर ID + एक्सेस टोकन, और मेटा के स्वीकृत टेम्पलेट (गाड़ी अंदर/बाहर, भुगतान रिमाइंडर, दिन-अंत सारांश, मालिक अलर्ट)। यह लगा हो तो अलर्ट और वाउचर ख़ुद चले जाते हैं; न लगा हो तो हर भेजने पर एक टैप wa.me बटन आता है। SMS (API पता, कुंजी, भेजने वाला ID) भी इसी कार्ड में व्हाट्सएप के नीचे है। यह कार्ड ऑनलाइन संस्करण में होता है; PC संस्करण में प्रिंट और एक टैप बटन से काम चलता है।")),
 _K("set_email", "setting", "settings",
    {"lat": ["email", "smtp", "email setting", "email kahan", "password reset", "password bhool",
             "forgot password", "login by email", "email par bhejo"],
     "ur": ["ای میل", "ای میل ترتیب", "پاس ورڈ بھول"], "hi": ["ईमेल", "ईमेल सेटिंग", "पासवर्ड भूल"]},
    _L("Email (SMTP) settings", "Email (SMTP) ki setting",
       "ای میل (SMTP) کی ترتیب", "ईमेल (SMTP) सेटिंग"),
    _L("Where is email set, and how do password reset and email statements work?",
       "email kahan set hota hai, password reset aur email statement kaisay kaam karte hain",
       "ای میل کہاں مقرر ہوتی ہے، پاس ورڈ ری سیٹ اور ای میل تفصیل کیسے کام کرتے ہیں؟",
       "ईमेल कहाँ सेट होता है, पासवर्ड रीसेट और ईमेल विवरण कैसे काम करते हैं?"),
    _L("Email is set in Settings -> the Email card (Owner only): SMTP host/port/security, username + password, From name/email, the master ON switch and per-event toggles, plus the System address used in reset links. Gmail needs smtp.gmail.com, port 587, STARTTLS and an App Password. Logins can also sign in with their email, and 'Forgot password?' on the login page emails a one-hour reset link. Each login and each party carries its own email field; statements and invoices have a Send by Email button, a payment received emails the party, a client payment proof emails the owner, and the Day-End summary can email the owner once a day. Every email send (or failure) is written in the Alerts list with channel 'email'.",
       "Email Settings -> Email wale card mein set hoti hai (sirf Owner): SMTP host/port/security, username + password, From name/email, master ON switch aur har event ke toggle, aur reset links ke liye System address. Gmail ke liye smtp.gmail.com, port 587, STARTTLS aur App Password chahiye. Login apni email se bhi ho sakta hai, aur login page par 'Forgot password?' se ek ghante wala reset link email ho jata hai. Har login aur har party ka apna email khana hai; khata aur invoice par Send by Email button hai, payment milne par party ko email jata hai, client ki payment proof par owner ko, aur Day-End summary roz ek dafa owner ko email ho sakti hai. Har email (kamiyab ya nakam) Alerts list mein 'email' channel se likhi jati hai.",
       "ای میل ترتیبات -> ای میل والے کارڈ میں مقرر ہوتی ہے (صرف مالک): SMTP ہوسٹ/پورٹ/سیکیورٹی، صارف نام + پاس ورڈ، بھیجنے والے کا نام/ای میل، ماسٹر ON سوئچ اور ہر ایونٹ کے ٹوگل، اور ری سیٹ لنکس کے لیے سسٹم پتہ۔ Gmail کے لیے smtp.gmail.com، پورٹ 587، STARTTLS اور ایپ پاس ورڈ چاہیے۔ لاگ ان اپنی ای میل سے بھی ہو سکتا ہے، اور لاگ ان صفحے پر 'پاس ورڈ بھول گئے؟' سے ایک گھنٹے والا ری سیٹ لنک ای میل ہو جاتا ہے۔ ہر لاگ ان اور ہر پارٹی کا اپنا ای میل خانہ ہے؛ کھاتے اور انوائس پر ای میل بھیجنے کا بٹن ہے، ادائیگی ملنے پر پارٹی کو ای میل جاتا ہے، کلائنٹ کے ادائیگی ثبوت پر مالک کو، اور دن اختتام خلاصہ روز ایک دفعہ مالک کو ای میل ہو سکتا ہے۔ ہر ای میل (کامیاب یا ناکام) الرٹس فہرست میں 'email' چینل سے لکھی جاتی ہے۔",
       "ईमेल सेटिंग्स -> ईमेल वाले कार्ड में सेट होता है (केवल मालिक): SMTP होस्ट/पोर्ट/सुरक्षा, उपयोगकर्ता नाम + पासवर्ड, भेजने वाले का नाम/ईमेल, मास्टर ON स्विच और हर इवेंट के टॉगल, और रीसेट लिंक्स के लिए सिस्टम पता। Gmail के लिए smtp.gmail.com, पोर्ट 587, STARTTLS और ऐप पासवर्ड चाहिए। लॉगिन अपनी ईमेल से भी हो सकता है, और लॉगिन पृष्ठ पर 'पासवर्ड भूल गए?' से एक घंटे वाला रीसेट लिंक ईमेल हो जाता है। हर लॉगिन और हर पार्टी का अपना ईमेल खाना है; खाते और इनवॉइस पर ईमेल भेजने का बटन है, भुगतान मिलने पर पार्टी को ईमेल जाता है, ग्राहक के भुगतान प्रमाण पर मालिक को, और दिन अंत सारांश रोज़ एक बार मालिक को ईमेल हो सकता है। हर ईमेल (सफल या असफल) अलर्ट सूची में 'email' चैनल से लिखा जाता है।")),
 _K("set_theme", "setting", "settings",
    {"lat": ["theme", "rang badalna", "colour", "color", "theme colour", "rang"],
     "ur": ["تھیم", "رنگ"], "hi": ["थीम", "रंग"]},
    _L("Theme colour", "Theme ka rang", "تھیم کا رنگ", "थीम का रंग"),
    _L("Where do I change the theme colour?", "theme colour kahan se badalta hai",
       "تھیم کا رنگ کہاں سے بدلتا ہے؟", "थीम का रंग कहाँ से बदलता है?"),
    _L("The theme colour is in Settings -> the Appearance card (Owner only): 12 colours, dark and light both. It applies to the whole system, including the login screen.",
       "Theme ka rang Settings -> Appearance card mein hai (sirf Owner ke liye): 12 rang hain, gehray aur halke dono. Ye poore system par lagta hai, login screen par bhi.",
       "تھیم کا رنگ ترتیبات -> ظاہری کارڈ میں ہے (صرف مالک کے لیے): 12 رنگ ہیں، گہرے اور ہلکے دونوں۔ یہ پورے سسٹم پر لگتا ہے، لاگ ان اسکرین پر بھی۔",
       "थीम का रंग सेटिंग्स -> दिखावट कार्ड में है (केवल मालिक के लिए): 12 रंग हैं, गहरे और हल्के दोनों। यह पूरे सिस्टम पर लगता है, लॉगिन स्क्रीन पर भी।")),
 _K("set_logo", "setting", "settings",
    {"lat": ["logo"], "ur": ["لوگو"], "hi": ["लोगो"]},
    _L("Mill logo", "Mill ka logo", "مل کا لوگو", "मिल का लोगो"),
    _L("Where is the logo uploaded?", "logo kahan se lagta hai",
       "لوگو کہاں سے لگتا ہے؟", "लोगो कहाँ से लगता है?"),
    _L("The mill logo is uploaded in Settings -> the Mill Profile card (the Logo section). It shows on the login screen, on prints and invoices, and on the vehicle voucher.",
       "Mill ka logo Settings -> Mill Profile card mein Logo wale hisse se lagta hai. Ye login screen, prints/invoices aur gari ke voucher par nazar ata hai.",
       "مل کا لوگو ترتیبات -> مل پروفائل کارڈ میں لوگو والے حصے سے لگتا ہے۔ یہ لاگ ان اسکرین، پرنٹس/انوائسز اور گاڑی کے واؤچر پر نظر آتا ہے۔",
       "मिल का लोगो सेटिंग्स -> मिल प्रोफ़ाइल कार्ड में लोगो वाले भाग से लगता है। यह लॉगिन स्क्रीन, प्रिंट/इनवॉइस और गाड़ी के वाउचर पर नज़र आता है।")),
 _K("set_profile", "setting", "settings",
    {"lat": ["mill name", "mill ka naam", "factory name", "mill phone", "mill address",
             "pata badalna", "naam badalna", "phone badalna"],
     "ur": ["مل کا نام", "مل فون", "پتہ"], "hi": ["मिल का नाम", "मिल फ़ोन", "पता"]},
    _L("Mill profile (name / phone / address)", "Mill profile (naam / phone / pata)",
       "مل پروفائل (نام / فون / پتہ)", "मिल प्रोफ़ाइल (नाम / फ़ोन / पता)"),
    _L("Where do I change the mill name?", "mill ka naam kahan se badlun",
       "مل کا نام کہاں سے بدلوں؟", "मिल का नाम कहाँ से बदलूँ?"),
    _L("Mill name, phone and address are in Settings -> the Mill Profile card. The name shows on the login screen, the dashboard, prints, invoices and the vehicle voucher.",
       "Mill ka naam, phone aur pata Settings -> Mill Profile card mein hote hain. Naam login screen, dashboard, prints, invoices aur gari ke voucher par ata hai.",
       "مل کا نام، فون اور پتہ ترتیبات -> مل پروفائل کارڈ میں ہوتے ہیں۔ نام لاگ ان اسکرین، ڈیش بورڈ، پرنٹس، انوائسز اور گاڑی کے واؤچر پر آتا ہے۔",
       "मिल का नाम, फ़ोन और पता सेटिंग्स -> मिल प्रोफ़ाइल कार्ड में होते हैं। नाम लॉगिन स्क्रीन, डैशबोर्ड, प्रिंट, इनवॉइस और गाड़ी के वाउचर पर आता है।")),
 _K("set_limits", "setting", "settings",
    {"lat": ["cash limit", "holder limit", "approval limit", "limit badalna", "cash rules",
             "cash ki limit", "limit kahan"],
     "ur": ["نقد حد", "کیش لمٹ"], "hi": ["नकद सीमा", "लिमिट", "कैश लिमिट"]},
    _L("Cash limits", "Cash ki limits", "نقد کی حدیں", "नकद की सीमाएँ"),
    _L("Where are the cash limits set?", "cash limit kahan set hoti hai",
       "نقد کی حد کہاں مقرر ہوتی ہے؟", "नकद की सीमा कहाँ सेट होती है?"),
    _L("Cash limits are in Settings -> the Cash Rules card. Right now they are: {v}. Crossing the holder limit shows a warning on Cash in Hand, and a Manager-paid cash expense above the approval limit stays pending until the Owner approves it.",
       "Cash ki limits Settings -> Cash Rules card mein hain. Abhi ye rakhi hain: {v}. Holder limit cross ho to Cash in Hand par warning ati hai, aur approval limit se bara Manager cash kharcha Owner ki approval tak pending rehta hai.",
       "نقد کی حدیں ترتیبات -> نقد اصول کارڈ میں ہیں۔ ابھی یہ رکھی ہیں: {v}۔ حامل حد پار ہو تو ہاتھ میں نقد پر وارننگ آتی ہے، اور منظوری حد سے بڑا منیجر نقد خرچہ مالک کی منظوری تک زیر التوا رہتا ہے۔",
       "नकद की सीमाएँ सेटिंग्स -> नकद नियम कार्ड में हैं। अभी ये रखी हैं: {v}। धारक सीमा पार हो तो हाथ में नकद पर चेतावनी आती है, और स्वीकृति सीमा से बड़ा मैनेजर नकद खर्च मालिक की स्वीकृति तक लंबित रहता है।"),
    dyn="limits"),
 _K("set_banks", "setting", "settings",
    {"lat": ["bank list", "bank add", "bank balance kahan", "bank opening", "bank ka balance", "banks kahan"],
     "ur": ["بینک فہرست", "بینک بیلنس"], "hi": ["बैंक सूची", "बैंक शेष"]},
    _L("Bank list & opening balances", "Bank list aur opening balance",
       "بینک فہرست و ابتدائی بیلنس", "बैंक सूची व प्रारंभिक शेष"),
    _L("Where are the banks set?", "bank list kahan set hoti hai",
       "بینک فہرست کہاں مقرر ہوتی ہے؟", "बैंक सूची कहाँ सेट होती है?"),
    _L("Bank names are listed in Settings -> the Bank List card (one name per line), and each bank's opening balance is set in the Cash Rules card. The Bank Book (inside the Cash Book page) builds every bank's running balance from those openings plus bank payments and bank expenses.",
       "Bankon ke naam Settings -> Bank List card mein likhe jate hain (har line par ek naam), aur har bank ka opening balance Cash Rules card mein set hota hai. Bank Book (Cash Book page ke andar) har bank ka chalta balance inhi openings + bank payments aur bank kharchon se banati hai.",
       "بینکوں کے نام ترتیبات -> بینک فہرست کارڈ میں لکھے جاتے ہیں (ہر لائن پر ایک نام)، اور ہر بینک کا ابتدائی بیلنس نقد اصول کارڈ میں مقرر ہوتا ہے۔ بینک بک (کیش بک صفحے کے اندر) ہر بینک کا چلتا بیلنس انہی ابتدائی اعداد + بینک ادائیگیوں اور بینک اخراجات سے بناتی ہے۔",
       "बैंकों के नाम सेटिंग्स -> बैंक सूची कार्ड में लिखे जाते हैं (हर पंक्ति पर एक नाम), और हर बैंक का प्रारंभिक शेष नकद नियम कार्ड में सेट होता है। बैंक बुक (कैश बुक पृष्ठ के अंदर) हर बैंक का चलता शेष इन्हीं प्रारंभिक आँकड़ों + बैंक भुगतानों और बैंक खर्चों से बनाती है।")),
 _K("set_font", "setting", "settings",
    {"lat": ["font", "print font", "text size", "print size", "bold heading", "font badalna"],
     "ur": ["فونٹ", "پرنٹ فونٹ"], "hi": ["फ़ॉन्ट", "प्रिंट"]},
    _L("Font & Print settings", "Font & Print ki setting", "فونٹ و پرنٹ کی ترتیب", "फ़ॉन्ट व प्रिंट सेटिंग"),
    _L("Where are the font settings?", "font kahan se badalta hai",
       "فونٹ کہاں سے بدلتا ہے؟", "फ़ॉन्ट कहाँ से बदलता है?"),
    _L("Fonts are in Settings -> the Font & Print card: screen font and text size for the app, print font and size for printouts, and bold print headings on/off. They apply to the whole system and to every print (voucher, invoice, reports).",
       "Font Settings -> Font & Print card mein hai: app ke liye screen font aur text size, print ke liye print font aur size, aur print headings bold on/off. Ye poore system par aur har print (voucher, invoice, reports) par lagta hai.",
       "فونٹ ترتیبات -> فونٹ و پرنٹ کارڈ میں ہے: ایپ کے لیے اسکرین فونٹ اور متن سائز، پرنٹ کے لیے پرنٹ فونٹ اور سائز، اور پرنٹ سرخیاں بولڈ آن/آف۔ یہ پورے سسٹم پر اور ہر پرنٹ (واؤچر، انوائس، رپورٹس) پر لگتا ہے۔",
       "फ़ॉन्ट सेटिंग्स -> फ़ॉन्ट व प्रिंट कार्ड में है: ऐप के लिए स्क्रीन फ़ॉन्ट और टेक्स्ट साइज़, प्रिंट के लिए प्रिंट फ़ॉन्ट और साइज़, और प्रिंट शीर्षक बोल्ड ऑन/ऑफ़। यह पूरे सिस्टम पर और हर प्रिंट (वाउचर, इनवॉइस, रिपोर्ट) पर लगता है।")),
 _K("set_voice", "setting", "settings",
    {"lat": ["voice alert", "voice alerts", "awaz wala alert", "bol kar", "voice notification",
             "awaz band", "awaz on"],
     "ur": ["آواز الرٹ", "آواز والی اطلاع"], "hi": ["आवाज़ अलर्ट", "वॉइस अलर्ट"]},
    _L("Voice alerts", "Voice alerts", "آواز الرٹ", "आवाज़ अलर्ट"),
    _L("Where are voice alerts switched?", "voice alerts kahan se on hote hain",
       "آواز الرٹ کہاں سے آن ہوتے ہیں؟", "आवाज़ अलर्ट कहाँ से ऑन होते हैं?"),
    _L("Voice alerts are switched in Settings -> the Voice Alerts card: a master switch, plus separate switches for vehicle entries and for payments. While the app is open, a new entry is announced by voice with a toast; the speaker button in the top bar mutes it on that device only.",
       "Voice alerts Settings -> Voice Alerts card se on/off hote hain: ek master switch, aur gari entries aur payments ke alag switches. App khula ho to nayi entry awaz ke saath aur toast mein ati hai; upar wali bar ka speaker button sirf usi device par awaz band karta hai.",
       "آواز الرٹ ترتیبات -> آواز الرٹ کارڈ سے آن/آف ہوتے ہیں: ایک ماسٹر سوئچ، اور گاڑی انٹریوں اور ادائیگیوں کے الگ سوئچ۔ ایپ کھلا ہو تو نئی انٹری آواز کے ساتھ اور ٹوسٹ میں آتی ہے؛ اوپر والی بار کا اسپیکر بٹن صرف اسی ڈیوائس پر آواز بند کرتا ہے۔",
       "आवाज़ अलर्ट सेटिंग्स -> आवाज़ अलर्ट कार्ड से ऑन/ऑफ़ होते हैं: एक मास्टर स्विच, और गाड़ी एंट्रियों व भुगतानों के अलग स्विच। ऐप खुला हो तो नई एंट्री आवाज़ के साथ और टोस्ट में आती है; ऊपर वाली बार का स्पीकर बटन सिर्फ़ उसी डिवाइस पर आवाज़ बंद करता है।")),
 _K("set_age", "setting", "settings",
    {"lat": ["powder age", "purana powder", "age limit", "powder warning", "ageing", "aging"],
     "ur": ["پاؤڈر عمر", "پرانا پاؤڈر"], "hi": ["पाउडर आयु", "पुराना पाउडर"]},
    _L("Powder age warning limit", "Powder age ki warning limit", "پاؤڈر عمر کی وارننگ حد", "पाउडर आयु की चेतावनी सीमा"),
    _L("Where is the powder age limit set?", "powder age limit kahan set hoti hai",
       "پاؤڈر عمر کی حد کہاں مقرر ہوتی ہے؟", "पाउडर आयु की सीमा कहाँ सेट होती है?"),
    _L("The powder-age warning limit is in Settings -> the Mill Profile card (the 'Powder age days' field, right now {v} days). Powder lying ready longer than this is flagged with an ageing warning on the Dashboard and in the Warehouse, so old stock goes out first.",
       "Powder ki age warning ki limit Settings -> Mill Profile card mein 'Powder age days' wale khane mein hai (abhi {v} din). Is se zyada din para rehne wala tayyar powder Dashboard aur Warehouse mein ageing warning ke saath dikhta hai, taake purana stock pehle rawana ho.",
       "پاؤڈر کی عمر وارننگ کی حد ترتیبات -> مل پروفائل کارڈ میں 'پاؤڈر عمر دن' والے خانے میں ہے (ابھی {v} دن)۔ اس سے زیادہ دن پڑا رہنے والا تیار پاؤڈر ڈیش بورڈ اور گودام میں عمر وارننگ کے ساتھ دکھتا ہے، تاکہ پرانا اسٹاک پہلے روانہ ہو۔",
       "पाउडर की आयु चेतावनी की सीमा सेटिंग्स -> मिल प्रोफ़ाइल कार्ड में 'पाउडर आयु दिन' वाले खाने में है (अभी {v} दिन)। इससे ज़्यादा दिन पड़ा रहने वाला तैयार पाउडर डैशबोर्ड और गोदाम में आयु चेतावनी के साथ दिखता है, ताकि पुराना स्टॉक पहले रवाना हो।"),
    dyn="age"),
]

_KB += [
 # ------------------------------------------------------------- heads ---
 _K("head_khata", "head", "parties",
    {"lat": ["khata heads", "ledger heads", "heads kon se", "kon se head", "khata mein head", "ledger head"],
     "ur": ["کھاتہ ہیڈ", "ہیڈز کون سے"], "hi": ["खाता हेड", "हेड कौन से"]},
    _L("Khata (ledger) heads", "Khata (ledger) ke heads", "کھاتے کے ہیڈز", "खाते के हेड"),
    _L("What heads does a party khata have?", "khata mein kon se head hote hain",
       "کھاتے میں کون سے ہیڈ ہوتے ہیں؟", "खाते में कौन से हेड होते हैं?"),
    _L("A party's khata (ledger) has these line types: Opening (the starting balance), Grinding (grinding charge - debit), Sale (own powder sold - debit), Purchase (rock bought from the party - credit), Rent (vehicle rent on a mine-rate Vehicle In, to the seller - credit; set to Driver it is a mill cash cost instead, no khata line), Freight (debit when the party pays it), Loading (debit when the party bears it) and Payment (money in = credit, money out = debit). Debit increases what the party owes us; credit decreases it. Open the khata from Parties -> the Ledger button in a party's row.",
       "Party ke khatay (ledger) mein ye line types hote hain: Opening (shuru ka balance), Grinding (pisai charge - debit), Sale (apna powder becha - debit), Purchase (party se pathar khareeda - credit), Rent (Mine rate wali Vehicle In par gari ka rent, seller ko - credit; Driver par set ho to mill ka cash kharcha hai, khata line nahi), Freight (party de to debit), Loading (party ke zimme ho to debit) aur Payment (paisay aaye = credit, paisay diye = debit). Debit se party ka dena badhta hai, credit se kam hota hai. Khata Parties page par party ki row ke Ledger button se khulta hai.",
       "پارٹی کے کھاتے میں یہ لائن اقسام ہوتی ہیں: ابتدائی (شروع کا بیلنس)، پسائی (پسائی چارج - ڈیبٹ)، فروخت (اپنا پاؤڈر بیچا - ڈیبٹ)، خرید (پارٹی سے پتھر خریدا - کریڈٹ)، کرایہ (مائن ریٹ والی گاڑی اندر پر گاڑی کا کرایہ، بیچنے والے کو - کریڈٹ؛ ڈرائیور پر رکھا جائے تو مل کا نقد خرچ ہے، کھاتا لائن نہیں)، فریٹ (پارٹی دے تو ڈیبٹ)، لوڈنگ (پارٹی کے ذمے ہو تو ڈیبٹ) اور ادائیگی (پیسے آئے = کریڈٹ، پیسے دیے = ڈیبٹ)۔ ڈیبٹ سے پارٹی کا دینا بڑھتا ہے، کریڈٹ سے کم ہوتا ہے۔ کھاتہ پارٹیاں صفحے پر پارٹی کی قطار کے کھاتہ بٹن سے کھلتا ہے۔",
       "पार्टी के खाते में ये पंक्ति प्रकार होते हैं: प्रारंभिक (शुरू का शेष), पिसाई (पिसाई शुल्क - डेबिट), बिक्री (अपना पाउडर बेचा - डेबिट), ख़रीद (पार्टी से रॉक ख़रीदा - क्रेडिट), किराया (माइन दर वाली गाड़ी अंदर पर गाड़ी का किराया, विक्रेता को - क्रेडिट; ड्राइवर पर रखा जाए तो मिल का नकद खर्च है, खाता पंक्ति नहीं), फ्रेट (पार्टी दे तो डेबिट), लोडिंग (पार्टी के ज़िम्मे हो तो डेबिट) और भुगतान (पैसे आए = क्रेडिट, पैसे दिए = डेबिट)। डेबिट से पार्टी का देना बढ़ता है, क्रेडिट से कम होता है। खाता पार्टियाँ पृष्ठ पर पार्टी की पंक्ति के खाता बटन से खुलता है।")),
 _K("head_grinding", "head", "parties",
    {"lat": ["grinding head", "pisai head", "grinding charge kahan", "pisai ka charge kahan lagta"],
     "ur": ["پسائی ہیڈ", "پسائی چارج"], "hi": ["पिसाई हेड", "पिसाई शुल्क"]},
    _L("Grinding head", "Grinding head", "پسائی ہیڈ", "पिसाई हेड"),
    _L("What is the Grinding head?", "grinding head kya hai",
       "پسائی ہیڈ کیا ہے؟", "पिसाई हेड क्या है?"),
    _L("The Grinding head in a party khata is the grinding charge the party owes (debit). It is created in two ways: (1) a grinding record with a rate (older entries), and (2) the Grinding rate written on a Vehicle OUT - net tons x rate posts under this same head when the powder leaves. The Grinding & Production entry itself has no rate and posts no money.",
       "Party ke khatay mein Grinding head pisai ka wo charge hai jo party ne dena hai (debit). Ye do tareeqon se banta hai: (1) rate wali grinding entry se (purani entries), aur (2) Vehicle OUT par likhe gaye Grinding rate se - powder rawana hote waqt net ton x rate isi head mein lag jata hai. Grinding & Production wali entry mein rate hota hi nahi, us se paisay NAHI lagte.",
       "پارٹی کے کھاتے میں پسائی ہیڈ پسائی کا وہ چارج ہے جو پارٹی نے دینا ہے (ڈیبٹ)۔ یہ دو طریقوں سے بنتا ہے: (1) ریٹ والی پسائی انٹری سے (پرانی انٹریاں)، اور (2) گاڑی باہر پر لکھے گئے پسائی ریٹ سے - پاؤڈر روانہ ہوتے وقت خالص ٹن × ریٹ اسی ہیڈ میں لگ جاتا ہے۔ پسائی و پیداوار والی انٹری میں ریٹ ہوتا ہی نہیں، اس سے پیسے نہیں لگتے۔",
       "पार्टी के खाते में पिसाई हेड पिसाई का वह शुल्क है जो पार्टी ने देना है (डेबिट)। यह दो तरीकों से बनता है: (1) दर वाली पिसाई एंट्री से (पुरानी एंट्रियाँ), और (2) गाड़ी बाहर पर लिखे गए पिसाई दर से - पाउडर रवाना होते समय शुद्ध टन × दर इसी हेड में लग जाता है। पिसाई व उत्पादन वाली एंट्री में दर होता ही नहीं, उससे पैसे नहीं लगते।")),
 _K("head_purchase", "head", "parties",
    {"lat": ["purchase head", "khareed head", "purchase kahan lagta"],
     "ur": ["خرید ہیڈ"], "hi": ["ख़रीद हेड"]},
    _L("Purchase head", "Purchase head", "خرید ہیڈ", "ख़रीद हेड"),
    _L("What is the Purchase head?", "purchase head kya hai",
       "خرید ہیڈ کیا ہے؟", "ख़रीद हेड क्या है?"),
    _L("The Purchase head is rock bought FROM the party - money we owe them (credit). It is created by an Own Trade purchase (billed tons after the deduction % x rate) or by the Rock rate on an Own (Mine) Vehicle IN (net tons x rate) - a gate purchase exists only on Own entries, and it posts to the 'Buy from' seller's khata (Buy from = Own itself posts nothing). It shows in the party khata and in the Own Stock / Party Business figures.",
       "Purchase head party SE khareeda gaya pathar hai - ye raqam hum ne party ko deni hai (credit). Ye Own Trade ki purchase se banta hai (deduction % ke baad billed ton x rate) ya Own (Mine) Vehicle IN par likhe Rock rate se (net ton x rate) - gate khareed sirf Own entry par hoti hai, aur ye 'Buy from' seller ke khatay mein lagta hai (Buy from = Own khud ho to kuch nahi lagta). Ye party ke khatay aur Own Stock / Party Business ke numbers mein dikhta hai.",
       "خرید ہیڈ پارٹی سے خریدا گیا پتھر ہے - یہ رقم ہم نے پارٹی کو دینی ہے (کریڈٹ)۔ یہ اپنی تجارت کی خرید سے بنتا ہے (کٹوتی % کے بعد بل ٹن × ریٹ) یا اپنی گاڑی اندر پر لکھے پتھر ریٹ سے (خالص ٹن × ریٹ) — گیٹ خرید صرف اپنی انٹری پر ہوتی ہے، اور یہ 'کس سے خریدا' بیچنے والے کے کھاتے میں لگتا ہے (کس سے خریدا = اپنا خود ہو تو کچھ نہیں لگتا)۔ یہ پارٹی کے کھاتے اور اپنا اسٹاک / پارٹی کاروبار کے اعداد میں دکھتا ہے۔",
       "ख़रीद हेड पार्टी से ख़रीदा गया रॉक है - यह राशि हमें पार्टी को देनी है (क्रेडिट)। यह अपने व्यापार की ख़रीद से बनता है (कटौती % के बाद बिल टन × दर) या अपनी गाड़ी अंदर पर लिखे रॉक दर से (शुद्ध टन × दर) — गेट ख़रीद केवल अपनी एंट्री पर होती है, और यह 'किससे ख़रीदा' विक्रेता के खाते में लगता है (किससे ख़रीदा = अपना ख़ुद हो तो कुछ नहीं लगता)। यह पार्टी के खाते और अपना स्टॉक / पार्टी व्यापार के आँकड़ों में दिखता है।")),
 _K("head_rent", "head", "parties",
    {"lat": ["rent head", "rent kya", "kiraya", "gari ka rent", "vehicle rent"],
     "ur": ["کرایہ", "گاڑی کرایہ"], "hi": ["किराया", "गाड़ी किराया"]},
    _L("Rent head", "Rent head", "کرایہ ہیڈ", "किराया हेड"),
    _L("What is the Rent head?", "rent head kya hai",
       "کرایہ ہیڈ کیا ہے؟", "किराया हेड क्या है?"),
    _L("The Rent head is the vehicle rent WE owe (credit). It is created only on an Own (Mine) Vehicle IN with the Mine rate (a gate purchase exists only on Own entries): the rent written there posts to the 'Buy from' seller's khata under Rent. If the rent is set to Driver instead, no Rent line is made - that rent is a mill cash cost shown in Day-End and the P&L. On the Factory ponch (delivered) rate no rent is created at all - delivery is already inside that rate.",
       "Rent head gari ka wo kiraya hai jo HUM ne dena hai (credit). Ye sirf Own (Mine) Vehicle IN par Mine rate chunne par banta hai (gate khareed sirf Own entry par hoti hai): wahan likha gaya rent 'Buy from' seller ke khatay mein Rent head ke neeche lag jata hai. Agar rent Driver par set ho to koi Rent line nahi banti - wo rent mill ka cash kharcha hai jo Day-End aur P&L mein dikhta hai. Factory ponch (delivered) rate par rent banta hi nahi - delivery usi rate ke andar hoti hai.",
       "کرایہ ہیڈ گاڑی کا وہ کرایہ ہے جو ہم نے دینا ہے (کریڈٹ)۔ یہ صرف اپنی گاڑی اندر پر مائن ریٹ منتخب کرنے پر بنتا ہے (گیٹ خرید صرف اپنی انٹری پر ہوتی ہے): وہاں لکھا گیا کرایہ 'کس سے خریدا' بیچنے والے کے کھاتے میں کرایہ ہیڈ کے نیچے لگ جاتا ہے۔ اگر کرایہ ڈرائیور پر رکھا جائے تو کوئی کرایہ لائن نہیں بنتی - وہ کرایہ مل کا نقد خرچ ہے جو دن اختتام اور نفع نقصان میں دکھتا ہے۔ فیکٹری پہنچ (پہنچایا ہوا) ریٹ پر کرایہ بنتا ہی نہیں - ترسیل اسی ریٹ کے اندر ہوتی ہے۔",
       "किराया हेड गाड़ी का वह किराया है जो हमें देना है (क्रेडिट)। यह सिर्फ़ अपनी गाड़ी अंदर पर माइन दर चुनने पर बनता है (गेट ख़रीद केवल अपनी एंट्री पर होती है): वहाँ लिखा गया किराया 'किससे ख़रीदा' विक्रेता के खाते में किराया हेड के नीचे लग जाता है। अगर किराया ड्राइवर पर रखा जाए तो कोई किराया लाइन नहीं बनती - वह किराया मिल का नकद खर्च है जो दिन-अंत और लाभ-हानि में दिखता है। फ़ैक्टरी पहुँच (पहुँची हुई) दर पर किराया बनता ही नहीं - डिलीवरी उसी दर के अंदर होती है।")),
 _K("head_freight", "head", "parties",
    {"lat": ["freight head", "loading head", "freight kya", "loading charge kya",
             "freight kahan lagta", "loading kahan lagta"],
     "ur": ["فریٹ", "لوڈنگ چارج"], "hi": ["फ्रेट", "लोडिंग"]},
    _L("Freight & Loading heads", "Freight aur Loading heads", "فریٹ و لوڈنگ ہیڈز", "फ्रेट व लोडिंग हेड"),
    _L("What are the Freight and Loading heads?", "freight aur loading head kya hain",
       "فریٹ اور لوڈنگ ہیڈ کیا ہیں؟", "फ्रेट और लोडिंग हेड क्या हैं?"),
    _L("Freight and Loading reach a party's khata only when the party bears them: Freight is charged on a Vehicle OUT whose freight payer is the party; Loading is charged when the trip's charge bearer is the party. When the mill bears them instead, they never touch the khata - they become the mill's own cost in the Profit & Loss.",
       "Freight aur Loading party ke khatay mein tabhi ate hain jab ye party ke zimme hon: Freight us Vehicle OUT par lagta hai jis ka freight payer party ho; Loading tab jab trip ke charges ka bearer party ho. Jab mill khud de, to ye khatay mein NAHI ate - Profit & Loss mein mill ka apna kharcha ban jate hain.",
       "فریٹ اور لوڈنگ پارٹی کے کھاتے میں تبھی آتے ہیں جب یہ پارٹی کے ذمے ہوں: فریٹ اس گاڑی باہر پر لگتا ہے جس کا فریٹ دینے والا پارٹی ہو؛ لوڈنگ تب جب ٹرپ کے چارجز کا حامل پارٹی ہو۔ جب مل خود دے، تو یہ کھاتے میں نہیں آتے - نفع نقصان میں مل کا اپنا خرچہ بن جاتے ہیں۔",
       "फ्रेट और लोडिंग पार्टी के खाते में तभी आते हैं जब ये पार्टी के ज़िम्मे हों: फ्रेट उस गाड़ी बाहर पर लगता है जिसका फ्रेट देने वाला पार्टी हो; लोडिंग तब जब ट्रिप के शुल्कों का वाहक पार्टी हो। जब मिल ख़ुद दे, तो ये खाते में नहीं आते - लाभ-हानि में मिल का अपना खर्च बन जाते हैं।")),
 _K("head_expense", "head", "expenses",
    {"lat": ["expense head", "expense heads", "kharcha head", "kharche ke head", "diesel head", "heads list"],
     "ur": ["خرچہ ہیڈ", "اخراجات ہیڈ"], "hi": ["खर्च हेड", "खर्चे के हेड"]},
    _L("Expense heads & sub-heads", "Expense heads aur sub-heads", "خرچہ ہیڈز و ذیلی ہیڈز", "खर्च हेड व उप-हेड"),
    _L("What expense heads are there?", "expense heads kon se hain",
       "خرچہ ہیڈز کون سے ہیں؟", "खर्च हेड कौन से हैं?"),
    _L("Expenses are booked under Main heads with Sub heads. The ready-made ones: Utilities (Electricity, Diesel, Gas, Water), Maintenance (Parts, Mechanic, Grinding Plates, Oil & Grease), Factory Operations (Loading Labour, Packing Material, Cleaning), Transport (Vehicle Fuel, Vehicle Repair, Freight), Office (Stationery, Mobile/Internet, Tea & Food), Workers Welfare (Food, Medical, Advance Adjustment) and Miscellaneous (Other). A Machine head is added by itself when a machine service/repair is logged. More heads can be added on the Expense Ledger page. Every expense sits under exactly one main + sub head, and reports group by head (Expense Ledger, Cost Per Ton).",
       "Kharcha Main heads aur un ke Sub heads ke neeche likha jata hai. Tayyar heads ye hain: Utilities (Electricity, Diesel, Gas, Water), Maintenance (Parts, Mechanic, Grinding Plates, Oil & Grease), Factory Operations (Loading Labour, Packing Material, Cleaning), Transport (Vehicle Fuel, Vehicle Repair, Freight), Office (Stationery, Mobile/Internet, Tea & Food), Workers Welfare (Food, Medical, Advance Adjustment) aur Miscellaneous (Other). Machine head khud ban jata hai jab machine ki service/repair likhi jati hai. Aur heads Expense Ledger page par add ho sakte hain. Har kharcha ek hi main + sub head ke neeche hota hai, aur reports head ke hisaab se group hoti hain (Expense Ledger, Cost Per Ton).",
       "خرچہ مرکزی ہیڈز اور ان کے ذیلی ہیڈز کے نیچے لکھا جاتا ہے۔ تیار ہیڈز یہ ہیں: سہولتیں (بجلی، ڈیزل، گیس، پانی)، مرمت (پرزے، مکینک، پسائی پلیٹیں، تیل و گریس)، فیکٹری امور (لوڈنگ مزدوری، پیکنگ مواد، صفائی)، نقل و حمل (گاڑی ایندھن، گاڑی مرمت، فریٹ)، دفتر (اسٹیشنری، موبائل/انٹرنیٹ، چائے و کھانا)، مزدور بہبود (کھانا، طبی، ایڈوانس ایڈجسٹمنٹ) اور متفرق (دیگر)۔ مشین ہیڈ خود بن جاتا ہے جب مشین کی سروس/مرمت لکھی جاتی ہے۔ مزید ہیڈز اخراجات لیجر صفحے پر شامل ہو سکتے ہیں۔ ہر خرچہ ایک ہی مرکزی + ذیلی ہیڈ کے نیچے ہوتا ہے، اور رپورٹس ہیڈ کے حساب سے گروپ ہوتی ہیں (اخراجات لیجر، فی ٹن لاگت)۔",
       "खर्च मुख्य हेड और उनके उप-हेड के नीचे लिखा जाता है। तैयार हेड ये हैं: सुविधाएँ (बिजली, डीज़ल, गैस, पानी), रखरखाव (पुर्ज़े, मकैनिक, पिसाई प्लेटें, तेल व ग्रीस), फ़ैक्टरी कार्य (लोडिंग मज़दूरी, पैकिंग सामग्री, सफ़ाई), परिवहन (गाड़ी ईंधन, गाड़ी मरम्मत, फ्रेट), कार्यालय (स्टेशनरी, मोबाइल/इंटरनेट, चाय व खाना), मज़दूर कल्याण (खाना, चिकित्सा, एडवांस समायोजन) और विविध (अन्य)। मशीन हेड ख़ुद बन जाता है जब मशीन की सर्विस/मरम्मत लिखी जाती है। और हेड खर्च लेजर पृष्ठ पर जोड़े जा सकते हैं। हर खर्च एक ही मुख्य + उप हेड के नीचे होता है, और रिपोर्ट हेड अनुसार समूह होती हैं (खर्च लेजर, प्रति टन लागत)।")),
 _K("head_dr_cr", "head", "parties",
    {"lat": ["debit credit", "debit kya", "credit kya", "debit ka matlab", "debit credit ka matlab"],
     "ur": ["ڈیبٹ کریڈٹ", "ڈیبٹ کیا"], "hi": ["डेबिट क्रेडिट", "डेबिट क्या"]},
    _L("Debit & Credit meaning", "Debit aur Credit ka matlab", "ڈیبٹ و کریڈٹ کا مطلب", "डेबिट व क्रेडिट का मतलब"),
    _L("What do debit and credit mean?", "debit credit ka matlab kya hai",
       "ڈیبٹ کریڈٹ کا مطلب کیا ہے؟", "डेबिट क्रेडिट का मतलब क्या है?"),
    _L("In a party khata: Debit = the party's dues go UP (a charge or a sale to them, or money we paid them). Credit = dues go DOWN (money they paid us, or rock/rent we owe them). The running balance is what matters: above zero means the party owes us; below zero means we owe the party.",
       "Party ke khatay mein: Debit = party ka dena BADH jata hai (koi charge ya un ko farokht, ya hum ne un ko paisay diye). Credit = dena KAM ho jata hai (unhon ne paisay diye, ya pathar/rent hum ne dena hai). Asal cheez running balance hai: balance zero se oopar ho to party ne dene hain; neeche ho to hum ne dene hain.",
       "پارٹی کے کھاتے میں: ڈیبٹ = پارٹی کا دینا بڑھ جاتا ہے (کوئی چارج یا ان کو فروخت، یا ہم نے ان کو پیسے دیے)۔ کریڈٹ = دینا کم ہو جاتا ہے (انہوں نے پیسے دیے، یا پتھر/کرایہ ہم نے دینا ہے)۔ اصل چیز چلتا بیلنس ہے: بیلنس صفر سے اوپر ہو تو پارٹی نے دینے ہیں؛ نیچے ہو تو ہم نے دینے ہیں۔",
       "पार्टी के खाते में: डेबिट = पार्टी का देना बढ़ जाता है (कोई शुल्क या उनको बिक्री, या हमने उनको पैसे दिए)। क्रेडिट = देना कम हो जाता है (उन्होंने पैसे दिए, या रॉक/किराया हमें देना है)। असली चीज़ चलता शेष है: शेष शून्य से ऊपर हो तो पार्टी ने देने हैं; नीचे हो तो हमें देने हैं।")),
 # ------------------------------------------------------------- flows ---
 _K("flow_grindprod", "flow", "grindprod",
    {"lat": ["grinding", "pisai", "production", "bags entry", "bag entry", "grinding entry", "production entry"],
     "ur": ["پسائی انٹری", "پیداوار انٹری"], "hi": ["पिसाई एंट्री", "उत्पादन एंट्री"]},
    _L("Where a Grinding & Production entry goes", "Grinding entry kahan jati hai",
       "پسائی انٹری کہاں جاتی ہے", "पिसाई एंट्री कहाँ जाती है"),
    _L("Where does a grinding bags entry go after saving?", "grinding bags ki entry add hony kay bad kaha jay gi",
       "پسائی تھیلوں کی انٹری محفوظ ہونے کے بعد کہاں جائے گی؟", "पिसाई बोरों की एंट्री सेव होने के बाद कहाँ जाएगी?"),
    _L("Grinding & Production is ONE entry for a grinding job: party (or Own), Day/Night shift, grade % and the powder bags + filter powder bags packed. On Save:\n1) The powder bags credit that party's Warehouse stock (bags ready; tons from the stamped bag weights).\n2) If the bags used were mill bags, the mill's bardana stock drops by the same count; party bags come out of that party's custody balance instead.\n3) Filter powder bags NEVER go to the job's party - they are the mill's own property: they credit the mill's Own filter-powder stock (Warehouse + Own Stock + Day-End). For the party they count as wastage - the party's recovery is its powder only.\n4) The bags land in the Day or Night column of the Phosphate Detail register and the Day-End split, by the shift on the entry.\n5) Theka workers with a per-bag rate earn on these bags.\n6) Rock consumption is worked out by itself: powder tons + wastage % - the party's rock waiting falls and the grinding loss % is figured.\n7) Dashboard ground/bags figures and Own Stock (for Own) update.\nNo money posts to any khata from this entry - the grinding charge is posted on the Vehicle OUT.",
       "Grinding & Production pisai ke kaam ki EK entry hai: party (ya Own), Day/Night shift, grade % aur bane hue powder bag + filter powder bag. Save karne ke baad:\n1) Powder bag us party ke Warehouse stock mein jama ho jate hain (bag tayyar; ton stamped bag wazan se).\n2) Bag mill ke thay to mill ka bardana utne bag kam ho jata hai; party ke bag thay to us party ki amanat se nikalte hain.\n3) Filter powder ke bag job wali party ko KABHI nahi jate - ye mill ki apni cheez hai: mill ke Own filter-powder stock mein jama hote hain (Warehouse + Own Stock + Day-End). Party ke liye ye wastage gine jate hain - party ko sirf us ka powder milta hai.\n4) Bag entry ki shift ke hisaab se Phosphate Detail register aur Day-End ke Day/Night hisse mein jate hain.\n5) Fi-bag rate wale theka mazdooron ki kamai in bagon par banti hai.\n6) Pathar ki khapat khud nikalti hai: powder ton + wastage % - party ka rock waiting kam hota hai aur grinding loss % banta hai.\n7) Dashboard ke ground/bags numbers aur Own Stock (Own ho to) update hote hain.\nIs entry se kisi khatay mein paisay NAHI lagte - pisai ka charge Vehicle OUT par lagta hai.",
       "پسائی و پیداوار پسائی کے کام کی ایک انٹری ہے: پارٹی (یا اپنا)، دن/رات شفٹ، گریڈ % اور بنے ہوئے پاؤڈر تھیلے + فلٹر پاؤڈر تھیلے۔ محفوظ کرنے کے بعد:\n1) پاؤڈر تھیلے اس پارٹی کے گودام اسٹاک میں جمع ہو جاتے ہیں (تھیلے تیار؛ ٹن مہر شدہ تھیلا وزن سے)۔\n2) تھیلے مل کے تھے تو مل کا باردانہ اتنے تھیلے کم ہو جاتا ہے؛ پارٹی کے تھیلے تھے تو اس پارٹی کی امانت سے نکلتے ہیں۔\n3) فلٹر پاؤڈر کے تھیلے کام والی پارٹی کو کبھی نہیں جاتے - یہ مل کی اپنی چیز ہے: مل کے اپنے فلٹر پاؤڈر اسٹاک میں جمع ہوتے ہیں (گودام + اپنا اسٹاک + دن اختتام)۔ پارٹی کے لیے یہ ضیاع گنے جاتے ہیں - پارٹی کو صرف اس کا پاؤڈر ملتا ہے۔\n4) تھیلے انٹری کی شفٹ کے حساب سے فاسفیٹ تفصیل رجسٹر اور دن اختتام کے دن/رات حصے میں جاتے ہیں۔\n5) فی تھیلا ریٹ والے ٹھیکہ مزدوروں کی کمائی ان تھیلوں پر بنتی ہے۔\n6) پتھر کی کھپت خود نکلتی ہے: پاؤڈر ٹن + ضیاع % - پارٹی کا منتظر پتھر کم ہوتا ہے اور پسائی نقصان % بنتا ہے۔\n7) ڈیش بورڈ کے پسائی/تھیلے اعداد اور اپنا اسٹاک (اپنا ہو تو) تازہ ہوتے ہیں۔\nاس انٹری سے کسی کھاتے میں پیسے نہیں لگتے - پسائی چارج گاڑی باہر پر لگتا ہے۔",
       "पिसाई व उत्पादन पिसाई के काम की एक एंट्री है: पार्टी (या अपना), दिन/रात शिफ़्ट, ग्रेड % और बने हुए पाउडर बोरे + फ़िल्टर पाउडर बोरे। सेव करने के बाद:\n1) पाउडर बोरे उस पार्टी के गोदाम स्टॉक में जमा हो जाते हैं (बोरे तैयार; टन अंकित बोरा वज़न से)।\n2) बोरे मिल के थे तो मिल का बरदाना उतने बोरे कम हो जाता है; पार्टी के बोरे थे तो उस पार्टी की धरोहर से निकलते हैं।\n3) फ़िल्टर पाउडर के बोरे काम वाली पार्टी को कभी नहीं जाते - यह मिल की अपनी चीज़ है: मिल के अपने फ़िल्टर पाउडर स्टॉक में जमा होते हैं (गोदाम + अपना स्टॉक + दिन-अंत)। पार्टी के लिए ये वेस्टेज गिने जाते हैं - पार्टी को केवल उसका पाउडर मिलता है।\n4) बोरे एंट्री की शिफ़्ट के हिसाब से फ़ॉस्फेट विवरण रजिस्टर और दिन-अंत के दिन/रात भाग में जाते हैं।\n5) प्रति बोरा दर वाले ठेका मज़दूरों की कमाई इन बोरों पर बनती है।\n6) रॉक की खपत ख़ुद निकलती है: पाउडर टन + वेस्टेज % - पार्टी का प्रतीक्षारत रॉक कम होता है और पिसाई नुकसान % बनता है।\n7) डैशबोर्ड के पिसाई/बोरे आँकड़े और अपना स्टॉक (अपना हो तो) ताज़ा होते हैं।\nइस एंट्री से किसी खाते में पैसे नहीं लगते - पिसाई शुल्क गाड़ी बाहर पर लगता है।")),
 _K("flow_vehicle_in", "flow", "vehicle_in",
    {"lat": ["vehicle in", "gari in", "gari andar", "rock in", "gari entry"],
     "ur": ["گاڑی اندر انٹری"], "hi": ["गाड़ी अंदर एंट्री"]},
    _L("Where a Vehicle In entry goes", "Vehicle In entry kahan jati hai",
       "گاڑی اندر انٹری کہاں جاتی ہے", "गाड़ी अंदर एंट्री कहाँ जाती है"),
    _L("What happens after a Vehicle In is saved?", "vehicle in save karne ke baad kya hota hai",
       "گاڑی اندر محفوظ کرنے کے بعد کیا ہوتا ہے؟", "गाड़ी अंदर सेव करने के बाद क्या होता है?"),
    _L("A Vehicle In entry records a vehicle bringing rock in (net weight only). On Save:\n1) The party's rock stock (rock waiting) rises by the net weight - see it in the Warehouse and the party's stock.\n2) The Rock purchase block exists ONLY on Own (Mine) entries: a client party's Vehicle In is a grinding arrival only - no rate, no buy-from, no credit ever posts from it. On an Own entry with a Rock rate written, a Purchase credit posts to the 'Buy from' seller's khata (net tons x rate = we owe them); Buy from = Own (Mine) itself (rock from your own mine) posts no credit. On the Mine rate the written vehicle rent also posts as a Rent credit to the seller - unless the rent is set to Driver, when it is a mill cash cost (Day-End / P&L) and no khata line is made; on the Factory ponch rate there is no rent and no freight.\n3) No loading charge ever posts on a Vehicle In.\n4) The voucher (gate pass) prints with 'Verified by' and the mill name; its WhatsApp copy goes to the party, the driver and the owner (auto-send when WhatsApp Cloud is set, otherwise one-tap buttons).\n5) The trip counts in the Dashboard vehicles and the Day-End rock-in figures.",
       "Vehicle In entry pathar lane wali gari ka record hai (sirf net weight). Save karne ke baad:\n1) Party ka rock stock (rock waiting) net weight jitna badh jata hai - Warehouse aur party ke stock mein dekhein.\n2) Rock purchase wala hissa SIRF Own (Mine) entry par hota hai: client party ki Vehicle In sirf pisai ki arrival hai - us se na rate, na buy-from, na koi credit kabhi nahi lagta. Own entry par Rock rate likha ho to 'Buy from' seller ke khatay mein Purchase credit lag jata hai (net ton x rate = hum ne dene hain); Buy from = Own (Mine) khud ho (apni mine ka pathar) to koi credit NAHI lagta. Mine rate par likha gaya gari rent bhi seller ke khatay mein Rent credit ban jata hai - siwaye jab rent Driver par set ho, tab wo mill ka cash kharcha hai (Day-End / P&L) aur koi khata line nahi banti; Factory ponch rate par na rent hota hai na freight.\n3) Vehicle In par loading charge kabhi NAHI lagta.\n4) Voucher (gate pass) 'Verified by' aur mill ke naam ke saath print hota hai; us ki WhatsApp copy party, driver aur owner ko jati hai (WhatsApp Cloud set ho to khud, warna one-tap buttons).\n5) Ye trip Dashboard ki gariyon aur Day-End ke rock-in numbers mein ginti hai.",
       "گاڑی اندر انٹری پتھر لانے والی گاڑی کا ریکارڈ ہے (صرف خالص وزن)۔ محفوظ کرنے کے بعد:\n1) پارٹی کا پتھر اسٹاک (منتظر پتھر) خالص وزن جتنا بڑھ جاتا ہے - گودام اور پارٹی کے اسٹاک میں دیکھیں۔\n2) خرید والا حصہ صرف اپنی (مائن) انٹری پر ہوتا ہے: گاہک پارٹی کی گاڑی اندر صرف پسائی کی آمد ہے — اس سے نہ ریٹ، نہ کس سے خریدا، نہ کوئی کریڈٹ کبھی نہیں لگتا۔ اپنی انٹری پر پتھر ریٹ لکھا ہو تو 'کس سے خریدا' بیچنے والے کے کھاتے میں خرید کریڈٹ لگ جاتا ہے (خالص ٹن × ریٹ = ہم نے دینے ہیں)؛ کس سے خریدا = اپنا خود ہو (اپنی کان کا پتھر) تو کوئی کریڈٹ نہیں لگتا۔ مائن ریٹ پر لکھا گیا گاڑی کرایہ بھی بیچنے والے کے کھاتے میں کرایہ کریڈٹ بن جاتا ہے — سوائے جب کرایہ ڈرائیور پر رکھا جائے، تب وہ مل کا نقد خرچ ہے (دن اختتام / نفع نقصان) اور کوئی کھاتا لائن نہیں بنتی؛ فیکٹری پہنچ ریٹ پر نہ کرایہ ہوتا ہے نہ فریٹ۔\n3) گاڑی اندر پر لوڈنگ چارج کبھی نہیں لگتا۔\n4) واؤچر (گیٹ پاس) 'تصدیق کنندہ' اور مل کے نام کے ساتھ پرنٹ ہوتا ہے؛ اس کی واٹس ایپ نقل پارٹی، ڈرائیور اور مالک کو جاتی ہے (واٹس ایپ کلاؤڈ مقرر ہو تو خود، ورنہ ایک ٹیپ بٹن)۔\n5) یہ ٹرپ ڈیش بورڈ کی گاڑیوں اور دن اختتام کے پتھر اندر اعداد میں گنتی ہے۔",
       "गाड़ी अंदर एंट्री रॉक लाने वाली गाड़ी का रिकॉर्ड है (केवल शुद्ध वज़न)। सेव करने के बाद:\n1) पार्टी का रॉक स्टॉक (प्रतीक्षारत रॉक) शुद्ध वज़न जितना बढ़ जाता है - गोदाम और पार्टी के स्टॉक में देखें।\n2) ख़रीद वाला भाग केवल अपनी (माइन) एंट्री पर होता है: ग्राहक पार्टी की गाड़ी अंदर केवल पिसाई की आमद है — उससे न दर, न किससे ख़रीदा, न कोई क्रेडिट कभी नहीं लगता। अपनी एंट्री पर रॉक दर लिखा हो तो 'किससे ख़रीदा' विक्रेता के खाते में ख़रीद क्रेडिट लग जाता है (शुद्ध टन × दर = हमें देने हैं); किससे ख़रीदा = अपना ख़ुद हो (अपनी खदान का रॉक) तो कोई क्रेडिट नहीं लगता। माइन दर पर लिखा गया गाड़ी किराया भी विक्रेता के खाते में किराया क्रेडिट बन जाता है — सिवाय जब किराया ड्राइवर पर रखा जाए, तब वह मिल का नकद खर्च है (दिन-अंत / लाभ-हानि) और कोई खाता लाइन नहीं बनती; फ़ैक्टरी पहुँच दर पर न किराया होता है न फ्रेट।\n3) गाड़ी अंदर पर लोडिंग शुल्क कभी नहीं लगता।\n4) वाउचर (गेट पास) 'सत्यापित द्वारा' और मिल के नाम के साथ प्रिंट होता है; उसकी व्हाट्सएप कॉपी पार्टी, ड्राइवर और मालिक को जाती है (व्हाट्सएप क्लाउड सेट हो तो ख़ुद, वरना एक टैप बटन)।\n5) यह ट्रिप डैशबोर्ड की गाड़ियों और दिन-अंत के रॉक-अंदर आँकड़ों में गिनी जाती है।")),
 _K("flow_vehicle_out", "flow", "vehicle_out",
    {"lat": ["vehicle out", "gari out", "dispatch", "rawangi", "gari bahar"],
     "ur": ["گاڑی باہر انٹری", "روانگی"], "hi": ["गाड़ी बाहर एंट्री", "रवानगी"]},
    _L("Where a Vehicle Out entry goes", "Vehicle Out entry kahan jati hai",
       "گاڑی باہر انٹری کہاں جاتی ہے", "गाड़ी बाहर एंट्री कहाँ जाती है"),
    _L("What happens after a Vehicle Out is saved?", "gari out ki entry save ke baad kahan kahan asar dalti hai",
       "گاڑی باہر انٹری محفوظ ہونے کے بعد کہاں کہاں اثر ڈالتی ہے؟", "गाड़ी बाहर एंट्री सेव होने के बाद कहाँ कहाँ असर डालती है?"),
    _L("A Vehicle Out entry dispatches powder on a vehicle (net weight + bags). On Save:\n1) The party's powder stock falls by the dispatch - Warehouse and party stock update.\n2) If a Grinding rate was written, the grinding charge (net tons x rate) posts as a debit under the Grinding head in the party khata. Left blank, no charge posts - an already-charged lot is never charged twice.\n3) Loading charges post to the khata when the party bears them, otherwise they become the mill's cost in the P&L; freight the same way, by its payer.\n4) If an Order was linked, its fulfilled quantity rises and the remaining falls.\n5) Theka workers with a per-ton rate earn on these OUT tons.\n6) The voucher prints; WhatsApp copies go to the party, the driver and the owner.\n7) Own dispatch sale (optional): with Party = Own (Mine), filling 'Powder sold to' + 'Sale rate /ton' records the sale ON this trip - the receivable (net tons x rate) posts in the buyer's khata from the trip itself, exactly once, and the stock leaves with this dispatch; do NOT enter the same sale again as a Ledger Sell. On Own the Grinding rate does not apply (it is our own material) - it is hidden and never charges. If a Ledger Sell and a trip sale look like the same sale, saving first asks for confirmation, and a confirmed duplicate is noted in the History (audit).",
       "Vehicle Out entry gari par powder rawana karti hai (net weight + bags). Save karne ke baad:\n1) Party ka powder stock rawangi jitna kam ho jata hai - Warehouse aur party stock update hote hain.\n2) Grinding rate likha ho to pisai charge (net ton x rate) party ke khatay mein Grinding head ke neeche debit lag jata hai. Khali chora ho to koi charge NAHI lagta - jis lot ka charge pehle lag chuka ho wo dobara nahi lagta.\n3) Loading charges: party ke zimme hon to khatay mein, warna P&L mein mill ka kharcha; freight bhi isi tarah, us ke dene wale ke hisaab se.\n4) Order link kiya ho to us ka fulfilled badhta hai aur remaining kam hota hai.\n5) Fi-ton rate wale theka mazdooron ki kamai in OUT ton par banti hai.\n6) Voucher print hota hai; WhatsApp copy party, driver aur owner ko jati hai.\n7) Own rawangi par sale (optional): Party = Own (Mine) ho to 'Powder sold to' + 'Sale rate /ton' bharne se sale ISI trip par likh jati hai - udhaar (net ton x rate) buyer ke khatay mein trip se hi lag jata hai, sirf ek dafa, aur stock bhi isi rawangi se nikalta hai; wahi sale Ledger Sell ke tor par DOBARA na lagayein. Own par Grinding rate NAHI lagta (hamara apna maal hai) - wo chhupa rehta hai aur charge kabhi nahi banta. Ledger Sell aur trip sale ek hi sale lagay to save pehle confirmation mangta hai, aur confirm ki hui duplicate History (audit) mein note ho jati hai.",
       "گاڑی باہر انٹری گاڑی پر پاؤڈر روانہ کرتی ہے (خالص وزن + تھیلے)۔ محفوظ کرنے کے بعد:\n1) پارٹی کا پاؤڈر اسٹاک روانگی جتنا کم ہو جاتا ہے - گودام اور پارٹی اسٹاک تازہ ہوتے ہیں۔\n2) پسائی ریٹ لکھا ہو تو پسائی چارج (خالص ٹن × ریٹ) پارٹی کے کھاتے میں پسائی ہیڈ کے نیچے ڈیبٹ لگ جاتا ہے۔ خالی چھوڑا ہو تو کوئی چارج نہیں لگتا - جس لاٹ کا چارج پہلے لگ چکا ہو وہ دوبارہ نہیں لگتا۔\n3) لوڈنگ چارجز: پارٹی کے ذمے ہوں تو کھاتے میں، ورنہ نفع نقصان میں مل کا خرچہ؛ فریٹ بھی اسی طرح، اس کے دینے والے کے حساب سے۔\n4) آرڈر منسلک کیا ہو تو اس کا مکمل بڑھتا ہے اور باقی کم ہوتا ہے۔\n5) فی ٹن ریٹ والے ٹھیکہ مزدوروں کی کمائی ان باہر ٹن پر بنتی ہے۔\n6) واؤچر پرنٹ ہوتا ہے؛ واٹس ایپ نقل پارٹی، ڈرائیور اور مالک کو جاتی ہے۔\n7) اپنی روانگی پر فروخت (اختیاری): پارٹی = اپنا ہو تو 'کس کو فروخت' + 'فروخت ریٹ' بھرنے سے فروخت اسی ٹرپ پر لکھ جاتی ہے - ادھار (خالص ٹن × ریٹ) خریدار کے کھاتے میں ٹرپ سے ہی لگ جاتا ہے، صرف ایک دفعہ، اور اسٹاک بھی اسی روانگی سے نکلتا ہے؛ وہی فروخت کھاتہ فروخت کے طور پر دوبارہ نہ لگائیں۔ اپنے مال پر پسائی ریٹ نہیں لگتا - وہ چھپا رہتا ہے اور چارج کبھی نہیں بنتا۔ کھاتہ فروخت اور ٹرپ فروخت ایک ہی فروخت لگیں تو محفوظ پہلے تصدیق مانگتا ہے، اور تصدیق شدہ نقل تاریخ (آڈٹ) میں درج ہو جاتی ہے۔",
       "गाड़ी बाहर एंट्री गाड़ी पर पाउडर रवाना करती है (शुद्ध वज़न + बोरे)। सेव करने के बाद:\n1) पार्टी का पाउडर स्टॉक रवानगी जितना कम हो जाता है - गोदाम और पार्टी स्टॉक ताज़ा होते हैं।\n2) पिसाई दर लिखा हो तो पिसाई शुल्क (शुद्ध टन × दर) पार्टी के खाते में पिसाई हेड के नीचे डेबिट लग जाता है। खाली छोड़ा हो तो कोई शुल्क नहीं लगता - जिस लॉट का शुल्क पहले लग चुका हो वह दोबारा नहीं लगता।\n3) लोडिंग शुल्क: पार्टी के ज़िम्मे हों तो खाते में, वरना लाभ-हानि में मिल का खर्च; फ्रेट भी इसी तरह, उसके देने वाले के हिसाब से।\n4) ऑर्डर जोड़ा हो तो उसका पूरा बढ़ता है और शेष कम होता है।\n5) प्रति टन दर वाले ठेका मज़दूरों की कमाई इन बाहर टन पर बनती है।\n6) वाउचर प्रिंट होता है; व्हाट्सएप कॉपी पार्टी, ड्राइवर और मालिक को जाती है।\n7) अपनी रवानगी पर बिक्री (वैकल्पिक): पार्टी = अपना हो तो 'किसे बेचा' + 'बिक्री दर' भरने से बिक्री इसी ट्रिप पर लिख जाती है - उधार (शुद्ध टन × दर) ख़रीदार के खाते में ट्रिप से ही लग जाता है, केवल एक बार, और स्टॉक भी इसी रवानगी से निकलता है; वही बिक्री खाता बिक्री के रूप में दोबारा न लगाएँ। अपने माल पर पिसाई दर नहीं लगती - वह छिपी रहती है और शुल्क कभी नहीं बनता। खाता बिक्री और ट्रिप बिक्री एक ही बिक्री लगें तो सेव पहले पुष्टि माँगता है, और पुष्टि की हुई नक़ल इतिहास (ऑडिट) में दर्ज हो जाती है।")),
 _K("flow_bags", "flow", "warehouse",
    {"lat": ["bardana", "party bags", "bags movement", "bag movement", "khali bag", "empty bags"],
     "ur": ["باردانہ", "پارٹی تھیلے"], "hi": ["बरदाना", "पार्टी बोरे"]},
    _L("Where a bags entry goes", "Bags ki entry kahan jati hai",
       "تھیلوں کی انٹری کہاں جاتی ہے", "बोरों की एंट्री कहाँ जाती है"),
    _L("What happens after a bags entry is saved?", "bardana entry save ke baad kya hota hai",
       "باردانہ انٹری محفوظ ہونے کے بعد کیا ہوتا ہے؟", "बरदाना एंट्री सेव होने के बाद क्या होता है?"),
    _L("Empty bags are recorded in the Warehouse page's ONE Bags card. Mill bags (bardana) are the mill's own empty-bag stock: IN raises it, OUT lowers it, and production packed in mill bags lowers it too - below 100 a low-stock warning shows. Party bags are a party's own bags kept at the mill: received-from-party raises that party's custody balance, returned-to-party lowers it. The two balances are always shown separately, and production consumes mill bardana only.",
       "Khali bag Warehouse page ke EK hi Bags card mein likhe jate hain. Mill bags (bardana) mill ke apne khali bag hain: IN se badhte hain, OUT se kam hote hain, aur mill bagon mein bhari production se bhi kam hote hain - 100 se kam hon to low-stock warning ati hai. Party bags party ke apne bag hain jo mill ke paas rakhe hain: party se mile to us party ki amanat badhti hai, wapas kiye to kam hoti hai. Dono balance hamesha alag alag dikhte hain, aur production mein sirf mill ka bardana lagta hai.",
       "خالی تھیلے گودام صفحے کے ایک ہی تھیلے کارڈ میں لکھے جاتے ہیں۔ مل کے تھیلے (باردانہ) مل کے اپنے خالی تھیلے ہیں: اندر سے بڑھتے ہیں، باہر سے کم ہوتے ہیں، اور مل تھیلوں میں بھری پیداوار سے بھی کم ہوتے ہیں - 100 سے کم ہوں تو کم اسٹاک وارننگ آتی ہے۔ پارٹی تھیلے پارٹی کے اپنے تھیلے ہیں جو مل کے پاس رکھے ہیں: پارٹی سے ملے تو اس پارٹی کی امانت بڑھتی ہے، واپس کیے تو کم ہوتی ہے۔ دونوں بیلنس ہمیشہ الگ الگ دکھتے ہیں، اور پیداوار میں صرف مل کا باردانہ لگتا ہے۔",
       "खाली बोरे गोदाम पृष्ठ के एक ही बोरे कार्ड में लिखे जाते हैं। मिल के बोरे (बरदाना) मिल के अपने खाली बोरे हैं: अंदर से बढ़ते हैं, बाहर से कम होते हैं, और मिल बोरों में भरे उत्पादन से भी कम होते हैं - 100 से कम हों तो कम स्टॉक चेतावनी आती है। पार्टी बोरे पार्टी के अपने बोरे हैं जो मिल के पास रखे हैं: पार्टी से मिले तो उस पार्टी की धरोहर बढ़ती है, वापस किए तो कम होती है। दोनों शेष हमेशा अलग अलग दिखते हैं, और उत्पादन में केवल मिल का बरदाना लगता है।")),
 _K("flow_payment", "flow", "payments",
    {"lat": ["payment", "adaigi", "payment entry"],
     "ur": ["ادائیگی انٹری"], "hi": ["भुगतान एंट्री"]},
    _L("Where a Payment entry goes", "Payment entry kahan jati hai",
       "ادائیگی انٹری کہاں جاتی ہے", "भुगतान एंट्री कहाँ जाती है"),
    _L("What happens after a payment is saved?", "payment save ke baad kahan jati hai",
       "ادائیگی محفوظ ہونے کے بعد کہاں جاتی ہے؟", "भुगतान सेव होने के बाद कहाँ जाती है?"),
    _L("A Payment entry is money between the mill and a party. On Save:\n1) In the party khata: money IN (the party paid us) posts as a credit and the balance falls; money OUT (we paid the party) posts as a debit.\n2) By its method it also lands in the Cash Book (cash) or Bank Book (bank), and online (JazzCash / Easypaisa / Raast) and cheque payments are kept by their reference numbers.\n3) A cheque payment also sits in the Cheque Register; if that cheque later bounces, the payment drops out of the khata by itself and the balance reopens.",
       "Payment entry mill aur party ke darmiyan paisay ki entry hai. Save karne ke baad:\n1) Party ke khatay mein: paisay IN (party ne diye) credit lagta hai aur balance kam hota hai; paisay OUT (hum ne diye) debit lagta hai.\n2) Method ke hisaab se ye Cash Book (cash) ya Bank Book (bank) mein bhi jati hai, aur online (JazzCash / Easypaisa / Raast) aur cheque wali payment reference number ke saath rehti hai.\n3) Cheque wali payment Cheque Register mein bhi hoti hai; wo cheque baad mein bounce ho jaye to payment khatay se khud hatt jati hai aur balance dobara khul jata hai.",
       "ادائیگی انٹری مل اور پارٹی کے درمیان پیسوں کی انٹری ہے۔ محفوظ کرنے کے بعد:\n1) پارٹی کے کھاتے میں: پیسے اندر (پارٹی نے دیے) کریڈٹ لگتا ہے اور بیلنس کم ہوتا ہے؛ پیسے باہر (ہم نے دیے) ڈیبٹ لگتا ہے۔\n2) طریقے کے حساب سے یہ کیش بک (نقد) یا بینک بک (بینک) میں بھی جاتی ہے، اور آن لائن (JazzCash / Easypaisa / Raast) اور چیک والی ادائیگی حوالہ نمبر کے ساتھ رہتی ہے۔\n3) چیک والی ادائیگی چیک رجسٹر میں بھی ہوتی ہے؛ وہ چیک بعد میں باؤنس ہو جائے تو ادائیگی کھاتے سے خود ہٹ جاتی ہے اور بیلنس دوبارہ کھل جاتا ہے۔",
       "भुगतान एंट्री मिल और पार्टी के बीच पैसों की एंट्री है। सेव करने के बाद:\n1) पार्टी के खाते में: पैसे अंदर (पार्टी ने दिए) क्रेडिट लगता है और शेष कम होता है; पैसे बाहर (हमने दिए) डेबिट लगता है।\n2) तरीके के हिसाब से यह कैश बुक (नकद) या बैंक बुक (बैंक) में भी जाती है, और ऑनलाइन (JazzCash / Easypaisa / Raast) और चेक वाला भुगतान संदर्भ नंबर के साथ रहता है।\n3) चेक वाला भुगतान चेक रजिस्टर में भी होता है; वह चेक बाद में बाउंस हो जाए तो भुगतान खाते से ख़ुद हट जाता है और शेष दोबारा खुल जाता है।")),
 _K("flow_expense", "flow", "expenses",
    {"lat": ["expense", "kharcha", "expense entry", "kharcha entry"],
     "ur": ["خرچہ انٹری"], "hi": ["खर्च एंट्री"]},
    _L("Where an Expense entry goes", "Expense entry kahan jati hai",
       "خرچہ انٹری کہاں جاتی ہے", "खर्च एंट्री कहाँ जाती है"),
    _L("What happens after an expense is saved?", "expense lagane se kahan asar parta hai",
       "خرچہ لگانے سے کہاں اثر پڑتا ہے؟", "खर्च लगाने से कहाँ असर पड़ता है?"),
    _L("An Expense entry is a factory cost under a main + sub head. On Save:\n1) It posts ONCE in the Expense Ledger under its head.\n2) The same single posting feeds the Cash Book and the monthly Profit & Loss as a cost - it is never counted twice.\n3) Paid By matters: a Manager-paid CASH expense above the approval limit (Settings -> Cash Rules, default Rs 25,000) stays pending until the Owner approves it.\n4) It appears in the Cost Per Ton report, grouped by head.\nMachine service/repair costs also land here, under the Machine head, exactly once.",
       "Expense entry factory ka kharcha hai, ek main + sub head ke neeche. Save karne ke baad:\n1) Ye Expense Ledger mein apne head ke neeche EK dafa lagta hai.\n2) Wohi ek posting Cash Book aur mahana Profit & Loss mein cost ke tor par jati hai - dohra kabhi NAHI ginta.\n3) Paid By ahem hai: Manager ka diya hua CASH kharcha approval limit (Settings -> Cash Rules, default Rs 25,000) se bara ho to Owner ki approval tak pending rehta hai.\n4) Ye Cost Per Ton report mein head ke hisaab se ata hai.\nMachine service/repair ka kharcha bhi yahin Machine head mein ek hi dafa lagta hai.",
       "خرچہ انٹری فیکٹری کا خرچہ ہے، ایک مرکزی + ذیلی ہیڈ کے نیچے۔ محفوظ کرنے کے بعد:\n1) یہ اخراجات لیجر میں اپنے ہیڈ کے نیچے ایک دفعہ لگتا ہے۔\n2) وہی ایک انٹری کیش بک اور ماہانہ نفع نقصان میں لاگت کے طور پر جاتی ہے - دوہرا کبھی نہیں گنتا۔\n3) ادا کنندہ اہم ہے: منیجر کا دیا ہوا نقد خرچہ منظوری حد (ترتیبات -> نقد اصول، طے شدہ Rs 25,000) سے بڑا ہو تو مالک کی منظوری تک زیر التوا رہتا ہے۔\n4) یہ فی ٹن لاگت رپورٹ میں ہیڈ کے حساب سے آتا ہے۔\nمشین سروس/مرمت کا خرچہ بھی یہیں مشین ہیڈ میں ایک ہی دفعہ لگتا ہے۔",
       "खर्च एंट्री फ़ैक्टरी का खर्च है, एक मुख्य + उप हेड के नीचे। सेव करने के बाद:\n1) यह खर्च लेजर में अपने हेड के नीचे एक बार लगता है।\n2) वही एक एंट्री कैश बुक और मासिक लाभ-हानि में लागत के रूप में जाती है - दोहरा कभी नहीं गिनता।\n3) देने वाला महत्वपूर्ण है: मैनेजर का दिया हुआ नकद खर्च स्वीकृति सीमा (सेटिंग्स -> नकद नियम, डिफ़ॉल्ट Rs 25,000) से बड़ा हो तो मालिक की स्वीकृति तक लंबित रहता है।\n4) यह प्रति टन लागत रिपोर्ट में हेड अनुसार आता है।\nमशीन सर्विस/मरम्मत का खर्च भी यहीं मशीन हेड में एक ही बार लगता है।")),
 _K("flow_cashhand", "flow", "cashinhand",
    {"lat": ["cash in hand", "handover", "haath mein cash", "cash hand"],
     "ur": ["ہاتھ میں نقد", "حوالگی"], "hi": ["हाथ में नकद", "हैंडओवर"]},
    _L("How Cash in Hand moves", "Cash in Hand ka flow", "ہاتھ میں نقد کا بہاؤ", "हाथ में नकद का प्रवाह"),
    _L("What happens in Cash in Hand?", "cash in hand mein entry ke baad kya hota hai",
       "ہاتھ میں نقد میں انٹری کے بعد کیا ہوتا ہے؟", "हाथ में नकद में एंट्री के बाद क्या होता है?"),
    _L("Cash in Hand tracks cash physically held by people. A handover is a TRANSFER, never an expense: on Save the holder's balance-in-hand rises and the handover waits for the holder's own acknowledgement; what the holder spends lowers it again. If a holder crosses the holder limit (Settings -> Cash Rules, default Rs 200,000) a warning shows. A cash count (ginti) compares the counted cash with the book balance, and any difference moves only through an owner-approved adjustment.",
       "Cash in Hand logon ke paas asal rakhe cash ka hisaab hai. Handover ek TRANSFER hai, kharcha KABHI nahi: Save par holder ka balance-in-hand badh jata hai aur handover holder ki apni tasdeeq ka intezaar karta hai; holder jo kharch kare us se balance kam hota hai. Holder limit (Settings -> Cash Rules, default Rs 200,000) cross ho to warning ati hai. Cash ginti gine gaye cash ko book balance se milati hai, aur farq sirf owner-approved adjustment se badalta hai.",
       "ہاتھ میں نقد لوگوں کے پاس اصل رکھے نقد کا حساب ہے۔ حوالگی ایک منتقلی ہے، خرچہ کبھی نہیں: محفوظ پر حامل کا ہاتھ بیلنس بڑھ جاتا ہے اور حوالگی حامل کی اپنی تصدیق کا انتظار کرتی ہے؛ حامل جو خرچ کرے اس سے بیلنس کم ہوتا ہے۔ حامل حد (ترتیبات -> نقد اصول، طے شدہ Rs 200,000) پار ہو تو وارننگ آتی ہے۔ نقد گنتی گنے گئے نقد کو کتابی بیلنس سے ملاتی ہے، اور فرق صرف مالک منظور شدہ ایڈجسٹمنٹ سے بدلتا ہے۔",
       "हाथ में नकद लोगों के पास असल रखे नकद का हिसाब है। हैंडओवर एक स्थानांतरण है, खर्च कभी नहीं: सेव पर धारक का हाथ शेष बढ़ जाता है और हैंडओवर धारक की अपनी पुष्टि का इंतज़ार करता है; धारक जो खर्च करे उससे शेष कम होता है। धारक सीमा (सेटिंग्स -> नकद नियम, डिफ़ॉल्ट Rs 200,000) पार हो तो चेतावनी आती है। नकद गिनती गिने गए नकद को किताबी शेष से मिलाती है, और फ़र्क़ सिर्फ़ मालिक स्वीकृत समायोजन से बदलता है।")),
 _K("flow_attendance", "flow", "attendance",
    {"lat": ["attendance", "hazri", "leave", "chutti", "punch"],
     "ur": ["حاضری", "چھٹی"], "hi": ["हाज़िरी", "छुट्टी"]},
    _L("Where attendance goes", "Hazri kahan jati hai", "حاضری کہاں جاتی ہے", "हाज़िरी कहाँ जाती है"),
    _L("What happens after attendance is marked?", "hazri lagane ke baad kya hota hai",
       "حاضری لگانے کے بعد کیا ہوتا ہے؟", "हाज़िरी लगाने के बाद क्या होता है?"),
    _L("Attendance is marked by hand or arrives from the biometric machines as punches. From the department's shift times, overtime is figured by itself and added to the worker's dues. Leave is recorded in the Leave register: an approved unpaid leave cuts salary by itself; overtime and attendance-correction requests take effect only after the Owner approves them on the Leave & Approvals page.",
       "Hazri haath se lagti hai ya biometric machines se punch ki surat mein ati hai. Department ke shift time se overtime khud banta hai aur mazdoor ke dues mein jama ho jata hai. Chutti Leave register mein likhi jati hai: approved unpaid chutti salary se khud kat-ti hai; overtime aur hazri-correction ki darkhwastein Leave & Approvals page par Owner ki approval ke baad hi lagti hain.",
       "حاضری ہاتھ سے لگتی ہے یا بایومیٹرک مشینوں سے پنچ کی صورت میں آتی ہے۔ شعبے کے شفٹ اوقات سے اوور ٹائم خود بنتا ہے اور مزدور کے واجبات میں جمع ہو جاتا ہے۔ چھٹی چھٹی رجسٹر میں لکھی جاتی ہے: منظور شدہ بلا معاوضہ چھٹی تنخواہ سے خود کٹتی ہے؛ اوور ٹائم اور حاضری درستگی کی درخواستیں چھٹی و منظوری صفحے پر مالک کی منظوری کے بعد ہی لگتی ہیں۔",
       "हाज़िरी हाथ से लगती है या बायोमेट्रिक मशीनों से पंच के रूप में आती है। विभाग के शिफ़्ट समय से ओवरटाइम ख़ुद बनता है और मज़दूर के देय में जमा हो जाता है। छुट्टी छुट्टी रजिस्टर में लिखी जाती है: स्वीकृत बिना वेतन छुट्टी वेतन से ख़ुद कटती है; ओवरटाइम और हाज़िरी सुधार के अनुरोध छुट्टी व स्वीकृति पृष्ठ पर मालिक की स्वीकृति के बाद ही लगते हैं।")),
 _K("flow_ginti", "flow", "warehouse",
    {"lat": ["ginti", "stock count", "godam ginti", "adjustment", "stock adjustment"],
     "ur": ["گنتی", "گودام گنتی"], "hi": ["गिनती", "गोदाम गिनती"]},
    _L("How a stock count adjusts stock", "Godam Ginti ka flow", "گودام گنتی کا بہاؤ", "गोदाम गिनती का प्रवाह"),
    _L("What happens after a stock count?", "godam ginti ke baad kya hota hai",
       "گودام گنتی کے بعد کیا ہوتا ہے؟", "गोदाम गिनती के बाद क्या होता है?"),
    _L("A Godam Ginti (stock count) writes the physically counted stock. The difference against the book stock becomes a stock adjustment, and the stock figures change ONLY when the Owner approves that adjustment on the Warehouse page - the difference and the decision stay in the audit record.",
       "Godam Ginti mein asal gina gaya stock likha jata hai. Book stock se farq ek stock adjustment ban jata hai, aur stock ke numbers SIRF tab badalte hain jab Owner Warehouse page par wo adjustment approve kar de - farq aur faisla audit record mein rehta hai.",
       "گودام گنتی میں اصل گنا گیا اسٹاک لکھا جاتا ہے۔ کتابی اسٹاک سے فرق ایک اسٹاک ایڈجسٹمنٹ بن جاتا ہے، اور اسٹاک کے اعداد صرف تب بدلتے ہیں جب مالک گودام صفحے پر وہ ایڈجسٹمنٹ منظور کر دے - فرق اور فیصلہ آڈٹ ریکارڈ میں رہتا ہے۔",
       "गोदाम गिनती में असल गिना गया स्टॉक लिखा जाता है। किताबी स्टॉक से फ़र्क़ एक स्टॉक समायोजन बन जाता है, और स्टॉक के आँकड़े सिर्फ़ तब बदलते हैं जब मालिक गोदाम पृष्ठ पर वह समायोजन स्वीकृत कर दे - फ़र्क़ और फ़ैसला ऑडिट रिकॉर्ड में रहता है।")),
 _K("flow_demo", "flow", "data",
    {"lat": ["demo", "demo data", "sample data"],
     "ur": ["ڈیمو"], "hi": ["डेमो"]},
    _L("What Demo Data does", "Demo Data kya karta hai", "ڈیمو ڈیٹا کیا کرتا ہے", "डेमो डेटा क्या करता है"),
    _L("What happens when demo data is loaded?", "demo data load karne se kya hota hai",
       "ڈیمو ڈیٹا لوڈ کرنے سے کیا ہوتا ہے؟", "डेमो डेटा लोड करने से क्या होता है?"),
    _L("Demo Data (on the Data page, Owner only) loads sample parties - their names start with DEMO - and sample entries, so every feature can be tried safely. Removing it from the same card deletes all demo data cleanly and the totals go back to exactly what they were; real data is never touched.",
       "Demo Data (Data page par, sirf Owner) sample parties - un ke naam DEMO se shuru hote hain - aur sample entries load karta hai, taake har feature mehfooz tareeqay se try ho sake. Usi card se Remove karne par saara demo data saaf delete ho jata hai aur totals bilkul pehle jaise ho jate hain; asal data ko kuch NAHI hota.",
       "ڈیمو ڈیٹا (ڈیٹا صفحے پر، صرف مالک) نمونہ پارٹیاں - ان کے نام DEMO سے شروع ہوتے ہیں - اور نمونہ انٹریاں لوڈ کرتا ہے، تاکہ ہر فیچر محفوظ طریقے سے آزمایا جا سکے۔ اسی کارڈ سے ہٹانے پر سارا ڈیمو ڈیٹا صاف حذف ہو جاتا ہے اور مجموعے بالکل پہلے جیسے ہو جاتے ہیں؛ اصل ڈیٹا کو کچھ نہیں ہوتا۔",
       "डेमो डेटा (डेटा पृष्ठ पर, केवल मालिक) नमूना पार्टियाँ - उनके नाम DEMO से शुरू होते हैं - और नमूना एंट्रियाँ लोड करता है, ताकि हर फ़ीचर सुरक्षित तरीके से आज़माया जा सके। उसी कार्ड से हटाने पर सारा डेमो डेटा साफ़ हट जाता है और योग बिल्कुल पहले जैसे हो जाते हैं; असली डेटा को कुछ नहीं होता।")),
 _K("flow_owntrade", "flow", "ownstock",
    {"lat": ["own trade", "apni khareed", "apni farokht", "own purchase", "own sale",
             "ledger buy", "ledger sell", "direct trade", "gate sale"],
     "ur": ["اپنی تجارت", "اپنی خرید", "براہ راست تجارت"], "hi": ["अपना व्यापार", "अपनी ख़रीद", "सीधा व्यापार"]},
    _L("Where an own buy/sell entry goes", "Apni khareed/farokht kahan jati hai",
       "اپنی خرید/فروخت کہاں جاتی ہے", "अपनी ख़रीद/बिक्री कहाँ जाती है"),
    _L("What happens after an own purchase or sale?", "apni khareed ya farokht save ke baad kya hota hai",
       "اپنی خرید یا فروخت محفوظ ہونے کے بعد کیا ہوتا ہے؟", "अपनी ख़रीद या बिक्री सेव होने के बाद क्या होता है?"),
    _L("Own buying and selling has FOUR doors, and every movement is counted exactly once. (1) GATE buy: rock bought on an Own (Mine) Vehicle In entry (rock rate, with the Buy-from seller) - the payable posts in the seller's khata and the rock stock goes to Own; there is no separate purchase row. A client party's Vehicle In is never a purchase - clients bring their own rock for grinding. (2) SELLING own powder has TWO doors, never both for the same goods: (a) the LEDGER door - enter the powder Sell in the buyer's Party Ledger (the receivable, the invoice and the own-stock-out all post there, exactly once) and record the vehicle on Vehicle Out as a GATE PASS (for a buyer the trip moves NO stock and NO money); or (b) the TRIP door - on an Own dispatch (Party = Own (Mine)) record the sale ON the trip itself, 'Powder sold to' + 'Sale rate /ton': the receivable posts in the buyer's khata from the trip row, exactly once, the stock leaves with the dispatch, and NO invoice is made. The system warns when a Ledger Sell and a trip sale look like the same sale, and a confirmed duplicate is written in the History (audit). A toll return deducts the client's own powder stock from the trip, and an Own dispatch (no party) deducts own stock. (3) LEDGER buy/sell: on a party's Ledger page, Add Buy / Add Sell is for goods that moved WITHOUT a gate record - step 1 pick the item: Rock (billed after the deduction %, rock stock moves), Powder (tons/bags, powder stock moves, a sale makes an invoice) or Other item (name + quantity + unit + rate: money posts to the khata only, NO stock moves). (4) DIRECT trade, added from the Own Stock page: buy from party A and sell to party B in ONE deal - the goods never enter the mill, so neither leg moves any stock; each leg posts to its own party's khata and the deal line shows the profit. The Own Stock page holds the stock position plus the combined trade history, every row tagged Gate / Ledger / Excel / Direct.",
       "Apni khareed-farokht ke CHAAR darwazay hain, aur har movement sirf EK dafa ginta hai. (1) GATE khareed: Own (Mine) Vehicle In entry par kharida pathar (rock rate, Buy-from seller ke saath) - dena seller ke khatay mein lagta hai aur pathar stock Own (apna) rehta hai; alag purchase row NAHI banti. Client party ki Vehicle In kabhi khareed NAHI hoti - client apna pathar pisai ke liye lata hai. (2) Apna powder BECHNE ke DO darwazay hain, ek hi maal ke liye dono KABHI nahi: (a) LEDGER darwaza - buyer ke Party Ledger mein powder Sell entry lagayein (udhaar, invoice aur apna stock-out teeno wahi lagte hain, sirf ek dafa) aur Vehicle Out par gari sirf GATE PASS ke tor par likhein (buyer ki trip se na stock move hota hai, na raqam); ya (b) TRIP darwaza - Own rawangi (Party = Own (Mine)) par sale ISI trip par likhein, 'Powder sold to' + 'Sale rate /ton': udhaar buyer ke khatay mein trip row se lag jata hai, sirf ek dafa, stock isi rawangi se nikalta hai, aur invoice NAHI banta. Ledger Sell aur trip sale ek hi sale lagay to system warning deta hai, aur confirm ki hui duplicate History (audit) mein likh jati hai. Toll wapis par trip client ke apne powder stock se kam karti hai, aur Own rawangi (koi party nahi) par apna stock kam hota hai. (3) LEDGER khareed/farokht: party ke Ledger page par Add Buy / Add Sell un cheezon ke liye hai jo gate record ke BAGHAIR move huin - step 1 item chunein: Rock (deduction % ke baad billed, rock stock move hota hai), Powder (ton/bag, powder stock move hota hai, sale par invoice banta hai) ya Other item (naam + miqdar + unit + rate: raqam sirf khatay mein lagti hai, stock BILKUL nahi move hota). (4) DIRECT trade, Own Stock page se add hota hai: party A se khareed aur party B ko farokht EK deal mein - maal mill mein ata hi NAHI, is liye koi leg stock nahi hilati; har leg apni party ke khatay mein lagti hai aur deal line par profit dikhta hai. Own Stock page par stock position aur mili hui trade history hai, har row par Gate / Ledger / Excel / Direct ka tag.",
       "اپنی خرید و فروخت کے چار دروازے ہیں، اور ہر حرکت صرف ایک دفعہ گنتی ہے۔ (1) گیٹ خرید: اپنی گاڑی اندر انٹری پر خریدا پتھر (پتھر ریٹ، کس سے خریدا بیچنے والے کے ساتھ) - دینی رقم بیچنے والے کے کھاتے میں لگتی ہے اور پتھر اسٹاک اپنا رہتا ہے؛ الگ خرید قطار نہیں بنتی۔ گاہک پارٹی کی گاڑی اندر کبھی خرید نہیں ہوتی — گاہک اپنا پتھر پسائی کے لیے لاتا ہے۔ (2) اپنا پاؤڈر بیچنے کے دو دروازے ہیں، ایک ہی مال کے لیے دونوں کبھی نہیں: (a) خریدار کے پارٹی کھاتے میں پاؤڈر فروخت انٹری لگائیں — ادھار، انوائس اور اپنا اسٹاک آؤٹ تینوں وہیں لگتے ہیں، صرف ایک دفعہ؛ (b) گاڑی باہر پر گاڑی صرف گیٹ پاس کے طور پر لکھیں — خریدار (جس کا اپنا پاؤڈر اسٹاک نہیں) کی ٹرپ سے نہ اسٹاک حرکت کرتا ہے، نہ رقم۔ گاڑی باہر صرف روانگی ہے: ٹول واپسی پر ٹرپ گاہک کے اپنے پاؤڈر اسٹاک سے کم کرتی ہے، اور اپنی روانگی (کوئی پارٹی نہیں) پر اپنا اسٹاک کم ہوتا ہے۔ (3) کھاتہ خرید/فروخت: پارٹی کے کھاتہ صفحے پر شامل خرید / شامل فروخت ان چیزوں کے لیے ہے جو گیٹ ریکارڈ کے بغیر حرکت کر گئیں - قدم 1 شے منتخب کریں: پتھر (کٹوتی فیصد کے بعد بل، پتھر اسٹاک حرکت کرتا ہے)، پاؤڈر (ٹن/تھیلے، پاؤڈر اسٹاک حرکت کرتا ہے، فروخت پر انوائس بنتی ہے) یا دیگر شے (نام + مقدار + اکائی + ریٹ: رقم صرف کھاتے میں لگتی ہے، اسٹاک بالکل نہیں حرکت کرتا)۔ (4) براہ راست تجارت، اپنا اسٹاک صفحے سے شامل ہوتی ہے: پارٹی ا سے خرید اور پارٹی ب کو فروخت ایک سودے میں - مال مل میں آتا ہی نہیں، اس لیے کوئی ٹانگ اسٹاک نہیں ہلاتی؛ ہر ٹانگ اپنی پارٹی کے کھاتے میں لگتی ہے اور سودا لائن پر منافع دکھتا ہے۔ اپنا اسٹاک صفحے پر اسٹاک صورتحال اور ملی ہوئی تجارت تاریخ ہے، ہر قطار پر گیٹ / کھاتہ / ایکسل / براہ راست کا ٹیگ۔ نوٹ: اپنی روانگی (پارٹی = اپنا) پر فروخت اسی ٹرپ پر بھی لکھی جا سکتی ہے — 'کس کو فروخت' + فروخت ریٹ — ادھار ٹرپ سے خریدار کے کھاتے میں لگتا ہے، صرف ایک دفعہ، انوائس نہیں بنتا؛ ایک ہی مال کی فروخت کھاتے اور ٹرپ دونوں پر کبھی نہیں، اور ملتی جلتی فروخت پر نظام وارننگ دیتا ہے۔",
       "अपनी ख़रीद-बिक्री के चार दरवाज़े हैं, और हर हलचल सिर्फ़ एक बार गिनी जाती है। (1) गेट ख़रीद: अपनी गाड़ी अंदर एंट्री पर ख़रीदा रॉक (रॉक दर, किससे ख़रीदा विक्रेता के साथ) - देय विक्रेता के खाते में लगता है और रॉक स्टॉक अपना रहता है; अलग ख़रीद पंक्ति नहीं बनती। ग्राहक पार्टी की गाड़ी अंदर कभी ख़रीद नहीं होती — ग्राहक अपना रॉक पिसाई के लिए लाता है। (2) अपना पाउडर बेचने के दो दरवाज़े हैं, एक ही माल के लिए दोनों कभी नहीं: (a) ख़रीदार के पार्टी खाते में पाउडर बिक्री एंट्री लगाएँ — उधार, इनवॉइस और अपना स्टॉक-आउट तीनों वहीं लगते हैं, केवल एक बार; (b) गाड़ी बाहर पर गाड़ी केवल गेट पास के रूप में लिखें — ख़रीदार (जिसका अपना पाउडर स्टॉक नहीं) की ट्रिप से न स्टॉक चलता है, न राशि। गाड़ी बाहर केवल रवानगी है: टोल वापसी पर ट्रिप ग्राहक के अपने पाउडर स्टॉक से कम करती है, और अपनी रवानगी (कोई पार्टी नहीं) पर अपना स्टॉक कम होता है। (3) खाता ख़रीद/बिक्री: पार्टी के खाता पृष्ठ पर ख़रीद जोड़ें / बिक्री जोड़ें उन चीज़ों के लिए है जो गेट रिकॉर्ड के बिना चली गईं - चरण 1 वस्तु चुनें: रॉक (कटौती % के बाद बिल, रॉक स्टॉक चलता है), पाउडर (टन/बोरे, पाउडर स्टॉक चलता है, बिक्री पर इनवॉइस बनता है) या अन्य वस्तु (नाम + मात्रा + इकाई + दर: राशि केवल खाते में लगती है, स्टॉक बिल्कुल नहीं चलता)। (4) सीधा व्यापार, अपना स्टॉक पृष्ठ से जुड़ता है: पार्टी A से ख़रीद और पार्टी B को बिक्री एक सौदे में - माल मिल में आता ही नहीं, इसलिए कोई टांग स्टॉक नहीं हिलाती; हर टांग अपनी पार्टी के खाते में लगती है और सौदा पंक्ति पर लाभ दिखता है। अपना स्टॉक पृष्ठ पर स्टॉक स्थिति और मिली हुई व्यापार इतिहास है, हर पंक्ति पर गेट / खाता / एक्सेल / सीधा का टैग। नोट: अपनी रवानगी (पार्टी = अपना) पर बिक्री इसी ट्रिप पर भी लिखी जा सकती है — 'किसे बेचा' + बिक्री दर — उधार ट्रिप से ख़रीदार के खाते में लगता है, केवल एक बार, इनवॉइस नहीं बनता; एक ही माल की बिक्री खाते और ट्रिप दोनों पर कभी नहीं, और मिलती-जुलती बिक्री पर सिस्टम चेतावनी देता है।")),
 _K("flow_outside", "flow", "outside",
    {"lat": ["outside grinding", "bahir grinding", "bahar pisai", "doosri mill pisai",
             "outside mill", "grinding bill", "bahir mill bill"],
     "ur": ["باہر پسائی", "دوسری مل پسائی"], "hi": ["बाहर पिसाई", "दूसरी मिल पिसाई"]},
    _L("Where an Outside Grinding entry goes", "Outside Grinding entry kahan jati hai",
       "باہر پسائی انٹری کہاں جاتی ہے", "बाहर पिसाई एंट्री कहाँ जाती है"),
    _L("What happens after rock is sent out for grinding?", "pathar bahar pisai ke liye bhejne ke baad kya hota hai",
       "پتھر باہر پسائی کے لیے بھیجنے کے بعد کیا ہوتا ہے؟", "रॉक बाहर पिसाई के लिए भेजने के बाद क्या होता है?"),
    _L("Outside Grinding is the mirror of toll grinding: OUR rock is ground by another mill and we PAY them - the charges are OUR payable, sitting on the 'we owe them' side of that factory's khata, exactly like a Purchase credit sits for a seller. The rock travels DIRECTLY from the mine to the outside factory; our godam stock never moves in either direction, and the powder is sold FROM the factory. Rock Sent only records the movement plus the AGREED rate - NO charge posts (an optional rock rate posts the purchase payable to the SELLER under the Purchase head). The charge is born in the Grinding Bill, recorded when settling with the factory: powder ground (bags at the stamped bag weight), the ACTUAL rock used (prefilled with a suggestion, editable to their figure), and the rate (auto from the agreement). Charge = powder tons x rate posts as a payable CREDIT under the Grinding head in the factory's khata, and stands as its own cost line ('Outside grinding') in the P&L - never in our own cost-per-ton. Rock remaining at the factory = sent - used across bills; wastage per bill = rock used - powder tons. An optional Amount Paid Now on the bill posts a normal money-out payment in the same save; plain Payments to the factory stay progress-free. Powder Sold from the factory posts a normal sale + invoice and draws down that factory's powder. The Phosphate Detail register does NOT count outside grinding (that rock was not ground here).",
       "Outside Grinding toll pisai ka ulta aina hai: hamara pathar DOOSRI mill se pista hai aur pisai charges HAM factory walay ko DETAY hain - charge factory ke khatay mein 'humaray denay' wali taraf lagta hai, bilkul waisay jaisay seller ke liye Purchase credit lagta hai; ye un ki kamai hai, hum par un ka lena NAHI. Pathar SEEDHA khaan se bahir factory jata hai; hamara godam stock dono taraf se NAHI hilta, aur powder bhi wahin se bikta hai. Rock Sent sirf movement aur TAY SHUDA rate likhta hai - koi charge NAHI lagta (optional rock rate par khareed ki raqam SELLER ke khatay mein Purchase head ke neeche dena lag jati hai). Charge Grinding Bill mein banta hai, jo factory se hisaab ke waqt lagta hai: pisa hua powder (mojooda bag weight par stamp bag), ASAL istemal shuda rock (suggestion pehle se bhara hota hai, un ke asal figure par badal sakte hain), aur rate (agreement se khud ajata hai). Charge = powder ton x rate factory ke khatay mein Grinding head ke neeche dena (payable) CREDIT lagta hai, aur P&L mein apni alag cost line ('Outside grinding') hai - hamari apni cost-per-ton mein KABHI nahi milta. Factory ke paas rock baqi = bheja - bills mein istemal; har bill ki wastage = rock used - powder ton. Bill par optional Abhi Ada raqam usi save mein aam money-out payment laga deti hai; aam Payments factory ko progress NAHI badalti (advances purane bills ke liye). Powder Sold us factory ke powder se aam farokht + invoice lagata hai. Phosphate Detail register outside grinding ko NAHI ginta (wo pathar yahan nahi pisa).",
       "باہر پسائی ٹول پسائی کا الٹا آئینہ ہے: ہمارا پتھر دوسری مل سے پستا ہے اور پسائی چارجز ہم فیکٹری والے کو دیتے ہیں - چارج فیکٹری کے کھاتے میں 'ہمارے دینے' والی طرف لگتا ہے، بالکل ویسے جیسے فروخت کنندہ کے لیے خرید کریڈٹ لگتا ہے؛ یہ ان کی کمائی ہے، ہم پر ان کا لینا نہیں۔ پتھر سیدھا کان سے باہر فیکٹری جاتا ہے؛ ہمارا گودام اسٹاک دونوں طرف سے نہیں ہلتا، اور پاؤڈر بھی وہیں سے بکتا ہے۔ پتھر بھیجا صرف آنا جانا اور طے شدہ ریٹ لکھتا ہے - کوئی چارج نہیں لگتا (اختیاری پتھر ریٹ پر خرید کی رقم فروخت کنندہ کے کھاتے میں خرید ہیڈ کے نیچے دینی لگ جاتی ہے)۔ چارج گرائنڈنگ بل میں بنتا ہے، جو فیکٹری سے حساب کے وقت لگتا ہے: پسا ہوا پاؤڈر (موجودہ تھیلا وزن پر مہر تھیلے)، اصل استعمال شدہ پتھر (تجویز پہلے سے بھری ہوتی ہے، ان کے اصل اعداد پر بدل سکتے ہیں)، اور ریٹ (معاہدے سے خود آ جاتا ہے)۔ چارج = پاؤڈر ٹن × ریٹ فیکٹری کے کھاتے میں پسائی ہیڈ کے نیچے دینی رقم کریڈٹ لگتا ہے، اور نفع نقصان (P&L) میں اپنی الگ لاگت لائن ('باہر پسائی') ہے - ہماری اپنی فی ٹن لاگت میں کبھی نہیں ملتا۔ فیکٹری کے پاس پتھر باقی = بھیجا - بلوں میں استعمال؛ ہر بل کی ویسٹیج = استعمال شدہ پتھر - پاؤڈر ٹن۔ بل پر اختیاری ابھی ادا رقم اسی محفوظ میں عام ادائیگی لگا دیتی ہے؛ عام ادائیگیاں فیکٹری کی پیش رفت نہیں بدلتیں۔ پاؤڈر فروخت اس فیکٹری کے پاؤڈر سے عام فروخت + انوائس لگاتی ہے۔ فاسفیٹ تفصیل رجسٹر باہر پسائی کو نہیں گنتا (وہ پتھر یہاں نہیں پسا)۔",
       "बाहर पिसाई टोल पिसाई का उल्टा आइना है: हमारा रॉक दूसरी मिल से पिसता है और पिसाई शुल्क हम फ़ैक्ट्री वाले को देते हैं - शुल्क फ़ैक्ट्री के खाते में 'हमारे देने' वाली तरफ लगता है, बिल्कुल वैसे जैसे विक्रेता के लिए ख़रीद क्रेडिट लगता है; यह उनकी कमाई है, हम पर उनका लेना नहीं। रॉक सीधा खदान से बाहर फ़ैक्ट्री जाता है; हमारा गोदाम स्टॉक दोनों तरफ़ से नहीं हिलता, और पाउडर भी वहीं से बिकता है। रॉक भेजा सिर्फ़ आना-जाना और तय दर लिखता है - कोई शुल्क नहीं लगता (वैकल्पिक रॉक दर पर ख़रीद की राशि विक्रेता के खाते में ख़रीद हेड के नीचे देय लग जाती है)। शुल्क ग्राइंडिंग बिल में बनता है, जो फ़ैक्ट्री से हिसाब के समय लगता है: पिसा पाउडर (मौजूदा बोरा वज़न पर मुहर बोरे), असली इस्तेमाल रॉक (सुझाव पहले से भरा होता है, उनके असली आँकड़े पर बदल सकते हैं), और दर (समझौते से ख़ुद आ जाती है)। शुल्क = पाउडर टन × दर फ़ैक्ट्री के खाते में पिसाई हेड के नीचे देय क्रेडिट लगता है, और लाभ-हानि (P&L) में अपनी अलग लागत पंक्ति ('बाहर पिसाई') है - हमारी अपनी प्रति टन लागत में कभी नहीं मिलता। फ़ैक्ट्री के पास रॉक बाकी = भेजा - बिलों में इस्तेमाल; हर बिल का वेस्टेज = इस्तेमाल रॉक - पाउडर टन। बिल पर वैकल्पिक अभी अदा राशि उसी सेव में सामान्य भुगतान लगा देती है; सामान्य भुगतान फ़ैक्ट्री की प्रगति नहीं बदलते। पाउडर बिक्री उस फ़ैक्ट्री के पाउडर से सामान्य बिक्री + इनवॉइस लगाती है। फ़ॉस्फेट विवरण रजिस्टर बाहर पिसाई को नहीं गिनता (वह रॉक यहाँ नहीं पिसा)।")),
]

_KB += [
 # ------------------------------------------------------------- rules ---
 _K("rule_edit_delete", "rule", None,
    {"lat": ["edit kon", "delete kon", "edit kar", "delete kar", "edit kaise", "edit kaisay",
             "ghalti ho", "mistake ho", "entry theek", "entry change", "entry badal",
             "record change"],
     "ur": ["تبدیل کون", "حذف کون", "غلطی ہو جائے"], "hi": ["एडिट कौन", "डिलीट कौन", "गलती हो जाए"]},
    _L("Who can edit or delete entries", "Entry edit/delete kon kar sakta hai",
       "انٹری تبدیل/حذف کون کر سکتا ہے", "एंट्री एडिट/डिलीट कौन कर सकता है"),
    _L("Who can edit or delete an entry?", "entry edit kon kar sakta hai",
       "انٹری تبدیل کون کر سکتا ہے؟", "एंट्री एडिट कौन कर सकता है?"),
    _L("Any entry can be corrected afterwards - but Edit and Delete are OWNER-ONLY, like a super admin, for every kind of entry: bags, vehicle in/out, grinding & production, payments, expenses, all of them. Manager and Staff can only add new entries and print. An edited vehicle trip reposts its charges cleanly, so the khata never gets double lines. A deleted entry lands in Recycle (Setup & System), the owner is alerted, and the owner can restore it from there.",
       "Koi bhi entry baad mein theek ki ja sakti hai - lekin Edit aur Delete SIRF Owner kar sakta hai, super admin ki tarah, har qisam ki entry par: bags, gari in/out, grinding & production, payment, kharcha - sab par. Manager aur Staff sirf nayi entry kar sakte hain aur print le sakte hain. Edit ki gayi gari entry apne charges saaf dobara lagati hai, is liye khatay mein double line kabhi NAHI banti. Delete ki gayi entry Recycle (Setup & System) mein jati hai, owner ko alert jata hai, aur owner wahan se restore bhi kar sakta hai.",
       "کوئی بھی انٹری بعد میں ٹھیک کی جا سکتی ہے - لیکن تبدیل اور حذف صرف مالک کر سکتا ہے، سپر ایڈمن کی طرح، ہر قسم کی انٹری پر: تھیلے، گاڑی اندر/باہر، پسائی و پیداوار، ادائیگی، خرچہ - سب پر۔ منیجر اور عملہ صرف نئی انٹری کر سکتے ہیں اور پرنٹ لے سکتے ہیں۔ تبدیل کی گئی گاڑی انٹری اپنے چارجز صاف دوبارہ لگاتی ہے، اس لیے کھاتے میں دوہری لائن کبھی نہیں بنتی۔ حذف کی گئی انٹری ری سائیکل (سیٹ اپ و سسٹم) میں جاتی ہے، مالک کو الرٹ جاتا ہے، اور مالک وہاں سے بحال بھی کر سکتا ہے۔",
       "कोई भी एंट्री बाद में ठीक की जा सकती है - लेकिन एडिट और डिलीट केवल मालिक कर सकता है, सुपर एडमिन की तरह, हर प्रकार की एंट्री पर: बोरे, गाड़ी अंदर/बाहर, पिसाई व उत्पादन, भुगतान, खर्च - सब पर। मैनेजर और स्टाफ़ केवल नई एंट्री कर सकते हैं और प्रिंट ले सकते हैं। एडिट की गई गाड़ी एंट्री अपने शुल्क साफ़ दोबारा लगाती है, इसलिए खाते में दोहरी पंक्ति कभी नहीं बनती। डिलीट की गई एंट्री रीसायकल (सेटअप व सिस्टम) में जाती है, मालिक को अलर्ट जाता है, और मालिक वहाँ से बहाल भी कर सकता है।")),
 _K("rule_roles", "rule", "logins",
    {"lat": ["roles", "role kya", "permission", "permissions", "staff access", "access kon",
             "manager kya kar sakta", "kon kya dekh sakta", "kis ko access",
             "demo login", "demo kya hai", "demo wala login"],
     "ur": ["رول", "اجازت", "رسائی"], "hi": ["रोल", "अनुमति", "पहुँच"]},
    _L("Roles & permissions", "Roles aur permissions", "رولز و اجازتیں", "रोल व अनुमतियाँ"),
    _L("What roles and permissions are there?", "roles aur permissions kya hain",
       "رولز اور اجازتیں کیا ہیں؟", "रोल और अनुमतियाँ क्या हैं?"),
    _L("There are 5 roles. Owner: everything - plus edit/delete of any entry, approvals, users and settings. Manager: full working access including all accounts and khatas, but the Dashboard's Money In/Out totals are Owner-only, and a Manager cannot edit or delete entries. Staff: only the pages the Owner ticks from the permissions - dashboard, vehicles, grinding, production, trade, parties, payments, expenses, cashbook, workers, reports. Client (online edition): only his own khata, stock and balance. Demo: the public view-only login (demo / demo12345) - it can see the business pages and ask the AI Assistant, but it cannot save, edit or delete anything, and Settings, Logins & Users and Backup stay closed for it. Logins are made on the Logins & Users page (Owner only).",
       "5 role hain. Owner: sab kuch - is ke ilawa har entry ka edit/delete, approvals, users aur settings bhi. Manager: poora kaam ka access, saare accounts aur khatay shamil, lekin Dashboard ke Money In/Out totals sirf Owner ko dikhte hain, aur Manager entry edit/delete NAHI kar sakta. Staff: sirf wohi pages jo Owner permissions mein tick kare - dashboard, vehicles, grinding, production, trade, parties, payments, expenses, cashbook, workers, reports. Client (online edition): sirf apna khata, stock aur balance. Demo: aam view-only login (demo / demo12345) - ye saare business pages dekh sakta hai aur AI Assistant se pooch sakta hai, lekin kuch bhi save, edit ya delete NAHI kar sakta, aur Settings, Logins & Users aur Backup is ke liye band rehte hain. Logins, Logins & Users page par bante hain (sirf Owner).",
       "5 رول ہیں۔ مالک: سب کچھ - اس کے علاوہ ہر انٹری کا تبدیل/حذف، منظوریاں، صارفین اور ترتیبات بھی۔ منیجر: پورا کام کا رسائی، سارے اکاؤنٹس اور کھاتے شامل، لیکن ڈیش بورڈ کے رقم اندر/باہر مجموعے صرف مالک کو دکھتے ہیں، اور منیجر انٹری تبدیل/حذف نہیں کر سکتا۔ عملہ: صرف وہی صفحے جو مالک اجازتوں میں نشان لگائے - ڈیش بورڈ، گاڑیاں، پسائی، پیداوار، تجارت، پارٹیاں، ادائیگیاں، اخراجات، کیش بک، مزدور، رپورٹس۔ گاہک (آن لائن ایڈیشن): صرف اپنا کھاتہ، اسٹاک اور بیلنس۔ ڈیمو: عوامی صرف دیکھنے والا لاگ ان (demo / demo12345) - یہ سارے کاروباری صفحے دیکھ سکتا ہے اور AI اسسٹنٹ سے پوچھ سکتا ہے، لیکن کچھ بھی محفوظ، تبدیل یا حذف نہیں کر سکتا، اور ترتیبات، لاگ ان و صارفین اور بیک اپ اس کے لیے بند رہتے ہیں۔ لاگ ان، لاگ ان و صارفین صفحے پر بنتے ہیں (صرف مالک)۔",
       "5 रोल हैं। मालिक: सब कुछ - इसके अलावा हर एंट्री का एडिट/डिलीट, स्वीकृतियाँ, उपयोगकर्ता और सेटिंग्स भी। मैनेजर: पूरा काम का पहुँच, सारे खाते शामिल, लेकिन डैशबोर्ड के पैसा अंदर/बाहर योग केवल मालिक को दिखते हैं, और मैनेजर एंट्री एडिट/डिलीट नहीं कर सकता। स्टाफ़: केवल वही पृष्ठ जो मालिक अनुमतियों में टिक करे - डैशबोर्ड, गाड़ियाँ, पिसाई, उत्पादन, व्यापार, पार्टियाँ, भुगतान, खर्च, कैश बुक, मज़दूर, रिपोर्ट। ग्राहक (ऑनलाइन संस्करण): केवल अपना खाता, स्टॉक और शेष। डेमो: सार्वजनिक केवल-देखने वाला लॉगिन (demo / demo12345) - यह सारे व्यावसायिक पृष्ठ देख सकता है और AI सहायक से पूछ सकता है, लेकिन कुछ भी सहेज, एडिट या डिलीट नहीं कर सकता, और सेटिंग्स, लॉगिन व उपयोगकर्ता और बैकअप इसके लिए बंद रहते हैं। लॉगिन, लॉगिन व उपयोगकर्ता पृष्ठ पर बनते हैं (केवल मालिक)।")),
 _K("rule_shift", "rule", "grindprod",
    {"lat": ["shift rule", "day night rule", "shift ka rule", "day night ka hisaab",
             "shift kis time", "day shift kab", "night shift kab", "shift timing",
             "day night", "shift"],
     "ur": ["شفٹ رول", "دن رات شفٹ"], "hi": ["शिफ़्ट नियम", "दिन रात शिफ़्ट"]},
    _L("Day / Night shift rule", "Day / Night shift ka rule", "دن / رات شفٹ کا اصول", "दिन / रात शिफ़्ट का नियम"),
    _L("What is the day/night shift rule?", "shift day night ka rule kya hai",
       "دن رات شفٹ کا اصول کیا ہے؟", "दिन रात शिफ़्ट का नियम क्या है?"),
    _L("Day/Night is decided by the Shift toggle on the Grinding & Production entry itself - the toggle always wins. Older entries without a toggle are classed by their start time: starting 06:00-18:00 = Day, anything else = Night. An entry with no start time counts in the day's total only, not in the Day/Night split. The same split shows in the Day-End Summary and the Phosphate Detail register.",
       "Day/Night ka faisla Grinding & Production entry par lage Shift toggle se hota hai - toggle hamesha jeet-ta hai. Purani entries jin par toggle nahi, un ka start time dekha jata hai: 06:00-18:00 shuru = Day, is ke ilawa = Night. Jis entry ka start time hi na ho wo sirf din ke total mein ginti hai, Day/Night split mein nahi. Yehi split Day-End Summary aur Phosphate Detail register dono mein dikhta hai.",
       "دن/رات کا فیصلہ پسائی و پیداوار انٹری پر لگے شفٹ ٹوگل سے ہوتا ہے - ٹوگل ہمیشہ جیتتا ہے۔ پرانی انٹریاں جن پر ٹوگل نہیں، ان کا شروع وقت دیکھا جاتا ہے: 06:00-18:00 شروع = دن، اس کے علاوہ = رات۔ جس انٹری کا شروع وقت ہی نہ ہو وہ صرف دن کے کل میں گنتی ہے، دن/رات تقسیم میں نہیں۔ یہی تقسیم دن اختتام خلاصے اور فاسفیٹ تفصیل رجسٹر دونوں میں دکھتی ہے۔",
       "दिन/रात का फ़ैसला पिसाई व उत्पादन एंट्री पर लगे शिफ़्ट टॉगल से होता है - टॉगल हमेशा जीतता है। पुरानी एंट्रियाँ जिन पर टॉगल नहीं, उनका शुरू समय देखा जाता है: 06:00-18:00 शुरू = दिन, इसके अलावा = रात। जिस एंट्री का शुरू समय ही न हो वह केवल दिन के योग में गिनी जाती है, दिन/रात विभाजन में नहीं। यही विभाजन दिन-अंत सारांश और फ़ॉस्फेट विवरण रजिस्टर दोनों में दिखता है।"),
    need=["rule", "kaise", "kya", "kab", "kis", "hota", "hoti", "time",
          "رول", "کیسے", "क्या", "कैसे", "कब", "नियम"]),
 _K("rule_formula", "rule", "phosdetail",
    {"lat": ["balance rock", "balance powder", "formula", "register formula", "balance kaise banta"],
     "ur": ["بیلنس پتھر", "فارمولا"], "hi": ["शेष रॉक", "फॉर्मूला"]},
    _L("Balance Rock / Powder formulas", "Balance Rock ka formula", "بیلنس پتھر کا فارمولا", "शेष रॉक का फ़ॉर्मूला"),
    _L("What is the Balance Rock formula?", "balance rock ka formula kya hai",
       "بیلنس پتھر کا فارمولا کیا ہے؟", "शेष रॉक का फ़ॉर्मूला क्या है?"),
    _L("The register's formulas: Balance Rock = previous Balance Rock + today's Rock In - Powder made - Wastage (the register treats production itself as the rock consumption, worked day by day from the first record). Balance Powder = previous powder + powder made - powder dispatched, which matches the Warehouse. Dispatched counts only powder that left the godam — powder sold from an outside factory is never in this register, and powder bought off-gate counts IN (its bags are noted on the day's row). Wastage = the Settings wastage % (default 5%) of the day's powder - a reporting figure only.",
       "Register ke formulas ye hain: Balance Rock = pichla Balance Rock + aaj ka Rock In - bana Powder - Wastage (register production ko hi pathar ki khapat manta hai, pehle record se roz-ba-roz). Balance Powder = pichla powder + bana - rawana hua, jo Warehouse se milta hai. Rawana sirf wohi powder hai jo godam se nikla — bahar wali factory se bika powder is register mein kabhi nahi aata, aur bahar se kharida powder andar gina jata hai (us ke bag us din ki row par note hote hain). Wastage = din ke powder ka Settings wala wastage % (default 5%) - ye sirf report ka number hai.",
       "رجسٹر کے فارمولے یہ ہیں: بیلنس پتھر = پچھلا بیلنس پتھر + آج کا پتھر اندر - بنا پاؤڈر - ضیاع (رجسٹر پیداوار کو ہی پتھر کی کھپت مانتا ہے، پہلے ریکارڈ سے روز بہ روز)۔ بیلنس پاؤڈر = پچھلا پاؤڈر + بنا - روانہ ہوا، جو گودام سے ملتا ہے۔ روانہ صرف وہی پاؤڈر ہے جو گودام سے نکلا — باہر والی فیکٹری سے بکا پاؤڈر اس رجسٹر میں کبھی نہیں آتا، اور باہر سے خریدا پاؤڈر اندر گنا جاتا ہے (اس کے تھیلے اس دن کی سطر پر درج ہوتے ہیں)۔ ضیاع = دن کے پاؤڈر کا ترتیبات والا ضیاع % (طے شدہ 5%) - یہ صرف رپورٹ کا عدد ہے۔",
       "रजिस्टर के फ़ॉर्मूले ये हैं: शेष रॉक = पिछला शेष रॉक + आज का रॉक अंदर - बना पाउडर - वेस्टेज (रजिस्टर उत्पादन को ही रॉक की खपत मानता है, पहले रिकॉर्ड से रोज़-ब-रोज़)। शेष पाउडर = पिछला पाउडर + बना - रवाना हुआ, जो गोदाम से मिलता है। रवाना केवल वही पाउडर है जो गोदाम से निकला — बाहर वाली फ़ैक्टरी से बिका पाउडर इस रजिस्टर में कभी नहीं आता, और बाहर से ख़रीदा पाउडर अंदर गिना जाता है (उसके बोरे उस दिन की पंक्ति पर दर्ज होते हैं)। वेस्टेज = दिन के पाउडर का सेटिंग्स वाला वेस्टेज % (डिफ़ॉल्ट 5%) - यह सिर्फ़ रिपोर्ट का आँकड़ा है।"),
    need=["formula", "kaise", "kya", "banta", "banti", "hisab", "hisaab",
          "فارمولا", "کیسے", "फॉर्मूला", "कैसे", "बनता"]),
 _K("rule_backup", "rule", "data",
    {"lat": ["backup", "restore"],
     "ur": ["بیک اپ", "بحالی"], "hi": ["बैकअप", "बहाली"]},
    _L("Backup & restore", "Backup aur restore", "بیک اپ و بحالی", "बैकअप व बहाली"),
    _L("How do I take a backup?", "backup kaise lein",
       "بیک اپ کیسے لیں؟", "बैकअप कैसे लें?"),
    _L("Backup is on the Data page (Setup & System): one click makes a full ZIP - the whole database (photos and proofs are inside it) plus a CSV of every table. Restore is on the same page and brings everything back. If no backup is taken for 7 days the system reminds you, and a separate weekly copy is kept as well. Keep the ZIP somewhere safe off the factory computer too, e.g. MEGA or Google Drive.",
       "Backup Data page (Setup & System) par hai: ek click par poora ZIP banta hai - saara database (photos/proofs us ke andar hain) aur har table ki CSV. Restore bhi usi page se hota hai aur sab wapas aa jata hai. 7 din backup na liya jaye to system yaad dilata hai, aur hafte ki ek copy alag se bhi rakhi jati hai. ZIP ko factory computer ke ilawa bhi kahin mehfooz rakhein, masalan MEGA ya Google Drive.",
       "بیک اپ ڈیٹا صفحے (سیٹ اپ و سسٹم) پر ہے: ایک کلک پر پورا ZIP بنتا ہے - سارا ڈیٹابیس (تصاویر/ثبوت اس کے اندر ہیں) اور ہر جدول کی CSV۔ بحالی بھی اسی صفحے سے ہوتی ہے اور سب واپس آ جاتا ہے۔ 7 دن بیک اپ نہ لیا جائے تو سسٹم یاد دلاتا ہے، اور ہفتے کی ایک نقل الگ سے بھی رکھی جاتی ہے۔ ZIP کو فیکٹری کمپیوٹر کے علاوہ بھی کہیں محفوظ رکھیں، مثلاً MEGA یا Google Drive۔",
       "बैकअप डेटा पृष्ठ (सेटअप व सिस्टम) पर है: एक क्लिक पर पूरा ZIP बनता है - सारा डेटाबेस (तस्वीरें/सबूत उसके अंदर हैं) और हर तालिका की CSV। बहाली भी उसी पृष्ठ से होती है और सब वापस आ जाता है। 7 दिन बैकअप न लिया जाए तो सिस्टम याद दिलाता है, और हफ़्ते की एक कॉपी अलग से भी रखी जाती है। ZIP को फ़ैक्टरी कंप्यूटर के अलावा भी कहीं सुरक्षित रखें, जैसे MEGA या Google Drive।")),
 _K("rule_lock", "rule", "logins",
    {"lat": ["login lock", "account lock", "lock ho gaya", "password ghalat", "locked", "band ho gaya"],
     "ur": ["لاگ ان لاک", "اکاؤنٹ لاک"], "hi": ["लॉगिन लॉक", "अकाउंट लॉक"]},
    _L("Login lock rule", "Login lock ka rule", "لاگ ان لاک کا اصول", "लॉगिन लॉक का नियम"),
    _L("When does a login lock?", "login lock kab hota hai",
       "لاگ ان لاک کب ہوتا ہے؟", "लॉगिन लॉक कब होता है?"),
    _L("After 5 wrong passwords in a row an account locks for 15 minutes (the login shows a locked message). It opens by itself after 15 minutes, or the Owner can reset that user's password sooner from Logins & Users.",
       "Lagatar 5 dafa ghalat password dalne par account 15 minute ke liye lock ho jata hai (login par locked ka message ata hai). 15 minute baad khud khul jata hai, ya Owner Logins & Users se us user ka password pehle reset kar sakta hai.",
       "لگاتار 5 دفعہ غلط پاس ورڈ ڈالنے پر اکاؤنٹ 15 منٹ کے لیے لاک ہو جاتا ہے (لاگ ان پر لاک کا پیغام آتا ہے)۔ 15 منٹ بعد خود کھل جاتا ہے، یا مالک لاگ ان و صارفین سے اس صارف کا پاس ورڈ پہلے ری سیٹ کر سکتا ہے۔",
       "लगातार 5 बार ग़लत पासवर्ड डालने पर अकाउंट 15 मिनट के लिए लॉक हो जाता है (लॉगिन पर लॉक का संदेश आता है)। 15 मिनट बाद ख़ुद खुल जाता है, या मालिक लॉगिन व उपयोगकर्ता से उस उपयोगकर्ता का पासवर्ड पहले रीसेट कर सकता है।")),
 _K("rule_lang", "rule", None,
    {"lat": ["language", "zaban", "urdu karna", "hindi karna", "english karna", "language badalna"],
     "ur": ["زبان", "اردو کرنا"], "hi": ["भाषा", "हिंदी करना"]},
    _L("Languages", "Zubanein", "زبانیں", "भाषाएँ"),
    _L("How do I change the language?", "language kaise badlun",
       "زبان کیسے بدلوں؟", "भाषा कैसे बदलूँ?"),
    _L("The system runs in 3 languages - English, Urdu and Hindi. Switch any time from the language selector in the top bar; changing it never loses what you have typed in a form, and each user's choice is saved for him. The login screen has a language dropdown too.",
       "System 3 zubanon mein chalta hai - English, Urdu aur Hindi. Upar wali bar ke language selector se kisi bhi waqt badal sakte hain; badalne se form mein likha hua data NAHI urta, aur har user ki apni pasand save rehti hai. Login screen par bhi language dropdown hai.",
       "سسٹم 3 زبانوں میں چلتا ہے - انگریزی، اردو اور ہندی۔ اوپر والی بار کے زبان منتخب کنندہ سے کسی بھی وقت بدل سکتے ہیں؛ بدلنے سے فارم میں لکھا ہوا ڈیٹا نہیں اڑتا، اور ہر صارف کی اپنی پسند محفوظ رہتی ہے۔ لاگ ان اسکرین پر بھی زبان کا ڈراپ ڈاؤن ہے۔",
       "सिस्टम 3 भाषाओं में चलता है - अंग्रेज़ी, उर्दू और हिंदी। ऊपर वाली बार के भाषा चयनकर्ता से किसी भी समय बदल सकते हैं; बदलने से फ़ॉर्म में लिखा हुआ डेटा नहीं उड़ता, और हर उपयोगकर्ता की अपनी पसंद सहेजी रहती है। लॉगिन स्क्रीन पर भी भाषा ड्रॉपडाउन है।")),
 _K("rule_update", "rule", None,
    {"lat": ["app update", "naya version", "update kaise", "apk update", "app ka update"],
     "ur": ["ایپ اپڈیٹ", "نیا ورژن"], "hi": ["ऐप अपडेट", "नया वर्शन"]},
    _L("Phone app updates", "Phone app ka update", "فون ایپ اپڈیٹ", "फ़ोन ऐप अपडेट"),
    _L("How does the phone app update?", "app update kaise hota hai",
       "ایپ اپڈیٹ کیسے ہوتا ہے؟", "ऐप अपडेट कैसे होता है?"),
    _L("The phone app (Orush Grinding Mill) checks the version kept on the server; when a newer version is published the app offers the update itself, and because every update carries the same signature, your data and login stay safe. The web version is new the moment the site reloads after an update is published.",
       "Phone app (Orush Grinding Mill) server par rakhe version se check karta hai; naya version aaye to app khud update ki peshkash karta hai, aur har update par wohi purani signature hoti hai is liye data aur login mehfooz rehte hain. Web version update publish hote hi reload par naya ho jata hai.",
       "فون ایپ (اورش گرائنڈنگ مل) سرور پر رکھے ورژن سے جانچتی ہے؛ نیا ورژن آئے تو ایپ خود اپڈیٹ کی پیشکش کرتی ہے، اور ہر اپڈیٹ پر وہی پرانی دستخط ہوتی ہے اس لیے ڈیٹا اور لاگ ان محفوظ رہتے ہیں۔ ویب ورژن اپڈیٹ شائع ہوتے ہی ری لوڈ پر نیا ہو جاتا ہے۔",
       "फ़ोन ऐप (ओरश ग्राइंडिंग मिल) सर्वर पर रखे वर्शन से जाँचता है; नया वर्शन आए तो ऐप ख़ुद अपडेट की पेशकश करता है, और हर अपडेट पर वही पुराना हस्ताक्षर होता है इसलिए डेटा और लॉगिन सुरक्षित रहते हैं। वेब वर्शन अपडेट प्रकाशित होते ही रीलोड पर नया हो जाता है।")),
 # ------------------------------------------------------------- pages ---
 _K("page_ledger", "page", "parties",
    {"lat": ["party khata", "khata kahan", "party ledger", "ledger kahan", "party ka khata"],
     "ur": ["پارٹی کھاتہ", "کھاتہ کہاں"], "hi": ["पार्टी खाता", "खाता कहाँ"]},
    _L("Party khata (ledger)", "Party ka khata", "پارٹی کا کھاتہ", "पार्टी का खाता"),
    _L("Where does a party's khata open?", "party ka khata kahan khulta hai",
       "پارٹی کا کھاتہ کہاں کھلتا ہے؟", "पार्टी का खाता कहाँ खुलता है?"),
    _L("A party's khata opens from the Parties page (Clients group): press the Ledger button in that party's row. It shows every entry - debit/credit with a running balance - plus the party's rock waiting and powder ready, and it prints from the same page.",
       "Party ka khata Parties page (Clients group) se khulta hai: us party ki row mein Ledger button dabayein. Wahan har entry debit/credit aur chalte balance ke saath dikhti hai, party ka rock waiting aur powder ready bhi, aur print bhi usi page se hota hai.",
       "پارٹی کا کھاتہ پارٹیاں صفحے (گاہک گروپ) سے کھلتا ہے: اس پارٹی کی قطار میں کھاتہ بٹن دبائیں۔ وہاں ہر انٹری ڈیبٹ/کریڈٹ اور چلتے بیلنس کے ساتھ دکھتی ہے، پارٹی کا منتظر پتھر اور تیار پاؤڈر بھی، اور پرنٹ بھی اسی صفحے سے ہوتا ہے۔",
       "पार्टी का खाता पार्टियाँ पृष्ठ (ग्राहक समूह) से खुलता है: उस पार्टी की पंक्ति में खाता बटन दबाएँ। वहाँ हर एंट्री डेबिट/क्रेडिट और चलते शेष के साथ दिखती है, पार्टी का प्रतीक्षारत रॉक और तैयार पाउडर भी, और प्रिंट भी उसी पृष्ठ से होता है।")),
 _K("page_dayend", "page", "cashbook",
    {"lat": ["day end", "day-end", "dayend", "din ka hisaab kahan", "roz ka hisab"],
     "ur": ["دن اختتام"], "hi": ["दिन अंत"]},
    _L("Day-End Summary", "Day-End Summary", "دن اختتام خلاصہ", "दिन-अंत सारांश"),
    _L("Where is the Day-End Summary?", "day end kahan hai",
       "دن اختتام کہاں ہے؟", "दिन-अंत कहाँ है?"),
    _L("The Day-End Summary is on the Cash Book page (Accounts group) - the middle card: the day's vehicles IN/OUT with tons, ground + bags with the Day/Night split, powder made and wastage, filter powder, cash net and expenses, plus a button to send the summary. The date can be changed at the top of the page.",
       "Day-End Summary Cash Book page (Accounts group) par hai - darmiyan wala card: din ki gariyan IN/OUT ton ke saath, ground + bags Day/Night split ke saath, bana powder aur wastage, filter powder, cash net aur kharcha, aur summary bhejne ka button bhi. Page ke oopar se date badal sakte hain.",
       "دن اختتام خلاصہ کیش بک صفحے (اکاؤنٹس گروپ) پر ہے - درمیان والا کارڈ: دن کی گاڑیاں اندر/باہر ٹن کے ساتھ، پسائی + تھیلے دن/رات تقسیم کے ساتھ، بنا پاؤڈر اور ضیاع، فلٹر پاؤڈر، نقد خالص اور خرچہ، اور خلاصہ بھیجنے کا بٹن بھی۔ صفحے کے اوپر سے تاریخ بدل سکتے ہیں۔",
       "दिन-अंत सारांश कैश बुक पृष्ठ (खाते समूह) पर है - बीच वाला कार्ड: दिन की गाड़ियाँ अंदर/बाहर टन के साथ, पिसाई + बोरे दिन/रात विभाजन के साथ, बना पाउडर और वेस्टेज, फ़िल्टर पाउडर, नकद शुद्ध और खर्च, और सारांश भेजने का बटन भी। पृष्ठ के ऊपर से तिथि बदल सकते हैं।")),
 _K("page_bankbook", "page", "cashbook",
    {"lat": ["bank book", "bankbook"],
     "ur": ["بینک بک"], "hi": ["बैंक बुक"]},
    _L("Bank Book", "Bank Book", "بینک بک", "बैंक बुक"),
    _L("Where is the Bank Book?", "bank book kidhar hai",
       "بینک بک کدھر ہے؟", "बैंक बुक किधर है?"),
    _L("The Bank Book is at the bottom of the Cash Book page (Accounts group): every bank from Settings with its opening balance, bank payments in/out and bank expenses, and the running balance. Bank names and openings are set in Settings.",
       "Bank Book Cash Book page (Accounts group) ke aakhir mein hai: Settings wale har bank ka opening balance, bank payments in/out aur bank kharchay, aur chalta balance. Bank ke naam aur opening Settings mein set hote hain.",
       "بینک بک کیش بک صفحے (اکاؤنٹس گروپ) کے آخر میں ہے: ترتیبات والے ہر بینک کا ابتدائی بیلنس، بینک ادائیگیاں اندر/باہر اور بینک اخراجات، اور چلتا بیلنس۔ بینک کے نام اور ابتدائی اعداد ترتیبات میں مقرر ہوتے ہیں۔",
       "बैंक बुक कैश बुक पृष्ठ (खाते समूह) के अंत में है: सेटिंग्स वाले हर बैंक का प्रारंभिक शेष, बैंक भुगतान अंदर/बाहर और बैंक खर्च, और चलता शेष। बैंक के नाम और प्रारंभिक आँकड़े सेटिंग्स में सेट होते हैं।")),
 _K("page_pnl", "page", "reports",
    {"lat": ["p&l", "profit loss", "profit and loss", "munafa nuqsan wali report", "pnl"],
     "ur": ["نفع نقصان"], "hi": ["लाभ हानि"]},
    _L("Profit & Loss page", "Profit & Loss wala page", "نفع نقصان والا صفحہ", "लाभ-हानि वाला पृष्ठ"),
    _L("Where is the Profit & Loss?", "p&l kahan hai",
       "نفع نقصان کہاں ہے؟", "लाभ-हानि कहाँ है?"),
    _L("Profit & Loss is the first card of the Reports page (Accounts group): the month's income (grinding + sales), every cost line, and the net profit, with a print button. The month can be changed at the top of the card.",
       "Profit & Loss Reports page (Accounts group) ka pehla card hai: mahine ki aamdani (pisai + farokht), har cost line, aur khalis munafa, print button ke saath. Card ke oopar se mahina badal sakte hain.",
       "نفع نقصان رپورٹس صفحے (اکاؤنٹس گروپ) کا پہلا کارڈ ہے: مہینے کی آمدنی (پسائی + فروخت)، ہر لاگت لائن، اور خالص منافع، پرنٹ بٹن کے ساتھ۔ کارڈ کے اوپر سے مہینہ بدل سکتے ہیں۔",
       "लाभ-हानि रिपोर्ट पृष्ठ (खाते समूह) का पहला कार्ड है: महीने की आय (पिसाई + बिक्री), हर लागत पंक्ति, और शुद्ध मुनाफ़ा, प्रिंट बटन के साथ। कार्ड के ऊपर से महीना बदल सकते हैं।")),
 _K("page_cpt", "page", "reports",
    {"lat": ["cost per ton", "fi ton cost", "fi ton kharcha kahan", "per ton cost"],
     "ur": ["فی ٹن لاگت"], "hi": ["प्रति टन लागत"]},
    _L("Cost Per Ton", "Cost Per Ton", "فی ٹن لاگت", "प्रति टन लागत"),
    _L("Where is Cost Per Ton?", "cost per ton kahan milegi",
       "فی ٹن لاگت کہاں ملے گی؟", "प्रति टन लागत कहाँ मिलेगी?"),
    _L("Cost Per Ton is the middle card of the Reports page (Accounts group): tons ground in the period, total expenses, expense per ton, grinding income per ton and the margin, plus expenses grouped by head. Pick this month / last month / custom dates at the top of the card.",
       "Cost Per Ton Reports page (Accounts group) ka darmiyan wala card hai: period mein ground ton, kul kharcha, fi ton kharcha, fi ton pisai aamdani aur margin, aur head ke hisaab se kharchay. Card ke oopar se is mahina / pichla mahina / apni dates chunein.",
       "فی ٹن لاگت رپورٹس صفحے (اکاؤنٹس گروپ) کا درمیان والا کارڈ ہے: مدت میں پسے ٹن، کل خرچہ، فی ٹن خرچہ، فی ٹن پسائی آمدنی اور مارجن، اور ہیڈ کے حساب سے اخراجات۔ کارڈ کے اوپر سے اس مہینہ / پچھلا مہینہ / اپنی تاریخیں منتخب کریں۔",
       "प्रति टन लागत रिपोर्ट पृष्ठ (खाते समूह) का बीच वाला कार्ड है: अवधि में पिसे टन, कुल खर्च, प्रति टन खर्च, प्रति टन पिसाई आय और मार्जिन, और हेड अनुसार खर्च। कार्ड के ऊपर से इस महीना / पिछला महीना / अपनी तिथियाँ चुनें।")),
 _K("page_biz", "page", "reports",
    {"lat": ["party business", "business summary"],
     "ur": ["پارٹی کاروبار"], "hi": ["पार्टी व्यापार"]},
    _L("Party Business Summary", "Party Business Summary", "پارٹی کاروبار خلاصہ", "पार्टी व्यापार सारांश"),
    _L("Where is the Party Business Summary?", "party business summary kahan hai",
       "پارٹی کاروبار خلاصہ کہاں ہے؟", "पार्टी व्यापार सारांश कहाँ है?"),
    _L("The Party Business Summary is the last card of the Reports page (Accounts group): per party - grinding income, other charges, sales total, purchases total and the net business, all in one table.",
       "Party Business Summary Reports page (Accounts group) ka aakhri card hai: har party ka - pisai aamdani, doosray charges, kul farokht, kul khareed aur net business, ek hi table mein.",
       "پارٹی کاروبار خلاصہ رپورٹس صفحے (اکاؤنٹس گروپ) کا آخری کارڈ ہے: ہر پارٹی کا - پسائی آمدنی، دوسرے چارجز، کل فروخت، کل خرید اور خالص کاروبار، ایک ہی جدول میں۔",
       "पार्टी व्यापार सारांश रिपोर्ट पृष्ठ (खाते समूह) का अंतिम कार्ड है: हर पार्टी का - पिसाई आय, दूसरे शुल्क, कुल बिक्री, कुल ख़रीद और शुद्ध व्यापार, एक ही तालिका में।")),
]

_KB_NOMATCH = _L(
    "That one I did not quite get. I know the whole system - every page, every setting, every head, and where each entry goes. Tap a topic below, or ask in other words. (I only know this mill system - nothing outside it.)",
    "Ye wala sawal samajh nahi aaya. Mujhe poora system pata hai - har page, har setting, har head, aur har entry kahan jati hai. Neeche kisi topic par tap kar dein, ya sawal doosray lafzon mein pooch lein. (Mein sirf aap ke mill system ke baare mein janta hoon - is ke bahar ki cheezein mujhe nahi aatin.)",
    "یہ والا سوال سمجھ نہیں آیا۔ مجھے پورا سسٹم پتا ہے - ہر صفحہ، ہر ترتیب، ہر ہیڈ، اور ہر انٹری کہاں جاتی ہے۔ نیچے کسی موضوع پر ٹیپ کر دیں، یا سوال دوسرے لفظوں میں پوچھ لیں۔",
    "यह वाला सवाल समझ नहीं आया। मुझे पूरा सिस्टम पता है - हर पृष्ठ, हर सेटिंग, हर हेड, और हर एंट्री कहाँ जाती है। नीचे किसी विषय पर टैप करें, या सवाल दूसरे शब्दों में पूछें।")

# extra chip candidates for areas the guide (not the KB) answers
_KB_CHIP_TOPICS = [
    {"kw": {"lat": ["setting", "settings"], "ur": ["ترتیبات"], "hi": ["सेटिंग्स"]},
     "label": _L("Settings", "Settings", "ترتیبات", "सेटिंग्स"),
     "q": _L("Where are the settings?", "setting wali jaga kahan hai",
             "ترتیبات کہاں ہیں؟", "सेटिंग्स कहाँ हैं?"),
     "view": "settings"},
    {"kw": {"lat": ["vehicle in", "gari in"], "ur": ["گاڑی اندر"], "hi": ["गाड़ी अंदर"]},
     "label": _L("Vehicle In", "Vehicle In", "گاڑی اندر", "गाड़ी अंदर"),
     "q": _L("Where is Vehicle In?", "vehicle in kahan hai",
             "گاڑی اندر کہاں ہے؟", "गाड़ी अंदर कहाँ है?"),
     "view": "vehicle_in"},
    {"kw": {"lat": ["stock"], "ur": ["اسٹاک"], "hi": ["स्टॉक"]},
     "label": _L("Stock position", "Stock position", "اسٹاک صورتحال", "स्टॉक स्थिति"),
     "q": _L("What is the stock position?", "stock kitna hai",
             "اسٹاک کتنا ہے؟", "स्टॉक कितना है?"),
     "view": None},
]
_KB_CHIP_DEFAULTS = ["page_ledger", "flow_grindprod", "rule_backup"]

def _kb_kw_len(kw, lat, urn, raw):
    """Length of the longest keyword of one set that hits, else 0."""
    bl = 0
    for a in kw.get("lat", []):
        if a in lat and len(a) > bl:
            bl = len(a)
    for a in kw.get("ur", []):
        if a and _norm_urdu(a) in urn and len(a) > bl:
            bl = len(a)
    for a in kw.get("hi", []):
        if a and a in raw and len(a) > bl:
            bl = len(a)
    return bl

def _kb_pick(entries, lat, urn, raw):
    best, bl = None, 0
    for e in entries:
        need = e.get("need")
        if need and not (any(n in lat for n in need)
                          or any(_norm_urdu(n) in urn for n in need)
                          or any(n in raw for n in need)):
            continue
        l = _kb_kw_len(e["kw"], lat, urn, raw)
        if l > bl:
            best, bl = e, l
    return best, bl

def _kb_pat(pat, lat, urn, raw):
    return (any(k in lat for k in pat["lat"])
            or any(_norm_urdu(k) in urn for k in pat["ur"])
            or any(k in raw for k in pat["hi"]))

def _kb_dyn(con, e):
    d = e.get("dyn")
    try:
        if d == "wastage":
            return "%g" % wastage_pct(con)
        if d == "bagw":
            bw = bag_weights(con)
            return "powder %g kg, filter %g kg" % (
                float(bw.get("powder_bag_kg") or 50), float(bw.get("filter_bag_kg") or 50))
        if d == "limits":
            r = cash_rules(con)
            return "holder limit Rs %s, approval limit Rs %s" % (
                format(float(r["holder_limit"]), ",.0f"),
                format(float(r["approval_limit"]), ",.0f"))
        if d == "age":
            return meta_get(con, "powder_age_days", "3") or "3"
    except Exception:
        return ""
    return ""

# ------------------------------------------------------------ alias map --
# Vocabulary coverage: every topic (data intents, pages, settings,
# khata heads, data flows, form/field concepts) carries a WIDE trigger
# set — canonical labels, Roman-Urdu colloquial variants,
# transliteration variants, synonyms and common misspellings — merged
# into the live keyword tables here. Longest phrase wins in the
# matchers, so wide sets stay safe.
_KW_ALIAS = {
 "vehicles": {"lat": ["vehical", "vehicals", "gaddi", "gaari", "wagon", "loader", "trolley", "truck wala",
                      "dakhil hui", "rawana hui", "nikal gayi", "aayi thi", "gayi thi",
                      "gari aayi", "gari gayi", "vehicle in", "vehicle out"],
              "ur": ["گاڑیاں آئیں", "گاڑی آئی", "گاڑی گئی"], "hi": ["गाड़ी आई", "गाड़ी गई", "वाहन"]},
 "production": {"lat": ["pisai hui", "pisa hua", "kitna pisa", "boriyan bani", "thele bane",
                        "thailay", "thela", "bori bhar", "packing hui"],
                "ur": ["پیداوار ہوئی", "بوریاں بنیں"], "hi": ["पिसाई हुई", "बोरे बने"]},
 "stock": {"lat": ["stok", "bacha hua maal", "mojood stock", "godam mein kitna", "inventory",
                   "maal kitna hai", "pathar para hai", "powder para hai", "reh gaya maal"],
           "ur": ["بچا ہوا مال", "گودام میں کتنا"], "hi": ["बचा हुआ माल", "गोदाम में कितना"]},
 "expenses": {"lat": ["kharch", "lagat", "kharcha hua", "kharchay", "bill", "diesel ka kharcha"],
              "ur": ["خرچ ہوا"], "hi": ["खर्च हुआ", "लागत"]},
 "cash": {"lat": ["naqad", "paisay", "paise", "rokkar", "cash aya", "cash gaya", "money in", "money out"],
          "ur": ["پیسے", "نقدی"], "hi": ["पैसे", "नकदी"]},
 "workers": {"lat": ["mulazim", "banda", "banday", "labour wala", "kaam karne wala", "mazdur",
                     "mahana", "salary wala", "pagaar", "paghar"],
             "ur": ["ملازم", "مزدور کون"], "hi": ["मज़दूर कौन", "तनख़्वाह"]},
 "dues": {"lat": ["paisay baqi", "baqi hain", "baqi", "baki hai", "lena dena", "udhaar kitna", "wajibaat", "wajib"],
          "ur": ["باقی", "لین دین"], "hi": ["बाकी", "लेन देन"]},
 "receivable": {"lat": ["mujhe lene", "mujhy lene", "wasooli", "wusooli", "lenay hain", "party ne dena"],
                "ur": ["مجھے لینے"], "hi": ["मुझे लेने"]},
 "payable": {"lat": ["mujhe dene", "mujhy dene", "denay hain", "apne zimme", "mill ne dena"],
             "ur": ["مجھے دینے"], "hi": ["मुझे देने"]},
 "balance": {"lat": ["balanc", "bahi", "ledger", "account", "lena dena", "jamah kharch", "jama kharch",
                     "kitna banta", "hisab kitab"],
             "ur": ["لیجر", "اکاؤنٹ", "لین دین"], "hi": ["लेजर", "अकाउंट", "लेन देन"]},
 "profit": {"lat": ["bachat", "kamayi", "kamai", "nafaa", "earning", " earnings"],
            "ur": ["بچت", "کمائی"], "hi": ["बचत", "कमाई"]},
 "summary": {"lat": ["roz ka hisaab", "din bhar ka", "aaj ka khulasa", "daily report",
                     "din ki report", "roznamcha khulasa"],
             "ur": ["روز کا حساب"], "hi": ["रोज़ का हिसाब", "दैनिक रिपोर्ट"]},
 "today": {"lat": ["ajj", "aj ka", "aaj ka"], "ur": [], "hi": []},
 "month": {"lat": ["mahinay", "maheenay", "monthly"], "ur": [], "hi": ["मासिक"]},
 "phosdetail": {"lat": ["register", "rozmarra", "phosphate register", "daily register"],
                "ur": ["رجسٹر"], "hi": ["रजिस्टर"]},
}
_KB_ALIAS = {
 "set_bagw": {"lat": ["bag ka wazn", "bag wazn", "bag weight", "bori ka wazan", "thela wazan", "per bag kg", "bag kg",
                      "powder bag weight", "filter bag weight", "default bag"],
              "ur": ["تھیلے کا وزن"], "hi": ["बोरे का वज़न"]},
 "set_wastage": {"lat": ["wastage", "wastge", "wastage percent", "kami percent", "kmi", "loss percent", "barbadi ka percent"],
                 "ur": ["ضائع فیصد"], "hi": ["वेस्टेज"]},
 "set_profile": {"lat": ["mill name", "mill profile", "factory name", "mill ki maloomat", "profile"],
                 "ur": ["مل پروفائل"], "hi": ["मिल प्रोफ़ाइल"]},
 "set_logo": {"lat": ["logo", "mill logo", "tasveer logo", "logo lagana"], "ur": ["لوگو"], "hi": ["लोगो"]},
 "set_theme": {"lat": ["theme", "theem", "rang", "color", "colour", "dark mode", "light mode", "theme colour", "rang badalna"],
               "ur": ["تھیم", "رنگ"], "hi": ["थीम", "रंग"]},
 "set_font": {"lat": ["font", "fnt", "print size", "font size", "print font", "font and print"], "ur": ["فونٹ"], "hi": ["फ़ॉन्ट"]},
 "set_banks": {"lat": ["bank list", "bnk list", "banks", "bank names", "apne bank", "bank khate"], "ur": ["بینک"], "hi": ["बैंक"]},
 "set_limits": {"lat": ["cash limit", "cash limt", "holder limit", "cash rules", "peti cash", "petty cash",
                        "limit kitni"], "ur": ["نقد حد"], "hi": ["नकद सीमा"]},
 "set_msg": {"lat": ["whatsapp message", "message style", "khata message", "statement style"],
             "ur": ["واٹس ایپ پیغام"], "hi": ["व्हाट्सएप संदेश"]},
 "set_owawa": {"lat": ["owner whatsapp", "owner number", "malik ka number", "apna whatsapp number", "malik whatsapp", "whatsap number"],
               "ur": ["مالک واٹس ایپ"], "hi": ["मालिक व्हाट्सएप"]},
 "set_voice": {"lat": ["voice", "voic", "awaz", "awaaz", "voice alert", "voice alerts", "bolne wali alert"],
               "ur": ["آواز"], "hi": ["आवाज़"]},
 "set_age": {"lat": ["powder age", "purana powder", "age days", "powder ageing", "kitne din purana"],
             "ur": ["پرانا پاؤڈر"], "hi": ["पुराना पाउडर"]},
 "head_grinding": {"lat": ["grinding head", "grindng head", "pisai head", "pisai ka head", "pisai wala head"], "ur": ["پسائی ہیڈ"], "hi": ["पिसाई हेड"]},
 "head_purchase": {"lat": ["purchase head", "purchse head", "khareed head", "khareed ka head"], "ur": ["خرید ہیڈ"], "hi": ["ख़रीद हेड"]},
 "head_freight": {"lat": ["freight head", "freigt head", "bhara head", "kiraya head", "kiraya wala head"], "ur": ["فریٹ ہیڈ"], "hi": ["फ्रेट हेड"]},
 "head_rent": {"lat": ["rent head", "rnt head", "rent ka head", "gari rent head", "gaari ka kiraya"], "ur": ["کرایہ ہیڈ"], "hi": ["किराया हेड"]},
 "head_expense": {"lat": ["expense head", "kharcha head", "heads", "sub head", "sub-head"],
                  "ur": ["خرچہ ہیڈ", "ذیلی ہیڈ"], "hi": ["खर्च हेड", "उप हेड"]},
 "head_khata": {"lat": ["khata head", "khata hed", "ledger head", "hisab head", "bahi khata"], "ur": ["کھاتہ ہیڈ"], "hi": ["खाता हेड"]},
 "head_dr_cr": {"lat": ["debit", "credit", "jama", "naam e khata", "debit credit farq",
                        "lena dena farq", "debt crdt", "jama aur nam"], "ur": ["ڈیبٹ", "کریڈٹ", "جمع"], "hi": ["डेबिट", "क्रेडिट", "जमा"]},
 "flow_vehicle_in": {"lat": ["vehicle in flow", "gari andar flow", "kanta entry", "gate entry flow", "vehical in save", "gari andar ki entry"],
                     "ur": [], "hi": []},
 "flow_vehicle_out": {"lat": ["vehicle out flow", "dispatch flow", "rawangi flow", "vehical out save", "gari bahar ki entry"], "ur": [], "hi": []},
 "flow_grindprod": {"lat": ["grinding flow", "pisai flow", "production flow", "prodction save", "pisai ki entry"], "ur": [], "hi": []},
 "flow_payment": {"lat": ["payment flow", "adaigi flow", "payment dene", "paymnt save", "adaigi ki entry"], "ur": [], "hi": []},
 "flow_expense": {"lat": ["expense flow", "kharcha flow", "expence save"], "ur": [], "hi": []},
 "flow_owntrade": {"lat": ["apni trade ki entry", "own trad save", "own trade save"], "ur": [], "hi": []},
 "flow_outside": {"lat": ["bahar pisai ki entry", "outside grinding save", "outsid save",
                          "grinding bill", "bill ki entry", "bahir bill"], "ur": [], "hi": []},
 "flow_bags": {"lat": ["bags", "bori", "boriyan", "thela", "bardana", "khali bori", "empty bags"],
               "ur": ["بوری", "باردانہ", "تھیلا"], "hi": ["बोरी", "बरदाना", "थैला"]},
 "flow_attendance": {"lat": ["hazri flow", "chutti flow", "leave flow"], "ur": [], "hi": []},
 "flow_cashhand": {"lat": ["cash hand flow", "handover flow"], "ur": [], "hi": []},
 "flow_ginti": {"lat": ["ginti flow", "count flow", "godam count"], "ur": [], "hi": []},
 "rule_edit_delete": {"lat": ["edit delet", "entry badalna", "ghalti", "correction", "theek karna", "badalna", "mitana",
                              "hata sakta", "galti ho gayi"], "ur": ["غلطی"], "hi": ["गलती", "सुधार"]},
 "rule_roles": {"lat": ["rols", "kis ko access", "kon dekh sakta", "login roles", "staff permission", "manager staff ka farq", "demo login"],
                "ur": [], "hi": []},
 "rule_shift": {"lat": ["din raat", "night shift", "day shift", "shift timing"], "ur": [], "hi": []},
 "rule_backup": {"lat": ["backup", "bakup rule", "data backup", "backup kahan", "backup kab", "data mehfooz"], "ur": ["بیک اپ"], "hi": ["बैकअप"]},
 "rule_lang": {"lat": ["language", "zuban", "urdu language", "hindi language", "bhasha"],
               "ur": ["زبان"], "hi": ["भाषा"]},
 "page_pnl": {"lat": ["pnl", "pnl reprt", "nafa nuqsan", "profit loss", "munafa nuqsan"], "ur": ["نفع نقصان"], "hi": ["लाभ हानि"]},
 "page_dayend": {"lat": ["day end", "dayend", "roz band", "din khatam report"], "ur": ["دن اختتام"], "hi": ["दिन अंत"]},
 "page_cpt": {"lat": ["cost per ton", "cpt reprt", "fi ton lagat", "per ton cost", "ton ki lagat"],
              "ur": ["فی ٹن لاگت"], "hi": ["प्रति टन लागत"]},
 "page_ledger": {"lat": ["ledger page", "ledgr", "khata page", "party ledger", "khata kahan", "party ka khata page"], "ur": [], "hi": []},
 "page_biz": {"lat": ["party business", "bizns report", "business summary", "party ka business", "party ka karobar"], "ur": [], "hi": []},
 "page_bankbook": {"lat": ["bank book", "bnk book", "bank balance", "bank hisab", "bank ki passbook"], "ur": ["بینک بک"], "hi": ["बैंक बुक"]},
}
_VG_ALIAS = {
 "vehicle_in": ["kanta", "gate entry", "weighbridge", "pathar aaya", "rock in page", "maal andar", "gari andar", "gari in", "vehical in", "vehical"],
 "vehicle_out": ["dispatch", "rawangi", "maal bahar", "powder gaya", "gari bahar page", "gari bahar", "gari out", "vehical out"],
 "grindprod": ["pisai", "grinding entry", "production entry", "pisai page", "grindng", "prodction"],
 "warehouse": ["godam", "bag hisab", "stock count", "ginti page", "warehous", "godam ginti"],
 "ownstock": ["apna maal", "own trade history", "trade history", "apna stock page", "stok", "apna stok", "own stok"],
 "outside": ["bahar pisai", "bahir grinding", "doosri mill", "outside mill page", "bahir pisai", "outsid", "outsid grinding", "bahar wali pisai"],
 "parties": ["gahak", "clients", "supplier list", "party list", "naya gahak", "partis"],
 "payments": ["adaigi", "paisay diye", "payment page", "raqam di", "paymnt"],
 "expenses": ["kharcha", "kharcha page", "bill lagana", "kharchay", "expence"],
 "cashbook": ["roznamcha", "day end page", "roz ka cash", "roz ka hisaab", "cashbok"],
 "cashinhand": ["haath cash", "holder cash", "cash handover page", "naqad", "cash in han", "cash in hain", "kis ke paas"],
 "workers": ["mazdoor", "staff list", "worker list", "mulazim", "workrs", "mazdoor ki list"],
 "attendance": ["hazri", "hazri page", "attendance page", "attendnce", "hazri lagana"],
 "machines": ["machine diary", "service book", "repair diary", "machne", "machine ki diary"],
 "phosdetail": ["register", "phosphate register", "roz ka register", "detial", "register wali report"],
 "reports": ["reportein", "reports page", "saari reports", "reprts", "report wali"],
 "settings": ["setting", "settings page", "mill setting", "setings", "setting wali jaga"],
 "logins": ["users", "login banana", "staff login", "logns", "naya user"],
 "data": ["backup", "bakup", "excel", "import export", "data page"],
 "guide": ["rehnumai", "step by step", "guide page", "seekhna", "guid"],
 "departments": ["shoba", "department page", "departmnts", "shoba wala"],
 "cheques": ["cheque", "cheq", "cheque register", "cheque page"],
 "alerts": ["alert", "alrts", "ghanti", "khatray ki ghanti", "khatra ghanti"],
 "recycle": ["recycle", "recycl", "delete wapas", "recycle bin", "data wapas", "delete hua"],
 "leaves": ["chutti", "leves", "leave page", "chutti ki entry"],
 "dashboard": ["dashbord", "home page", "pehla page", "main screen"],
}
for _gid, _extra in _KW_ALIAS.items():
    if _gid in _ASST_KW:
        for _k in ("lat", "ur", "hi"):
            _ASST_KW[_gid][_k] = list(dict.fromkeys(
                list(_ASST_KW[_gid].get(_k, [])) + list(_extra.get(_k, []))))
for _e in _KB:
    _x = _KB_ALIAS.get(_e["id"])
    if _x:
        for _k in ("lat", "ur", "hi"):
            _e["kw"][_k] = list(dict.fromkeys(
                list(_e["kw"].get(_k, [])) + list(_x.get(_k, []))))
for _g in _VIEW_GUIDE:
    _x = _VG_ALIAS.get(_g["view"])
    if _x:
        _g["lat"] = list(dict.fromkeys(list(_g["lat"]) + list(_x)))

def _kb_answer(con, lat, urn, raw, lang):
    """Knowledge-base router. Settings and heads answer on a keyword
    alone (their words are distinctive); rules and flows arbitrate by
    the longer keyword when both hit; flows also need a flow or
    definition intent, extra pages a location intent."""
    by_kind = {}
    for kind in ("setting", "head", "rule", "flow", "page"):
        by_kind[kind] = _kb_pick([e for e in _KB if e["kind"] == kind],
                                 lat, urn, raw)
    e = None
    if by_kind["setting"][0] is not None:
        e = by_kind["setting"][0]
    elif by_kind["head"][0] is not None:
        e = by_kind["head"][0]
    else:
        r, rl = by_kind["rule"]
        f, fl = by_kind["flow"]
        flow_ok = _kb_pat(_KB_FLOW_PAT, lat, urn, raw) or _kb_pat(_KB_DEF_PAT, lat, urn, raw)
        if f is not None and flow_ok and (r is None or fl >= rl):
            e = f
        elif r is not None:
            e = r
        elif by_kind["page"][0] is not None and _kb_pat(_KB_LOC_PAT, lat, urn, raw):
            e = by_kind["page"][0]
    if e is None:
        return None
    txt = e["text"][lang]
    if "{v}" in txt:
        txt = txt.replace("{v}", _kb_dyn(con, e))
    out = {"answer": txt}
    if e.get("view"):
        out["view"] = e["view"]
    return out

def _kb_suggest(lat, urn, raw, lang):
    """The 3 closest topics as tappable chips: scored by keyword hits
    over every KB entry plus the guide-only chip topics; filled up to
    3 from sensible defaults when nothing scores."""
    cand = []
    for e in _KB:
        cand.append({"id": e["id"], "kw": e["kw"], "label": e["label"],
                     "q": e["q"], "view": e.get("view")})
    cand.extend(_KB_CHIP_TOPICS)
    scored = []
    for c in cand:
        s = _kb_kw_len(c["kw"], lat, urn, raw)
        if s:
            scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    picked, seen = [], set()
    for _s, c in scored:
        key = c["label"]["en"]
        if key in seen:
            continue
        seen.add(key)
        picked.append(c)
        if len(picked) == 3:
            break
    if len(picked) < 3:
        by_id = {e["id"]: e for e in _KB}
        for did in _KB_CHIP_DEFAULTS:
            e = by_id[did]
            if e["label"]["en"] not in seen:
                seen.add(e["label"]["en"])
                picked.append({"id": e["id"], "label": e["label"], "q": e["q"],
                               "view": e.get("view")})
            if len(picked) == 3:
                break
    _texts = {e["id"]: e["text"][lang] for e in _KB}
    out = []
    for c in picked[:3]:
        hint = ""
        t = _texts.get(c.get("id") or "")
        if t:
            hint = t.replace("{v}", "").split(". ")[0].strip()
            if len(hint) > 110:
                hint = hint[:107] + "…"
        out.append({"label": c["label"][lang], "q": c["q"][lang], "hint": hint})
    return out


# ------------------------------------------------------------- G wrapper ---
def assistant_answer(con, q, user):
    """Wrapper: returns {answer, view?, report?, suggest?}. Order: the
    full-system knowledge base (settings / heads / rules / data flows /
    extra pages) -> system guide (G1) -> report builder (G2) ->
    ranged/special data (G3) -> the classic data core -> a no-match
    reply carrying the 3 closest topics as tappable chips (never a
    dead end). The capability menu is the greeting for an empty
    question only, never an answer to a real one."""
    raw = (q or "").strip()
    lang = _asst_lang(raw)
    menu = _ASST_MENU[lang]
    if not raw:
        return {"answer": menu}
    lat = _norm_loose(raw.lower())
    urn = _norm_urdu(raw)
    if user and user.get("role") == "client":
        ida = _identity_answer(con, lat, urn, raw, lang, user)
        if ida is not None:
            return ida
        r = _assistant_data(con, q, user)
        return {"answer": r if r is not None else menu}
    soc = _social_answer(raw, lat, urn, lang, user)
    if soc is not None:
        return soc
    # backup STATUS is live data, not knowledge — the KB rule entry
    # keys on the bare word "backup" and would swallow it, so a
    # when/status phrasing is answered here, before the KB
    if ("backup" in lat or "بیک اپ" in urn) and any(
            k in lat for k in ("kab", "hua", "aakhri", "last", "status")):
        _bw = meta_get(con, "last_backup")
        if _bw:
            return {"answer": _ASST[lang]["backup_s"].format(when=_bw)}
        return {"answer": _ASST[lang]["backup_none"]}
    # a NAMED party + wastage/bill is live outside-grinding data, not
    # the wastage-% setting — the KB keys the setting on the bare word
    # "wastage", so route these to the data core first
    if user.get("role") != "client":
        _mp = _match_party(con, lat, urn)
        if _mp is not None and any(k in lat for k in ("wastage", "bill")):
            r = _assistant_data(con, q, user)
            if r is not None:
                return {"answer": r}
    kb = _kb_answer(con, lat, urn, raw, lang)
    if kb is not None:
        return kb
    g = _guide_match(lat, urn, raw)
    if g:
        key = {"en": "en", "roman": "roman", "ur": "urt", "hi": "hit"}[lang]
        grp = _ASST_GROUPS[g["group"]][lang]
        return {"answer": "%s -> %s" % (grp, g[key]), "view": g["view"]}
    ida = _identity_answer(con, lat, urn, raw, lang, user)
    if ida is not None:
        return ida
    rk = _report_kind(con, lat, urn, raw)
    if rk:
        text, fn = _build_report(con, rk[0], rk[1], lang)
        return {"answer": text, "report": {"text": text, "filename": fn}}
    sp = _special_answer(con, lat, urn, raw, lang)
    if sp is not None:
        return {"answer": sp}
    r = _assistant_data(con, q, user)
    if r is not None:
        return {"answer": r}
    sug = _kb_suggest(lat, urn, raw, lang)
    lines = [_KB_NOMATCH[lang]]
    for c in sug:
        if c.get("hint"):
            lines.append("• %s — %s" % (c["label"], c["hint"]))
    return {"answer": "\n".join(lines), "suggest": sug}

# ------------------------------------------------------------- csv/backup ---
TABLES = ["parties", "trips", "grinding_jobs", "grind_sessions", "purchases",
          "sales", "orders", "production", "bag_movements", "client_bags",
          "departments", "workers", "worker_payouts", "attendance", "leaves",
          "approvals", "payments", "cheques", "expense_heads", "expenses",
          "maintenance", "stock_counts", "day_costs", "attachments",
          "payment_proofs", "biometric_devices", "device_punches", "alerts",
          "notifications", "audit_log", "vehicle_tares", "meta", "daily_remarks",
          "shift_closures", "alert_dismissals", "factory_closures"]
EDITABLE_TABLES = {"trips", "grinding_jobs", "purchases", "sales", "production",
                   "payments", "expenses", "worker_payouts", "maintenance",
                   "bag_movements", "client_bags", "orders", "day_costs",
                   "stock_counts", "machines", "machine_entries",
                   "outside_grinding"}
ATTACH_OK_MIME = ("image/", "application/pdf")
ATTACH_MAX = 5 * 1024 * 1024

def table_csv(con, table):
    cur = con.execute("SELECT * FROM %s" % table)
    cols = [d[0] for d in cur.description]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(cols)
    for row in cur.fetchall():
        vals = []
        for v in row:
            if isinstance(v, bytes):
                vals.append("<binary %d bytes>" % len(v))
            else:
                vals.append(v)
        w.writerow(vals)
    return out.getvalue()

def make_backup():
    cfg = load_config()
    bdir = cfg.get("backup_dir") or os.path.join(BASE, "Backups")
    os.makedirs(bdir, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    name = "mill-backup-%s.zip" % stamp
    zpath = os.path.join(bdir, name)
    con = get_db()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        tmp = os.path.join(BASE, "_snapshot.db")
        if os.path.exists(tmp):
            os.remove(tmp)
        dest = sqlite3.connect(tmp)
        con.backup(dest); dest.close()
        z.write(tmp, "mill-database.db")
        os.remove(tmp)
        for t in TABLES:
            try:
                z.writestr("csv/%s.csv" % t, table_csv(con, t))
            except Exception:
                pass
        z.writestr("README.txt",
                   "Phosphate Mill backup created %s\n"
                   "mill-database.db = full database (proof attachments/photos are\n"
                   "stored INSIDE the database, so they are included automatically).\n"
                   "Restore from inside the app (Backup page). csv/ = Excel copies.\n"
                   "Save this ZIP to MEGA / Google Drive to keep it safe off-site.\n" % stamp)
    meta_set(con, "last_backup", today())
    con.commit(); con.close()
    return name, zpath

def days_since_backup(con):
    lb = meta_get(con, "last_backup", "")
    if not lb:
        return None
    try:
        import datetime as _dt
        return (_dt.date.today() - _dt.date.fromisoformat(lb)).days
    except Exception:
        return None

# ------------------------------------------------- excel (xlsx) engine ----
# Minimal stdlib-only XLSX writer/reader (zipfile + XML) shared by every
# module's Excel export / sample / import — ONE engine, no dependencies.
import re as _re
import datetime as _dtmod
from xml.etree import ElementTree as _ET

_XL_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_XL_RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

def _xml_esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))

def _xl_col(idx):
    out = ""
    idx += 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        out = chr(65 + r) + out
    return out

def _xl_numstr(v):
    f = float(v)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return ("%.10f" % f).rstrip("0").rstrip(".")

def xlsx_build(headers, rows):
    """headers: list[str]; rows: list[list] -> .xlsx bytes."""
    shared = []
    sidx = {}
    def sref(s):
        s = str(s)
        if s not in sidx:
            sidx[s] = len(shared)
            shared.append(s)
        return sidx[s]
    def cell(ref, v):
        if v is None or v == "":
            return '<c r="%s"/>' % ref
        if isinstance(v, bool) or isinstance(v, str):
            return '<c r="%s" t="s"><v>%d</v></c>' % (ref, sref(v))
        if isinstance(v, (int, float)):
            return '<c r="%s"><v>%s</v></c>' % (ref, _xl_numstr(v))
        return '<c r="%s" t="s"><v>%d</v></c>' % (ref, sref(v))
    body = []
    allrows = [list(headers)] + [list(r) for r in rows]
    for ri, row in enumerate(allrows, 1):
        cells = "".join(cell("%s%d" % (_xl_col(ci), ri), v) for ci, v in enumerate(row))
        body.append('<row r="%d">%s</row>' % (ri, cells))
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="%s"><sheetData>%s</sheetData></worksheet>'
             % (_XL_NS[1:-1], "".join(body)))
    sst = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<sst xmlns="%s" count="%d" uniqueCount="%d">%s</sst>'
           % (_XL_NS[1:-1], len(shared), len(shared),
              "".join('<si><t xml:space="preserve">%s</t></si>' % _xml_esc(s) for s in shared)))
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="%s" xmlns:r="%s"><sheets>'
          '<sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>'
          % (_XL_NS[1:-1], _XL_RNS[1:-1]))
    wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
              '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
              '</Relationships>')
    rootrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
              '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
              '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
              '</Types>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rootrels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", sst)
    return buf.getvalue()

def _pdf_esc(s):
    """One cell -> safe WinAnsi text for a PDF literal string. Anything
    outside Latin-1 (e.g. Urdu script) degrades to '?' — the numbers and
    Latin names, which are what these sheets carry, stay exact."""
    s = "" if s is None else str(s)
    try:
        s.encode("latin-1")
    except UnicodeEncodeError:
        s = "".join(ch if ord(ch) < 256 else "?" for ch in s)
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def _pdf_num(v):
    """Numeric cell -> display text (ints without decimals)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return ("%f" % f).rstrip("0").rstrip(".")

def pdf_build(headers, rows, title, mill_name):
    """A true PDF of one module's table, built with ONLY the standard
    library (hand-written PDF objects + core Helvetica), so the same
    code runs on the PC install, PythonAnywhere and anywhere else with
    no pip dependency. Mill-name header, generation date, bold header
    row, a totals row for all-numeric columns, page numbers."""
    import zlib
    gen = time.strftime("%Y-%m-%d %H:%M")
    ncols = max(1, len(headers))
    landscape = ncols > 6
    PW, PH = (841.89, 595.28) if landscape else (595.28, 841.89)
    MARGIN = 36.0
    usable = PW - 2 * MARGIN
    FS = 8.0            # body font size
    TFS = 13.0          # mill name
    RH = 13.0           # row height

    def celltxt(v):
        n = _pdf_num(v)
        return n if n is not None else ("" if v is None else str(v))

    disp = [[celltxt(v) for v in r] for r in rows]
    # column widths: proportional to the longest content, then normalised
    raw_w = []
    for ci in range(ncols):
        longest = len(str(headers[ci]))
        for r in disp:
            if ci < len(r):
                longest = max(longest, len(r[ci]))
        raw_w.append(max(4, min(34, longest)))
    tot = float(sum(raw_w)) or 1.0
    widths = [w / tot * usable for w in raw_w]

    def fit(txt, wpt, fs):
        """Truncate txt so it fits wpt points at font size fs (Helvetica
        averages ~0.5 em per character)."""
        maxch = int(wpt / (fs * 0.52))
        if maxch < 1:
            maxch = 1
        return txt if len(txt) <= maxch else txt[:max(1, maxch - 1)] + "~"

    # totals: sum a column when every non-empty value in it is numeric
    totals = None
    if disp:
        totals = []
        for ci in range(ncols):
            vals = [r[ci] for r in disp if ci < len(r) and r[ci] != ""]
            s = 0.0; ok = bool(vals)
            for v in vals:
                try:
                    s += float(v)
                except (TypeError, ValueError):
                    ok = False; break
            totals.append(("%g" % round(s, 3)) if ok and ci > 0 else "")
        if not any(totals):
            totals = None

    def page_lines(page_rows, with_totals):
        ops = []
        y = PH - MARGIN
        ops.append("BT /F2 %.1f Tf %.2f %.2f Td (%s) Tj ET"
                   % (TFS, MARGIN, y - 12, _pdf_esc(mill_name or APP_NAME)))
        y -= 20
        ops.append("BT /F1 9 Tf %.2f %.2f Td (%s) Tj ET"
                   % (MARGIN, y - 9, _pdf_esc("%s — generated %s" % (title, gen))))
        y -= 16
        ops.append("0.85 g %.2f %.2f %.2f %.2f re f 0 g"
                   % (MARGIN, y - RH + 3, usable, RH))
        x = MARGIN
        for ci in range(ncols):
            ops.append("BT /F2 %.1f Tf %.2f %.2f Td (%s) Tj ET"
                       % (FS, x + 2, y - RH + 6.5,
                          _pdf_esc(fit(str(headers[ci]), widths[ci] - 4, FS))))
            x += widths[ci]
        y -= RH
        ops.append("%.2f %.2f m %.2f %.2f l 0.6 w S" % (MARGIN, y + 3, MARGIN + usable, y + 3))
        for r in page_rows:
            x = MARGIN
            for ci in range(ncols):
                v = r[ci] if ci < len(r) else ""
                if v != "":
                    num = _pdf_num(v)
                    if num is not None:
                        tw = len(num) * FS * 0.52
                        ops.append("BT /F1 %.1f Tf %.2f %.2f Td (%s) Tj ET"
                                   % (FS, x + widths[ci] - 2 - tw, y - RH + 6.5, _pdf_esc(num)))
                    else:
                        ops.append("BT /F1 %.1f Tf %.2f %.2f Td (%s) Tj ET"
                                   % (FS, x + 2, y - RH + 6.5, _pdf_esc(fit(v, widths[ci] - 4, FS))))
                x += widths[ci]
            y -= RH
            ops.append("0.9 g %.2f %.2f m %.2f %.2f l 0.25 w S 0 g" % (MARGIN, y + 3, MARGIN + usable, y + 3))
        if with_totals and totals:
            ops.append("%.2f %.2f m %.2f %.2f l 0.8 w S" % (MARGIN, y + 3, MARGIN + usable, y + 3))
            x = MARGIN
            for ci in range(ncols):
                v = "Total" if ci == 0 else totals[ci]
                if v:
                    if ci == 0:
                        ops.append("BT /F2 %.1f Tf %.2f %.2f Td (%s) Tj ET"
                                   % (FS, x + 2, y - RH + 6.5, _pdf_esc(v)))
                    else:
                        tw = len(v) * FS * 0.52
                        ops.append("BT /F2 %.1f Tf %.2f %.2f Td (%s) Tj ET"
                                   % (FS, x + widths[ci] - 2 - tw, y - RH + 6.5, _pdf_esc(v)))
                x += widths[ci]
            y -= RH
        return ops, y

    per_page = max(1, int((PH - 2 * MARGIN - 49) / RH))
    chunks = [disp[i:i + per_page] for i in range(0, len(disp), per_page)] or [[]]
    streams = []
    for pi, chunk in enumerate(chunks):
        ops, y = page_lines(chunk, pi == len(chunks) - 1)
        ops.append("BT /F1 7.5 Tf %.2f %.2f Td (%s) Tj ET"
                   % (PW / 2 - 30, MARGIN - 14,
                      _pdf_esc("Page %d of %d" % (pi + 1, len(chunks)))))
        streams.append("\n".join(ops).encode("latin-1", "replace"))

    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join("%d 0 R" % (5 + 2 * i) for i in range(len(streams)))
    objs.append(("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(streams))).encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    for i, st in enumerate(streams):
        objs.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] "
                     "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>"
                     % (PW, PH, 6 + 2 * i)).encode())
        comp = zlib.compress(st)
        objs.append(b"<< /Length " + str(len(comp)).encode() + b" /Filter /FlateDecode >>\nstream\n" + comp + b"\nendstream")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs):
        offsets.append(out.tell())
        out.write(("%d 0 obj\n" % (i + 1)).encode())
        out.write(body)
        out.write(b"\nendobj\n")
    xref = out.tell()
    out.write(("xref\n0 %d\n" % (len(objs) + 1)).encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(("%010d 00000 n \n" % off).encode())
    out.write(("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
               % (len(objs) + 1, xref)).encode())
    return out.getvalue()

def _xl_cell_value(c, shared):
    t = c.get("t")
    v = c.find(_XL_NS + "v")
    vtxt = v.text if v is not None else None
    if t == "s":
        try:
            return shared[int(vtxt)]
        except Exception:
            return ""
    if t == "inlineStr":
        isel = c.find(_XL_NS + "is")
        if isel is None:
            return ""
        return "".join((x.text or "") for x in isel.iter(_XL_NS + "t"))
    if t == "b":
        return "TRUE" if vtxt == "1" else "FALSE"
    if vtxt is None:
        return None
    if t in ("str", "e"):
        return vtxt
    try:
        return float(vtxt)
    except Exception:
        return vtxt

def xlsx_parse(data):
    """xlsx bytes -> list of row-lists (values str / float / None)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = _ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.iter(_XL_NS + "si"):
            shared.append("".join((x.text or "") for x in si.iter(_XL_NS + "t")))
    sheet_name = None
    try:
        wb = _ET.fromstring(z.read("xl/workbook.xml"))
        rels = _ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.get("Id"): r.get("Target") for r in rels}
        for sh in wb.iter(_XL_NS + "sheet"):
            tgt = relmap.get(sh.get(_XL_RNS + "id"), "")
            if tgt:
                sheet_name = "xl/" + tgt.lstrip("/") if not tgt.startswith("xl/") else tgt
            break
    except Exception:
        pass
    if not sheet_name or sheet_name not in names:
        cands = sorted(n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml"))
        if not cands:
            raise ValueError("Excel file ke andar sheet nahi mili")
        sheet_name = cands[0]
    root = _ET.fromstring(z.read(sheet_name))
    grid = []
    for row in root.iter(_XL_NS + "row"):
        vals = {}
        maxc = -1
        for c in row.iter(_XL_NS + "c"):
            ref = c.get("r") or ""
            m = _re.match(r"([A-Z]+)", ref)
            ci = 0
            if m:
                ci = 0
                for ch in m.group(1):
                    ci = ci * 26 + (ord(ch) - 64)
                ci -= 1
            vals[ci] = _xl_cell_value(c, shared)
            maxc = max(maxc, ci)
        grid.append([vals.get(i) for i in range(maxc + 1)] if maxc >= 0 else [])
    return grid

def _grid_to_dicts(grid):
    """First non-empty row = headers; rest -> dicts keyed by stripped headers."""
    hdr_i = None
    for i, row in enumerate(grid):
        if any(v is not None and str(v).strip() != "" for v in row):
            hdr_i = i
            break
    if hdr_i is None:
        return [], []
    headers = [str(v).strip() if v is not None else "" for v in grid[hdr_i]]
    out = []
    for row in grid[hdr_i + 1:]:
        if all(v is None or str(v).strip() == "" for v in row):
            continue
        d = {}
        for ci, h in enumerate(headers):
            if h:
                d[h] = row[ci] if ci < len(row) else None
        out.append(d)
    return headers, out

def _csv_to_dicts(text):
    rdr = csv.DictReader(io.StringIO(text))
    if not rdr.fieldnames:
        return [], []
    headers = [(h or "").strip() for h in rdr.fieldnames]
    out = []
    for r in rdr:
        if r is None:
            continue
        d = {}
        for k, v in r.items():
            if k is None:
                continue
            d[k.strip()] = v
        if any(v is not None and str(v).strip() != "" for v in d.values()):
            out.append(d)
    return headers, out

def upload_rows(d):
    """Request body -> (headers, raw row dicts) from an uploaded .xlsx/.csv."""
    b64 = d.get("file_b64") or ""
    if b64:
        try:
            raw = base64.b64decode(b64)
        except Exception:
            raise ValueError("file data kharab hai")
        if raw[:2] == b"PK":
            return _grid_to_dicts(xlsx_parse(raw))
        try:
            return _csv_to_dicts(raw.decode("utf-8-sig"))
        except Exception:
            raise ValueError("file parhi nahi gayi — .xlsx ya .csv file dein")
    if d.get("csv"):
        return _csv_to_dicts(d["csv"])
    raise ValueError("koi file nahi mili")

# --- import value helpers (raise ValueError with a friendly reason) --------
def _v_text(v):
    return "" if v is None else str(v).strip()

def _norm_name(s):
    return " ".join(str(s or "").strip().lower().split())

def _norm_phone(s):
    return "".join(ch for ch in str(s or "") if ch.isdigit())

def _v_num(v, label, required=False, default=0.0):
    if v is None or (isinstance(v, str) and v.strip() == ""):
        if required:
            raise ValueError("%s nahi likha" % label)
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("Rs", "").strip()
    try:
        return float(s)
    except Exception:
        raise ValueError("%s samajh nahi aaya: '%s'" % (label, v))

def _v_int(v, label, required=False, default=0):
    f = _v_num(v, label, required=required, default=None)
    if f is None:
        return default
    return int(f)

def _v_date(v, label="Date", default=""):
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return default
    if isinstance(v, (int, float)):
        # excel serial day number (epoch 1899-12-30)
        dt = _dtmod.date(1899, 12, 30) + _dtmod.timedelta(days=int(v))
        return dt.isoformat()
    s = str(v).strip()
    m = _re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return _dtmod.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except Exception:
            raise ValueError("%s ghalat hai: '%s'" % (label, v))
    m = _re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)
    if m:
        try:
            return _dtmod.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except Exception:
            raise ValueError("%s ghalat hai: '%s'" % (label, v))
    m = _re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$", s)
    if m:
        try:
            return _dtmod.date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except Exception:
            raise ValueError("%s ghalat hai: '%s'" % (label, v))
    raise ValueError("%s samajh nahi aayi: '%s' (YYYY-MM-DD likhein)" % (label, v))

def _hdr_norm(h):
    return " ".join(_re.sub(r"[^a-z0-9]+", " ", str(h or "").lower()).split())

_HDR_ALIAS = {"gross": "gross kg", "tare": "tare kg", "net": "net kg",
              "rate": "rate per ton", "grade": "grade", "party name": "party",
              "vehicle": "vehicle no", "vehicle number": "vehicle no",
              "head name": "head", "sub": "sub head", "credit": "credit limit",
              "opening": "opening balance", "bank name": "bank",
              "channel": "online channel", "cheque number": "cheque no",
              "expected": "expected date", "start": "start date",
              "device": "device code", "salary": "monthly salary"}

def _remap_row(raw, headers):
    """File row dict -> dict keyed by the template's canonical headers."""
    want = {_hdr_norm(h): h for h in headers}
    out = {}
    for k, v in raw.items():
        nk = _hdr_norm(k)
        nk = _HDR_ALIAS.get(nk, nk)
        h = want.get(nk)
        if h is not None and h not in out:
            out[h] = v
    return out

class _XlCtx:
    """Name-resolution maps for one import run (built once from the DB)."""
    def __init__(self, con):
        self.party_map = {}
        for p in con.execute("SELECT id,name FROM parties"):
            self.party_map.setdefault(_norm_name(p["name"]), []).append(p["id"])
        self.heads_main = {}
        self.heads_sub = {}
        for h in con.execute("SELECT * FROM expense_heads"):
            if h["parent_id"]:
                self.heads_sub.setdefault(h["parent_id"], {})[_norm_name(h["name"])] = h["id"]
            else:
                self.heads_main[_norm_name(h["name"])] = h["id"]
        self.dept_map = {}
        for dp in con.execute("SELECT id,name FROM departments"):
            self.dept_map[_norm_name(dp["name"])] = dp["id"]
        self.user_map = {}
        self.user_names = {}
        for usr in con.execute(
                "SELECT id, username FROM users WHERE role IN ('manager','staff')"):
            self.user_map[_norm_name(usr["username"])] = usr["id"]
            self.user_names[usr["id"]] = usr["username"]

def _xl_party(ctx, name, allow_own=False):
    s = _v_text(name)
    if not s:
        if allow_own:
            return None
        raise ValueError("Party ka naam khali hai")
    ids = ctx.party_map.get(_norm_name(s))
    if not ids:
        raise ValueError("Party '%s' system mein nahi mili — pehle Parties page par add karein" % s)
    if len(ids) > 1:
        raise ValueError("Party '%s' ke naam ki %d parties hain — naam wazeh karein" % (s, len(ids)))
    return ids[0]

def _xl_choice(v, options, label, default):
    s = _v_text(v).lower()
    if not s:
        return default
    if s not in options:
        raise ValueError("%s ghalat hai: '%s' (ye ho sakta hai: %s)" % (label, v, ", ".join(options)))
    return s

# --------------------------------------- excel module templates (ONE each) --
# Every module has ONE column template, defined here once and used by the
# sample file, the export and the import alike — so an exported file is
# always re-importable as-is. convert() turns a friendly file row into the
# exact payload dict the form POST uses; create() calls the same shared
# create_* helpers as the forms; dedupe() finds an identical live record
# (imports NEVER duplicate and NEVER overwrite).
def _party_names(con):
    return {p["id"]: p["name"] for p in con.execute("SELECT id,name FROM parties")}

def _conv_parties(con, ctx, r):
    name = _v_text(r.get("Name"))
    if not name:
        raise ValueError("Name khali hai")
    roles = []
    for x in _re.split(r"[,;]", _v_text(r.get("Roles"))):
        x = x.strip().lower()
        if x in ("supplier", "buyer", "grinding") and x not in roles:
            roles.append(x)
    return {"name": name, "phone": _v_text(r.get("Phone")),
            "whatsapp": _v_text(r.get("WhatsApp")), "email": _v_text(r.get("Email")),
            "address": _v_text(r.get("Address")),
            "roles": roles,
            "credit_limit": _v_num(r.get("Credit Limit"), "Credit Limit"),
            "opening_balance": _v_num(r.get("Opening Balance"), "Opening Balance"),
            "open_date": _v_date(r.get("Opening Date"), "Opening Date", "")}

def _dup_parties(con, ctx, p):
    key = (_norm_name(p["name"]), _norm_phone(p["phone"]))
    for row in con.execute("SELECT name,phone FROM parties"):
        if (_norm_name(row["name"]), _norm_phone(row["phone"])) == key:
            return True
    return False

def _conv_payments(con, ctx, r):
    method = _xl_choice(r.get("Method"), ("cash", "bank", "online", "cheque"), "Method", "cash")
    direction = _xl_choice(r.get("Direction"), ("in", "out"), "Direction", "")
    if not direction:
        raise ValueError("Direction khali hai (in ya out likhein)")
    return {"date": _v_date(r.get("Date"), default=today()),
            "party_id": _xl_party(ctx, r.get("Party")),
            "direction": direction,
            "amount": _v_num(r.get("Amount"), "Amount", required=True),
            "method": method,
            "bank_name": _v_text(r.get("Bank")),
            "online_channel": _v_text(r.get("Online Channel")),
            "ref_no": _v_text(r.get("Ref No")),
            "cheque_no": _v_text(r.get("Cheque No")),
            "due_date": _v_date(r.get("Due Date"), "Due Date"),
            "note": _v_text(r.get("Note"))}

def _dup_payments(con, ctx, p):
    return con.execute("SELECT 1 FROM payments WHERE date=? AND party_id=? AND amount=? AND method=?",
                       (p["date"], p["party_id"], p["amount"], p["method"])).fetchone() is not None

def _conv_trips(con, ctx, r):
    direction = _xl_choice(r.get("Direction"), ("in", "out"), "Direction", "")
    if not direction:
        raise ValueError("Direction khali hai (IN ya OUT likhein)")
    gross = _v_num(r.get("Gross kg"), "Gross")
    tare = _v_num(r.get("Tare kg"), "Tare")
    net = _v_num(r.get("Net kg"), "Net")
    if net and not gross:
        # net-only file (the current entry style): gross = net, tare = 0
        gross, tare = net, 0
    base = {"date": _v_date(r.get("Date"), default=today()),
            "direction": direction.upper(),
            "party_id": _xl_party(ctx, r.get("Party"), allow_own=True),
            "vehicle_no": _v_text(r.get("Vehicle No")),
            "driver": _v_text(r.get("Driver")),
            "driver_phone": _v_text(r.get("Driver Phone")),
            "gross_kg": gross,
            "tare_kg": tare,
            "net_kg": net,
            "bags": _v_int(r.get("Bags"), "Bags"),
            "grade_pct": _v_num(r.get("Grade %"), "Grade %"),
            "freight": _v_num(r.get("Freight"), "Freight"),
            "freight_payer": _xl_choice(r.get("Freight Payer"), ("mill", "party"), "Freight Payer", "mill"),
            "grind_rate": _v_num(r.get("Grinding Rate"), "Grinding Rate"),
            "rock_rate": _v_num(r.get("Rock Rate"), "Rock Rate"),
            "rate_type": _xl_choice(r.get("Rate Type"), ("factory", "mine"), "Rate Type", ""),
            "rent": _v_num(r.get("Rent"), "Rent"),
            "loading": _v_num(r.get("Loading"), "Loading"),
            "unloading": _v_num(r.get("Unloading"), "Unloading"),
            "charge_bearer": _xl_choice(r.get("Charge Payer"), ("mill", "party"), "Charge Payer", "party"),
            "buy_from_party_id": _xl_party(ctx, r.get("Buy From"), allow_own=True),
            "rent_to": _xl_choice(r.get("Rent To"), ("seller", "driver"), "Rent To", "seller"),
            "order_id": None,
            "note": _v_text(r.get("Note"))}
    # Own-dispatch sale columns (owner, 28 Oct 2026): an Own OUT row
    # may name "Sold To" + "Sale Rate" — create_trip validates the
    # pair (both or neither) and drops them on any other row, exactly
    # like the form. An unknown buyer name fails the row here.
    if _v_text(r.get("Sold To")):
        base["sale_buyer_id"] = _xl_party(ctx, r.get("Sold To"))
    if _v_text(r.get("Sale Rate")):
        base["sale_rate"] = _v_num(r.get("Sale Rate"), "Sale Rate")
    return base

def _dup_trips(con, ctx, p):
    return con.execute("SELECT 1 FROM trips WHERE date=? AND vehicle_no=? AND direction=?"
                       " AND net_kg=?",
                       (p["date"], p["vehicle_no"], p["direction"],
                        p["net_kg"])).fetchone() is not None

def _conv_grinding(con, ctx, r):
    # MERGED Grinding & Production module. Accepts the merged template
    # (Powder Bags / Powder Bag Kg / Shift / Bag Source / Start Time /
    # End Time / Filter Bags / Filter Bag Kg) AND the old grinding files
    # unchanged (their "Bags" column always meant the lot's powder bags,
    # so it maps to out_bags; their "Filter Powder (kg)" column still
    # maps to kg). create_job's merged path writes the job + one linked
    # production row when out_bags > 0. The per-bag weight columns are
    # carried WITH the file: a file without them imports at the standard
    # 50 kg defaults, whatever the current settings are.
    pb = r.get("Powder Bags")
    if pb is None or (isinstance(pb, str) and not pb.strip()):
        pb = r.get("Bags")
    pb_kg = _v_num(r.get("Powder Bag Kg"), "Powder Bag Kg")
    fb_kg = _v_num(r.get("Filter Bag Kg"), "Filter Bag Kg")
    return {"date": _v_date(r.get("Date"), default=today()),
            "party_id": _xl_party(ctx, r.get("Party"), allow_own=True),
            "tons": _v_num(r.get("Tons"), "Tons"),
            # a Rate column, when the file carries one, is still stored;
            # it is no longer required (the entry form collects none)
            "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton"),
            "grade_pct": _v_num(r.get("Grade %"), "Grade %"),
            # _xl_choice lowercases; shift is stored as Day / Night
            "shift": _xl_choice(r.get("Shift"), ("day", "night"), "Shift", "day").title(),
            "out_bags": _v_int(pb, "Powder Bags"),
            "powder_bag_kg": pb_kg if pb_kg > 0 else 50,
            "bag_source": _xl_choice(r.get("Bag Source"), ("mill", "client"), "Bag Source", "mill"),
            "start_time": _v_text(r.get("Start Time")),
            "end_time": _v_text(r.get("End Time")),
            "filter_bags": _v_num(r.get("Filter Bags"), "Filter Bags"),
            "filter_bag_kg": fb_kg if fb_kg > 0 else 50,
            "filter_kg": _v_num(r.get("Filter Powder (kg)"), "Filter Powder (kg)"),
            "note": _v_text(r.get("Note"))}

def _dup_grinding(con, ctx, p):
    # identity includes the powder bags: since the form went
    # register-style, every merged entry stores tons=0, so tons alone
    # would call two different same-day lots duplicates. Legacy
    # tons-carrying rows (tons > 0) still match on tons as before.
    if float(p.get("tons") or 0) > 0:
        return con.execute("SELECT 1 FROM grinding_jobs WHERE date=? AND party_id IS ? AND tons=?",
                           (p["date"], p["party_id"], p["tons"])).fetchone() is not None
    return con.execute("SELECT 1 FROM grinding_jobs WHERE date=? AND party_id IS ? AND tons=0 AND bags=?",
                       (p["date"], p["party_id"], int(p.get("out_bags") or 0))).fetchone() is not None

def _conv_production(con, ctx, r):
    return {"date": _v_date(r.get("Date"), default=today()),
            "bags": _v_int(r.get("Bags"), "Bags", required=True),
            "party_id": _xl_party(ctx, r.get("Party"), allow_own=True),
            "job_id": None,
            "bag_source": _xl_choice(r.get("Bag Source"), ("mill", "client"), "Bag Source", "mill"),
            "note": _v_text(r.get("Note"))}

def _dup_production(con, ctx, p):
    return con.execute("SELECT 1 FROM production WHERE date=? AND party_id IS ? AND bags=?",
                       (p["date"], p["party_id"], p["bags"])).fetchone() is not None

def _conv_purchases(con, ctx, r):
    item = _xl_choice(r.get("Item"), ("rock", "powder", "other"), "Item", "rock")
    base = {"date": _v_date(r.get("Date"), default=today()),
            "party_id": _xl_party(ctx, r.get("Party")), "item": item,
            "note": _v_text(r.get("Note"))}
    if item == "other":
        base.update({"tons": 0, "grade_pct": 0, "rate_per_ton": 0, "deduction_pct": 0,
                     "bags": 0, "item_name": _v_text(r.get("Item Name")),
                     "qty": _v_num(r.get("Qty"), "Qty", required=True),
                     "unit": _v_text(r.get("Unit")),
                     "unit_rate": _v_num(r.get("Rate per Unit"), "Rate per Unit", required=True)})
    elif item == "powder":
        base.update({"tons": _v_num(r.get("Tons"), "Tons", required=True),
                     "grade_pct": _v_num(r.get("Grade %"), "Grade %"),
                     "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton", required=True),
                     "deduction_pct": 0, "bags": _v_int(r.get("Bags"), "Bags"),
                     "item_name": "", "qty": 0, "unit": "", "unit_rate": 0})
    else:
        base.update({"tons": _v_num(r.get("Tons"), "Tons", required=True),
                     "grade_pct": _v_num(r.get("Grade %"), "Grade %"),
                     "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton", required=True),
                     "deduction_pct": _v_num(r.get("Deduction %"), "Deduction %"),
                     "bags": 0, "item_name": "", "qty": 0, "unit": "", "unit_rate": 0})
    return base

def _purchase_amount(p):
    item = p.get("item") or "rock"
    if item == "other":
        return round(float(p.get("qty") or 0) * float(p.get("unit_rate") or 0), 2)
    if item == "powder":
        return round(float(p.get("tons") or 0) * float(p.get("rate_per_ton") or 0), 2)
    billed = round(p["tons"] * (1 - p["deduction_pct"] / 100.0), 3)
    return billed * p["rate_per_ton"]

def _dup_purchases(con, ctx, p):
    amt = _purchase_amount(p)
    for row in con.execute("SELECT amount FROM purchases WHERE date=? AND party_id=? AND tons=? "
                           "AND COALESCE(item,'rock')=? AND COALESCE(qty,0)=?",
                           (p["date"], p["party_id"], p.get("tons") or 0,
                            p.get("item") or "rock", float(p.get("qty") or 0))):
        if abs(float(row["amount"] or 0) - amt) < 0.01:
            return True
    return False

def _conv_sales(con, ctx, r):
    item = _xl_choice(r.get("Item"), ("rock", "powder", "other"), "Item", "powder")
    base = {"date": _v_date(r.get("Date"), default=today()),
            "party_id": _xl_party(ctx, r.get("Party")), "item": item,
            "order_id": None, "note": _v_text(r.get("Note"))}
    if item == "other":
        base.update({"tons": 0, "bags": 0, "rate_per_ton": 0,
                     "item_name": _v_text(r.get("Item Name")),
                     "qty": _v_num(r.get("Qty"), "Qty", required=True),
                     "unit": _v_text(r.get("Unit")),
                     "unit_rate": _v_num(r.get("Rate per Unit"), "Rate per Unit", required=True)})
    else:
        base.update({"tons": _v_num(r.get("Tons"), "Tons", required=True),
                     "bags": _v_int(r.get("Bags"), "Bags") if item == "powder" else 0,
                     "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton", required=True),
                     "item_name": "", "qty": 0, "unit": "", "unit_rate": 0})
    return base

def _sale_amount(p):
    if (p.get("item") or "powder") == "other":
        return round(float(p.get("qty") or 0) * float(p.get("unit_rate") or 0), 2)
    return round(float(p.get("tons") or 0) * float(p.get("rate_per_ton") or 0), 2)

def _dup_sales(con, ctx, p):
    amt = _sale_amount(p)
    for row in con.execute("SELECT amount FROM sales WHERE date=? AND party_id=? AND tons=? "
                           "AND COALESCE(item,'powder')=? AND COALESCE(qty,0)=?",
                           (p["date"], p["party_id"], p.get("tons") or 0,
                            p.get("item") or "powder", float(p.get("qty") or 0))):
        if abs(float(row["amount"] or 0) - amt) < 0.01:
            return True
    return False

def _conv_outside(con, ctx, r):
    kind = _xl_choice(r.get("Kind"), ("sent", "bill", "received"), "Kind", "sent")
    base = {"date": _v_date(r.get("Date"), default=today()), "kind": kind,
            "party_id": _xl_party(ctx, r.get("Party")),
            "vehicle_no": _v_text(r.get("Vehicle No")), "note": _v_text(r.get("Note"))}
    if r.get("From Party"):
        base["from_party_id"] = _xl_party(ctx, r.get("From Party"))
    if kind == "sent":
        base.update({"tons": _v_num(r.get("Tons"), "Tons", required=True),
                     "grade_pct": _v_num(r.get("Grade %"), "Grade %"),
                     "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton", required=True),
                     "rock_rate": _v_num(r.get("Rock Rate"), "Rock Rate"),
                     "bags": 0})
    else:
        base.update({"tons": 0, "grade_pct": 0,
                     "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton"),
                     "bags": _v_num(r.get("Bags"), "Bags", required=True)})
        if r.get("Rock Used"):
            base["rock_used_t"] = _v_num(r.get("Rock Used"), "Rock Used")
        if r.get("Paid Now"):
            base["paid_now"] = _v_num(r.get("Paid Now"), "Paid Now")
    return base

def _dup_outside(con, ctx, p):
    if p["kind"] == "sent":
        return con.execute("SELECT 1 FROM outside_grinding WHERE date=? AND party_id=? "
                           "AND kind='sent' AND tons=?",
                           (p["date"], p["party_id"],
                            float(p.get("tons") or 0))).fetchone() is not None
    return con.execute("SELECT 1 FROM outside_grinding WHERE date=? AND party_id=? "
                       "AND kind IN ('bill','received') AND bags=?",
                       (p["date"], p["party_id"],
                        float(p.get("bags") or 0))).fetchone() is not None

def _parse_paid_by(ctx, v):
    """'Paid By' cell -> attribution payload. Formats: 'Owner',
    'Manager: <username>', 'Other: <name>'; a plain name means Other."""
    s = _v_text(v)
    if not s:
        return {"paid_kind": "other", "paid_by_holder": "", "paid_name": ""}
    low = s.lower()
    if low == "owner" or low.startswith("owner:"):
        return {"paid_kind": "owner", "paid_by_holder": "", "paid_name": ""}
    if low.startswith("manager:") or low.startswith("manager "):
        nm = s.split(":", 1)[1].strip() if ":" in s else s[7:].strip()
        uid = ctx.user_map.get(_norm_name(nm))
        if uid is None:
            raise ValueError("Manager '%s' ka login (manager/staff) nahi mila" % nm)
        return {"paid_kind": "manager", "paid_by_holder": "user:%d" % uid, "paid_name": ""}
    if low.startswith("other:"):
        nm = s.split(":", 1)[1].strip()
        return {"paid_kind": "other",
                "paid_by_holder": ("name:" + nm) if nm else "", "paid_name": nm}
    return {"paid_kind": "other", "paid_by_holder": "name:" + s, "paid_name": s}

def _conv_expenses(con, ctx, r):
    head_txt = _v_text(r.get("Head"))
    sub_txt = _v_text(r.get("Sub Head"))
    head_id = sub_id = None
    if head_txt:
        head_id = ctx.heads_main.get(_norm_name(head_txt))
        if head_id is None:
            raise ValueError("Head '%s' system mein nahi mila — pehle Expenses page par ye head banayein" % head_txt)
    if sub_txt:
        if head_id is None:
            raise ValueError("Sub Head '%s' ke saath Main Head bhi likhein" % sub_txt)
        sub_id = ctx.heads_sub.get(head_id, {}).get(_norm_name(sub_txt))
        if sub_id is None:
            raise ValueError("Sub Head '%s' head '%s' ke neeche nahi mila" % (sub_txt, head_txt))
    out = {"date": _v_date(r.get("Date"), default=today()),
           "category": "",
           "head_id": head_id, "sub_head_id": sub_id,
           "amount": _v_num(r.get("Amount"), "Amount", required=True),
           "paid_to": _v_text(r.get("Paid To")),
           "method": _xl_choice(r.get("Method"), ("cash", "bank", "online", "cheque"), "Method", "cash"),
           "pay_channel": _v_text(r.get("Bank/Channel")),
           "pay_ref": _v_text(r.get("Cheque/Ref No")),
           "note": _v_text(r.get("Note"))}
    out.update(_parse_paid_by(ctx, r.get("Paid By")))
    return out

def _dup_expenses(con, ctx, p):
    return con.execute("SELECT 1 FROM expenses WHERE date=? AND head_id IS ? AND amount=? AND paid_to=?",
                       (p["date"], p["head_id"], p["amount"], p["paid_to"])).fetchone() is not None

def _conv_workers(con, ctx, r):
    name = _v_text(r.get("Name"))
    if not name:
        raise ValueError("Name khali hai")
    dept_txt = _v_text(r.get("Department"))
    dept_id = None
    if dept_txt:
        dept_id = ctx.dept_map.get(_norm_name(dept_txt))
        if dept_id is None:
            raise ValueError("Department '%s' system mein nahi mila — pehle Departments page par banayein" % dept_txt)
    return {"name": name,
            "kind": _xl_choice(r.get("Type"), ("theka", "salary"), "Type", "theka"),
            "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton"),
            "rate_per_bag": _v_num(r.get("Rate per Bag"), "Rate per Bag"),
            "monthly_salary": _v_num(r.get("Monthly Salary"), "Monthly Salary"),
            "phone": _v_text(r.get("Phone")),
            "department_id": dept_id,
            "device_code": _v_text(r.get("Device Code")),
            "start_date": _v_date(r.get("Start Date"), "Start Date", default=today())}

def _dup_workers(con, ctx, p):
    key = (_norm_name(p["name"]), _norm_phone(p["phone"]))
    for row in con.execute("SELECT name,phone FROM workers"):
        if (_norm_name(row["name"]), _norm_phone(row["phone"])) == key:
            return True
    return False

def _conv_orders(con, ctx, r):
    status = _xl_choice(r.get("Status"), ("open", "closed"), "Status", "open")
    return {"date": _v_date(r.get("Date"), default=today()),
            "party_id": _xl_party(ctx, r.get("Party")),
            "tons": _v_num(r.get("Tons"), "Tons"),
            "bags": _v_int(r.get("Bags"), "Bags"),
            "rate_per_ton": _v_num(r.get("Rate per Ton"), "Rate per Ton", required=True),
            "expected_date": _v_date(r.get("Expected Date"), "Expected Date"),
            "note": _v_text(r.get("Note")),
            "_status": status}

def _dup_orders(con, ctx, p):
    return con.execute("SELECT 1 FROM orders WHERE date=? AND party_id=? AND tons=? AND bags=?",
                       (p["date"], p["party_id"], p["tons"], p["bags"])).fetchone() is not None

def _create_order_xl(con, p, u):
    res = create_order(con, {k: v for k, v in p.items() if not k.startswith("_")}, u)
    if p.get("_status") == "closed":
        con.execute("UPDATE orders SET status='closed' WHERE id=?", (res["id"],))
        con.commit()
    return res

def _create_trip_xl(con, p, u):
    return create_trip(con, p, u, notify=False)

def _exp_parties(con, q):
    return [[p["name"], p["phone"], p["whatsapp"],
             p["email"] if "email" in p.keys() else "", p["address"], p["roles"],
             p["credit_limit"], p["opening_balance"],
             p["open_date"] if "open_date" in p.keys() else ""]
            for p in con.execute("SELECT * FROM parties ORDER BY name")]

def _exp_payments(con, q):
    names = _party_names(con)
    out = []
    for r in con.execute("SELECT * FROM payments ORDER BY date,id"):
        chq = con.execute("SELECT cheque_no,due_date FROM cheques WHERE payment_id=?",
                          (r["id"],)).fetchone()
        out.append([r["date"], names.get(r["party_id"], ""), r["direction"], r["amount"],
                    r["method"], r["bank_name"], r["online_channel"], r["ref_no"],
                    chq["cheque_no"] if chq else "", chq["due_date"] if chq else "",
                    r["note"]])
    return out

def _exp_trips(con, q):
    names = _party_names(con)
    return [[r["date"], r["direction"], names.get(r["party_id"], "") if r["party_id"] else "",
             r["vehicle_no"], r["driver"], r["driver_phone"], r["net_kg"],
             r["bags"], r["grade_pct"], r["freight"], r["freight_payer"],
             r["loading"], r["charge_bearer"], r["note"],
             r["rock_rate"], r["rate_type"], r["rent"], r["grind_rate"],
             names.get(r["buy_from_party_id"], ""), r["rent_to"] or "seller",
             names.get(r["sale_buyer_id"], "") if r["sale_buyer_id"] else "",
             r["sale_rate"] or ""]
            for r in con.execute("SELECT * FROM trips ORDER BY date,id")]

def _exp_grinding(con, q):
    # merged export: one row per job; powder bags / per-bag weights /
    # bag source / shift times / filter bags come from the linked
    # production row when one exists (merged entries), else from the
    # job's own bags column at the standard 50 kg (older entries). A
    # legacy row that stored filter powder directly in kg exports its
    # kg as bags x its stamped bag weight, so the total survives the
    # round trip.
    names = _party_names(con)
    out = []
    for r in con.execute("SELECT * FROM grinding_jobs ORDER BY date,id"):
        pr = con.execute("SELECT bags, powder_bag_kg, bag_source, start_time, end_time, "
                         "filter_kg, filter_bags, filter_bag_kg FROM production "
                         "WHERE job_id=? ORDER BY id LIMIT 1", (r["id"],)).fetchone()
        if pr:
            pb, pb_kg = pr["bags"], _bagw(pr["powder_bag_kg"])
            src, st, et = pr["bag_source"], pr["start_time"], pr["end_time"]
            fb = float(pr["filter_bags"] or 0)
            fb_kg = _bagw(pr["filter_bag_kg"])
            if fb <= 0 and float(pr["filter_kg"] or 0) > 0:
                fb = round(float(pr["filter_kg"]) / fb_kg, 3)
        else:
            pb, pb_kg, src, st, et, fb, fb_kg = r["bags"], 50, "", "", "", 0, 50
        out.append([r["date"], names.get(r["party_id"], "") if r["party_id"] else "",
                    r["tons"], r["grade_pct"], r["shift"] or "Day",
                    pb, pb_kg, src, st, et, fb, fb_kg, r["note"]])
    return out

def _exp_production(con, q):
    names = _party_names(con)
    return [[r["date"], r["bags"], names.get(r["party_id"], "") if r["party_id"] else "",
             r["bag_source"], r["note"]]
            for r in con.execute("SELECT * FROM production ORDER BY date,id")]

def _exp_purchases(con, q):
    names = _party_names(con)
    return [[r["date"], names.get(r["party_id"], ""), r["tons"], r["grade_pct"],
             r["rate_per_ton"], r["deduction_pct"], r["note"], r["item"] or "rock",
             r["item_name"] or "", r["bags"] or 0, r["qty"] or 0, r["unit"] or "",
             r["unit_rate"] or 0]
            for r in con.execute("SELECT * FROM purchases ORDER BY date,id")]

def _exp_sales(con, q):
    names = _party_names(con)
    return [[r["date"], names.get(r["party_id"], ""), r["tons"], r["bags"],
             r["rate_per_ton"], r["note"], r["item"] or "powder",
             r["item_name"] or "", r["qty"] or 0, r["unit"] or "",
             r["unit_rate"] or 0]
            for r in con.execute("SELECT * FROM sales ORDER BY date,id")]

def _exp_outside(con, q):
    names = _party_names(con)
    out = []
    for r in con.execute("SELECT * FROM outside_grinding ORDER BY date,id"):
        used = ""
        if r["kind"] in ("bill", "received"):
            used = _og_consumed(con, r)
        out.append([r["date"], r["kind"], names.get(r["party_id"], ""),
                    names.get(r["from_party_id"], "") if r["from_party_id"] else "",
                    r["tons"], r["grade_pct"], r["rate_per_ton"],
                    r["rock_rate"] or "", r["bags"], used,
                    r["vehicle_no"] or "", r["note"] or ""])
    return out

def _exp_expenses(con, q):
    heads = {h["id"]: h["name"] for h in con.execute("SELECT id,name FROM expense_heads")}
    users = {u["id"]: u["username"] for u in con.execute("SELECT id,username FROM users")}
    def paid_disp(r):
        if r["paid_kind"] == "owner":
            return "Owner"
        if r["paid_kind"] == "manager":
            nm = r["paid_by"] or ""
            if r["paid_by_holder"].startswith("user:"):
                try:
                    nm = users.get(int(r["paid_by_holder"].split(":", 1)[1]), nm)
                except ValueError:
                    pass
            return "Manager: " + nm
        return "Other: " + (r["paid_by"] or "")
    return [[r["date"], heads.get(r["head_id"], r["category"] or ""), heads.get(r["sub_head_id"], ""),
             r["amount"], paid_disp(r), r["method"], r["pay_channel"], r["pay_ref"],
             r["paid_to"], r["note"]]
            for r in con.execute("SELECT * FROM expenses ORDER BY date,id")]

def _exp_workers(con, q):
    depts = {d["id"]: d["name"] for d in con.execute("SELECT id,name FROM departments")}
    return [[r["name"], r["kind"], r["rate_per_ton"], r["rate_per_bag"], r["monthly_salary"],
             r["phone"], depts.get(r["department_id"], ""), r["device_code"], r["start_date"]]
            for r in con.execute("SELECT * FROM workers ORDER BY name")]

def _exp_orders(con, q):
    names = _party_names(con)
    return [[r["date"], names.get(r["party_id"], ""), r["tons"], r["bags"],
             r["rate_per_ton"], r["expected_date"], r["status"], r["note"]]
            for r in con.execute("SELECT * FROM orders ORDER BY date,id")]

def _exp_cashbook(con, q):
    dfrom = _v_date((q.get("from", [""])[0] or ""), default="")
    dto = _v_date((q.get("to", [""])[0] or ""), default="")
    if not dto:
        dto = today()
    if not dfrom:
        dfrom = dto[:8] + "01"
    d0 = _dtmod.date.fromisoformat(dfrom)
    d1 = _dtmod.date.fromisoformat(dto)
    if d1 < d0:
        raise ValueError("date range ulta hai (from > to)")
    if (d1 - d0).days > 370:
        raise ValueError("date range bohat bara hai (max 1 saal)")
    out = []
    cur = d0
    while cur <= d1:
        cb = cashbook(con, cur.isoformat())
        for m in ("cash", "bank", "online", "cheque"):
            mm = cb["methods"][m]
            out.append([cur.isoformat(), m, mm["in"], mm["out"], mm["net"]])
        cur += _dtmod.timedelta(days=1)
    return out

XL_MODULES = {
    "parties": {
        "label": "Parties (Clients)", "perm": "parties",
        "headers": ["Name", "Phone", "WhatsApp", "Email", "Address", "Roles", "Credit Limit", "Opening Balance", "Opening Date"],
        "need": ["Name"],
        "sample": [["Example Party", "03000000000", "03000000000", "", "Example Address", "supplier,buyer", 50000, 0, "2025-04-01"],
                   ["Example Party Do", "03001111111", "", "", "", "grinding", 0, 1000, ""]],
        "export": _exp_parties, "convert": _conv_parties, "dedupe": _dup_parties,
        "key": lambda p: ("parties", _norm_name(p["name"]), _norm_phone(p["phone"])),
        "create": create_party},
    "payments": {
        "label": "Payments (Khata)", "perm": "payments",
        "headers": ["Date", "Party", "Direction", "Amount", "Method", "Bank", "Online Channel", "Ref No", "Cheque No", "Due Date", "Note"],
        "need": ["Party", "Amount"],
        "sample": [["2026-01-05", "Example Party", "in", 5000, "cash", "", "", "", "", "", "Example wasool"],
                   ["2026-01-06", "Example Party", "out", 2000, "bank", "Example Bank", "", "REF-001", "", "", "Example adaigi"]],
        "export": _exp_payments, "convert": _conv_payments, "dedupe": _dup_payments,
        "key": lambda p: ("payments", p["date"], p["party_id"], p["amount"], p["method"]),
        "create": create_payment},
    "trips": {
        "label": "Vehicles / Trips", "perm": "vehicles",
        # Gross/Tare/Unloading left the template when the entry form
        # went net-only (round 5); they stay in "also" so old files —
        # and old exports — still import unchanged. "Buy From" and
        # "Rent To" ride along so an export round-trips losslessly.
        # "Bags" is the OUT dispatch count only: rock arriving IN is
        # weighed, never bagged, so an IN row's Bags value is ignored
        # on import (create_trip stores 0 for every IN trip).
        "also": ["Gross kg", "Tare kg", "Unloading"],
        "headers": ["Date", "Direction", "Party", "Vehicle No", "Driver", "Driver Phone", "Net kg",
                    "Bags", "Grade %", "Freight", "Freight Payer", "Loading", "Charge Payer", "Note",
                    "Rock Rate", "Rate Type", "Rent", "Grinding Rate", "Buy From", "Rent To",
                    "Sold To", "Sale Rate"],
        "need": ["Direction"],
        "sample": [["2026-01-05", "IN", "Example Party", "EX-1234", "Example Driver", "03005555555", 20000, 0, 42, 0, "mill", 0, "party", "Example trip", 1500, "mine", 4000, 0, "", "seller", "", ""],
                   ["2026-01-06", "OUT", "Example Party", "EX-1234", "Example Driver", "03005555555", 10000, 200, 0, 3000, "party", 500, "party", "", 0, "", 0, 800, "", "seller", "", ""]],
        "export": _exp_trips, "convert": _conv_trips, "dedupe": _dup_trips,
        "key": lambda p: ("trips", p["date"], p["vehicle_no"], p["direction"], p["net_kg"]),
        "create": _create_trip_xl},
    "grinding": {
        "label": "Grinding & Production", "perm": ("grinding", "production"),
        # old grinding files: "Bags" meant the powder bags; a "Rate per
        # Ton" column is still read + stored when a legacy file carries
        # one, but it is no longer exported (the form collects no rate);
        # a legacy "Filter Powder (kg)" column still imports as kg
        "also": ["Bags", "Rate per Ton", "Filter Powder (kg)"],
        "headers": ["Date", "Party", "Tons", "Grade %", "Shift",
                    "Powder Bags", "Powder Bag Kg", "Bag Source", "Start Time", "End Time",
                    "Filter Bags", "Filter Bag Kg", "Note"],
        # Tons is NOT required: the entry form collects no rock weight
        # (round 7) — a file without it imports at 0 and consumption is
        # derived register-style, exactly like a form entry.
        "need": [],
        "sample": [["2026-01-05", "Example Party", 10, 42, "Day", 190, 50, "mill", "06:00", "14:00", 2, 50, "Example grinding"],
                   ["2026-01-06", "", 5, 0, "Night", 100, 50, "mill", "", "", 0, 50, "Apni (own) grinding"]],
        "export": _exp_grinding, "convert": _conv_grinding, "dedupe": _dup_grinding,
        "key": lambda p: ("grinding", p["date"], p["party_id"], p["tons"], p.get("out_bags") or 0),
        "create": create_job},
    "production": {
        "label": "Production (Bags) — old format", "perm": "production",
        "headers": ["Date", "Bags", "Party", "Bag Source", "Note"],
        "need": ["Bags"],
        "sample": [["2026-01-05", 200, "Example Party", "mill", "Example production"],
                   ["2026-01-06", 150, "", "mill", "Apni production"]],
        "export": _exp_production, "convert": _conv_production, "dedupe": _dup_production,
        "key": lambda p: ("production", p["date"], p["party_id"], p["bags"]),
        "create": create_production},
    "purchases": {
        "label": "Own Purchases (Ledger)", "perm": "trade",
        "headers": ["Date", "Party", "Tons", "Grade %", "Rate per Ton", "Deduction %", "Note",
                    "Item", "Item Name", "Bags", "Qty", "Unit", "Rate per Unit"],
        "need": ["Party"],
        "sample": [["2026-01-05", "Example Party", 20, 42, 3000, 2, "Example khareed", "rock", "", 0, 0, "", 0],
                   ["2026-01-06", "Example Party", 0, 0, 0, 0, "", "other", "Cement bags", 0, 50, "bags", 800]],
        "export": _exp_purchases, "convert": _conv_purchases, "dedupe": _dup_purchases,
        "key": lambda p: ("purchases", p["date"], p["party_id"], p.get("tons") or 0,
                          p.get("item") or "rock", round(_purchase_amount(p), 2)),
        "create": create_purchase},
    "sales": {
        "label": "Own Sales (Ledger)", "perm": "trade",
        "headers": ["Date", "Party", "Tons", "Bags", "Rate per Ton", "Note",
                    "Item", "Item Name", "Qty", "Unit", "Rate per Unit"],
        "need": ["Party"],
        "sample": [["2026-01-05", "Example Party", 8, 160, 9000, "Example farokht", "powder", "", 0, "", 0],
                   ["2026-01-06", "Example Party", 5, 100, 9200, "", "powder", "", 0, "", 0]],
        "export": _exp_sales, "convert": _conv_sales, "dedupe": _dup_sales,
        "key": lambda p: ("sales", p["date"], p["party_id"], p.get("tons") or 0,
                          p.get("item") or "powder", round(_sale_amount(p), 2)),
        "create": create_sale},
    "outside": {
        "label": "Outside Grinding", "perm": "trade",
        "headers": ["Date", "Kind", "Party", "From Party", "Tons", "Grade %", "Rate per Ton", "Rock Rate", "Bags", "Rock Used", "Vehicle No", "Note"],
        "need": ["Party"],
        "sample": [["2026-01-05", "sent", "Example Mill", "Example Mine", 40, 42, 2500, 1800, 0, "", "LEA-123", "Rock bheja"],
                   ["2026-01-08", "bill", "Example Mill", "", 0, 0, 2500, "", 760, 40, "LEA-123", "Grinding bill"]],
        "export": _exp_outside, "convert": _conv_outside, "dedupe": _dup_outside,
        "key": lambda p: ("outside", p["date"], p["party_id"], p["kind"],
                          float(p.get("tons") or 0), float(p.get("bags") or 0)),
        "create": create_outside},
    "expenses": {
        "label": "Expenses", "perm": "expenses",
        "headers": ["Date", "Head", "Sub Head", "Amount", "Paid By", "Method", "Bank/Channel", "Cheque/Ref No", "Paid To", "Note"],
        "need": ["Amount"],
        "sample": [["2026-01-05", "Utilities", "Diesel", 15000, "Owner", "cash", "", "", "Example Pump", "Example kharcha"],
                   ["2026-01-06", "Office", "Stationery", 1200, "Other: Example Person", "cash", "", "", "Example Shop", ""]],
        "export": _exp_expenses, "convert": _conv_expenses, "dedupe": _dup_expenses,
        "key": lambda p: ("expenses", p["date"], p["head_id"], p["amount"], p["paid_to"]),
        "create": create_expense},
    "workers": {
        "label": "Workers", "perm": "workers",
        "headers": ["Name", "Type", "Rate per Ton", "Rate per Bag", "Monthly Salary", "Phone", "Department", "Device Code", "Start Date"],
        "need": ["Name"],
        "sample": [["Example Worker", "theka", 850, 0, 0, "03002222222", "", "101", "2026-01-05"],
                   ["Example Worker Do", "salary", 0, 0, 45000, "03003333333", "", "", "2026-01-05"]],
        "export": _exp_workers, "convert": _conv_workers, "dedupe": _dup_workers,
        "key": lambda p: ("workers", _norm_name(p["name"]), _norm_phone(p["phone"])),
        "create": create_worker},
    "cashbook": {
        "label": "Cash Book", "perm": "cashbook",
        "headers": ["Date", "Method", "In", "Out", "Net"],
        "need": [], "sample": [],
        "export": _exp_cashbook, "convert": None, "dedupe": None,
        "key": None, "create": None},
}

def xl_analyze(con, module, headers, raw_rows):
    """Validate + dedupe a parsed upload WITHOUT inserting anything.
    Returns items: {row, status: ok|duplicate|error, reason, data, payload?}."""
    M = XL_MODULES[module]
    canon = {_hdr_norm(h): h for h in M["headers"]}
    present = set()
    for h in headers:
        nk = _HDR_ALIAS.get(_hdr_norm(h), _hdr_norm(h))
        if nk in canon:
            present.add(canon[nk])
    missing = [h for h in M["need"] if h not in present]
    if missing:
        raise ValueError("file mein ye columns nahi mile: %s — Sample file download karke usi format mein file banayein"
                         % ", ".join(missing))
    ctx = _XlCtx(con)
    items = []
    seen = set()
    for i, raw in enumerate(raw_rows):
        rowno = i + 2
        # a module may accept extra legacy columns ("also") that its
        # convert() understands but the current template no longer shows
        mapped = _remap_row(raw, M["headers"] + list(M.get("also", [])))
        data = {h: ("" if mapped.get(h) is None else str(mapped.get(h))) for h in M["headers"] if h in mapped}
        try:
            payload = M["convert"](con, ctx, mapped)
        except ValueError as e:
            items.append({"row": rowno, "status": "error", "reason": str(e), "data": data})
            continue
        key = M["key"](payload)
        if key in seen:
            items.append({"row": rowno, "status": "duplicate",
                          "reason": "Yehi record is file mein pehle bhi hai (duplicate)", "data": data})
        elif M["dedupe"](con, ctx, payload):
            items.append({"row": rowno, "status": "duplicate",
                          "reason": "Ye record system mein pehle se maujood hai (duplicate)", "data": data})
        else:
            seen.add(key)
            _note = ""
            if module == "trips" and payload.get("direction") == "IN" \
                    and payload.get("party_id") \
                    and (float(payload.get("rock_rate") or 0) > 0
                         or payload.get("buy_from_party_id")):
                # the purchase block is Own-only (owner, 28 Oct 2026):
                # create_trip drops these fields for a client party —
                # say so in the preview instead of dropping silently
                _note = ("Note: Rock Rate / Buy From sirf Own (Mine) entry par lagta hai — "
                         "is client entry mein ye save nahi honge (sirf pisai arrival save hogi)")
            items.append({"row": rowno, "status": "ok", "reason": _note, "data": data, "payload": payload})
    return items

# --------------------------------------- Item J: required fields -----
def _req_fields(d, spec, partial):
    miss = []
    for key, label, kind in spec:
        if partial and key not in d:
            continue
        v = d.get(key)
        if kind == "text":
            if v is None or str(v).strip() == "":
                miss.append(label)
        elif kind == "pos":
            try:
                ok = float(v) > 0
            except (TypeError, ValueError):
                ok = False
            if not ok:
                miss.append(label)
        elif kind == "num":
            if v is None or (isinstance(v, str) and v.strip() == ""):
                miss.append(label)
    return miss


def _validate_payload(path, d):
    """Server-side twin of the client validator: a record NEVER saves
    while a compulsory field is empty. Returns missing field labels."""
    partial = bool(d.get("id"))
    P = lambda spec: _req_fields(d, spec, partial)
    if path == "/api/parties":
        return P([("name", "Name", "text")])
    if path == "/api/trips":
        m = P([("vehicle_no", "Vehicle No", "text")])
        if not partial:
            try:
                w_ok = float(d.get("gross_kg") or 0) > 0 or float(d.get("net_kg") or 0) > 0
            except (TypeError, ValueError):
                w_ok = False
            if not w_ok:
                m.append("Weights")
        # (a trip never needs a buyer for a sale — Vehicle Out is
        # dispatch-only since 28 Oct 2026; any sale_rate sent by an
        # old client is ignored by create_trip/update_trip.)
        return m
    if path == "/api/jobs":
        # party picker always resolves (a party, or Own = party_id null).
        # Quantity: legacy payloads carry tons (tons / weight_tons) or a
        # bag count (server derives the tons). MERGED Grinding &
        # Production payloads ("out_bags" present) carry NEITHER — the
        # register never weighs ground rock, so the job stores tons 0
        # and its rock consumption derives from the powder produced.
        if d.get("tons") is not None or d.get("weight_tons") is not None:
            v = d.get("tons") if d.get("tons") is not None else d.get("weight_tons")
            try:
                ok = float(v) > 0
            except (TypeError, ValueError):
                ok = False
            return [] if ok else ["Tons"]
        if partial or "out_bags" in d:
            return []
        return P([("bags", "Bags", "pos")])
    if path == "/api/production":
        return P([("bags", "Bags", "pos")])
    if path == "/api/purchases":
        if (d.get("item") or "rock") == "other":
            return P([("party_id", "Party", "text"), ("item_name", "Item Name", "text"),
                      ("qty", "Quantity", "pos"), ("unit_rate", "Rate", "num")])
        return P([("party_id", "Party", "text"), ("tons", "Tons", "pos"),
                  ("rate_per_ton", "Rate", "num")])
    if path == "/api/sales":
        if (d.get("item") or "powder") == "other":
            return P([("party_id", "Party", "text"), ("item_name", "Item Name", "text"),
                      ("qty", "Quantity", "pos"), ("unit_rate", "Rate", "num")])
        if (d.get("source") or "") == "outside":
            # powder sold from an outside factory is entered in BAGS
            return P([("party_id", "Party", "text"), ("bags", "Bags", "pos"),
                      ("rate_per_ton", "Rate", "num")])
        return P([("party_id", "Party", "text"), ("tons", "Tons", "pos"),
                  ("rate_per_ton", "Rate", "num")])
    if path == "/api/outside-grinding":
        if (d.get("kind") or "sent") in ("bill", "received"):
            return P([("party_id", "Outside Mill", "text"), ("bags", "Bags", "pos")])
        return P([("party_id", "Outside Mill", "text"), ("tons", "Tons", "pos"),
                  ("rate_per_ton", "Rate", "num")])
    if path == "/api/direct-deals":
        m = P([("buy_party_id", "Buy From", "text"), ("sell_party_id", "Sell To", "text")])
        if not m and str(d.get("buy_party_id")) == str(d.get("sell_party_id")):
            m.append("Sell To (buyer seller se alag ho)")
        if (d.get("item") or "rock") == "other":
            m += P([("item_name", "Item Name", "text"), ("qty", "Quantity", "pos"),
                    ("buy_unit_rate", "Buy Rate", "num"), ("sell_unit_rate", "Sell Rate", "num")])
        else:
            m += P([("tons", "Tons", "pos"), ("buy_rate", "Buy Rate", "num"),
                    ("sell_rate", "Sell Rate", "num")])
        return m
    if path == "/api/orders":
        return P([("party_id", "Party", "text"), ("tons", "Tons", "pos")])
    if path == "/api/payments":
        m = P([("party_id", "Party", "text"), ("amount", "Amount", "pos")])
        if d.get("method") == "cheque":
            m += P([("due_date", "Due Date", "text")])
        return m
    if path == "/api/expenses":
        m = P([("amount", "Amount", "pos")])
        if not partial and not (d.get("head_id") or d.get("sub_head_id")):
            m.append("Main Head")
        return m
    if path == "/api/workers":
        return P([("name", "Name", "text")])
    if path in ("/api/departments", "/api/departments/update"):
        return P([("name", "Name", "text")])
    if path == "/api/cash-handovers":
        m = P([("amount", "Amount", "pos")])
        if not partial and not (d.get("holder_user_id")
                                or str(d.get("holder_name") or "").strip()):
            m.append("Holder")
        return m
    if path == "/api/cash-counts":
        return P([("holder_key", "Holder", "text"), ("counted", "Counted Amount", "num")])
    if path == "/api/machines":
        return P([("name", "Name", "text")])
    if path == "/api/machine-entries":
        return P([("machine_id", "Machine", "text"), ("date", "Date", "text"),
                  ("work_type", "Work", "text")])
    if path == "/api/godam-counts":
        return P([("counted_bags", "Bags", "num")])
    if path == "/api/phosphate-detail/remark":
        return P([("date", "Date", "text")])
    if path == "/api/users":
        m = P([("username", "Username", "text"), ("role", "Role", "text")])
        if not d.get("id"):
            m += P([("password", "Password", "text")])
        return m
    if path == "/api/attendance":
        return P([("worker_id", "Worker", "text"), ("date", "Date", "text")])
    if path == "/api/leaves":
        return P([("worker_id", "Worker", "text"), ("from_date", "From Date", "text"),
                  ("to_date", "To Date", "text")])
    if path == "/api/payouts":
        return P([("worker_id", "Worker", "text"), ("amount", "Amount", "pos")])
    if path == "/api/heads":
        return P([("name", "Name", "text")])
    return []


# ------------------------------------------------- route -> perm maps -----
# GET surfaces a demo session may never read, whatever the generic
# permission map says (defence in depth: most already ride on the
# 'owner'/'om' markers perm_ok refuses for demo; /api/alerts exposes
# the deletion-alert trail, so it is shut here explicitly). The
# raw-table CSV export (/api/export/*, incl. the meta table with the
# WhatsApp token) is blocked by the prefix check in api_get.
DEMO_BLOCKED_GETS = ("/api/settings", "/api/backups", "/api/users",
                     "/api/notifications", "/api/recycle", "/api/audit",
                     "/api/alerts")

def _get_perm(path):
    """Permission a GET route needs (see perm_ok for the markers)."""
    if path in ("/api/notifications", "/api/recycle", "/api/audit", "/api/users"):
        return "owner"
    if path in ("/api/settings", "/api/backups") or path.startswith("/api/export/"):
        return "om"
    if path == "/api/party-options":
        return None
    if path == "/api/shift-alert":
        return None               # per-family eligibility lives in daily_alerts()
    if path == "/api/shift-closures":
        return ("grinding", "production")
    if path == "/api/factory-status":
        return None               # read-only status for every staff shell
    if path == "/api/dashboard":
        return "dashboard"
    if path == "/api/trends":
        return "dashboard"
    if path == "/api/events":
        return "reports"
    if path.startswith("/api/wa-statement/"):
        return "parties"
    if path == "/api/ownstock":
        return "trade"
    if path == "/api/outside-stock":
        return "trade"
    if path in ("/api/costperton", "/api/party-business", "/api/phosphate-detail"):
        return "reports"
    if path in ("/api/machines", "/api/machine-entries"):
        return "production"
    if path == "/api/godam":
        return "parties"
    if path == "/api/assistant":
        return "reports"          # staff may ask the assistant only with Reports
    if path == "/api/search":
        return None               # sections are filtered per-perm in the handler
    if path.startswith("/api/parties/") and path.endswith("/last-rates"):
        return ("grinding", "trade", "parties")
    if path == "/api/parties" or path.startswith("/api/parties/"):
        return "parties"
    if path in ("/api/tare", "/api/last-trip", "/api/trips", "/api/trip-stock"):
        return "vehicles"
    if path in ("/api/jobs", "/api/grind-sessions"):
        return ("grinding", "production")   # merged Grinding & Production page
    if path in ("/api/purchases", "/api/sales", "/api/trade-history",
                "/api/outside-grinding"):
        return "trade"
    if path == "/api/production":
        return ("grinding", "production")   # merged page reads both lists
    if path in ("/api/warehouse", "/api/bag-moves", "/api/client-bags", "/api/stock-counts"):
        return "parties"
    if path in ("/api/workers", "/api/payouts", "/api/attendance", "/api/departments",
                "/api/leaves", "/api/approvals", "/api/devices", "/api/punches"):
        return "workers"
    if path == "/api/payments":
        return "payments"
    if path in ("/api/expenses", "/api/heads", "/api/maintenance", "/api/day-costs",
                "/api/expense-report"):
        return "expenses"
    if path in ("/api/cashbook", "/api/dayend", "/api/cheques"):
        return "cashbook"
    if path == "/api/bankbook":
        return "cashbook"
    if path == "/api/holder-users":
        return ("expenses", "cashbook")
    if path == "/api/cash-hand":
        return None               # handler filters to the caller's own record
    if path == "/api/pnl":
        return "reports"
    if path == "/api/orders":
        return "orders"
    if path in ("/api/alerts", "/api/proofs"):
        return "vehicles"
    if path == "/api/attachments":
        return ("parties", "vehicles", "payments", "expenses", "trade")
    return "owner"                # unknown GET: fail closed

_DELETE_PERM = {"trips": "vehicles", "grinding_jobs": ("grinding", "production"),
                "purchases": "trade", "sales": "trade",
                "production": ("grinding", "production"), "payments": "payments",
                "expenses": "expenses", "worker_payouts": "workers",
                "maintenance": "expenses", "bag_movements": "parties",
                "client_bags": "parties", "orders": "orders",
                "outside_grinding": "trade",
                "day_costs": "expenses", "stock_counts": "parties",
                "parties": "parties", "workers": "workers",
                "departments": "workers",
                "machines": "production", "machine_entries": "production"}

def _post_perm(path, d):
    """Permission a POST route needs (see perm_ok for the markers)."""
    if path in ("/api/users", "/api/users/update", "/api/users/password",
                "/api/users/delete", "/api/settings", "/api/settings/test-email",
                "/api/restore",
                "/api/restore-recycle", "/api/notifications/read",
                "/api/leaves/decide", "/api/approvals/decide",
                "/api/cash-handovers", "/api/cash-counts", "/api/expenses/status",
                "/api/stock-adjustments/decide",
                "/api/demo/load", "/api/demo/remove"):
        return "owner"
    if path == "/api/cash-handovers/ack":
        return None               # the holder himself (checked in the handler)
    if path in ("/api/profile", "/api/profile/password", "/api/profile/avatar"):
        return None               # round 12: own record only (handler enforces)
    if path in ("/api/xl/import/preview", "/api/xl/import/apply"):
        # per-module Excel import: the module's own permission decides
        mod = XL_MODULES.get((d or {}).get("module") or "")
        return mod["perm"] if mod else "owner"
    if path in ("/api/import/preview", "/api/import/apply", "/api/backup"):
        return "om"
    if path in ("/api/settings/bag-kg", "/api/settings/bag-weights"):
        return "om"               # the Grinding page bag-weight cards
    if path == "/api/email/statement":
        return "parties"          # round 12: same door as the WhatsApp statement
    if path == "/api/email/invoice":
        return "trade"            # round 12: same door as the printed invoice
    if path == "/api/delete":
        return _DELETE_PERM.get((d or {}).get("table"), "owner")
    if path == "/api/parties":
        return "parties"
    if path == "/api/trips":
        return "vehicles"
    if path in ("/api/jobs", "/api/grind/start", "/api/grind/stop"):
        return ("grinding", "production")   # merged entry: either perm opens it
    if path == "/api/shift-alert/dismiss":
        return None               # handler checks eligibility per alert kind
    if path == "/api/shift-closures":
        return ("grinding", "production")
    if path in ("/api/factory-close", "/api/factory-reopen"):
        return "om"               # Owner + Manager only (handler re-checks)
    if path in ("/api/purchases", "/api/sales", "/api/outside-grinding",
                "/api/direct-deals", "/api/direct-deals/delete"):
        return "trade"
    if path in ("/api/orders", "/api/orders/close"):
        return "orders"
    if path == "/api/production":
        return "production"
    if path in ("/api/machines", "/api/machine-entries"):
        return "production"
    if path in ("/api/godam-counts", "/api/stock-adjustments"):
        return "parties"
    if path == "/api/phosphate-detail/remark":
        return "reports"
    if path in ("/api/bag-moves", "/api/client-bags", "/api/stock-counts"):
        return "parties"
    if path in ("/api/departments", "/api/departments/update", "/api/workers",
                "/api/payouts", "/api/attendance", "/api/leaves", "/api/approvals",
                "/api/devices", "/api/bio/import"):
        return "workers"
    if path == "/api/payments":
        return "payments"
    if path == "/api/cheques/status":
        return "cashbook"
    if path in ("/api/heads", "/api/expenses", "/api/maintenance", "/api/day-costs"):
        return "expenses"
    if path in ("/api/attachments", "/api/attachments/delete"):
        return ("parties", "vehicles", "payments", "expenses", "trade")
    if path == "/api/proofs":
        return "vehicles"
    if path in ("/api/proofs/confirm", "/api/proofs/reject"):
        return "payments"
    if path in ("/api/alerts/generate", "/api/alerts/send", "/api/alerts/delete"):
        return "vehicles"
    return "owner"                # unknown POST: fail closed

# --------------------------------------- owner-only edit/delete rule -----
# Owner's order (27 Oct 2026): entries must be correctable afterwards,
# but EDIT and DELETE of any stored entry are the OWNER's alone — like
# a super admin. Creating new entries keeps the module permissions
# exactly as they were. Settings saves (bag-weight defaults included),
# approval decisions (expense / adjustment approve) and profile saves
# are NOT entries and are deliberately absent from these lists.
_EDIT_PATHS = ("/api/delete", "/api/attachments/delete", "/api/alerts/delete",
               "/api/departments/update", "/api/orders/close",
               "/api/direct-deals/delete")
_CREATE_PATHS = ("/api/parties", "/api/trips", "/api/jobs", "/api/purchases",
                 "/api/sales", "/api/orders", "/api/production",
                 "/api/outside-grinding", "/api/direct-deals",
                 "/api/bag-moves", "/api/client-bags", "/api/workers",
                 "/api/payouts", "/api/payments", "/api/expenses",
                 "/api/heads", "/api/machines", "/api/machine-entries",
                 "/api/maintenance", "/api/stock-counts", "/api/leaves",
                 "/api/godam-counts", "/api/devices")

def _entry_mutation(path, d):
    """True when a POST edits or deletes a STORED entry: either a
    dedicated update/delete path, or a create-endpoint call carrying
    an existing record id (that IS an edit, whatever the caller calls
    it). A plain create (no id) is not a mutation."""
    if path in _EDIT_PATHS:
        return True
    return path in _CREATE_PATHS and bool((d or {}).get("id"))

OWNER_EDIT_MSG = "entry edit/delete sirf owner kar sakta hai"

# Password-reset page strings (round 12) — the reset page is
# server-rendered (it is opened from an email, outside the app shell),
# so its en/ur/hi texts live here, chosen by the link's &lang= (the
# account's own saved language).
RESET_TXT = {
 "en": {"title": "Set a new password", "new_pw": "New password",
        "conf_pw": "Confirm password", "btn": "Set password",
        "ok": "Your password has been changed. You can now log in.",
        "bad": "This reset link is invalid or has expired. Please request a new one from the login page.",
        "mismatch": "Passwords do not match.", "empty": "Please enter a password.",
        "login_link": "Go to login"},
 "ur": {"title": "نیا پاس ورڈ لگائیں", "new_pw": "نیا پاس ورڈ",
        "conf_pw": "پاس ورڈ دوبارہ لکھیں", "btn": "پاس ورڈ لگائیں",
        "ok": "آپ کا پاس ورڈ تبدیل ہو گیا ہے۔ اب آپ لاگ ان کر سکتے ہیں۔",
        "bad": "یہ ری سیٹ لنک درست نہیں یا اس کی مدت ختم ہو گئی ہے۔ لاگ ان صفحے سے نیا لنک مانگیں۔",
        "mismatch": "دونوں پاس ورڈ ایک جیسے نہیں ہیں۔", "empty": "براہ کرم پاس ورڈ لکھیں۔",
        "login_link": "لاگ ان پر جائیں"},
 "hi": {"title": "नया पासवर्ड लगाएँ", "new_pw": "नया पासवर्ड",
        "conf_pw": "पासवर्ड फिर से लिखें", "btn": "पासवर्ड लगाएँ",
        "ok": "आपका पासवर्ड बदल गया है। अब आप लॉगिन कर सकते हैं।",
        "bad": "यह रीसेट लिंक मान्य नहीं है या इसकी अवधि समाप्त हो गई है। लॉगिन पृष्ठ से नया लिंक माँगें।",
        "mismatch": "दोनों पासवर्ड एक जैसे नहीं हैं।", "empty": "कृपया पासवर्ड लिखें।",
        "login_link": "लॉगिन पर जाएँ"},
}

# ---------------------------------------------------------------- handler ---
MAIN_PORT = [8765]

class H(BaseHTTPRequestHandler):
    server_version = "MillLocal/2.0"

    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, ctype="text/html; charset=utf-8", code=200):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, body, ctype, fname):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", "attachment; filename=%s" % fname)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return self.wfile.write(body)

    def body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def user(self):
        cookie = self.headers.get("Cookie") or ""
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("mill_session="):
                tok = part.split("=", 1)[1]
                u = SESSIONS.get(tok)
                if u and u.get("exp", 0) > now_ts():
                    return u
                SESSIONS.pop(tok, None)
        return None

    def need_login(self, roles=None):
        u = self.user()
        if not u:
            self.send_json({"error": "login required"}, 401)
            return None
        if roles and u["role"] not in roles:
            self.send_json({"error": "not allowed for this login"}, 403)
            return None
        return u

    def do_GET(self):
        ensure_migrated()
        path = urlparse(self.path).path
        q = parse_qs(urlparse(self.path).query)
        if path == "/" or path == "/index.html":
            return self.static_file("index.html", "text/html; charset=utf-8")
        if path.startswith("/static/"):
            name = path.split("/", 2)[2]
            ctype = "text/css" if name.endswith(".css") else "application/javascript"
            return self.static_file(name, ctype)
        if path == "/download-app":
            return self.download_app()
        if path == "/reset-password":
            return self.reset_page(q)
        if path == "/branding/logo":
            return self.branding_logo()
        if path.startswith("/api/avatar/"):
            return self.user_avatar(path.rsplit("/", 1)[1])
        if path == "/api/edition":
            return self.send_json({"edition": EDITION})
        if path == "/api/state":
            return self.api_state()
        if path.startswith("/api/"):
            return self.api_get(path, q)
        if path.startswith("/print/"):
            return self.print_page(path, q)
        self.send_text("Not found", code=404)

    def download_app(self):
        """Public download of the Android app (owner, 29 Oct 2026).
        The host's static server hands .apk files out as
        application/javascript with no attachment header, so a phone
        browser shows the binary as garbage text instead of saving
        it. This route streams the SAME file with the Android APK
        content type and an attachment disposition, so the browser
        downloads it. The PC edition ships no APK — the route
        answers a plain 404 there instead of crashing."""
        p = os.path.join(STATIC_DIR, "OrushGrindingMill.apk")
        if not os.path.exists(p):
            return self.send_text("not found", code=404)
        with open(p, "rb") as f:
            body = f.read()
        return self.send_file(body, "application/vnd.android.package-archive",
                              "OrushGrindingMill.apk")

    def branding_logo(self):
        """Public route for the mill logo (login screen needs it before
        login). Bytes live in the meta table with the other settings."""
        if not db_path() or not os.path.exists(db_path()):
            return self.send_text("not found", code=404)
        con = get_db()
        try:
            b64 = meta_get(con, "mill_logo_b64")
            mime = meta_get(con, "mill_logo_mime", "image/png") or "image/png"
        finally:
            con.close()
        if not b64:
            return self.send_text("not found", code=404)
        try:
            raw = base64.b64decode(b64)
        except Exception:
            return self.send_text("not found", code=404)
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "public, max-age=300")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        return self.wfile.write(raw)

    def user_avatar(self, uid_raw):
        """Round 12: a login's profile picture (login required — avatars
        are inside-the-system pictures, unlike the public mill logo)."""
        if not self.user():
            return self.send_text("login required", code=401)
        try:
            uid = int(uid_raw)
        except (TypeError, ValueError):
            return self.send_text("not found", code=404)
        if not db_path() or not os.path.exists(db_path()):
            return self.send_text("not found", code=404)
        con = get_db()
        try:
            r = con.execute("SELECT avatar_b64, avatar_mime FROM users WHERE id=?",
                            (uid,)).fetchone()
        finally:
            con.close()
        if not r or not r["avatar_b64"]:
            return self.send_text("not found", code=404)
        try:
            raw = base64.b64decode(r["avatar_b64"])
        except Exception:
            return self.send_text("not found", code=404)
        self.send_response(200)
        self.send_header("Content-Type", r["avatar_mime"] or "image/png")
        self.send_header("Cache-Control", "private, max-age=300")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        return self.wfile.write(raw)

    def do_POST(self):
        ensure_migrated()
        path = urlparse(self.path).path
        if path == "/api/setup":
            return self.api_setup()
        if path == "/api/pick-folder":
            _pu = self.user()
            if _pu and _pu.get("role") == "demo":
                return self.send_json({"error": DEMO_MSG}, 403)
            return self.api_pick_folder()
        if path == "/api/login":
            return self.api_login()
        if path == "/api/forgot-password":
            return self.api_forgot_password()
        if path == "/api/reset-password":
            return self.api_reset_password()
        if path == "/api/logout":
            cookie = self.headers.get("Cookie") or ""
            for part in cookie.split(";"):
                part = part.strip()
                if part.startswith("mill_session="):
                    SESSIONS.pop(part.split("=", 1)[1], None)
            return self.send_json({"ok": True})
        if path.startswith("/api/"):
            return self.api_post(path)
        self.send_text("Not found", code=404)

    def static_file(self, name, ctype):
        p = os.path.join(STATIC_DIR, os.path.basename(name))
        if not os.path.exists(p):
            return self.send_text("missing file", code=404)
        with open(p, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- state / setup / login
    def api_state(self):
        cfg = load_config()
        u = self.user()
        out = {"configured": bool(cfg.get("db_path")), "user": None,
               "db_path": cfg.get("db_path"), "backup_dir": cfg.get("backup_dir"),
               "device_port": MAIN_PORT[0] + DEVICE_PORT_OFFSET, "lan_ip": lan_ip(),
               "edition": EDITION}
        if cfg.get("db_path") and os.path.exists(cfg["db_path"]):
            con = get_db()
            try:
                out["mill"] = {"name": meta_get(con, "mill_name", APP_NAME),
                               "phone": meta_get(con, "mill_phone"),
                               "address": meta_get(con, "mill_address"),
                               "theme_color": meta_get(con, "theme_color", "green") or "green",
                               "has_logo": bool(meta_get(con, "mill_logo_b64")),
                               "logo_ver": int(meta_get(con, "mill_logo_ver", "0") or 0)}
                out["backup_days"] = days_since_backup(con)
                out["factory"] = factory_status(con)
                out["demo_loaded"] = bool(meta_get(con, "demo_ids"))
                out["font"] = font_settings(con)
                out["voice"] = voice_settings(con)
                out["bag_kg"] = bag_kg(con)
                out.update(bag_weights(con))
                if u:
                    out["user"] = {"id": u["id"], "username": u["username"],
                                   "role": u["role"], "party_id": u["party_id"],
                                   "lang": u.get("lang", "en"), "theme": u.get("theme", "light"),
                                   "unit": u.get("unit") or "t", "perms": u.get("perms") or [],
                                   "display_name": u.get("display_name", ""),
                                   "has_avatar": bool(u.get("has_avatar")),
                                   "avatar_ver": u.get("avatar_ver", 0)}
                    if u["role"] == "owner":
                        out["unread_notifications"] = con.execute(
                            "SELECT COUNT(*) c FROM notifications WHERE is_read=0").fetchone()["c"]
                    out["pending_counts"] = pending_counts(con, u)
            finally:
                con.close()
        elif u:
            out["user"] = {"id": u["id"], "username": u["username"], "role": u["role"],
                           "party_id": u["party_id"], "lang": u.get("lang", "en"),
                           "theme": u.get("theme", "light"), "unit": u.get("unit") or "t",
                           "perms": u.get("perms") or [],
                           "display_name": u.get("display_name", ""),
                           "has_avatar": bool(u.get("has_avatar")),
                           "avatar_ver": u.get("avatar_ver", 0)}
        if u and u.get("role") == "demo":
            # never hand server file paths to the public demo login
            out["db_path"] = ""
            out["backup_dir"] = ""
        return self.send_json(out)

    def api_setup(self):
        cfg = load_config()
        if cfg.get("db_path"):
            return self.send_json({"error": "already set up"}, 400)
        d = self.body_json()
        folder = (d.get("db_folder") or "").strip()
        if not folder:
            folder = os.path.join(BASE, "MillData")
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            return self.send_json({"error": "folder cannot be created: %s" % e}, 400)
        backup_folder = (d.get("backup_folder") or "").strip() or os.path.join(folder, "Backups")
        try:
            os.makedirs(backup_folder, exist_ok=True)
        except Exception:
            pass
        cfg["db_path"] = os.path.join(folder, "mill.db")
        cfg["backup_dir"] = backup_folder
        save_config(cfg)
        globals()["CONFIG"] = cfg
        init_db()
        con = get_db()
        salt, h = hash_pw(d.get("owner_password") or d.get("password") or "owner123")
        _oemail = (d.get("owner_email") or "").strip()
        if not _valid_email(_oemail):
            _oemail = ""
        con.execute("INSERT INTO users(username,salt,pass_hash,role,party_id,email,created)"
                    " VALUES(?,?,?,'owner',NULL,?,?)",
                    ((d.get("owner_username") or d.get("username") or "owner").strip(), salt, h, _oemail, today()))
        if d.get("owner_whatsapp"):
            meta_set(con, "owner_whatsapp", d["owner_whatsapp"].strip())
        if d.get("mill_name"):
            meta_set(con, "mill_name", d["mill_name"].strip())
        audit(con, "system", "setup", "database created at " + cfg["db_path"])
        con.commit(); con.close()
        return self.send_json({"ok": True, "db_path": cfg["db_path"]})

    def api_pick_folder(self):
        try:
            import tkinter
            from tkinter import filedialog
            root = tkinter.Tk(); root.withdraw(); root.attributes("-topmost", True)
            path = filedialog.askdirectory(title="Choose folder")
            root.destroy()
            return self.send_json({"path": path or ""})
        except Exception as e:
            return self.send_json({"path": "", "error": "picker not available (%s). Type the folder path instead." % e})

    def api_login(self):
        if not load_config().get("db_path"):
            return self.send_json({"error": "system not set up yet"}, 400)
        d = self.body_json()
        uname = (d.get("username") or "").strip()
        con = get_db()
        r = con.execute("SELECT * FROM users WHERE username=?", (uname,)).fetchone()
        if not r and "@" in uname:
            # round 12: login by email — the login box accepts the
            # username OR the account's email (case-insensitive);
            # the username match above always wins when both could hit
            r = con.execute("SELECT * FROM users WHERE email<>'' AND "
                            "LOWER(email)=LOWER(?)", (uname,)).fetchone()
        if r and float(r["locked_until"] or 0) > now_ts():
            mins = int((float(r["locked_until"]) - now_ts()) / 60) + 1
            con.close()
            return self.send_json({"error": "account locked for %d minutes (too many wrong tries)" % mins}, 423)
        if not r or not check_pw(d.get("password") or "", r["salt"], r["pass_hash"]):
            if r:
                fc = int(r["fail_count"] or 0) + 1
                locked = now_ts() + 15 * 60 if fc >= 5 else 0
                con.execute("UPDATE users SET fail_count=?, locked_until=? WHERE id=?",
                            (0 if locked else fc, locked, r["id"]))
                audit(con, uname, "login_failed",
                      "wrong password (try %d%s)" % (fc, ", account locked 15 min" if locked else ""))
                con.commit()
            con.close()
            return self.send_json({"error": "wrong username or password"}, 401)
        if IS_PC and r["role"] == "client":
            con.close()
            return self.send_json({"error": "Client (gahak) login PC edition mein available nahi hai — ye sirf online version mein hota hai."}, 403)
        con.execute("UPDATE users SET fail_count=0, locked_until=0 WHERE id=?", (r["id"],))
        audit(con, uname, "login", "login ok")
        con.commit(); con.close()
        perms = parse_perms(_rget(r, "perms", "[]"))
        token = secrets.token_hex(24)
        SESSIONS[token] = {"id": r["id"], "username": r["username"], "role": r["role"],
                           "party_id": r["party_id"], "lang": r["lang"] or "en",
                           "theme": r["theme"] or "light", "unit": r["unit"] or "t",
                           "perms": perms,
                           "display_name": _rget(r, "display_name", "") or "",
                           "has_avatar": bool(_rget(r, "avatar_b64", "")),
                           "avatar_ver": _rget(r, "avatar_ver", 0) or 0,
                           "exp": now_ts() + 7 * 24 * 3600}
        body = json.dumps({"ok": True, "role": r["role"], "user": {
            "id": r["id"], "username": r["username"], "role": r["role"],
            "party_id": r["party_id"], "lang": r["lang"] or "en",
            "theme": r["theme"] or "light", "unit": r["unit"] or "t",
            "display_name": _rget(r, "display_name", "") or "",
            "has_avatar": bool(_rget(r, "avatar_b64", "")),
            "avatar_ver": _rget(r, "avatar_ver", 0) or 0,
            "perms": perms}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", "mill_session=%s; Path=/; HttpOnly; SameSite=Strict" % token)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- password reset by email (round 12)
    def api_forgot_password(self):
        # Anti-enumeration: the response is IDENTICAL whether or not
        # the account exists — only the mailbox learns the truth.
        generic = {"ok": True,
                   "message": "If the account exists, a reset email has been sent."}
        if not load_config().get("db_path"):
            return self.send_json(generic)
        d = self.body_json()
        ident = (d.get("username") or d.get("email") or "").strip()
        if not ident:
            return self.send_json(generic)
        con = get_db()
        try:
            r = con.execute("SELECT * FROM users WHERE username=?",
                            (ident,)).fetchone()
            if not r and "@" in ident:
                r = con.execute("SELECT * FROM users WHERE email<>'' AND "
                                "LOWER(email)=LOWER(?)", (ident,)).fetchone()
            if r and r["role"] != "demo" and (r["email"] or "").strip():
                # the public demo login never resets (its password is
                # published on purpose); accounts without a saved
                # email simply receive nothing
                recent = con.execute(
                    "SELECT COUNT(*) c FROM password_resets WHERE user_id=? "
                    "AND created>?", (r["id"], now_ts() - 3600)).fetchone()["c"]
                if recent >= 3:
                    audit(con, r["username"], "password_reset_rate_limited",
                          "3+ reset emails in an hour — this one not sent")
                    con.commit()
                elif not mail_configured(con):
                    audit(con, r["username"], "password_reset_no_mail",
                          "reset requested but email (SMTP) is not set up")
                    con.commit()
                else:
                    con.execute("UPDATE password_resets SET used=2 WHERE "
                                "user_id=? AND used=0", (r["id"],))
                    token = secrets.token_urlsafe(32)
                    th = hashlib.sha256(token.encode("utf-8")).hexdigest()
                    con.execute("INSERT INTO password_resets(user_id,token_hash,"
                                "created,expires,used) VALUES(?,?,?,?,0)",
                                (r["id"], th, now_ts(), now_ts() + 3600))
                    lang = r["lang"] if r["lang"] in ("en", "ur", "hi") else "en"
                    link = "%s/reset-password?token=%s&lang=%s" % (
                        system_base_url(con, self), token, lang)
                    mill = meta_get(con, "mill_name", APP_NAME)
                    T = MAIL_TXT.get(lang) or MAIL_TXT["en"]
                    subj = T["reset_subj"].format(mill=mill)
                    body = T["reset_body"].format(name=r["username"],
                                                  mill=mill, link=link)
                    # a reset is a security function, not a
                    # notification: it sends whenever SMTP is set up,
                    # even if the notification master switch is off
                    ok, detail = send_email(con, r["email"], subj, body,
                                            _email_html(mill, body))
                    log_email(con, "email_reset", None, r["email"], subj,
                              ok, detail)
                    audit(con, r["username"], "password_reset_requested",
                          "reset email %s" % ("sent" if ok else
                                               "FAILED: " + detail))
                    con.commit()
            return self.send_json(generic)
        finally:
            con.close()

    def api_reset_password(self):
        if not load_config().get("db_path"):
            return self.send_json({"error": "system not set up yet"}, 400)
        d = self.body_json()
        token = (d.get("token") or "").strip()
        pw = d.get("password") or ""
        if not token or not pw:
            return self.send_json(
                {"error": "This reset link is invalid or has expired. "
                          "Request a new one."}, 400)
        th = hashlib.sha256(token.encode("utf-8")).hexdigest()
        con = get_db()
        try:
            row = con.execute("SELECT * FROM password_resets WHERE token_hash=? "
                              "AND used=0", (th,)).fetchone()
            if not row or float(row["expires"] or 0) < now_ts():
                return self.send_json(
                    {"error": "This reset link is invalid or has expired. "
                              "Request a new one."}, 400)
            urow = con.execute("SELECT * FROM users WHERE id=?",
                               (row["user_id"],)).fetchone()
            if not urow or urow["role"] == "demo":
                return self.send_json(
                    {"error": "This reset link is invalid or has expired. "
                              "Request a new one."}, 400)
            salt, h = hash_pw(pw)
            con.execute("UPDATE users SET salt=?, pass_hash=?, fail_count=0, "
                        "locked_until=0 WHERE id=?", (salt, h, urow["id"]))
            con.execute("UPDATE password_resets SET used=1 WHERE user_id=? "
                        "AND used=0", (urow["id"],))
            audit(con, urow["username"], "password_reset_done",
                  "password changed via the emailed reset link")
            con.commit()
            _drop_sessions(urow["id"])
            return self.send_json({"ok": True})
        finally:
            con.close()

    def reset_page(self, q):
        token = (q.get("token", [""])[0] or "").strip()
        lang = (q.get("lang", ["en"])[0] or "en")
        if lang not in RESET_TXT:
            lang = "en"
        T = RESET_TXT[lang]
        mill = APP_NAME
        valid = False
        if load_config().get("db_path") and token:
            con = get_db()
            try:
                mill = meta_get(con, "mill_name", APP_NAME)
                th = hashlib.sha256(token.encode("utf-8")).hexdigest()
                row = con.execute("SELECT * FROM password_resets WHERE "
                                  "token_hash=? AND used=0", (th,)).fetchone()
                valid = bool(row and float(row["expires"] or 0) >= now_ts())
            finally:
                con.close()
        rtl = " dir='rtl'" if lang == "ur" else ""
        css = ("<style>body{font-family:system-ui,'Noto Sans Arabic',sans-serif;"
               "background:#0e3a2a;margin:0;padding:24px}"
               ".card{max-width:400px;margin:8vh auto;background:#fff;"
               "border-radius:12px;padding:22px;box-shadow:0 8px 30px rgba(0,0,0,.35)}"
               "h2{margin:0 0 6px;color:#0c7a4e}label{display:block;margin:12px 0 4px;"
               "font-size:13px;color:#444}input{width:100%;box-sizing:border-box;"
               "padding:10px;border:1px solid #bbb;border-radius:8px;font-size:15px}"
               "button{margin-top:16px;width:100%;padding:11px;border:none;"
               "border-radius:8px;background:#0c7a4e;color:#fff;font-size:15px;cursor:pointer}"
               ".muted{color:#777;font-size:13px}.err{color:#b00020}.ok{color:#0c7a4e}"
               "a{color:#0c7a4e}</style>")
        if not valid:
            body = ("<div class='card'><h2>%s</h2><p class='err'>%s</p>"
                    "<p><a href='/'>%s</a></p></div>"
                    % (htmlesc(mill), htmlesc(T["bad"]), htmlesc(T["login_link"])))
        else:
            js = ("<script>async function go(){var p=document.getElementById('p1').value,"
                  "c=document.getElementById('p2').value,m=document.getElementById('m');"
                  "if(!p){m.textContent=%s;m.className='err';return}"
                  "if(p!==c){m.textContent=%s;m.className='err';return}"
                  "var tk=new URLSearchParams(location.search).get('token');"
                  "var r=await fetch('/api/reset-password',{method:'POST',"
                  "headers:{'Content-Type':'application/json'},"
                  "body:JSON.stringify({token:tk,password:p})});"
                  "var j=await r.json().catch(function(){return{}});"
                  "if(j.ok){document.getElementById('f').style.display='none';"
                  "m.textContent=%s;m.className='ok'}"
                  "else{m.textContent=j.error||'error';m.className='err'}}</script>"
                  % (json.dumps(T["empty"]), json.dumps(T["mismatch"]),
                     json.dumps(T["ok"])))
            body = ("<div class='card'><h2>%s</h2><p class='muted'>%s</p>"
                    "<div id='f'><label>%s</label><input id='p1' type='password'>"
                    "<label>%s</label><input id='p2' type='password'>"
                    "<button onclick='go()'>%s</button></div>"
                    "<p id='m'></p><p><a href='/'>%s</a></p></div>%s"
                    % (htmlesc(mill), htmlesc(T["title"]), htmlesc(T["new_pw"]),
                       htmlesc(T["conf_pw"]), htmlesc(T["btn"]),
                       htmlesc(T["login_link"]), js))
        return self.send_text("<!DOCTYPE html><html lang='%s'%s><head>"
                              "<meta charset='utf-8'><meta name='viewport' "
                              "content='width=device-width,initial-scale=1'>"
                              "<title>%s</title>%s</head><body>%s</body></html>"
                              % (lang, rtl, htmlesc(T["title"]), css, body))

# ------------------------------------------------------- biometric device ---
    # -- GET api
    def api_get(self, path, q):
        if IS_PC and path.startswith("/api/my/"):
            return self.send_text("Not found", code=404)
        if path == "/api/my/khata":
            u = self.need_login(("client", "owner", "manager"))
            if not u: return
            if u["role"] == "client":
                pid = u["party_id"]
            else:
                pid = int(q.get("party", [0])[0])
            if not pid:
                return self.send_json({"error": "no party linked"}, 400)
            con = get_db()
            p = con.execute("SELECT * FROM parties WHERE id=?", (pid,)).fetchone()
            if not p:
                con.close()
                return self.send_json({"error": "party not found"}, 404)
            entries, bal = party_ledger(con, pid)
            stock = party_stock(con, pid)
            proofs = [dict(r) for r in con.execute(
                "SELECT * FROM payment_proofs WHERE party_id=? ORDER BY id DESC", (pid,))]
            con.close()
            return self.send_json({"party": dict(p), "entries": entries,
                                   "balance": bal, "stock": stock, "proofs": proofs})
        if path == "/api/profile":
            # round 12: the caller's OWN profile — handled here, before
            # the client gate below, because every role has one
            u = self.need_login()
            if not u: return
            con = get_db()
            try:
                r = con.execute("SELECT username,role,party_id,email,display_name,phone,"
                                "CASE WHEN avatar_b64<>'' THEN 1 ELSE 0 END has_avatar,avatar_ver "
                                "FROM users WHERE id=?", (u["id"],)).fetchone()
                if not r:
                    return self.send_json({"error": "login not found"}, 404)
                prof = dict(r)
                prof["has_avatar"] = bool(prof.get("has_avatar"))
                prof["party_name"] = ""
                if prof.get("party_id"):
                    pr = con.execute("SELECT name FROM parties WHERE id=?",
                                     (prof["party_id"],)).fetchone()
                    if pr:
                        prof["party_name"] = pr["name"] or ""
                return self.send_json(prof)
            finally:
                con.close()
        if path.startswith("/api/attachments/") and path.endswith("/raw"):
            u = self.need_login()
            if not u: return
            aid = int(path.split("/")[3])
            con = get_db()
            r = con.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
            con.close()
            if not r:
                return self.send_text("not found", code=404)
            if u["role"] == "client":
                return self.send_json({"error": "not allowed"}, 403)
            if u["role"] == "staff" and not perm_ok(u, ("parties", "vehicles", "payments", "expenses", "trade")):
                return self.send_json({"error": "not allowed"}, 403)
            body = r["data"] or b""
            self.send_response(200)
            self.send_header("Content-Type", r["mime"] or "application/octet-stream")
            self.send_header("Content-Disposition", "inline; filename=%s" % (r["filename"] or "file"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        u = self.need_login()
        if not u: return
        if u["role"] == "client":
            return self.send_json({"error": "not allowed for this login"}, 403)
        if path in ("/api/xl/export", "/api/xl/sample"):
            return self.xl_download(path, q, u)
        if path == "/api/xl/format":
            return self.xl_format(q, u)
        if not perm_ok(u, _get_perm(path)):
            return self.send_json({"error": "not allowed for this login"}, 403)
        if u["role"] == "demo" and (path in DEMO_BLOCKED_GETS
                                    or path.startswith("/api/export/")):
            # public demo login: secrets-bearing and internals
            # surfaces stay shut even if a future perm change would
            # otherwise open them (settings hold the WhatsApp token,
            # a backup download is the whole database).
            return self.send_json({"error": "demo login se ye page band hai"}, 403)
        con = get_db()
        try:
            names = {p["id"]: p["name"] for p in con.execute("SELECT id,name FROM parties")}
            if path == "/api/party-options":
                # names only — form dropdowns for any non-client login.
                # ?context= filters by party roles (comma string), same map
                # as the UI's partiesFor(): vehicle_in -> supplier+grinding,
                # vehicle_out/orders/sale -> buyer+grinding (orders/sale also
                # accept any buyer), purchase -> supplier, production ->
                # supplier+grinding. No/unknown context -> all parties.
                ctx = (q.get("context", [""])[0] or "").strip()
                want = {"vehicle_in": ("supplier", "grinding"),
                        "vehicle_out": ("buyer", "grinding"),
                        "grinding": ("grinding",),
                        "purchase": ("supplier",),
                        "sale": ("buyer",),
                        "orders": ("buyer",),
                        "production": ("supplier", "grinding"),
                        "grindprod": ("supplier", "grinding")}.get(ctx)
                rows = [{"id": p["id"], "name": p["name"], "roles": p["roles"]}
                        for p in con.execute("SELECT id,name,roles FROM parties ORDER BY name")]
                if want:
                    rows = [r for r in rows
                            if any(w in (r["roles"] or "").split(",") for w in want)]
                return self.send_json(rows)
            if path == "/api/trip-stock":
                # Vehicle Out live stock hint: which pool a dispatch
                # for this party would deduct from (the very _trip_fx
                # stamp the save applies) and the ground powder lying
                # in it — the exact figures the save-time gate checks.
                # available_t is null for a gate pass (no stock moves).
                _spid = q.get("party_id", [""])[0]
                _spid = int(_spid) if str(_spid).isdigit() else None
                _sfx = _trip_fx(con, "OUT", _spid)
                _sold = None
                _sxt = q.get("exclude_trip", [""])[0]
                if str(_sxt).isdigit():
                    _sold = con.execute("SELECT * FROM trips WHERE id=?",
                                        (int(_sxt),)).fetchone()
                _spool = _powder_pool(con, _sfx, _spid, _sold)
                return self.send_json(
                    {"fx": _sfx, "party_id": _spid,
                     "available_t": _spool[1] if _spool else None})
            if path == "/api/dashboard":
                t = today()
                def one(sql, a=()):
                    return con.execute(sql, a).fetchone()["s"] or 0
                parties = []
                to_receive = to_pay = 0.0
                ageing = {"d0_30": 0.0, "d31_60": 0.0, "d60p": 0.0}
                import datetime as _dt
                for p in con.execute("SELECT * FROM parties ORDER BY name"):
                    ents, bal = party_ledger(con, p["id"])
                    parties.append({"id": p["id"], "name": p["name"],
                                    "roles": p["roles"], "balance": bal,
                                    "credit_limit": p["credit_limit"],
                                    "over_limit": bool(p["credit_limit"]) and bal > float(p["credit_limit"] or 0)})
                    if bal > 0:
                        to_receive += bal
                        # ageing: how long since balance last touched zero -
                        # approximate with oldest unpaid entry date
                        oldest = None
                        run = 0.0
                        for e in ents:
                            run = e["balance"]
                            if run > 0 and oldest is None and e["date"]:
                                oldest = e["date"]
                        if oldest:
                            age = (_dt.date.today() - _dt.date.fromisoformat(oldest)).days
                            if age <= 30: ageing["d0_30"] += bal
                            elif age <= 60: ageing["d31_60"] += bal
                            else: ageing["d60p"] += bal
                    else:
                        to_pay += -bal
                gr = con.execute(
                    "SELECT gs.*, p.name party_name FROM grind_sessions gs LEFT JOIN parties p "
                    "ON p.id=gs.party_id WHERE gs.ended='' ORDER BY gs.id DESC").fetchall()
                # E6: machine maintenance due within 7 days (or overdue)
                maint_due = [dict(r) for r in con.execute(
                    "SELECT me.id, me.next_due, me.work_type, m.name machine_name "
                    "FROM machine_entries me LEFT JOIN machines m ON m.id=me.machine_id "
                    "WHERE me.next_due!='' AND me.next_due<=date('now','+7 days') "
                    "ORDER BY me.next_due")]
                wh = warehouse(con)
                ostock = own_stock(con)
                # v3: factory-wide totals + own-vs-clients split, derived
                # ONLY from the existing aggregates (party_stock per party,
                # own_stock, warehouse) — no new math anywhere.
                cl_rock = cl_powder = cl_bags = 0.0
                for p in con.execute("SELECT id FROM parties"):
                    pst = party_stock(con, p["id"])
                    cl_rock += pst["rock_waiting_t"]
                    cl_powder += pst["powder_ready_t"]
                    cl_bags += pst["bags_ready"]
                own_bags = (wh.get("own") or {}).get("bags_ready", 0)
                own_powder = ostock["powder_left_t"]
                dash_totals = {
                    "rock_t": round(ostock["rock_left_t"] + cl_rock, 3),
                    "powder_t": round(own_powder + cl_powder, 3),
                    "bags": own_bags + cl_bags,
                    "to_receive": to_receive, "to_pay": to_pay,
                }
                dash_split = {
                    "own_rock_t": ostock["rock_left_t"],
                    "clients_rock_t": round(cl_rock, 3),
                    "own_powder_t": own_powder,
                    "clients_powder_t": round(cl_powder, 3),
                    "own_bags": own_bags, "clients_bags": cl_bags,
                }
                data = {
                    "date": t,
                    "rock_in_today_t": one("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='IN' AND date=?", (t,)) / 1000.0,
                    "powder_out_today_t": one("SELECT COALESCE(SUM(net_kg),0) s FROM trips WHERE direction='OUT' AND date=?", (t,)) / 1000.0,
                    "ground_today_t": round(jobs_ground_t(con, "WHERE date=?", (t,)), 3),
                    "bags_today": one("SELECT COALESCE(SUM(bags),0) s FROM production WHERE date=?", (t,)),
                    "cash_in_today": one("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE direction='in' AND date=?", (t,)),
                    "cash_out_today": one("SELECT COALESCE(SUM(amount),0) s FROM payments WHERE direction='out' AND date=?", (t,)) +
                                      one("SELECT COALESCE(SUM(amount),0) s FROM expenses WHERE date=? AND status!='rejected'", (t,)),
                    "to_receive": to_receive, "to_pay": to_pay, "ageing": ageing,
                    "totals": dash_totals, "split": dash_split,
                    "powder_ageing": wh.get("ageing") or [],
                    "maint_due": maint_due,
                    # dashboard UI reads rock_t / powder_t / powder_bags —
                    # alias them from own_stock's *_left_t + godam bags_ready
                    # (missing keys crashed the dashboard view on a fresh DB)
                    "own_stock": {**ostock,
                                  "rock_t": ostock["rock_left_t"],
                                  "powder_t": ostock["powder_left_t"],
                                  "powder_bags": (wh.get("own") or {}).get("bags_ready", 0)},
                    "parties": parties,
                    "now_grinding": [dict(r) for r in gr],
                    "bardana": wh["bardana"],
                    "recent": [dict(r) for r in con.execute("SELECT * FROM trips ORDER BY id DESC LIMIT 8")],
                    "cheques_due": [dict(r) for r in con.execute(
                        "SELECT c.*, p.name party_name FROM cheques c LEFT JOIN parties p ON p.id=c.party_id "
                        "WHERE c.status='pending' AND c.due_date!='' AND c.due_date<=date('now','+3 days') ORDER BY c.due_date")],
                }
                # Money in/out is OWNER ONLY (owner's order): today's cash
                # in / cash out, the total receivable / payable (and their
                # copies inside Totals) and the receivables-ageing buckets
                # are REMOVED from the payload for manager/staff — never
                # sent, not merely hidden by the UI. Stock, production and
                # per-party khata balances keep their existing visibility.
                data["money_visible"] = u["role"] == "owner"
                if not data["money_visible"]:
                    for _k in ("cash_in_today", "cash_out_today",
                               "to_receive", "to_pay", "ageing"):
                        data.pop(_k, None)
                    for _k in ("to_receive", "to_pay"):
                        data["totals"].pop(_k, None)
                return self.send_json(data)
            if path == "/api/trends":
                # v3: last-N-days aggregates for the dashboard Daily
                # Progress chart. Every figure comes from day_end() — the
                # exact same source as the Day-End Summary — so today's
                # numbers agree with it to the paisa/kilo.
                import datetime as _dt2
                try:
                    ndays = int((q.get("days", ["7"])[0] or "7"))
                except ValueError:
                    ndays = 7
                ndays = max(1, min(31, ndays))
                base = _dt2.date.today()
                days_out = []
                for i in range(ndays - 1, -1, -1):
                    ds = (base - _dt2.timedelta(days=i)).isoformat()
                    de = day_end(con, ds)
                    cb = de["cashbook"]
                    days_out.append({
                        "date": ds,
                        "rock_in_t": round(de["rock_in_t"], 3),
                        "ground_t": round(de["ground_t"], 3),
                        "bags": de["bags"],
                        "cash_in": cb["total_in"], "cash_out": cb["total_out"],
                        "cash_net": cb["total"],
                    })
                if u["role"] != "owner":
                    # the chart's money series are owner-only too (above)
                    for _d in days_out:
                        _d.pop("cash_in", None)
                        _d.pop("cash_out", None)
                        _d.pop("cash_net", None)
                return self.send_json({"days": days_out})
            if path == "/api/outside-stock":
                return self.send_json(outside_stock(con))
            if path == "/api/ownstock":
                # v3: Own Maal page — everything derived from the existing
                # own_stock() / warehouse() aggregates plus own-trade sums.
                os_ = own_stock(con)
                wh2 = warehouse(con)
                pur_t = con.execute("SELECT COALESCE(SUM(amount),0) s FROM purchases").fetchone()["s"]
                sal_t = con.execute("SELECT COALESCE(SUM(amount),0) s FROM sales").fetchone()["s"]
                # Own-dispatch sales ride on the OUT trip row (no sales
                # row): count them in the Own page totals exactly once.
                sal_t += con.execute("SELECT COALESCE(SUM(net_kg/1000.0*sale_rate),0) s FROM trips "
                                     "WHERE direction='OUT' AND sale_buyer_id IS NOT NULL "
                                     "AND sale_rate>0").fetchone()["s"]
                recv = pay = 0.0
                for p in con.execute("SELECT id FROM parties"):
                    ps = con.execute("SELECT COALESCE(SUM(amount),0) s FROM purchases WHERE party_id=?",
                                     (p["id"],)).fetchone()["s"]
                    ss = con.execute("SELECT COALESCE(SUM(amount),0) s FROM sales WHERE party_id=?",
                                     (p["id"],)).fetchone()["s"]
                    ss += con.execute("SELECT COALESCE(SUM(net_kg/1000.0*sale_rate),0) s FROM trips "
                                      "WHERE direction='OUT' AND sale_buyer_id=? AND sale_rate>0",
                                      (p["id"],)).fetchone()["s"]
                    bal = ss - ps          # + = party owes us for own trade
                    if bal > 0: recv += bal
                    else: pay += -bal
                return self.send_json({
                    "rock_bought_t": os_["rock_bought_t"], "ground_t": os_["ground_t"],
                    "rock_left_t": os_["rock_left_t"],
                    "powder_bought_t": os_["powder_bought_t"],
                    "rock_sold_t": os_["rock_sold_t"],
                    "outside_sent_t": os_["outside_sent_t"],
                    "outside_received_t": os_["outside_received_t"],
                    "filter_bags": os_["filter_bags"],
                    "filter_kg": os_["filter_kg"], "filter_t": os_["filter_t"],
                    "powder_made_t": os_["powder_made_t"], "sold_t": os_["sold_t"],
                    "dispatched_t": os_["dispatched_t"],
                    "powder_left_t": os_["powder_left_t"],
                    "bags_made": wh2["own"]["bags_made"], "bags_sold": wh2["own"]["bags_sold"],
                    "bags_dispatched": wh2["own"]["bags_dispatched"],
                    "bags_bought": wh2["own"]["bags_bought"],
                    "bags_outside": wh2["own"]["bags_outside"],
                    "bags_ready": wh2["own"]["bags_ready"],
                    "purchases_total": pur_t, "sales_total": sal_t,
                    "trade_receivable": round(recv, 2), "trade_payable": round(pay, 2),
                })
            if path == "/api/trade-history":
                return self.send_json({"rows": trade_history(con)})
            if path == "/api/costperton":
                import datetime as _dt3
                td = _dt3.date.today()
                d_from = (q.get("from", [""])[0] or td.replace(day=1).isoformat())
                d_to = (q.get("to", [""])[0] or td.isoformat())
                return self.send_json(cost_per_ton(con, d_from, d_to))
            if path == "/api/party-business":
                return self.send_json({"rows": party_business(con)})
            if path == "/api/phosphate-detail":
                ds = q.get("date", [today()])[0] or today()
                return self.send_json(phosphate_detail(con, ds))
            if path in ("/api/machines", "/api/machine-entries"):
                ms = [dict(r) for r in con.execute("SELECT * FROM machines ORDER BY name")]
                es = [dict(r) for r in con.execute(
                    "SELECT me.*, m.name machine_name FROM machine_entries me "
                    "LEFT JOIN machines m ON m.id=me.machine_id ORDER BY me.id DESC LIMIT 200")]
                return self.send_json({"machines": ms, "entries": es})
            if path == "/api/godam":
                counts = [dict(r) for r in con.execute(
                    "SELECT gc.*, p.name party_name FROM godam_counts gc "
                    "LEFT JOIN parties p ON p.id=gc.party_id ORDER BY gc.id DESC LIMIT 100")]
                adjs = [dict(r) for r in con.execute(
                    "SELECT ba.*, p.name party_name FROM bag_adjustments ba "
                    "LEFT JOIN parties p ON p.id=ba.party_id ORDER BY ba.id DESC LIMIT 100")]
                return self.send_json({"counts": counts, "adjustments": adjs})
            if path == "/api/parties":
                _amap = _party_avatar_map(con)
                rows = []
                for p in con.execute("SELECT * FROM parties ORDER BY name"):
                    _, bal = party_ledger(con, p["id"])
                    rows.append({**dict(p), "balance": bal, "stock": party_stock(con, p["id"]),
                                 **_amap.get(p["id"], {"cuid": None, "cavatar": False, "caver": 0})})
                return self.send_json(rows)
            if path.startswith("/api/parties/") and path.endswith("/last-rates"):
                try:
                    pid = int(path.split("/")[3])
                except ValueError:
                    return self.send_json({"error": "bad party id"}, 404)
                jobs = [dict(r) for r in con.execute(
                    "SELECT date,tons,rate_per_ton,grade_pct FROM grinding_jobs WHERE party_id=? ORDER BY id DESC LIMIT 3", (pid,))]
                purs = [dict(r) for r in con.execute(
                    "SELECT date,tons,rate_per_ton,grade_pct,deduction_pct FROM purchases WHERE party_id=? ORDER BY id DESC LIMIT 3", (pid,))]
                return self.send_json({"jobs": jobs, "purchases": purs})
            if path.startswith("/api/parties/"):
                try:
                    pid = int(path.split("/")[3])
                except ValueError:
                    return self.send_json({"error": "bad party id"}, 404)
                p = con.execute("SELECT * FROM parties WHERE id=?", (pid,)).fetchone()
                if not p: return self.send_json({"error": "not found"}, 404)
                entries, bal = party_ledger(con, pid)
                _pd = dict(p)
                _pd.update(_party_avatar_map(con).get(pid,
                           {"cuid": None, "cavatar": False, "caver": 0}))
                atts = [dict(r) for r in con.execute(
                    "SELECT id,table_name,record_id,filename,mime,size,created FROM attachments "
                    "WHERE (table_name='parties' AND record_id=?) OR (table_name IN "
                    "('trips','grinding_jobs','purchases','sales','payments') AND record_id IN "
                    "(SELECT id FROM payments WHERE party_id=?)) ORDER BY id DESC", (pid, pid))]
                return self.send_json({"party": _pd, "entries": entries,
                                       "balance": bal, "stock": party_stock(con, pid),
                                       "attachments": atts})
            if path == "/api/tare":
                veh = (q.get("vehicle", [""])[0]).strip()
                r = con.execute("SELECT tare_kg FROM vehicle_tares WHERE vehicle_no=?", (veh,)).fetchone()
                return self.send_json({"tare_kg": r["tare_kg"] if r else None})
            if path == "/api/last-trip":
                veh = (q.get("vehicle", [""])[0]).strip()
                r = con.execute("SELECT * FROM trips WHERE vehicle_no=? ORDER BY id DESC LIMIT 1", (veh,)).fetchone()
                return self.send_json(dict(r) if r else {})
            simple = {"/api/trips": "trips", "/api/jobs": "grinding_jobs",
                      "/api/purchases": "purchases", "/api/sales": "sales",
                      "/api/production": "production", "/api/workers": "workers",
                      "/api/payouts": "worker_payouts", "/api/payments": "payments",
                      "/api/expenses": "expenses", "/api/attendance": "attendance",
                      "/api/departments": "departments", "/api/heads": "expense_heads",
                      "/api/cheques": "cheques", "/api/orders": "orders",
                      "/api/maintenance": "maintenance", "/api/stock-counts": "stock_counts",
                      "/api/day-costs": "day_costs", "/api/bag-moves": "bag_movements",
                      "/api/client-bags": "client_bags", "/api/leaves": "leaves",
                      "/api/outside-grinding": "outside_grinding",
                      "/api/approvals": "approvals", "/api/devices": "biometric_devices",
                      "/api/punches": "device_punches", "/api/alerts": "alerts",
                      "/api/proofs": "payment_proofs", "/api/grind-sessions": "grind_sessions"}
            if path in simple:
                tbl = simple[path]
                order = "id DESC"
                rows = [dict(r) for r in con.execute(
                    "SELECT * FROM %s ORDER BY %s LIMIT 800" % (tbl, order))]
                if path == "/api/workers":
                    for r in rows:
                        r.update(worker_dues(con, r["id"]))
                        d = con.execute("SELECT name FROM departments WHERE id=?",
                                        (r.get("department_id") or 0,)).fetchone()
                        r["department_name"] = d["name"] if d else ""
                if path in ("/api/trips", "/api/purchases", "/api/sales", "/api/jobs",
                            "/api/payments", "/api/production", "/api/client-bags",
                            "/api/cheques", "/api/orders", "/api/proofs",
                            "/api/outside-grinding"):
                    for r in rows:
                        r["party_name"] = names.get(r.get("party_id"), "Own / Apna" if r.get("party_id") is None else "?")
                if path == "/api/proofs":
                    # who submitted: the party's client login + its picture
                    _amap = _party_avatar_map(con)
                    for r in rows:
                        r.update(_amap.get(r.get("party_id"),
                                 {"cuid": None, "cavatar": False, "caver": 0}))
                if path == "/api/outside-grinding":
                    _paymap = {pp["og_bill_id"]: pp for pp in con.execute(
                        "SELECT * FROM payments WHERE og_bill_id IS NOT NULL")}
                    for r in rows:
                        r["from_name"] = names.get(r.get("from_party_id"), "")
                        _bp = _paymap.get(r.get("id"))
                        r["paid_now"] = float(_bp["amount"]) if _bp else 0
                        r["pay_method"] = _bp["method"] if _bp else ""
                if path == "/api/sales":
                    for r in rows:
                        if (r.get("source") or "") == "outside":
                            r["factory_name"] = names.get(r.get("og_factory_id"), "")
                if path == "/api/trips":
                    _sales_by_trip = {}
                    for _sr in con.execute("SELECT trip_id, id, rate_per_ton, amount, "
                                           "invoice_no FROM sales WHERE trip_id IS NOT NULL"):
                        _sales_by_trip[_sr["trip_id"]] = _sr
                    for r in rows:
                        r["buy_from_name"] = names.get(r.get("buy_from_party_id"), "")
                        # the trip's OWN recorded sale (Own dispatch,
                        # 28 Oct 2026) rides under its own keys: the
                        # legacy sale_* keys below keep meaning the
                        # round-9 linked sale row, exactly as before
                        r["own_sale_buyer_id"] = r.get("sale_buyer_id")
                        r["own_sale_buyer_name"] = (names.get(r.get("sale_buyer_id"), "")
                                                    if r.get("sale_buyer_id") else "")
                        r["own_sale_rate"] = float(r.get("sale_rate") or 0)
                        _ls = _sales_by_trip.get(r["id"])
                        r["sale_id"] = _ls["id"] if _ls else None
                        r["sale_rate"] = float(_ls["rate_per_ton"]) if _ls else 0
                        r["sale_amount"] = float(_ls["amount"]) if _ls else 0
                        r["sale_invoice"] = _ls["invoice_no"] if _ls else ""
                if path == "/api/payments":
                    # cheque details ride along so the owner Edit form can
                    # prefill them (cheques live in their own register)
                    for r in rows:
                        cq = con.execute("SELECT cheque_no,due_date FROM cheques "
                                         "WHERE payment_id=?", (r["id"],)).fetchone()
                        r["cheque_no"] = cq["cheque_no"] if cq else ""
                        r["due_date"] = cq["due_date"] if cq else ""
                if path == "/api/payouts" or path == "/api/attendance" or path == "/api/leaves":
                    wnames = {w["id"]: w["name"] for w in con.execute("SELECT id,name FROM workers")}
                    for r in rows:
                        r["worker_name"] = wnames.get(r.get("worker_id"), "?")
                if path == "/api/orders":
                    for r in rows:
                        r.update(order_progress(con, r))
                if path == "/api/expenses":
                    heads = {h["id"]: h["name"] for h in con.execute("SELECT id,name FROM expense_heads")}
                    for r in rows:
                        r["head_name"] = heads.get(r.get("head_id"), r.get("category") or "")
                        r["sub_name"] = heads.get(r.get("sub_head_id"), "")
                return self.send_json(rows)
            if path == "/api/warehouse":
                return self.send_json(warehouse(con))
            if path == "/api/cashbook":
                return self.send_json(cashbook(con, q.get("date", [today()])[0]))
            if path == "/api/bankbook":
                return self.send_json(bank_book(con))
            if path == "/api/holder-users":
                return self.send_json([{"id": r["id"], "username": r["username"],
                                        "role": r["role"]}
                                       for r in con.execute(
                                           "SELECT id, username, role FROM users "
                                           "WHERE role IN ('manager','staff') ORDER BY username")])
            if path == "/api/cash-hand":
                holders = holder_summaries(con)
                rules = cash_rules(con)
                if u["role"] == "owner":
                    pend = []
                    heads = {h["id"]: h["name"] for h in con.execute("SELECT id,name FROM expense_heads")}
                    for r in con.execute("SELECT * FROM expenses WHERE status='pending' ORDER BY date, id"):
                        e = dict(r)
                        e["head_name"] = heads.get(e.get("head_id"), e.get("category") or "")
                        pend.append(e)
                    users = [{"id": r["id"], "username": r["username"], "role": r["role"]}
                             for r in con.execute(
                                 "SELECT id, username, role FROM users "
                                 "WHERE role IN ('manager','staff') ORDER BY username")]
                    return self.send_json({"holders": holders, "users": users,
                                           "rules": rules, "pending_expenses": pend,
                                           "own_only": False})
                mine = [h for h in holders if h["key"] == "user:%d" % u["id"]]
                return self.send_json({"holders": mine, "users": [], "rules": rules,
                                       "pending_expenses": [], "own_only": True})
            if path == "/api/dayend":
                _ds = q.get("date", [today()])[0]
                _de = day_end(con, _ds)
                if _ds == today():
                    # round 12: the owner's Day-End email (toggle,
                    # default off) fires from the summary being viewed
                    maybe_email_dayend(con, _de)
                return self.send_json(_de)
            if path == "/api/shift-alert":
                # round 11: ONE check for both daily alert families
                # (shift production + vehicle movement); eligibility
                # and dismissals are resolved inside daily_alerts()
                return self.send_json(daily_alerts(con, u))
            if path == "/api/factory-status":
                return self.send_json(factory_status(con))
            if path == "/api/shift-closures":
                # factory-closed records: ?date= for one day, else the
                # last 14 days (the Grinding & Production page strip)
                import datetime as _dt
                _qd = (q.get("date", [""])[0] or "").strip()
                if _qd:
                    rows = shift_closures_for(con, _qd)
                else:
                    _since = (_dt.date.today()
                              - _dt.timedelta(days=14)).isoformat()
                    rows = [dict(r) for r in con.execute(
                        "SELECT date, shift, reason, note, by_user, created "
                        "FROM shift_closures WHERE date>=? "
                        "ORDER BY date DESC, id DESC", (_since,))]
                return self.send_json(rows)
            if path == "/api/pnl":
                month = q.get("month", [today()[:7]])[0]
                return self.send_json(pnl(con, month))
            if path == "/api/expense-report":
                month = q.get("month", [today()[:7]])[0]
                heads = {}
                for h in con.execute("SELECT * FROM expense_heads"):
                    heads[h["id"]] = dict(h)
                agg = {}
                for r in con.execute("SELECT head_id, sub_head_id, COALESCE(SUM(amount),0) s FROM expenses "
                                     "WHERE date LIKE ? AND status!='rejected' GROUP BY head_id, sub_head_id", (month + "%",)):
                    hn = heads.get(r["head_id"], {}).get("name") if r["head_id"] else None
                    sn = heads.get(r["sub_head_id"], {}).get("name") if r["sub_head_id"] else None
                    agg.setdefault(hn or "Other", {})[sn or "-"] = r["s"]
                payto = [dict(r) for r in con.execute(
                    "SELECT paid_to, COALESCE(SUM(amount),0) total, COUNT(*) n FROM expenses "
                    "WHERE date LIKE ? AND status!='rejected' AND paid_to!='' GROUP BY paid_to ORDER BY total DESC", (month + "%",))]
                return self.send_json({"month": month, "by_head": agg, "by_paid_to": payto})
            if path == "/api/notifications":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                return self.send_json([dict(r) for r in con.execute(
                    "SELECT * FROM notifications ORDER BY id DESC LIMIT 200")])
            if path == "/api/recycle":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                return self.send_json([dict(r) for r in con.execute(
                    "SELECT * FROM recycle ORDER BY id DESC LIMIT 200")])
            if path == "/api/audit":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                return self.send_json([dict(r) for r in con.execute(
                    "SELECT * FROM audit_log ORDER BY id DESC LIMIT 300")])
            if path == "/api/attachments":
                tbl = q.get("table", [""])[0]
                rec = int(q.get("record", [0])[0])
                return self.send_json([dict(r) for r in con.execute(
                    "SELECT id,table_name,record_id,filename,mime,size,created,uploaded_by "
                    "FROM attachments WHERE table_name=? AND record_id=? ORDER BY id DESC", (tbl, rec))])
            if path == "/api/assistant":
                return self.send_json(assistant_answer(con, q.get("q", [""])[0], u))
            if path == "/api/search":
                term = "%" + (q.get("q", [""])[0]).strip() + "%"
                res = {"parties": [], "trips": [], "workers": [], "payments": [],
                       "expenses": []}
                if term != "%%":
                    if perm_ok(u, "parties"):
                        res["parties"] = [dict(r) for r in con.execute(
                            "SELECT id,name,roles FROM parties WHERE name LIKE ? LIMIT 10", (term,))]
                    if perm_ok(u, "vehicles"):
                        res["trips"] = [dict(r) for r in con.execute(
                            "SELECT id,date,direction,vehicle_no,driver,net_kg FROM trips WHERE vehicle_no LIKE ? OR driver LIKE ? LIMIT 10",
                            (term, term))]
                    if perm_ok(u, "workers"):
                        res["workers"] = [dict(r) for r in con.execute(
                            "SELECT id,name,kind FROM workers WHERE name LIKE ? LIMIT 10", (term,))]
                    if perm_ok(u, "payments"):
                        res["payments"] = [dict(r) for r in con.execute(
                            "SELECT id,date,direction,amount,note FROM payments WHERE note LIKE ? LIMIT 10", (term,))]
                    if perm_ok(u, "expenses"):
                        res["expenses"] = [dict(r) for r in con.execute(
                            "SELECT e.id,e.date,e.amount,e.paid_to,e.note,"
                            "COALESCE(h.name,'') head_name FROM expenses e "
                            "LEFT JOIN expense_heads h ON h.id=e.head_id "
                            "WHERE e.note LIKE ? OR e.paid_to LIKE ? LIMIT 10",
                            (term, term))]
                return self.send_json(res)
            if path == "/api/users":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                rows = []
                for r in con.execute("SELECT id,username,role,party_id,email,display_name,phone,"
                                      "CASE WHEN avatar_b64<>'' THEN 1 ELSE 0 END has_avatar,avatar_ver,"
                                      "lang,theme,unit,perms "
                                      "FROM users ORDER BY role,username"):
                    d0 = dict(r)
                    d0["perms"] = parse_perms(d0.get("perms"))
                    d0["has_avatar"] = bool(d0.get("has_avatar"))
                    rows.append(d0)
                return self.send_json(rows)
            if path == "/api/events":
                return self.send_json(recent_events(con, (q.get("since") or [""])[0]))
            if path.startswith("/api/wa-statement/"):
                try:
                    pid = int(path.rsplit("/", 1)[1])
                except ValueError:
                    return self.send_json({"error": "bad party id"}, 404)
                lang = (q.get("lang") or ["en"])[0]
                unit = (q.get("u") or ["t"])[0]
                trip = None
                tv = (q.get("trip") or [""])[0]
                if tv:
                    tr = con.execute("SELECT net_kg FROM trips WHERE id=?", (int(tv),)).fetchone()
                    if tr:
                        trip = {"net_t": tr["net_kg"] / 1000.0}
                r = wa_compose(con, pid, lang, unit, trip)
                if not r:
                    return self.send_json({"error": "party not found"}, 404)
                prow = con.execute("SELECT whatsapp,phone FROM parties WHERE id=?",
                                   (pid,)).fetchone()
                r["phone"] = (prow["whatsapp"] or prow["phone"] or "") if prow else ""
                return self.send_json(r)
            if path == "/api/settings":
                cfg = load_config()
                st = {"db_path": cfg.get("db_path"), "backup_dir": cfg.get("backup_dir"),
                      "device_port": MAIN_PORT[0] + DEVICE_PORT_OFFSET, "lan_ip": lan_ip(),
                      "mill_name": meta_get(con, "mill_name", APP_NAME),
                      "mill_phone": meta_get(con, "mill_phone"),
                      "mill_address": meta_get(con, "mill_address"),
                      "theme_color": meta_get(con, "theme_color", "green") or "green",
                      "has_logo": bool(meta_get(con, "mill_logo_b64")),
                      "logo_ver": int(meta_get(con, "mill_logo_ver", "0") or 0),
                      "owner_whatsapp": meta_get(con, "owner_whatsapp", cfg.get("owner_whatsapp", "")),
                      "wa_phone_id": meta_get(con, "wa_phone_id"),
                      "wa_token_set": bool(meta_get(con, "wa_token")),
                      "wa_token_hint": ("••••" + meta_get(con, "wa_token")[-4:]) if meta_get(con, "wa_token") else "",
                      "sms_url": meta_get(con, "sms_url"),
                      "sms_key_set": bool(meta_get(con, "sms_key")),
                      "sms_sender": meta_get(con, "sms_sender"),
                      "templates": WA_TEMPLATES,
                      "last_backup": meta_get(con, "last_backup", ""),
                      "cash_holder_limit": cash_rules(con)["holder_limit"],
                      "cash_approval_limit": cash_rules(con)["approval_limit"],
                      "powder_age_days": int(meta_get(con, "powder_age_days", "3") or 3),
                      **shift_end_settings(con),
                      "wastage_pct": wastage_pct(con),
                      "bag_kg": bag_kg(con),
                      **bag_weights(con),
                      **font_settings(con),
                      **voice_settings(con),
                      "bank_opening": json.loads(meta_get(con, "bank_opening", "{}") or "{}"),
                      "banks": json.loads(meta_get(con, "banks", "[]") or "[]"),
                      **mail_public_settings(con)}
                return self.send_json(st)
            if path == "/api/backups":
                cfg = load_config()
                bdir = cfg.get("backup_dir") or ""
                files = []
                if bdir and os.path.isdir(bdir):
                    files = sorted([f for f in os.listdir(bdir) if f.endswith(".zip")], reverse=True)
                return self.send_json({"backup_dir": bdir, "files": files,
                                       "backup_days": days_since_backup(con)})
            if path.startswith("/api/export/"):
                name = path.split("/")[3].replace(".csv", "")
                if name not in TABLES:
                    return self.send_json({"error": "unknown table"}, 400)
                body = table_csv(con, name).encode("utf-8-sig")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=%s.csv" % name)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return self.wfile.write(body)
            return self.send_json({"error": "unknown endpoint"}, 404)
        finally:
            con.close()

    # -- POST api (writes)
    def api_profile_post(self, path, d, u):
        # round 12: SELF-SERVICE profile writes — dispatched from
        # the api_post preamble (before the client gate) because a
        # login edits ONLY its own record, whatever its role.
        con = get_db()
        try:
                # round 12: SELF-SERVICE profile — a login edits ONLY its
                # own record. Username / role / perms / status / party
                # link stay owner-only: posting them is rejected outright.
                if any(k in d for k in ("username", "role", "perms", "permissions",
                                        "status", "active", "party_id", "user_id")):
                    return self.send_json({"error": "username, role, permission aur party link sirf owner badal sakta hai"}, 400)
                me = con.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
                if not me:
                    return self.send_json({"error": "login not found"}, 404)
                if path == "/api/profile/avatar":
                    if d.get("avatar_remove"):
                        con.execute("UPDATE users SET avatar_b64='', avatar_mime='', avatar_ver=avatar_ver+1 WHERE id=?",
                                    (u["id"],))
                        audit(con, u["username"], "profile_avatar", "profile picture removed")
                        con.commit()
                        _refresh_session_user(con, u["id"])
                        return self.send_json({"ok": True, "has_avatar": False})
                    mime = str(d.get("avatar_mime") or "").lower()
                    if mime not in ("image/png", "image/jpeg", "image/webp"):
                        return self.send_json({"error": "tasveer PNG / JPG / WebP hi ho sakti hai"}, 400)
                    b64 = str(d.get("avatar_data") or "").strip()
                    try:
                        raw = base64.b64decode(b64, validate=True)
                    except Exception:
                        return self.send_json({"error": "tasveer ka data kharab hai"}, 400)
                    if not raw or len(raw) > 2 * 1024 * 1024:
                        return self.send_json({"error": "tasveer zyada bari hai (max 2 MB) — chhoti tasveer chunein"}, 400)
                    con.execute("UPDATE users SET avatar_b64=?, avatar_mime=?, avatar_ver=avatar_ver+1 WHERE id=?",
                                (b64, mime, u["id"]))
                    audit(con, u["username"], "profile_avatar", "profile picture updated")
                    con.commit()
                    _refresh_session_user(con, u["id"])
                    return self.send_json({"ok": True, "has_avatar": True})
                if path == "/api/profile/password":
                    if not check_pw(str(d.get("current_password") or ""), me["salt"], me["pass_hash"]):
                        return self.send_json({"error": "current (maujooda) password ghalat hai"}, 400)
                    newpw = str(d.get("new_password") or "")
                    if not newpw:
                        return self.send_json({"error": "naya password likhein"}, 400)
                    salt, h = hash_pw(newpw)
                    con.execute("UPDATE users SET salt=?, pass_hash=?, fail_count=0, locked_until=0 WHERE id=?",
                                (salt, h, u["id"]))
                    con.execute("UPDATE password_resets SET used=2 WHERE user_id=? AND used=0",
                                (u["id"],))
                    audit(con, u["username"], "profile_password", "own password changed")
                    con.commit()
                    # other sessions sign out; THIS session stays
                    _my_tok = ""
                    for _part in (self.headers.get("Cookie") or "").split(";"):
                        _part = _part.strip()
                        if _part.startswith("mill_session="):
                            _my_tok = _part.split("=", 1)[1]
                    for _tok in [t for t, s in SESSIONS.items()
                                 if s.get("id") == u["id"] and t != _my_tok]:
                        SESSIONS.pop(_tok, None)
                    return self.send_json({"ok": True})
                # ---- /api/profile: display name / phone / email
                new_name = str(d.get("display_name") if d.get("display_name") is not None
                               else (me["display_name"] or "")).strip()
                new_phone = str(d.get("phone") if d.get("phone") is not None
                                else (me["phone"] or "")).strip()
                new_email = str(d.get("email") if d.get("email") is not None
                                else (me["email"] or "")).strip()
                _ee = _user_email_error(con, new_email, exclude_id=u["id"])
                if _ee:
                    return self.send_json({"error": _ee}, 400)
                changed = []
                if new_name != (me["display_name"] or ""):
                    changed.append("name: %s -> %s" % (me["display_name"] or "-", new_name or "-"))
                if new_phone != (me["phone"] or ""):
                    changed.append("phone: %s -> %s" % (me["phone"] or "-", new_phone or "-"))
                if new_email != (me["email"] or ""):
                    changed.append("email: %s -> %s" % (me["email"] or "-", new_email or "-"))
                con.execute("UPDATE users SET display_name=?, phone=?, email=? WHERE id=?",
                            (new_name, new_phone, new_email, u["id"]))
                if changed:
                    audit(con, u["username"], "profile_update", "; ".join(changed))
                party_synced = False
                if me["role"] == "client" and me["party_id"]:
                    # the client's own save WINS on the linked party's
                    # email / WhatsApp, so statements keep reaching them
                    pr = con.execute("SELECT name, email, whatsapp, phone FROM parties WHERE id=?",
                                     (me["party_id"],)).fetchone()
                    if pr and ((pr["email"] or "") != new_email
                               or (pr["whatsapp"] or "") != new_phone):
                        con.execute("UPDATE parties SET email=?, whatsapp=? WHERE id=?",
                                    (new_email, new_phone, me["party_id"]))
                        if not (pr["phone"] or "") and new_phone:
                            con.execute("UPDATE parties SET phone=? WHERE id=?",
                                        (new_phone, me["party_id"]))
                        audit(con, u["username"], "profile_party_sync",
                              "party #%s email/whatsapp user ki profile se barabar: email %s -> %s, whatsapp %s -> %s"
                              % (me["party_id"], pr["email"] or "-", new_email or "-",
                                 pr["whatsapp"] or "-", new_phone or "-"))
                        party_synced = True
                    contact_changed = [c for c in changed if c.startswith(("phone:", "email:"))]
                    if contact_changed:
                        notify_owner(con, "client_profile",
                                     "Client %s (%s) updated their contact: %s"
                                     % (pr["name"] if pr else u["username"], u["username"],
                                        "; ".join(contact_changed)))
                con.commit()
                _refresh_session_user(con, u["id"])
                return self.send_json({"ok": True, "party_synced": party_synced,
                                       "display_name": new_name, "phone": new_phone,
                                       "email": new_email})
        finally:
            con.close()

    def api_post(self, path):
        if IS_PC and path.startswith("/api/my/"):
            return self.send_text("Not found", code=404)
        d = self.body_json()
        # endpoints any logged-in user may use
        if path == "/api/prefs":
            u = self.need_login()
            if not u: return
            if u["role"] == "demo":
                # even per-login preferences are a server write —
                # the UI keeps them locally for the session instead
                return self.send_json({"error": DEMO_MSG}, 403)
            con = get_db()
            try:
                for key, col in (("lang", "lang"), ("theme", "theme"), ("unit", "unit")):
                    if d.get(key):
                        con.execute("UPDATE users SET %s=? WHERE id=?" % col, (d[key], u["id"]))
                        u[col] = d[key]
                con.commit()
            finally:
                con.close()
            return self.send_json({"ok": True})
        if path in ("/api/profile", "/api/profile/password", "/api/profile/avatar"):
            # round 12: self-service profile — any logged-in role may
            # edit ONLY its own record (handled in api_profile_post);
            # demo stays read-only like everywhere else
            u = self.need_login()
            if not u: return
            if u["role"] == "demo":
                return self.send_json({"error": DEMO_MSG}, 403)
            return self.api_profile_post(path, d, u)
        if path == "/api/proofs" and self.user() and self.user()["role"] == "client":
            u = self.user()
            con = get_db()
            try:
                amount = float(d.get("amount") or 0)
                cur = con.execute(
                    "INSERT INTO payment_proofs(party_id,date,amount,attachment_id,note)"
                    " VALUES(?,?,?,?,?)",
                    (u["party_id"], d.get("date") or today(), amount,
                     d.get("attachment_id") or None, d.get("note", "")))
                audit(con, u["username"], "proof_upload", "party %s Rs %s" % (u["party_id"], d.get("amount")))
                # owner ko bell + Notifications par khabar — client ki
                # proof pending parhi rehti thi, koi alert nahi banta tha
                prow = con.execute("SELECT name FROM parties WHERE id=?",
                                   (u["party_id"],)).fetchone()
                notify_owner(con, "payment_proof",
                             "Client payment proof: %s ne Rs %s ki payment proof bheji hai"
                             " — Alerts page par confirm karein."
                             % ((prow["name"] if prow else "Client"),
                                "{:,.0f}".format(amount)))
                con.commit()
                # round 12: the bell's email twin — the owner also
                # gets the proof by email (toggle mail_ev_proof)
                email_proof_to_owner(con, u["party_id"], amount,
                                     d.get("date") or today())
                return self.send_json({"ok": True, "id": cur.lastrowid})
            finally:
                con.close()
        if path == "/api/attachments" and self.user() and self.user()["role"] == "client":
            u = self.user()
            return self._save_attachment(d, u)
        u = self.need_login()
        if not u: return
        if u["role"] == "demo":
            # public view-only login: NO writes of any kind — no
            # entries, settings saves, uploads, decisions, restores
            # or user changes. Login/logout are handled in do_POST
            # and never reach this function; the AI Assistant is a
            # GET endpoint (provably write-free) and keeps working.
            return self.send_json({"error": DEMO_MSG}, 403)
        if u["role"] == "client":
            return self.send_json({"error": "not allowed for this login"}, 403)
        if not perm_ok(u, _post_perm(path, d)):
            return self.send_json({"error": "not allowed for this login"}, 403)
        # OWNER-ONLY EDIT/DELETE: the module permission above governs
        # CREATING entries; touching a stored one (edit or delete, any
        # module) is the owner's alone — enforced here, server-side,
        # so hidden buttons are never the only barrier.
        if u["role"] != "owner" and _entry_mutation(path, d):
            return self.send_json({"error": OWNER_EDIT_MSG}, 403)
        _miss = _validate_payload(path, d)
        if _miss:
            return self.send_json({"error": "Missing: " + ", ".join(_miss),
                                   "missing": _miss}, 400)
        con = get_db()
        try:
            # OWNER EDITS: a create-endpoint call carrying an existing
            # record id is an EDIT (owner-gated above) — route it to the
            # matching update function before the create handlers run.
            # Create paths with no edit route refuse the id outright,
            # so an edit can never silently insert a duplicate.
            if d.get("id") and path in _CREATE_PATHS:
                _upd = _EDIT_ROUTES.get(path)
                if _upd is None:
                    return self.send_json(
                        {"error": "is entry ki edit yahan se nahi hoti"}, 400)
                try:
                    return self.send_json(_upd(con, d, u))
                except StockConfirmRequired as e:
                    # powder-stock check: nothing was saved — the UI
                    # asks "phir bhi save karein?" and only a save
                    # carrying the confirm flag proceeds
                    return self.send_json(e.payload(), 409)
                except DuplicateSaleConfirmRequired as e:
                    # duplicate-sale guard: same contract — nothing
                    # saved until the re-post confirms it is separate
                    return self.send_json(e.payload(), 409)
                except LookupError as e:
                    return self.send_json({"error": str(e)}, 404)
                except ValueError as e:
                    return self.send_json({"error": str(e)}, 400)
            if path == "/api/parties":
                return self.send_json(create_party(con, d, u))
            if path == "/api/trips":
                try:
                    return self.send_json(create_trip(con, d, u))
                except StockConfirmRequired as e:
                    return self.send_json(e.payload(), 409)
                except DuplicateSaleConfirmRequired as e:
                    return self.send_json(e.payload(), 409)
            if path == "/api/jobs":
                return self.send_json(create_job(con, d, u))
            if path == "/api/grind/start":
                cur = con.execute("INSERT INTO grind_sessions(party_id,started,note) VALUES(?,?,?)",
                                  (d.get("party_id") or None, now_str(), d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/grind/stop":
                con.execute("UPDATE grind_sessions SET ended=? WHERE id=?",
                            (now_str(), int(d["id"])))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/purchases":
                return self.send_json(create_purchase(con, d, u))
            if path == "/api/sales":
                try:
                    return self.send_json(create_sale(con, d, u))
                except DuplicateSaleConfirmRequired as e:
                    return self.send_json(e.payload(), 409)
            if path == "/api/outside-grinding":
                return self.send_json(create_outside(con, d, u))
            if path == "/api/direct-deals":
                return self.send_json(create_direct_deal(con, d, u))
            if path == "/api/direct-deals/delete":
                # the deal is ONE unit: both legs are recycled + removed
                try:
                    pr, sr = _deal_legs(con, d.get("deal_id") or d.get("id"))
                except LookupError as e:
                    return self.send_json({"error": str(e)}, 404)
                for _tbl, _row in (("purchases", pr), ("sales", sr)):
                    _rd = {k: _row[k] for k in _row.keys()}
                    con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                                " VALUES(?,?,?,?,?)", (now_str(), _tbl, _row["id"],
                                                      json.dumps(_rd), u["username"]))
                    con.execute("DELETE FROM %s WHERE id=?" % _tbl, (_row["id"],))
                audit(con, u["username"], "delete", "direct deal %s" % (pr["deal_id"],))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/orders":
                return self.send_json(create_order(con, d, u))
            if path == "/api/orders/close":
                con.execute("UPDATE orders SET status='closed' WHERE id=?", (int(d["id"]),))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/production":
                return self.send_json(create_production(con, d, u))
            if path == "/api/shift-alert/dismiss":
                # round 11: "Later" / acknowledge for either alert
                # family — one dismissal row per (user, kind, date,
                # shift); the alert never re-pops for that user.
                _kind = d.get("kind")
                if _kind not in ("shift", "vehicle_in", "vehicle_out"):
                    return self.send_json({"error": "alert kind ghalat hai"}, 400)
                _dstr = (d.get("date") or today()).strip()
                _shift = d.get("shift") if d.get("shift") in ("Day", "Night") else ""
                if _kind == "shift":
                    if u["role"] not in ("manager", "staff"):
                        return self.send_json({"error": "not allowed for this login"}, 403)
                    if not _shift:
                        return self.send_json({"error": "shift ghalat hai"}, 400)
                else:
                    if u["role"] not in ("owner", "manager", "staff"):
                        return self.send_json({"error": "not allowed for this login"}, 403)
                    _shift = ""
                con.execute(
                    "INSERT OR IGNORE INTO alert_dismissals(username,kind,date,shift,created)"
                    " VALUES(?,?,?,?,?)",
                    (u["username"], _kind, _dstr, _shift, now_str()))
                audit(con, u["username"], "alert_dismiss",
                      "%s %s %s" % (_kind, _dstr, _shift))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/shift-closures":
                # round 11: "Factory Closed" — recording WHY a shift
                # has no production clears that shift's alert for
                # everyone, permanently (the row itself is the record
                # shown on the Grinding page and in Day-End).
                if u["role"] not in ("owner", "manager", "staff"):
                    return self.send_json({"error": "not allowed for this login"}, 403)
                _dstr = (d.get("date") or today()).strip()
                _shift = d.get("shift")
                _reason = d.get("reason")
                if _shift not in ("Day", "Night"):
                    return self.send_json({"error": "shift ghalat hai"}, 400)
                if _reason not in ("technical", "power"):
                    return self.send_json({"error": "reason ghalat hai"}, 400)
                _note = str(d.get("note") or "").strip()[:200]
                con.execute(
                    "INSERT INTO shift_closures(date,shift,reason,note,by_user,created)"
                    " VALUES(?,?,?,?,?,?)"
                    " ON CONFLICT(date,shift) DO UPDATE SET "
                    "reason=excluded.reason, note=excluded.note,"
                    " by_user=excluded.by_user, created=excluded.created",
                    (_dstr, _shift, _reason, _note, u["username"], now_str()))
                audit(con, u["username"], "shift_closure",
                      "%s %s %s" % (_dstr, _shift, _reason))
                con.commit()
                return self.send_json({"ok": True,
                                       "closure": shift_closures_for(con, _dstr)})
            if path == "/api/factory-close":
                # round 11: mark the factory Band for whole days.
                # Owner + Manager only (the "om" perm above + this
                # re-check). closed_to, when given, is the expected
                # REOPENING day and must fall after closed_from.
                if u["role"] not in ("owner", "manager"):
                    return self.send_json({"error": "not allowed for this login"}, 403)
                import datetime as _dt
                _from = (d.get("closed_from") or today()).strip()
                _to = (d.get("closed_to") or "").strip() or None
                _reason = d.get("reason")
                _rtext = str(d.get("reason_text") or "").strip()
                if _reason not in FACTORY_REASONS:
                    return self.send_json({"error": "reason ghalat hai"}, 400)
                if _reason == "other" and not _rtext:
                    return self.send_json(
                        {"error": "Other ki wajah likhna zaroori hai"}, 400)
                try:
                    _fd = _dt.date.fromisoformat(_from)
                    if _to and _dt.date.fromisoformat(_to) <= _fd:
                        return self.send_json(
                            {"error": "khulne ki date band hone ki date ke baad honi chahiye"}, 400)
                except ValueError:
                    return self.send_json({"error": "date ghalat hai"}, 400)
                if factory_closed_on(con, _from) or con.execute(
                        "SELECT COUNT(*) c FROM factory_closures "
                        "WHERE closed_to IS NULL").fetchone()["c"]:
                    return self.send_json(
                        {"error": "factory pehle hi band hai"}, 400)
                cur = con.execute(
                    "INSERT INTO factory_closures(closed_from,closed_to,reason,"
                    "reason_text,note,closed_by,created,updated)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (_from, _to, _reason, _rtext[:200],
                     str(d.get("note") or "").strip()[:200],
                     u["username"], now_str(), now_str()))
                audit(con, u["username"], "factory_close",
                      "%s %s" % (_from, _reason))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid,
                                       "factory": factory_status(con)})
            if path == "/api/factory-reopen":
                # one press: the CURRENT period closes with
                # closed_to = today (today is the first open day).
                if u["role"] not in ("owner", "manager"):
                    return self.send_json({"error": "not allowed for this login"}, 403)
                _cur = factory_closed_on(con, today())
                if not _cur:
                    return self.send_json(
                        {"error": "factory band nahi hai"}, 400)
                con.execute(
                    "UPDATE factory_closures SET closed_to=?, reopened_by=?, "
                    "updated=? WHERE id=?",
                    (today(), u["username"], now_str(), _cur["id"]))
                audit(con, u["username"], "factory_reopen",
                      "%s since %s" % (today(), _cur["closed_from"]))
                con.commit()
                return self.send_json({"ok": True,
                                       "factory": factory_status(con)})
            if path == "/api/bag-moves":
                cur = con.execute("INSERT INTO bag_movements(date,direction,bags,note) VALUES(?,?,?,?)",
                                  (d.get("date") or today(), d["direction"], int(d["bags"]), d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/client-bags":
                cur = con.execute("INSERT INTO client_bags(date,party_id,direction,bags,note) VALUES(?,?,?,?,?)",
                                  (d.get("date") or today(), int(d["party_id"]), d["direction"],
                                   int(d["bags"]), d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/departments":
                cur = con.execute(
                    "INSERT INTO departments(name,in_time,out_time,off_days,overtime_allowed,overtime_rate)"
                    " VALUES(?,?,?,?,?,?)",
                    (d["name"].strip(), d.get("in_time") or "08:00", d.get("out_time") or "17:00",
                     ",".join(str(x) for x in (d.get("off_days") or [6])),
                     1 if d.get("overtime_allowed") else 0, float(d.get("overtime_rate") or 0)))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/departments/update":
                con.execute("UPDATE departments SET name=?,in_time=?,out_time=?,off_days=?,"
                            "overtime_allowed=?,overtime_rate=? WHERE id=?",
                            (d["name"].strip(), d.get("in_time") or "08:00", d.get("out_time") or "17:00",
                             ",".join(str(x) for x in (d.get("off_days") or [6])),
                             1 if d.get("overtime_allowed") else 0,
                             float(d.get("overtime_rate") or 0), int(d["id"])))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/workers":
                return self.send_json(create_worker(con, d, u))
            if path == "/api/payouts":
                cur = con.execute(
                    "INSERT INTO worker_payouts(worker_id,date,amount,kind,method,note) VALUES(?,?,?,?,?,?)",
                    (int(d["worker_id"]), d.get("date") or today(), float(d["amount"]),
                     d.get("kind") or "payment", d.get("method") or "cash", d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/attendance":
                wid = int(d["worker_id"]); date_str = d.get("date") or today()
                # the attendance POST is an upsert: saving over an
                # EXISTING day-row is an edit of a stored entry
                if u["role"] != "owner" and con.execute(
                        "SELECT id FROM attendance WHERE worker_id=? AND date=?",
                        (wid, date_str)).fetchone():
                    return self.send_json({"error": OWNER_EDIT_MSG}, 403)
                w = con.execute("SELECT * FROM workers WHERE id=?", (wid,)).fetchone()
                ci, co = d.get("check_in", ""), d.get("check_out", "")
                if d.get("overtime_hours") is not None and d.get("overtime_hours") != "":
                    ot = float(d["overtime_hours"])
                else:
                    ot = compute_overtime(con, w, date_str, ci, co) if w else 0.0
                con.execute("INSERT INTO attendance(worker_id,date,present,check_in,check_out,overtime_hours)"
                            " VALUES(?,?,?,?,?,?) ON CONFLICT(worker_id,date) DO UPDATE SET "
                            "present=excluded.present, check_in=excluded.check_in,"
                            " check_out=excluded.check_out, overtime_hours=excluded.overtime_hours",
                            (wid, date_str, 1 if d.get("present", True) else 0, ci, co, ot))
                con.commit()
                return self.send_json({"ok": True, "overtime_hours": ot})
            if path == "/api/leaves":
                cur = con.execute(
                    "INSERT INTO leaves(worker_id,from_date,to_date,kind,note) VALUES(?,?,?,?,?)",
                    (int(d["worker_id"]), d["from_date"], d["to_date"],
                     d.get("kind") or "unpaid", d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/leaves/decide":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                con.execute("UPDATE leaves SET status=?, decided_by=? WHERE id=?",
                            (d["status"], u["username"], int(d["id"])))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/approvals":
                cur = con.execute(
                    "INSERT INTO approvals(type,payload,requested_by,created) VALUES(?,?,?,?)",
                    (d["type"], json.dumps(d.get("payload") or {}), u["username"], now_str()))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/approvals/decide":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                row = con.execute("SELECT * FROM approvals WHERE id=?", (int(d["id"]),)).fetchone()
                if not row:
                    return self.send_json({"error": "not found"}, 404)
                if d["status"] == "approved":
                    p = json.loads(row["payload"] or "{}")
                    w = con.execute("SELECT * FROM workers WHERE id=?", (int(p.get("worker_id") or 0),)).fetchone()
                    if row["type"] == "overtime" and w:
                        hrs = float(p.get("hours") or 0)
                        date_str = p.get("date") or today()
                        ex = con.execute("SELECT * FROM attendance WHERE worker_id=? AND date=?",
                                         (w["id"], date_str)).fetchone()
                        if ex:
                            con.execute("UPDATE attendance SET overtime_hours=overtime_hours+? WHERE id=?",
                                        (hrs, ex["id"]))
                        else:
                            con.execute("INSERT INTO attendance(worker_id,date,present,overtime_hours)"
                                        " VALUES(?,?,1,?)", (w["id"], date_str, hrs))
                    if row["type"] == "att_correction" and w:
                        date_str = p.get("date") or today()
                        ci, co = p.get("check_in", ""), p.get("check_out", "")
                        ot = compute_overtime(con, w, date_str, ci, co)
                        con.execute("INSERT INTO attendance(worker_id,date,present,check_in,check_out,overtime_hours)"
                                    " VALUES(?,?,?,?,?,?) ON CONFLICT(worker_id,date) DO UPDATE SET "
                                    "present=excluded.present, check_in=excluded.check_in,"
                                    " check_out=excluded.check_out, overtime_hours=excluded.overtime_hours",
                                    (w["id"], date_str, 1 if p.get("present", True) else 0, ci, co, ot))
                con.execute("UPDATE approvals SET status=?, decided_by=? WHERE id=?",
                            (d["status"], u["username"], int(d["id"])))
                audit(con, u["username"], "approval_" + d["status"], "%s #%s" % (row["type"], row["id"]))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/payments":
                _pr = create_payment(con, d, u)
                if _pr.get("ok") and d.get("direction") == "in":
                    # round 12: payment received -> email the party
                    # (the save above has already committed; the email
                    # is best-effort and can never undo it)
                    email_payment_to_party(con, int(d["party_id"]),
                                           float(d["amount"]),
                                           d.get("method") or "cash",
                                           d.get("date") or today())
                return self.send_json(_pr)
            if path == "/api/cheques/status":
                row = con.execute("SELECT * FROM cheques WHERE id=?", (int(d["id"]),)).fetchone()
                if not row:
                    return self.send_json({"error": "not found"}, 404)
                con.execute("UPDATE cheques SET status=? WHERE id=?", (d["status"], int(d["id"])))
                audit(con, u["username"], "cheque_" + d["status"],
                      "cheque %s Rs %g" % (row["cheque_no"], row["amount"]))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/heads":
                cur = con.execute("INSERT INTO expense_heads(name,parent_id) VALUES(?,?)",
                                  (d["name"].strip(), d.get("parent_id") or None))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/expenses":
                return self.send_json(create_expense(con, d, u))
            if path == "/api/expenses/status":
                row = con.execute("SELECT * FROM expenses WHERE id=?", (int(d["id"]),)).fetchone()
                if not row:
                    return self.send_json({"error": "not found"}, 404)
                st = d["status"]
                if st not in ("approved", "rejected"):
                    return self.send_json({"error": "status approved/rejected hi ho sakta hai"}, 400)
                con.execute("UPDATE expenses SET status=? WHERE id=?", (st, int(d["id"])))
                audit(con, u["username"], "expense_" + st,
                      "expense #%s Rs %g (%s)" % (row["id"], row["amount"], row["paid_by"]))
                con.commit()
                return self.send_json({"ok": True, "status": st})
            if path == "/api/cash-handovers":
                r = create_handover(con, d, u)
                audit(con, u["username"], "cash_handover",
                      "Rs %g -> %s" % (float(d.get("amount") or 0), r["holder_name"]))
                return self.send_json(r)
            if path == "/api/cash-handovers/ack":
                row = con.execute("SELECT * FROM cash_handovers WHERE id=?", (int(d["id"]),)).fetchone()
                if not row:
                    return self.send_json({"error": "not found"}, 404)
                if u["role"] != "owner" and row["holder_key"] != "user:%d" % u["id"]:
                    return self.send_json({"error": "ye handover aap ka nahi hai"}, 403)
                con.execute("UPDATE cash_handovers SET status='confirmed', ack_at=? WHERE id=?",
                            (now_str(), int(d["id"])))
                audit(con, u["username"], "cash_ack", "handover #%s" % row["id"])
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/cash-counts":
                r = create_cash_count(con, d, u)
                audit(con, u["username"], "cash_count",
                      "%s counted %g book %g diff %g" % (d.get("holder_key"), r["counted"], r["book"], r["diff"]))
                return self.send_json(r)
            if path == "/api/machines":
                cur = con.execute("INSERT INTO machines(name,note) VALUES(?,?)",
                                  ((d.get("name") or "").strip(), d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/machine-entries":
                r = create_machine_entry(con, d, u)
                audit(con, u["username"], "machine_entry",
                      "machine #%s %s Rs %g" % (d.get("machine_id"), d.get("work_type") or "", float(d.get("cost") or 0)))
                return self.send_json(r)
            if path == "/api/godam-counts":
                r = create_godam_count(con, d, u)
                audit(con, u["username"], "godam_count",
                      "party %s counted %s book %s diff %s" % (d.get("party_id"), r["counted_bags"], r["book_bags"], r["diff"]))
                return self.send_json(r)
            if path == "/api/phosphate-detail/remark":
                ds = (d.get("date") or "").strip()
                rk = (d.get("remark") or "").strip()
                con.execute("INSERT INTO daily_remarks(date, remark) VALUES(?,?) "
                            "ON CONFLICT(date) DO UPDATE SET remark=excluded.remark",
                            (ds, rk))
                audit(con, u["username"], "phosphate_remark", "%s: %s" % (ds, rk[:60]))
                con.commit()
                return self.send_json({"ok": True, "date": ds, "remark": rk})
            if path == "/api/demo/load":
                ids = demo_load(con, u)
                if ids is None:
                    return self.send_json(
                        {"error": "Demo data pehle se load hai — pehle purana demo delete karein."}, 400)
                audit(con, u["username"], "demo_load", "%d rows" % len(ids))
                return self.send_json({"ok": True, "count": len(ids)})
            if path == "/api/demo/remove":
                n = demo_remove(con, u)
                audit(con, u["username"], "demo_remove", "%d rows" % n)
                return self.send_json({"ok": True, "removed": n})
            if path == "/api/stock-adjustments":
                cnt = con.execute("SELECT * FROM godam_counts WHERE id=?",
                                  (int(d["count_id"]),)).fetchone()
                if not cnt:
                    return self.send_json({"error": "count nahi mila"}, 404)
                if cnt["diff"] == 0:
                    return self.send_json({"error": "farq zero hai — adjustment ki zaroorat nahi"}, 400)
                dup = con.execute("SELECT id FROM bag_adjustments WHERE count_id=? "
                                  "AND status IN ('pending','approved')", (cnt["id"],)).fetchone()
                if dup:
                    return self.send_json({"error": "is ginti ka adjustment pehle se maujood hai"}, 400)
                cur = con.execute(
                    "INSERT INTO bag_adjustments(date,party_id,bags,count_id,status,created_by,note)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (today(), cnt["party_id"], cnt["diff"], cnt["id"], "pending",
                     u["username"], "Ginti Adjustment"))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/stock-adjustments/decide":
                row = con.execute("SELECT * FROM bag_adjustments WHERE id=?",
                                  (int(d["id"]),)).fetchone()
                if not row:
                    return self.send_json({"error": "not found"}, 404)
                st = d["status"]
                if st not in ("approved", "rejected"):
                    return self.send_json({"error": "status approved/rejected hi ho sakta hai"}, 400)
                if row["status"] != "pending":
                    return self.send_json({"error": "ye adjustment pehle decide ho chuka hai"}, 400)
                con.execute("UPDATE bag_adjustments SET status=?, decided_by=? WHERE id=?",
                            (st, u["username"], int(d["id"])))
                audit(con, u["username"], "stock_adj_" + st,
                      "adjustment #%s bags %+d party %s" % (row["id"], row["bags"], row["party_id"]))
                con.commit()
                return self.send_json({"ok": True, "status": st})
            if path == "/api/maintenance":
                cur = con.execute(
                    "INSERT INTO maintenance(date,machine,detail,cost,downtime_hours) VALUES(?,?,?,?,?)",
                    (d.get("date") or today(), d.get("machine", ""), d.get("detail", ""),
                     float(d.get("cost") or 0), float(d.get("downtime_hours") or 0)))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/stock-counts":
                cur = con.execute(
                    "INSERT INTO stock_counts(date,item,counted_qty,book_qty,note) VALUES(?,?,?,?,?)",
                    (d.get("date") or today(), d.get("item", ""), float(d.get("counted_qty") or 0),
                     float(d.get("book_qty") or 0), d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/day-costs":
                # upsert by date: a second save for the same day edits
                # the stored row — owner-only, like every entry edit
                if u["role"] != "owner" and con.execute(
                        "SELECT date FROM day_costs WHERE date=?",
                        (d.get("date") or today(),)).fetchone():
                    return self.send_json({"error": OWNER_EDIT_MSG}, 403)
                con.execute("INSERT INTO day_costs(date,diesel_litres,elec_units) VALUES(?,?,?)"
                            " ON CONFLICT(date) DO UPDATE SET diesel_litres=excluded.diesel_litres,"
                            " elec_units=excluded.elec_units",
                            (d.get("date") or today(), float(d.get("diesel_litres") or 0),
                             float(d.get("elec_units") or 0)))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/attachments":
                return self._save_attachment(d, u, con)
            if path == "/api/attachments/delete":
                row = con.execute("SELECT * FROM attachments WHERE id=?", (int(d["id"]),)).fetchone()
                if row:
                    con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                                " VALUES(?,?,?,?,?)",
                                (now_str(), "attachments", row["id"],
                                 json.dumps({"filename": row["filename"], "mime": row["mime"]}), u["username"]))
                    con.execute("DELETE FROM attachments WHERE id=?", (int(d["id"]),))
                    con.commit()
                return self.send_json({"ok": True})
            if path == "/api/proofs":
                cur = con.execute(
                    "INSERT INTO payment_proofs(party_id,date,amount,attachment_id,note) VALUES(?,?,?,?,?)",
                    (int(d["party_id"]), d.get("date") or today(), float(d.get("amount") or 0),
                     d.get("attachment_id") or None, d.get("note", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid})
            if path == "/api/proofs/confirm":
                pr = con.execute("SELECT * FROM payment_proofs WHERE id=?", (int(d["id"]),)).fetchone()
                if not pr:
                    return self.send_json({"error": "not found"}, 404)
                cur = con.execute(
                    "INSERT INTO payments(date,party_id,direction,amount,method,note) VALUES(?,?,?,?,?,?)",
                    (today(), pr["party_id"], "in", float(d.get("amount") or pr["amount"]),
                     d.get("method") or "online", "Client proof confirmed"))
                con.execute("UPDATE payment_proofs SET status='confirmed', payment_id=? WHERE id=?",
                            (cur.lastrowid, int(d["id"])))
                audit(con, u["username"], "proof_confirmed", "proof #%s" % d["id"])
                con.commit()
                # round 12: the confirmed payment is RECEIVED money —
                # email the party its receipt, like any other payment
                email_payment_to_party(con, pr["party_id"],
                                       float(d.get("amount") or pr["amount"]),
                                       d.get("method") or "online", today())
                return self.send_json({"ok": True, "payment_id": cur.lastrowid})
            if path == "/api/proofs/reject":
                con.execute("UPDATE payment_proofs SET status='rejected' WHERE id=?", (int(d["id"]),))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/devices":
                cur = con.execute(
                    "INSERT INTO biometric_devices(name,serial,pin) VALUES(?,?,?)",
                    (d.get("name", ""), d["serial"].strip(), d.get("pin", "")))
                con.commit()
                return self.send_json({"ok": True, "id": cur.lastrowid,
                                       "address": "http://%s:%d/iclock/cdata" % (lan_ip(), MAIN_PORT[0] + DEVICE_PORT_OFFSET)})
            if path == "/api/bio/import":
                return self._bio_import(con, d, u)
            if path == "/api/alerts/generate":
                made = []
                for p in con.execute("SELECT * FROM parties ORDER BY name"):
                    _e, bal = party_ledger(con, p["id"])
                    if bal > 0 and p["whatsapp"]:
                        comp = wa_compose(con, p["id"], "ur", "t")
                        msg = comp["text"] if comp else (
                            "Payment reminder — %s\nBalance: Rs %s (aap ne denay hain)."
                            % (p["name"], format(bal, ",.0f")))
                        aid = make_alert(con, "payment_reminder", p["id"], p["whatsapp"], msg,
                                         [p["name"], format(bal, ",.0f")])
                        made.append(aid)
                owa = meta_get(con, "owner_whatsapp")
                if owa:
                    tot_r = sum(max(party_ledger(con, p["id"])[1], 0)
                                for p in con.execute("SELECT id FROM parties"))
                    msg = "Weekly summary: total to receive Rs " + format(tot_r, ",.0f")
                    make_alert(con, "owner_summary", None, owa, msg, [format(tot_r, ",.0f")])
                return self.send_json({"ok": True, "generated": len(made)})
            if path == "/api/alerts/send":
                row = con.execute("SELECT * FROM alerts WHERE id=?", (int(d["id"]),)).fetchone()
                if not row:
                    return self.send_json({"error": "not found"}, 404)
                st = dispatch_alert(con, row)
                con.commit()
                return self.send_json({"ok": True, "status": st})
            if path == "/api/alerts/delete":
                con.execute("DELETE FROM alerts WHERE id=?", (int(d["id"]),))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/notifications/read":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                if d.get("id"):
                    con.execute("UPDATE notifications SET is_read=1 WHERE id=?", (int(d["id"]),))
                else:
                    con.execute("UPDATE notifications SET is_read=1")
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/delete":
                tbl = d.get("table")
                if tbl not in EDITABLE_TABLES and tbl not in ("parties", "workers", "departments"):
                    return self.send_json({"error": "this table cannot be deleted from here"}, 400)
                rid = int(d["id"])
                row = con.execute("SELECT * FROM %s WHERE id=?" % tbl, (rid,)).fetchone()
                if not row:
                    return self.send_json({"error": "not found"}, 404)
                rowd = {k: (("<binary>" if isinstance(row[k], bytes) else row[k])) for k in row.keys()}
                con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                            " VALUES(?,?,?,?,?)", (now_str(), tbl, rid, json.dumps(rowd), u["username"]))
                con.execute("DELETE FROM %s WHERE id=?" % tbl, (rid,))
                if tbl == "grinding_jobs":
                    # merged entry: the production row written with this
                    # job is part of the same entry — recycle + delete it
                    # too, so the pair never splits (each row keeps its
                    # own recycle entry and restores on its own).
                    for pr in con.execute("SELECT * FROM production WHERE job_id=?",
                                          (rid,)).fetchall():
                        pd = {k: (("<binary>" if isinstance(pr[k], bytes) else pr[k]))
                              for k in pr.keys()}
                        con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                                    " VALUES(?,?,?,?,?)", (now_str(), "production", pr["id"],
                                                          json.dumps(pd), u["username"]))
                        con.execute("DELETE FROM production WHERE id=?", (pr["id"],))
                if tbl == "trips":
                    # a gate sale is part of the trip entry: recycle +
                    # delete the linked sale row with its trip
                    for sr in con.execute("SELECT * FROM sales WHERE trip_id=?",
                                          (rid,)).fetchall():
                        sd = {k: (("<binary>" if isinstance(sr[k], bytes) else sr[k]))
                              for k in sr.keys()}
                        con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                                    " VALUES(?,?,?,?,?)", (now_str(), "sales", sr["id"],
                                                          json.dumps(sd), u["username"]))
                        con.execute("DELETE FROM sales WHERE id=?", (sr["id"],))
                if tbl == "outside_grinding" and (rowd.get("kind") or "") == "bill":
                    # a Grinding Bill's paid-now payment is part of the
                    # same entry — recycle + delete it with the bill
                    for pr in con.execute("SELECT * FROM payments WHERE og_bill_id=?",
                                          (rid,)).fetchall():
                        pd2 = {k: (("<binary>" if isinstance(pr[k], bytes) else pr[k]))
                               for k in pr.keys()}
                        con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                                    " VALUES(?,?,?,?,?)", (now_str(), "payments", pr["id"],
                                                          json.dumps(pd2), u["username"]))
                        con.execute("DELETE FROM payments WHERE id=?", (pr["id"],))
                if tbl in ("purchases", "sales") and (rowd.get("deal_id") or ""):
                    # one leg of a direct-trade deal: the deal is a unit
                    # — its other leg is recycled + deleted with it
                    _other = "sales" if tbl == "purchases" else "purchases"
                    for lr in con.execute("SELECT * FROM %s WHERE deal_id=?" % _other,
                                          (rowd["deal_id"],)).fetchall():
                        ld = {k: (("<binary>" if isinstance(lr[k], bytes) else lr[k]))
                              for k in lr.keys()}
                        con.execute("INSERT INTO recycle(created,table_name,record_id,data_json,deleted_by)"
                                    " VALUES(?,?,?,?,?)", (now_str(), _other, lr["id"],
                                                          json.dumps(ld), u["username"]))
                        con.execute("DELETE FROM %s WHERE id=?" % _other, (lr["id"],))
                detail = "%s #%d deleted by %s" % (tbl, rid, u["username"])
                audit(con, u["username"], "delete", detail)
                notify_owner(con, "delete", detail + " — Recycle/Deleted Report se restore ho sakta hai.")
                con.commit()
                owa = meta_get(con, "owner_whatsapp")
                if owa:
                    make_alert(con, "deletion", None, owa,
                               "Deletion alert: " + detail, [tbl, str(rid), u["username"]])
                return self.send_json({"ok": True})
            if path == "/api/restore-recycle":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                rec = con.execute("SELECT * FROM recycle WHERE id=?", (int(d["id"]),)).fetchone()
                if not rec:
                    return self.send_json({"error": "not found"}, 404)
                data = json.loads(rec["data_json"] or "{}")
                cols = [c for c in data.keys()]
                vals = [data[c] for c in cols]
                con.execute("INSERT OR REPLACE INTO %s(%s) VALUES(%s)"
                            % (rec["table_name"], ",".join(cols), ",".join("?" * len(cols))), vals)
                con.execute("DELETE FROM recycle WHERE id=?", (rec["id"],))
                audit(con, u["username"], "restore", "%s #%s" % (rec["table_name"], rec["record_id"]))
                con.commit()
                return self.send_json({"ok": True})
            if path == "/api/xl/import/preview":
                return self._xl_import(con, d, u, apply=False)
            if path == "/api/xl/import/apply":
                return self._xl_import(con, d, u, apply=True)
            if path == "/api/import/preview":
                return self._import(con, d, apply=False)
            if path == "/api/import/apply":
                return self._import(con, d, apply=True)
            if path == "/api/backup":
                con.close()
                name, _ = make_backup()
                return self.send_json({"ok": True, "file": name})
            if path == "/api/restore":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                cfg = load_config()
                fname = os.path.basename(d.get("file") or "")
                zpath = os.path.join(cfg.get("backup_dir") or "", fname)
                if not fname or not os.path.exists(zpath):
                    return self.send_json({"error": "backup file not found"}, 400)
                con.close()  # must close BEFORE make_backup: its snapshot of the
                # live DB would otherwise wait on this connection's locks forever
                safety, _ = make_backup()
                with zipfile.ZipFile(zpath) as z:
                    data = z.read("mill-database.db")
                with open(db_path(), "wb") as f:
                    f.write(data)
                return self.send_json({"ok": True, "safety_backup": safety})
            if path == "/api/users":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                role = d["role"]
                if role not in ("owner", "manager", "client", "staff", "demo"):
                    return self.send_json({"error": "invalid role"}, 400)
                if (d.get("username") or "").strip() == DEMO_USERNAME and role != "demo":
                    # the published demo name may only ever be the
                    # view-only login — never a disguised full account
                    return self.send_json({"error": "'demo' naam sirf demo (view-only) login ke liye hai"}, 400)
                if IS_PC and role == "client":
                    return self.send_json({"error": "PC edition mein client login nahi banta — client portal sirf online version mein hai"}, 400)
                email = (d.get("email") or "").strip()
                if role == "demo":
                    email = ""   # the published demo login never carries an email
                _ee = _user_email_error(con, email)
                if _ee:
                    return self.send_json({"error": _ee}, 400)
                salt, h = hash_pw(d["password"])
                cur = con.execute(
                    "INSERT INTO users(username,salt,pass_hash,role,party_id,perms,email,created) VALUES(?,?,?,?,?,?,?,?)",
                    (d["username"].strip(), salt, h, role, d.get("party_id") or None,
                     json.dumps(clean_perms(d.get("perms")) if role == "staff" else []), email, today()))
                if role == "client" and d.get("party_id"):
                    _sync_party_user_email(con, int(d["party_id"]), email,
                                           from_user=True)
                audit(con, u["username"], "create", "login %s (%s)" % (d["username"].strip(), role))
                con.commit()
                cred = None
                if role != "demo":
                    # Round 12: send the new login its credentials
                    # (best-effort; result reported to the owner)
                    cred = deliver_credentials(con, self,
                                               {"username": d["username"].strip(),
                                                "role": role,
                                                "party_id": d.get("party_id") or None,
                                                "email": email},
                                               d["password"])
                return self.send_json({"ok": True, "id": cur.lastrowid, "cred": cred})
            if path == "/api/users/update":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                uid = int(d["user_id"])
                role = d.get("role") or ""
                if role not in ("owner", "manager", "client", "staff", "demo"):
                    return self.send_json({"error": "invalid role"}, 400)
                _tgt = con.execute("SELECT username, role, email FROM users WHERE id=?",
                                   (uid,)).fetchone()
                if not _tgt:
                    return self.send_json({"error": "login not found"}, 404)
                if _tgt["role"] == "demo" and role != "demo":
                    # a demo login can never be promoted into a real
                    # account — delete it and make a fresh login instead
                    return self.send_json({"error": "demo login ka role change nahi hota — ye sirf view-only rehta hai (delete karke naya login bana lein)"}, 400)
                if IS_PC and role == "client":
                    return self.send_json({"error": "PC edition mein client login nahi banta — client portal sirf online version mein hai"}, 400)
                if uid == u["id"] and role != "owner":
                    return self.send_json({"error": "apna role owner hi rakhein (lockout se bachein)"}, 400)
                email = ((d.get("email") if d.get("email") is not None
                          else _tgt["email"]) or "").strip()
                if role == "demo":
                    email = ""   # the published demo login never carries an email
                _ee = _user_email_error(con, email, exclude_id=uid)
                if _ee:
                    return self.send_json({"error": _ee}, 400)
                con.execute("UPDATE users SET role=?, party_id=?, perms=?, email=? WHERE id=?",
                            (role, d.get("party_id") or None,
                             json.dumps(clean_perms(d.get("perms")) if role == "staff" else []), email, uid))
                if role == "client" and d.get("party_id"):
                    _sync_party_user_email(con, int(d["party_id"]), email,
                                           from_user=True)
                audit(con, u["username"], "update", "login #%d -> role %s" % (uid, role))
                con.commit()
                _drop_sessions(uid)
                return self.send_json({"ok": True})
            if path == "/api/users/password":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                _trow = con.execute("SELECT * FROM users WHERE id=?",
                                    (int(d["user_id"]),)).fetchone()
                salt, h = hash_pw(d["password"])
                con.execute("UPDATE users SET salt=?, pass_hash=?, fail_count=0, locked_until=0 WHERE id=?",
                            (salt, h, int(d["user_id"])))
                # a password change kills any open reset link for this login
                con.execute("UPDATE password_resets SET used=2 WHERE user_id=? AND used=0",
                            (int(d["user_id"]),))
                con.commit()
                _drop_sessions(int(d["user_id"]))
                cred = None
                if _trow and _trow["role"] != "demo":
                    # Round 12: offer the same credential send with the
                    # JUST-SET password (old passwords are never stored)
                    cred = deliver_credentials(con, self, _trow, d["password"])
                return self.send_json({"ok": True, "cred": cred})
            if path == "/api/users/delete":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                if int(d["user_id"]) == u["id"]:
                    return self.send_json({"error": "you cannot delete your own login"}, 400)
                _du = con.execute("SELECT username FROM users WHERE id=?",
                                  (int(d["user_id"]),)).fetchone()
                con.execute("DELETE FROM users WHERE id=?", (int(d["user_id"]),))
                if _du and _du["username"] == DEMO_USERNAME:
                    # tombstone: the startup seed must not resurrect
                    # a demo login the owner deliberately removed
                    meta_set(con, "demo_seed_off", "1")
                con.commit()
                _drop_sessions(int(d["user_id"]))
                return self.send_json({"ok": True})
            if path == "/api/settings/test-email":
                # round 12: the owner's live SMTP check — the result
                # (including the server's own error text) is reported
                # honestly, never dressed up as success
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                to = (d.get("to") or "").strip() or owner_email_addr(con) \
                    or mail_settings(con)["smtp_user"]
                mill = meta_get(con, "mill_name", APP_NAME)
                T = MAIL_TXT.get(u.get("lang") or "en") or MAIL_TXT["en"]
                subj = T["test_subj"].format(mill=mill)
                body = T["test_body"].format(mill=mill)
                ok, detail = send_email(con, to, subj, body,
                                        _email_html(mill, body))
                log_email(con, "email_test", None, to, subj, ok, detail)
                audit(con, u["username"], "email_test",
                      "test email to %s: %s" % (to, "sent" if ok else detail))
                con.commit()
                return self.send_json({"ok": ok, "detail": detail, "to": to})
            if path == "/api/email/statement":
                # round 12: "Send by Email" for the party khata — the
                # same composed statement the WhatsApp button sends,
                # to the party's email (party field, else client login)
                pid = int(d.get("party_id") or 0)
                prow = con.execute("SELECT * FROM parties WHERE id=?",
                                   (pid,)).fetchone()
                if not prow:
                    return self.send_json({"error": "party not found"}, 404)
                if not mail_configured(con):
                    return self.send_json(
                        {"error": "Email is not set up yet — Settings -> Email mein SMTP dalein"}, 400)
                if not mail_settings(con)["mail_enabled"]:
                    return self.send_json(
                        {"error": "Email sending Settings -> Email mein off hai"}, 400)
                to = party_email_addr(con, pid)
                if not to:
                    return self.send_json(
                        {"error": "is party ka email saved nahi hai (party par ya us ke client login par email dalein)"}, 400)
                lang = d.get("lang") or party_lang(
                    con, pid, default=u.get("lang") or "en")
                if lang not in ("en", "ur", "hi"):
                    lang = "en"
                comp = wa_compose(con, pid, lang, d.get("unit") or u.get("unit") or "t")
                if not comp:
                    return self.send_json({"error": "party not found"}, 404)
                mill = meta_get(con, "mill_name", APP_NAME)
                T = MAIL_TXT.get(lang) or MAIL_TXT["en"]
                subj = T["stmt_subj"].format(party=prow["name"]) + " — " + mill
                ok, detail = send_email(con, to, subj, comp["text"],
                                        _email_html(mill, comp["text"]))
                log_email(con, "email_statement", pid, to, subj, ok, detail)
                audit(con, u["username"], "email_statement",
                      "khata statement to %s (%s)" % (prow["name"],
                                                      "sent" if ok else detail))
                con.commit()
                if not ok:
                    return self.send_json({"error": "email nahi gaya: " + detail}, 400)
                return self.send_json({"ok": True, "to": to})
            if path == "/api/email/invoice":
                # round 12: "Send by Email" for a sale invoice — the
                # printed invoice's figures, as a clean email
                sid = int(d.get("sale_id") or 0)
                s = con.execute("SELECT * FROM sales WHERE id=?",
                                (sid,)).fetchone()
                if not s:
                    return self.send_json({"error": "sale not found"}, 404)
                if not mail_configured(con):
                    return self.send_json(
                        {"error": "Email is not set up yet — Settings -> Email mein SMTP dalein"}, 400)
                if not mail_settings(con)["mail_enabled"]:
                    return self.send_json(
                        {"error": "Email sending Settings -> Email mein off hai"}, 400)
                prow = con.execute("SELECT * FROM parties WHERE id=?",
                                   (s["party_id"],)).fetchone()
                to = party_email_addr(con, s["party_id"])
                if not to:
                    return self.send_json(
                        {"error": "is party ka email saved nahi hai (party par ya us ke client login par email dalein)"}, 400)
                lang = party_lang(con, s["party_id"],
                                  default=u.get("lang") or "en")
                T = MAIL_TXT.get(lang) or MAIL_TXT["en"]
                _sit = s["item"] or "powder"
                if _sit == "other":
                    _idesc = s["item_name"] or "Item"
                    _iwt = "%g %s" % (s["qty"] or 0, s["unit"] or "")
                    _ibags = "-"
                    _irate = format(s["unit_rate"] or 0, ",.0f")
                elif _sit == "rock":
                    _idesc = "Phosphate Rock"
                    _iwt = fmt_weight(s["tons"] * 1000, u.get("unit") or "t")
                    _ibags = "-"
                    _irate = format(s["rate_per_ton"], ",.0f")
                else:
                    _idesc = "Phosphate Powder"
                    _iwt = fmt_weight(s["tons"] * 1000, u.get("unit") or "t")
                    _ibags = "%d" % s["bags"]
                    _irate = format(s["rate_per_ton"], ",.0f")
                mill = meta_get(con, "mill_name", APP_NAME)
                subj = T["inv_subj"].format(
                    inv=s["invoice_no"] or ("#" + str(s["id"])),
                    amt=format(s["amount"], ",.0f")) + " — " + mill
                body = T["inv_body"].format(
                    inv=s["invoice_no"] or ("#" + str(s["id"])), date=s["date"],
                    party=prow["name"] if prow else "", item=_idesc, wt=_iwt,
                    bags=_ibags, rate=_irate,
                    amt=format(s["amount"], ",.0f"), mill=mill)
                ok, detail = send_email(con, to, subj, body,
                                        _email_html(mill, body))
                log_email(con, "email_invoice", s["party_id"], to, subj,
                          ok, detail)
                audit(con, u["username"], "email_invoice",
                      "invoice %s to %s (%s)"
                      % (s["invoice_no"] or sid, prow["name"] if prow else "",
                         "sent" if ok else detail))
                con.commit()
                if not ok:
                    return self.send_json({"error": "email nahi gaya: " + detail}, 400)
                return self.send_json({"ok": True, "to": to})
            if path == "/api/settings/bag-kg":
                # Grinding page card: owner/manager (perm map says "om").
                _bk_err = _save_bag_kg(con, d.get("bag_kg"))
                if _bk_err:
                    return self.send_json({"error": _bk_err}, 400)
                con.commit()
                return self.send_json({"ok": True, "bag_kg": bag_kg(con)})
            if path == "/api/settings/bag-weights":
                # Grinding & Production page 'Bag weight defaults' card:
                # owner/manager (perm map says "om"). Stores the DEFAULT
                # kg per powder bag + per filter bag; production saves
                # stamp the values in effect onto their own rows.
                _bw_err = _save_bag_weights(con, d.get("powder_bag_kg"),
                                            d.get("filter_bag_kg"))
                if _bw_err:
                    return self.send_json({"error": _bw_err}, 400)
                con.commit()
                return self.send_json({"ok": True, **bag_weights(con)})
            if path == "/api/settings":
                if u["role"] != "owner":
                    return self.send_json({"error": "owner only"}, 403)
                cfg = load_config()
                _skeys = ("mill_name", "mill_phone", "mill_address", "owner_whatsapp",
                          "wa_phone_id", "sms_url", "sms_sender")
                if IS_PC:
                    _skeys = ("mill_name", "mill_phone", "mill_address", "owner_whatsapp")
                for key in _skeys:
                    if d.get(key) is not None:
                        meta_set(con, key, str(d[key]).strip())
                if d.get("wa_token") and not IS_PC:
                    meta_set(con, "wa_token", str(d["wa_token"]).strip())
                if d.get("sms_key") and not IS_PC:
                    meta_set(con, "sms_key", str(d["sms_key"]).strip())
                # round 12: email (SMTP) settings — saved on BOTH
                # editions (unlike the WhatsApp Cloud keys above): a
                # factory PC has internet too, and SMTP is portable.
                # The PC difference is only the reset LINK's reach —
                # that is what the system_address setting is for.
                if d.get("smtp_from_email"):
                    if not _valid_email(str(d["smtp_from_email"])):
                        return self.send_json({"error": "From email theek likhein"}, 400)
                for _mk in ("smtp_host", "smtp_user", "smtp_from_name",
                            "smtp_from_email", "system_address"):
                    if d.get(_mk) is not None:
                        meta_set(con, _mk, str(d[_mk]).strip())
                if d.get("smtp_port") is not None:
                    try:
                        _sp = int(d["smtp_port"])
                    except (TypeError, ValueError):
                        return self.send_json({"error": "SMTP port number likhein"}, 400)
                    if _sp < 1 or _sp > 65535:
                        return self.send_json({"error": "SMTP port 1 se 65535 ke darmiyan rakhein"}, 400)
                    meta_set(con, "smtp_port", str(_sp))
                if d.get("smtp_security") is not None:
                    if str(d["smtp_security"]) not in ("starttls", "ssl", "none"):
                        return self.send_json({"error": "SMTP security ghalat hai"}, 400)
                    meta_set(con, "smtp_security", str(d["smtp_security"]))
                if d.get("mail_preset") is not None:
                    if str(d["mail_preset"]) not in ("custom", "gmail", "brevo",
                                                     "smtp2go", "hostinger", "outlook"):
                        return self.send_json({"error": "Email service ghalat hai"}, 400)
                    meta_set(con, "mail_preset", str(d["mail_preset"]))
                if d.get("smtp_pass"):
                    meta_set(con, "smtp_pass", str(d["smtp_pass"]).strip())
                for _tk2 in ("mail_enabled", "mail_ev_proof", "mail_ev_payment",
                             "mail_ev_voucher", "mail_ev_dayend"):
                    if d.get(_tk2) is not None:
                        meta_set(con, _tk2, "1" if d[_tk2] else "0")
                if d.get("banks") is not None:
                    meta_set(con, "banks", json.dumps(d["banks"]))
                for _ck in ("cash_holder_limit", "cash_approval_limit"):
                    if d.get(_ck) is not None:
                        try:
                            _cv = float(d[_ck])
                        except (TypeError, ValueError):
                            return self.send_json({"error": "cash limit number likhein"}, 400)
                        if _cv < 0:
                            return self.send_json({"error": "cash limit negative nahi ho sakta"}, 400)
                        meta_set(con, _ck, str(_cv))
                if d.get("powder_age_days") is not None:
                    try:
                        _pd = int(d["powder_age_days"])
                    except (TypeError, ValueError):
                        return self.send_json({"error": "powder age days number likhein"}, 400)
                    if _pd < 0:
                        return self.send_json({"error": "powder age days negative nahi ho sakte"}, 400)
                    meta_set(con, "powder_age_days", str(_pd))
                if d.get("wastage_pct") is not None:
                    try:
                        _wp = float(d["wastage_pct"])
                    except (TypeError, ValueError):
                        return self.send_json({"error": "wastage % number likhein"}, 400)
                    if _wp < 0 or _wp > 100:
                        return self.send_json({"error": "wastage % 0 se 100 ke darmiyan rakhein"}, 400)
                    meta_set(con, "wastage_pct", str(_wp))
                for _tk in ("day_shift_end", "night_shift_end", "vehicle_alert_time"):
                    if d.get(_tk):
                        _tv = _hhmm(d[_tk], "")
                        if not _tv:
                            return self.send_json(
                                {"error": "time HH:MM format mein likhein"}, 400)
                        meta_set(con, _tk, _tv)
                if d.get("bag_kg") is not None:
                    _bk_err = _save_bag_kg(con, d.get("bag_kg"))
                    if _bk_err:
                        return self.send_json({"error": _bk_err}, 400)
                if d.get("powder_bag_kg") is not None or d.get("filter_bag_kg") is not None:
                    _cur_bw = bag_weights(con)
                    _bw_err = _save_bag_weights(
                        con,
                        d.get("powder_bag_kg") if d.get("powder_bag_kg") is not None
                        else _cur_bw["powder_bag_kg"],
                        d.get("filter_bag_kg") if d.get("filter_bag_kg") is not None
                        else _cur_bw["filter_bag_kg"])
                    if _bw_err:
                        return self.send_json({"error": _bw_err}, 400)
                for _fk in ("ui_font", "print_font"):
                    if d.get(_fk) is not None:
                        if str(d[_fk]) not in FONT_STACKS:
                            return self.send_json({"error": "font ghalat hai"}, 400)
                        meta_set(con, _fk, str(d[_fk]))
                for _fk in ("ui_text_size", "print_text_size"):
                    if d.get(_fk) is not None:
                        if str(d[_fk]) not in FONT_SIZES:
                            return self.send_json({"error": "text size ghalat hai"}, 400)
                        meta_set(con, _fk, str(d[_fk]))
                for k in ("voice_alerts", "voice_vehicles", "voice_payments"):
                    if d.get(k) is not None:
                        meta_set(con, k, "1" if d[k] else "0")
                if d.get("print_bold_headings") is not None:
                    meta_set(con, "print_bold_headings", "1" if d["print_bold_headings"] else "0")
                if d.get("print_voucher_copies") is not None:
                    if str(d["print_voucher_copies"]) not in ("1", "2", "3"):
                        return self.send_json({"error": "voucher copies 1, 2 ya 3 select karein"}, 400)
                    meta_set(con, "print_voucher_copies", str(d["print_voucher_copies"]))
                if d.get("bank_opening") is not None:
                    _bo = d["bank_opening"]
                    if not isinstance(_bo, dict):
                        return self.send_json({"error": "bank_opening ghalat hai"}, 400)
                    _clean = {}
                    for _bk, _bv in _bo.items():
                        try:
                            _clean[str(_bk)] = float(_bv or 0)
                        except (TypeError, ValueError):
                            return self.send_json({"error": "bank opening balance number likhein"}, 400)
                    meta_set(con, "bank_opening", json.dumps(_clean))
                if d.get("theme_color") is not None:
                    tc = str(d["theme_color"]).strip().lower()
                    if tc not in ACCENTS:
                        return self.send_json({"error": "unknown theme colour"}, 400)
                    meta_set(con, "theme_color", tc)
                if d.get("logo_remove"):
                    meta_set(con, "mill_logo_b64", "")
                    meta_set(con, "mill_logo_mime", "")
                    meta_set(con, "mill_logo_ver",
                             str(int(meta_get(con, "mill_logo_ver", "0") or 0) + 1))
                if d.get("logo_data") is not None:
                    mime = str(d.get("logo_mime") or "").lower()
                    if mime not in ("image/png", "image/jpeg", "image/webp"):
                        return self.send_json({"error": "logo PNG / JPG / WebP hi ho sakta hai"}, 400)
                    b64 = str(d["logo_data"]).strip()
                    try:
                        raw = base64.b64decode(b64, validate=True)
                    except Exception:
                        return self.send_json({"error": "logo data kharab hai"}, 400)
                    if not raw or len(raw) > 90 * 1024:
                        return self.send_json({"error": "logo zyada bara hai (max ~90 KB)"}, 400)
                    meta_set(con, "mill_logo_b64", b64)
                    meta_set(con, "mill_logo_mime", mime)
                    meta_set(con, "mill_logo_ver",
                             str(int(meta_get(con, "mill_logo_ver", "0") or 0) + 1))
                audit(con, u["username"], "settings", "settings updated")
                if d.get("backup_dir"):
                    os.makedirs(d["backup_dir"], exist_ok=True)
                    cfg["backup_dir"] = d["backup_dir"]
                if d.get("new_db_folder"):
                    folder = d["new_db_folder"]
                    os.makedirs(folder, exist_ok=True)
                    new_path = os.path.join(folder, "mill.db")
                    con.commit()  # close the write txn before snapshotting
                    dest = sqlite3.connect(new_path)
                    con.backup(dest); dest.close()
                    cfg["db_path"] = new_path
                save_config(cfg)
                globals()["CONFIG"] = cfg
                con.commit()
                return self.send_json({"ok": True, "db_path": cfg["db_path"],
                                       "theme_color": meta_get(con, "theme_color", "green") or "green",
                                       "has_logo": bool(meta_get(con, "mill_logo_b64")),
                                       "logo_ver": int(meta_get(con, "mill_logo_ver", "0") or 0)})
            return self.send_json({"error": "unknown endpoint"}, 404)
        except sqlite3.IntegrityError as e:
            return self.send_json({"error": "duplicate or invalid data: %s" % e}, 400)
        except (KeyError, ValueError) as e:
            return self.send_json({"error": "missing/invalid field: %s" % e}, 400)
        finally:
            try: con.close()
            except Exception: pass

    def _save_attachment(self, d, u, con=None):
        own = con is None
        if own:
            con = get_db()
        try:
            b64 = d.get("data_b64") or ""
            try:
                raw = base64.b64decode(b64)
            except Exception:
                return self.send_json({"error": "invalid file data"}, 400)
            mime = d.get("mime") or ""
            if not any(mime.startswith(p) for p in ATTACH_OK_MIME):
                return self.send_json({"error": "only images and PDF allowed"}, 400)
            if len(raw) > ATTACH_MAX:
                return self.send_json({"error": "file too large (max 5 MB)"}, 400)
            cur = con.execute(
                "INSERT INTO attachments(table_name,record_id,filename,mime,size,data,uploaded_by,created)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (d.get("table_name") or "misc", int(d.get("record_id") or 0),
                 d.get("filename") or "file", mime, len(raw), raw, u["username"], now_str()))
            con.commit()
            return self.send_json({"ok": True, "id": cur.lastrowid})
        finally:
            if own:
                con.close()

    def _bio_import(self, con, d, u):
        text = d.get("csv") or ""
        rdr = csv.DictReader(io.StringIO(text))
        ok = skip = 0
        for row in rdr:
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            code = row.get("device_code") or row.get("code") or row.get("pin") or row.get("user id") or row.get("id")
            date_str = row.get("date") or (row.get("datetime") or row.get("time") or "")[:10]
            tm = row.get("check_in") or row.get("time") or (row.get("datetime") or "")[11:16]
            if not code or not date_str:
                skip += 1
                continue
            w = con.execute("SELECT * FROM workers WHERE device_code=?", (code,)).fetchone()
            if not w:
                skip += 1
                continue
            hm = tm[:5] if tm else ""
            ex = con.execute("SELECT * FROM attendance WHERE worker_id=? AND date=?",
                             (w["id"], date_str)).fetchone()
            if ex is None:
                con.execute("INSERT INTO attendance(worker_id,date,present,check_in) VALUES(?,?,1,?)",
                            (w["id"], date_str, hm))
            else:
                ci = ex["check_in"] or hm
                co = ex["check_out"] or hm
                if hm and hm < ci: ci = hm
                if hm and hm > co: co = hm
                ot = compute_overtime(con, w, date_str, ci, co)
                con.execute("UPDATE attendance SET present=1, check_in=?, check_out=?, overtime_hours=? WHERE id=?",
                            (ci, co, ot, ex["id"]))
            ok += 1
        audit(con, u["username"], "bio_import", "%d rows ok, %d skipped" % (ok, skip))
        con.commit()
        return self.send_json({"ok": True, "imported": ok, "skipped": skip})

    def xl_format(self, q, u):
        """GET /api/xl/format — the data behind the upload popup: the
        module's expected columns + example rows, read from the SAME
        XL_MODULES entry the sample file and the importer use, so the
        popup can never drift from what the importer accepts (single
        source of truth). Same per-module permission as the sample."""
        mod = (q.get("module", [""])[0] or "").strip()
        M = XL_MODULES.get(mod)
        if not M or not M.get("convert"):
            return self.send_json({"error": "unknown module"}, 400)
        if not perm_ok(u, M["perm"]):
            return self.send_json({"error": "not allowed for this login"}, 403)
        return self.send_json({"module": mod, "label": M["label"],
                               "headers": M["headers"],
                               "sample": M["sample"],
                               "also": M.get("also") or [],
                               "need": M.get("need") or []})

    def xl_download(self, path, q, u):
        """GET /api/xl/export and /api/xl/sample — the module's own
        permission gates the download (checked here, per module)."""
        mod = (q.get("module", [""])[0] or "").strip()
        M = XL_MODULES.get(mod)
        if not M:
            return self.send_json({"error": "unknown module"}, 400)
        if not perm_ok(u, M["perm"]):
            return self.send_json({"error": "not allowed for this login"}, 403)
        fmt = (q.get("fmt", ["xlsx"])[0] or "xlsx").lower()
        con = get_db()
        try:
            if path == "/api/xl/sample":
                headers, rows = M["headers"], M["sample"]
                fname = "%s-sample" % mod
            else:
                headers = M["headers"]
                rows = M["export"](con, q)
                fname = "%s-export" % mod
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)
        finally:
            con.close()
        if fmt == "csv":
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(headers)
            for r in rows:
                w.writerow(["" if v is None else v for v in r])
            body = out.getvalue().encode("utf-8-sig")
            return self.send_file(body, "text/csv; charset=utf-8", fname + ".csv")
        if fmt == "pdf":
            con = get_db()
            try:
                mill = meta_get(con, "mill_name", APP_NAME)
            finally:
                con.close()
            body = pdf_build(headers, rows, M["label"], mill)
            return self.send_file(body, "application/pdf", fname + ".pdf")
        body = xlsx_build(headers, rows)
        return self.send_file(body,
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              fname + ".xlsx")

    def _xl_import(self, con, d, u, apply):
        mod = (d.get("module") or "").strip()
        M = XL_MODULES.get(mod)
        if not M or not M.get("convert"):
            return self.send_json({"error": "is module ka Excel import nahi hai"}, 400)
        try:
            headers, raw_rows = upload_rows(d)
            items = xl_analyze(con, mod, headers, raw_rows)
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)
        if not raw_rows:
            return self.send_json({"error": "file mein koi data row nahi mili"}, 400)
        pub = [{"row": it["row"], "status": it["status"], "reason": it["reason"],
                "data": it["data"]} for it in items]
        if not apply:
            return self.send_json({"ok": True, "module": mod, "total": len(items),
                                   "valid": sum(1 for it in items if it["status"] == "ok"),
                                   "duplicates": sum(1 for it in items if it["status"] == "duplicate"),
                                   "errors": sum(1 for it in items if it["status"] == "error"),
                                   "items": pub})
        added = 0
        for it in items:
            if it["status"] != "ok":
                continue
            # re-check against the live DB: a row earlier in THIS file may
            # have just added the same record
            if M["dedupe"](con, _XlCtx(con), it["payload"]):
                it["status"] = "duplicate"
                it["reason"] = "Ye record system mein pehle se maujood hai (duplicate)"
                continue
            try:
                _pl = it["payload"]
                if mod in ("purchases", "sales"):
                    _pl = dict(_pl, source="excel")
                M["create"](con, _pl, u)
                added += 1
            except Exception as e:
                it["status"] = "error"
                it["reason"] = "save nahi hua: %s" % e
        audit(con, u["username"], "xl_import",
              "%s: %d added, %d duplicate, %d error" % (
                  mod, added,
                  sum(1 for it in items if it["status"] == "duplicate"),
                  sum(1 for it in items if it["status"] == "error")))
        con.commit()
        pub = [{"row": it["row"], "status": it["status"], "reason": it["reason"],
                "data": it["data"]} for it in items]
        return self.send_json({"ok": True, "module": mod, "added": added,
                               "duplicates": [x for x in pub if x["status"] == "duplicate"],
                               "errors": [x for x in pub if x["status"] == "error"],
                               "total": len(items)})

    def _import(self, con, d, apply):
        tbl = d.get("table")
        allowed = {"parties", "trips", "production", "expenses", "payments", "workers", "attendance"}
        if tbl not in allowed:
            return self.send_json({"error": "import not supported for this table"}, 400)
        text = d.get("csv") or ""
        rdr = csv.DictReader(io.StringIO(text))
        if not rdr.fieldnames:
            return self.send_json({"error": "CSV has no header row"}, 400)
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % tbl)]
        rows = []
        for r in rdr:
            rows.append({k.strip(): v for k, v in r.items() if k and k.strip() in cols and k.strip() != "id"})
        if not apply:
            return self.send_json({"ok": True, "count": len(rows), "columns": list(rows[0].keys()) if rows else [],
                                   "preview": rows[:10]})
        n = 0
        for r in rows:
            if not r:
                continue
            keys = list(r.keys())
            try:
                con.execute("INSERT INTO %s(%s) VALUES(%s)" % (tbl, ",".join(keys), ",".join("?" * len(keys))),
                            [r[k] if r[k] != "" else None for k in keys])
                n += 1
            except Exception:
                pass
        audit(con, "import", "import_" + tbl, "%d rows" % n)
        con.commit()
        return self.send_json({"ok": True, "imported": n})

    # -- printable pages
    def _mill_header(self, con):
        name = meta_get(con, "mill_name", APP_NAME)
        phone = meta_get(con, "mill_phone")
        addr = meta_get(con, "mill_address")
        logo = ""
        if meta_get(con, "mill_logo_b64"):
            logo = ("<img src='/branding/logo?v=%s' alt='' "
                    "style='height:46px;max-width:220px;object-fit:contain'>"
                    % htmlesc(meta_get(con, "mill_logo_ver", "0")))
        acc = ACCENT_HEX.get(meta_get(con, "theme_color", "green") or "green", "#0c7a4e")
        return ("<div class='band' style='background:%s'>%s"
                "<div class='bname'>%s</div>"
                "<div class='bsub'>%s %s</div></div>"
                % (acc, logo, htmlesc(name), htmlesc(phone), htmlesc(addr)))

    def _mill_header_compact(self, con):
        # Narrow per-column variant of _mill_header for the multi-copy
        # voucher (bank-challan columns): the SAME branding fields —
        # accent colour, logo, mill name, phone, address — sized for a
        # ~64-96mm column, so every cut-apart copy carries the full
        # mill header on its own and the multi-copy page needs no
        # once-per-page band at all.
        name = meta_get(con, "mill_name", APP_NAME)
        phone = meta_get(con, "mill_phone")
        addr = meta_get(con, "mill_address")
        logo = ""
        if meta_get(con, "mill_logo_b64"):
            logo = ("<img src='/branding/logo?v=%s' alt='' "
                    "style='height:22px;max-width:110px;object-fit:contain'>"
                    % htmlesc(meta_get(con, "mill_logo_ver", "0")))
        acc = ACCENT_HEX.get(meta_get(con, "theme_color", "green") or "green", "#0c7a4e")
        return ("<div class='cband' style='background:%s'>%s"
                "<div class='cbname'>%s</div>"
                "<div class='cbsub'>%s %s</div></div>"
                % (acc, logo, htmlesc(name), htmlesc(phone), htmlesc(addr)))

    def print_page(self, path, q=None):
        u = self.user()
        if not u:
            return self.send_text("<p>Please log in first.</p><a href='/'>Open the system</a>", code=401)
        q = q or {}
        unit = (q.get("u", ["t"])[0] or "t").lower()
        if unit not in ("t", "kg", "maund"):
            unit = "t"
        if u["role"] == "staff":
            need = ("vehicles" if path.startswith("/print/trip/")
                    else "parties" if path.startswith("/print/party/")
                    else "trade" if path.startswith("/print/invoice/")
                    else "reports")
            if not perm_ok(u, need):
                return self.send_text("not allowed", code=403)
        con = get_db()
        try:
            head = self._mill_header(con)
            _fs = font_settings(con)
            _stack = FONT_STACKS.get(_fs["print_font"], FONT_STACKS["default"])
            _psz = {"small": ("12px", "11.5px"), "normal": ("13.5px", "13px"),
                    "large": ("15.5px", "15px")} [_fs["print_text_size"]]
            _bold = "" if _fs["print_bold_headings"] else "th,h2,h3{font-weight:400}"
            css = ("<style>"
                   "body{font-family:%s;margin:0;color:#111;font-size:%s}"
                   "@page{size:A4;margin:13mm}"
                   ".band{color:#fff;padding:10px 14px;border-radius:6px;text-align:center;margin-bottom:12px}"
                   ".band img{background:#fff;border-radius:4px;padding:2px}"
                   ".bname{font-size:22px;font-weight:bold}"
                   ".bsub{font-size:12px;opacity:.92}"
                   "table{border-collapse:collapse;width:100%%}"
                   "td,th{border:1px solid #9a9a9a;padding:5px 8px;font-size:%s;text-align:right}"
                   "td:first-child,th:first-child{text-align:left}"
                   "th{background:#eef3f0}"
                   ".tot{background:#eef3f0;border-top:2px solid #333;padding:6px 8px}"
                   ".slipwrap{max-width:150mm;margin:0 auto;border:1px solid #bbb;padding:14px}"
                   ".sliphead{display:flex;align-items:center;gap:10px;margin-bottom:8px}"
                   ".sliptitle{flex:1;min-width:0}"
                   ".sliptitle h2{margin:0;text-align:center}"
                   ".slipqr{flex:none;line-height:0}"
                   ".slipqr svg{width:76px;height:76px}"
                   ".slipfoot{margin-top:14px;border-top:1px solid #999;padding-top:8px}"
                   ".sigs{display:flex;justify-content:space-between;margin-top:36px;gap:40px}"
                   ".sig{flex:1;border-top:1px solid #333;padding-top:4px;font-size:12px;text-align:center}"
                   ".pfoot{margin-top:16px;font-size:11px;color:#555;text-align:center;border-top:1px solid #ccc;padding-top:6px}"
                   "%s"
                   "@media print{button{display:none}body{margin:0}}"
                   "</style>"
                   "<button onclick='window.print()'>Print / Save PDF</button>"
                   % (_stack, _psz[0], _psz[1], _bold))
            foot = ("<div class='pfoot'>Computer generated · %s · %s</div>"
                    % (htmlesc(meta_get(con, "mill_name", APP_NAME)), now_str()))
            sigs = ("<div class='sigs'><div class='sig'>Prepared by</div>"
                    "<div class='sig'>Received by</div></div>")
            if path.startswith("/print/party/"):
                pid = int(path.split("/")[3])
                if u["role"] == "client" and u.get("party_id") != pid:
                    return self.send_text("not allowed", code=403)
                p = con.execute("SELECT * FROM parties WHERE id=?", (pid,)).fetchone()
                if not p:
                    return self.send_text("not found", code=404)
                entries, bal = party_ledger(con, pid)
                st = party_stock(con, pid)
                rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                               % (e["date"], htmlesc(e["desc"]), (format(e["debit"], ",.0f")) if e["debit"] else "",
                                  (format(e["credit"], ",.0f")) if e["credit"] else "", format(e["balance"], ",.0f"))
                               for e in entries)
                html = (css + head + "<h2>Khata — %s</h2>"
                        "<p>Phone: %s | Roles: %s</p>"
                        "<p>Stock: rock waiting %s, powder ready %s / %d bags</p>"
                        "<table><tr><th>Date</th><th>Detail</th><th>Debit (dena)</th>"
                        "<th>Credit (lena)</th><th>Balance</th></tr>%s</table>"
                        "<h3 class='tot'>Net Balance: Rs %s (%s)</h3>"
                        % (htmlesc(p["name"]), htmlesc(p["phone"] or ""), htmlesc(p["roles"] or ""),
                           fmt_weight(st["rock_waiting_t"] * 1000, unit),
                           fmt_weight(st["powder_ready_t"] * 1000, unit), st["bags_ready"],
                           rows, format(bal, ",.0f"),
                           ("To Receive" if bal > 0 else "To Pay" if bal < 0 else "Clear")))
                return self.send_text(html + foot, ctype="text/html; charset=utf-8")
            if path == "/print/phosphate-detail":
                if u["role"] == "client":
                    return self.send_text("not allowed", code=403)
                ds = (q.get("date", [today()])[0] or today())
                pd = phosphate_detail(con, ds)
                wlab = ("%g%% Wastage" % pd["wastage_pct"])
                unspec = ("<p style='font-size:11px'>%d bags had no shift time — counted in the totals, not in Day or Night.</p>"
                          % pd["bags_unclassified"]) if pd["bags_unclassified"] else ""
                brows = "".join(
                    "<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                    % (htmlesc(r["party"]), fmt_weight(r["rock_in_t"] * 1000, unit),
                       r["bags_day"], r["bags_night"],
                       fmt_weight(r["powder_t"] * 1000, unit),
                       fmt_weight(r["dispatched_t"] * 1000, unit),
                       fmt_weight(r["powder_balance_t"] * 1000, unit))
                    for r in pd["rows"])
                sidenotes = unspec
                if pd["adj_bags"]:
                    sidenotes += ("<p style='font-size:11px'>Ginti adjustment: %+d bags "
                                  "(included in Balance Powder).</p>" % pd["adj_bags"])
                if pd["bought_bags"]:
                    sidenotes += ("<p style='font-size:11px'>Powder bought: %d bags "
                                  "(included in Balance Powder).</p>" % pd["bought_bags"])
                html = (css + head + "<h2 style='text-align:center'>Phosphate Detail — %s</h2>"
                        "<table><tr><th>Rock In</th>"
                        "<th>Total Rock in Tons</th><th>Day</th><th>Night</th>"
                        "<th>%s</th><th>Powder In Ton</th><th>Previous Powder in Tons</th>"
                        "<th>Dispatched</th>"
                        "<th>Balance Powder</th><th>Balance Rock In Tons</th><th>Remarks</th></tr>"
                        "<tr><td>%s</td>"
                        "<td>%s<br><span style='font-size:10px'>(Prev %s + Rock In %s)</span></td>"
                        "<td>%d</td><td>%d</td>"
                        "<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr></table>"
                        "%s"
                        "<h3>Per-Party Detail</h3>"
                        "<table><tr><th>Party</th><th>Rock In</th><th>Day Bags</th><th>Night Bags</th>"
                        "<th>Powder</th><th>Dispatched</th><th>Powder Balance</th></tr>%s</table>"
                        "<p style='font-size:11px'>Balance Rock = Total Rock − (Powder + Wastage). "
                        "Balance Powder = Previous Powder + Powder made − Dispatched; it matches the Warehouse balance.</p>"
                        % (ds, wlab,
                           fmt_weight(pd["rock_in_t"] * 1000, unit),
                           fmt_weight(pd["total_rock_t"] * 1000, unit),
                           fmt_weight(pd["total_stock_rock_t"] * 1000, unit),
                           fmt_weight(pd["rock_in_t"] * 1000, unit),
                           pd["bags_day"], pd["bags_night"],
                           fmt_weight(pd["wastage_t"] * 1000, unit),
                           fmt_weight(pd["powder_in_t"] * 1000, unit),
                           fmt_weight(pd["prev_powder_t"] * 1000, unit),
                           fmt_weight(pd["dispatched_t"] * 1000, unit),
                           fmt_weight(pd["balance_powder_t"] * 1000, unit),
                           fmt_weight(pd["balance_rock_t"] * 1000, unit),
                           htmlesc(pd["remark"] or ""), sidenotes, brows))
                html += sigs
                return self.send_text(html + foot, ctype="text/html; charset=utf-8")
            if path == "/print/pnl":
                if u["role"] == "client":
                    return self.send_text("not allowed", code=403)
                month = today()[:7]
                p = pnl(con, month)
                _lines = [("Grinding income", p["grinding_income"]), ("Sales income", p["sales_income"]),
                          ("Purchases (own rock)", p["purchases"]), ("Expenses (ledger)", p["expenses"]),
                          ("Worker payouts", p["worker_payouts"]), ("Maintenance", p["maintenance"]),
                          ("Freight (mill)", p["freight_mill"]), ("Loading/Unloading (mill)", p["loading_mill"]),
                          ("Vehicle rent to driver (cash)", p["rent_mill"])]
                body = "".join("<tr><td>%s</td><td>%s</td></tr>" % (htmlesc(k), format(v, ",.0f")) for k, v in _lines)
                html = (css + head + "<h2>Profit &amp; Loss — %s</h2><table>%s</table>"
                        "<h3 class='tot'>Total Income: Rs %s | Total Cost: Rs %s | NET PROFIT: Rs %s</h3>"
                        % (month, body, format(p["income"], ",.0f"), format(p["costs"], ",.0f"),
                           format(p["profit"], ",.0f")))
                return self.send_text(html + foot, ctype="text/html; charset=utf-8")
            if path.startswith("/print/trip/"):
                if u["role"] == "client":
                    return self.send_text("not allowed", code=403)
                tid = int(path.split("/")[3])
                t = con.execute("SELECT * FROM trips WHERE id=?", (tid,)).fetchone()
                if not t:
                    return self.send_text("not found", code=404)
                pname = "Own / Apna"
                if t["party_id"]:
                    pr = con.execute("SELECT name FROM parties WHERE id=?", (t["party_id"],)).fetchone()
                    pname = pr["name"] if pr else pname
                qr = qr_svg("MILL|TRIP|%d|%s|%s|%.0fKG|%s" % (tid, t["direction"], t["vehicle_no"], t["net_kg"], t["date"]))
                # voucher tail, in this order: Verified by (entry user +
                # role), the mill name, and the legal line last — it
                # replaces the signature blanks for this slip.
                _mill = meta_get(con, "mill_name", APP_NAME)
                _role = _user_role(con, t["entered_by"] or "")
                tail = ("<div class='slipfoot'>"
                        "<p>Verified by: %s%s</p>"
                        "<p style='text-align:center;font-size:15px'><b>%s</b></p>"
                        "<p style='text-align:center'>%s</p></div>"
                        % (htmlesc(t["entered_by"] or "-"),
                           (" (%s)" % htmlesc(_role)) if _role else "",
                           htmlesc(_mill), LEGAL_LINE))
                extra = ""
                if t["direction"] == "IN" and float(t["rock_rate"] or 0) > 0:
                    extra += ("<tr><th>Rock purchase</th><td>%s @ Rs %g (%s) = <b>Rs %s</b></td></tr>"
                              % (fmt_weight(t["net_kg"], unit), t["rock_rate"],
                                 "mine rate" if t["rate_type"] == "mine" else "factory ponch rate",
                                 format(t["net_kg"] / 1000.0 * float(t["rock_rate"]), ",.0f")))
                    if t["rate_type"] == "mine" and float(t["rent"] or 0) > 0:
                        if (t["rent_to"] or "seller") == "driver":
                            extra += ("<tr><th>Vehicle rent to driver</th><td>Rs %s (cash)</td></tr>"
                                      % format(float(t["rent"]), ",.0f"))
                        else:
                            extra += ("<tr><th>Vehicle rent</th><td>Rs %s</td></tr>"
                                      % format(float(t["rent"]), ",.0f"))
                if t["direction"] == "OUT" and float(t["grind_charge"] or 0) > 0:
                    extra += ("<tr><th>Grinding charge</th><td>%s @ Rs %g = <b>Rs %s</b></td></tr>"
                              % (fmt_weight(t["net_kg"], unit), t["grind_rate"],
                                 format(float(t["grind_charge"]), ",.0f")))
                if t["direction"] == "OUT" and _trip_sale_amount(t) > 0:
                    # Own-dispatch sale recorded on this trip: one more
                    # row inside the repeated slip, so it prints on
                    # every copy in both the single and column layouts
                    _sbn = con.execute("SELECT name FROM parties WHERE id=?",
                                       (t["sale_buyer_id"],)).fetchone()
                    extra += ("<tr><th>Sold to</th><td>%s @ Rs %g /ton = <b>Rs %s</b></td></tr>"
                              % (htmlesc(_sbn["name"] if _sbn else "?"),
                                 float(t["sale_rate"]),
                                 format(_trip_sale_amount(t), ",.0f")))
                dphone_row = (("<tr><th>Driver Phone</th><td>%s</td></tr>"
                               % htmlesc(t["driver_phone"])) if t["driver_phone"] else "")
                buyfrom_row = ""
                if t["buy_from_party_id"] and int(t["buy_from_party_id"]) != (t["party_id"] or 0):
                    _bfr = con.execute("SELECT name FROM parties WHERE id=?",
                                       (t["buy_from_party_id"],)).fetchone()
                    if _bfr:
                        buyfrom_row = ("<tr><th>Bought from</th><td>%s</td></tr>"
                                       % htmlesc(_bfr["name"]))
                # Bags print only on a dispatch voucher — an IN gate
                # pass is a weighed arrival, it has no Bags row at all.
                bags_row = (("<tr><th>Bags</th><td>%d</td></tr>" % t["bags"])
                            if t["direction"] == "OUT" else "")
                # The QR rides in the slip header (title block + QR
                # at the far end) — Talha's order 2026-10-28: below
                # the table it wasted a whole row of the sheet. Every
                # copy keeps its OWN QR (copies are cut apart; the
                # Driver Copy leaves with the driver), so the QR is
                # part of the repeated slip, never of the page band.
                slip = ("<div class='sliphead'><div class='sliptitle'>"
                        "<h2>VEHICLE VOUCHER / GATE PASS #%d — %s</h2></div>"
                        "<div class='slipqr'>%s</div></div>"
                        "<table><tr><th>Date</th><td>%s</td></tr>"
                        "<tr><th>Party</th><td>%s</td></tr>%s"
                        "<tr><th>Vehicle</th><td>%s</td></tr>"
                        "<tr><th>Driver</th><td>%s</td></tr>%s"
                        "<tr><th>Net Weight</th><td><b>%s</b></td></tr>"
                        "%s"
                        "<tr><th>Grade</th><td>%g%%</td></tr>%s</table>"
                        % (tid, t["direction"], qr, t["date"], htmlesc(pname), buyfrom_row,
                           htmlesc(t["vehicle_no"]),
                           htmlesc(t["driver"] or ""), dphone_row, fmt_weight(t["net_kg"], unit),
                           bags_row, t["grade_pct"], extra))
                slip += tail
                # Font & Print -> print_voucher_copies (default 2): the
                # slip repeats N times on ONE A4 sheet as bank-challan
                # COLUMNS side by side (never stacked — stacking spilled
                # to a 2nd page on a real printer), each column fully
                # self-contained: copy label (Driver / Office / Client,
                # in the print language), the compact mill band, then
                # the slip (title + header QR, table, Verified-by
                # tail). The once-per-page band is dropped here — the
                # per-column bands carry the same branding. 1 copy
                # keeps the classic single-slip page, band included.
                _nc = _fs["print_voucher_copies"]
                if _nc <= 1:
                    html = css + head + "<div class='slipwrap'>" + slip + "</div>"
                else:
                    _lang = (q.get("lang", ["en"])[0] or "en").lower()
                    if _lang not in VOUCHER_COPY_LABELS:
                        _lang = "en"
                    _labels = VOUCHER_COPY_LABELS[_lang]
                    _cband = self._mill_header_compact(con)
                    _blocks = "".join(
                        "<div class='vcol%s'><div class='slipwrap'>"
                        "<span class='copylabel'>%s</span>%s%s</div></div>"
                        % (" cut" if _i else "", _labels[_i], _cband, slip)
                        for _i in range(_nc))
                    html = (css + VOUCHER_PRINT_CSS
                            + "<div class='vcols copies%d'>" % _nc
                            + _blocks + "</div>")
                return self.send_text(html + foot, ctype="text/html; charset=utf-8")
            if path.startswith("/print/invoice/"):
                if u["role"] == "client":
                    return self.send_text("not allowed", code=403)
                sid = int(path.split("/")[3])
                s = con.execute("SELECT * FROM sales WHERE id=?", (sid,)).fetchone()
                if not s:
                    return self.send_text("not found", code=404)
                pr = con.execute("SELECT * FROM parties WHERE id=?", (s["party_id"],)).fetchone()
                qr = qr_svg("MILL|INV|%s|%.0f" % (s["invoice_no"], s["amount"]))
                _sit = s["item"] or "powder"
                if _sit == "other":
                    _idesc = htmlesc(s["item_name"] or "Item")
                    _iwt = "%g %s" % (s["qty"] or 0, htmlesc(s["unit"] or ""))
                    _ibags = "-"; _irate = format(s["unit_rate"] or 0, ",.0f")
                elif _sit == "rock":
                    _idesc = "Phosphate Rock"
                    _iwt = fmt_weight(s["tons"] * 1000, unit)
                    _ibags = "-"; _irate = format(s["rate_per_ton"], ",.0f")
                else:
                    _idesc = "Phosphate Powder"
                    _iwt = fmt_weight(s["tons"] * 1000, unit)
                    _ibags = "%d" % s["bags"]; _irate = format(s["rate_per_ton"], ",.0f")
                html = (css + head +
                        "<h2 style='text-align:center'>SALES INVOICE %s</h2>"
                        "<p>Buyer: %s | Date: %s</p>"
                        "<table><tr><th>Item</th><th>Weight</th><th>Bags</th><th>Rate</th><th>Amount</th></tr>"
                        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr></table>"
                        "<h3 class='tot'>Total: Rs %s</h3>"
                        "<div style='text-align:center'>%s</div>"
                        % (htmlesc(s["invoice_no"] or ""), htmlesc(pr["name"] if pr else ""),
                           s["date"], _idesc, _iwt, _ibags, _irate,
                           format(s["amount"], ",.0f"), format(s["amount"], ",.0f"), qr))
                html += sigs
                return self.send_text(html + foot, ctype="text/html; charset=utf-8")
            return self.send_text("not found", code=404)
        finally:
            con.close()



class DeviceH(BaseHTTPRequestHandler):
    """LAN listener for fingerprint devices (ZKTeco ADMS/iclock style).
    Accepts ONLY /iclock/* from registered device serials. No UI, no data
    reading - devices can only PUSH attendance punches in."""
    server_version = "MillDevice/1.0"

    def log_message(self, *a):
        pass

    def _reply(self, text, code=200):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _device(self, sn):
        if not db_path() or not os.path.exists(db_path()):
            return None
        con = get_db()
        try:
            return con.execute("SELECT * FROM biometric_devices WHERE serial=?", (sn,)).fetchone()
        finally:
            con.close()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        q = parse_qs(parsed.query)
        sn = (q.get("SN", [""])[0]).strip()
        if path not in ("/iclock/cdata", "/iclock/getrequest", "/iclock/ping"):
            return self._reply("not found", 404)
        dev = self._device(sn)
        if not dev:
            return self._reply("error: device not registered", 403)
        con = get_db()
        try:
            con.execute("UPDATE biometric_devices SET last_seen=? WHERE serial=?", (now_str(), sn))
            con.commit()
        finally:
            con.close()
        if path == "/iclock/cdata":
            return self._reply(
                "GET OPTION FROM: %s\nStamp=0\nOpStamp=0\nPhotoStamp=0\n"
                "ErrorDelay=30\nDelay=10\nTransTimes=00:00;23:59\nTransInterval=1\n"
                "TransFlag=1111000000\nTimeZone=5\nRealtime=1\nEncrypt=None\n" % sn)
        return self._reply("OK")

    def do_POST(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        sn = (q.get("SN", [""])[0]).strip()
        table = (q.get("table", [""])[0]).upper()
        if parsed.path != "/iclock/cdata":
            return self._reply("not found", 404)
        dev = self._device(sn)
        if not dev:
            return self._reply("error: device not registered", 403)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8", "replace") if n else ""
        if table != "ATTLOG":
            return self._reply("OK")
        con = get_db()
        try:
            stamp = now_str()
            con.execute("UPDATE biometric_devices SET last_seen=?, last_punch=? WHERE serial=?",
                        (stamp, stamp, sn))
            for line in raw.strip().splitlines():
                parts = line.replace("\t", " ").split()
                if len(parts) < 2:
                    continue
                code = parts[0]
                ptime = parts[1] + (" " + parts[2] if len(parts) > 2 and ":" in parts[2] else "")
                con.execute("INSERT INTO device_punches(device_serial,device_code,punch_time,raw)"
                            " VALUES(?,?,?,?)", (sn, code, ptime, line[:300]))
                w = con.execute("SELECT * FROM workers WHERE device_code=?", (code,)).fetchone()
                if w:
                    date_str = ptime[:10]
                    hm = ptime[11:16] if len(ptime) >= 16 else ""
                    row = con.execute("SELECT * FROM attendance WHERE worker_id=? AND date=?",
                                      (w["id"], date_str)).fetchone()
                    if row is None:
                        ot = compute_overtime(con, w, date_str, hm, "")
                        con.execute("INSERT INTO attendance(worker_id,date,present,check_in,overtime_hours)"
                                    " VALUES(?,?,1,?,?)", (w["id"], date_str, hm, ot))
                    else:
                        ci = row["check_in"] or hm
                        co = row["check_out"] or hm
                        if hm and hm < ci:
                            ci = hm
                        if hm and hm > co:
                            co = hm
                        ot = compute_overtime(con, w, date_str, ci, co)
                        con.execute("UPDATE attendance SET present=1, check_in=?, check_out=?, overtime_hours=?"
                                    " WHERE id=?", (ci, co, ot, row["id"]))
            con.commit()
        finally:
            con.close()
        return self._reply("OK")

def main():
    cfg = load_config()
    port = int(os.environ.get("MILL_PORT", "8765"))
    last_err = None
    for cand in range(port, port + 15):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", cand), H)
            MAIN_PORT[0] = cand
            break
        except OSError as e:
            last_err = e
    else:
        raise SystemExit("No free port: %s" % last_err)
    # biometric LAN listener on a separate port (0.0.0.0 so factory devices
    # on the local network can push punches; only /iclock/* paths exist and
    # unregistered device serials are refused)
    dev_srv = None
    try:
        dev_srv = ThreadingHTTPServer(("0.0.0.0", MAIN_PORT[0] + DEVICE_PORT_OFFSET), DeviceH)
        threading.Thread(target=dev_srv.serve_forever, daemon=True).start()
    except OSError as e:
        print("Biometric listener could not start: %s" % e)
    url = "http://127.0.0.1:%d/" % MAIN_PORT[0]
    print("=" * 60)
    print("%s — PC Edition (FULL)" % APP_NAME)
    print("System chal raha hai:  %s" % url)
    print("Biometric device address (factory LAN): http://%s:%d/iclock/cdata"
          % (lan_ip(), MAIN_PORT[0] + DEVICE_PORT_OFFSET))
    print("Band karne ke liye ye window band kar dein (Ctrl+C).")
    print("=" * 60)
    if not cfg.get("db_path"):
        print("Pehli dafa: browser mein setup chalega — data folder chunein aur owner login banayein.")
    if os.environ.get("MILL_NO_BROWSER") != "1":
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nBand ho raha hai...")


if __name__ == "__main__":
    main()
