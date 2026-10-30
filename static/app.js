// Phosphate Grinding Mill System — PC Edition (FULL PARITY)
// Single-page UI. 3 languages (en / ur RTL / hi), dark+light, voice entry,
// attachments, AI assistant, biometric, alerts — all against the local API.
const appEl = document.getElementById('app');
let STATE = { configured: false, user: null, mill: {}, backup_days: null,
              device_port: null, lan_ip: null, unread: 0 };
let PREFS = { lang: localStorage.getItem('mill_lang') || 'en',
              theme: localStorage.getItem('mill_theme') || 'light',
              unit: localStorage.getItem('mill_unit') || 't' };
let VIEW = 'dashboard';
let CACHE = { parties: [], workers: [], departments: [], heads: [], settings: null };

/* ---------------- i18n ---------------- */
const I18N = {
en: { app:'Phosphate Grinding Mill', sys_tag:'Management System', dashboard:'Dashboard', guide:'Step-by-Step Guide',
  parties:'Parties', vehicles:'Vehicles / Weighbridge', vehicle_in:'Vehicle In', vehicle_out:'Vehicle Out', grinding:'Grinding',
  production:'Production', grind_prod:'Grinding & Production', warehouse:'Warehouse', owntrade:'Own Trade',
  orders:'Powder Orders', workers:'Workers', departments:'Departments', attendance:'Attendance',
  leaves:'Leave & Approvals', money:'Money', payments:'Payments', expenses:'Expense Ledger',
  cashbook:'Cash Book', cashinhand:'Cash in Hand', cheques:'Cheque Register', reports:'Reports (P&L)', alerts:'Alerts',
  assistant:'AI Assistant', data:'Data — Import / Export / Backup', logins:'Logins & Users',
  settings:'Settings', help:'Help', logout:'Logout', save:'Save', add:'Add', del:'Delete',
  edit:'Edit', search:'Search…', balance:'Balance', to_receive:'To Receive', to_pay:'To Pay', bal_clear:'Clear', calc_l:'Calculator', calc_quick_l:'Mill quick hisaab', calc_bags_tons_l:'Bags → Tons', calc_tons_rate_l:'Tons × Rate', calc_gross_tare_l:'Gross − Tare', calc_tons_l:'Tons', calc_rate_ton_l:'Rate /ton',
  date:'Date', party:'Party', vehicle:'Vehicle', driver:'Driver', gross:'Gross', tare:'Tare',
  net:'Net', bags:'Bags', grade:'Grade %', rate:'Rate', amount:'Amount', note:'Note',
  direction:'Direction', kind:'Kind', local:'Local', export:'Export', today:'Today',
  voice:'🎤 Voice', voice_hint:'Chrome browser needed for voice. It only FILLS the form — check and press Save yourself.',
  now_grinding:'Now Grinding', own_stock:'Own Stock', rock:'Rock', powder:'Powder',
  bardana:'Bardana (empty bags)', low:'LOW', print:'Print', restore:'Restore',
  login:'Login', username:'Username', password:'Password', welcome:'Welcome',
  first_steps:'No data yet — start with Step 1: add your first party (client / supplier / buyer), then record your first Vehicle In entry. Your stock, balances and today\u2019s figures will appear here.',
  language:'Language', theme:'Theme', unit:'Unit', dark:'Dark', light:'Light',
  client_view:'My Ledger', upload_proof:'Upload Payment Proof', pending:'Pending',
  confirmed:'Confirmed', rejected:'Rejected', generated:'Generate weekly reminders',
  send:'Send', status:'Status', worker:'Worker', present:'Present', checkin:'Check-in',
  checkout:'Check-out', overtime:'Overtime', hours:'Hours', method:'Method', cash:'Cash',
  bank:'Bank', online:'Online', cheque:'Cheque', description:'Description',
  g_factory:'🏭 Factory Management', g_accounts:'💰 Accounts', g_workers:'👷 Workers & Attendance', g_system:'⚙️ Setup & System',
  recycle:'Recycle / Deleted Entries',
  mill_profile:'Mill Profile', mill_profile_hint:'This name and detail appear on the app header, the login screen, printed ledger, weigh slip / gate pass and invoices. Change it here any time.',
  ai_placeholder:'Ask a question…', ai_drag:'Drag me anywhere', outside_grinding:'Outside Grinding', trade_history_l:'Trade History', trade_l:'Trade', add_buy_l:'Add Buy', add_sell_l:'Add Sell', item_l:'Item', item_rock_l:'Phosphate Rock', item_powder_l:'Powder', item_other_l:'Other Item', item_name_l:'Item Name', qty_l:'Quantity', unit_l:'Unit', unit_rate_l:'Rate / unit', choose_item_l:'Step 1 — choose the item', src_l:'Source', src_gate_l:'Gate', src_ledger_l:'Ledger', src_excel_l:'Excel', src_direct_l:'Direct', direct_trade_l:'Direct Trade', add_direct_l:'Add Direct Trade', sell_to_l:'Sell to', buy_rate_l:'Buy rate', sell_rate_l:'Sell rate', profit_l:'Profit', loss_l:'Loss', direct_note_l:'Goods never enter the factory — no stock moves, only the two parties khatas.', ledger_note_l:'Goods that moved without a gate record — stock comes in / goes out from this entry.', sale_section_l:'Powder sale (own stock) — optional', sale_rate_l:'Sale rate /ton', sale_hint_l:'Own dispatch only: fill BOTH fields to record the sale on this trip — the receivable (net tons × rate) posts in the buyer khata from this trip, exactly once. Do NOT enter the same sale again in the Ledger. Leave both blank for a plain dispatch.', sold_to_l:'Powder sold to', dup_warn_t:'Possible duplicate sale', dup_anyway_l:'Confirm — separate sale', dup_trip_l:'This powder was already sold to {buyer} on the Vehicle Out trip of {date} (vehicle {vehicle}, {tons} @ Rs {rate}/ton). If this entry is the SAME sale again, press Cancel — if it is a separate sale, Confirm.', dup_sell_l:'A Ledger sale of {tons} @ Rs {rate}/ton to {buyer} is already recorded on {date}. If this dispatch is THAT sale, press Cancel and clear the buyer/rate here — if it is a separate sale, Confirm.', rock_sent_l:'Rock Sent', powder_back_l:'Powder Produced', outside_mill_l:'Outside Mill', sent_t_l:'Rock sent', charges_l:'Grinding charges', powder_bought_l:'Powder bought', rock_sold_l:'Rock sold', outside_sent_l:'Sent out for grinding', outside_recv_l:'Powder at outside mills', c_outside:'Outside grinding', src_outside_l:'Outside', og_bill_l:'Grinding Bill', add_bill_l:'Add Grinding Bill', powder_ground_l:'Powder ground (bags)', rock_used_l:'Rock used', rock_rate_l:'Rock rate /ton', paid_now_l:'Paid now', remaining_l:'Rock remaining there', ground_l:'Rock ground', powder_left_l:'Powder left there', og_sold_l:'Powder sold', og_charges_l:'Grinding charges (we pay)', og_overview_l:'All factories', from_mine_l:'From mine / seller', sold_from_l:'Sold from this factory', de_gate_purch_l:'Purchases at gate (Vehicle In)', de_grind_earned_l:'Grinding earned', de_gate_sales_l:'Sales at gate (Vehicle Out)', de_trade_purch_l:'Own purchases (ledger / Excel)', de_trade_sales_l:'Own sales (ledger / Excel)', de_direct_l:'Direct trades (profit)', de_payments_l:'Payments in / out', de_handovers_l:'Cash handovers', de_payouts_l:'Worker payouts', de_attendance_l:'Workers present', ai_which_party:'Which party do you mean? Pick one:', deal_saved:'Direct trade saved', outside_saved:'Outside grinding saved',
  sa_title:'Production Entry Pending', sa_body:'The production entry for the {shift} shift ({date}) has not been recorded yet. Please enter the number of bags produced.', sa_enter:'Enter Now', sa_later:'Later', sa_closed_btn:'Factory Closed', sa_closed_t:'Factory Closed — No Production', sa_reason_technical:'Technical issue / factory closed', sa_reason_power:'Power outage', sa_note_ph:'Note (optional)', sa_closed_saved:'Closure recorded — no production for this shift', closed_l:'Factory closed', shift_closures_l:'Factory closures (no production)', day_shift_end_l:'Day shift ends at', night_shift_end_l:'Night shift ends at', vehicle_alert_time_l:'Vehicle alerts after (daily review)', va_in_t:'No Vehicle Arrivals Recorded Today', va_in_b:'No vehicle arrival has been recorded at the factory so far today. If a vehicle has arrived, please record its entry.', va_out_t:'No Vehicle Departures Recorded Today', va_out_b:'No loaded vehicle departure has been recorded from the factory so far today. If a vehicle has left, please record its departure.', va_ok:'OK, understood',
  fc_running:'Factory Running', fc_closed:'Factory Closed', fc_banner_txt:'Factory is closed — {reason} · since {date}', fc_days:'day(s)', fc_close_t:'Mark Factory Closed', fc_from_l:'Closed from', fc_to_l:'Expected reopen date (optional)', fc_reason_l:'Reason', fc_r_power_outage:'Power outage', fc_r_breakdown:'Machine breakdown', fc_r_maintenance_work:'Maintenance / repair work', fc_r_no_material:'No raw material (rock)', fc_r_other:'Other', fc_rtext_ph:'Write the reason (required for Other)', fc_save_close:'Mark Closed', fc_reopen_btn:'Reopen Factory (Mark Running)', fc_closed_saved:'Factory marked closed', fc_reopened:'Factory is running again', fc_days_l:'Factory closed days', fc_was_closed_l:'Factory was closed', fc_only_om:'Only the Owner or Manager can change this.', fc_gate_l:'During closure: rock arrived {rock} · powder dispatched {pow}',
  ai_hint:'I answer only from your mill records — I never make up numbers. Ask e.g. "How many vehicles came today?", "What is the stock position?", "This month profit?", "Ahmed Traders balance?"',
  ai_try:'Try one of these:',
  guide_intro:'Follow these steps in order — first Step 1, then Step 2… Each card has a button that takes you straight to that section.',
  g_clients:'Clients', g_daily:'Daily Work', g_own:'Own Goods',
  quick:'Quick Actions', qa_in:'Vehicle In', qa_out:'Vehicle Out', qa_grind:'Grinding & Production',
  qa_bags:'Bags Entry', qa_payment:'Payment', qa_expense:'Expense', qa_client:'Add Client', qa_ledger:'Party Ledger',
  totals:'Totals', total_rock:'Total Rock in Factory', total_powder:'Total Powder', total_bags:'Total Bags',
  own_s:'Own', clients_s:'Clients', daily_progress:'Daily Progress', rock_in:'Rock In',
  cash_in:'Cash In', cash_out:'Cash Out', vs_yday:'vs yesterday',
  ageing_h:'Ageing 0-30 / 31-60 / 60+', recent_vehicles:'Recent Vehicles',
  no_session:'No session is running', own_opt:'Own (Mine)', over_credit:'Over credit limit',
  cheques_due:'Cheques due in the next 3 days', slip:'Slip', nothing_found:'Nothing found.',
  name_l:'Name', phone_l:'Phone', wa_same_l:'Same as Phone', roles_l:'Roles', supplier:'Supplier', buyer:'Buyer',
  credit_limit:'Credit Limit (Rs)', opening:'Opening Balance', open_date_l:'Account Opening Date', opened_l:'Account opened', owes_us:'Client owes us',
  owe_client:'We owe client', opening_hint:'Balance from before this system started',
  stock_l:'Stock', address_l:'Address', weight_l:'Weight', saved:'Saved \u2713', ledger:'Ledger',
  type_l:'Type', time_l:'Time', start_time:'Start Time', end_time:'End Time', source_l:'Source',
  entered_by:'Entered by', mill_bags:'Mill bags', client_bags_s:'Client export bags',
  stop_l:'Stop', start_l:'Start', close_l:'Close', invoice_l:'Invoice', booked_l:'Booked',
  fulfilled_l:'Fulfilled', remaining_l:'Remaining', machine_l:'Machine', detail_l:'Detail',
  channel_l:'Channel', cheque_no:'Cheque No', due_date:'Due Date', dispatch:'Dispatch',
  sale_l:'Sale', product_l:'Product', credit_l:'Credit', upload_l:'Upload',
  choose_file:'Choose a file first', khata_btn:'Ledger',
  proof_attach:'Proof / Attachment (image or PDF, max 5MB)',
  bags_packing:'Bags Packing', grinding_job:'Grinding Job', bag_source:'Bag Source',
  bags_made_l:'Bags made', bags_out_l:'Bags out', bags_ready_l:'Bags ready', bags_tons:'Bags weight',
  shift_l:'Shift', rock_lying:'Rock Lying in Factory', rock_bought:'Rock Bought',
  rock_ground:'Rock Ground', powder_lying:'Powder Lying', powder_made_l:'Powder Made',
  powder_sold:'Powder Sold', purchases_total:'Total Purchases', sales_total:'Total Sales',
  cpt:'Cost Per Ton', period:'Period', this_month:'This Month', last_month:'Last Month',
  custom:'Custom', tons_ground:'Tons Ground', total_expenses:'Total Factory Expenses',
  expense_per_ton:'Expense per Ton', grinding_income:'Grinding Income', income_per_ton:'Income per Ton',
  margin_per_ton:'Margin per Ton', by_head:'By Head', biz_summary:'Party Business Summary',
  biz_note:'Business done with each party — this is a summary, not a balance.',
  charges_l:'Loading / Other Charges', net_l:'Net',
  wa_khata:'\uD83D\uDCF2 Send Ledger on WhatsApp', wa_no_phone:'No phone number on file for this party',
  wa_owe:'Balance: party owes us', wa_weowe:'Balance: we owe the party',
  wa_last5:'Last 5 entries', wa_pay_numbers:'Our payment numbers',
  godam_ginti:'Stock Count (Godam Ginti)', counted_bags:'Counted Bags (physical)', book_bags:'Book Bags',
  difference:'Difference', shortage:'Shortage', excess:'Excess', count_save:'Save Count',
  adj_request:'Request Adjustment', adj_pending:'Adjustment pending owner approval',
  ginti_adj:'Ginti Adjustment', counts_history:'Counts History', adj_history:'Adjustments',
  approve:'Approve', reject:'Reject', pending_adj:'Pending stock adjustments',
  powder_ageing:'Old Powder Waiting', days_waiting:'days waiting',
  voice_alerts_t:'Voice Alerts', voice_master_l:'Voice alerts on', voice_vehicles_l:'Vehicle alerts', voice_payments_l:'Payment alerts',
  ev_in:"{party}'s vehicle has arrived", ev_out:"{party}'s vehicle has left with the load",
  ev_pay_in:'Payment received: Rs {amount} — {party}', ev_pay_out:'Payment sent: Rs {amount} — {party}',
  ev_exp_pending:'Large expense waiting for approval: Rs {amount} ({party})',
  missing_t:'Missing fields: ', fl_name:'Name', fl_party:'Party', fl_amount:'Amount', fl_vehicle:'Vehicle No',
  fl_weights:'Weights', fl_tons:'Tons', fl_rate:'Rate', fl_bags:'Bags', fl_head:'Main Head', fl_due:'Due Date',
  fl_net:'Net Weight', xl_pdf:'⬇ PDF', rate_type_l:'Rate type',
  grind_rate_l:'Grinding rate /ton (optional)', grind_charge_l:'Grinding charge',
  rock_purchase_l:'Rock purchase — if this rock was bought', rock_rate_l:'Rock rate /ton',
  factory_rate_l:'Factory ponch rate', mine_rate_l:'Mine rate', rent_l:'Vehicle rent (Rs)',
  buy_from_l:'Buy from (seller)', bought_from_l:'Bought from',
  rent_to_l:'Vehicle rent payable to', rent_seller_l:'Seller', rent_driver_l:'Driver (cash)',
  rent_mill_l:'Vehicle rent (mill)', c_rent:'Vehicle rent to driver (mill)',
  owner_only_edit:'Only the owner can edit or delete entries',
  editing_l:'✏️ Editing entry — fix the values and press Save changes',
  back_btn:'Back',
  driver_phone_l:'Driver phone', print_voucher_l:'Print voucher', wa_auto_sent:'Voucher auto-sent on WhatsApp ✓',
  wa_party_btn:'Send to the party on WhatsApp', wa_driver_btn:'Send to the driver on WhatsApp', wa_owner_btn:'Send to the owner on WhatsApp',
  fl_holder:'Holder', fl_counted:'Counted Amount', fl_date:'Date', fl_work:'Work', fl_machine:'Machine',
  fl_user:'Username', fl_pass:'Password', fl_role:'Role', fl_worker:'Worker',
  role_owner_l:'Owner', role_manager_l:'Manager', role_staff_l:'Staff', role_client_l:'Client', role_demo_l:'Demo (view-only)', demo_hint:'Demo login: demo / demo12345 — sirf dekhne ke liye', pnl_t:'Profit & Loss', pnl_income:'Income', pnl_costs:'Costs', pnl_net:'NET PROFIT', st_cleared:'Cleared', st_bounced:'Bounced',
  c_purchases:'Purchases (own rock)', c_expenses:'Expenses (ledger)', c_payouts:'Worker payouts', c_maint:'Maintenance', c_freight:'Freight (mill)', c_loading:'Loading (mill)',
  age_note:'Powder ready for longer than the limit set in Settings, still not dispatched',
  powder_age_days:'Powder age limit (days)',
  phos_detail:'Phosphate Detail', total_stock:'Total Stock', total_rock:'Total Rock',
  day_l:'Day', night_l:'Night', wastage_l:'Wastage', powder_in_l:'Powder In Ton',
  prev_powder_l:'Previous Powder', bal_powder_l:'Balance Powder', bal_rock_l:'Balance Rock', prev_rock_l:'Previous Rock',
  remarks_l:'Remarks', dispatched_l:'Dispatched', pd_breakdown:'Per-Party Detail', factory_l:'Factory',
  unspec_l:'Bags without shift time (counted in the totals only)', wastage_pct_l:'Wastage % (register)',
  pd_help:'Balance Powder = Previous Powder + Powder In − Dispatched — it matches the Warehouse balance. Balance Rock = Total Rock − (Powder + Wastage) — the register treats production as the rock consumption and runs day by day from the first record.',
  machines:'Machines', machine_name:'Machine Name', work_type:'Work Type', service:'Service',
  repair:'Repair', part_change:'Part Change', other_l:'Other', next_due:'Next Due Date',
  cost_l:'Cost (Rs)', maint_diary:'Machine Maintenance Diary', maint_due:'Machine maintenance due',
  overdue:'Overdue', add_machine:'Add Machine', maint_entry:'Maintenance Entry',
  linked_expense:'Expense Ledger entry',
    font_print_t:'Font & Print', ui_font_l:'System font', ui_size_l:'System text size',
  print_font_l:'Print font', print_size_l:'Print text size', print_bold_l:'Bold headings in print',
  print_copies_l:'Voucher copies per page',
  stock_avail_l:'Available powder stock', stock_warn_t:'Powder stock is low',
  stock_warn_msg:'Only {avail} of ground powder is in stock — you are sending out {net}. Save anyway?',
  stock_anyway_l:'Save anyway',
  font_default:'Default (System Sans)', font_serif:'Serif', font_rounded:'Rounded / Friendly',
  font_naskh:'Naskh (Noto Sans Arabic)', font_nastaliq:'Nastaliq (Noto Nastaliq Urdu)',
  size_small:'Small', size_normal:'Normal', size_large:'Large',
  demo_title:'Demo Data', demo_load:'Load Demo Data', demo_remove:'Delete All Demo Data',
  record:'Record', restored_ok:'Restored \u2713', debit:'Debit', waiting_l:'waiting', ready_l:'ready',
  open_view:'Open', download_file:'\u2B07 Download', reset_pw:'Reset password',
  edit_user_msg:'is being edited \u2014 change the role/access and press Save changes.',
  staff_note:'A staff login can use only the ticked items \u2014 the server blocks everything else too; the items are not merely hidden. A client login sees only its own ledger, stock and balance. The demo login (demo / demo12345) is public and view-only: it can look at the whole system and ask the assistant, but the server blocks every change, and Settings, Logins and Backup stay closed for it. 5 wrong passwords lock a login for 15 minutes.',
  staff_note_pc:'A staff login can use only the ticked items \u2014 the server blocks everything else too; the items are not merely hidden. 5 wrong passwords lock a login for 15 minutes.',
  backup_done:'Backup made \u2713', restore_done:'Restored \u2713 \u2014 safety backup:', restore_confirm:'Restore this backup? A safety backup is created automatically first.',
  import_done:'Import done \u2713', rows_l:'rows', no_backup:'\u2014 no backup yet', backup_folder_l:'Backup folder',
  last_backup_l:'Last backup', never_l:'never', days_ago_l:'days ago', table_l:'Table',
  paste_ph:'Paste the header row + data rows', preview_l:'Preview', columns_l:'columns',
  mill_name_l:'Mill name', mill_phone_l:'Mill phone', mill_addr_l:'Mill address', owner_wa_l:'Owner WhatsApp (for alerts)',
  logo_hint:'Logo file (PNG / JPG / WebP \u2014 resized to 256px automatically on upload)', logo_none:'No logo is set yet.',
  replace_logo:'Replace logo', upload_logo:'Upload logo', remove_l:'Remove', logo_pick:'Pick a logo file first',
  theme_note:'This colour applies to the whole system \u2014 header, buttons, sidebar and login screen \u2014 for every login of the mill.',
  wa_note:'Put the Meta WhatsApp Cloud API Phone Number ID and Access Token here and alerts send by themselves. First these 7 templates must be approved on Meta:',
  holder_limit_l:'Holder limit (Rs) \u2014 warning when one holder holds more cash than this',
  approval_limit_l:'Approval limit (Rs) \u2014 a manager/staff CASH expense above this needs owner approval',
  bank_open_hint:'Add banks in the bank list below first, then set the opening balance here.',
  db_file_l:'Database file', bio_addr_l:'Biometric address (write this on the machine)',
  backup_dir_l:'Backup folder', move_db_l:'Move the database to a new folder',
  help_1:'<b>Start:</b> double-click <span class=\"mono\">Start-Mill-System.bat</span>. The browser opens by itself. Do not close the black window while working.',
  help_2:'<b>From another phone/PC (factory WiFi):</b> the system runs on this PC; keep the data folder in a MEGA/Google Drive sync folder and the backup reaches the cloud by itself.',
  help_3:'<b>Biometric machine:</b> write the address shown on the Attendance page in the machine server settings, register its serial, give the worker a device code \u2014 punches arrive in attendance by themselves (the PC must be on).',
  help_4:'<b>WhatsApp auto-send:</b> get the 7 templates approved on Meta and put the Phone Number ID + Token in Settings. Otherwise use the wa.me buttons on the Alerts page.',
  help_4_pc:'<b>WhatsApp:</b> on PC, use the one-tap wa.me buttons on the Alerts page and in the party ledger \u2014 the message opens ready in WhatsApp.',
  help_5:'<b>Voice:</b> the mic button in Chrome \u2014 spoken words only fill the form, you press Save yourself.',
  help_6:'<b>Invoices:</b> every powder sale prints a clean invoice with the mill profile and logo — use the invoice button in the Sales list.',
  help_6_pc:'<b>Invoices:</b> every powder sale prints a clean invoice with the mill profile and logo — use the invoice button in the Sales list.',
  help_7:'<b>Backup:</b> back up from the Data page every week and keep the ZIP in MEGA/Drive. A safety backup is created automatically before any restore.',
  help_8:'<b>Mistake made?</b> delete the entry \u2014 the owner gets an alert and it can be restored from Recycle / Deleted Entries.',
  demo_loaded_msg:'Demo data loaded \u2713', demo_removed_msg:'Demo data deleted \u2713',
  demo_text:'Load sample data to see every feature working. All names start with DEMO. Delete it any time — your real data stays untouched.',
  xl_download:'\u2B07 Excel download', xl_sample:'\uD83D\uDCC4 Sample file',
  xl_upload:'\u2B06 Excel upload', xl_label:'Excel:',
  xl_fmt_title:'Excel Upload — Pehle Format Dekhein', xl_choose:'Choose file',
  xl_why:'This popup is shown so you can first see the sample format and prepare your old data in exactly this format. A file in the wrong format will be rejected or import wrongly — so match these columns before uploading.',
  xl_fmt_note:'The first row of your file must have exactly these column names, in this order. Write your data under them — the rows below are examples.',
  xl_also:'Old files with these extra columns also work:',
  deleted_entries:'Deleted Entries', notifications:'Notifications', audit_log:'Audit Log',
  owner_only_note:'Owner only.', all_read:'Mark all read',
  from_l:'From', to_l:'To', show:'Show',
  bags_suffix:'bags', rock_waiting:'Rock waiting', powder_ready:'Powder ready',
  grinding_loss:'Grinding loss', attachments:'Attachments',
  freight:'Freight', freight_payer:'Freight payer', loading:'Loading', unloading:'Unloading',
  load_payer:'Loading/Unloading payer', order_out:'Linked order', repeat_trip:'Repeat last trip',
  in_rock:'Rock In', out_powder:'Powder Out',
  saved_tare:'Saved tare found', vehicle_first:'Write the vehicle number first',
  no_old_trip:'No old trip found for this vehicle', filled_old:'Old trip details filled in',
  listening:'Listening… say the party name and the numbers.',
  heard:'Heard: ', check_save:'— form filled. Please check it and press Save.',
  voice_fail:'Voice entry did not work — Chrome and an internet connection are needed.',
  choose_folder_first:'Write the data folder first',
  server_down:'The server is not reachable — please refresh the page.',
  setup_intro:'First-time setup: choose the data folder (pick a place that syncs with MEGA / Google Drive for backup), then create the Owner login.',
  data_folder:'Data folder', mill_name_l:'Mill name', owner_wa:'Owner WhatsApp', start_btn:'Start',
  imp_title:'Excel Import - Preview', imp_rows:'rows found', imp_ok:'are fine', imp_dup:'duplicate',
  imp_wrong:'wrong', imp_note:'Duplicate records will NOT be added again and wrong rows will be skipped. Confirm to save only the fine rows.',
  imp_do:'Import', imp_done:'Import Complete', imp_added:'records added', imp_dup_skip:'duplicates (skipped)',
  imp_wrong_rows:'wrong rows', imp_none_bad:'No duplicate or wrong rows.', row_l:'Row',
  chip_ok:'fine', chip_dup:'duplicate', chip_bad:'wrong',
  summary_t:'Summary', search_t:'Search', own_word:'Own',
  backup_warn:'days since the last backup — take a one-click backup from the Data page and keep it in MEGA / Google Drive.',
  backup_warn_start:'Backup is', pend_exp_t:'Pending expense approvals',
  pend_exp_note:'Pending expenses are counted in P&L; rejecting removes them and the cash stays with the holder.',
  pend_adj_note:'Approving makes the book bags equal to the counted bags (a Ginti Adjustment entry is posted).',
  wa_card_note:'If WhatsApp Cloud API (Phone Number ID + token) is set in Settings, alerts send by themselves. Otherwise every alert has a one-tap wa.me button. If an SMS gateway is set, SMS is tried when WhatsApp fails. The status is written on every alert.',
  proofs_t:'Client payment proofs (confirmation pending)', confirm_pay:'Confirm (posts the payment)',
  view_proof:'view', when_l:'When', to_l2:'To', message_l:'Message',
  maint_sec:'Maintenance / Downtime', day_costs:'Day costs', diesel_l:'Diesel litres', elec_l:'Electricity units',
  day_cost_save:'Save day costs', maint_note:'Only daily quantities are recorded here, as a diary. The diesel / electricity AMOUNTS go in the Expense Ledger above, so nothing is counted twice in the P&L. Machine repairs and their costs belong in Machines → Maintenance Diary (they post to the ledger from there).',
  cost_note:'The expense ledger total is counted ONCE only. Diesel / electricity quantities are only for per-ton cost; amounts come from the ledger.',
  head_new:'Create a head', head_name:'Head name', head_parent:'Parent (for a sub-head)', head_add:'Add head',
  main_head:'Main head', sub_head:'Sub head', paid_by_l:'Paid by', paid_to_l:'Paid to',
  month_headwise:'This month, by head', paidto_wise:'By paid-to',
  chq_note:'If a cheque bounces, set the status to Bounced — the amount goes back onto the party balance automatically. Marking it Cleared changes nothing.',
  no_cheque:'- no cheque', bankbook_empty:'Add your banks in Settings — then every bank balance shows here, live.',
  opening_bal:'Opening balance', payments_in_bank:'Payments IN (bank)', payments_out_bank:'Payments OUT (bank)',
  expenses_bank:'Expenses (bank)', bank_balance:'Balance', txn_type:'Type', ref_chq:'Ref / Cheque',
  dayend_t:'Day-End Summary', vehicles_l:'Vehicles', ground_bags:'Ground / Bags', cash_net:'Cash net',
  expenses_l:'Expenses', send_dayend:'Send Day-End to Owner', excel_range:'Excel Export — Cash Book (date range)',
  total_net:'Total net',
  handover_t:'Cash Handover (cash given to someone)', holder_l:'Holder (manager / staff)',
  other_name:'Other - name', handover_save:'Save Handover', handover_note:'A handover is a transfer, not an expense — it never enters the P&L.',
  holder_limit_l:'Holder limit', approval_limit_l:'big cash expenses need owner approval above',
  my_account:'- my account', received_l:'Received (handovers)', spent_l:'Spent (cash)',
  balance_in_hand:'Balance in hand', over_warn:'Spent more than the balance — please check the accounts',
  ack_pending:'Handover acknowledgement pending', ack_btn:'Cash Received', confirmed_l:'confirmed',
  in_mila:'IN (received)', out_kharcha:'OUT (spent)', ginti_t:'Cash Count (physical)',
  ginti_book:'Book balance now', ginti_note:'Saving a count records the difference (short / extra); the book balance does NOT change.',
  physical_cash:'Physical cash (counted)', ginti_save:'Save Count', kam:'Short', zyada:'Extra',
  detail_word:'Detail', expense_ledger_note:'Rejecting removes the expense from P&L and the holder account - the cash is treated as still with the holder.',
  bio_t:'Biometric machines', bio_note:'Set this address on the machine over the factory network (WiFi / LAN). Register the machine serial here - punches from an unregistered machine are not accepted. The worker device code is the same PIN / ID as on the machine.',
  machine_name_l:'Machine name', serial_l:'Serial number', last_seen:'Last seen', last_punch:'Last punch',
  csv_t:'CSV import (file exported from the machine)', csv_note:'Columns: device_code, date, time - or check_in. The first header row is required.',
  import_punches:'Import punches', last_punches:'Latest punches',
  att_manual:'Attendance (manual)', ot_auto:'(leave empty for auto)',
  leave_t:'Leave Register', approvals_t:'Approvals - overtime / attendance correction requests',
  leave_note:'Approved unpaid leave is deducted from the monthly pay of a salaried worker (salary / 30 x days).',
  send_request:'Send Request', request_sent:'Request sent — the owner will review it',
  dept_note:'All time worked on an off day becomes overtime (if allowed). On other days, time beyond the shift is overtime. Overtime is added to the worker dues automatically.',
  off_days:'Off days / weekend', ot_rate:'Overtime rate / hour', ot_allowed:'Overtime allowed', shift_t2:'Shift',
  worker_type:'Type', theka_l:'Theka (per ton / bag)', salary_l:'Salary', rate_ton_out:'Rate / ton OUT (theka)',
  rate_bag:'Rate / bag (theka)', monthly_salary:'Monthly salary', device_code:'Biometric device code',
  start_date:'Start date', payout_t:'Payments & Advances', advance_l:'Advance', payment_l:'Payment',
  earned_l:'Earned', taken_l:'Taken', due_l:'Due (balance)', code_l:'code',
  theka_note:'Theka earnings = total powder OUT (tons) x rate + production bags x rate + overtime. Salary earnings = monthly salary - approved unpaid leave share + overtime.',
  own_purchase_t:'Own Purchase — Rock (from a supplier)', own_sale_t:'Own Sale — Powder (to a buyer)',
  ded_l:'Moisture / dirt deduction %', rate_locked:'Rate-locked booking', fulfilled_note:'Fulfilled counts the OUT trips / sales on which this order was selected.',
  out_warn:'If OUT bags exceed the ready bags, the system warns you (the entry is not stopped).',
  party_bags_t:'Party bags', received_opt:'Received from party', returned_opt:'Returned to party',
  bag_type_l:'Bag type', bags_mill_opt:'Mill bags (bardana)', bags_party_opt:'Party bags',
  powder_bags:'Powder bags produced', filter_powder_l:'Filter powder', entries_l:'Entries',
  filter_bags_l:'Filter powder bags', bag_weights_l:'Bag weight defaults',
  powder_bag_kg_l:'Powder bag kg', filter_bag_kg_l:'Filter bag kg', total_production_l:'Total production',
  bag_weights_hint:'Kg in one bag — new entries use these weights; a saved record always keeps the weight of its own day.',
  stock_count_t:'Physical Stock Count', item_l:'Item', counted_l:'Counted', book_l:'Book', diff_l:'Difference',
  came:'came', used_l:'used', returned_l:'returned', left_l:'left',
  bardana_used:'Bags used in production', bardana_in:'Total IN', bardana_out:'Total OUT',
  dir_in_bags:'In — new bags received', dir_out_bags:'Out — bags issued / damaged',
  own_bags_line:'Own bags', made_l:'made', sold_l:'sold',
  last_rate_g:'Last grinding rate', last_rate_p:'Last purchase rate',
  entry_t:'Entry', now_grinding_party:'Party (leave empty for Own)',
  rock_in_full:'Rock IN (total)', edit_user_msg:'is being edited — change the role / access and press Save Changes.',
  save_changes:'Save Changes', new_pw:'New password:', pw_changed:'Password changed',
  staff_access_note:'A staff login reaches only the ticked items — the server blocks the rest too, not just the menu. A client login sees only its own ledger, stock and balance. After 5 wrong passwords, a login locks for 15 minutes.',
  client_party:'Client party', access_staff:'Access (staff)', role_l:'Role',
  only_owner_logins:'Only the owner can create logins.', staff_access_t:'Staff access - tick the work this login may do (everything else stays closed)',
  access_token:'Access Token', token_hint:'Leave empty to keep the current token; the full token is never shown on screen',
  sms_t:'SMS gateway (fallback)', sms_note:'Use the placeholders {to} {msg} {key} {sender} in the URL.',
  sender_id:'Sender ID', phone_id:'Phone Number ID',
  wa_auto_t:'WhatsApp auto-send (Cloud API)', wa_auto_note:'Put the Meta WhatsApp Cloud API Phone Number ID and Access Token here and alerts send by themselves. These 7 templates must first be approved on Meta:',
  cash_rules_t:'Cash Rules (Cash in Hand)', holder_limit_f:'Holder limit (Rs) — warning when one holder holds more cash than this',
  approval_limit_f:'Approval limit (Rs) — a manager / staff CASH expense above this needs owner approval',
  bank_opening_t:'Bank opening balances', bank_opening_f:'— opening balance (Rs)',
  bank_first:'Add a bank in the bank list below first, then its opening balance appears here.',
  bank_list_t:'Bank List and Data', bank_list_f:'Bank accounts (one per line - shown in payments)',
  db_file:'Database file', bio_addr:'Biometric address (write this on the machine)', backup_folder:'Backup folder',
  db_move:'Move the database to a new folder', save_settings:'Save Settings',
  appearance_t:'Appearance - Theme Colour', appearance_note:'This colour applies to the whole system — header, buttons, sidebar and login screen — for every login of the mill.',
  logo_t:'Mill Logo', logo_none:'No logo is set yet.', logo_file_f:'Logo file (PNG / JPG / WebP — resized to 256px automatically on upload)',
  replace_logo:'Replace logo', upload_logo:'Upload logo', remove_l:'Remove', logo_first:'Choose the logo file first',
  logo_done:'Logo set', logo_removed:'Logo removed', logo_fail:'Logo did not upload',
  settings_saved:'Settings saved', theme_done:'Theme colour set',
  data_backup_t:'Backup', data_last:'Last backup', data_never:'never', data_days_ago:'days ago',
  backup_btn:'One-click Full Backup (ZIP)', backup_note:'The ZIP holds the database + a CSV of every table + all attachments. Keep the file in MEGA / Google Drive (keep the backup folder as a Drive / MEGA sync folder and backups upload by themselves).',
  restore_t:'Restore', export_t:'Export (CSV / Excel)', import_t:'Import (CSV) - preview first',
  table_l:'Table', paste_ph:'paste the header row + data rows', preview_btn:'Preview', import_btn:'Import',
  backup_done:'Backup made', restore_done:'Restored - safety backup:', restore_q:'Restore this backup? A safety backup is created automatically first.',
  import_done:'Import done', rows_l:'rows',
  proof_sent:'Proof sent — once the mill confirms it, the payment posts to your ledger.',
  my_proofs:'My sent proofs', sess_started:'Grinding session started', sess_stopped:'Grinding session stopped',
  trip_saved:'Trip saved — Net', photo_attached:'+ photo attached', wa_ready:'— the WhatsApp alert is ready on the Alerts page.',
  job_saved:'Grinding saved — Amount', prod_saved:'Production saved', party_saved:'Party saved',
  worker_saved:'Worker saved', payout_saved:'Payout saved', dept_saved:'Department saved',
  att_saved:'Attendance saved — Overtime:', machine_reg:'Machine registered — Address:',
  import_punches_done:'punches fine,', skip_l:'skipped', leave_saved:'Leave saved',
  head_saved:'Head saved', expense_saved:'Expense saved', bill_attached:'+ bill attached',
  approval_pending:'— approval pending', maint_saved:'Maintenance saved', daycost_saved:'Day costs saved',
  handover_saved:'Handover saved', ack_note2:'— the holder confirms it from his own login (Cash Received)',
  ack_done:'Cash received - confirmed', ginti_saved:'Cash count saved', book_w:'Book:', ginti_w:'Count:',
  payment_saved:'Payment saved', proof_attached2:'+ proof attached',
  order_saved:'Order saved', order_closed:'Order closed', purchase_saved:'Purchase saved - Billed',
  sale_saved:'Sale saved', cheque_done:'Cheque', reminder_made:'reminders made',
  proof_confirm_done:'Proof confirmed — payment posted to the ledger', proof_rejected:'Proof rejected',
  profile_t:'My Profile', disp_name_l:'Display name', phone_wa_l:'Phone / WhatsApp number', cur_pw_l:'Current password', profile_saved:'Profile saved ✓', pw_changed_l:'Password changed ✓ — other devices signed out', avatar_l:'Profile picture', avatar_hint:'JPG / PNG / WebP — shrunk automatically; max 2 MB', avatar_change_l:'📷 Change', avatar_remove_l:'Remove', cred_sent_l:'sent',
  login_created:'Login created', login_updated:'Login updated (the old session of that login is closed — it must log in again)',
  expense_approved:'Expense approved', expense_rejected:'Expense rejected — removed from P&L and the holder account',
  leave_done:'Leave', request_done:'Request', alert_status:'Alert status:',
  dayend_msg:'Day-end text:', dayend_hint:'— it can be sent to the owner from the Alerts page.',
  rec_del_note:'Owner gets an alert and it can be restored from Deleted Entries.',
  delete_q:'Delete this?', cancel_l:'Cancel', delete_l:'Delete',
  choose_l:'Choose…', setup_word:'Setup', theme_colour_l:'Theme colour',
  purchase_l:'Purchase', deleted_ok2:'Record deleted \u2713',
  login_user_l:'Username or Email', forgot_pw:'Forgot password?', forgot_t:'Reset password',
  forgot_hint:'Enter your username or email. If the account has an email saved, a reset link will be emailed to it (valid 60 minutes).',
  send_link:'Send reset link', forgot_sent:'If the account exists, a reset email has been sent. Please check the inbox (and the spam folder).',
  back_login:'Back to login', email_l:'Email',
  email_t:'Email (SMTP)', email_note:'Email copies of statements, payment receipts and owner alerts — sent through your own mail account (SMTP). Works in both editions.',
  email_gmail_hint:'Gmail: host smtp.gmail.com, Port 587, Security STARTTLS, Username = your Gmail address, Password = an App Password (Google Account → Security → App passwords) — the normal Gmail password does not work.',
  smtp_host_l:'SMTP host', smtp_port_l:'Port', smtp_sec_l:'Security', smtp_user_l:'SMTP username', smtp_pass_l:'SMTP password',
  from_name_l:'From name', from_email_l:'From email (optional)',
  mail_on_l:'Email sending ON', mail_test_t:'Test recipient (optional)', mail_test_btn:'Send test email',
  mail_test_first:'Save the settings first, then test.', mail_sent_to:'Test email sent to',
  sys_addr_l:'System address (for reset links)', sys_addr_hint:'The address people open this system at — it goes into password-reset links. Leave empty to use the address of the current visit. On a factory PC, put the PC LAN address here (e.g. http://192.168.1.10:8765).',
  mail_ev_t:'Email notifications — also send an email when:',
  mail_ev_proof_l:'A client sends a payment proof → to the owner', mail_ev_payment_l:'A payment is received → to the party',
  mail_ev_voucher_l:'A vehicle IN/OUT voucher is made → to the party', mail_ev_dayend_l:'The Day-End Summary is opened → to the owner (once a day)',
  send_email_btn:'Send by Email', email_sent_ok:'Email sent ✓',
  wa_guide_t:'How to set this up — step by step',
  wa_guide:'<b>What each field is</b><ul><li><b>Phone Number ID</b> — the ID of your WhatsApp Business number (a long number shown on the Meta API Setup page — it is NOT the phone number itself). Alerts are sent FROM this number.</li><li><b>Access Token</b> — the secret key that gives this system permission to send from that number. Anyone holding it can send as you — never share it.</li><li><b>Templates</b> — WhatsApp only allows automatic messages that use pre-approved templates. The 7 names listed above must be created and approved in your Meta account, spelled exactly the same. The login_credentials template takes 4 values in order: mill name, username, password, login link.</li><li><b>SMS URL / Key / Sender ID</b> (optional) — a fallback SMS gateway, tried when WhatsApp fails. The URL may contain {to} {msg} {key} {sender}.</li></ul><b>Where to get the Phone Number ID + Token</b><ol><li>Open <b>developers.facebook.com</b> → My Apps → Create App → choose <b>Business</b> (or open your existing Meta Business account).</li><li>Add the <b>WhatsApp</b> product to the app, then open <b>WhatsApp → API Setup</b>.</li><li>Register the business phone number there. The same page shows its <b>Phone Number ID</b> — copy it into the field above.</li><li>For a permanent token: <b>Business Settings → Users → System Users</b> → add a system user, give it the <b>whatsapp_business_messaging</b> permission, generate its token, and paste it above.</li><li>Create the 7 templates under <b>WhatsApp → Message Templates</b> with the exact names above and wait for approval (usually a few hours).</li><li>Save here — alerts and vouchers now send by themselves; anything unsent keeps its one-tap wa.me button.</li></ol>',
  email_guide_t:'How to set this up — step by step',
  email_guide:'<b>What each field is</b><ul><li><b>SMTP host / Port / Security</b> — the sending server of your email provider. Host + port come from the provider (examples below). Security: <b>STARTTLS</b> normally goes with port <b>587</b>, <b>SSL</b> with port <b>465</b>.</li><li><b>SMTP username</b> — almost always your full email address.</li><li><b>SMTP password</b> — the password for that mailbox. Gmail and Yahoo do NOT accept the normal password here — they need an <b>App Password</b> (steps below).</li><li><b>From name / From email</b> — what the receiver sees. From email is optional; blank = the SMTP username is used.</li><li><b>System address</b> — the web address of this system itself. Password-reset emails build their link from it, so it must be the address people actually open.</li></ul><b>Gmail — the common case</b><ol><li>Open <b>myaccount.google.com → Security</b> and turn ON <b>2-Step Verification</b> (App Passwords only exist after this).</li><li>Same Security page → <b>App passwords</b> → app name e.g. Mill → Create. Google shows a 16-letter password — copy it.</li><li>Here: Host <b>smtp.gmail.com</b>, Port <b>587</b>, Security <b>STARTTLS</b>, Username = your Gmail address, Password = that App Password.</li><li>Save, turn <b>Email sending ON</b>, then press <b>Send test email</b> — the result (or the error the server returns) is shown as-is.</li></ol><b>Other providers</b><ul><li><b>Outlook / Hotmail:</b> smtp.office365.com, port 587, STARTTLS.</li><li><b>Yahoo:</b> smtp.mail.yahoo.com, port 465, SSL — also needs an App Password (Yahoo Account Security → Generate app password).</li></ul>',
  acc_register:'Attendance Register',
  ib_need_t:'What you\'ll need', ib_tips_t:'Tips & security',
  ib_wa_need:'<li>A <b>Meta Business</b> account with the WhatsApp product added</li><li>A registered WhatsApp Business phone number</li><li>Its <b>Phone Number ID</b> and a permanent <b>Access Token</b> (from a System User)</li><li>The 7 message templates listed below, approved in Meta with the exact same names</li>',
  ib_wa_tips:'<li>The Access Token is a secret key — anyone holding it can send as you, so never share it</li><li>Use the permanent System-User token; the temporary test token expires in 24 hours</li><li>Template names must match exactly, otherwise sending fails</li><li>Anything that could not be sent keeps its one-tap wa.me button</li>',
  ib_mail_need:'<li>The <b>SMTP host + port</b> of your provider (Gmail: smtp.gmail.com, 587 — Outlook: smtp.office365.com, 587)</li><li>Your full email address as the <b>SMTP username</b></li><li>An <b>App Password</b> for Gmail or Yahoo — the normal password is not accepted</li><li>The <b>System address</b> that people actually open — reset links are built from it</li>',
  ib_mail_tips:'<li><b>STARTTLS</b> goes with port 587 and <b>SSL</b> with port 465</li><li>Save the settings first, then press <b>Send test email</b> — the real reply from the server is shown as-is</li><li>The SMTP password is stored only on the server and is never shown back</li><li>From email is optional — left blank, the SMTP username is used</li>',
  mail_preset_l:'Email service',
  mail_preset_custom:'Custom (manual)', mail_preset_gmail:'Gmail',
  mail_preset_brevo:'Brevo — Free plan (300 emails/day)', mail_preset_smtp2go:'SMTP2GO — Free plan (1,000 emails/month)',
  mail_preset_hostinger:'Hostinger', mail_preset_outlook:'Microsoft 365 / Outlook',
  mail_note_custom:'Manual setup — fill in the host, port and password your own email provider gives you.',
  mail_note_gmail:'Account: a normal Google account. Password = an <b>App Password</b>, NOT your Gmail password: turn ON 2-Step Verification, then Google Account → Security → App passwords (16 letters — full steps in the guide below). Free Gmail limit: 500 emails/day. Your Gmail address becomes the sender automatically.',
  mail_note_brevo:'Sign up free at <b>brevo.com</b> — no credit card, free forever: <b>300 emails/day</b>. SMTP username = the email you log in to Brevo with. SMTP password = an <b>SMTP key</b>, NOT your account password: Brevo → Settings → SMTP & API → Generate a new SMTP key. Sender check: confirm your From email under Brevo → Senders, or authenticate your domain (Brevo shows the SPF/DKIM records to add).',
  mail_note_smtp2go:'Sign up free at <b>smtp2go.com</b> — no credit card, <b>1,000 emails/month free forever</b>. Until your sender domain is verified, the limits are 200/day and 25/hour. Username + password = a dedicated pair you create under Sending → SMTP Users (not your account login). A verified sender domain is required: add the 3 CNAME records SMTP2GO shows.',
  mail_note_hostinger:'For a mailbox on your own domain hosted at Hostinger (hPanel → Emails). Password = that mailbox\'s own password (the one you use in hPanel webmail). Hostinger\'s own sending limits apply to the mailbox.',
  mail_note_outlook:'For Microsoft 365 / Outlook mailboxes. Password = the mailbox password, and the mailbox must have <b>SMTP AUTH enabled</b> (Microsoft 365 admin → Users → Mail → Manage email apps), otherwise sending is refused.',
  accd_profile:'Mill name, contact, alert times and logo — shown on header, slips and invoices.',
  accd_appearance:'The colour theme of the whole system — header, buttons, sidebar and login screen.',
  accd_fontprint:'Screen and print fonts, text sizes, bold headings and voucher copies.',
  accd_voice:'Spoken announcements when vehicles and payments are recorded.',
  accd_whatsapp:'Meta WhatsApp Cloud API — alerts, vouchers and reminders send by themselves.',
  accd_email:'Your own mail account (SMTP) — statements, receipts and alerts by email.',
  accd_cash:'Cash-in-hand holder limit, approval limit and bank opening balances.',
  accd_banks:'Bank accounts list, database file, backup folder and biometric address.',
  accd_session:'Start a grinding session, or stop the one running now.',
  accd_gp_entry:'One entry per job: party, shift, grade, powder bags and filter bags.',
  accd_closures:'Recent shifts when the factory stayed closed, with the reason.',
  accd_records:'Saved entries, newest first — the owner can edit or delete.',
  accd_wh_overview:'Bags made, bags out and bags ready — per party and your own.',
  accd_ginti:'Physical bag counting against the book — differences and adjustments.',
  accd_bags:'Mill bardana and party bags — received, used, returned and left.',
  accd_stockcount:'Count any stock item and compare it with the book figure.',
  accd_trade:'Off-gate buy or sell for this party — rock, powder or any other item.',
  accd_khata:'Every debit and credit of this party, with the running balance.',
  accd_os_summary:'Rock, powder, filter powder and bags lying with the mill, plus trade totals.',
  accd_workers:'Add a worker and see every worker with earned, taken and due.',
  accd_payouts:'Pay a worker — salary payment or advance — and see past payouts.',
  accd_att_manual:'Mark a worker present with check-in, check-out and overtime.',
  accd_bio:'Biometric machines, CSV punch import and the latest punches.',
  accd_leave:'Record a worker leave — paid or unpaid — and decide pending ones.',
  accd_approvals:'Overtime and attendance-correction requests, and their decisions.',
  accd_expense_entry:'Record an expense under its head — and add a new head when needed.',
  accd_expense_summary:'This month’s spending, head by head and paid-to by paid-to.',
  accd_daycosts:'Today’s diesel litres and electricity units for cost reports.',
  accd_cashbook:'Today’s money in and out, by cash, bank, online and cheque.',
  accd_dayend:'The whole day in one summary — vehicles, grinding, cash and expenses.',
  accd_excel:'Download the cash book for any date range as Excel, CSV or PDF.',
  accd_bankbook:'Every bank account — opening balance, movements and transactions.',
  accd_pnl:'This month’s income, costs and net profit — with factory closed days.',
  accd_cpt:'Expenses and income divided by the tons ground, for any period.',
  accd_biz:'Grinding, charges, sales and purchases — party by party, with net.',
  accd_deleted:'Deleted entries kept here — the owner can restore any of them.',
  accd_notifs:'System notices for the owner — proofs, alerts and updates.',
  accd_audit:'Who did what, and when — the full activity trail.',
  accd_alerts:'Reminders queued for WhatsApp, SMS and email — send or resend.',
  accd_proofs:'Payment proofs sent by clients — confirm to post the payment.',
  accd_backup:'One-click backup of the whole database, and restore from a file.',
  accd_export:'Download any table as a CSV file.',
  accd_import:'Paste CSV rows to bring records in — preview first, then import.',
  accd_demo:'Fill the system with sample data to try things, or remove it.',
  accd_machines:'Register the mill machines here — service and repairs are noted in the diary.',
  accd_diary:'Every service, repair and part change, with cost and next due date.',
  accd_proofup:'Send a payment proof to the mill, and see the ones you sent before.',
  open:'Open' },
ur: { app:'فاسفیٹ گرائنڈنگ مل', sys_tag:'نظامِ انتظام', dashboard:'ڈیش بورڈ', guide:'قدم بہ قدم رہنمائی',
  parties:'پارٹیاں', vehicles:'گاڑیاں / کانٹا', vehicle_in:'گاڑی اندر', vehicle_out:'گاڑی باہر', grinding:'پسائی',
  production:'پیداوار', grind_prod:'پسائی و پیداوار', warehouse:'گودام', owntrade:'اپنی تجارت',
  orders:'پاؤڈر آرڈرز', workers:'مزدور', departments:'شعبے', attendance:'حاضری',
  leaves:'چھٹی و منظوری', money:'رقم', payments:'ادائیگیاں', expenses:'اخراجات لیجر',
  cashbook:'کیش بک', cashinhand:'کیش ان ہینڈ', cheques:'چیک رجسٹر', reports:'رپورٹس (نفع نقصان)', alerts:'الرٹس',
  assistant:'اے آئی اسسٹنٹ', data:'ڈیٹا — امپورٹ / ایکسپورٹ / بیک اپ', logins:'لاگ ان صارفین',
  settings:'ترتیبات', help:'مدد', logout:'لاگ آؤٹ', save:'محفوظ کریں', add:'شامل کریں', del:'حذف', edit:'تبدیل',
  search:'تلاش کریں…', balance:'بیلنس', to_receive:'وصول کرنا ہے', to_pay:'ادا کرنا ہے', bal_clear:'کھاتہ صاف', calc_l:'کیلکولیٹر', calc_quick_l:'مل کا فوری حساب', calc_bags_tons_l:'تھیلے → ٹن', calc_tons_rate_l:'ٹن × ریٹ', calc_gross_tare_l:'مجموعی − خالی وزن', calc_tons_l:'ٹن', calc_rate_ton_l:'ریٹ فی ٹن',
  date:'تاریخ', party:'پارٹی', vehicle:'گاڑی', driver:'ڈرائیور', gross:'مجموعی وزن', tare:'خالی وزن',
  net:'خالص', bags:'تھیلے', grade:'گریڈ %', rate:'ریٹ', amount:'رقم', note:'نوٹ',
  direction:'سمت', kind:'قسم', local:'مقامی', export:'ایکسپورٹ', today:'آج',
  voice:'🎤 آواز', voice_hint:'آواز کے لیے Chrome browser چاہیے۔ یہ صرف فارم بھرتا ہے — خود چیک کر کے محفوظ دبائیں۔',
  now_grinding:'ابھی پسائی جاری', own_stock:'اپنا اسٹاک', rock:'پتھر', powder:'پاؤڈر',
  bardana:'باردانہ (خالی تھیلے)', low:'کم', print:'پرنٹ', restore:'واپس لائیں',
  login:'لاگ ان', username:'صارف نام', password:'پاس ورڈ', welcome:'خوش آمدید',
  first_steps:'ابھی کوئی ڈیٹا نہیں — قدم 1 سے شروع کریں: اپنی پہلی پارٹی (گاہک / سپلائر / خریدار) شامل کریں، پھر گاڑی IN کی پہلی انٹری درج کریں۔ آپ کا اسٹاک، بیلنس اور آج کے اعداد یہیں نظر آئیں گے۔',
  language:'زبان', theme:'تھیم', unit:'اکائی', dark:'گہرا', light:'روشن',
  client_view:'میرا کھاتہ', upload_proof:'ادائیگی کا ثبوت بھیجیں', pending:'زیر التوا',
  confirmed:'تصدیق شدہ', rejected:'مسترد', generated:'ہفتہ وار یاددہانی بنائیں',
  send:'بھیجیں', status:'حالت', worker:'مزدور', present:'حاضر', checkin:'آمد',
  checkout:'روانگی', overtime:'اوور ٹائم', hours:'گھنٹے', method:'طریقہ', cash:'نقد',
  bank:'بینک', online:'آن لائن', cheque:'چیک', description:'تفصیل',
  g_factory:'🏭 فیکٹری مینجمنٹ', g_accounts:'💰 اکاؤنٹس / حساب کتاب', g_workers:'👷 ورکرز اور حاضری', g_system:'⚙️ سیٹ اپ اور سسٹم', recycle:'ری سائیکل / حذف شدہ انٹریز',
  mill_profile:'مل پروفائل', mill_profile_hint:'یہ نام اور تفصیل ایپ کے ہیڈر، لاگ ان اسکرین، پرنٹ شدہ کھاتے، وزن سلپ / گیٹ پاس اور انوائس پر نظر آتی ہے۔ یہیں سے کسی بھی وقت بدل سکتے ہیں۔',
  ai_placeholder:'سوال لکھیں…', ai_drag:'گھسیٹ کر کہیں بھی رکھیں', outside_grinding:'باہر پسائی', trade_history_l:'تجارت تاریخ', trade_l:'تجارت', add_buy_l:'خرید شامل کریں', add_sell_l:'فروخت شامل کریں', item_l:'شے', item_rock_l:'فاسفیٹ پتھر', item_powder_l:'پاؤڈر', item_other_l:'دیگر شے', item_name_l:'شے کا نام', qty_l:'مقدار', unit_l:'اکائی', unit_rate_l:'ریٹ / اکائی', choose_item_l:'قدم 1 — شے منتخب کریں', src_l:'ماخذ', src_gate_l:'گیٹ', src_ledger_l:'کھاتہ', src_excel_l:'ایکسل', src_direct_l:'براہ راست', direct_trade_l:'براہ راست تجارت', add_direct_l:'براہ راست تجارت شامل کریں', sell_to_l:'فروخت کریں', buy_rate_l:'خرید ریٹ', sell_rate_l:'فروخت ریٹ', profit_l:'منافع', loss_l:'نقصان', direct_note_l:'مال فیکٹری میں نہیں آتا — اسٹاک حرکت نہیں کرتا، صرف دو پارٹیوں کے کھاتے لگتے ہیں۔', ledger_note_l:'وہ مال جو گیٹ ریکارڈ کے بغیر حرکت کر گیا — اسٹاک اسی انٹری سے اندر / باہر ہوتا ہے۔', sale_section_l:'پاؤڈر فروخت (اپنا اسٹاک) — اختیاری', sale_rate_l:'فروخت ریٹ / ٹن', sale_hint_l:'صرف اپنی روانگی پر: دونوں خانے بھریں تو فروخت اسی ٹرپ سے خریدار کے کھاتے میں لگ جاتی ہے (خالص ٹن × ریٹ)، صرف ایک دفعہ۔ وہی فروخت کھاتے میں دوبارہ نہ لگائیں۔ سادہ روانگی کے لیے دونوں خالی چھوڑیں۔', sold_to_l:'پاؤڈر فروخت — کس کو', dup_warn_t:'ممکنہ دہری فروخت', dup_anyway_l:'تصدیق — الگ فروخت ہے', dup_trip_l:'یہ پاؤڈر {date} کو گاڑی باہر ٹرپ پر پہلے ہی {buyer} کو بک چکا ہے (گاڑی {vehicle}، {tons} ٹن @ Rs {rate}/ٹن)۔ اگر یہ انٹری وہی فروخت دوبارہ ہے تو منسوخ کریں — الگ فروخت ہے تو تصدیق کریں۔', dup_sell_l:'{buyer} کے کھاتے میں {tons} ٹن @ Rs {rate}/ٹن کی کھاتہ فروخت {date} کو پہلے سے درج ہے۔ اگر یہ روانگی وہی فروخت ہے تو منسوخ کر کے یہاں خریدار/ریٹ صاف کریں — الگ فروخت ہے تو تصدیق کریں۔', rock_sent_l:'پتھر بھیجا', powder_back_l:'پاؤڈر پسا', outside_mill_l:'باہر مل', sent_t_l:'پتھر بھیجا', charges_l:'پسائی چارجز', powder_bought_l:'پاؤڈر خریدا', rock_sold_l:'پتھر بیچا', outside_sent_l:'پسائی کے لیے بھیجا', outside_recv_l:'پاؤڈر باہر ملوں پر', c_outside:'باہر پسائی', src_outside_l:'باہر', og_bill_l:'پسائی بل', add_bill_l:'پسائی بل لگائیں', powder_ground_l:'پاؤڈر پسا (تھیلے)', rock_used_l:'پتھر استعمال', rock_rate_l:'پتھر ریٹ /ٹن', paid_now_l:'ابھی ادا', remaining_l:'پتھر باقی وہاں', ground_l:'پتھر پسا', powder_left_l:'پاؤڈر باقی وہاں', og_sold_l:'پاؤڈر بکا', og_charges_l:'پسائی چارجز (ہمارے دینے)', og_overview_l:'تمام فیکٹریاں', from_mine_l:'کان / بیچنے والے سے', sold_from_l:'اس فیکٹری سے فروخت', de_gate_purch_l:'گیٹ پر خرید (گاڑی اندر)', de_grind_earned_l:'پسائی کمائی', de_gate_sales_l:'گیٹ پر فروخت (گاڑی باہر)', de_trade_purch_l:'اپنی خرید (کھاتہ / ایکسل)', de_trade_sales_l:'اپنی فروخت (کھاتہ / ایکسل)', de_direct_l:'براہ راست سودے (منافع)', de_payments_l:'ادائیگیاں اندر / باہر', de_handovers_l:'نقد حوالگیاں', de_payouts_l:'مزدور ادائیگیاں', de_attendance_l:'حاضر مزدور', ai_which_party:'کس پارٹی کی بات کر رہے ہیں؟ ایک منتخب کریں:', deal_saved:'براہ راست سودا محفوظ', outside_saved:'باہر پسائی محفوظ',
  sa_title:'پروڈکشن انٹری باقی ہے', sa_body:'{shift} شفٹ ({date}) کی پروڈکشن انٹری ابھی تک درج نہیں ہوئی۔ براہ کرم بنے ہوئے تھیلوں کی تعداد درج کریں۔', sa_enter:'ابھی انٹری کریں', sa_later:'بعد میں', sa_closed_btn:'فیکٹری بند تھی', sa_closed_t:'فیکٹری بند — کوئی پروڈکشن نہیں', sa_reason_technical:'تکنیکی خرابی / فیکٹری بند', sa_reason_power:'بجلی کی بندش', sa_note_ph:'نوٹ (اختیاری)', sa_closed_saved:'بندش درج ہو گئی — اس شفٹ کی کوئی پروڈکشن نہیں', closed_l:'فیکٹری بند', shift_closures_l:'فیکٹری بندشیں (کوئی پروڈکشن نہیں)', day_shift_end_l:'دن کی شفٹ ختم ہونے کا وقت', night_shift_end_l:'رات کی شفٹ ختم ہونے کا وقت', vehicle_alert_time_l:'گاڑی الرٹ کا وقت (روزانہ جائزہ)', va_in_t:'آج کوئی گاڑی اندر درج نہیں ہوئی', va_in_b:'آج ابھی تک فیکٹری میں کسی گاڑی کی آمد درج نہیں ہوئی۔ اگر کوئی گاڑی آئی ہے تو براہ کرم اس کی انٹری درج کریں۔', va_out_t:'آج کوئی گاڑی باہر درج نہیں ہوئی', va_out_b:'آج ابھی تک فیکٹری سے کسی لدی ہوئی گاڑی کی روانگی درج نہیں ہوئی۔ اگر کوئی گاڑی گئی ہے تو براہ کرم اس کی روانگی درج کریں۔', va_ok:'ٹھیک ہے، سمجھ گیا',
  fc_running:'فیکٹری چل رہی ہے', fc_closed:'فیکٹری بند ہے', fc_banner_txt:'فیکٹری بند ہے — {reason} · {date} سے', fc_days:'دن', fc_close_t:'فیکٹری بند کریں', fc_from_l:'بند ہونے کی تاریخ', fc_to_l:'متوقع کھلنے کی تاریخ (اختیاری)', fc_reason_l:'وجہ', fc_r_power_outage:'بجلی بند تھی', fc_r_breakdown:'مشین خراب تھی', fc_r_maintenance_work:'فیکٹری کا کام چل رہا تھا (مرمت)', fc_r_no_material:'مال (پتھر) نہیں تھا', fc_r_other:'دیگر', fc_rtext_ph:'وجہ لکھیں (دیگر کے لیے ضروری)', fc_save_close:'بند درج کریں', fc_reopen_btn:'فیکٹری کھول دیں (چل رہی ہے)', fc_closed_saved:'فیکٹری بند درج ہو گئی', fc_reopened:'فیکٹری دوبارہ چل رہی ہے', fc_days_l:'فیکٹری بند دن', fc_was_closed_l:'فیکٹری بند تھی', fc_only_om:'یہ صرف مالک یا منیجر بدل سکتے ہیں۔', fc_gate_l:'بندش کے دوران: راک آمد {rock} · پاؤڈر روانگی {pow}',
  ai_hint:'میں صرف آپ کے مل ریکارڈ سے جواب دیتا ہوں — نمبر خود نہیں بناتا۔ مثلاً پوچھیں: "آج کتنی گاڑیاں آئیں؟"، "اسٹاک کتنا ہے؟"، "اس مہینے کا منافع؟"',
  ai_try:'ان میں سے ایک چنیں:',
  guide_intro:'ان اقدامات کو ترتیب سے کریں — پہلے قدم 1، پھر قدم 2… ہر کارڈ پر بٹن ہے جو سیدھا اس حصے میں لے جاتا ہے۔',
  g_clients:'گاہک', g_daily:'روز کا کام', g_own:'اپنا مال',
  quick:'فوری کام', qa_in:'گاڑی اندر', qa_out:'گاڑی باہر', qa_grind:'پسائی و پیداوار',
  qa_bags:'تھیلے انٹری', qa_payment:'ادائیگی', qa_expense:'خرچہ', qa_client:'نیا گاہک', qa_ledger:'پارٹی کھاتہ',
  totals:'کل مجموعہ', total_rock:'فیکٹری میں کل پتھر', total_powder:'کل پاؤڈر', total_bags:'کل تھیلے',
  own_s:'اپنا', clients_s:'گاہکوں کا', daily_progress:'روز کی پیش رفت', rock_in:'پتھر اندر',
  cash_in:'نقد اندر', cash_out:'نقد باہر', vs_yday:'کل سے فرق',
  ageing_h:'مدت 0-30 / 31-60 / 60+', recent_vehicles:'حالیہ گاڑیاں',
  no_session:'کوئی سیشن نہیں چل رہا', own_opt:'اپنا', over_credit:'ادھار حد سے زیادہ',
  cheques_due:'اگلے 3 دن میں واجب چیک', slip:'سلپ', nothing_found:'کچھ نہیں ملا۔',
  name_l:'نام', phone_l:'فون', wa_same_l:'فون والا ہی نمبر', roles_l:'رول', supplier:'سپلائر', buyer:'خریدار',
  credit_limit:'ادھار حد (روپے)', opening:'ابتدائی بیلنس', open_date_l:'اکاؤنٹ کھلنے کی تاریخ', opened_l:'اکاؤنٹ کھلا', owes_us:'گاہک نے ہمیں دینے ہیں',
  owe_client:'ہم نے گاہک کو دینے ہیں', opening_hint:'اس سسٹم سے پہلے کا بیلنس',
  stock_l:'اسٹاک', address_l:'پتہ', weight_l:'وزن', saved:'محفوظ ہو گیا \u2713', ledger:'کھاتہ',
  type_l:'قسم', time_l:'وقت', start_time:'شروع وقت', end_time:'ختم وقت', source_l:'ذریعہ',
  entered_by:'درج کردہ', mill_bags:'مل کے تھیلے', client_bags_s:'گاہک کے تھیلے',
  stop_l:'روکیں', start_l:'شروع', close_l:'بند کریں', invoice_l:'انوائس', booked_l:'بک شدہ',
  fulfilled_l:'مکمل', remaining_l:'باقی', machine_l:'مشین', detail_l:'تفصیل',
  channel_l:'چینل', cheque_no:'چیک نمبر', due_date:'تاریخ', dispatch:'روانگی',
  sale_l:'فروخت', product_l:'پروڈکٹ', credit_l:'ادھار', upload_l:'اپ لوڈ',
  choose_file:'پہلے فائل منتخب کریں', khata_btn:'کھاتہ',
  proof_attach:'ثبوت / اٹیچمنٹ (تصویر یا PDF، زیادہ سے زیادہ 5MB)',
  bags_packing:'تھیلے پیکنگ', grinding_job:'پسائی جاب', bag_source:'تھیلے کا ذریعہ',
  bags_made_l:'تھیلے بنے', bags_out_l:'تھیلے گئے', bags_ready_l:'تھیلے تیار', bags_tons:'تھیلوں کا وزن',
  shift_l:'شفٹ', rock_lying:'فیکٹری میں پڑا پتھر', rock_bought:'خریدا گیا پتھر',
  rock_ground:'پیسا گیا پتھر', powder_lying:'پڑا پاؤڈر', powder_made_l:'بنا پاؤڈر',
  powder_sold:'فروخت شدہ پاؤڈر', purchases_total:'کل خریداری', sales_total:'کل فروخت',
  cpt:'فی ٹن لاگت', period:'مدت', this_month:'یہ مہینہ', last_month:'پچھلا مہینہ',
  custom:'اپنی مدت', tons_ground:'پسائی ٹن', total_expenses:'کل فیکٹری اخراجات',
  expense_per_ton:'فی ٹن خرچہ', grinding_income:'پسائی آمدنی', income_per_ton:'فی ٹن آمدنی',
  margin_per_ton:'فی ٹن بچت', by_head:'ہیڈ کے حساب سے', biz_summary:'پارٹی کاروبار خلاصہ',
  biz_note:'ہر پارٹی کے ساتھ ہوا کاروبار — یہ خلاصہ ہے، بیلنس نہیں۔',
  charges_l:'لوڈنگ / دیگر چارجز', net_l:'نیٹ',
  wa_khata:'\uD83D\uDCF2 واٹس ایپ پر کھاتہ بھیجیں', wa_no_phone:'اس پارٹی کا فون نمبر موجود نہیں',
  wa_owe:'بیلنس: پارٹی نے ہمیں دینے ہیں', wa_weowe:'بیلنس: ہم نے پارٹی کو دینے ہیں',
  wa_last5:'آخری 5 انٹریز', wa_pay_numbers:'ہمارے ادائیگی نمبر',
  godam_ginti:'گودام گنتی', counted_bags:'گنے گئے تھیلے', book_bags:'کتابی تھیلے',
  difference:'فرق', shortage:'کمی', excess:'اضافہ', count_save:'گنتی محفوظ کریں',
  adj_request:'ایڈجسٹمنٹ کی درخواست', adj_pending:'ایڈجسٹمنٹ مالک کی منظوری کی منتظر',
  ginti_adj:'گنتی ایڈجسٹمنٹ', counts_history:'گنتی کی تاریخ', adj_history:'ایڈجسٹمنٹس',
  approve:'منظور', reject:'مسترد', pending_adj:'اسٹاک ایڈجسٹمنٹ زیر التوا',
  powder_ageing:'پرانا پاؤڈر منتظر', days_waiting:'دن سے منتظر',
  voice_alerts_t:'آواز کی اطلاعات', voice_master_l:'آواز اطلاعات آن', voice_vehicles_l:'گاڑی کی اطلاعات', voice_payments_l:'ادائیگی کی اطلاعات',
  ev_in:'{party} کی گاڑی نے مال اتار دیا ہے', ev_out:'{party} کی گاڑی لوڈ ہو کر چلی گئی ہے',
  ev_pay_in:'Rs {amount} ادائیگی آ گئی ہے — {party}', ev_pay_out:'Rs {amount} ادائیگی بھیج دی ہے — {party}',
  ev_exp_pending:'بڑا خرچہ منظوری کے انتظار میں ہے: Rs {amount} ({party})',
  missing_t:'یہ خانے خالی رہ گئے ہیں: ', fl_name:'نام', fl_party:'پارٹی', fl_amount:'رقم', fl_vehicle:'گاڑی نمبر',
  fl_weights:'وزن', fl_tons:'ٹن', fl_rate:'ریٹ', fl_bags:'تھیلے', fl_head:'مین ہیڈ', fl_due:'آخری تاریخ',
  fl_net:'خالص وزن', xl_pdf:'⬇ PDF', rate_type_l:'ریٹ کی قسم',
  grind_rate_l:'پسائی ریٹ /ٹن (اختیاری)', grind_charge_l:'پسائی چارج',
  rock_purchase_l:'پتھر خرید — اگر یہ پتھر خریدا گیا ہو', rock_rate_l:'پتھر ریٹ /ٹن',
  factory_rate_l:'فیکٹری پہنچ ریٹ', mine_rate_l:'مائن ریٹ', rent_l:'گاڑی کا کرایہ (روپے)',
  buy_from_l:'خرید کس سے (بیچنے والا)', bought_from_l:'خرید کس سے',
  rent_to_l:'گاڑی کا کرایہ کس کو ادا ہوگا', rent_seller_l:'بیچنے والا', rent_driver_l:'ڈرائیور (نقد)',
  rent_mill_l:'گاڑی کرایہ (مل)', c_rent:'ڈرائیور کو کرایہ (مل)',
  owner_only_edit:'انٹری میں تبدیلی یا حذف صرف مالک کر سکتا ہے',
  editing_l:'✏️ انٹری میں تبدیلی ہو رہی ہے — قدریں ٹھیک کر کے تبدیلی محفوظ کریں',
  back_btn:'واپس',
  driver_phone_l:'ڈرائیور فون', print_voucher_l:'واؤچر پرنٹ کریں', wa_auto_sent:'واؤچر واٹس ایپ پر خودکار بھیج دیا گیا ✓',
  wa_party_btn:'پارٹی کو واٹس ایپ بھیجیں', wa_driver_btn:'ڈرائیور کو واٹس ایپ بھیجیں', wa_owner_btn:'مالک کو واٹس ایپ بھیجیں',
  fl_holder:'رکھنے والا', fl_counted:'گنتی کی رقم', fl_date:'تاریخ', fl_work:'کام', fl_machine:'مشین',
  fl_user:'یوزر نیم', fl_pass:'پاس ورڈ', fl_role:'رول', fl_worker:'ورکر',
  role_owner_l:'مالک', role_manager_l:'منیجر', role_staff_l:'عملہ', role_client_l:'گاہک', role_demo_l:'ڈیمو (صرف دیکھنا)', demo_hint:'ڈیمو لاگ ان: demo / demo12345 — صرف دیکھنے کے لیے', pnl_t:'منافع و نقصان', pnl_income:'آمدن', pnl_costs:'اخراجات', pnl_net:'خالص منافع', st_cleared:'کلیئر', st_bounced:'باؤنس',
  c_purchases:'خرید (اپنا پتھر)', c_expenses:'اخراجات (لیجر)', c_payouts:'ورکر ادائیگی', c_maint:'مرمت', c_freight:'کرایہ (مل)', c_loading:'لوڈنگ (مل)',
  age_note:'حد (ترتیبات) سے زیادہ دن تیار پڑا پاؤڈر، روانگی کے بغیر',
  powder_age_days:'پاؤڈر عمر حد (دن)',
  phos_detail:'فاسفیٹ تفصیل', total_stock:'کل اسٹاک', total_rock:'کل پتھر',
  day_l:'دن', night_l:'رات', wastage_l:'ضیاع', powder_in_l:'پاؤڈر (ٹن)',
  prev_powder_l:'پچھلا پاؤڈر', bal_powder_l:'بیلنس پاؤڈر', bal_rock_l:'بیلنس پتھر', prev_rock_l:'پچھلا پتھر',
  remarks_l:'تبصرہ', dispatched_l:'روانہ', pd_breakdown:'پارٹی وار تفصیل', factory_l:'فیکٹری',
  unspec_l:'بغیر شفٹ وقت والے تھیلے (صرف کل میں شامل)', wastage_pct_l:'ضیاع % (رجسٹر)',
  pd_help:'بیلنس پاؤڈر = پچھلا پاؤڈر + پاؤڈر اندر − روانہ — یہ گودام کے بیلنس سے ملتا ہے۔ بیلنس پتھر = کل پتھر − (پاؤڈر + ضیاع) — رجسٹر پیداوار کو پتھر کی کھپت مانتا ہے اور پہلے ریکارڈ سے روز بہ روز چلتا ہے۔',
  machines:'مشینیں', machine_name:'مشین کا نام', work_type:'کام کی قسم', service:'سروس',
  repair:'مرمت', part_change:'پرزہ تبدیلی', other_l:'دیگر', next_due:'اگلی تاریخ',
  cost_l:'لاگت (روپے)', maint_diary:'مشین مرمت ڈائری', maint_due:'مشین مرمت واجب',
  overdue:'تاخیر', add_machine:'مشین شامل کریں', maint_entry:'مرمت انٹری',
  linked_expense:'اخراجات لیجر انٹری',
    font_print_t:'فونٹ و پرنٹ', ui_font_l:'سسٹم فونٹ', ui_size_l:'سسٹم متن سائز',
  print_font_l:'پرنٹ فونٹ', print_size_l:'پرنٹ متن سائز', print_bold_l:'پرنٹ میں سرخیاں موٹی',
  print_copies_l:'واؤچر کاپیاں فی صفحہ',
  stock_avail_l:'دستیاب پاؤڈر اسٹاک', stock_warn_t:'پاؤڈر اسٹاک کم ہے',
  stock_warn_msg:'اسٹاک میں صرف {avail} پسا ہوا پاؤڈر ہے — آپ {net} باہر بھیج رہے ہیں۔ پھر بھی save کریں؟',
  stock_anyway_l:'پھر بھی Save کریں',
  font_default:'طے شدہ (سسٹم سانز)', font_serif:'سیریف', font_rounded:'گول / دوستانہ',
  font_naskh:'نسخ (Noto Sans Arabic)', font_nastaliq:'نستعلیق (Noto Nastaliq Urdu)',
  size_small:'چھوٹا', size_normal:'درمیانہ', size_large:'بڑا',
  demo_title:'ڈیمو ڈیٹا', demo_load:'ڈیمو ڈیٹا لوڈ کریں', demo_remove:'تمام ڈیمو ڈیٹا حذف کریں',
  record:'ریکارڈ', restored_ok:'بحال ہو گیا ✓', debit:'ڈیبٹ', waiting_l:'انتظار میں', ready_l:'تیار',
  open_view:'کھولیں', download_file:'⬇ ڈاؤن لوڈ', reset_pw:'پاس ورڈ بدلیں',
  edit_user_msg:'ترمیم ہو رہا ہے — رول/رسائی بدل کر تبدیلیاں محفوظ دبائیں۔',
  staff_note:'اسٹاف لاگ ان صرف نشان لگی چیزوں تک جا سکتا ہے — سرور بھی باقی روکتا ہے، صرف مینو نہیں چھپتا۔ گاہک لاگ ان صرف اپنا کھاتہ، اسٹاک اور بیلنس دیکھتا ہے۔ ڈیمو لاگ ان (demo / demo12345) عوامی اور صرف دیکھنے کے لیے ہے: یہ پورا سسٹم دیکھ سکتا ہے اور اسسٹنٹ سے پوچھ سکتا ہے، مگر سرور ہر تبدیلی روکتا ہے، اور ترتیبات، لاگ ان اور بیک اپ اس کے لیے بند رہتے ہیں۔ 5 غلط پاس ورڈ پر لاگ ان 15 منٹ کے لیے مقفل ہو جاتا ہے۔',
  staff_note_pc:'اسٹاف لاگ ان صرف نشان لگی چیزوں تک جا سکتا ہے — سرور بھی باقی روکتا ہے، صرف مینو نہیں چھپتا۔ 5 غلط پاس ورڈ پر لاگ ان 15 منٹ کے لیے مقفل ہو جاتا ہے۔',
  backup_done:'بیک اپ بن گیا ✓', restore_done:'بحال ہو گیا ✓ — حفاظتی بیک اپ:', restore_confirm:'بحال کریں؟ پہلے حفاظتی بیک اپ خود بن جائے گا۔',
  import_done:'درآمد ہو گیا ✓', rows_l:'قطاریں', no_backup:'— ابھی کوئی بیک اپ نہیں', backup_folder_l:'بیک اپ فولڈر',
  last_backup_l:'آخری بیک اپ', never_l:'کبھی نہیں', days_ago_l:'دن پہلے', table_l:'ٹیبل',
  paste_ph:'ہیڈر قطار + ڈیٹا قطاریں یہاں چپکائیں', preview_l:'پیش منظر', columns_l:'کالم',
  mill_name_l:'مل کا نام', mill_phone_l:'مل کا فون', mill_addr_l:'مل کا پتہ', owner_wa_l:'مالک واٹس ایپ (الرٹس کے لیے)',
  logo_hint:'لوگو فائل (PNG / JPG / WebP — اپ لوڈ پر خود 256px تک چھوٹی ہو جاتی ہے)', logo_none:'ابھی کوئی لوگو نہیں لگا ہوا۔',
  replace_logo:'لوگو بدلیں', upload_logo:'لوگو لگائیں', remove_l:'ہٹائیں', logo_pick:'پہلے لوگو فائل منتخب کریں',
  theme_note:'پورے سسٹم کا رنگ — ہیڈر، بٹن، سائیڈبار اور لاگ ان اسکرین سب پر یہی رنگ آئے گا، مل کے ہر لاگ ان پر۔',
  wa_note:'Meta واٹس ایپ کلاؤڈ API کا Phone Number ID اور Access Token یہاں لگائیں تو الرٹ خود بھیجتے ہیں۔ پہلے Meta پر یہ 7 سانچے منظور کرانا ہوتے ہیں:',
  holder_limit_l:'حامل حد (روپے) — ایک حامل کے پاس اس سے زیادہ نقد پر انتباہ',
  approval_limit_l:'منظوری حد (روپے) — منیجر/عملے کا اس سے بڑا نقد خرچہ مالک منظوری مانگتا ہے',
  bank_open_hint:'پہلے نیچے بینک فہرست میں بینک شامل کریں، پھر یہاں ابتدائی بیلنس ملے گا۔',
  db_file_l:'ڈیٹابیس فائل', bio_addr_l:'بایومیٹرک پتہ (مشین پر یہ لکھیں)',
  backup_dir_l:'بیک اپ فولڈر', move_db_l:'ڈیٹابیس نئے فولڈر میں منتقل کریں',
  help_1:'<b>شروع:</b> <span class="mono">Start-Mill-System.bat</span> پر دو دفعہ کلک کریں۔ براؤزر خود کھلتا ہے۔ کام کے دوران کالی ونڈو بند نہ کریں۔',
  help_2:'<b>دوسرے موبائل/PC سے (فیکٹری وائی فائی):</b> سسٹم اسی PC پر چلتا ہے؛ ڈیٹا فولڈر MEGA/Google Drive ہم وقت فولڈر میں رکھیں تو بیک اپ خود کلاؤڈ پر جاتا ہے۔',
  help_3:'<b>بایومیٹرک مشین:</b> حاضری صفحے پر دیا پتہ مشین کی سرور ترتیبات میں لکھیں، سیریل درج کریں، مزدور کو ڈیوائس کوڈ دیں — حاضریاں خود آتی ہیں (PC کھلا ہونا چاہیے)۔',
  help_4:'<b>واٹس ایپ خودکار بھیجنا:</b> Meta پر 7 سانچے منظور کرا کر ترتیبات میں فون نمبر ID + ٹوکن لگائیں۔ ورنہ الرٹس صفحے کے wa.me بٹن استعمال کریں۔',
  help_4_pc:'<b>واٹس ایپ:</b> PC پر الرٹس صفحے اور پارٹی کھاتے کے ایک ٹیپ wa.me بٹن استعمال کریں — پیغام واٹس ایپ میں تیار کھلتا ہے۔',
  help_5:'<b>آواز:</b> Chrome میں مائیک بٹن — بولی ہوئی بات صرف فارم بھرتی ہے، محفوظ آپ خود دباتے ہیں۔',
  help_6:'<b>انوائس:</b> ہر پاؤڈر فروخت کی صاف انوائس مل پروفائل اور لوگو کے ساتھ چھپتی ہے — فروخت فہرست میں انوائس بٹن استعمال کریں۔',
  help_6_pc:'<b>انوائس:</b> ہر پاؤڈر فروخت کی صاف انوائس مل پروفائل اور لوگو کے ساتھ چھپتی ہے — فروخت فہرست میں انوائس بٹن استعمال کریں۔',
  help_7:'<b>بیک اپ:</b> ہر ہفتے ڈیٹا صفحے سے بیک اپ لیں اور ZIP کو MEGA/Drive میں رکھیں۔ بحالی سے پہلے حفاظتی بیک اپ خود بنتا ہے۔',
  help_8:'<b>غلطی ہو جائے:</b> انٹری حذف کریں — مالک کو الرٹ جاتا ہے اور ری سائیکل / حذف شدہ انٹریز سے بحال ہو جاتی ہے۔',
  demo_loaded_msg:'ڈیمو ڈیٹا لوڈ ہو گیا \u2713', demo_removed_msg:'ڈیمو ڈیٹا حذف ہو گیا \u2713',
  demo_text:'ہر فیچر چلتا دیکھنے کے لیے نمونہ ڈیٹا لوڈ کریں۔ تمام نام DEMO سے شروع ہوتے ہیں۔ کسی بھی وقت حذف کریں — آپ کا اصل ڈیٹا محفوظ رہتا ہے۔',
  xl_download:'\u2B07 ایکسل ڈاؤن لوڈ', xl_sample:'\uD83D\uDCC4 نمونہ فائل',
  xl_upload:'\u2B06 ایکسل اپ لوڈ', xl_label:'ایکسل:',
  xl_fmt_title:'ایکسل اپ لوڈ — پہلے فارمیٹ دیکھیں', xl_choose:'فائل منتخب کریں',
  xl_why:'یہ پاپ اپ اس لیے دکھایا جاتا ہے کہ آپ پہلے نمونہ فارمیٹ دیکھ کر اپنا پرانا ڈیٹا بالکل اسی فارمیٹ میں تیار کر سکیں۔ غلط فارمیٹ والی فائل مسترد ہو جائے گی یا غلط درآمد ہو گی — اس لیے اپ لوڈ سے پہلے یہ کالم ضرور ملا لیں۔',
  xl_fmt_note:'آپ کی فائل کی پہلی سطر میں بالکل یہی کالم نام اسی ترتیب سے ہونے چاہئیں۔ ان کے نیچے اپنا ڈیٹا لکھیں — نیچے والی سطریں مثالیں ہیں۔',
  xl_also:'پرانی فائلوں کے یہ اضافی کالم بھی چلتے ہیں:',
  deleted_entries:'حذف شدہ انٹریز', notifications:'اطلاعات', audit_log:'آڈٹ لاگ',
  owner_only_note:'صرف مالک کے لیے۔', all_read:'سب پڑھا ہوا نشان لگائیں',
  from_l:'سے', to_l:'تک', show:'دکھائیں',
  bags_suffix:'تھیلے', rock_waiting:'پتھر منتظر', powder_ready:'پاؤڈر تیار',
  grinding_loss:'پسائی نقصان', attachments:'اٹیچمنٹس',
  freight:'کرایہ', freight_payer:'کرایہ دینے والا', loading:'لوڈنگ', unloading:'ان لوڈنگ',
  load_payer:'لوڈنگ/ان لوڈنگ دینے والا', order_out:'منسلک آرڈر', repeat_trip:'پچھلی ٹرپ دہرائیں',
  in_rock:'پتھر اندر', out_powder:'پاؤڈر باہر',
  saved_tare:'محفوظ خالی وزن مل گیا', vehicle_first:'پہلے گاڑی نمبر لکھیں',
  no_old_trip:'اس گاڑی کی پرانی ٹرپ نہیں ملی', filled_old:'پرانی ٹرپ کی تفصیل بھر دی گئی',
  listening:'سن رہا ہوں… بولیں (پارٹی کا نام اور نمبر)۔',
  heard:'سنا: ', check_save:'— فارم بھر دیا ہے، چیک کر کے محفوظ دبائیں۔',
  voice_fail:'آواز نہیں چلی — کروم براؤزر اور انٹرنیٹ چاہیے۔',
  choose_folder_first:'پہلے ڈیٹا فولڈر لکھیں',
  server_down:'سرور سے رابطہ نہیں ہو رہا — صفحہ تازہ کریں۔',
  setup_intro:'پہلی دفعہ سیٹ اپ: ڈیٹا فولڈر منتخب کریں (ایسی جگہ جو MEGA / Google Drive سے ہم آہنگ ہو، بیک اپ کے لیے)، پھر مالک لاگ ان بنائیں۔',
  data_folder:'ڈیٹا فولڈر', mill_name_l:'مل کا نام', owner_wa:'مالک واٹس ایپ', start_btn:'شروع',
  imp_title:'ایکسل درآمد — پیش منظر', imp_rows:'قطاریں ملیں', imp_ok:'ٹھیک ہیں', imp_dup:'نقل',
  imp_wrong:'غلط', imp_note:'نقل ریکارڈ دوبارہ شامل نہیں ہوں گے اور غلط قطاریں چھوڑ دی جائیں گی۔ تصدیق کریں تو صرف ٹھیک قطاریں محفوظ ہوں گی۔',
  imp_do:'درآمد کریں', imp_done:'درآمد مکمل', imp_added:'ریکارڈ شامل ہوئے', imp_dup_skip:'نقل تھیں (چھوڑ دیں)',
  imp_wrong_rows:'غلط قطاریں', imp_none_bad:'کوئی نقل یا غلط قطار نہیں تھی۔', row_l:'قطار',
  chip_ok:'ٹھیک', chip_dup:'نقل', chip_bad:'غلط',
  summary_t:'خلاصہ', search_t:'تلاش', own_word:'اپنا',
  backup_warn:'دن ہو گئے ہیں آخری بیک اپ کو — ڈیٹا صفحے سے ایک کلک بیک اپ لے کر MEGA / Google Drive میں رکھیں۔',
  backup_warn_start:'بیک اپ کو', pend_exp_t:'خرچہ منظوری زیر التوا',
  pend_exp_note:'زیر التوا خرچہ نفع نقصان میں شامل ہے؛ مسترد کرنے سے نکل جائے گا اور نقد حامل کے پاس ہی سمجھا جائے گا۔',
  pend_adj_note:'منظوری سے کتابی تھیلے گنے گئے تھیلوں کے برابر ہو جائیں گے (گنتی ایڈجسٹمنٹ انٹری لگے گی)۔',
  wa_card_note:'ترتیبات میں واٹس ایپ کلاؤڈ API (فون نمبر ID + ٹوکن) لگا ہو تو الرٹ خود چلے جاتے ہیں۔ ورنہ ہر الرٹ کے ساتھ ایک ٹیپ wa.me بٹن ہے۔ SMS گیٹ وے لگا ہو تو واٹس ایپ ناکام ہونے پر SMS کوشش ہوتا ہے۔ حالت ہر الرٹ پر لکھی آتی ہے۔',
  proofs_t:'گاہک ادائیگی ثبوت (تصدیق زیر التوا)', confirm_pay:'تصدیق (ادائیگی لگ جائے گی)',
  view_proof:'دیکھیں', when_l:'کب', to_l2:'بنام', message_l:'پیغام',
  maint_sec:'مرمت / بندش', day_costs:'دن کے اخراجات', diesel_l:'ڈیزل لیٹر', elec_l:'بجلی یونٹ',
  day_cost_save:'دن خرچ محفوظ', maint_note:'یہاں صرف روز کی مقدار درج ہوتی ہے، بطور ڈائری۔ ڈیزل/بجلی کی رقم اوپر اخراجات لیجر میں لکھیں، تاکہ نفع نقصان میں دوہرا حساب نہ ہو۔ مشین کی مرمت اور اس کی لاگت مشینیں ← مرمت ڈائری میں لکھیں (وہاں سے لیجر میں لگتی ہے)۔',
  cost_note:'اخراجات لیجر کی ہر انٹری صرف ایک دفعہ گنی جاتی ہے۔ ڈیزل/بجلی کی مقدار صرف فی ٹن لاگت کے لیے ہے، رقم لیجر سے آتی ہے۔',
  head_new:'نیا ہیڈ بنائیں', head_name:'ہیڈ کا نام', head_parent:'والد ہیڈ (ذیلی ہیڈ کے لیے)', head_add:'ہیڈ شامل',
  main_head:'مرکزی ہیڈ', sub_head:'ذیلی ہیڈ', paid_by_l:'ادا کنندہ', paid_to_l:'وصول کنندہ',
  month_headwise:'اس مہینے ہیڈ کے حساب سے', paidto_wise:'وصول کنندہ کے حساب سے',
  chq_note:'چیک باؤنس ہو تو حالت باؤنس کریں — پارٹی کا بیلنس خود دوبارہ کھل جائے گا (وہ ادائیگی حساب سے نکل جاتی ہے)۔ کلیئر پر کوئی فرق نہیں۔',
  no_cheque:'— کوئی چیک نہیں', bankbook_empty:'ترتیبات میں بینک فہرست شامل کریں — پھر ہر بینک کا بیلنس یہاں زندہ نظر آئے گا۔',
  opening_bal:'ابتدائی بیلنس', payments_in_bank:'ادائیگیاں اندر (بینک)', payments_out_bank:'ادائیگیاں باہر (بینک)',
  expenses_bank:'اخراجات (بینک)', bank_balance:'بیلنس', txn_type:'قسم', ref_chq:'حوالہ / چیک',
  dayend_t:'دن اختتام خلاصہ', vehicles_l:'گاڑیاں', ground_bags:'پسائی / تھیلے', cash_net:'نقد نیٹ',
  expenses_l:'اخراجات', send_dayend:'دن اختتام مالک کو بھیجیں', excel_range:'ایکسل برآمد — کیش بک (تاریخ کی حد)',
  total_net:'کل نیٹ',
  handover_t:'نقد حوالگی (کس کو نقد دیا)', holder_l:'حامل (منیجر / عملہ)', other_name:'دیگر — نام',
  handover_save:'حوالگی محفوظ', handover_note:'حوالگی ایک منتقلی ہے — خرچہ نہیں؛ نفع نقصان میں نہیں جاتی۔',
  holder_limit_l:'حامل حد', approval_limit_l:'بڑے نقد اخراجات کو اس سے اوپر مالک منظوری چاہیے',
  my_account:'— میرا حساب', received_l:'ملا (حوالگیاں)', spent_l:'خرچہ (نقد)',
  balance_in_hand:'ہاتھ میں بیلنس', over_warn:'بیلنس سے زیادہ خرچہ — حساب چیک کریں',
  ack_pending:'حوالگی رسید کی تصدیق باقی ہے', ack_btn:'نقد مل گیا', confirmed_l:'تصدیق شدہ',
  in_mila:'اندر (ملا)', out_kharcha:'باہر (خرچہ)', ginti_t:'نقد گنتی (جسمانی)',
  ginti_book:'کتابی بیلنس ابھی', ginti_note:'گنتی محفوظ کرنے پر فرق (کم/زیادہ) ریکارڈ ہو جاتا ہے؛ کتابی بیلنس نہیں بدلتا۔',
  physical_cash:'جسمانی نقد (گن کر)', ginti_save:'گنتی محفوظ', kam:'کم', zyada:'زیادہ',
  detail_word:'تفصیل', expense_ledger_note:'مسترد کرنے سے خرچہ نفع نقصان اور حامل کے خرچے سے نکل جائے گا — نقد حامل کے پاس ہی سمجھا جائے گا۔',
  bio_t:'بایومیٹرک مشینیں', bio_note:'مشین کو فیکٹری نیٹ ورک (WiFi/LAN) پر اس پتہ پر مقرر کریں۔ مشین کا سیریل نمبر یہاں درج کریں — بغیر درج مشین کی حاضری قبول نہیں ہوگی۔ مزدور کا ڈیوائس کوڈ وہی PIN/ID ہو جو مشین پر اس مزدور کا ہے۔',
  machine_name_l:'مشین کا نام', serial_l:'سیریل نمبر', last_seen:'آخری دفعہ دیکھا', last_punch:'آخری حاضری',
  csv_t:'CSV درآمد (مشین سے برآمد فائل)', csv_note:'کالم: device_code, date, time — یا check_in۔ پہلی ہیڈر قطار ضرور ہو۔',
  import_punches:'حاضریاں درآمد', last_punches:'آخری حاضریاں',
  att_manual:'حاضری (دستی)', ot_auto:'(خالی چھوڑیں = خودکار)',
  leave_t:'چھٹی رجسٹر', approvals_t:'منظوریاں — اوور ٹائم / حاضری درستگی درخواستیں',
  leave_note:'منظور شدہ بلا معاوضہ چھٹی تنخواہ والے مزدور کی اس مہینے کی کمائی سے (تنخواہ/30 × دن) کٹتی ہے۔',
  send_request:'درخواست بھیجیں', request_sent:'درخواست بھیج دی — مالک منظور کرے گا',
  dept_note:'چھٹی والے دن کی گئی ڈیوٹی کا سارا وقت اوور ٹائم بنتا ہے (اگر اجازت ہو)۔ باقی دنوں میں شفٹ سے زیادہ وقت اوور ٹائم ہے۔ اوور ٹائم مزدور کے واجبات میں خود شامل ہوتا ہے۔',
  off_days:'چھٹی کے دن', ot_rate:'اوور ٹائم ریٹ / گھنٹہ', ot_allowed:'اوور ٹائم اجازت', shift_t2:'شفٹ',
  worker_type:'قسم', theka_l:'ٹھیکہ (فی ٹن/تھیلا)', salary_l:'تنخواہ', rate_ton_out:'ریٹ / ٹن باہر (ٹھیکہ)',
  rate_bag:'ریٹ / تھیلا (ٹھیکہ)', monthly_salary:'ماہانہ تنخواہ', device_code:'بایومیٹرک ڈیوائس کوڈ',
  start_date:'شروع تاریخ', payout_t:'ادائیگیاں / ایڈوانس', advance_l:'ایڈوانس', payment_l:'ادائیگی',
  earned_l:'کمایا', taken_l:'لیا', due_l:'واجب (باقی)', code_l:'کوڈ',
  theka_note:'ٹھیکہ کمائی = کل پاؤڈر باہر ٹن × ریٹ + پیداوار تھیلے × ریٹ + اوور ٹائم۔ تنخواہ کمائی = ماہانہ تنخواہ − منظور شدہ بلا معاوضہ چھٹی کا حصہ + اوور ٹائم۔',
  own_purchase_t:'اپنی خریداری — پتھر (سپلائر سے)', own_sale_t:'اپنی فروخت — پاؤڈر (خریدار کو)',
  ded_l:'نمی / مٹی کٹوتی %', rate_locked:'ریٹ مقفل بکنگ', fulfilled_note:'مکمل وہ باہر ٹرپ/فروخت ہیں جن پر یہ آرڈر منتخب ہوا تھا۔',
  out_warn:'باہر پر تھیلے تیار سے زیادہ ہوں تو سسٹم خبردار کرتا ہے (انٹری رکتی نہیں)۔',
  party_bags_t:'پارٹی کے تھیلے', received_opt:'پارٹی سے موصول', returned_opt:'پارٹی کو واپس',
  bag_type_l:'تھیلے کی قسم', bags_mill_opt:'مل کے تھیلے (باردانہ)', bags_party_opt:'پارٹی کے تھیلے',
  powder_bags:'تیار شدہ پاؤڈر تھیلے', filter_powder_l:'فلٹر پاؤڈر', entries_l:'اندراجات',
  filter_bags_l:'فلٹر پاؤڈر تھیلے', bag_weights_l:'تھیلے کے وزن کی طے شدہ قدریں',
  powder_bag_kg_l:'پاؤڈر تھیلا (کلو)', filter_bag_kg_l:'فلٹر تھیلا (کلو)', total_production_l:'کل پیداوار',
  bag_weights_hint:'ایک تھیلے میں کلو — نئی انٹریوں پر یہی وزن لگتا ہے؛ محفوظ ریکارڈ ہمیشہ اپنے دن کا وزن رکھتا ہے۔',
  stock_count_t:'جسمانی اسٹاک گنتی', item_l:'شے', counted_l:'گنا گیا', book_l:'کتابی', diff_l:'فرق',
  came:'آئے', used_l:'استعمال', returned_l:'واپس', left_l:'بچے',
  bardana_used:'پیداوار میں استعمال تھیلے', bardana_in:'کل اندر', bardana_out:'کل باہر',
  dir_in_bags:'اندر — نئے تھیلے موصول', dir_out_bags:'باہر — تھیلے جاری / خراب',
  own_bags_line:'اپنے تھیلے', made_l:'بنے', sold_l:'فروخت',
  last_rate_g:'آخری پسائی ریٹ', last_rate_p:'آخری خرید ریٹ',
  entry_t:'انٹری', now_grinding_party:'پارٹی (خالی چھوڑیں = اپنا)',
  rock_in_full:'پتھر اندر (کل)', edit_user_msg:'تبدیل ہو رہا ہے — رول/رسائی بدل کر تبدیلیاں محفوظ دبائیں۔',
  save_changes:'تبدیلیاں محفوظ', new_pw:'نیا پاس ورڈ لکھیں:', pw_changed:'پاس ورڈ بدل گیا',
  staff_access_note:'عملہ لاگ ان کو صرف نشان زد چیزوں تک رسائی ملتی ہے — سرور بھی وہی روکتا ہے، صرف مینو نہیں چھپتا۔ گاہک لاگ ان صرف اپنا کھاتہ/اسٹاک/بیلنس دیکھتا ہے۔ 5 غلط پاس ورڈ پر لاگ ان 15 منٹ بند ہو جاتا ہے۔',
  client_party:'گاہک کی پارٹی', access_staff:'رسائی (عملہ)', role_l:'رول',
  only_owner_logins:'صرف مالک لاگ ان بنا سکتا ہے۔', staff_access_t:'عملہ رسائی — جو کام اس لاگ ان کو دینا ہے وہ نشان لگائیں (باقی سب بند)',
  access_token:'رسائی ٹوکن', token_hint:'ٹوکن خالی چھوڑیں تو پرانا رہتا ہے؛ اسکرین پر ٹوکن کبھی پورا نہیں دکھتا',
  sms_t:'SMS گیٹ وے (متبادل)', sms_note:'URL میں {to} {msg} {key} {sender} جگہیں استعمال کریں۔',
  sender_id:'بھیجنے والا ID', phone_id:'فون نمبر ID',
  wa_auto_t:'واٹس ایپ خودکار بھیجنا (کلاؤڈ API)', wa_auto_note:'Meta واٹس ایپ کلاؤڈ API سے فون نمبر ID اور رسائی ٹوکن یہاں لگائیں تو الرٹ خود بھیجتے ہیں۔ پہلے Meta پر یہ 7 سانچے منظور کروانا ہوتے ہیں:',
  cash_rules_t:'نقد اصول (ہاتھ میں نقد)', holder_limit_f:'حامل حد (روپے) — ایک حامل کے پاس اس سے زیادہ نقد پر خبردار',
  approval_limit_f:'منظوری حد (روپے) — منیجر/عملے کا اس سے بڑا نقد خرچہ مالک منظوری مانگتا ہے',
  bank_opening_t:'بینک ابتدائی بیلنس', bank_opening_f:'— ابتدائی بیلنس (روپے)',
  bank_first:'پہلے نیچے بینک فہرست میں بینک شامل کریں، پھر یہاں ابتدائی بیلنس ملے گا۔',
  bank_list_t:'بینک فہرست اور ڈیٹا', bank_list_f:'بینک کھاتے (ہر سطر ایک — ادائیگیوں میں فہرست)',
  db_file:'ڈیٹابیس فائل', bio_addr:'بایومیٹرک پتہ (مشین پر یہ لکھیں)', backup_folder:'بیک اپ فولڈر',
  db_move:'ڈیٹابیس نئے فولڈر میں منتقل کریں', save_settings:'ترتیبات محفوظ',
  appearance_t:'ظاہری — تھیم رنگ', appearance_note:'پورے سسٹم کا رنگ — ہیڈر، بٹن، سائیڈبار اور لاگ ان اسکرین سب پر یہی رنگ آئے گا، مل کے ہر لاگ ان پر۔',
  logo_t:'مل لوگو', logo_none:'ابھی کوئی لوگو نہیں لگا ہوا۔', logo_file_f:'لوگو فائل (PNG / JPG / WebP — اپ لوڈ پر خود 256px تک چھوٹی ہو جاتی ہے)',
  replace_logo:'لوگو بدلیں', upload_logo:'لوگو لگائیں', remove_l:'ہٹائیں', logo_first:'پہلے لوگو فائل منتخب کریں',
  logo_done:'لوگو لگ گیا', logo_removed:'لوگو ہٹا دیا', logo_fail:'لوگو اپ لوڈ نہیں ہوا',
  settings_saved:'ترتیبات محفوظ ہو گئیں', theme_done:'تھیم رنگ لگ گیا',
  data_backup_t:'بیک اپ', data_last:'آخری بیک اپ', data_never:'کبھی نہیں', data_days_ago:'دن پہلے',
  backup_btn:'ایک کلک مکمل بیک اپ (ZIP)', backup_note:'ZIP میں ڈیٹابیس + ہر جدول کی CSV + ساری اٹیچمنٹس ہوتی ہیں۔ فائل کو MEGA / Google Drive میں ضرور رکھیں (بیک اپ فولڈر کو Drive/MEGA ہم آہنگ فولڈر رکھ دیں تو خود ہو جاتا ہے)۔',
  restore_t:'بحال', export_t:'برآمد (CSV / ایکسل)', import_t:'درآمد (CSV) — پہلے پیش منظر',
  table_l:'جدول', paste_ph:'ہیڈر قطار + ڈیٹا قطاریں چسپاں کریں', preview_btn:'پیش منظر', import_btn:'درآمد کریں',
  backup_done:'بیک اپ بن گیا', restore_done:'بحال ہو گیا — حفاظتی بیک اپ:', restore_q:'بحال کریں؟ پہلے حفاظتی بیک اپ خود بن جائے گا۔',
  import_done:'درآمد ہو گیا', rows_l:'قطاریں',
  proof_sent:'ثبوت بھیج دیا — مل تصدیق کرے گا تو کھاتے میں لگ جائے گی۔',
  my_proofs:'میری بھیجی ہوئی رسیدیں', sess_started:'پسائی سیشن شروع ہو گیا', sess_stopped:'پسائی سیشن بند ہو گیا',
  trip_saved:'ٹرپ محفوظ ہو گئی — نیٹ', photo_attached:'+ تصویر منسلک', wa_ready:'— واٹس ایپ الرٹ الرٹس صفحے میں تیار ہے۔',
  job_saved:'پسائی محفوظ ہو گئی — رقم', prod_saved:'پیداوار محفوظ ہو گئی', party_saved:'پارٹی محفوظ ہو گئی',
  worker_saved:'مزدور محفوظ ہو گیا', payout_saved:'ادائیگی محفوظ ہو گئی', dept_saved:'شعبہ محفوظ ہو گیا',
  att_saved:'حاضری محفوظ ہو گئی — اوور ٹائم:', machine_reg:'مشین درج ہو گئی — پتہ:',
  import_punches_done:'حاضریاں ٹھیک،', skip_l:'چھوڑ دیں', leave_saved:'چھٹی محفوظ ہو گئی',
  head_saved:'ہیڈ محفوظ ہو گیا', expense_saved:'خرچہ محفوظ ہو گیا', bill_attached:'+ بل منسلک',
  approval_pending:'— منظوری زیر التوا ہے', maint_saved:'مرمت محفوظ ہو گئی', daycost_saved:'دن اخراجات محفوظ ہو گئے',
  handover_saved:'حوالگی محفوظ ہو گئی', ack_note2:'— حامل اپنے لاگ ان سے نقد مل گیا کی تصدیق کرے گا',
  ack_done:'نقد مل گیا — تصدیق ہو گئی', ginti_saved:'نقد گنتی محفوظ', book_w:'کتابی:', ginti_w:'گنتی:',
  payment_saved:'ادائیگی محفوظ ہو گئی', proof_attached2:'+ ثبوت منسلک',
  order_saved:'آرڈر محفوظ ہو گیا', order_closed:'آرڈر بند ہو گیا', purchase_saved:'خریداری محفوظ ہو گئی — بل شدہ',
  sale_saved:'فروخت محفوظ ہو گئی', cheque_done:'چیک', reminder_made:'یاددہانیاں بن گئیں',
  proof_confirm_done:'ثبوت تصدیق — ادائیگی کھاتے میں لگ گئی', proof_rejected:'ثبوت مسترد ہو گیا',
  profile_t:'میری پروفائل', disp_name_l:'دکھنے والا نام', phone_wa_l:'فون / واٹس ایپ نمبر', cur_pw_l:'موجودہ پاس ورڈ', profile_saved:'پروفائل محفوظ ہو گئی ✓', pw_changed_l:'پاس ورڈ بدل گیا ✓ — باقی آلات سائن آؤٹ ہو گئے', avatar_l:'پروفائل تصویر', avatar_hint:'JPG / PNG / WebP — خود چھوٹی ہو جاتی ہے؛ حد 2 MB', avatar_change_l:'📷 بدلیں', avatar_remove_l:'ہٹائیں', cred_sent_l:'بھیج دیا',
  login_created:'لاگ ان بن گیا', login_updated:'لاگ ان تازہ ہو گیا (اس لاگ ان کا پرانا سیشن بند — دوبارہ لاگ ان ہوگا)',
  expense_approved:'خرچہ منظور ہو گیا', expense_rejected:'خرچہ مسترد ہو گیا — نفع نقصان اور حامل کے حساب سے نکل گیا',
  leave_done:'چھٹی', request_done:'درخواست', alert_status:'الرٹ حالت:',
  dayend_msg:'دن اختتام متن:', dayend_hint:'— الرٹس صفحے سے مالک کو بھیجا جا سکتا ہے۔',
  rec_del_note:'مالک کو الرٹ جائے گا اور حذف شدہ انٹریز سے بحال ہو سکتا ہے۔',
  delete_q:'حذف کریں؟', cancel_l:'منسوخ', delete_l:'حذف',
  choose_l:'منتخب کریں...', setup_word:'سیٹ اپ', theme_colour_l:'تھیم رنگ',
  purchase_l:'خریداری', deleted_ok2:'ریکارڈ حذف ہو گیا \u2713',
  login_user_l:'صارف نام یا ای میل', forgot_pw:'پاس ورڈ بھول گئے؟', forgot_t:'پاس ورڈ ری سیٹ',
  forgot_hint:'اپنا صارف نام یا ای میل لکھیں۔ اگر اکاؤنٹ پر ای میل محفوظ ہے تو ری سیٹ لنک اسی پر بھیجا جائے گا (60 منٹ کارآمد)۔',
  send_link:'ری سیٹ لنک بھیجیں', forgot_sent:'اگر اکاؤنٹ موجود ہے تو ری سیٹ ای میل بھیج دی گئی ہے۔ ان باکس (اور سپام فولڈر) دیکھ لیں۔',
  back_login:'لاگ ان پر واپس', email_l:'ای میل',
  email_t:'ای میل (SMTP)', email_note:'کھاتے کی تفصیل، ادائیگی رسیدوں اور مالک الرٹس کی ای میل نقول — آپ کے اپنے میل اکاؤنٹ (SMTP) سے جاتی ہیں۔ دونوں ایڈیشنز میں کام کرتی ہے۔',
  email_gmail_hint:'Gmail: ہوسٹ smtp.gmail.com، پورٹ 587، سیکیورٹی STARTTLS، صارف نام = آپ کا Gmail پتہ، پاس ورڈ = ایپ پاس ورڈ (Google اکاؤنٹ → سیکیورٹی → ایپ پاس ورڈز) — عام Gmail پاس ورڈ کام نہیں کرتا۔',
  smtp_host_l:'SMTP ہوسٹ', smtp_port_l:'پورٹ', smtp_sec_l:'سیکیورٹی', smtp_user_l:'SMTP صارف نام', smtp_pass_l:'SMTP پاس ورڈ',
  from_name_l:'بھیجنے والے کا نام', from_email_l:'بھیجنے والے کی ای میل (اختیاری)',
  mail_on_l:'ای میل بھیجنا ON', mail_test_t:'ٹیسٹ وصول کنندہ (اختیاری)', mail_test_btn:'ٹیسٹ ای میل بھیجیں',
  mail_test_first:'پہلے ترتیبات محفوظ کریں، پھر ٹیسٹ کریں۔', mail_sent_to:'ٹیسٹ ای میل بھیج دی گئی:',
  sys_addr_l:'سسٹم پتہ (ری سیٹ لنکس کے لیے)', sys_addr_hint:'وہ پتہ جس پر لوگ یہ سسٹم کھولتے ہیں — پاس ورڈ ری سیٹ لنکس میں یہی لگتا ہے۔ خالی چھوڑیں تو موجودہ وزٹ کا پتہ استعمال ہوگا۔ فیکٹری PC پر یہاں PC کا LAN پتہ لکھیں (مثلاً http://192.168.1.10:8765)۔',
  mail_ev_t:'ای میل اطلاعات — ای میل بھی جائے جب:',
  mail_ev_proof_l:'کلائنٹ ادائیگی کا ثبوت بھیجے → مالک کو', mail_ev_payment_l:'ادائیگی موصول ہو → پارٹی کو',
  mail_ev_voucher_l:'گاڑی اندر/باہر واؤچر بنے → پارٹی کو', mail_ev_dayend_l:'دن اختتام خلاصہ کھلے → مالک کو (روز ایک دفعہ)',
  send_email_btn:'ای میل بھیجیں', email_sent_ok:'ای میل بھیج دی گئی ✓',
  wa_guide_t:'یہ سیٹ اپ کیسے کریں — مرحلہ وار',
  wa_guide:'<b>ہر خانہ کیا ہے</b><ul><li><b>فون نمبر ID</b> — آپ کے واٹس ایپ بزنس نمبر کی شناخت (ایک لمبا نمبر جو Meta کے API Setup صفحے پر نظر آتا ہے — یہ خود فون نمبر نہیں ہے)۔ الرٹ اسی نمبر سے جاتے ہیں۔</li><li><b>رسائی ٹوکن</b> — وہ خفیہ چابی جو اس سسٹم کو اس نمبر سے بھیجنے کی اجازت دیتی ہے۔ جس کے پاس یہ ہو وہ آپ بن کر بھیج سکتا ہے — کبھی کسی سے شیئر نہ کریں۔</li><li><b>سانچے (Templates)</b> — واٹس ایپ خودکار پیغام صرف پہلے سے منظور شدہ سانچوں میں بھیجنے دیتا ہے۔ اوپر لکھے 7 ناموں کے سانچے آپ کے Meta اکاؤنٹ میں انہی ہجوں سے بنے اور منظور شدہ ہونے چاہئیں۔ login_credentials سانچے میں 4 چیزیں اسی ترتیب سے جاتی ہیں: مل کا نام، صارف نام، پاس ورڈ، لاگ ان لنک۔</li><li><b>SMS پتہ / چابی / بھیجنے والا ID</b> (اختیاری) — واٹس ایپ ناکام ہو تو کوشش ہونے والا SMS گیٹ وے۔ پتے میں {to} {msg} {key} {sender} لگ سکتے ہیں۔</li></ul><b>فون نمبر ID اور ٹوکن کہاں سے ملے گا</b><ol><li><b>developers.facebook.com</b> کھولیں → My Apps → Create App → <b>Business</b> منتخب کریں (یا اپنا موجودہ Meta Business اکاؤنٹ کھولیں)۔</li><li>ایپ میں <b>WhatsApp</b> پروڈکٹ شامل کریں، پھر <b>WhatsApp → API Setup</b> کھولیں۔</li><li>وہاں بزنس فون نمبر رجسٹر کریں۔ اسی صفحے پر اس کا <b>Phone Number ID</b> نظر آئے گا — اوپر والے خانے میں لگا دیں۔</li><li>مستقل ٹوکن کے لیے: <b>Business Settings → Users → System Users</b> → سسٹم صارف بنائیں، اسے <b>whatsapp_business_messaging</b> اجازت دیں، اس کا ٹوکن بنائیں اور اوپر لگا دیں۔</li><li><b>WhatsApp → Message Templates</b> میں اوپر والے 7 ناموں کے سانچے بنائیں اور منظوری کا انتظار کریں (عموماً چند گھنٹے)۔</li><li>یہاں محفوظ کر دیں — الرٹ اور واؤچر اب خود جائیں گے؛ جو نہ جائے اس پر ایک ٹیپ wa.me بٹن رہے گا۔</li></ol>',
  email_guide_t:'یہ سیٹ اپ کیسے کریں — مرحلہ وار',
  email_guide:'<b>ہر خانہ کیا ہے</b><ul><li><b>SMTP ہوسٹ / پورٹ / سیکیورٹی</b> — آپ کے ای میل فراہم کنندہ کا بھیجنے والا سرور۔ ہوسٹ + پورٹ فراہم کنندہ سے ملتے ہیں (مثالیں نیچے ہیں)۔ سیکیورٹی: <b>STARTTLS</b> عموماً پورٹ <b>587</b> کے ساتھ، <b>SSL</b> پورٹ <b>465</b> کے ساتھ۔</li><li><b>SMTP صارف نام</b> — تقریباً ہمیشہ آپ کا مکمل ای میل پتہ ہوتا ہے۔</li><li><b>SMTP پاس ورڈ</b> — اس میل بکس کا پاس ورڈ۔ Gmail اور Yahoo یہاں عام پاس ورڈ قبول نہیں کرتے — انہیں <b>ایپ پاس ورڈ</b> چاہیے (مراحل نیچے ہیں)۔</li><li><b>بھیجنے والے کا نام / ای میل</b> — وصول کنندہ کو یہی نظر آتا ہے۔ ای میل خالی ہو تو SMTP صارف نام ہی لگتا ہے۔</li><li><b>سسٹم پتہ</b> — اس سسٹم کا اپنا ویب پتہ۔ پاس ورڈ ری سیٹ ای میل کا لنک اسی سے بنتا ہے، اس لیے وہی پتہ ہو جو لوگ اصل میں کھولتے ہیں۔</li></ul><b>Gmail — عام صورت</b><ol><li><b>myaccount.google.com → Security</b> کھولیں اور <b>2-Step Verification</b> ON کریں (ایپ پاس ورڈ اسی کے بعد بنتا ہے)۔</li><li>اسی Security صفحے پر → <b>App passwords</b> → نام مثلاً Mill → Create۔ Google 16 حروف کا پاس ورڈ دکھائے گا — نقل کر لیں۔</li><li>یہاں لکھیں: ہوسٹ <b>smtp.gmail.com</b>، پورٹ <b>587</b>، سیکیورٹی <b>STARTTLS</b>، صارف نام = آپ کا Gmail پتہ، پاس ورڈ = وہی ایپ پاس ورڈ۔</li><li>محفوظ کریں، <b>ای میل بھیجنا ON</b> کریں، پھر <b>ٹیسٹ ای میل بھیجیں</b> دبائیں — نتیجہ (یا سرور کی خرابی) ویسا ہی نظر آئے گا۔</li></ol><b>دیگر فراہم کنندہ</b><ul><li><b>Outlook / Hotmail:</b> smtp.office365.com، پورٹ 587، STARTTLS۔</li><li><b>Yahoo:</b> smtp.mail.yahoo.com، پورٹ 465، SSL — اسے بھی ایپ پاس ورڈ چاہیے (Yahoo Account Security → Generate app password)۔</li></ul>',
  acc_register:'حاضری رجسٹر',
  ib_need_t:'کیا چاہیے ہوگا', ib_tips_t:'ٹپس اور سیکیورٹی',
  ib_wa_need:'<li><b>Meta Business</b> اکاؤنٹ جس میں WhatsApp پروڈکٹ شامل ہو</li><li>رجسٹر شدہ WhatsApp Business فون نمبر</li><li>اس کا <b>Phone Number ID</b> اور مستقل <b>Access Token</b> (System User سے ملتا ہے)</li><li>نیچے لکھے 7 سانچے Meta میں بالکل انہی ناموں سے منظور شدہ ہوں</li>',
  ib_wa_tips:'<li>Access Token خفیہ چابی ہے — جس کے پاس ہو وہ آپ بن کر بھیج سکتا ہے، اس لیے کبھی شیئر نہ کریں</li><li>مستقل System User ٹوکن استعمال کریں؛ عارضی ٹیسٹ ٹوکن 24 گھنٹے میں ختم ہو جاتا ہے</li><li>سانچوں کے نام بالکل وہی ہوں ورنہ بھیجنا ناکام ہوگا</li><li>جو پیغام خود نہ بھیجا جا سکے اس پر ایک ٹیپ wa.me بٹن رہتا ہے</li>',
  ib_mail_need:'<li>آپ کے فراہم کنندہ کا <b>SMTP ہوسٹ + پورٹ</b> (Gmail: smtp.gmail.com، 587 — Outlook: smtp.office365.com، 587)</li><li><b>SMTP صارف نام</b> کے طور پر آپ کا مکمل ای میل پتہ</li><li>Gmail یا Yahoo کے لیے <b>App Password</b> — عام پاس ورڈ قبول نہیں ہوتا</li><li>وہ <b>سسٹم پتہ</b> جو لوگ اصل میں کھولتے ہیں — ری سیٹ لنک اسی سے بنتا ہے</li>',
  ib_mail_tips:'<li><b>STARTTLS</b> پورٹ 587 کے ساتھ اور <b>SSL</b> پورٹ 465 کے ساتھ جاتا ہے</li><li>پہلے ترتیبات محفوظ کریں، پھر <b>ٹیسٹ ای میل بھیجیں</b> دبائیں — سرور کا اصل جواب ویسا ہی دکھایا جاتا ہے</li><li>SMTP پاس ورڈ صرف سرور پر محفوظ ہوتا ہے اور کبھی واپس نہیں دکھایا جاتا</li><li>From ای میل اختیاری ہے — خالی ہو تو SMTP صارف نام ہی استعمال ہوتا ہے</li>',
  mail_preset_l:'ای میل سروس',
  mail_preset_custom:'اپنی مرضی (دستی)', mail_preset_gmail:'Gmail',
  mail_preset_brevo:'Brevo — مفت پلان (روزانہ 300 ای میل)', mail_preset_smtp2go:'SMTP2GO — مفت پلان (ماہانہ 1,000 ای میل)',
  mail_preset_hostinger:'Hostinger', mail_preset_outlook:'Microsoft 365 / Outlook',
  mail_note_custom:'دستی سیٹ اپ — وہی ہوسٹ، پورٹ اور پاس ورڈ لکھیں جو آپ کا اپنا ای میل فراہم کنندہ دیتا ہے۔',
  mail_note_gmail:'اکاؤنٹ: عام Google اکاؤنٹ۔ پاس ورڈ = <b>ایپ پاس ورڈ</b>، آپ کا Gmail پاس ورڈ نہیں: 2-Step Verification ON کریں، پھر Google اکاؤنٹ → سیکیورٹی → ایپ پاس ورڈز (16 حروف — مکمل مراحل نیچے گائیڈ میں ہیں)۔ Gmail کی مفت حد: روزانہ 500 ای میل۔ بھیجنے والے کے طور پر آپ کا Gmail پتہ خود لگ جاتا ہے۔',
  mail_note_brevo:'<b>brevo.com</b> پر مفت اکاؤنٹ بنائیں — کریڈٹ کارڈ نہیں چاہیے، ہمیشہ مفت: <b>روزانہ 300 ای میل</b>۔ SMTP صارف نام = وہی ای میل جس سے آپ Brevo میں لاگ ان ہوتے ہیں۔ SMTP پاس ورڈ = ایک <b>SMTP کلید</b>، اکاؤنٹ پاس ورڈ نہیں: Brevo → Settings → SMTP & API → نئی SMTP کلید بنائیں۔ بھیجنے والے کی تصدیق: اپنی From ای میل کو Brevo → Senders میں تصدیق کریں، یا اپنا ڈومین لگائیں (Brevo SPF/DKIM ریکارڈ دکھاتا ہے)۔',
  mail_note_smtp2go:'<b>smtp2go.com</b> پر مفت اکاؤنٹ بنائیں — کریڈٹ کارڈ نہیں چاہیے، <b>ماہانہ 1,000 ای میل ہمیشہ مفت</b>۔ ڈومین تصدیق سے پہلے حد: روزانہ 200 اور فی گھنٹہ 25۔ صارف نام + پاس ورڈ = ایک الگ جوڑا جو آپ Sending → SMTP Users میں بناتے ہیں (اکاؤنٹ لاگ ان نہیں)۔ تصدیق شدہ بھیجنے والا ڈومین لازمی ہے: SMTP2GO کے دکھائے گئے 3 CNAME ریکارڈ لگائیں۔',
  mail_note_hostinger:'آپ کے اپنے ڈومین کے اس میل بکس کے لیے جو Hostinger پر ہے (hPanel → Emails)۔ پاس ورڈ = اسی میل بکس کا اپنا پاس ورڈ (جو hPanel ویب میل میں لگتا ہے)۔ بھیجنے کی حد Hostinger کی اپنی لاگو ہوتی ہے۔',
  mail_note_outlook:'Microsoft 365 / Outlook میل بکس کے لیے۔ پاس ورڈ = میل بکس کا پاس ورڈ، اور اس میل بکس پر <b>SMTP AUTH آن</b> ہونا لازمی ہے (Microsoft 365 admin → Users → Mail → Manage email apps) ورنہ بھیجنا رد ہو جائے گا۔',
  accd_profile:'مل کا نام، رابطہ، الرٹ اوقات اور لوگو — ہیڈر، سلپ اور انوائس پر نظر آتا ہے۔',
  accd_appearance:'پورے سسٹم کا رنگ — ہیڈر، بٹن، سائیڈبار اور لاگ ان اسکرین۔',
  accd_fontprint:'اسکرین و پرنٹ فونٹ، متن سائز، بولڈ سرخیاں اور واؤچر کاپیاں۔',
  accd_voice:'گاڑی اور ادائیگی درج ہونے پر بولی جانے والی اطلاعات۔',
  accd_whatsapp:'Meta واٹس ایپ کلاؤڈ API — الرٹ، واؤچر اور یاددہانیاں خود بھیجتی ہیں۔',
  accd_email:'آپ کا اپنا میل اکاؤنٹ (SMTP) — کھاتہ، رسیدیں اور الرٹ ای میل سے۔',
  accd_cash:'ہاتھ نقد کی حد، منظوری حد اور بینک ابتدائی بیلنس۔',
  accd_banks:'بینک کھاتوں کی فہرست، ڈیٹابیس فائل، بیک اپ فولڈر اور بایومیٹرک پتہ۔',
  accd_session:'پسائی سیشن شروع کریں، یا چلتا ہوا بند کریں۔',
  accd_gp_entry:'ہر کام کی ایک انٹری: پارٹی، شفٹ، گریڈ، پاؤڈر تھیلے اور فلٹر تھیلے۔',
  accd_closures:'حالیہ شفٹیں جب فیکٹری بند رہی، وجہ کے ساتھ۔',
  accd_records:'محفوظ اندراجات، نئے پہلے — مالک تبدیل یا حذف کر سکتا ہے۔',
  accd_wh_overview:'تھیلے بنے، تھیلے گئے اور تھیلے تیار — ہر پارٹی اور اپنے۔',
  accd_ginti:'کتابی اسٹاک سے اصل گنتی کا مقابلہ — فرق اور ایڈجسٹمنٹ۔',
  accd_bags:'مل کا باردانہ اور پارٹی تھیلے — آئے، استعمال، واپس اور باقی۔',
  accd_stockcount:'کسی بھی اسٹاک شے کی گنتی کریں اور کتابی تعداد سے ملائیں۔',
  accd_trade:'اس پارٹی کی بغیر گیٹ خرید یا فروخت — پتھر، پاؤڈر یا کوئی اور شے۔',
  accd_khata:'اس پارٹی کا ہر ڈیبٹ اور کریڈٹ، چلتے بیلنس کے ساتھ۔',
  accd_os_summary:'مل کے پاس پڑا پتھر، پاؤڈر، فلٹر پاؤڈر اور تھیلے، تجارت کے کُل کے ساتھ۔',
  accd_workers:'مزدور شامل کریں اور ہر مزدور کی کمائی، لی ہوئی اور باقی رقم دیکھیں۔',
  accd_payouts:'مزدور کو ادائیگی کریں — تنخواہ یا ایڈوانس — اور پچھلی ادائیگیاں دیکھیں۔',
  accd_att_manual:'مزدور کی حاضری لگائیں — آمد، روانگی اور اوور ٹائم کے ساتھ۔',
  accd_bio:'بایومیٹرک مشینیں، CSV پنچ امپورٹ اور تازہ پنچز۔',
  accd_leave:'مزدور کی چھٹی درج کریں — با معاوضہ یا بلا معاوضہ — اور زیر التوا پر فیصلہ کریں۔',
  accd_approvals:'اوور ٹائم اور حاضری درستگی کی درخواستیں، اور ان کے فیصلے۔',
  accd_expense_entry:'خرچ اس کے ہیڈ میں درج کریں — ضرورت پر نیا ہیڈ بھی بنائیں۔',
  accd_expense_summary:'اس مہینے کا خرچ، ہیڈ کے حساب سے اور وصول کنندہ کے حساب سے۔',
  accd_daycosts:'لاگت رپورٹس کے لیے آج کے ڈیزل لیٹر اور بجلی یونٹ۔',
  accd_cashbook:'آج کی رقم آمد و خرچ — نقد، بینک، آن لائن اور چیک کے حساب سے۔',
  accd_dayend:'پورا دن ایک خلاصے میں — گاڑیاں، پسائی، نقد اور اخراجات۔',
  accd_excel:'کسی بھی تاریخ حد کی کیش بک Excel، CSV یا PDF میں ڈاؤن لوڈ کریں۔',
  accd_bankbook:'ہر بینک کھاتہ — ابتدائی بیلنس، آمد و خرچ اور لین دین۔',
  accd_pnl:'اس مہینے کی آمدنی، لاگت اور خالص منافع — فیکٹری بند دنوں کے ساتھ۔',
  accd_cpt:'کسی بھی مدت کے لیے اخراجات اور آمدنی، پسے ہوئے ٹن پر تقسیم۔',
  accd_biz:'پسائی، چارجز، فروخت اور خرید — پارٹی بہ پارٹی، نیٹ کے ساتھ۔',
  accd_deleted:'حذف شدہ اندراجات یہاں رہتے ہیں — مالک کوئی بھی واپس لا سکتا ہے۔',
  accd_notifs:'مالک کے لیے سسٹم اطلاعات — ثبوت، الرٹ اور اپڈیٹس۔',
  accd_audit:'کس نے کیا کیا، اور کب — مکمل سرگرمی ریکارڈ۔',
  accd_alerts:'واٹس ایپ، SMS اور ای میل کے لیے تیار یاددہانیاں — بھیجیں یا دوبارہ بھیجیں۔',
  accd_proofs:'گاہکوں کے بھیجے ادائیگی ثبوت — تصدیق کریں تو ادائیگی لگ جائے۔',
  accd_backup:'پورے ڈیٹابیس کا ایک کلک بیک اپ، اور فائل سے بحالی۔',
  accd_export:'کوئی بھی ٹیبل CSV فائل میں ڈاؤن لوڈ کریں۔',
  accd_import:'ریکارڈ لانے کے لیے CSV سطریں لگائیں — پہلے جائزہ، پھر امپورٹ۔',
  accd_demo:'آزمائش کے لیے سسٹم میں نمونہ ڈیٹا بھریں، یا ہٹا دیں۔',
  accd_machines:'مل کی مشینیں یہاں درج کریں — سروس اور مرمت ڈائری میں لکھی جاتی ہے۔',
  accd_diary:'ہر سروس، مرمت اور پرزہ تبدیلی، لاگت اور اگلی تاریخ کے ساتھ۔',
  accd_proofup:'مل کو ادائیگی کا ثبوت بھیجیں، اور پہلے بھیجے ہوئے دیکھیں۔',
  open:'کھولیں' },
hi: { app:'फॉस्फेट ग्राइंडिंग मिल', sys_tag:'प्रबंधन प्रणाली', dashboard:'डैशबोर्ड', guide:'चरण-दर-चरण गाइड',
  parties:'पार्टियाँ', vehicles:'वाहन / कांटा', vehicle_in:'गाड़ी अंदर', vehicle_out:'गाड़ी बाहर', grinding:'पिसाई',
  production:'उत्पादन', grind_prod:'पिसाई और उत्पादन', warehouse:'गोदाम', owntrade:'अपना व्यापार',
  orders:'पाउडर ऑर्डर', workers:'मज़दूर', departments:'विभाग', attendance:'हाज़िरी',
  leaves:'छुट्टी व स्वीकृति', money:'पैसा', payments:'भुगतान', expenses:'खर्च लेजर',
  cashbook:'कैश बुक', cashinhand:'कैश इन हैंड', cheques:'चेक रजिस्टर', reports:'रिपोर्ट (लाभ-हानि)', alerts:'अलर्ट',
  assistant:'AI सहायक', data:'डेटा — इम्पोर्ट / एक्सपोर्ट / बैकअप', logins:'लॉगिन उपयोगकर्ता',
  settings:'सेटिंग्स', help:'मदद', logout:'लॉगआउट', save:'सहेजें', add:'जोड़ें', del:'हटाएँ', edit:'बदलें',
  search:'खोजें…', balance:'शेष', to_receive:'लेना है', to_pay:'देना है', bal_clear:'खाता साफ़', calc_l:'कैलकुलेटर', calc_quick_l:'मिल का त्वरित हिसाब', calc_bags_tons_l:'बोरे → टन', calc_tons_rate_l:'टन × दर', calc_gross_tare_l:'कुल − खाली वज़न', calc_tons_l:'टन', calc_rate_ton_l:'दर प्रति टन',
  date:'तारीख़', party:'पार्टी', vehicle:'वाहन', driver:'ड्राइवर', gross:'कुल वज़न', tare:'खाली वज़न',
  net:'शुद्ध', bags:'बोरे', grade:'ग्रेड %', rate:'दर', amount:'राशि', note:'नोट',
  direction:'दिशा', kind:'प्रकार', local:'स्थानीय', export:'निर्यात', today:'आज',
  voice:'🎤 आवाज़', voice_hint:'आवाज़ के लिए Chrome ब्राउज़र चाहिए। यह सिर्फ़ फ़ॉर्म भरता है — ख़ुद जाँचकर सहेजें दबाएँ।',
  now_grinding:'अभी पिसाई जारी', own_stock:'अपना स्टॉक', rock:'पत्थर', powder:'पाउडर',
  bardana:'बरदाना (खाली बोरे)', low:'कम', print:'प्रिंट', restore:'वापस लाएँ',
  login:'लॉगिन', username:'उपयोगकर्ता नाम', password:'पासवर्ड', welcome:'स्वागत है',
  first_steps:'अभी कोई डेटा नहीं — चरण 1 से शुरू करें: अपनी पहली पार्टी (ग्राहक / सप्लायर / ख़रीदार) जोड़ें, फिर वाहन IN की पहली एंट्री दर्ज करें। आपका स्टॉक, बैलेंस और आज के आँकड़े यहीं दिखेंगे।',
  language:'भाषा', theme:'थीम', unit:'इकाई', dark:'गहरा', light:'हल्का',
  client_view:'मेरा खाता', upload_proof:'भुगतान का सबूत भेजें', pending:'लंबित',
  confirmed:'पुष्ट', rejected:'अस्वीकृत', generated:'साप्ताहिक अनुस्मारक बनाएँ',
  send:'भेजें', status:'स्थिति', worker:'मज़दूर', present:'उपस्थित', checkin:'आगमन',
  checkout:'प्रस्थान', overtime:'ओवरटाइम', hours:'घंटे', method:'तरीका', cash:'नकद',
  bank:'बैंक', online:'ऑनलाइन', cheque:'चेक', description:'विवरण',
  g_factory:'🏭 फैक्ट्री प्रबंधन', g_accounts:'💰 खाते / हिसाब किताब', g_workers:'👷 वर्कर व हाज़िरी', g_system:'⚙️ सेटअप व सिस्टम', recycle:'रीसायकल / हटाई गई प्रविष्टियाँ',
  mill_profile:'मिल प्रोफ़ाइल', mill_profile_hint:'यह नाम और विवरण ऐप हेडर, लॉगिन स्क्रीन, प्रिंट खाता, वज़न पर्ची / गेट पास और इनवॉइस पर दिखता है। यहीं से कभी भी बदल सकते हैं।',
  ai_placeholder:'सवाल लिखें…', ai_drag:'खींचकर कहीं भी रखें', outside_grinding:'बाहर पिसाई', trade_history_l:'व्यापार इतिहास', trade_l:'व्यापार', add_buy_l:'ख़रीद जोड़ें', add_sell_l:'बिक्री जोड़ें', item_l:'वस्तु', item_rock_l:'फॉस्फेट रॉक', item_powder_l:'पाउडर', item_other_l:'अन्य वस्तु', item_name_l:'वस्तु का नाम', qty_l:'मात्रा', unit_l:'इकाई', unit_rate_l:'दर / इकाई', choose_item_l:'चरण 1 — वस्तु चुनें', src_l:'स्रोत', src_gate_l:'गेट', src_ledger_l:'खाता', src_excel_l:'एक्सेल', src_direct_l:'सीधा', direct_trade_l:'सीधा व्यापार', add_direct_l:'सीधा व्यापार जोड़ें', sell_to_l:'बेचें', buy_rate_l:'ख़रीद दर', sell_rate_l:'बिक्री दर', profit_l:'लाभ', loss_l:'हानि', direct_note_l:'माल फैक्टरी में नहीं आता — स्टॉक नहीं चलता, केवल दो पार्टियों के खाते लगते हैं।', ledger_note_l:'वह माल जो गेट रिकॉर्ड के बिना चला गया — स्टॉक इसी एंट्री से अंदर / बाहर होता है।', sale_section_l:'पाउडर बिक्री (अपना स्टॉक) — वैकल्पिक', sale_rate_l:'बिक्री दर /टन', sale_hint_l:'केवल अपनी रवानगी पर: दोनों फ़ील्ड भरें तो बिक्री इसी ट्रिप से ख़रीदार के खाते में लग जाती है (शुद्ध टन × दर), केवल एक बार। वही बिक्री खाते में दोबारा न लगाएँ। साधारण रवानगी के लिए दोनों खाली छोड़ें।', sold_to_l:'पाउडर बेचा — किसे', dup_warn_t:'संभावित दोहरी बिक्री', dup_anyway_l:'पुष्टि — अलग बिक्री है', dup_trip_l:'यह पाउडर {date} को गाड़ी बाहर ट्रिप पर पहले ही {buyer} को बिक चुका है (गाड़ी {vehicle}, {tons} टन @ Rs {rate}/टन)। यदि यह एंट्री वही बिक्री दोबारा है तो रद्द करें — अलग बिक्री है तो पुष्टि करें।', dup_sell_l:'{buyer} के खाते में {tons} टन @ Rs {rate}/टन की खाता बिक्री {date} को पहले से दर्ज है। यदि यह रवानगी वही बिक्री है तो रद्द करके यहाँ ख़रीदार/दर साफ़ करें — अलग बिक्री है तो पुष्टि करें।', rock_sent_l:'रॉक भेजा', powder_back_l:'पाउडर पिसा', outside_mill_l:'बाहर मिल', sent_t_l:'रॉक भेजा', charges_l:'पिसाई शुल्क', powder_bought_l:'पाउडर ख़रीदा', rock_sold_l:'रॉक बेचा', outside_sent_l:'पिसाई के लिए भेजा', outside_recv_l:'पाउडर बाहर मिलों पर', c_outside:'बाहर पिसाई', src_outside_l:'बाहर', og_bill_l:'पिसाई बिल', add_bill_l:'पिसाई बिल लगाएँ', powder_ground_l:'पाउडर पिसा (बोरे)', rock_used_l:'रॉक इस्तेमाल', rock_rate_l:'रॉक दर /टन', paid_now_l:'अभी अदा', remaining_l:'रॉक बाकी वहाँ', ground_l:'रॉक पिसा', powder_left_l:'पाउडर बाकी वहाँ', og_sold_l:'पाउडर बिका', og_charges_l:'पिसाई शुल्क (हमारे देने)', og_overview_l:'सभी फ़ैक्ट्रियाँ', from_mine_l:'खदान / विक्रेता से', sold_from_l:'इस फ़ैक्ट्री से बिक्री', de_gate_purch_l:'गेट पर ख़रीद (गाड़ी अंदर)', de_grind_earned_l:'पिसाई कमाई', de_gate_sales_l:'गेट पर बिक्री (गाड़ी बाहर)', de_trade_purch_l:'अपनी ख़रीद (खाता / एक्सेल)', de_trade_sales_l:'अपनी बिक्री (खाता / एक्सेल)', de_direct_l:'सीधे सौदे (लाभ)', de_payments_l:'भुगतान अंदर / बाहर', de_handovers_l:'नकद हैंडओवर', de_payouts_l:'वर्कर भुगतान', de_attendance_l:'उपस्थित मज़दूर', ai_which_party:'किस पार्टी की बात कर रहे हैं? एक चुनें:', deal_saved:'सीधा सौदा सहेजा गया', outside_saved:'बाहर पिसाई सहेजी गई',
  sa_title:'प्रोडक्शन एंट्री बाकी है', sa_body:'{shift} शिफ़्ट ({date}) की प्रोडक्शन एंट्री अभी तक दर्ज नहीं हुई है। कृपया बने बोरों की संख्या दर्ज करें।', sa_enter:'अभी एंट्री करें', sa_later:'बाद में', sa_closed_btn:'फ़ैक्टरी बंद थी', sa_closed_t:'फ़ैक्टरी बंद — कोई प्रोडक्शन नहीं', sa_reason_technical:'तकनीकी खराबी / फ़ैक्टरी बंद', sa_reason_power:'बिजली बंद', sa_note_ph:'नोट (वैकल्पिक)', sa_closed_saved:'बंदी दर्ज हो गई — इस शिफ़्ट का कोई प्रोडक्शन नहीं', closed_l:'फ़ैक्टरी बंद', shift_closures_l:'फ़ैक्टरी बंदियाँ (कोई प्रोडक्शन नहीं)', day_shift_end_l:'दिन की शिफ़्ट समाप्त होने का समय', night_shift_end_l:'रात की शिफ़्ट समाप्त होने का समय', vehicle_alert_time_l:'वाहन अलर्ट समय (दैनिक समीक्षा)', va_in_t:'आज कोई वाहन आगमन दर्ज नहीं हुआ', va_in_b:'आज अभी तक फ़ैक्टरी में किसी वाहन का आगमन दर्ज नहीं हुआ है। यदि कोई वाहन आया है, तो कृपया उसकी एंट्री दर्ज करें।', va_out_t:'आज कोई वाहन प्रस्थान दर्ज नहीं हुआ', va_out_b:'आज अभी तक फ़ैक्टरी से किसी लदे हुए वाहन का प्रस्थान दर्ज नहीं हुआ है। यदि कोई वाहन गया है, तो कृपया उसका प्रस्थान दर्ज करें।', va_ok:'ठीक है, समझ गया',
  fc_running:'फ़ैक्टरी चल रही है', fc_closed:'फ़ैक्टरी बंद है', fc_banner_txt:'फ़ैक्टरी बंद है — {reason} · {date} से', fc_days:'दिन', fc_close_t:'फ़ैक्टरी बंद करें', fc_from_l:'बंद होने की तिथि', fc_to_l:'संभावित खुलने की तिथि (वैकल्पिक)', fc_reason_l:'कारण', fc_r_power_outage:'बिजली बंद थी', fc_r_breakdown:'मशीन ख़राब थी', fc_r_maintenance_work:'फ़ैक्टरी का काम चल रहा था (मरम्मत)', fc_r_no_material:'माल (पत्थर) नहीं था', fc_r_other:'अन्य', fc_rtext_ph:'कारण लिखें (अन्य के लिए आवश्यक)', fc_save_close:'बंद दर्ज करें', fc_reopen_btn:'फ़ैक्टरी खोल दें (चल रही है)', fc_closed_saved:'फ़ैक्टरी बंद दर्ज हो गई', fc_reopened:'फ़ैक्टरी फिर चल रही है', fc_days_l:'फ़ैक्टरी बंद दिन', fc_was_closed_l:'फ़ैक्टरी बंद थी', fc_only_om:'यह केवल मालिक या मैनेजर बदल सकते हैं।', fc_gate_l:'बंदी के दौरान: रॉक आगमन {rock} · पाउडर प्रस्थान {pow}',
  ai_hint:'मैं सिर्फ़ आपके मिल रिकॉर्ड से जवाब देता हूँ — नंबर ख़ुद नहीं बनाता। जैसे पूछें: "आज कितनी गाड़ियाँ आईं?", "स्टॉक कितना है?", "इस महीने का मुनाफ़ा?"',
  ai_try:'इनमें से एक चुनें:',
  guide_intro:'इन चरणों को क्रम से करें — पहले चरण 1, फिर चरण 2… हर कार्ड पर बटन है जो सीधे उस भाग में ले जाता है।',
  g_clients:'ग्राहक', g_daily:'रोज़ का काम', g_own:'अपना माल',
  quick:'त्वरित कार्य', qa_in:'गाड़ी अंदर', qa_out:'गाड़ी बाहर', qa_grind:'पिसाई और उत्पादन',
  qa_bags:'बोरे एंट्री', qa_payment:'भुगतान', qa_expense:'खर्च', qa_client:'ग्राहक जोड़ें', qa_ledger:'पार्टी खाता',
  totals:'कुल योग', total_rock:'फैक्टरी में कुल रॉक', total_powder:'कुल पाउडर', total_bags:'कुल बोरे',
  own_s:'अपना', clients_s:'ग्राहकों का', daily_progress:'दैनिक प्रगति', rock_in:'रॉक अंदर',
  cash_in:'नकद अंदर', cash_out:'नकद बाहर', vs_yday:'कल से अंतर',
  ageing_h:'अवधि 0-30 / 31-60 / 60+', recent_vehicles:'हाल के वाहन',
  no_session:'कोई सेशन नहीं चल रहा', own_opt:'अपना', over_credit:'क्रेडिट सीमा से अधिक',
  cheques_due:'अगले 3 दिनों में देय चेक', slip:'पर्ची', nothing_found:'कुछ नहीं मिला।',
  name_l:'नाम', phone_l:'फ़ोन', wa_same_l:'फ़ोन वाला ही नंबर', roles_l:'भूमिकाएँ', supplier:'सप्लायर', buyer:'ख़रीदार',
  credit_limit:'क्रेडिट सीमा (Rs)', opening:'प्रारंभिक शेष', open_date_l:'खाता खुलने की तारीख़', opened_l:'खाता खुला', owes_us:'ग्राहक से लेना है',
  owe_client:'ग्राहक को देना है', opening_hint:'इस सिस्टम से पहले का शेष',
  stock_l:'स्टॉक', address_l:'पता', weight_l:'वज़न', saved:'सहेजा गया \u2713', ledger:'खाता',
  type_l:'प्रकार', time_l:'समय', start_time:'शुरू समय', end_time:'समाप्ति समय', source_l:'स्रोत',
  entered_by:'दर्जकर्ता', mill_bags:'मिल के बोरे', client_bags_s:'ग्राहक के बोरे',
  stop_l:'रोकें', start_l:'शुरू', close_l:'बंद करें', invoice_l:'इनवॉइस', booked_l:'बुक किया',
  fulfilled_l:'पूरा हुआ', remaining_l:'शेष', machine_l:'मशीन', detail_l:'विवरण',
  channel_l:'चैनल', cheque_no:'चेक नंबर', due_date:'तिथि', dispatch:'रवानगी',
  sale_l:'बिक्री', product_l:'उत्पाद', credit_l:'क्रेडिट', upload_l:'अपलोड',
  choose_file:'पहले फ़ाइल चुनें', khata_btn:'खाता',
  proof_attach:'सबूत / अटैचमेंट (छवि या PDF, अधिकतम 5MB)',
  bags_packing:'बोरे पैकिंग', grinding_job:'पिसाई जॉब', bag_source:'बोरे का स्रोत',
  bags_made_l:'बोरे बने', bags_out_l:'बोरे गए', bags_ready_l:'बोरे तैयार', bags_tons:'बोरों का वज़न',
  shift_l:'शिफ़्ट', rock_lying:'फैक्टरी में पड़ा रॉक', rock_bought:'ख़रीदा रॉक',
  rock_ground:'पिसा रॉक', powder_lying:'पड़ा पाउडर', powder_made_l:'बना पाउडर',
  powder_sold:'बिका पाउडर', purchases_total:'कुल ख़रीद', sales_total:'कुल बिक्री',
  cpt:'प्रति टन लागत', period:'अवधि', this_month:'यह महीना', last_month:'पिछला महीना',
  custom:'कस्टम', tons_ground:'पिसे टन', total_expenses:'कुल फैक्टरी खर्च',
  expense_per_ton:'प्रति टन खर्च', grinding_income:'पिसाई आय', income_per_ton:'प्रति टन आय',
  margin_per_ton:'प्रति टन मार्जिन', by_head:'हेड अनुसार', biz_summary:'पार्टी व्यापार सारांश',
  biz_note:'हर पार्टी के साथ हुआ व्यापार — यह सारांश है, शेष नहीं।',
  charges_l:'लोडिंग / अन्य शुल्क', net_l:'नेट',
  wa_khata:'\uD83D\uDCF2 WhatsApp पर खाता भेजें', wa_no_phone:'इस पार्टी का फ़ोन नंबर नहीं है',
  wa_owe:'शेष: पार्टी को हमें देना है', wa_weowe:'शेष: हमें पार्टी को देना है',
  wa_last5:'अंतिम 5 एंट्री', wa_pay_numbers:'हमारे भुगतान नंबर',
  godam_ginti:'गोदाम गिनती', counted_bags:'गिने गए बोरे', book_bags:'किताबी बोरे',
  difference:'अंतर', shortage:'कमी', excess:'अधिक', count_save:'गिनती सहेजें',
  adj_request:'समायोजन अनुरोध', adj_pending:'समायोजन मालिक की स्वीकृति प्रतीक्षित',
  ginti_adj:'गिनती समायोजन', counts_history:'गिनती इतिहास', adj_history:'समायोजन',
  approve:'स्वीकृत', reject:'अस्वीकृत', pending_adj:'स्टॉक समायोजन लंबित',
  powder_ageing:'पुराना पाउडर प्रतीक्षित', days_waiting:'दिन से प्रतीक्षा',
  voice_alerts_t:'आवाज़ सूचनाएँ', voice_master_l:'आवाज़ सूचनाएँ चालू', voice_vehicles_l:'गाड़ी सूचनाएँ', voice_payments_l:'भुगतान सूचनाएँ',
  ev_in:'{party} की गाड़ी ने माल उतार दिया है', ev_out:'{party} की गाड़ी लोड होकर चली गई है',
  ev_pay_in:'Rs {amount} भुगतान आ गया है — {party}', ev_pay_out:'Rs {amount} भुगतान भेज दिया है — {party}',
  ev_exp_pending:'बड़ा खर्च स्वीकृति की प्रतीक्षा में है: Rs {amount} ({party})',
  missing_t:'ये ख़ाने खाली रह गए हैं: ', fl_name:'नाम', fl_party:'पार्टी', fl_amount:'राशि', fl_vehicle:'गाड़ी नंबर',
  fl_weights:'वज़न', fl_tons:'टन', fl_rate:'रेट', fl_bags:'बोरे', fl_head:'मुख्य हेड', fl_due:'नियत तारीख़',
  fl_net:'शुद्ध वज़न', xl_pdf:'⬇ PDF', rate_type_l:'दर का प्रकार',
  grind_rate_l:'पिसाई दर /टन (वैकल्पिक)', grind_charge_l:'पिसाई शुल्क',
  rock_purchase_l:'रॉक ख़रीद — अगर यह रॉक ख़रीदा गया हो', rock_rate_l:'रॉक दर /टन',
  factory_rate_l:'फ़ैक्टरी पहुँच दर', mine_rate_l:'माइन दर', rent_l:'वाहन किराया (रु)',
  buy_from_l:'किससे खरीदा (विक्रेता)', bought_from_l:'किससे खरीदा',
  rent_to_l:'वाहन किराया किसे देना है', rent_seller_l:'विक्रेता', rent_driver_l:'ड्राइवर (नकद)',
  rent_mill_l:'वाहन किराया (मिल)', c_rent:'ड्राइवर को किराया (मिल)',
  owner_only_edit:'एंट्री बदलना या हटाना केवल मालिक कर सकता है',
  editing_l:'✏️ एंट्री बदली जा रही है — मान ठीक करके बदलाव सहेजें दबाएँ',
  back_btn:'वापस',
  driver_phone_l:'ड्राइवर फ़ोन', print_voucher_l:'वाउचर प्रिंट करें', wa_auto_sent:'वाउचर WhatsApp पर अपने आप भेज दिया गया ✓',
  wa_party_btn:'पार्टी को WhatsApp भेजें', wa_driver_btn:'ड्राइवर को WhatsApp भेजें', wa_owner_btn:'मालिक को WhatsApp भेजें',
  fl_holder:'धारक', fl_counted:'गिनती राशि', fl_date:'तारीख़', fl_work:'काम', fl_machine:'मशीन',
  fl_user:'यूज़र नाम', fl_pass:'पासवर्ड', fl_role:'रोल', fl_worker:'वर्कर',
  role_owner_l:'मालिक', role_manager_l:'मैनेजर', role_staff_l:'स्टाफ़', role_client_l:'ग्राहक', role_demo_l:'डेमो (केवल देखें)', demo_hint:'डेमो लॉगिन: demo / demo12345 — सिर्फ़ देखने के लिए', pnl_t:'लाभ-हानि', pnl_income:'आय', pnl_costs:'खर्च', pnl_net:'शुद्ध लाभ', st_cleared:'क्लियर', st_bounced:'बाउंस',
  c_purchases:'खरीद (अपना रॉक)', c_expenses:'खर्च (लेजर)', c_payouts:'वर्कर भुगतान', c_maint:'रखरखाव', c_freight:'किराया (मिल)', c_loading:'लोडिंग (मिल)',
  age_note:'सीमा (सेटिंग्स) से अधिक दिन तैयार पड़ा पाउडर, रवानगी के बिना',
  powder_age_days:'पाउडर आयु सीमा (दिन)',
  phos_detail:'फॉस्फेट विवरण', total_stock:'कुल स्टॉक', total_rock:'कुल रॉक',
  day_l:'दिन', night_l:'रात', wastage_l:'नुकसान', powder_in_l:'पाउडर (टन)',
  prev_powder_l:'पिछला पाउडर', bal_powder_l:'शेष पाउडर', bal_rock_l:'शेष रॉक', prev_rock_l:'पिछला रॉक',
  remarks_l:'टिप्पणी', dispatched_l:'रवाना', pd_breakdown:'पार्टी अनुसार विवरण', factory_l:'फैक्टरी',
  unspec_l:'बिना शिफ़्ट समय वाले बोरे (केवल योग में शामिल)', wastage_pct_l:'नुकसान % (रजिस्टर)',
  pd_help:'शेष पाउडर = पिछला पाउडर + पाउडर अंदर − रवाना — यह गोदाम के शेष से मिलता है। शेष रॉक = कुल रॉक − (पाउडर + नुकसान) — रजिस्टर उत्पादन को रॉक की खपत मानता है और पहले रिकॉर्ड से रोज़-ब-रोज़ चलता है।',
  machines:'मशीनें', machine_name:'मशीन का नाम', work_type:'कार्य प्रकार', service:'सर्विस',
  repair:'मरम्मत', part_change:'पुर्ज़ा बदलाव', other_l:'अन्य', next_due:'अगली तिथि',
  cost_l:'लागत (Rs)', maint_diary:'मशीन मरम्मत डायरी', maint_due:'मशीन मरम्मत देय',
  overdue:'अतिदेय', add_machine:'मशीन जोड़ें', maint_entry:'मरम्मत एंट्री',
  linked_expense:'खर्च लेजर एंट्री',
    font_print_t:'फ़ॉन्ट व प्रिंट', ui_font_l:'सिस्टम फ़ॉन्ट', ui_size_l:'सिस्टम पाठ आकार',
  print_font_l:'प्रिंट फ़ॉन्ट', print_size_l:'प्रिंट पाठ आकार', print_bold_l:'प्रिंट में शीर्षक मोटे',
  print_copies_l:'वाउचर प्रतियाँ प्रति पृष्ठ',
  stock_avail_l:'उपलब्ध पाउडर स्टॉक', stock_warn_t:'पाउडर स्टॉक कम है',
  stock_warn_msg:'स्टॉक में केवल {avail} पिसा हुआ पाउडर है — आप {net} बाहर भेज रहे हैं। फिर भी save करें?',
  stock_anyway_l:'फिर भी Save करें',
  font_default:'डिफ़ॉल्ट (सिस्टम सैंस)', font_serif:'सेरिफ़', font_rounded:'गोल / दोस्ताना',
  font_naskh:'नस्ख (Noto Sans Arabic)', font_nastaliq:'नस्तालीक (Noto Nastaliq Urdu)',
  size_small:'छोटा', size_normal:'सामान्य', size_large:'बड़ा',
  demo_title:'डेमो डेटा', demo_load:'डेमो डेटा लोड करें', demo_remove:'सारा डेमो डेटा हटाएँ',
  record:'रिकॉर्ड', restored_ok:'बहाल हो गया ✓', debit:'डेबिट', waiting_l:'प्रतीक्षा में', ready_l:'तैयार',
  open_view:'खोलें', download_file:'⬇ डाउनलोड', reset_pw:'पासवर्ड बदलें',
  edit_user_msg:'संपादित हो रहा है — भूमिका/पहुँच बदलकर परिवर्तन सहेजें दबाएँ।',
  staff_note:'स्टाफ़ लॉगिन केवल टिक की गई चीज़ों तक जा सकता है — सर्वर भी बाकी रोकता है, सिर्फ़ मेनू नहीं छिपता। ग्राहक लॉगिन केवल अपना खाता, स्टॉक और शेष देखता है। डेमो लॉगिन (demo / demo12345) सार्वजनिक और केवल देखने के लिए है: यह पूरा सिस्टम देख सकता है और सहायक से पूछ सकता है, मगर सर्वर हर बदलाव रोकता है, और सेटिंग्स, लॉगिन व बैकअप इसके लिए बंद रहते हैं। 5 ग़लत पासवर्ड पर लॉगिन 15 मिनट के लिए लॉक हो जाता है।',
  staff_note_pc:'स्टाफ़ लॉगिन केवल टिक की गई चीज़ों तक जा सकता है — सर्वर भी बाकी रोकता है, सिर्फ़ मेनू नहीं छिपता। 5 ग़लत पासवर्ड पर लॉगिन 15 मिनट के लिए लॉक हो जाता है।',
  backup_done:'बैकअप बन गया ✓', restore_done:'बहाल हो गया ✓ — सुरक्षा बैकअप:', restore_confirm:'बहाल करें? पहले सुरक्षा बैकअप ख़ुद बन जाएगा।',
  import_done:'आयात हो गया ✓', rows_l:'पंक्तियाँ', no_backup:'— अभी कोई बैकअप नहीं', backup_folder_l:'बैकअप फ़ोल्डर',
  last_backup_l:'अंतिम बैकअप', never_l:'कभी नहीं', days_ago_l:'दिन पहले', table_l:'तालिका',
  paste_ph:'हेडर पंक्ति + डेटा पंक्तियाँ यहाँ चिपकाएँ', preview_l:'पूर्वावलोकन', columns_l:'कॉलम',
  mill_name_l:'मिल का नाम', mill_phone_l:'मिल का फ़ोन', mill_addr_l:'मिल का पता', owner_wa_l:'मालिक WhatsApp (अलर्ट के लिए)',
  logo_hint:'लोगो फ़ाइल (PNG / JPG / WebP — अपलोड पर ख़ुद 256px तक छोटी हो जाती है)', logo_none:'अभी कोई लोगो नहीं लगा हुआ।',
  replace_logo:'लोगो बदलें', upload_logo:'लोगो लगाएँ', remove_l:'हटाएँ', logo_pick:'पहले लोगो फ़ाइल चुनें',
  theme_note:'पूरे सिस्टम का रंग — हेडर, बटन, साइडबार और लॉगिन स्क्रीन सब पर यही रंग आएगा, मिल के हर लॉगिन पर।',
  wa_note:'Meta WhatsApp क्लाउड API का Phone Number ID और Access Token यहाँ लगाएँ तो अलर्ट ख़ुद भेजते हैं। पहले Meta पर ये 7 टेम्पलेट स्वीकृत कराने होते हैं:',
  holder_limit_l:'धारक सीमा (रु) — एक धारक के पास इससे ज़्यादा नकद पर चेतावनी',
  approval_limit_l:'स्वीकृति सीमा (रु) — मैनेजर/स्टाफ़ का इससे बड़ा नकद खर्च मालिक स्वीकृति माँगता है',
  bank_open_hint:'पहले नीचे बैंक सूची में बैंक जोड़ें, फिर यहाँ प्रारंभिक शेष मिलेगा।',
  db_file_l:'डेटाबेस फ़ाइल', bio_addr_l:'बायोमेट्रिक पता (मशीन पर यह लिखें)',
  backup_dir_l:'बैकअप फ़ोल्डर', move_db_l:'डेटाबेस नए फ़ोल्डर में ले जाएँ',
  help_1:'<b>शुरू:</b> <span class="mono">Start-Mill-System.bat</span> पर दो बार क्लिक करें। ब्राउज़र ख़ुद खुलता है। काम के दौरान काली विंडो बंद न करें।',
  help_2:'<b>दूसरे मोबाइल/PC से (फ़ैक्टरी वाई-फ़ाई):</b> सिस्टम इसी PC पर चलता है; डेटा फ़ोल्डर MEGA/Google Drive सिंक फ़ोल्डर में रखें तो बैकअप ख़ुद क्लाउड पर जाता है।',
  help_3:'<b>बायोमेट्रिक मशीन:</b> हाज़िरी पृष्ठ पर दिया पता मशीन की सर्वर सेटिंग्स में लिखें, सीरियल दर्ज करें, मज़दूर को डिवाइस कोड दें — हाज़िरियाँ ख़ुद आती हैं (PC खुला होना चाहिए)।',
  help_4:'<b>WhatsApp स्वतः भेजना:</b> Meta पर 7 टेम्पलेट स्वीकृत कराकर सेटिंग्स में फ़ोन नंबर ID + टोकन लगाएँ। वरना अलर्ट पृष्ठ के wa.me बटन उपयोग करें।',
  help_4_pc:'<b>WhatsApp:</b> PC पर अलर्ट पृष्ठ और पार्टी खाते के एक टैप wa.me बटन उपयोग करें — संदेश WhatsApp में तैयार खुलता है।',
  help_5:'<b>आवाज़:</b> Chrome में माइक बटन — बोली हुई बात केवल फ़ॉर्म भरती है, सहेजना आप ख़ुद दबाते हैं।',
  help_6:'<b>इनवॉइस:</b> हर पाउडर बिक्री का साफ़ इनवॉइस मिल प्रोफ़ाइल और लोगो के साथ छपता है — बिक्री सूची में इनवॉइस बटन उपयोग करें।',
  help_6_pc:'<b>इनवॉइस:</b> हर पाउडर बिक्री का साफ़ इनवॉइस मिल प्रोफ़ाइल और लोगो के साथ छपता है — बिक्री सूची में इनवॉइस बटन उपयोग करें।',
  help_7:'<b>बैकअप:</b> हर हफ़्ते डेटा पृष्ठ से बैकअप लें और ZIP को MEGA/Drive में रखें। बहाली से पहले सुरक्षा बैकअप ख़ुद बनता है।',
  help_8:'<b>ग़लती हो जाए:</b> एंट्री हटाएँ — मालिक को अलर्ट जाता है और रीसायकल / हटाई गई एंट्री से बहाल हो जाती है।',
  demo_loaded_msg:'डेमो डेटा लोड हो गया \u2713', demo_removed_msg:'डेमो डेटा हटा दिया गया \u2713',
  demo_text:'हर फ़ीचर चलता देखने के लिए नमूना डेटा लोड करें। सभी नाम DEMO से शुरू होते हैं। कभी भी हटाएँ — आपका असली डेटा सुरक्षित रहता है।',
  xl_download:'\u2B07 एक्सेल डाउनलोड', xl_sample:'\uD83D\uDCC4 नमूना फ़ाइल',
  xl_upload:'\u2B06 एक्सेल अपलोड', xl_label:'एक्सेल:',
  xl_fmt_title:'एक्सेल अपलोड — पहले फ़ॉर्मेट देखें', xl_choose:'फ़ाइल चुनें',
  xl_why:'यह पॉपअप इसलिए दिखाया जाता है कि आप पहले नमूना फ़ॉर्मेट देखकर अपना पुराना डेटा बिल्कुल इसी फ़ॉर्मेट में तैयार कर सकें। ग़लत फ़ॉर्मेट वाली फ़ाइल अस्वीकार हो जाएगी या ग़लत आयात होगी — इसलिए अपलोड से पहले ये कॉलम ज़रूर मिला लें।',
  xl_fmt_note:'आपकी फ़ाइल की पहली पंक्ति में बिल्कुल यही कॉलम नाम इसी क्रम में होने चाहिए। उनके नीचे अपना डेटा लिखें — नीचे वाली पंक्तियाँ उदाहरण हैं।',
  xl_also:'पुरानी फ़ाइलों के ये अतिरिक्त कॉलम भी चलते हैं:',
  deleted_entries:'हटाई गई एंट्री', notifications:'सूचनाएँ', audit_log:'ऑडिट लॉग',
  owner_only_note:'केवल मालिक के लिए।', all_read:'सभी को पढ़ा हुआ चिह्नित करें',
  from_l:'से', to_l:'तक', show:'दिखाएँ',
  bags_suffix:'बोरे', rock_waiting:'रॉक प्रतीक्षित', powder_ready:'पाउडर तैयार',
  grinding_loss:'पिसाई हानि', attachments:'अटैचमेंट',
  freight:'किराया', freight_payer:'किराया देने वाला', loading:'लोडिंग', unloading:'अनलोडिंग',
  load_payer:'लोडिंग/अनलोडिंग देने वाला', order_out:'जुड़ा ऑर्डर', repeat_trip:'पिछली ट्रिप दोहराएँ',
  in_rock:'रॉक अंदर', out_powder:'पाउडर बाहर',
  saved_tare:'सहेजा खाली वज़न मिल गया', vehicle_first:'पहले वाहन नंबर लिखें',
  no_old_trip:'इस वाहन की पुरानी ट्रिप नहीं मिली', filled_old:'पुरानी ट्रिप का विवरण भर दिया गया',
  listening:'सुन रहा हूँ… बोलें (पार्टी का नाम और नंबर)।',
  heard:'सुना: ', check_save:'— फ़ॉर्म भर दिया है, जाँचकर सहेजें दबाएँ।',
  voice_fail:'आवाज़ नहीं चली — Chrome ब्राउज़र और इंटरनेट चाहिए।',
  choose_folder_first:'पहले डेटा फ़ोल्डर लिखें',
  server_down:'सर्वर से संपर्क नहीं हो रहा — पृष्ठ ताज़ा करें।',
  setup_intro:'पहली बार सेटअप: डेटा फ़ोल्डर चुनें (ऐसी जगह जो MEGA / Google Drive से सिंक हो, बैकअप के लिए), फिर मालिक लॉगिन बनाएँ।',
  data_folder:'डेटा फ़ोल्डर', mill_name_l:'मिल का नाम', owner_wa:'मालिक WhatsApp', start_btn:'शुरू',
  imp_title:'एक्सेल आयात — पूर्वावलोकन', imp_rows:'पंक्तियाँ मिलीं', imp_ok:'ठीक हैं', imp_dup:'डुप्लिकेट',
  imp_wrong:'ग़लत', imp_note:'डुप्लिकेट रिकॉर्ड दोबारा नहीं जुड़ेंगे और ग़लत पंक्तियाँ छोड़ दी जाएँगी। पुष्टि करें तो केवल ठीक पंक्तियाँ सहेजी जाएँगी।',
  imp_do:'आयात करें', imp_done:'आयात पूर्ण', imp_added:'रिकॉर्ड जुड़े', imp_dup_skip:'डुप्लिकेट थीं (छोड़ दीं)',
  imp_wrong_rows:'ग़लत पंक्तियाँ', imp_none_bad:'कोई डुप्लिकेट या ग़लत पंक्ति नहीं थी।', row_l:'पंक्ति',
  chip_ok:'ठीक', chip_dup:'डुप्लिकेट', chip_bad:'ग़लत',
  summary_t:'सारांश', search_t:'खोज', own_word:'अपना',
  backup_warn:'दिन हो गए हैं अंतिम बैकअप को — डेटा पृष्ठ से एक क्लिक बैकअप लेकर MEGA / Google Drive में रखें।',
  backup_warn_start:'बैकअप को', pend_exp_t:'खर्च स्वीकृति लंबित',
  pend_exp_note:'लंबित खर्च लाभ-हानि में शामिल है; अस्वीकार करने से निकल जाएगा और नकद धारक के पास ही माना जाएगा।',
  pend_adj_note:'स्वीकृति से किताबी बोरे गिने गए बोरों के बराबर हो जाएँगे (गिनती समायोजन एंट्री लगेगी)।',
  wa_card_note:'सेटिंग्स में WhatsApp क्लाउड API (फ़ोन नंबर ID + टोकन) लगा हो तो अलर्ट ख़ुद चले जाते हैं। वरना हर अलर्ट के साथ एक टैप wa.me बटन है। SMS गेटवे लगा हो तो WhatsApp विफल होने पर SMS कोशिश होता है। स्थिति हर अलर्ट पर लिखी आती है।',
  proofs_t:'ग्राहक भुगतान सबूत (पुष्टि लंबित)', confirm_pay:'पुष्टि (भुगतान लग जाएगा)',
  view_proof:'देखें', when_l:'कब', to_l2:'को', message_l:'संदेश',
  maint_sec:'मरम्मत / बंदी', day_costs:'दिन के खर्च', diesel_l:'डीज़ल लीटर', elec_l:'बिजली यूनिट',
  day_cost_save:'दिन खर्च सहेजें', maint_note:'यहाँ केवल रोज़ की मात्रा दर्ज होती है, डायरी के रूप में। डीज़ल/बिजली की राशि ऊपर खर्च लेजर में लिखें, ताकि लाभ-हानि में दोहरा हिसाब न हो। मशीन मरम्मत और उसकी लागत मशीनें → मरम्मत डायरी में लिखें (वहाँ से लेजर में लगती है)।',
  cost_note:'खर्च लेजर की हर एंट्री केवल एक बार गिनी जाती है। डीज़ल/बिजली की मात्रा केवल प्रति टन लागत के लिए है, राशि लेजर से आती है।',
  head_new:'नया हेड बनाएँ', head_name:'हेड का नाम', head_parent:'मूल हेड (उप-हेड के लिए)', head_add:'हेड जोड़ें',
  main_head:'मुख्य हेड', sub_head:'उप हेड', paid_by_l:'देने वाला', paid_to_l:'पाने वाला',
  month_headwise:'इस महीने हेड अनुसार', paidto_wise:'पाने वाले अनुसार',
  chq_note:'चेक बाउंस हो तो स्थिति बाउंस करें — पार्टी का शेष ख़ुद दोबारा खुल जाएगा (वह भुगतान हिसाब से निकल जाती है)। क्लियर पर कोई अंतर नहीं।',
  no_cheque:'— कोई चेक नहीं', bankbook_empty:'सेटिंग्स में बैंक सूची जोड़ें — फिर हर बैंक का शेष यहाँ लाइव दिखेगा।',
  opening_bal:'प्रारंभिक शेष', payments_in_bank:'भुगतान अंदर (बैंक)', payments_out_bank:'भुगतान बाहर (बैंक)',
  expenses_bank:'खर्च (बैंक)', bank_balance:'शेष', txn_type:'प्रकार', ref_chq:'संदर्भ / चेक',
  dayend_t:'दिन अंत सारांश', vehicles_l:'वाहन', ground_bags:'पिसाई / बोरे', cash_net:'नकद नेट',
  expenses_l:'खर्च', send_dayend:'दिन अंत मालिक को भेजें', excel_range:'एक्सेल निर्यात — कैश बुक (तिथि सीमा)',
  total_net:'कुल नेट',
  handover_t:'नकद हैंडओवर (किसको नकद दिया)', holder_l:'धारक (मैनेजर / स्टाफ़)', other_name:'अन्य — नाम',
  handover_save:'हैंडओवर सहेजें', handover_note:'हैंडओवर एक स्थानांतरण है — खर्च नहीं; लाभ-हानि में नहीं जाता।',
  holder_limit_l:'धारक सीमा', approval_limit_l:'बड़े नकद खर्चों को इससे ऊपर मालिक स्वीकृति चाहिए',
  my_account:'— मेरा हिसाब', received_l:'मिला (हैंडओवर)', spent_l:'खर्च (नकद)',
  balance_in_hand:'हाथ में शेष', over_warn:'शेष से अधिक खर्च — हिसाब जाँचें',
  ack_pending:'हैंडओवर रसीद पुष्टि बाकी है', ack_btn:'नकद मिल गया', confirmed_l:'पुष्ट',
  in_mila:'अंदर (मिला)', out_kharcha:'बाहर (खर्च)', ginti_t:'नकद गिनती (भौतिक)',
  ginti_book:'किताबी शेष अभी', ginti_note:'गिनती सहेजने पर अंतर (कम/अधिक) रिकॉर्ड हो जाता है; किताबी शेष नहीं बदलता।',
  physical_cash:'भौतिक नकद (गिनकर)', ginti_save:'गिनती सहेजें', kam:'कम', zyada:'अधिक',
  detail_word:'विवरण', expense_ledger_note:'अस्वीकार करने से खर्च लाभ-हानि और धारक के खर्चे से निकल जाएगा — नकद धारक के पास ही माना जाएगा।',
  bio_t:'बायोमेट्रिक मशीनें', bio_note:'मशीन को फैक्टरी नेटवर्क (WiFi/LAN) पर इस पते पर सेट करें। मशीन का सीरियल नंबर यहाँ दर्ज करें — बिना दर्ज मशीन की हाज़िरी स्वीकार नहीं होगी। मज़दूर का डिवाइस कोड वही PIN/ID हो जो मशीन पर उस मज़दूर का है।',
  machine_name_l:'मशीन का नाम', serial_l:'सीरियल नंबर', last_seen:'अंतिम बार देखा', last_punch:'अंतिम हाज़िरी',
  csv_t:'CSV आयात (मशीन से निर्यात फ़ाइल)', csv_note:'कॉलम: device_code, date, time — या check_in। पहली हेडर पंक्ति ज़रूर हो।',
  import_punches:'हाज़िरी आयात', last_punches:'अंतिम हाज़िरियाँ',
  att_manual:'हाज़िरी (मैनुअल)', ot_auto:'(खाली छोड़ें = स्वतः)',
  leave_t:'छुट्टी रजिस्टर', approvals_t:'स्वीकृतियाँ — ओवरटाइम / हाज़िरी सुधार अनुरोध',
  leave_note:'स्वीकृत बिना वेतन छुट्टी वेतन वाले मज़दूर की इस महीने की कमाई से (वेतन/30 × दिन) कटती है।',
  send_request:'अनुरोध भेजें', request_sent:'अनुरोध भेज दिया — मालिक स्वीकृत करेगा',
  dept_note:'छुट्टी वाले दिन की ड्यूटी का सारा समय ओवरटाइम बनता है (यदि अनुमति हो)। बाकी दिनों में शिफ़्ट से अधिक समय ओवरटाइम है। ओवरटाइम मज़दूर के देय में ख़ुद शामिल होता है।',
  off_days:'छुट्टी के दिन', ot_rate:'ओवरटाइम दर / घंटा', ot_allowed:'ओवरटाइम अनुमति', shift_t2:'शिफ़्ट',
  worker_type:'प्रकार', theka_l:'ठेका (प्रति टन/बोरा)', salary_l:'वेतन', rate_ton_out:'दर / टन बाहर (ठेका)',
  rate_bag:'दर / बोरा (ठेका)', monthly_salary:'मासिक वेतन', device_code:'बायोमेट्रिक डिवाइस कोड',
  start_date:'शुरू तिथि', payout_t:'भुगतान / एडवांस', advance_l:'एडवांस', payment_l:'भुगतान',
  earned_l:'कमाया', taken_l:'लिया', due_l:'देय (शेष)', code_l:'कोड',
  theka_note:'ठेका कमाई = कुल पाउडर बाहर टन × दर + उत्पादन बोरे × दर + ओवरटाइम। वेतन कमाई = मासिक वेतन − स्वीकृत बिना वेतन छुट्टी का हिस्सा + ओवरटाइम।',
  own_purchase_t:'अपनी ख़रीद — रॉक (सप्लायर से)', own_sale_t:'अपनी बिक्री — पाउडर (ख़रीदार को)',
  ded_l:'नमी / मिट्टी कटौती %', rate_locked:'दर लॉक बुकिंग', fulfilled_note:'पूरा = वे बाहर ट्रिप/बिक्री जिन पर यह ऑर्डर चुना गया था।',
  out_warn:'बाहर पर बोरे तैयार से अधिक हों तो सिस्टम चेतावनी देता है (एंट्री रुकती नहीं)।',
  party_bags_t:'पार्टी के बोरे', received_opt:'पार्टी से प्राप्त', returned_opt:'पार्टी को वापस',
  bag_type_l:'बोरे का प्रकार', bags_mill_opt:'मिल के बोरे (बरदाना)', bags_party_opt:'पार्टी के बोरे',
  powder_bags:'बने हुए पाउडर बोरे', filter_powder_l:'फ़िल्टर पाउडर', entries_l:'प्रविष्टियाँ',
  filter_bags_l:'फ़िल्टर पाउडर बोरे', bag_weights_l:'बोरे के वज़न की डिफ़ॉल्ट',
  powder_bag_kg_l:'पाउडर बोरा (किलो)', filter_bag_kg_l:'फ़िल्टर बोरा (किलो)', total_production_l:'कुल उत्पादन',
  bag_weights_hint:'एक बोरे में किलो — नई एंट्रियों पर यही वज़न लागू होता है; सहेजा गया रिकॉर्ड हमेशा अपने दिन का वज़न रखता है।',
  stock_count_t:'भौतिक स्टॉक गिनती', item_l:'वस्तु', counted_l:'गिना गया', book_l:'किताबी', diff_l:'अंतर',
  came:'आए', used_l:'उपयोग', returned_l:'वापस', left_l:'बचे',
  bardana_used:'उत्पादन में उपयोग बोरे', bardana_in:'कुल अंदर', bardana_out:'कुल बाहर',
  dir_in_bags:'अंदर — नए बोरे प्राप्त', dir_out_bags:'बाहर — बोरे जारी / ख़राब',
  own_bags_line:'अपने बोरे', made_l:'बने', sold_l:'बिके',
  last_rate_g:'अंतिम पिसाई दर', last_rate_p:'अंतिम ख़रीद दर',
  entry_t:'एंट्री', now_grinding_party:'पार्टी (खाली छोड़ें = अपना)',
  rock_in_full:'रॉक अंदर (कुल)', edit_user_msg:'बदला जा रहा है — रोल/पहुँच बदलकर परिवर्तन सहेजें दबाएँ।',
  save_changes:'परिवर्तन सहेजें', new_pw:'नया पासवर्ड लिखें:', pw_changed:'पासवर्ड बदल गया',
  staff_access_note:'स्टाफ़ लॉगिन केवल टिक की गई चीज़ों तक पहुँचता है — सर्वर भी वही रोकता है, केवल मेनू नहीं छिपता। ग्राहक लॉगिन केवल अपना खाता/स्टॉक/शेष देखता है। 5 ग़लत पासवर्ड पर लॉगिन 15 मिनट बंद हो जाता है।',
  client_party:'ग्राहक की पार्टी', access_staff:'पहुँच (स्टाफ़)', role_l:'रोल',
  only_owner_logins:'केवल मालिक लॉगिन बना सकता है।', staff_access_t:'स्टाफ़ पहुँच — जो काम इस लॉगिन को देना है वह टिक करें (बाकी सब बंद)',
  access_token:'पहुँच टोकन', token_hint:'टोकन खाली छोड़ें तो पुराना रहता है; स्क्रीन पर टोकन कभी पूरा नहीं दिखता',
  sms_t:'SMS गेटवे (वैकल्पिक)', sms_note:'URL में {to} {msg} {key} {sender} स्थान उपयोग करें।',
  sender_id:'प्रेषक ID', phone_id:'फ़ोन नंबर ID',
  wa_auto_t:'WhatsApp स्वतः भेजना (क्लाउड API)', wa_auto_note:'Meta WhatsApp क्लाउड API से फ़ोन नंबर ID और पहुँच टोकन यहाँ लगाएँ तो अलर्ट ख़ुद भेजते हैं। पहले Meta पर ये 7 टेम्पलेट स्वीकृत करवाने होते हैं:',
  cash_rules_t:'नकद नियम (हाथ में नकद)', holder_limit_f:'धारक सीमा (Rs) — एक धारक के पास इससे अधिक नकद पर चेतावनी',
  approval_limit_f:'स्वीकृति सीमा (Rs) — मैनेजर/स्टाफ़ का इससे बड़ा नकद खर्च मालिक स्वीकृति माँगता है',
  bank_opening_t:'बैंक प्रारंभिक शेष', bank_opening_f:'— प्रारंभिक शेष (Rs)',
  bank_first:'पहले नीचे बैंक सूची में बैंक जोड़ें, फिर यहाँ प्रारंभिक शेष मिलेगा।',
  bank_list_t:'बैंक सूची व डेटा', bank_list_f:'बैंक खाते (हर पंक्ति एक — भुगतान में सूची)',
  db_file:'डेटाबेस फ़ाइल', bio_addr:'बायोमेट्रिक पता (मशीन पर यह लिखें)', backup_folder:'बैकअप फ़ोल्डर',
  db_move:'डेटाबेस नए फ़ोल्डर में ले जाएँ', save_settings:'सेटिंग्स सहेजें',
  appearance_t:'रूप — थीम रंग', appearance_note:'पूरे सिस्टम का रंग — हेडर, बटन, साइडबार और लॉगिन स्क्रीन सब पर यही रंग आएगा, मिल के हर लॉगिन पर।',
  logo_t:'मिल लोगो', logo_none:'अभी कोई लोगो नहीं लगा है।', logo_file_f:'लोगो फ़ाइल (PNG / JPG / WebP — अपलोड पर ख़ुद 256px तक छोटी हो जाती है)',
  replace_logo:'लोगो बदलें', upload_logo:'लोगो लगाएँ', remove_l:'हटाएँ', logo_first:'पहले लोगो फ़ाइल चुनें',
  logo_done:'लोगो लग गया', logo_removed:'लोगो हटा दिया', logo_fail:'लोगो अपलोड नहीं हुआ',
  settings_saved:'सेटिंग्स सहेजी गईं', theme_done:'थीम रंग लग गया',
  data_backup_t:'बैकअप', data_last:'अंतिम बैकअप', data_never:'कभी नहीं', data_days_ago:'दिन पहले',
  backup_btn:'एक क्लिक पूर्ण बैकअप (ZIP)', backup_note:'ZIP में डेटाबेस + हर तालिका की CSV + सारे अटैचमेंट होते हैं। फ़ाइल को MEGA / Google Drive में ज़रूर रखें (बैकअप फ़ोल्डर को Drive/MEGA सिंक फ़ोल्डर रख दें तो ख़ुद हो जाता है)।',
  restore_t:'बहाल', export_t:'निर्यात (CSV / एक्सेल)', import_t:'आयात (CSV) — पहले पूर्वावलोकन',
  table_l:'तालिका', paste_ph:'हेडर पंक्ति + डेटा पंक्तियाँ चिपकाएँ', preview_btn:'पूर्वावलोकन', import_btn:'आयात करें',
  backup_done:'बैकअप बन गया', restore_done:'बहाल हो गया — सुरक्षा बैकअप:', restore_q:'बहाल करें? पहले सुरक्षा बैकअप ख़ुद बन जाएगा।',
  import_done:'आयात हो गया', rows_l:'पंक्तियाँ',
  proof_sent:'सबूत भेज दिया — मिल पुष्टि करेगा तो खाते में लग जाएगी।',
  my_proofs:'मेरी भेजी हुई रसीदें', sess_started:'पिसाई सेशन शुरू हो गया', sess_stopped:'पिसाई सेशन बंद हो गया',
  trip_saved:'ट्रिप सहेजी गई — नेट', photo_attached:'+ तस्वीर संलग्न', wa_ready:'— WhatsApp अलर्ट अलर्ट पृष्ठ में तैयार है।',
  job_saved:'पिसाई सहेजी गई — राशि', prod_saved:'उत्पादन सहेजा गया', party_saved:'पार्टी सहेजी गई',
  worker_saved:'मज़दूर सहेजा गया', payout_saved:'भुगतान सहेजा गया', dept_saved:'विभाग सहेजा गया',
  att_saved:'हाज़िरी सहेजी गई — ओवरटाइम:', machine_reg:'मशीन दर्ज हो गई — पता:',
  import_punches_done:'हाज़िरियाँ ठीक,', skip_l:'छोड़ दीं', leave_saved:'छुट्टी सहेजी गई',
  head_saved:'हेड सहेजा गया', expense_saved:'खर्च सहेजा गया', bill_attached:'+ बिल संलग्न',
  approval_pending:'— स्वीकृति लंबित है', maint_saved:'मरम्मत सहेजी गई', daycost_saved:'दिन खर्च सहेजे गए',
  handover_saved:'हैंडओवर सहेजा गया', ack_note2:'— धारक अपने लॉगिन से नकद मिल गया की पुष्टि करेगा',
  ack_done:'नकद मिल गया — पुष्टि हो गई', ginti_saved:'नकद गिनती सहेजी', book_w:'किताबी:', ginti_w:'गिनती:',
  payment_saved:'भुगतान सहेजा गया', proof_attached2:'+ सबूत संलग्न',
  order_saved:'ऑर्डर सहेजा गया', order_closed:'ऑर्डर बंद हो गया', purchase_saved:'ख़रीद सहेजी गई — बिल',
  sale_saved:'बिक्री सहेजी गई', cheque_done:'चेक', reminder_made:'रिमाइंडर बन गए',
  proof_confirm_done:'सबूत पुष्ट — भुगतान खाते में लग गई', proof_rejected:'सबूत अस्वीकार हो गया',
  profile_t:'मेरी प्रोफ़ाइल', disp_name_l:'दिखने वाला नाम', phone_wa_l:'फ़ोन / WhatsApp नंबर', cur_pw_l:'मौजूदा पासवर्ड', profile_saved:'प्रोफ़ाइल सहेजी गई ✓', pw_changed_l:'पासवर्ड बदल गया ✓ — बाकी डिवाइस साइन आउट हो गए', avatar_l:'प्रोफ़ाइल तस्वीर', avatar_hint:'JPG / PNG / WebP — ख़ुद छोटी हो जाती है; सीमा 2 MB', avatar_change_l:'📷 बदलें', avatar_remove_l:'हटाएँ', cred_sent_l:'भेज दिया',
  login_created:'लॉगिन बन गया', login_updated:'लॉगिन ताज़ा हो गया (उस लॉगिन का पुराना सेशन बंद — दोबारा लॉगिन होगा)',
  expense_approved:'खर्च स्वीकृत हो गया', expense_rejected:'खर्च अस्वीकृत हो गया — लाभ-हानि और धारक हिसाब से निकल गया',
  leave_done:'छुट्टी', request_done:'अनुरोध', alert_status:'अलर्ट स्थिति:',
  dayend_msg:'दिन अंत पाठ:', dayend_hint:'— अलर्ट पृष्ठ से मालिक को भेजा जा सकता है।',
  rec_del_note:'मालिक को अलर्ट जाएगा और हटाई गई एंट्री से बहाल हो सकता है।',
  delete_q:'हटाएँ?', cancel_l:'रद्द', delete_l:'हटाएँ',
  choose_l:'चुनें...', setup_word:'सेटअप', theme_colour_l:'थीम रंग',
  purchase_l:'ख़रीद', deleted_ok2:'रिकॉर्ड हटाया गया \u2713',
  login_user_l:'उपयोगकर्ता नाम या ईमेल', forgot_pw:'पासवर्ड भूल गए?', forgot_t:'पासवर्ड रीसेट',
  forgot_hint:'अपना उपयोगकर्ता नाम या ईमेल लिखें। यदि खाते पर ईमेल सहेजा है तो रीसेट लिंक उसी पर भेजा जाएगा (60 मिनट मान्य)।',
  send_link:'रीसेट लिंक भेजें', forgot_sent:'यदि खाता मौजूद है तो रीसेट ईमेल भेज दिया गया है। इनबॉक्स (और स्पैम फ़ोल्डर) देख लें।',
  back_login:'लॉगिन पर वापस', email_l:'ईमेल',
  email_t:'ईमेल (SMTP)', email_note:'खाता विवरण, भुगतान रसीदों और मालिक अलर्ट की ईमेल प्रतियाँ — आपके अपने मेल खाते (SMTP) से जाती हैं। दोनों संस्करणों में काम करती है।',
  email_gmail_hint:'Gmail: होस्ट smtp.gmail.com, पोर्ट 587, सुरक्षा STARTTLS, उपयोगकर्ता नाम = आपका Gmail पता, पासवर्ड = ऐप पासवर्ड (Google खाता → सुरक्षा → ऐप पासवर्ड) — सामान्य Gmail पासवर्ड काम नहीं करता।',
  smtp_host_l:'SMTP होस्ट', smtp_port_l:'पोर्ट', smtp_sec_l:'सुरक्षा', smtp_user_l:'SMTP उपयोगकर्ता नाम', smtp_pass_l:'SMTP पासवर्ड',
  from_name_l:'भेजने वाले का नाम', from_email_l:'भेजने वाले की ईमेल (वैकल्पिक)',
  mail_on_l:'ईमेल भेजना ON', mail_test_t:'टेस्ट प्राप्तकर्ता (वैकल्पिक)', mail_test_btn:'टेस्ट ईमेल भेजें',
  mail_test_first:'पहले सेटिंग्स सहेजें, फिर टेस्ट करें।', mail_sent_to:'टेस्ट ईमेल भेजा गया:',
  sys_addr_l:'सिस्टम पता (रीसेट लिंक्स के लिए)', sys_addr_hint:'वह पता जिस पर लोग यह सिस्टम खोलते हैं — पासवर्ड रीसेट लिंक्स में यही लगता है। खाली छोड़ें तो वर्तमान विज़िट का पता उपयोग होगा। फ़ैक्टरी PC पर यहाँ PC का LAN पता लिखें (जैसे http://192.168.1.10:8765)।',
  mail_ev_t:'ईमेल सूचनाएँ — ईमेल भी जाए जब:',
  mail_ev_proof_l:'ग्राहक भुगतान का प्रमाण भेजे → मालिक को', mail_ev_payment_l:'भुगतान प्राप्त हो → पार्टी को',
  mail_ev_voucher_l:'गाड़ी अंदर/बाहर वाउचर बने → पार्टी को', mail_ev_dayend_l:'दिन अंत सारांश खुले → मालिक को (रोज़ एक बार)',
  send_email_btn:'ईमेल भेजें', email_sent_ok:'ईमेल भेजा गया ✓',
  wa_guide_t:'यह सेटअप कैसे करें — चरण-दर-चरण',
  wa_guide:'<b>हर खाना क्या है</b><ul><li><b>फ़ोन नंबर ID</b> — आपके WhatsApp Business नंबर की पहचान (एक लंबा नंबर जो Meta के API Setup पृष्ठ पर दिखता है — यह ख़ुद फ़ोन नंबर नहीं है)। अलर्ट इसी नंबर से जाते हैं।</li><li><b>एक्सेस टोकन</b> — वह गुप्त कुंजी जो इस सिस्टम को उस नंबर से भेजने की अनुमति देती है। जिसके पास यह हो वह आप बनकर भेज सकता है — कभी किसी से साझा न करें।</li><li><b>टेम्पलेट</b> — WhatsApp स्वचालित संदेश केवल पहले से स्वीकृत टेम्पलेट में भेजने देता है। ऊपर लिखे 7 नामों के टेम्पलेट आपके Meta खाते में उन्हीं वर्तनी से बने और स्वीकृत होने चाहिए। login_credentials टेम्पलेट में 4 चीज़ें इसी क्रम से जाती हैं: मिल का नाम, उपयोगकर्ता नाम, पासवर्ड, लॉगिन लिंक।</li><li><b>SMS पता / कुंजी / भेजने वाला ID</b> (वैकल्पिक) — WhatsApp विफल हो तो कोशिश होने वाला SMS गेटवे। पते में {to} {msg} {key} {sender} लग सकते हैं।</li></ul><b>फ़ोन नंबर ID और टोकन कहाँ से मिलेगा</b><ol><li><b>developers.facebook.com</b> खोलें → My Apps → Create App → <b>Business</b> चुनें (या अपना मौजूदा Meta Business खाता खोलें)।</li><li>ऐप में <b>WhatsApp</b> उत्पाद जोड़ें, फिर <b>WhatsApp → API Setup</b> खोलें।</li><li>वहाँ बिज़नेस फ़ोन नंबर रजिस्टर करें। उसी पृष्ठ पर उसका <b>Phone Number ID</b> दिखेगा — ऊपर वाले खाने में लगा दें।</li><li>स्थायी टोकन के लिए: <b>Business Settings → Users → System Users</b> → सिस्टम उपयोगकर्ता बनाएँ, उसे <b>whatsapp_business_messaging</b> अनुमति दें, उसका टोकन बनाएँ और ऊपर लगा दें।</li><li><b>WhatsApp → Message Templates</b> में ऊपर वाले 7 नामों के टेम्पलेट बनाएँ और स्वीकृति की प्रतीक्षा करें (आमतौर पर कुछ घंटे)।</li><li>यहाँ सहेज दें — अलर्ट और वाउचर अब ख़ुद जाएँगे; जो न जाए उस पर एक टैप wa.me बटन रहेगा।</li></ol>',
  email_guide_t:'यह सेटअप कैसे करें — चरण-दर-चरण',
  email_guide:'<b>हर खाना क्या है</b><ul><li><b>SMTP होस्ट / पोर्ट / सुरक्षा</b> — आपके ईमेल प्रदाता का भेजने वाला सर्वर। होस्ट + पोर्ट प्रदाता से मिलते हैं (उदाहरण नीचे हैं)। सुरक्षा: <b>STARTTLS</b> आमतौर पर पोर्ट <b>587</b> के साथ, <b>SSL</b> पोर्ट <b>465</b> के साथ।</li><li><b>SMTP उपयोगकर्ता नाम</b> — लगभग हमेशा आपका पूरा ईमेल पता होता है।</li><li><b>SMTP पासवर्ड</b> — उस मेलबॉक्स का पासवर्ड। Gmail और Yahoo यहाँ सामान्य पासवर्ड स्वीकार नहीं करते — उन्हें <b>ऐप पासवर्ड</b> चाहिए (चरण नीचे हैं)।</li><li><b>भेजने वाले का नाम / ईमेल</b> — प्राप्तकर्ता को यही दिखता है। ईमेल खाली हो तो SMTP उपयोगकर्ता नाम ही लगता है।</li><li><b>सिस्टम पता</b> — इस सिस्टम का अपना वेब पता। पासवर्ड रीसेट ईमेल का लिंक इसी से बनता है, इसलिए वही पता हो जो लोग असल में खोलते हैं।</li></ul><b>Gmail — आम स्थिति</b><ol><li><b>myaccount.google.com → Security</b> खोलें और <b>2-Step Verification</b> ON करें (ऐप पासवर्ड इसी के बाद बनता है)।</li><li>उसी Security पृष्ठ पर → <b>App passwords</b> → नाम जैसे Mill → Create। Google 16 अक्षरों का पासवर्ड दिखाएगा — कॉपी कर लें।</li><li>यहाँ लिखें: होस्ट <b>smtp.gmail.com</b>, पोर्ट <b>587</b>, सुरक्षा <b>STARTTLS</b>, उपयोगकर्ता नाम = आपका Gmail पता, पासवर्ड = वही ऐप पासवर्ड।</li><li>सहेजें, <b>ईमेल भेजना ON</b> करें, फिर <b>टेस्ट ईमेल भेजें</b> दबाएँ — परिणाम (या सर्वर की त्रुटि) वैसा ही दिखेगा।</li></ol><b>अन्य प्रदाता</b><ul><li><b>Outlook / Hotmail:</b> smtp.office365.com, पोर्ट 587, STARTTLS।</li><li><b>Yahoo:</b> smtp.mail.yahoo.com, पोर्ट 465, SSL — इसे भी ऐप पासवर्ड चाहिए (Yahoo Account Security → Generate app password)।</li></ul>',
  acc_register:'उपस्थिति रजिस्टर',
  ib_need_t:'क्या चाहिए होगा', ib_tips_t:'टिप्स और सुरक्षा',
  ib_wa_need:'<li><b>Meta Business</b> खाता जिसमें WhatsApp उत्पाद जुड़ा हो</li><li>पंजीकृत WhatsApp Business फ़ोन नंबर</li><li>उसका <b>Phone Number ID</b> और स्थायी <b>Access Token</b> (System User से मिलता है)</li><li>नीचे लिखे 7 टेम्पलेट Meta में बिल्कुल उन्हीं नामों से स्वीकृत हों</li>',
  ib_wa_tips:'<li>Access Token गुप्त कुंजी है — जिसके पास हो वह आप बनकर भेज सकता है, इसलिए कभी साझा न करें</li><li>स्थायी System User टोकन इस्तेमाल करें; अस्थायी टेस्ट टोकन 24 घंटे में खत्म हो जाता है</li><li>टेम्पलेट के नाम बिल्कुल वही हों वरना भेजना विफल होगा</li><li>जो संदेश खुद न भेजा जा सके उस पर एक-टैप wa.me बटन रहता है</li>',
  ib_mail_need:'<li>आपके प्रदाता का <b>SMTP होस्ट + पोर्ट</b> (Gmail: smtp.gmail.com, 587 — Outlook: smtp.office365.com, 587)</li><li><b>SMTP उपयोगकर्ता नाम</b> के रूप में आपका पूरा ईमेल पता</li><li>Gmail या Yahoo के लिए <b>App Password</b> — सामान्य पासवर्ड स्वीकार नहीं होता</li><li>वह <b>सिस्टम पता</b> जो लोग असल में खोलते हैं — रीसेट लिंक उसी से बनता है</li>',
  ib_mail_tips:'<li><b>STARTTLS</b> पोर्ट 587 के साथ और <b>SSL</b> पोर्ट 465 के साथ जाता है</li><li>पहले सेटिंग्स सहेजें, फिर <b>टेस्ट ईमेल भेजें</b> दबाएँ — सर्वर का असली जवाब वैसा ही दिखाया जाता है</li><li>SMTP पासवर्ड केवल सर्वर पर रखा जाता है और कभी वापस नहीं दिखाया जाता</li><li>From ईमेल वैकल्पिक है — खाली हो तो SMTP उपयोगकर्ता नाम ही इस्तेमाल होता है</li>',
  mail_preset_l:'ईमेल सेवा',
  mail_preset_custom:'कस्टम (मैन्युअल)', mail_preset_gmail:'Gmail',
  mail_preset_brevo:'Brevo — मुफ़्त प्लान (रोज़ 300 ईमेल)', mail_preset_smtp2go:'SMTP2GO — मुफ़्त प्लान (महीने में 1,000 ईमेल)',
  mail_preset_hostinger:'Hostinger', mail_preset_outlook:'Microsoft 365 / Outlook',
  mail_note_custom:'मैन्युअल सेटअप — वही होस्ट, पोर्ट और पासवर्ड लिखें जो आपका अपना ईमेल प्रदाता देता है।',
  mail_note_gmail:'खाता: सामान्य Google खाता। पासवर्ड = <b>ऐप पासवर्ड</b>, आपका Gmail पासवर्ड नहीं: 2-Step Verification ON करें, फिर Google खाता → Security → ऐप पासवर्ड (16 अक्षर — पूरे चरण नीचे गाइड में हैं)। Gmail की मुफ़्त सीमा: रोज़ 500 ईमेल। भेजने वाले के रूप में आपका Gmail पता ख़ुद लग जाता है।',
  mail_note_brevo:'<b>brevo.com</b> पर मुफ़्त खाता बनाएँ — क्रेडिट कार्ड नहीं चाहिए, हमेशा मुफ़्त: <b>रोज़ 300 ईमेल</b>। SMTP उपयोगकर्ता नाम = वही ईमेल जिससे आप Brevo में लॉग इन करते हैं। SMTP पासवर्ड = एक <b>SMTP कुंजी</b>, खाता पासवर्ड नहीं: Brevo → Settings → SMTP & API → नई SMTP कुंजी बनाएँ। भेजने वाले की पुष्टि: अपनी From ईमेल को Brevo → Senders में पुष्ट करें, या अपना डोमेन लगाएँ (Brevo SPF/DKIM रिकॉर्ड दिखाता है)।',
  mail_note_smtp2go:'<b>smtp2go.com</b> पर मुफ़्त खाता बनाएँ — क्रेडिट कार्ड नहीं चाहिए, <b>महीने में 1,000 ईमेल हमेशा मुफ़्त</b>। डोमेन पुष्टि से पहले सीमा: रोज़ 200 और प्रति घंटा 25। उपयोगकर्ता नाम + पासवर्ड = एक अलग जोड़ा जो आप Sending → SMTP Users में बनाते हैं (खाता लॉगिन नहीं)। पुष्ट भेजने वाला डोमेन ज़रूरी है: SMTP2GO के दिखाए 3 CNAME रिकॉर्ड लगाएँ।',
  mail_note_hostinger:'आपके अपने डोमेन के उस मेलबॉक्स के लिए जो Hostinger पर है (hPanel → Emails)। पासवर्ड = उसी मेलबॉक्स का अपना पासवर्ड (जो hPanel वेबमेल में लगता है)। भेजने की सीमा Hostinger की अपनी लागू होती है।',
  mail_note_outlook:'Microsoft 365 / Outlook मेलबॉक्स के लिए। पासवर्ड = मेलबॉक्स का पासवर्ड, और उस मेलबॉक्स पर <b>SMTP AUTH चालू</b> होना ज़रूरी है (Microsoft 365 admin → Users → Mail → Manage email apps) वरना भेजना अस्वीकार हो जाएगा।',
  accd_profile:'मिल का नाम, संपर्क, अलर्ट समय और लोगो — हेडर, पर्ची और इनवॉइस पर दिखता है।',
  accd_appearance:'पूरे सिस्टम का रंग — हेडर, बटन, साइडबार और लॉगिन स्क्रीन।',
  accd_fontprint:'स्क्रीन व प्रिंट फ़ॉन्ट, पाठ आकार, बोल्ड शीर्षक और वाउचर प्रतियाँ।',
  accd_voice:'गाड़ी और भुगतान दर्ज होने पर बोली जाने वाली सूचनाएँ।',
  accd_whatsapp:'Meta WhatsApp क्लाउड API — अलर्ट, वाउचर और रिमाइंडर ख़ुद भेजते हैं।',
  accd_email:'आपका अपना मेल खाता (SMTP) — विवरण, रसीदें और अलर्ट ईमेल से।',
  accd_cash:'हाथ नकद की सीमा, स्वीकृति सीमा और बैंक प्रारंभिक शेष।',
  accd_banks:'बैंक खातों की सूची, डेटाबेस फ़ाइल, बैकअप फ़ोल्डर और बायोमेट्रिक पता।',
  accd_session:'पिसाई सत्र शुरू करें, या चल रहा बंद करें।',
  accd_gp_entry:'हर काम की एक एंट्री: पार्टी, शिफ़्ट, ग्रेड, पाउडर बोरे और फ़िल्टर बोरे।',
  accd_closures:'हाल की शिफ़्टें जब फ़ैक्ट्री बंद रही, कारण के साथ।',
  accd_records:'सहेजी प्रविष्टियाँ, नई पहले — मालिक बदल या हटा सकता है।',
  accd_wh_overview:'बोरे बने, बोरे गए और बोरे तैयार — हर पार्टी और अपने।',
  accd_ginti:'किताबी स्टॉक से असली गिनती का मिलान — अंतर और समायोजन।',
  accd_bags:'मिल का बरदाना और पार्टी बोरे — आए, इस्तेमाल, वापस और बाकी।',
  accd_stockcount:'किसी भी स्टॉक वस्तु की गिनती करें और किताबी संख्या से मिलाएँ।',
  accd_trade:'इस पार्टी की बिना गेट ख़रीद या बिक्री — रॉक, पाउडर या कोई अन्य वस्तु।',
  accd_khata:'इस पार्टी का हर डेबिट और क्रेडिट, चलते शेष के साथ।',
  accd_os_summary:'मिल के पास पड़ा रॉक, पाउडर, फ़िल्टर पाउडर और बोरे, व्यापार योग के साथ।',
  accd_workers:'मज़दूर जोड़ें और हर मज़दूर की कमाई, ली हुई और बाकी राशि देखें।',
  accd_payouts:'मज़दूर को भुगतान करें — वेतन या एडवांस — और पिछले भुगतान देखें।',
  accd_att_manual:'मज़दूर की हाज़िरी लगाएँ — आगमन, प्रस्थान और ओवरटाइम के साथ।',
  accd_bio:'बायोमेट्रिक मशीनें, CSV पंच आयात और ताज़ा पंच।',
  accd_leave:'मज़दूर की छुट्टी दर्ज करें — सवैतन या अवैतन — और लंबित पर निर्णय करें।',
  accd_approvals:'ओवरटाइम और उपस्थिति सुधार के अनुरोध, और उनके निर्णय।',
  accd_expense_entry:'खर्च उसके हेड में दर्ज करें — ज़रूरत पर नया हेड भी बनाएँ।',
  accd_expense_summary:'इस महीने का खर्च, हेड के हिसाब से और प्राप्तकर्ता के हिसाब से।',
  accd_daycosts:'लागत रिपोर्ट के लिए आज के डीज़ल लीटर और बिजली यूनिट।',
  accd_cashbook:'आज का पैसा अंदर व बाहर — नकद, बैंक, ऑनलाइन और चेक के हिसाब से।',
  accd_dayend:'पूरा दिन एक सारांश में — गाड़ियाँ, पिसाई, नकद और खर्चे।',
  accd_excel:'किसी भी तिथि सीमा की कैश बुक Excel, CSV या PDF में डाउनलोड करें।',
  accd_bankbook:'हर बैंक खाता — प्रारंभिक शेष, आवाजाही और लेन-देन।',
  accd_pnl:'इस महीने की आय, लागत और शुद्ध लाभ — फ़ैक्ट्री बंद दिनों के साथ।',
  accd_cpt:'किसी भी अवधि के लिए खर्च और आय, पिसे हुए टन पर विभाजित।',
  accd_biz:'पिसाई, शुल्क, बिक्री और ख़रीद — पार्टी दर पार्टी, नेट के साथ।',
  accd_deleted:'हटाई प्रविष्टियाँ यहाँ रहती हैं — मालिक कोई भी वापस ला सकता है।',
  accd_notifs:'मालिक के लिए सिस्टम सूचनाएँ — प्रमाण, अलर्ट और अपडेट।',
  accd_audit:'किसने क्या किया, और कब — पूरा गतिविधि रिकॉर्ड।',
  accd_alerts:'WhatsApp, SMS और ईमेल के लिए तैयार रिमाइंडर — भेजें या फिर भेजें।',
  accd_proofs:'ग्राहकों के भेजे भुगतान प्रमाण — पुष्टि करें तो भुगतान लग जाए।',
  accd_backup:'पूरे डेटाबेस का एक क्लिक बैकअप, और फ़ाइल से बहाली।',
  accd_export:'कोई भी तालिका CSV फ़ाइल में डाउनलोड करें।',
  accd_import:'रिकॉर्ड लाने के लिए CSV पंक्तियाँ लगाएँ — पहले पूर्वावलोकन, फिर आयात।',
  accd_demo:'आज़माइश के लिए सिस्टम में नमूना डेटा भरें, या हटा दें।',
  accd_machines:'मिल की मशीनें यहाँ दर्ज करें — सेवा और मरम्मत डायरी में लिखी जाती है।',
  accd_diary:'हर सेवा, मरम्मत और पुर्ज़ा बदलाव, लागत और अगली तारीख़ के साथ।',
  accd_proofup:'मिल को भुगतान का प्रमाण भेजें, और पहले भेजे हुए देखें।',
  open:'खोलें' }
};
function t(k){ return (I18N[PREFS.lang] && I18N[PREFS.lang][k]) || I18N.en[k] || k; }

/* ---------------- helpers ---------------- */
const $ = s => document.querySelector(s);
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => 'Rs ' + Number(n || 0).toLocaleString('en-PK', {maximumFractionDigits: 0});
const fmtN = n => Number(n || 0).toLocaleString('en-PK', {maximumFractionDigits: 2});
/* Party khata balance direction label (presentation only — the sign
   convention never changes): + = party owes us (To Receive),
   - = we owe the party (To Pay), 0 = Clear / khata saaf. */
const balTag = v => { const n = Number(v || 0); return `<span class="baltag">${t(n > 0 ? 'to_receive' : n < 0 ? 'to_pay' : 'bal_clear')}</span>`; };
const MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function dfmt(iso){ if (!iso) return ''; const p = String(iso).slice(0, 10).split('-');
  return p.length < 3 ? String(iso) : (+p[2]) + ' ' + (MONTHS_EN[+p[1] - 1] || '') + ' ' + p[0]; }
function kgDisp(kg){
  kg = Number(kg || 0);
  if (PREFS.unit === 't') return (kg / 1000).toFixed(3) + ' t';
  if (PREFS.unit === 'maund') return (kg / 40).toFixed(2) + ' md';
  return fmtN(kg) + ' kg';
}
/* Weights are always STORED in kg; entry/display follow the chosen unit. */
const UNIT_TO_KG = { kg: 1, t: 1000, maund: 40 };
function unitLabel(){ return PREFS.unit === 't' ? 'tons' : (PREFS.unit === 'maund' ? 'maund' : 'kg'); }
function toKgVal(v){ return Math.round((parseFloat(v) || 0) * (UNIT_TO_KG[PREFS.unit] || 1)); }
function fromKgVal(kg){ const f = UNIT_TO_KG[PREFS.unit] || 1; return Math.round(((kg || 0) / f) * 1000) / 1000; }
function toTonsVal(v){ return Math.round(((parseFloat(v) || 0) * (UNIT_TO_KG[PREFS.unit] || 1) / 1000) * 1000) / 1000; }
function tonsDisp(tons){ return kgDisp((tons || 0) * 1000); }
async function api(path, opts){
  const r = await fetch(path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}));
  let data = {};
  try { data = await r.json(); } catch (e) {}
  if (!r.ok) throw Object.assign(new Error(data.error || ('HTTP ' + r.status)), { status: r.status, data });
  return data;
}
const get = p => api(p);
const post = (p, b) => api(p, { method: 'POST', body: JSON.stringify(b || {}) });
function todayStr(){ const d = new Date(); return d.toISOString().slice(0, 10); }
function msg(text, cls){ const m = $('#msg'); if (m) { m.className = 'msg ' + (cls || ''); m.textContent = text; m.style.display = 'block'; } }
/* ---------- ONE global save-confirmation popup ----------
   Every successful create / edit / save in the app routes through
   okPopup(): a centered modal with a big tick that survives render()
   (it lives on document.body, outside #app), auto-closes in ~2.5s,
   and can never stack — one element is reused for every save. */
let _okTimer = null;
function okPopup(text){
  let ov = document.getElementById('okpop');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'okpop'; ov.className = 'okpop';
    ov.innerHTML = '<div class="okcard"><div class="oktick">✓</div><div class="oktext"></div><button type="button" class="okbtn">OK</button></div>';
    ov.querySelector('.okbtn').addEventListener('click', closeOk);
    ov.addEventListener('click', e => { if (e.target === ov) closeOk(); });
    document.body.appendChild(ov);
  }
  ov.querySelector('.oktext').textContent = text || t('saved');
  ov.style.display = 'flex';
  if (_okTimer) clearTimeout(_okTimer);
  _okTimer = setTimeout(closeOk, 2500);
  return ov;
}
function closeOk(){
  const ov = document.getElementById('okpop');
  if (ov) ov.style.display = 'none';
  if (_okTimer) { clearTimeout(_okTimer); _okTimer = null; }
}
window.okPopup = okPopup; window.closeOk = closeOk;
/* Item J: branded error popup + the ONE shared required-field validator.
   Runs BEFORE any submit: on missing fields it lists them in the UI
   language, marks them red, and NO request is sent. */
function errPopup(text){
  const ov = okPopup(text);
  const tick = ov.querySelector('.oktick');
  tick.textContent = '✕'; tick.classList.add('err');
  setTimeout(() => { tick.textContent = '✓'; tick.classList.remove('err'); }, 2600);
  return ov;
}
window.errPopup = errPopup;
function reqCheck(list){
  const missing = [];
  document.querySelectorAll('.reqbad').forEach(e => e.classList.remove('reqbad'));
  for (const [id, key, kind] of list) {
    const el = document.getElementById(id);
    if (!el) continue;
    const v = (el.value || '').trim();
    let bad = false;
    if (kind === 'pos') bad = !(parseFloat(v) > 0);
    else if (kind === 'num') bad = v === '';
    else bad = v === '';
    if (bad) { missing.push(t(key)); el.classList.add('reqbad'); }
  }
  if (missing.length) { errPopup(t('missing_t') + missing.join(', ')); return false; }
  return true;
}
window.reqCheck = reqCheck;
/* ---------- ONE delete-confirmation modal ----------
   EVERY delete / remove action in the app routes through
   confirmDelete(): a branded modal in the app theme (never the
   browser's plain confirm()). Nothing is deleted until the red
   Delete button is tapped — Cancel, backdrop click and Escape all
   leave the data untouched. desc/note are set via textContent, so
   item names can never break the markup. */
let _delPending = null;
function confirmDelete(desc, onYes, note){
  let ov = document.getElementById('delpop');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'delpop'; ov.className = 'delpop';
    ov.innerHTML = '<div class="delcard"><div class="delicon">🗑</div>'
      + '<div class="deltitle">Delete karein?</div>'
      + '<div class="deldesc"></div><div class="delnote"></div>'
      + '<div class="delrow"><button type="button" class="danger delbtn">Delete</button>'
      + '<button type="button" class="ghost delcancel">Cancel</button></div></div>';
    ov.querySelector('.delbtn').addEventListener('click', () => {
      const fn = _delPending; closeDel(); if (fn) fn();
    });
    ov.querySelector('.delcancel').addEventListener('click', closeDel);
    ov.addEventListener('click', e => { if (e.target === ov) closeDel(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDel(); });
    document.body.appendChild(ov);
  }
  ov.querySelector('.delbtn').textContent = t('delete_l');
  ov.querySelector('.delcancel').textContent = t('cancel_l');
  ov.querySelector('.deldesc').textContent = desc || t('record');
  const dn = ov.querySelector('.delnote');
  dn.textContent = note || '';
  dn.style.display = note ? 'block' : 'none';
  _delPending = onYes || null;
  ov.style.display = 'flex';
  return ov;
}
function closeDel(){
  const ov = document.getElementById('delpop');
  if (ov) ov.style.display = 'none';
  _delPending = null;
}
window.confirmDelete = confirmDelete; window.closeDel = closeDel;
/* generic modal (Excel import preview / summary) */
function showModal(html){
  let ov = document.getElementById('xlmodal');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'xlmodal'; ov.className = 'xlmodal';
    ov.innerHTML = '<div class="xlcard"></div>';
    ov.addEventListener('click', e => { if (e.target === ov) closeModal(); });
    document.body.appendChild(ov);
  }
  ov.querySelector('.xlcard').innerHTML = html;
  ov.style.display = 'flex';
}
function closeModal(){ const ov = document.getElementById('xlmodal'); if (ov) ov.style.display = 'none'; }
window.closeModal = closeModal;
/* ---------- Calculator (header 🧮) ----------
   Purely client-side utility: a standard calculator plus three mill
   quick-hisaab tools. Nothing is saved, no API is called. */
let _calcExpr = '', _calcShown = null, _calcKb = false;
function _calcDisp(){ const d = document.getElementById('calc_disp'); if (!d) return;
  d.textContent = _calcShown != null ? _calcShown : ((_calcExpr || '0').replace(/\*/g, '×').replace(/\//g, '÷').replace(/-/g, '−')); }
function _calcEval(src){
  const toks = (String(src).match(/(\d+\.?\d*|\.\d+)|[+\-*/]/g) || []);
  if (!toks.length) throw new Error('empty');
  const vals = [], ops = []; let expectNum = true, neg = false;
  for (const tk of toks) {
    if (/^[+\-*/]$/.test(tk)) {
      if (expectNum) { if (tk === '-') { neg = !neg; continue; } if (tk === '+') continue; throw new Error('op'); }
      ops.push(tk); expectNum = true;
    } else { let v = parseFloat(tk); if (neg) { v = -v; neg = false; } vals.push(v); expectNum = false; }
  }
  if (expectNum || vals.length !== ops.length + 1) throw new Error('incomplete');
  const v2 = [vals[0]], o2 = [];
  for (let i = 0; i < ops.length; i++) {
    if (ops[i] === '*' || ops[i] === '/') {
      const a = v2.pop(), b = vals[i + 1];
      v2.push(ops[i] === '*' ? a * b : a / b);
    } else { o2.push(ops[i]); v2.push(vals[i + 1]); }
  }
  let r = v2[0];
  for (let i = 0; i < o2.length; i++) r = o2[i] === '+' ? r + v2[i + 1] : r - v2[i + 1];
  if (!isFinite(r)) throw new Error('range');
  return Math.round(r * 1e10) / 1e10;
}
window.calcPress = k => {
  _calcShown = null;
  if (k === 'C') _calcExpr = '';
  else if (k === 'B') _calcExpr = _calcExpr.slice(0, -1);
  else if (k === '%') {
    const m = _calcExpr.match(/(\d+\.?\d*|\.\d+)$/);
    if (m) _calcExpr = _calcExpr.slice(0, _calcExpr.length - m[1].length) + String(parseFloat(m[1]) / 100);
  }
  else if (k === '=') {
    try { _calcExpr = String(_calcEval(_calcExpr)); }
    catch (e) { _calcExpr = ''; _calcShown = 'Error'; }
  }
  else if (/^[+\-*/]$/.test(k)) {
    if (!_calcExpr && k !== '-') return;
    if (/[+\-*/]$/.test(_calcExpr)) _calcExpr = _calcExpr.slice(0, -1) + k; else _calcExpr += k;
  }
  else if (k === '.') {
    const seg = (_calcExpr.split(/[+\-*/]/).pop() || '');
    if (!seg.includes('.')) _calcExpr += (seg ? '.' : '0.');
  }
  else if (/^\d$/.test(k)) _calcExpr += k;
  _calcDisp();
};
window.calcQuick = () => {
  const gv = id => { const e = document.getElementById(id); return e ? parseFloat(e.value) : NaN; };
  const set = (id, txt) => { const e = document.getElementById(id); if (e) e.textContent = txt; };
  const bags = gv('calc_q_bags'), bkg = gv('calc_q_bagkg');
  set('calc_q_bags_res', (!isNaN(bags) && !isNaN(bkg)) ? '= ' + (bags * bkg / 1000).toFixed(3) + ' ' + t('calc_tons_l') : '');
  const tons = gv('calc_q_tons'), rate = gv('calc_q_rate');
  set('calc_q_tr_res', (!isNaN(tons) && !isNaN(rate)) ? '= ' + fmt(tons * rate) : '');
  const gross = gv('calc_q_gross'), tare = gv('calc_q_tare');
  set('calc_q_net_res', (!isNaN(gross) && !isNaN(tare)) ? '= ' + fmtN(gross - tare) + ' kg = ' + ((gross - tare) / 1000).toFixed(3) + ' ' + t('calc_tons_l') : '');
};
function _calcKbHandler(e){
  const ov = document.getElementById('calcmodal');
  if (!ov || ov.style.display === 'none') return;
  const tg = e.target;
  if (tg && (tg.tagName === 'INPUT' || tg.tagName === 'TEXTAREA' || tg.tagName === 'SELECT' || tg.isContentEditable)) return;
  let k = null;
  if (/^[0-9.]$/.test(e.key) || /^[+\-*/%]$/.test(e.key)) k = e.key;
  else if (e.key === 'Enter' || e.key === '=') k = '=';
  else if (e.key === 'Backspace') k = 'B';
  else if (e.key === 'Escape') { closeCalc(); return; }
  if (k) { e.preventDefault(); calcPress(k); }
}
window.openCalc = () => {
  let ov = document.getElementById('calcmodal');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'calcmodal'; ov.className = 'calcmodal';
    ov.addEventListener('click', e => { if (e.target === ov) closeCalc(); });
    document.body.appendChild(ov);
  }
  const keys = ['C', 'B', '%', '/', '7', '8', '9', '*', '4', '5', '6', '-', '1', '2', '3', '+', '0', '.', '='];
  const label = k => k === 'B' ? '⌫' : k === '*' ? '×' : k === '/' ? '÷' : k === '-' ? '−' : k;
  ov.innerHTML = `<div class="calccard"><div class="calchead"><h2>🧮 ${t('calc_l')}</h2><button type="button" class="ghost small" onclick="closeCalc()">✕</button></div>
   <div class="calcdisp" id="calc_disp">0</div>
   <div class="calcgrid">${keys.map(k => `<button type="button" class="${k === '=' ? 'calcgo' : ''}" ${k === '0' ? 'style="grid-column:span 2"' : ''} onclick="calcPress('${k}')">${label(k)}</button>`).join('')}</div>
   <h3>⚖ ${t('calc_quick_l')}</h3>
   <div class="calcq"><div class="calcqrow"><span>${t('calc_bags_tons_l')}</span><input id="calc_q_bags" type="number" step="any" placeholder="${t('bags')}" oninput="calcQuick()"><input id="calc_q_bagkg" type="number" step="any" value="${(typeof STATE !== 'undefined' && STATE && STATE.powder_bag_kg) || 50}" title="${t('powder_bag_kg_l')}" oninput="calcQuick()"><b class="calcres" id="calc_q_bags_res"></b></div>
   <div class="calcqrow"><span>${t('calc_tons_rate_l')}</span><input id="calc_q_tons" type="number" step="any" placeholder="${t('calc_tons_l')}" oninput="calcQuick()"><input id="calc_q_rate" type="number" step="any" placeholder="${t('calc_rate_ton_l')}" oninput="calcQuick()"><b class="calcres" id="calc_q_tr_res"></b></div>
   <div class="calcqrow"><span>${t('calc_gross_tare_l')}</span><input id="calc_q_gross" type="number" step="any" placeholder="${t('gross')} kg" oninput="calcQuick()"><input id="calc_q_tare" type="number" step="any" placeholder="${t('tare')} kg" oninput="calcQuick()"><b class="calcres" id="calc_q_net_res"></b></div></div></div>`;
  ov.style.display = 'flex';
  _calcDisp();
  if (!_calcKb) { document.addEventListener('keydown', _calcKbHandler); _calcKb = true; }
};
window.closeCalc = () => { const ov = document.getElementById('calcmodal'); if (ov) ov.style.display = 'none'; };
/* ---------- Excel import / export (per module) ---------- */
function xlBar(module){
  const ex = (fmt, label) => `<a class="xla" href="/api/xl/export?module=${module}&fmt=${fmt}"><button type="button" class="small ghost">${label}</button></a>`;
  return `<div class="xlbar"><span class="xltitle">📊 ${t('xl_label')}</span>
    ${ex('xlsx', t('xl_download'))} ${ex('csv', '⬇ CSV')} ${ex('pdf', t('xl_pdf'))}
    <a class="xla" href="/api/xl/sample?module=${module}"><button type="button" class="small ghost">${t('xl_sample')}</button></a>
    <button type="button" class="small ghost" onclick="xlUploadStart('${module}')">${t('xl_upload')}</button></div>`;
}
let XL_PENDING = null;
function _b64(buf){
  let bin = '';
  const b = new Uint8Array(buf), CH = 32768;
  for (let i = 0; i < b.length; i += CH) bin += String.fromCharCode.apply(null, b.subarray(i, i + CH));
  return btoa(bin);
}
window.xlPick = async (input, module) => {
  const f = input.files && input.files[0];
  input.value = '';
  if (!f) return;
  try {
    const buf = await f.arrayBuffer();
    XL_PENDING = { module, file_b64: _b64(buf), filename: f.name };
    const r = await post('/api/xl/import/preview', XL_PENDING);
    showXlPreview(r);
  } catch (e) { msg(e.message, 'err'); }
};
function xlRowLine(it){
  const chip = it.status === 'ok' ? `<span class="badge">${t('chip_ok')}</span>`
    : it.status === 'duplicate' ? `<span class="badge amber">${t('chip_dup')}</span>`
    : `<span class="badge red">${t('chip_bad')}</span>`;
  const data = Object.entries(it.data || {}).filter(([k, v]) => v !== '').map(([k, v]) => `${esc(k)}: ${esc(v)}`).join(' · ');
  return `<div class="xlrow">${chip} <b>${t('row_l')} ${it.row}</b>${it.reason ? ' — ' + esc(it.reason) : ''}<br><span class="muted small">${data}</span></div>`;
}
let XL_FMT_MODULE = null;
/* Upload opens a FORMAT popup first (owner, 28 Oct 2026): why it is
   shown, the exact columns + example rows, a Sample download and only
   then Choose file. The columns/rows come from GET /api/xl/format,
   which the server reads from the SAME module definition as the
   sample file and the importer — one source of truth, so the popup
   can never drift from what the importer accepts. Choose file runs
   the unchanged xlPick preview/apply flow. */
window.xlUploadStart = async module => {
  XL_FMT_MODULE = module;
  try {
    const f = await get('/api/xl/format?module=' + encodeURIComponent(module));
    const head = (f.headers || []).map(h => `<th>${esc(h)}</th>`).join('');
    const rows = (f.sample || []).map(r => `<tr>${(f.headers || []).map((h, i) => `<td>${esc(r[i] == null ? '' : r[i])}</td>`).join('')}</tr>`).join('');
    showModal(`<h2>📤 ${t('xl_fmt_title')}</h2>
     <p>${t('xl_why')}</p>
     <p class="small muted">${t('xl_fmt_note')}</p>
     <div class="wrap"><table><tr>${head}</tr>${rows}</table></div>
     ${(f.also && f.also.length) ? `<p class="small muted">${t('xl_also')} ${f.also.map(esc).join(', ')}</p>` : ''}
     <div class="row" style="margin-top:12px">
       <a class="xla" href="/api/xl/sample?module=${module}"><button type="button" class="ghost">${t('xl_sample')}</button></a>
       <button type="button" onclick="document.getElementById('xl_file').click()">📁 ${t('xl_choose')}</button>
       <button type="button" class="ghost" onclick="closeModal()">${t('cancel_l')}</button></div>
     <input type="file" id="xl_file" style="display:none" accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv,application/csv" onchange="xlPick(this, XL_FMT_MODULE)">`);
  } catch (e) { msg(e.message, 'err'); }
};
function showXlPreview(r){
  showModal(`<h2>📥 ${t('imp_title')}</h2>
   <p><b>${r.total}</b> ${t('imp_rows')} — <b>${r.valid}</b> ${t('imp_ok')}, <b>${r.duplicates}</b> ${t('imp_dup')}, <b>${r.errors}</b> ${t('imp_wrong')}.</p>
   <p class="small muted">${t('imp_note')}</p>
   <div class="xllist">${(r.items || []).map(xlRowLine).join('') || '<span class="muted">—</span>'}</div>
   <div class="row" style="margin-top:12px"><button onclick="xlDoApply()" ${r.valid ? '' : 'disabled'}>✔ ${t('imp_do')} (${r.valid})</button>
   <button class="ghost" onclick="closeModal()">${t('cancel_l')}</button></div>`);
}
window.xlDoApply = async () => {
  if (!XL_PENDING) return;
  try {
    const r = await post('/api/xl/import/apply', XL_PENDING);
    XL_PENDING = null;
    const bad = (r.duplicates || []).concat(r.errors || []).sort((a, b) => a.row - b.row);
    showModal(`<h2>✅ ${t('imp_done')}</h2>
     <p style="font-size:16px"><b>${r.added}</b> ${t('imp_added')}, <b>${(r.duplicates || []).length}</b> ${t('imp_dup_skip')}, <b>${(r.errors || []).length}</b> ${t('imp_wrong_rows')}.</p>
     ${bad.length ? `<div class="xllist">${bad.map(xlRowLine).join('')}</div>` : `<p class="muted">${t('imp_none_bad')}</p>`}
     <div style="margin-top:12px"><button onclick="closeModal();render()">OK</button></div>`);
  } catch (e) { closeModal(); msg(e.message, 'err'); }
};
function val(id){ const e = document.getElementById(id); return e ? e.value : ''; }
function num(id){ return parseFloat(val(id)) || 0; }
function chk(id){ const e = document.getElementById(id); return e ? e.checked : false; }
/* Role-filtered party pickers: each form's context decides which
   parties appear, by their roles (supplier / buyer / grinding). A
   both-role party appears in every list its roles qualify for; a party
   with neither relevant role never appears. Staff logins hold only
   ids+names+roles (party-options endpoint, same server-side filter). */
const PARTY_CTX = { vehicle_in: ['supplier', 'grinding'], vehicle_out: ['buyer', 'grinding'],
  grinding: ['grinding'], purchase: ['supplier'], sale: ['buyer'], orders: ['buyer'],
  production: ['supplier', 'grinding'], grindprod: ['supplier', 'grinding'], all: null };
function partiesFor(ctx){
  const want = PARTY_CTX[ctx];
  if (!want) return CACHE.parties;
  return CACHE.parties.filter(p => want.some(r => String(p.roles || '').split(',').includes(r)));
}
function partyOpts(sel, ctx){ return partiesFor(ctx).map(p => `<option value="${p.id}" ${String(sel) === String(p.id) ? 'selected' : ''}>${esc(p.name)}</option>`).join(''); }
function workerOpts(sel){ return CACHE.workers.map(w => `<option value="${w.id}" ${String(sel) === String(w.id) ? 'selected' : ''}>${esc(w.name)}</option>`).join(''); }
function deptOpts(sel){ return CACHE.departments.map(d => `<option value="${d.id}" ${String(sel) === String(d.id) ? 'selected' : ''}>${esc(d.name)}</option>`).join(''); }
function headOpts(sel, parent){
  return CACHE.heads.filter(h => (parent === undefined ? !h.parent_id : String(h.parent_id || '') === String(parent)))
    .map(h => `<option value="${h.id}" ${String(sel) === String(h.id) ? 'selected' : ''}>${esc(h.name)}</option>`).join('');
}
async function loadBase(){
  if (!STATE.user || STATE.user.role === 'client') return;
  /* staff logins only reach the modules they are allowed — tolerate 403s
     and fall back to the names-only list for form dropdowns */
  const safe = p => get(p).catch(() => null);
  const [p, po, w, d, h, hu] = await Promise.all([safe('/api/parties'), safe('/api/party-options'),
    safe('/api/workers'), safe('/api/departments'), safe('/api/heads'), safe('/api/holder-users')]);
  CACHE.parties = p || po || [];
  CACHE.workers = w || [];
  CACHE.departments = d || [];
  CACHE.heads = h || [];
  CACHE.holders = hu || [];
}
/* mill-wide theme colour (owner picks it in Settings; the server stores
   it and /api/state carries it, so even the login screen wears it) */
const ACCENTS = [
  { k: 'green', en: 'Green', ur: 'سبز', c1: '#0c7a4e', c2: '#0c2e21' },
  { k: 'blue', en: 'Blue', ur: 'نیلا', c1: '#1565c0', c2: '#0c2340' },
  { k: 'teal', en: 'Teal', ur: 'فیروزی', c1: '#0e7a7b', c2: '#083a3b' },
  { k: 'maroon', en: 'Maroon', ur: 'عنابی', c1: '#8e2434', c2: '#33101a' },
  { k: 'purple', en: 'Purple', ur: 'جامنی', c1: '#6a3ec9', c2: '#221238' },
  { k: 'slate', en: 'Slate', ur: 'سلیٹ', c1: '#4a6076', c2: '#1c2733' },
  { k: 'bronze', en: 'Bronze', ur: 'کانسی', c1: '#a06a1c', c2: '#33270d' },
  { k: 'sky', en: 'Sky', ur: 'آسمانی', c1: '#2b78b8', c2: '#14334e' },
  { k: 'mint', en: 'Mint', ur: 'پودینہ', c1: '#18825f', c2: '#0d3527' },
  { k: 'peach', en: 'Peach', ur: 'آڑو', c1: '#bf5a11', c2: '#472708' },
  { k: 'lavender', en: 'Lavender', ur: 'بنفشی', c1: '#7d5fc0', c2: '#2a2140' },
  { k: 'rose', en: 'Rose', ur: 'گلابی', c1: '#c74e74', c2: '#451626' }
];
function applyAccent(){
  const a = (STATE.mill && STATE.mill.theme_color) || localStorage.getItem('mill_accent') || 'green';
  document.documentElement.dataset.accent = a;
  if (document.body) document.body.dataset.accent = a;
  try { localStorage.setItem('mill_accent', a); } catch (e) {}
}
window.setAccent = async k => {
  try {
    const r = await post('/api/settings', { theme_color: k });
    STATE.mill.theme_color = (r && r.theme_color) || k;
    applyAccent(); render();
    okPopup('Theme colour lag gaya ✓ ' + k);
  } catch (e) { msg(e.message, 'err'); }
};
/* The ONE accent picker used inside the app (round 13): the same
   dropdown as the login screen — same 12 options, same names, same
   setAccent() behaviour and server-side persistence. No swatches. */
function accentDropdownHTML(){
  const cur = (STATE.mill && STATE.mill.theme_color) || localStorage.getItem('mill_accent') || 'green';
  return `<select class="lgaccent accdd" onchange="setAccent(this.value)" aria-label="${t('theme_colour_l')}">${ACCENTS.map(a =>
    `<option value="${a.k}" ${a.k === cur ? 'selected' : ''}>${PREFS.lang === 'ur' ? a.ur : a.en}</option>`).join('')}</select>`;
}

/* ---------------- accordion sections (round 13) ----------------
   Shared component for every multi-system page: only the section
   HEADS show as compact rows; clicking a head expands that section's
   full card — one open at a time per page. The open section is
   remembered per page for the session (sessionStorage mill_acc13),
   defaulting to the page's primary block. Switching happens ONLY on
   a head click, or an explicit accOpen() from an edit prefill — a
   section never collapses under a form being filled. Closed bodies
   stay in the DOM ([hidden]), so field reads like saveSettings()
   keep working exactly as before. */
let ACC_STATE = {};
try { ACC_STATE = JSON.parse(sessionStorage.getItem('mill_acc13') || '{}') || {}; } catch (e) { ACC_STATE = {}; }
function accSaveState(){ try { sessionStorage.setItem('mill_acc13', JSON.stringify(ACC_STATE)); } catch (e) {} }
function accOpenKey(page, def){ return ACC_STATE[page] !== undefined ? ACC_STATE[page] : def; }
function accHead(page, key, icon, title, desc, def){
  const open = accOpenKey(page, def) === key;
  return `<div class="accsec${open ? ' open' : ''}" data-accpage="${page}" data-acckey="${key}">
   <button type="button" class="acchead" onclick="accToggle('${page}','${key}')" aria-expanded="${open}">
    <span class="accic">${icon}</span>
    <span class="accttl"><b>${esc(title)}</b>${desc ? `<span class="accdesc">${esc(desc)}</span>` : ''}</span>
    <span class="accchv">▾</span></button>
   <div class="accbody"${open ? '' : ' hidden'}>`;
}
const accEnd = () => '</div></div>';
function accApply(page){
  document.querySelectorAll(`.accsec[data-accpage="${page}"]`).forEach(s => {
    const on = s.dataset.acckey === ACC_STATE[page];
    s.classList.toggle('open', on);
    const b = s.querySelector('.accbody'); if (b) b.hidden = !on;
    const h = s.querySelector('.acchead'); if (h) h.setAttribute('aria-expanded', String(on));
  });
}
window.accToggle = (page, key) => {
  ACC_STATE[page] = (accOpenKey(page, null) === key) ? '' : key;
  accSaveState(); accApply(page);
};
window.accOpen = (page, key) => {
  ACC_STATE[page] = key; accSaveState(); accApply(page);
  const s = document.querySelector(`.accsec[data-accpage="${page}"][data-acckey="${key}"]`);
  if (s) s.scrollIntoView({ block: 'start' });
};

/* ---------------- settings tabs + info boxes (round 14) ----------------
   The Settings page trades the round-13 accordion for the campus-CMS
   pattern Talha pointed at: pill tabs across the top, ONE panel
   visible below. Inactive panels stay in the DOM ([hidden]) exactly
   like accordion bodies, so saveSettings() reading every st_* id and
   all existing handlers are byte-identical in behaviour. The active
   tab reuses the round-13 session memory (ACC_STATE['settings'] in
   mill_acc13) with the same section keys, so a section left open in
   the accordion era opens as the active tab. */
window.setTab = key => {
  ACC_STATE['settings'] = key; accSaveState();
  document.querySelectorAll('.settab').forEach(b => {
    const on = b.dataset.settab === key;
    b.classList.toggle('active', on);
    b.setAttribute('aria-selected', String(on));
  });
  document.querySelectorAll('.setpanel').forEach(p => { p.hidden = p.dataset.setpanel !== key; });
  const p = document.querySelector(`.setpanel[data-setpanel="${key}"]`);
  if (p) p.scrollIntoView({ block: 'start' });
};
function infoBoxes(needKey, tipsKey){
  return `<div class="infoboxes"><div class="infobox need"><h4>🧰 ${t('ib_need_t')}</h4><ul>${t(needKey)}</ul></div>
   <div class="infobox tips"><h4>🛡️ ${t('ib_tips_t')}</h4><ul>${t(tipsKey)}</ul></div></div>`;
}
/* ---------------- email service presets (round 15) ----------------
   The Email panel opens with a service picker: choosing a preset
   only FILLS the existing host/port/security fields and swaps the
   provider mini-note under the info boxes — the fields stay fully
   editable, the stored smtp_* values remain what send_email() uses,
   and the picked label persists as the mail_preset setting. Free
   plans lead the list (Brevo 300/day, SMTP2GO 1,000/month) because
   Talha asked for a free-plan route to be built in. */
const MAIL_PRESET_KEYS = ['custom', 'gmail', 'brevo', 'smtp2go', 'hostinger', 'outlook'];
const MAIL_PRESETS = {
  gmail:     { host: 'smtp.gmail.com', port: 587, sec: 'starttls' },
  brevo:     { host: 'smtp-relay.brevo.com', port: 587, sec: 'starttls' },
  smtp2go:   { host: 'mail.smtp2go.com', port: 587, sec: 'starttls' },
  hostinger: { host: 'smtp.hostinger.com', port: 587, sec: 'starttls' },
  outlook:   { host: 'smtp.office365.com', port: 587, sec: 'starttls' },
};
window.mailPreset = key => {
  const p = MAIL_PRESETS[key];
  if (p) {
    const h = $('#st_smtphost'), po = $('#st_smtpport'), se = $('#st_smtpsec');
    if (h) h.value = p.host;
    if (po) po.value = p.port;
    if (se) se.value = p.sec;
  }
  document.querySelectorAll('.mailpnote').forEach(n => { n.hidden = n.dataset.mailpreset !== key; });
};
function logoHTML(cls){
  return STATE.mill.has_logo ? `<img class="${cls}" src="/branding/logo?v=${STATE.mill.logo_ver || 0}" alt=""> ` : '';
}
const FONT_STACKS = {
  default: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans Arabic', Arial, sans-serif",
  serif: "Georgia, 'Times New Roman', 'Noto Naskh Arabic', 'Noto Sans Arabic', serif",
  rounded: "ui-rounded, 'SF Pro Rounded', 'Segoe UI Rounded', system-ui, 'Noto Sans Arabic', sans-serif",
  naskh: "'Noto Naskh Arabic', 'Noto Sans Arabic', system-ui, serif",
  nastaliq: "'Noto Nastaliq Urdu', 'Noto Sans Arabic', system-ui, sans-serif",
};
const FONT_OPTS = ['default', 'serif', 'rounded', 'naskh', 'nastaliq'];
function applyFonts(){
  const f = (typeof STATE !== 'undefined' && STATE.font) || {};
  const root = document.documentElement;
  root.style.setProperty('--uifont', FONT_STACKS[f.ui_font] || FONT_STACKS.default);
  root.style.setProperty('--uiscale', { small: 0.9, normal: 1, large: 1.12 }[f.ui_text_size] || 1);
  root.dataset.uifont = f.ui_font || 'default';
}
function applyPrefs(){
  applyFonts();
  document.documentElement.lang = PREFS.lang === 'ur' ? 'ur' : (PREFS.lang === 'hi' ? 'hi' : 'en');
  document.documentElement.dir = PREFS.lang === 'ur' ? 'rtl' : 'ltr';
  document.body.dataset.theme = PREFS.theme;
  document.documentElement.dataset.theme = PREFS.theme;
  applyAccent();
  localStorage.setItem('mill_lang', PREFS.lang); localStorage.setItem('mill_theme', PREFS.theme); localStorage.setItem('mill_unit', PREFS.unit);
}
async function setPref(key, value){
  PREFS[key] = value; applyPrefs();
  if (STATE.user) { try { await post('/api/prefs', { [key]: value }); } catch (e) {} }
}
/* language switch mid-form: keep typed values */
function switchLang(v){
  const saved = {};
  document.querySelectorAll('#main input, #main select, #main textarea, #lg_user, #lg_pass').forEach(e => { if (e.id) saved[e.id] = e.type === 'checkbox' ? e.checked : e.value; });
  const restore = () => { Object.keys(saved).forEach(id => { const e = document.getElementById(id); if (e) { if (e.type === 'checkbox') e.checked = saved[id]; else if (e.value !== saved[id]) e.value = saved[id]; } }); };
  /* on the login screen there is no app shell to re-render — rebuild the
     login card instead, keeping whatever was typed in the two fields */
  const onLogin = !STATE.user && !!document.getElementById('lg_user');
  setPref('lang', v).then(() => { if (onLogin) renderLogin(); else render(); }).then(() => {
    restore();
    [200, 500, 1000, 1600].forEach(ms => setTimeout(restore, ms));
  });
}
/* attachments */
function attachHTML(table, record){
  return `<div class="field"><label>📎 ${t('proof_attach')}</label>
    <input type="file" id="att_file" accept="image/*,application/pdf">
    <div id="att_list"></div></div>`;
}
async function loadAttachments(table, record){
  const box = $('#att_list'); if (!box) return;
  const rows = await get(`/api/attachments?table=${table}&record=${record}`);
  box.innerHTML = rows.map(a => `<div class="fileline">${a.mime && a.mime.startsWith('image') ? `<img class="thumb" src="/api/attachments/${a.id}/raw">` : '📄'}
    <a href="/api/attachments/${a.id}/raw" target="_blank">${esc(a.filename)}</a>
    <span class="muted small">${(a.size / 1024).toFixed(0)} KB</span>
    ${isOwner() ? `<button class="small danger" onclick="delAttachment(${a.id},'${table}',${record})">${t('del')}</button>` : ''}</div>`).join('') || '<span class="muted small">—</span>';
}
async function uploadAttachment(table, record){
  const f = $('#att_file'); if (!f || !f.files[0]) return null;
  const file = f.files[0];
  const b64 = await new Promise(res => { const r = new FileReader(); r.onload = () => res(String(r.result).split(',')[1]); r.readAsDataURL(file); });
  const out = await post('/api/attachments', { table_name: table, record_id: record, filename: file.name, mime: file.type, data_b64: b64 });
  return out.id;
}
window.delAttachment = (id, table, record) => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  confirmDelete(t('attachments') + ' #' + id, async () => {
    try { await post('/api/attachments/delete', { id }); loadAttachments(table, record); }
    catch (e) { msg(e.message, 'err'); }
  });
};
/* generic delete with recycle — always via the shared confirm modal */
function delLabel(table){
  const K = { parties: 'party', trips: 'vehicle', grinding_jobs: 'grind_prod',
    production: 'production', bag_movements: 'bardana', client_bags: 'party_bags_t',
    purchases: 'purchase_l', sales: 'sale_l',
    payments: 'payments', expenses: 'expenses', workers: 'worker',
    departments: 'departments', attendance: 'attendance',
    biometric_devices: 'machine_l', machines: 'machines', machine_entries: 'maint_entry' };
  return t(K[table] || 'record');
}
window.delRow = (table, id) => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  confirmDelete(delLabel(table) + ' #' + id, async () => {
    try { await post('/api/delete', { table, id }); okPopup(t('deleted_ok2')); render(); }
    catch (e) { msg(e.message, 'err'); }
  }, t('rec_del_note'));
};
// Owner-only entry rule (27 Oct): edit/delete buttons render ONLY for
// the owner. The server enforces the same rule on every mutation, so
// hiding here is presentation, not the protection itself.
const isOwner = () => !!(STATE.user && STATE.user.role === 'owner');
const delBtn = (table, id) => isOwner() ? `<button class="small danger" onclick="delRow('${table}',${id})">${t('del')}</button>` : '';
/* voice entry — fills the form only, NEVER saves */
window.voiceFill = function(kind){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert(t('voice_hint')); return; }
  const rec = new SR();
  rec.lang = PREFS.lang === 'ur' ? 'ur-PK' : (PREFS.lang === 'hi' ? 'hi-IN' : 'en-US');
  rec.interimResults = false;
  msg('🎤 ' + t('listening'));
  rec.onresult = ev => {
    const text = ev.results[0][0].transcript;
    msg(t('heard') + '"' + text + '" ' + t('check_save'));
    fillFromSpeech(kind, text);
  };
  rec.onerror = () => msg(t('voice_fail'), 'err');
  rec.start();
};
function fillFromSpeech(kind, text){
  const low = text.toLowerCase();
  const nums = (text.match(/\d+[\d,]*\.?\d*/g) || []).map(s => parseFloat(s.replace(/,/g, '')));
  // party match by name (Latin or local script stored names)
  const sel = document.getElementById(kind === 'payment' ? 'pay_party' : (kind === 'trip' ? 'tr_party' : (kind === 'job' ? 'job_party' : 'party')));
  if (sel) {
    const hit = CACHE.parties.find(p => low.includes(p.name.toLowerCase()) || text.includes(p.name));
    if (hit) sel.value = hit.id;
  }
  const set = (id, v) => { const e = document.getElementById(id); if (e && v !== undefined && !isNaN(v)) e.value = v; };
  if (kind === 'trip') {
    const v = text.match(/[A-Za-z]{2,3}[-\s]?\d{2,4}/);
    if (v) { const e = $('#tr_vehicle'); if (e) e.value = v[0].toUpperCase().replace(/\s/g, '-'); }
    if (nums.length) set('tr_net', nums[nums.length - 1]);
    tripPartyChanged();   // a voice-set party fires no onchange: keep the Buy-from picker and the powder-stock hint in step
  }
  if (kind === 'payment' && nums.length) set('pay_amount', nums[nums.length - 1]);
  if (kind === 'expense' && nums.length) set('ex_amount', nums[nums.length - 1]);
  if (kind === 'job' && nums.length) { set('job_outbags', Math.round(nums[0])); }
}

/* ---------------- shell ---------------- */
async function boot(){
  applyPrefs();
  const st = await get('/api/state').catch(() => null);
  if (!st) { appEl.innerHTML = '<div class="center card">' + t('server_down') + '</div>'; return; }
  STATE = Object.assign(STATE, st);
  if (st.user) {
    PREFS = { lang: st.user.lang || PREFS.lang, theme: st.user.theme || PREFS.theme, unit: st.user.unit || PREFS.unit };
    applyPrefs();
    await loadBase();
    render();
    maybeDailyAlerts();
  } else if (!st.configured) { renderSetup(); }
  else { renderLogin(); }
}
function langSelect(id){ return `<select id="${id}" onchange="switchLang(this.value)">
  ${['en', 'ur', 'hi'].map(l => `<option value="${l}" ${PREFS.lang === l ? 'selected' : ''}>${l === 'en' ? 'English' : (l === 'ur' ? 'اردو' : 'हिन्दी')}</option>`).join('')}</select>`; }
function renderSetup(){
  appEl.innerHTML = `<div class="center wide"><div class="card authcard">
    <div class="authband">🏭</div>
    <h1>${t('app')} — ${t('setup_word')}</h1>
    <p class="muted">${t('setup_intro')}</p>
    <div id="msg" class="msg" style="display:none"></div>
    <div class="field"><label>${t('data_folder')}</label><div class="row" style="flex-wrap:nowrap">
      <input id="su_folder" placeholder="e.g. D:\\MillData"><button class="ghost" onclick="pickFolder()">📁 ${t('choose_l')}</button></div></div>
    <div class="row"><div class="field"><label>${t('mill_name_l')}</label><input id="su_mill" value="Phosphate Grinding Mill"></div>
    <div class="field"><label>${t('owner_wa')} (03xx…)</label><input id="su_wa" placeholder="03XX-XXXXXXX"></div></div>
    <div class="row"><div class="field"><label>${t('username')} (owner)</label><input id="su_user" placeholder="owner"></div>
    <div class="field"><label>${t('password')}</label><input id="su_pass" type="password"></div></div>
    <div class="field"><label>${t('email_l')} (owner)</label><input id="su_email" type="email" placeholder="owner@example.com"></div>
    <button onclick="doSetup()">${t('save')} — ${t('start_btn')}</button>
    <p class="small muted">${t('voice_hint')}</p></div></div>`;
}
window.pickFolder = async () => { try { const r = await post('/api/pick-folder', {}); if (r.path) $('#su_folder').value = r.path; } catch (e) { msg(e.message, 'err'); } };
window.doSetup = async () => {
  try {
    await post('/api/setup', { db_folder: val('su_folder'), username: val('su_user'), password: val('su_pass'),
      mill_name: val('su_mill'), owner_whatsapp: val('su_wa'), owner_email: val('su_email') });
    location.reload();
  } catch (e) { msg(e.message, 'err'); }
};
function loginLangSelect(){
  /* login-card language DROPDOWN (Talha, 28 Oct 2026 — replaces the
     language pill buttons he had): the same 3 languages with the same
     native labels, styled like the theme-colour select beside it, and
     wired to the SAME switchLang path as the header langSelect — so it
     applies at once (Urdu = Urdu strings + RTL), persists locally via
     applyPrefs, and the signed-in account's saved prefs still win. */
  const names = { en: 'English', ur: 'اردو', hi: 'हिन्दी' };
  return `<select id="lg_lang" class="lglang" title="${t('language')}" onchange="switchLang(this.value)">${['en', 'ur', 'hi'].map(l =>
    `<option value="${l}" ${PREFS.lang === l ? 'selected' : ''}>${names[l]}</option>`).join('')}</select>`;
}
const LG_USER_SVG = '<svg class="inicon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/></svg>';
const LG_LOCK_SVG = '<svg class="inicon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';
/* Login-page appearance (owner, 28 Oct 2026 — the MT login look):
   the Dark toggle drives the SAME per-user 'theme' pref as the app
   header (setPref: applies at once, persists to localStorage, and
   server-saves only when a user is logged in — never pre-login; on
   sign-in the account's saved prefs replace PREFS as always). The
   colour select offers the SAME ACCENTS set as the in-app dropdown;
   pre-login it is a LOCAL choice — live on this page and kept in
   localStorage ('mill_accent', the local layer applyAccent already
   maintains) — while the mill-wide theme_color stays the in-app
   truth, exactly as before. */
window.loginTheme = () => {
  const next = PREFS.theme === 'dark' ? 'light' : 'dark';
  setPref('theme', next);
  const b = document.getElementById('lg_theme');
  if (b) b.innerHTML = next === 'dark' ? '☀️ ' + t('light') : '🌙 ' + t('dark');
};
window.loginAccent = k => {
  document.documentElement.dataset.accent = k;
  if (document.body) document.body.dataset.accent = k;
  try { localStorage.setItem('mill_accent', k); } catch (e) {}
};
function renderLogin(){
  /* read the local colour choice BEFORE applyAccent(): applyAccent
     re-stamps 'mill_accent' with the mill colour, which would erase
     the visitor's login-page choice before it could be honoured */
  const savedAcc = localStorage.getItem('mill_accent');
  applyAccent();
  if (savedAcc) {
    document.documentElement.dataset.accent = savedAcc;
    if (document.body) document.body.dataset.accent = savedAcc;
    try { localStorage.setItem('mill_accent', savedAcc); } catch (e) {}
  }
  const curAcc = savedAcc || (STATE.mill && STATE.mill.theme_color) || 'green';
  document.title = (STATE.mill.name || t('app'));
  const nm = STATE.mill.name || t('app');
  const badge = STATE.mill.has_logo
    ? `<img class="brandlogo" src="/branding/logo?v=${STATE.mill.logo_ver || 0}" alt="">`
    : `<span class="brandmark">${esc((nm || 'M').trim().charAt(0).toUpperCase())}</span>`;
  /* round 10 (Talha, 29 Oct 2026): the appearance row is reordered to
     language -> theme colour -> dark toggle on ONE line (CSS .loginapps
     is nowrap; the two selects shrink, the row never wraps), the card
     sits in a .loginwrap with a small .loginfoot credit line under it —
     the same wording as the in-app sidebar footer. */
  appEl.innerHTML = `<div class="loginbg"><div class="loginwrap"><div class="logincard">
    <div class="brandpanel"><div class="brandbadge">${badge}</div>
      <div class="brandname">${esc(nm)}</div>
      ${nm !== t('app') ? `<div class="brandsub">${t('app')}</div>` : ''}
      <div class="brandrule"></div>
      <div class="brandtag">${t('sys_tag')}</div></div>
    <div class="loginform">
    <div id="msg" class="msg" style="display:none"></div>
    <div class="loginapps">${loginLangSelect()}<select id="lg_accent" class="lgaccent" title="${t('theme_colour_l')}" onchange="loginAccent(this.value)">${ACCENTS.map(a => `<option value="${a.k}" ${curAcc === a.k ? 'selected' : ''}>${PREFS.lang === 'ur' ? a.ur : a.en}</option>`).join('')}</select><button type="button" id="lg_theme" class="lgthemebtn" onclick="loginTheme()">${PREFS.theme === 'dark' ? '☀️ ' + t('light') : '🌙 ' + t('dark')}</button></div>
    <div id="lg_main">
    <div class="field"><label>${t('login_user_l')}</label><div class="inwrap">${LG_USER_SVG}<input id="lg_user" autocomplete="username"></div></div>
    <div class="field"><label>${t('password')}</label><div class="inwrap">${LG_LOCK_SVG}<input id="lg_pass" type="password" autocomplete="current-password"
      onkeydown="if(event.key==='Enter')doLogin()"></div></div>
    <button class="loginbtn" onclick="doLogin()">${t('login')}</button>
    <div style="text-align:end;margin-top:8px"><a href="#" onclick="showForgot();return false" class="small">${t('forgot_pw')}</a></div>
    <div class="demohint">👀 ${t('demo_hint')}</div></div>
    <div id="lg_forgot" style="display:none">
    <h3 style="margin:4px 0 6px">🔑 ${t('forgot_t')}</h3>
    <p class="small muted">${t('forgot_hint')}</p>
    <div class="field"><label>${t('login_user_l')}</label><div class="inwrap">${LG_USER_SVG}<input id="fg_user" autocomplete="username"
      onkeydown="if(event.key==='Enter')doForgot()"></div></div>
    <button class="loginbtn" onclick="doForgot()">${t('send_link')}</button>
    <p id="fg_msg" class="small" style="display:none;color:var(--ok,#0c7a4e)"></p>
    <div style="margin-top:8px"><a href="#" onclick="showLoginForm();return false" class="small">← ${t('back_login')}</a></div>
    </div></div></div><div class="loginfoot">© 2026 Orush Grinding Mill — All Rights Reserved · Developed by Talha Islam</div></div></div>`;
}
window.doLogin = async () => {
  try {
    const r = await post('/api/login', { username: val('lg_user'), password: val('lg_pass') });
    STATE.user = r.user; PREFS = { lang: r.user.lang, theme: r.user.theme, unit: r.user.unit }; applyPrefs();
    await loadBase();
    VIEW = r.user.role === 'client' ? 'mykhata' : (r.user.role === 'staff' ? firstView() : 'dashboard');
    render();
    maybeDailyAlerts();
  } catch (e) { msg(e.message, 'err'); }
};
window.doLogout = async () => { await post('/api/logout', {}); location.reload(); };
/* round 12: forgot-password — the server ALWAYS answers ok (the
   account's existence is never revealed on this page); the emailed
   link lands on the server-rendered /reset-password page */
window.showForgot = () => {
  const m = $('#lg_main'), f = $('#lg_forgot'); if (!m || !f) return;
  const u = $('#lg_user'); if (u && u.value && $('#fg_user')) $('#fg_user').value = u.value;
  m.style.display = 'none'; f.style.display = '';
};
window.showLoginForm = () => {
  const m = $('#lg_main'), f = $('#lg_forgot'); if (!m || !f) return;
  f.style.display = 'none'; m.style.display = '';
};
window.doForgot = async () => {
  try { await post('/api/forgot-password', { username: val('fg_user') }); } catch (e) {}
  const p = $('#fg_msg'); if (p) { p.textContent = t('forgot_sent'); p.style.display = ''; }
};
window.go = v => { VIEW = v; render(); };
/* ---------- Daily alerts (round 11) ----------
   ONE check after login/app load (GET /api/shift-alert) drives a
   short queue of popups: SHIFT production alerts first (they carry
   the entry actions), then VEHICLE movement notices. Navigating
   away from a popup (Enter Now / the Vehicle page shortcut) ends
   the queue for this session — anything still due returns on the
   next app open, unless it was dismissed or resolved meanwhile. */
let ALERTS_CHECKED = false;
let GP_PREFILL = null;   // {date, shift} — consumed by VIEWS.grindprod
function alertDateDisp(ds){
  try { return new Date(ds + 'T00:00:00').toLocaleDateString('en-GB',
    { day: 'numeric', month: 'short', year: 'numeric' }); }
  catch (e) { return ds; }
}
async function maybeDailyAlerts(){
  if (ALERTS_CHECKED) return; ALERTS_CHECKED = true;
  if (!STATE.user) return;
  const role = STATE.user.role;
  if (role === 'client' || role === 'demo') return;
  let r = null;
  try { r = await get('/api/shift-alert'); } catch (e) { return; }
  if (!r) return;
  const q = [];
  (r.shift_alerts || []).forEach(a => q.push({ fam: 'shift', date: a.date, shift: a.shift }));
  (r.vehicle_alerts || []).forEach(a => q.push({ fam: a.type, date: a.date }));
  if (q.length) showAlertQueue(q);
}
function showAlertQueue(q){
  if (!q.length) { closeModal(); return; }
  const a = q[0], rest = q.slice(1);
  window._alertCur = a; window._alertRest = rest;
  if (a.fam === 'shift') {
    const shiftName = a.shift === 'Night' ? t('night_l') : t('day_l');
    const body = t('sa_body').replace('{shift}', shiftName)
      .replace('{date}', alertDateDisp(a.date));
    showModal(`<h3 style="margin-top:0">⏰ ${t('sa_title')}</h3>
      <p>${esc(body)}</p>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <button onclick="alertEnterNow()">${t('sa_enter')}</button>
        <button class="ghost" onclick="alertLater()">${t('sa_later')}</button>
        <button class="ghost" onclick="alertClosedForm()">${t('sa_closed_btn')}</button>
      </div>`);
  } else {
    const isIn = a.fam === 'vehicle_in';
    showModal(`<h3 style="margin-top:0">🚛 ${t(isIn ? 'va_in_t' : 'va_out_t')}</h3>
      <p>${t(isIn ? 'va_in_b' : 'va_out_b')}</p>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <button onclick="alertGotoVehicle()">${t(isIn ? 'vehicle_in' : 'vehicle_out')}</button>
        <button class="ghost" onclick="alertAck()">${t('va_ok')}</button>
      </div>`);
  }
}
window.alertEnterNow = () => {
  const a = window._alertCur; closeModal();
  if (a) { GP_PREFILL = { date: a.date, shift: a.shift }; go('grindprod'); }
};
window.alertLater = async () => {
  const a = window._alertCur, rest = window._alertRest || [];
  try { await post('/api/shift-alert/dismiss',
    { kind: 'shift', date: a.date, shift: a.shift }); } catch (e) {}
  showAlertQueue(rest);
};
window.alertClosedForm = () => {
  const a = window._alertCur;
  const shiftName = a.shift === 'Night' ? t('night_l') : t('day_l');
  showModal(`<h3 style="margin-top:0">🏭 ${t('sa_closed_t')}</h3>
    <p class="muted">${shiftName} · ${alertDateDisp(a.date)}</p>
    <div class="field"><label><input type="radio" name="sa_reason" value="technical" checked> ${t('sa_reason_technical')}</label></div>
    <div class="field"><label><input type="radio" name="sa_reason" value="power"> ${t('sa_reason_power')}</label></div>
    <div class="field"><label>${t('note')}</label><input id="sa_note" placeholder="${t('sa_note_ph')}"></div>
    <div class="row" style="gap:8px;flex-wrap:wrap">
      <button onclick="alertClosedSave()">${t('save')}</button>
      <button class="ghost" onclick="alertBack()">${t('cancel_l')}</button>
    </div>`);
};
window.alertBack = () => showAlertQueue([window._alertCur].concat(window._alertRest || []));
window.alertClosedSave = async () => {
  const a = window._alertCur, rest = window._alertRest || [];
  const sel = document.querySelector('input[name="sa_reason"]:checked');
  try {
    await post('/api/shift-closures', { date: a.date, shift: a.shift,
      reason: sel ? sel.value : 'technical', note: val('sa_note') });
  } catch (e) { msg(e.message, 'err'); return; }
  if (rest.length) showAlertQueue(rest);
  else { closeModal(); okPopup(t('sa_closed_saved')); }
};
window.alertAck = async () => {
  const a = window._alertCur, rest = window._alertRest || [];
  try { await post('/api/shift-alert/dismiss', { kind: a.fam, date: a.date }); } catch (e) {}
  showAlertQueue(rest);
};
window.alertGotoVehicle = async () => {
  const a = window._alertCur; closeModal();
  try { await post('/api/shift-alert/dismiss', { kind: a.fam, date: a.date }); } catch (e) {}
  go(a.fam === 'vehicle_in' ? 'vehicle_in' : 'vehicle_out');
};

/* ---- Factory open/closed status (round 11, Talha's order) --------
   Status button at the TOP of the sidebar (green = running, red =
   closed + since-date); a slim red banner under the header while
   closed. Owner + Manager toggle it (server-enforced); Staff only
   see the status. A closure period covers whole days: it suppresses
   that date's SHIFT-entry alerts server-side, but vehicle alerts
   keep working (rock still arrives, powder still dispatches). */
const FACTORY_REASONS = ['power_outage', 'breakdown', 'maintenance_work',
  'no_material', 'other'];
function fcReasonLabel(r, rtext){
  return r === 'other' ? (rtext || t('fc_r_other')) : t('fc_r_' + (r || 'other'));
}
function factoryBtnHTML(){
  const f = STATE.factory || { closed: false };
  if (f.closed && f.current) {
    const c = f.current;
    return `<button type="button" class="fstatus closed" onclick="factoryStatusClick()">🔴 ${t('fc_closed')}<span class="fsub">${alertDateDisp(c.closed_from)} · ${c.days || 1} ${t('fc_days')}</span></button>`;
  }
  return `<button type="button" class="fstatus open" onclick="factoryStatusClick()">🟢 ${t('fc_running')}</button>`;
}
function factoryBannerHTML(){
  const f = STATE.factory || {};
  if (!f.closed || !f.current) return '';
  const c = f.current;
  const txt = t('fc_banner_txt')
    .replace('{reason}', fcReasonLabel(c.reason, c.reason_text))
    .replace('{date}', alertDateDisp(c.closed_from));
  return `<div class="fcbanner" id="fcbanner">🏭 ${esc(txt)}</div>`;
}
window.factoryStatusClick = () => {
  const f = STATE.factory || { closed: false };
  const can = ['owner', 'manager'].includes(STATE.user.role);
  if (!f.closed) {
    if (!can) {
      showModal(`<h3 style="margin-top:0">🟢 ${t('fc_running')}</h3>
        <p class="muted">${t('fc_only_om')}</p>
        <button class="ghost" onclick="closeModal()">${t('va_ok')}</button>`);
      return;
    }
    showModal(`<h3 style="margin-top:0">🏭 ${t('fc_close_t')}</h3>
      <div class="field"><label>${t('fc_from_l')}</label><input id="fc_from" type="date" value="${todayStr()}"></div>
      <div class="field"><label>${t('fc_to_l')}</label><input id="fc_to" type="date"></div>
      <div class="field"><label>${t('fc_reason_l')}</label><select id="fc_reason" onchange="fcReasonUI()">${FACTORY_REASONS.map(r => `<option value="${r}">${t('fc_r_' + r)}</option>`).join('')}</select></div>
      <div class="field" id="fc_rtext_f" style="display:none"><label>${t('fc_r_other')}</label><input id="fc_rtext" placeholder="${t('fc_rtext_ph')}"></div>
      <div class="field"><label>${t('note')}</label><input id="fc_note" placeholder="${t('sa_note_ph')}"></div>
      <div class="row" style="gap:8px;flex-wrap:wrap"><button onclick="factoryCloseSave()">${t('fc_save_close')}</button>
      <button class="ghost" onclick="closeModal()">${t('cancel_l')}</button></div>`);
    return;
  }
  const c = f.current || {};
  const info = `<h3 style="margin-top:0">🔴 ${t('fc_closed')}</h3>
    <div class="kv"><span>${t('fc_reason_l')}</span><b>${esc(fcReasonLabel(c.reason, c.reason_text))}</b></div>
    <div class="kv"><span>${t('fc_from_l')}</span><b>${alertDateDisp(c.closed_from)} · ${c.days || 1} ${t('fc_days')}</b></div>
    ${c.closed_to ? `<div class="kv"><span>${t('fc_to_l')}</span><b>${alertDateDisp(c.closed_to)}</b></div>` : ''}
    ${c.note ? `<div class="kv"><span>${t('note')}</span><b>${esc(c.note)}</b></div>` : ''}`;
  if (!can) {
    showModal(info + `<button class="ghost" onclick="closeModal()">${t('va_ok')}</button>`);
    return;
  }
  showModal(info + `<div class="row" style="gap:8px;flex-wrap:wrap"><button onclick="factoryReopen()">${t('fc_reopen_btn')}</button>
    <button class="ghost" onclick="closeModal()">${t('cancel_l')}</button></div>`);
};
window.fcReasonUI = () => {
  const f = document.getElementById('fc_rtext_f');
  if (f) f.style.display = val('fc_reason') === 'other' ? '' : 'none';
};
window.factoryCloseSave = async () => {
  try {
    const r = await post('/api/factory-close',
      { closed_from: val('fc_from'), closed_to: val('fc_to') || null,
        reason: val('fc_reason'), reason_text: val('fc_rtext'), note: val('fc_note') });
    STATE.factory = r.factory; closeModal(); okPopup(t('fc_closed_saved')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.factoryReopen = async () => {
  try {
    const r = await post('/api/factory-reopen', {});
    STATE.factory = r.factory; closeModal(); okPopup(t('fc_reopened')); render();
  } catch (e) { msg(e.message, 'err'); }
};
/* sidebar: collapsible MAIN HEADS (accordion) grouped as Factory
   Management / Accounts / Workers & Attendance / Setup & System.
   Dashboard and the Guide stay standalone on top; the group holding the
   current page always opens on navigation; the open group is remembered
   per user. Groups are presentation only — access is per-view (below). */
const NAV_TOP = [['dashboard', 'dashboard'], ['guide', 'guide'], ['profile', 'profile_t']];
const NAV_GROUPS = [
  ['g_clients', [['parties', 'parties']]],
  ['g_daily', [['vehicle_in', 'vehicle_in'], ['vehicle_out', 'vehicle_out'], ['grindprod', 'grind_prod'], ['warehouse', 'warehouse'], ['machines', 'machines']]],
  ['g_own', [['ownstock', 'own_stock'], ['outside', 'outside_grinding']]],
  ['g_accounts', [['payments', 'payments'], ['expenses', 'expenses'], ['cashbook', 'cashbook'], ['cashinhand', 'cashinhand'], ['cheques', 'cheques'], ['reports', 'reports'], ['phosdetail', 'phos_detail']]],
  ['g_workers', [['workers', 'workers'], ['departments', 'departments'], ['attendance', 'attendance'], ['leaves', 'leaves']]],
  ['g_system', [['settings', 'settings'], ['logins', 'logins'], ['alerts', 'alerts'], ['data', 'data'], ['recycle', 'recycle'], ['help', 'help']]]
];
const VIEW_GROUP = { party: 'g_clients' };
NAV_GROUPS.forEach(([g, items]) => items.forEach(([v]) => { VIEW_GROUP[v] = g; }));
/* view -> permission key for staff logins (owner/manager see everything;
   views with no key here — settings, logins, data, recycle, help — are
   owner/manager only; the Guide is always open to staff) */
const VIEW_PERM = { dashboard: 'dashboard', parties: 'parties', party: 'parties',
  vehicle_in: 'vehicles', vehicle_out: 'vehicles', warehouse: 'parties',
  machines: 'production', ownstock: 'trade',
  outside: 'trade', payments: 'payments', expenses: 'expenses',
  cashbook: 'cashbook', cheques: 'cashbook', reports: 'reports', phosdetail: 'reports', workers: 'workers',
  departments: 'workers', attendance: 'workers', leaves: 'workers', alerts: 'vehicles' };
function canView(v){
  const u = STATE.user; if (!u) return false;
  if (u.role === 'owner' || u.role === 'manager') return true;
  if (u.role === 'demo')
    /* public view-only login: every business page opens; the Setup
       & System surfaces that hold secrets or manage access stay
       shut (Settings, Logins, Data/Backup, Recycle, Alerts) — the
       server blocks them too, this is only the menu. */
    return !['settings', 'logins', 'data', 'recycle', 'alerts'].includes(v);
  if (u.role !== 'staff') return false;
  if (v === 'guide') return true;
  if (v === 'profile') return true;   /* round 12: every login has its own profile */
  /* Cash in Hand: a staff login always sees his OWN record (the server
     filters it); full access follows the cashbook perm anyway */
  if (v === 'cashinhand') return true;
  /* Grinding & Production is one merged page: either legacy perm opens it */
  if (v === 'grindprod') return Array.isArray(u.perms) && (u.perms.includes('grinding') || u.perms.includes('production'));
  const p = VIEW_PERM[v];
  return !!p && Array.isArray(u.perms) && u.perms.includes(p);
}
function firstView(){
  const all = NAV_GROUPS.flatMap(g => g[1].map(x => x[0])).concat(NAV_TOP.map(x => x[0]));
  return all.find(v => canView(v)) || 'guide';
}
let NAV_OPEN = localStorage.getItem('mill_nav_group') || '';
window.navToggle = g => {
  NAV_OPEN = (NAV_OPEN === g) ? '' : g;
  localStorage.setItem('mill_nav_group', NAV_OPEN);
  document.querySelectorAll('.navgroup').forEach(el =>
    el.classList.toggle('open', el.dataset.group === NAV_OPEN));
};
/* Pending-count badges (Talha's order, 28 Oct 2026): /api/state
   carries pending_counts keyed by view — how many things await an
   action in that section. A red number pill sits on the sidebar item
   (count > 0 only); a CLOSED group head carries the group's total so
   pending work is visible without opening every group (CSS hides the
   head pill once the group opens and the items show their own). */
function pendBadge(v){ const n = (STATE.pending_counts || {})[v] || 0; return n ? `<span class="pbadge">${n}</span>` : ''; }
/* round 12: a user's picture (or initial-letter fallback) — used by the
   header chips, the owner's Logins / Parties / Party / Proofs rows and
   the My Profile page, so a face means the same login everywhere */
function avatarHTML(uid, has, ver, name, cls){
  const c = cls || 'uav';
  if (has && uid) return `<img class="${c}" src="/api/avatar/${uid}?v=${ver || 0}" alt="">`;
  return `<span class="${c}">${esc(((name || '?').trim().charAt(0) || '?').toUpperCase())}</span>`;
}
function chipAvatarHTML(){
  const u = STATE.user || {};
  return u.has_avatar
    ? `<img src="/api/avatar/${u.id}?v=${u.avatar_ver || 0}" alt="">`
    : esc(((u.display_name || u.username || '?').trim().charAt(0) || '?').toUpperCase());
}
function buildNav(){
  const u = STATE.user;
  const link = ([v, k]) => `<a href="#" class="${VIEW === v ? 'active' : ''}" onclick="go('${v}');return false">${t(k)}${pendBadge(v)}</a>`;
  return factoryBtnHTML() + NAV_TOP.filter(([v]) => canView(v)).map(link).join('') + NAV_GROUPS.map(([g, items]) => {
    const vis = items.filter(([v]) => canView(v));
    if (!vis.length) return '';
    const gtot = vis.reduce((s, [v]) => s + ((STATE.pending_counts || {})[v] || 0), 0);
    return `<div class="navgroup ${NAV_OPEN === g ? 'open' : ''}" data-group="${g}">` +
    `<button type="button" class="navhead" onclick="navToggle('${g}')"><span>${t(g)}</span>${gtot ? `<span class="pbadge">${gtot}</span>` : ''}<span class="chev">▾</span></button>` +
    `<div class="navitems">${vis.map(link).join('')}</div></div>`;
  }).join('') + (u.role === 'owner'
    ? `<div class="sidefoot"><div class="small" style="opacity:.8">🎨 ${t('theme_colour_l')}</div>${accentDropdownHTML()}</div>` : '')
  + `<div class="sidecopy"><div>© 2026 Orush Grinding Mill — All Rights Reserved</div><div>Developed by Talha Islam</div></div>`;
}
/* Re-fetch the counts (cheap COUNT queries server-side) and repaint
   ONLY the sidebar + bell when they changed — hitched to render(), so
   every action that ends in render() (confirm/reject a proof, decide
   an adjustment, ack a handover…) drops its badge by itself. */
window.refreshPending = async () => {
  if (window._pendBusy || !STATE || !STATE.user || STATE.user.role === 'client') return;
  window._pendBusy = true;
  try {
    const st = await get('/api/state');
    if (st) {
      const before = JSON.stringify(STATE.pending_counts || {}) + '|' + (STATE.unread_notifications || 0);
      STATE.pending_counts = st.pending_counts || {};
      if (st.unread_notifications !== undefined) STATE.unread_notifications = st.unread_notifications;
      const fChanged = JSON.stringify(STATE.factory || {}) !== JSON.stringify(st.factory || {});
      if (st.factory) STATE.factory = st.factory;
      if (JSON.stringify(STATE.pending_counts) !== before.split('|')[0]
          || String(STATE.unread_notifications || 0) !== before.split('|')[1] || fChanged) {
        const sb = document.querySelector('.sidebar');
        if (sb) sb.innerHTML = buildNav();
        const bell = document.querySelector('.tb-btn.bell');
        if (bell) bell.innerHTML = '🔔' + (STATE.unread_notifications ? `<span class="dot">${STATE.unread_notifications}</span>` : '');
        const bn = document.getElementById('fcbanner'), tb = document.querySelector('.topbar');
        if (bn) bn.outerHTML = factoryBannerHTML();
        else if (tb && factoryBannerHTML()) tb.insertAdjacentHTML('afterend', factoryBannerHTML());
      }
    }
  } catch (e) {}
  window._pendBusy = false;
};
function render(){ if (window.startEvPoll) startEvPoll();
  applyPrefs();
  const u = STATE.user;
  if (u.role === 'client') { renderClient(); return; }
  if (!canView(VIEW)) VIEW = firstView();
  document.title = (STATE.mill.name || t('app'));
  const curGroup = VIEW_GROUP[VIEW] || '';
  if (curGroup && NAV_OPEN !== curGroup) { NAV_OPEN = curGroup; localStorage.setItem('mill_nav_group', NAV_OPEN); }
  const nav = buildNav();
  appEl.innerHTML = `
  <div class="topbar">
    <div class="tb-brand">
      <button type="button" class="tb-btn tb-burger" aria-label="Menu" onclick="document.getElementById('layout').classList.toggle('closed')">☰</button>
      <div class="tb-logo">${logoHTML('milllogo')}${STATE.mill.has_logo ? '' : '<span class="tb-logomark">🏭</span>'}</div>
      <div class="tb-names"><div class="tb-name">${esc(STATE.mill.name || t('app'))}</div><div class="tb-sub">${t('sys_tag')}</div></div>
    </div>
    <div class="tb-search"><svg class="tb-sicon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M20.5 20.5L16.7 16.7"></path></svg><input type="search" id="gsearch" placeholder="${t('search')}" onkeydown="if(event.key==='Enter')doSearch()"></div>
    <div class="tb-actions">
      <button type="button" class="tb-btn" title="${t('calc_l')}" onclick="openCalc()">🧮</button>
      ${langSelect('hd_lang')}
      <button type="button" class="tb-btn" id="mutebtn" onclick="toggleMute()">${localStorage.getItem('mill_mute') === '1' ? '🔇' : '🔊'}</button>
      <select class="tb-ctl" onchange="setPref('theme',this.value).then(render)"><option value="light" ${PREFS.theme === 'light' ? 'selected' : ''}>☀ ${t('light')}</option><option value="dark" ${PREFS.theme === 'dark' ? 'selected' : ''}>🌙 ${t('dark')}</option></select>
      <select class="tb-ctl" onchange="setPref('unit',this.value).then(render)"><option value="kg" ${PREFS.unit === 'kg' ? 'selected' : ''}>kg</option><option value="t" ${PREFS.unit === 't' ? 'selected' : ''}>tons</option><option value="maund" ${PREFS.unit === 'maund' ? 'selected' : ''}>maund</option></select>
    </div>
    <div class="tb-userbox">
      ${canView('alerts') ? `<button type="button" class="tb-btn bell" onclick="go('alerts')">🔔${STATE.unread_notifications ? `<span class="dot">${STATE.unread_notifications}</span>` : ''}</button>` : ''}
      <div class="tb-user"><span class="tb-avatar" style="cursor:pointer" title="${t('profile_t')}" onclick="go('profile')">${chipAvatarHTML()}</span><span class="tb-unames"><span class="tb-uname">${esc(u.display_name || u.username)}</span><span class="tb-urole">${esc(u.role)}</span></span>${u.role === 'demo' ? '<span class="tb-demo">DEMO</span>' : ''}</div>
      <button type="button" class="tb-btn tb-logout" onclick="doLogout()">${t('logout')}</button>
    </div>
  </div>
  ${factoryBannerHTML()}
  <div class="layout${window.innerWidth <= 760 ? ' closed' : ''}" id="layout"><div class="sidebar">${nav}</div>
  <div class="main" id="main">${VIEW !== 'dashboard' ? `<div class="backbar"><button type="button" class="ghost backbtn" onclick="go('dashboard')">⬅ ${t('back_btn')}</button></div>` : ''}<div id="msg" class="msg" style="display:none"></div><div id="view"></div></div></div>`;
  const fn = VIEWS[VIEW] || VIEWS.dashboard;
  fn($('#view'));
  mountAI();
  if (window.refreshPending) window.refreshPending();
}
window.doSearch = async () => {
  const q = val('gsearch'); if (!q) return;
  const r = await get('/api/search?q=' + encodeURIComponent(q));
  $('#view').innerHTML = `<div class="card"><h2>🔍 ${esc(q)}</h2>
    ${r.parties.map(p => `<div class="kv"><span>👤 ${esc(p.name)}</span><button class="small" onclick="openParty(${p.id})">${t('khata_btn')}</button></div>`).join('')}
    ${r.trips.map(x => `<div class="kv"><span>🚛 #${x.id} ${x.date} ${x.direction} ${esc(x.vehicle_no)} — ${kgDisp(x.net_kg)}</span><a target="_blank" href="/print/trip/${x.id}?u=${PREFS.unit}&lang=${PREFS.lang}">${t('slip')}</a></div>`).join('')}
    ${r.workers.map(w => `<div class="kv"><span>👷 ${esc(w.name)}</span><span>${esc(w.kind)}</span></div>`).join('')}
    ${r.payments.map(p => `<div class="kv"><span>💰 ${p.date} ${p.direction} ${fmt(p.amount)}</span><span>${esc(p.note || '')}</span></div>`).join('')}
    ${(r.expenses || []).map(x => `<div class="kv"><span>🧾 ${x.date} ${fmt(x.amount)}</span><span>${esc(x.paid_to || '')} ${esc(x.head_name || '')} ${esc(x.note || '')}</span></div>`).join('')}
    ${(!r.parties.length && !r.trips.length && !r.workers.length && !r.payments.length && !(r.expenses || []).length) ? `<p class="muted">${t('nothing_found')}</p>` : ''}</div>`;
};
window.openParty = id => { VIEW = 'party'; VIEW_ARG = id; render(); };
let VIEW_ARG = null;
/* client shell */
let CLIENT_VIEW = 'mykhata';
window.clientGo = v => { CLIENT_VIEW = v; render(); };
function renderClient(){
  const u = STATE.user;
  appEl.innerHTML = `
  <div class="topbar">
    <div class="tb-brand">
      <div class="tb-logo">${logoHTML('milllogo')}${STATE.mill.has_logo ? '' : '<span class="tb-logomark">🏭</span>'}</div>
      <div class="tb-names"><div class="tb-name">${esc(STATE.mill.name || t('app'))}</div><div class="tb-sub">${t('sys_tag')}</div></div>
    </div>
    <div class="tb-actions">
      <button type="button" class="tb-btn" title="${t('calc_l')}" onclick="openCalc()">🧮</button>
      ${langSelect('hd_lang')}
      <select class="tb-ctl" onchange="setPref('theme',this.value).then(render)"><option value="light" ${PREFS.theme === 'light' ? 'selected' : ''}>☀ ${t('light')}</option><option value="dark" ${PREFS.theme === 'dark' ? 'selected' : ''}>🌙 ${t('dark')}</option></select>
    </div>
    <div class="tb-userbox">
      <div class="tb-user"><span class="tb-avatar" style="cursor:pointer" title="${t('profile_t')}" onclick="clientGo('profile')">${chipAvatarHTML()}</span><span class="tb-unames"><span class="tb-uname">${esc(u.display_name || u.username)}</span></span></div>
      <button type="button" class="tb-btn tb-logout" onclick="doLogout()">${t('logout')}</button>
    </div>
  </div>
  <div class="main" id="main" style="max-width:860px;margin:0 auto"><div class="row" style="gap:8px;margin:10px 0 2px"><button class="${CLIENT_VIEW === 'mykhata' ? '' : 'ghost'}" onclick="clientGo('mykhata')">📒 ${t('khata')}</button><button class="${CLIENT_VIEW === 'profile' ? '' : 'ghost'}" onclick="clientGo('profile')">👤 ${t('profile_t')}</button></div><div id="msg" class="msg" style="display:none"></div><div id="view"></div></div>`;
  document.title = (STATE.mill.name || t('app'));
  if (CLIENT_VIEW === 'profile') VIEWS.profile($('#view')); else VIEWS.mykhata($('#view'));
  mountAI();
}
const VIEWS = {};

/* ---------------- views ---------------- */
VIEWS.dashboard = async el => {
  const d = await get('/api/dashboard');
  const s = await get('/api/settings').catch(() => null);
  CACHE.settings = s;
  const isOwner = STATE.user.role === 'owner';
  const pendExp = isOwner
    ? await get('/api/expenses').then(rs => rs.filter(r => r.status === 'pending')).catch(() => []) : [];
  const pendAdj = isOwner
    ? await get('/api/godam').then(g => (g.adjustments || []).filter(a => a.status === 'pending')).catch(() => []) : [];
  const tr = await get('/api/trends?days=7').catch(() => ({ days: [] }));
  window._trends = tr.days || [];
  const T = d.totals || {}, SP = d.split || {};
  const showMoney = !!d.money_visible;   // server strips money in/out for non-owners
  window._showMoney = showMoney;
  const QA = [
    ['vehicle_in', '', '🚛', t('qa_in')], ['vehicle_out', '', '🚚', t('qa_out')],
    ['grindprod', '', '⚙️', t('qa_grind')],
    ['payments', '', '💰', t('qa_payment')], ['expenses', '', '🧾', t('qa_expense')],
    ['parties', '', '👥', t('qa_client')], ['parties', '', '📒', t('qa_ledger')]];
  el.innerHTML = `
  ${STATE.backup_days !== null && STATE.backup_days >= 7 ? `<div class="msg warn">⚠ ${t('backup_warn_start')} ${STATE.backup_days} ${t('backup_warn')}</div>` : ''}
  ${pendExp.length ? `<div class="card" style="border:2px solid #e0a800"><h2>⏳ ${t('pend_exp_t')} (${pendExp.length})</h2>
    ${pendExp.map(r => `<div class="kv"><span>${r.date} · ${esc(r.head_name || '')} · ${paidDisp(r)} → ${esc(r.paid_to || '')}</span><span><b>${fmt(r.amount)}</b>
    <button class="small" onclick="exStatus(${r.id},'approved')">✓ ${t('approve')}</button>
    <button class="small danger" onclick="exStatus(${r.id},'rejected')">✗ ${t('reject')}</button></span></div>`).join('')}
    <p class="small muted">${t('pend_exp_note')}</p></div>` : ''}
  ${pendAdj.length ? `<div class="card" style="border:2px solid #e0a800"><h2>⏳ ${t('pending_adj')} (${pendAdj.length})</h2>
    ${pendAdj.map(a => `<div class="kv"><span>${a.date} · ${esc(a.party_name || t('own_word'))} · ${t('ginti_adj')} <b>${a.bags > 0 ? '+' : ''}${a.bags}</b> ${t('bags')}</span><span>
    <button class="small" onclick="adjDecide(${a.id},'approved')">✓ ${t('approve')}</button>
    <button class="small danger" onclick="adjDecide(${a.id},'rejected')">✗ ${t('reject')}</button></span></div>`).join('')}
    <p class="small muted">${t('pend_adj_note')}</p></div>` : ''}
  <div class="grid">
    <div class="stat"><div class="ic">🚛</div><div class="n">${tonsDisp(d.rock_in_today_t)}</div><div class="l">${t('rock_in')} — ${t('today')}</div></div>
    <div class="stat"><div class="ic">⚙️</div><div class="n">${tonsDisp(d.ground_today_t)}</div><div class="l">${t('grinding')} — ${t('today')}</div></div>
    <div class="stat"><div class="ic">📦</div><div class="n">${tonsDisp(d.powder_out_today_t)}</div><div class="l">${t('powder')} OUT — ${t('today')}</div></div>
    <div class="stat"><div class="ic gold">🧺</div><div class="n">${d.bags_today}</div><div class="l">${t('bags')} — ${t('today')}</div></div>
    ${showMoney ? `<div class="stat"><div class="ic">💰</div><div class="n">${fmt(d.to_receive)}</div><div class="l">${t('to_receive')}</div></div>
    <div class="stat"><div class="ic gold">💸</div><div class="n">${fmt(d.to_pay)}</div><div class="l">${t('to_pay')}</div></div>
    <div class="stat"><div class="ic">💵</div><div class="n">${fmt(d.cash_in_today)}</div><div class="l">${t('cash_in')} — ${t('today')}</div></div>
    <div class="stat"><div class="ic gold">🧾</div><div class="n">${fmt(d.cash_out_today)}</div><div class="l">${t('cash_out')} — ${t('today')}</div></div>` : ''}
  </div>
  <div class="card"><h2>⚡ ${t('quick')}</h2><div class="qagrid">
    ${QA.filter(([v]) => canView(v)).map(([v, preset, ic, label]) => `<button type="button" class="qabtn" onclick="goQA('${v}','${preset}')"><span class="qaic">${ic}</span><span>${label}</span></button>`).join('')}
  </div></div>
  <div class="card"><h2>📊 ${t('totals')}</h2>
    <div class="grid">
      <div class="stat"><div class="n">${tonsDisp(T.rock_t)}</div><div class="l">${t('total_rock')}</div></div>
      <div class="stat"><div class="n">${tonsDisp(T.powder_t)}</div><div class="l">${t('total_powder')}</div></div>
      <div class="stat"><div class="n">${T.bags || 0}</div><div class="l">${t('total_bags')}</div></div>
      ${showMoney ? `<div class="stat"><div class="n">${fmt(T.to_receive)}</div><div class="l">${t('to_receive')}</div></div>
      <div class="stat"><div class="n">${fmt(T.to_pay)}</div><div class="l">${t('to_pay')}</div></div>` : ''}
    </div>
    <div class="wrap"><table><tr><th></th><th>${t('rock')}</th><th>${t('powder')}</th><th>${t('bags')}</th></tr>
      <tr><td><b>${t('own_s')}</b></td><td>${tonsDisp(SP.own_rock_t)}</td><td>${tonsDisp(SP.own_powder_t)}</td><td>${SP.own_bags || 0}</td></tr>
      <tr><td><b>${t('clients_s')}</b></td><td>${tonsDisp(SP.clients_rock_t)}</td><td>${tonsDisp(SP.clients_powder_t)}</td><td>${SP.clients_bags || 0}</td></tr>
    </table></div></div>
  <div class="card"><h2>📈 ${t('daily_progress')}</h2>
    <div class="row"><div class="field" style="flex:0"><label>&nbsp;</label>
      <select id="dp_metric" onchange="dashChart()">
        <option value="rock_in_t">${t('rock_in')} (t)</option>
        <option value="ground_t">${t('grinding')} (t)</option>
        <option value="bags">${t('bags')}</option>
        ${showMoney ? `<option value="cash_in">${t('cash_in')}</option>
        <option value="cash_out">${t('cash_out')}</option>` : ''}
      </select></div></div>
    <div id="dp_chart"></div><div id="dp_deltas" style="margin-top:8px"></div></div>
  ${d.parties.length ? '' : `<div class="card"><h2>👋 ${t('welcome')}!</h2><p class="muted">${t('first_steps')}</p><button onclick="go('parties')">➕ ${t('parties')}</button></div>`}
  <div class="card"><h2>⚙ ${t('now_grinding')}</h2>
    ${d.now_grinding.length ? d.now_grinding.map(g => `<div class="kv"><span>${esc(g.party_name || t('own_word'))} · ${esc(g.started)}</span><button class="small" onclick="stopGrind(${g.id})">${t('stop_l')}</button></div>`).join('') : `<span class="muted">${t('no_session')}</span>`}
    <div class="row" style="margin-top:8px"><div class="field"><label>${t('now_grinding_party')}</label><select id="ng_party"><option value="">${t('own_opt')}</option>${partyOpts(null, 'grinding')}</select></div>
    <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="startGrind()">▶ ${t('start_l')}</button></div></div></div>
  <div class="card"><h2>🏭 ${t('own_stock')}</h2>
    <div class="kv"><span>${t('rock')}</span><b>${tonsDisp(d.own_stock.rock_t)}</b></div>
    <div class="kv"><span>${t('powder')}</span><b>${tonsDisp(d.own_stock.powder_t)} / ${d.own_stock.powder_bags} ${t('bags')}</b></div>
    <div class="kv"><span>${t('bardana')}</span><b>${d.bardana.left} ${d.bardana.low ? `<span class="badge red">${t('low')}</span>` : ''}</b></div></div>
  ${(d.powder_ageing || []).length ? `<div class="card" style="border:2px solid #e0a800"><h2>⏰ ${t('powder_ageing')}</h2>
    ${d.powder_ageing.map(a => `<div class="kv"><span>${esc(a.party)}</span><b>${a.bags} ${t('bags')} · ${tonsDisp(a.tons)} · ${a.days} ${t('days_waiting')}</b></div>`).join('')}
    <p class="small muted">${t('age_note')}</p></div>` : ''}
  ${(d.maint_due || []).length ? `<div class="card" style="border:2px solid #e0a800"><h2>🔧 ${t('maint_due')}</h2>
    ${d.maint_due.map(m => `<div class="kv"><span>${esc(m.machine_name || '')} · ${esc(m.work_type || '')}</span><b>${m.next_due}${m.next_due < d.date ? ' · <span class="badge red">' + t('overdue') + '</span>' : ''}</b></div>`).join('')}</div>` : ''}
  <div class="card"><h2>👥 ${t('parties')} — ${t('balance')}</h2><div class="wrap"><table>
    <tr><th>${t('party')}</th><th>${t('balance')}</th><th>${t('ageing_h')}</th><th></th></tr>
    ${d.parties.map(p => `<tr><td>${esc(p.name)} ${p.over_limit ? `<span class="badge red">${t('over_credit')}</span>` : ''}<br><span class="muted small">${(p.roles || '').split(',').filter(Boolean).map(r => t(r === 'grinding' ? 'grinding' : r)).join(', ')}</span></td>
      <td class="num">${fmt(p.balance)}${balTag(p.balance)}</td><td></td><td><button class="small" onclick="openParty(${p.id})">${t('khata_btn')}</button></td></tr>`).join('')}
    <tr><td class="muted">${t('totals')}</td><td></td><td>${d.ageing ? fmt(d.ageing.d0_30) + ' / ' + fmt(d.ageing.d31_60) + ' / ' + fmt(d.ageing.d60p) : ''}</td><td></td></tr></table></div></div>
  ${d.cheques_due.length ? `<div class="card"><h2>🧾 ${t('cheques_due')}</h2>${d.cheques_due.map(c => `<div class="kv"><span>${esc(c.party_name || '')} — ${esc(c.cheque_no)} (${esc(c.bank)})</span><b>${fmt(c.amount)} · ${c.due_date}</b></div>`).join('')}</div>` : ''}
  <div class="card"><h2>🚛 ${t('recent_vehicles')}</h2><div class="wrap"><table>
    <tr><th>${t('date')}</th><th></th><th>${t('vehicle')}</th><th>${t('net')}</th><th>${t('bags')}</th><th></th></tr>
    ${d.recent.map(x => `<tr><td>${x.date}</td><td>${x.direction}</td><td>${esc(x.vehicle_no)}</td><td>${kgDisp(x.net_kg)}</td><td>${x.bags}</td><td><a target="_blank" href="/print/trip/${x.id}?u=${PREFS.unit}&lang=${PREFS.lang}">🖨 ${t('slip')}</a></td></tr>`).join('')}</table></div></div>`;
  dashChart();
};
let QA_PRESET = '';
window.goQA = (v, preset) => { QA_PRESET = preset || ''; VIEW = v; render(); };
window.adjDecide = async (id, st) => {
  try { await post('/api/stock-adjustments/decide', { id, status: st }); okPopup(t('saved')); render(); }
  catch (e) { msg(e.message, 'err'); }
};
window.dashChart = () => {
  const box = document.getElementById('dp_chart');
  if (!box) return;
  const days = window._trends || [];
  const metric = (document.getElementById('dp_metric') || {}).value || 'rock_in_t';
  const max = Math.max(1, ...days.map(x => Number(x[metric] || 0)));
  const W = 340, H = 120, bw = W / Math.max(1, days.length);
  box.innerHTML = `<svg viewBox="0 0 ${W} ${H + 22}" style="width:100%;max-width:560px" role="img">` +
    days.map((x, i) => {
      const v = Number(x[metric] || 0);
      const h = Math.round((v / max) * (H - 18));
      return `<rect x="${(i * bw + 4).toFixed(1)}" y="${H - h}" width="${(bw - 8).toFixed(1)}" height="${h}" rx="3" fill="var(--accent)"></rect>` +
        `<text x="${(i * bw + bw / 2).toFixed(1)}" y="${H - h - 4}" text-anchor="middle" font-size="9" fill="var(--ink)">${metric === 'cash_in' || metric === 'cash_out' ? Math.round(v) : v}</text>` +
        `<text x="${(i * bw + bw / 2).toFixed(1)}" y="${H + 14}" text-anchor="middle" font-size="9" fill="var(--muted)">${x.date.slice(5)}</text>`;
    }).join('') + '</svg>';
  const dbox = document.getElementById('dp_deltas');
  if (dbox && days.length >= 2) {
    const td = days[days.length - 1], yd = days[days.length - 2];
    const M = [['rock_in_t', t('rock_in'), 0], ['ground_t', t('grinding'), 0], ['bags', t('bags'), 0],
               ['cash_in', t('cash_in'), 0], ['cash_out', t('cash_out'), 1]]
      .filter(([k]) => window._showMoney !== false || (k !== 'cash_in' && k !== 'cash_out'));
    dbox.innerHTML = M.map(([k, label, invert]) => {
      const a = Number(td[k] || 0), b = Number(yd[k] || 0), diff = a - b;
      const up = diff >= 0;
      const good = invert ? !up : up;
      const val = (k === 'cash_in' || k === 'cash_out') ? fmt(a) : (k === 'bags' ? a : tonsDisp(a));
      const dv = (k === 'cash_in' || k === 'cash_out') ? fmt(Math.abs(diff)) : (k === 'bags' ? Math.abs(diff) : tonsDisp(Math.abs(diff)));
      return `<div class="kv"><span>${label} — ${t('today')}</span><b>${val} <span style="color:${diff === 0 ? 'var(--muted)' : (good ? '#0c7a4e' : '#c0392b')}">${diff === 0 ? '—' : (up ? '▲' : '▼') + ' ' + dv}</span> <span class="muted small">${t('vs_yday')}</span></b></div>`;
    }).join('');
  }
};
window.startGrind = async () => { await post('/api/grind/start', { party_id: val('ng_party') || null }); okPopup(t('sess_started')); render(); };
window.stopGrind = async id => { await post('/api/grind/stop', { id }); okPopup(t('sess_stopped')); render(); };

const GUIDE_STEPS = {
en: [
  { icon: '👥', view: 'parties', title: 'Register a Client', desc: 'Add every client, supplier and buyer here, with roles. One party can hold many roles - one ledger, one net balance.' },
  { icon: '🚛', view: 'vehicle_in', title: 'Vehicle In — Rock Arrives', desc: 'Record a Vehicle In on its own page: write the Net Weight only, and print the voucher. The Rock purchase block shows ONLY when the Party is Own (Mine) — a client party\'s Vehicle In is a grinding arrival only (clients bring their own rock). On an Own entry, if the rock was bought, add its rate on the same entry (Factory ponch rate = delivered rate, no rent; Mine rate = rent is added) and pick Buy from — the purchase money posts to that seller\'s khata; on Mine rate you also choose whether the rent goes to the Seller or to the Driver (cash).' },
  { icon: '⚙️', view: 'grindprod', title: 'Grinding & Production', desc: 'One entry for the whole job: a party\'s grinding, Day or Night shift, grade %, shift times, the powder bags packed and the filter powder bags - both outputs are counted in bags, the form shows the shift\'s total live (bags x kg per bag = kg = tons), and one save records the grinding — the powder bags credit that party\'s warehouse stock, while the filter powder bags are the mill\'s own stock, never the party\'s. Kg per bag comes from the Bag weight defaults card at the end of this page.' },
  { icon: '🏬', view: 'warehouse', title: 'Warehouse / Stock', desc: 'Bags made, bags gone, bags ready - per party and your own, with weights in tons. One Bags card records the mill bardana and party bags - pick the bag type at the top of the card.' },
  { icon: '🚚', view: 'vehicle_out', title: 'Vehicle Out — Powder Dispatch', desc: 'Record a Vehicle Out on its own page when powder leaves: bags and net weight. An optional grinding rate posts the charge and loading charges are entered here. For a party trip, powder sales are entered in the party Ledger — the trip is dispatch only. On an Own dispatch the sale can be recorded on the trip itself (Powder sold to + Sale rate) instead — never both for the same goods — and the Grinding rate stays hidden because it is our own material. The form shows the powder stock available for the selected party (or your Own stock), and if a dispatch exceeds that stock the save asks for confirmation first.' },
  { icon: '🔄', view: 'ownstock', title: 'Own Stock & Trade', desc: 'No separate Own Trade page: buy at the gate on Vehicle In, or buy and sell off-gate in a party Ledger (Add Buy / Add Sell — first pick the item: Rock, Powder or Other); an Own Vehicle Out dispatch can also carry its own sale (Powder sold to + rate) instead of a Ledger Sell — never both. This page shows your stock and the full trade history (Gate / Ledger / Excel / Direct); Direct Trade — buy from one party, sell to another, goods never enter the mill — is added here.' },
  { icon: '🏭', view: 'outside', title: 'Outside Grinding', desc: 'When your rock is ground by ANOTHER mill: the rock goes DIRECTLY from the mine to that factory and the powder is sold from there — your godam never moves. Record Rock Sent (mine/seller → factory, agreed rate; an optional rock rate makes the purchase payable to the seller; NO charge yet), then a Grinding Bill when you settle with the factory (powder ground + actual rock used + rate — the charge accrues there as YOUR payable in their khata, with an optional Paid Now). Powder Sold sells from the factory stock. The page shows per-factory sent / ground / powder / wastage / remaining / charges.' },
  { icon: '💰', view: 'payments', title: 'Payments', desc: 'Money in and out per party: cash, bank, online or cheque, with reference numbers.' },
  { icon: '🧾', view: 'expenses', title: 'Expenses / Cash', desc: 'The Expense Ledger, Cash Book, Cash in Hand and the Cheque Register.' },
  { icon: '👷', view: 'workers', title: 'Workers / Attendance', desc: 'Workers (theka or salary), departments, attendance, leave and approvals.' },
  { icon: '📈', view: 'reports', title: 'Reports', desc: 'Monthly Profit and Loss, cost per ton and the party business summary.' },
  { icon: '💾', view: 'data', title: 'Backup', desc: 'Take a one-click backup from Data and keep the ZIP in MEGA / Google Drive.' }
],
ur: [
  { icon: '👥', view: 'parties', title: 'گاہک درج کریں', desc: 'ہر گاہک، سپلائر اور خریدار یہاں شامل کریں، رول کے ساتھ۔ ایک پارٹی کے کئی رول ہو سکتے ہیں — کھاتہ ایک، نیٹ بیلنس ایک۔' },
  { icon: '🚛', view: 'vehicle_in', title: 'گاڑی اندر — پتھر آیا', desc: 'گاڑی IN اس کے اپنے صفحے پر لکھیں: صرف خالص وزن لکھیں اور واؤچر پرنٹ کریں۔ خرید والا حصہ صرف تب نظر آتا ہے جب پارٹی اپنی ہو — گاہک پارٹی کی گاڑی اندر صرف پسائی کی آمد ہے (گاہک اپنا پتھر خود لاتا ہے)۔ اپنی انٹری پر پتھر خریدا گیا ہو تو اسی انٹری پر اس کا ریٹ لکھیں (فیکٹری پہنچ ریٹ = کرایہ نہیں؛ مائن ریٹ = کرایہ شامل) اور کس سے خریدا منتخب کریں — خرید کے پیسے اسی بیچنے والے کے کھاتے میں جاتے ہیں؛ مائن ریٹ پر یہ بھی منتخب کریں کہ کرایہ بیچنے والے کو جائے گا یا ڈرائیور کو (نقد)۔' },
  { icon: '⚙️', view: 'grindprod', title: 'پسائی و پیداوار', desc: 'پورے کام کی ایک انٹری: کس پارٹی کی پسائی ہوئی، دن یا رات کی شفٹ، گریڈ %، شفٹ کے اوقات، بنے ہوئے پاؤڈر تھیلے اور فلٹر پاؤڈر تھیلے — دونوں پیداوار تھیلوں میں گنی جاتی ہیں، فارم شفٹ کا کل زندہ دکھاتا ہے (تھیلے × فی تھیلا کلو = کلو = ٹن)، اور ایک ہی محفوظ سے پسائی درج ہوتی ہے اور تھیلے گودام اسٹاک میں جمع ہو جاتے ہیں۔ فی تھیلا کلو اس صفحے کے آخر میں تھیلے کے وزن کی طے شدہ قدروں والے کارڈ سے آتا ہے۔' },
  { icon: '🏬', view: 'warehouse', title: 'گودام / اسٹاک', desc: 'تھیلے بنے، تھیلے گئے، تھیلے تیار — ہر پارٹی اور اپنے، ٹن وزن کے ساتھ۔ ایک ہی تھیلے کارڈ میں مل کا باردانہ اور پارٹی کے تھیلے درج ہوتے ہیں — کارڈ کے اوپر قسم منتخب کریں۔' },
  { icon: '🚚', view: 'vehicle_out', title: 'روانگی — گاڑی باہر', desc: 'پاؤڈر جاتے وقت گاڑی OUT اس کے اپنے صفحے پر لکھیں: تھیلے اور خالص وزن؛ اختیاری پسائی ریٹ سے چارج لگ جاتا ہے اور لوڈنگ چارجز یہیں لکھے جاتے ہیں۔ پارٹی ٹرپ پر پاؤڈر کی فروخت پارٹی کے کھاتے میں درج ہوتی ہے — ٹرپ صرف روانگی ہے۔ اپنی روانگی پر فروخت اسی ٹرپ پر بھی لکھی جا سکتی ہے (کس کو فروخت + فروخت ریٹ) — ایک ہی مال دونوں جگہ کبھی نہیں — اور پسائی ریٹ چھپا رہتا ہے کیونکہ یہ ہمارا اپنا مال ہے۔ فارم منتخب پارٹی کا دستیاب پاؤڈر اسٹاک دکھاتا ہے (یا اپنا اسٹاک)، اور روانگی اس اسٹاک سے زیادہ ہو تو save سے پہلے تصدیق مانگی جاتی ہے۔' },
  { icon: '🔄', view: 'ownstock', title: 'اپنا اسٹاک و تجارت', desc: 'الگ اپنی تجارت کا صفحہ نہیں: خرید گیٹ پر گاڑی اندر سے، یا بغیر گیٹ کے پارٹی کے کھاتے میں خرید و فروخت (خرید / فروخت شامل کریں — پہلے شے منتخب کریں: پتھر، پاؤڈر یا دیگر)؛ اپنی گاڑی باہر روانگی اپنی فروخت خود بھی لکھ سکتی ہے (کس کو فروخت + ریٹ) کھاتہ فروخت کی جگہ — دونوں کبھی نہیں۔ یہ صفحہ آپ کا اسٹاک اور پوری تجارت تاریخ (گیٹ / کھاتہ / ایکسل / براہ راست) دکھاتا ہے؛ براہ راست تجارت — ایک پارٹی سے خرید، دوسری کو فروخت، مال فیکٹری میں نہیں آتا — یہیں شامل ہوتی ہے۔' },
  { icon: '🏭', view: 'outside', title: 'باہر پسائی', desc: 'جب آپ کا پتھر دوسری مل پسوائے: پتھر سیدھا کان سے اس فیکٹری جاتا ہے اور پاؤڈر بھی وہیں سے بکتا ہے — آپ کا گودام نہیں ہلتا۔ پتھر بھیجا لکھیں (کان/بیچنے والا ← فیکٹری، طے شدہ ریٹ؛ اختیاری پتھر ریٹ خرید کی رقم بیچنے والے کے کھاتے میں لگاتا ہے؛ ابھی کوئی چارج نہیں)، پھر فیکٹری سے حساب کے وقت پسائی بل لگائیں (پاؤڈر پسا + اصل استعمال شدہ پتھر + ریٹ — چارج وہیں بنتا ہے، ان کے کھاتے میں آپ کی دینی رقم، اختیاری ابھی ادا کے ساتھ)۔ پاؤڈر فروخت فیکٹری کے اسٹاک سے بکتا ہے۔ صفحے پر ہر فیکٹری کا بھیجا / پسا / پاؤڈر / ضیاع / باقی / چارجز نظر آتا ہے۔' },
  { icon: '💰', view: 'payments', title: 'ادائیگیاں', desc: 'ہر پارٹی سے رقم اندر اور باہر: نقد، بینک، آن لائن یا چیک، حوالہ نمبر کے ساتھ۔' },
  { icon: '🧾', view: 'expenses', title: 'اخراجات / نقد', desc: 'اخراجات لیجر، کیش بک، ہاتھ میں نقد اور چیک رجسٹر۔' },
  { icon: '👷', view: 'workers', title: 'مزدور / حاضری', desc: 'مزدور (ٹھیکہ یا تنخواہ)، شعبے، حاضری، چھٹی اور منظوریاں۔' },
  { icon: '📈', view: 'reports', title: 'رپورٹس', desc: 'ماہانہ نفع نقصان، فی ٹن لاگت اور پارٹی کاروبار خلاصہ۔' },
  { icon: '💾', view: 'data', title: 'بیک اپ', desc: 'ڈیٹا سے ایک کلک میں بیک اپ لیں اور ZIP کو MEGA / Google Drive میں رکھیں۔' }
],
hi: [
  { icon: '👥', view: 'parties', title: 'ग्राहक दर्ज करें', desc: 'हर ग्राहक, सप्लायर और ख़रीदार यहाँ भूमिकाओं के साथ जोड़ें। एक पार्टी की कई भूमिकाएँ हो सकती हैं — खाता एक, नेट शेष एक।' },
  { icon: '🚛', view: 'vehicle_in', title: 'वाहन अंदर — रॉक आया', desc: 'वाहन IN उसके अपने पृष्ठ पर लिखें: केवल शुद्ध वज़न लिखें और वाउचर प्रिंट करें। ख़रीद वाला भाग केवल तब दिखता है जब पार्टी अपनी हो — ग्राहक पार्टी की गाड़ी अंदर केवल पिसाई की आमद है (ग्राहक अपना रॉक ख़ुद लाता है)। अपनी एंट्री पर रॉक ख़रीदा गया हो तो उसी एंट्री पर उसकी दर लिखें (फ़ैक्टरी पहुँच दर = किराया नहीं; माइन दर = किराया जुड़ता है) और किससे ख़रीदा चुनें — ख़रीद के पैसे उसी विक्रेता के खाते में जाते हैं; माइन दर पर यह भी चुनें कि किराया विक्रेता को जाएगा या ड्राइवर को (नकद)।' },
  { icon: '⚙️', view: 'grindprod', title: 'पिसाई और उत्पादन', desc: 'पूरे काम की एक एंट्री: किस पार्टी की पिसाई हुई, दिन या रात की शिफ़्ट, ग्रेड %, शिफ़्ट के समय, बने हुए पाउडर बोरे और फ़िल्टर पाउडर बोरे — दोनों उत्पादन बोरों में गिने जाते हैं, फ़ॉर्म शिफ़्ट का योग लाइव दिखाता है (बोरे × प्रति बोरा किलो = किलो = टन), और एक ही सहेज से पिसाई दर्ज होती है और बोरे गोदाम स्टॉक में जमा हो जाते हैं। प्रति बोरा किलो इस पृष्ठ के अंत में बोरे के वज़न की डिफ़ॉल्ट वाले कार्ड से आता है।' },
  { icon: '🏬', view: 'warehouse', title: 'गोदाम / स्टॉक', desc: 'बोरे बने, बोरे गए, बोरे तैयार — हर पार्टी और अपने, टन वज़न के साथ। एक ही बोरे कार्ड में मिल का बरदाना और पार्टी के बोरे दर्ज होते हैं — कार्ड के ऊपर प्रकार चुनें।' },
  { icon: '🚚', view: 'vehicle_out', title: 'रवानगी — वाहन बाहर', desc: 'पाउडर जाते समय वाहन OUT उसके अपने पृष्ठ पर लिखें: बोरे और शुद्ध वज़न; वैकल्पिक पिसाई दर से शुल्क लग जाता है और लोडिंग शुल्क यहीं लिखे जाते हैं। पार्टी ट्रिप पर पाउडर बिक्री पार्टी के खाते में दर्ज होती है — ट्रिप केवल रवानगी है। अपनी रवानगी पर बिक्री इसी ट्रिप पर भी लिखी जा सकती है (किसे बेचा + बिक्री दर) — एक ही माल दोनों जगह कभी नहीं — और पिसाई दर छिपी रहती है क्योंकि यह हमारा अपना माल है। फ़ॉर्म चुनी पार्टी का उपलब्ध पाउडर स्टॉक दिखाता है (या अपना स्टॉक), और रवानगी उस स्टॉक से अधिक हो तो save से पहले पुष्टि माँगी जाती है।' },
  { icon: '🔄', view: 'ownstock', title: 'अपना स्टॉक व व्यापार', desc: 'अलग अपना व्यापार पेज नहीं: ख़रीद गेट पर गाड़ी अंदर से, या बिना गेट के पार्टी के खाते में ख़रीद व बिक्री (ख़रीद / बिक्री जोड़ें — पहले वस्तु चुनें: रॉक, पाउडर या अन्य); अपनी गाड़ी बाहर रवानगी अपनी बिक्री ख़ुद भी लिख सकती है (किसे बेचा + दर) खाता बिक्री की जगह — दोनों कभी नहीं। यह पेज आपका स्टॉक और पूरा व्यापार इतिहास (गेट / खाता / एक्सेल / सीधा) दिखाता है; सीधा व्यापार — एक पार्टी से ख़रीद, दूसरी को बिक्री, माल फैक्टरी में नहीं आता — यहीं जुड़ता है।' },
  { icon: '🏭', view: 'outside', title: 'बाहर पिसाई', desc: 'जब आपका रॉक दूसरी मिल पिसवाए: रॉक सीधा खदान से उस फ़ैक्ट्री जाता है और पाउडर भी वहीं से बिकता है — आपका गोदाम नहीं हिलता। रॉक भेजा लिखें (खदान/विक्रेता → फ़ैक्ट्री, तय दर; वैकल्पिक रॉक दर ख़रीद की राशि विक्रेता के खाते में लगाता है; अभी कोई शुल्क नहीं), फिर फ़ैक्ट्री से हिसाब के समय पिसाई बिल लगाएँ (पाउडर पिसा + असली इस्तेमाल रॉक + दर — शुल्क वहीं बनता है, उनके खाते में आपकी देय राशि, वैकल्पिक अभी अदा के साथ)। पाउडर बिक्री फ़ैक्ट्री के स्टॉक से बिकता है। पृष्ठ पर हर फ़ैक्ट्री का भेजा / पिसा / पाउडर / वेस्टेज / बाकी / शुल्क दिखता है।' },
  { icon: '💰', view: 'payments', title: 'भुगतान', desc: 'हर पार्टी से पैसा अंदर और बाहर: नकद, बैंक, ऑनलाइन या चेक, संदर्भ नंबर के साथ।' },
  { icon: '🧾', view: 'expenses', title: 'खर्च / नकद', desc: 'खर्च लेजर, कैश बुक, हाथ में नकद और चेक रजिस्टर।' },
  { icon: '👷', view: 'workers', title: 'मज़दूर / हाज़िरी', desc: 'मज़दूर (ठेका या वेतन), विभाग, हाज़िरी, छुट्टी और स्वीकृतियाँ।' },
  { icon: '📈', view: 'reports', title: 'रिपोर्ट', desc: 'मासिक लाभ-हानि, प्रति टन लागत और पार्टी व्यापार सारांश।' },
  { icon: '💾', view: 'data', title: 'बैकअप', desc: 'डेटा से एक क्लिक में बैकअप लें और ZIP को MEGA / Google Drive में रखें।' }
]};

VIEWS.guide = el => {
  const steps = GUIDE_STEPS[PREFS.lang] || GUIDE_STEPS.en;
  el.innerHTML = `<div class="card guidecard"><h2>📖 ${t('guide')}</h2>
  <p class="muted">${t('guide_intro')}</p>
  <div class="guideflow">
  ${steps.map((s, i) => `<div class="gstep">
     <div class="gnum">${i + 1}</div>
     <div class="gbody"><div class="gtitle"><span class="gicon">${s.icon}</span> ${esc(s.title)}</div>
     <p class="muted">${esc(s.desc)}</p>
     <button class="small" onclick="go('${s.view}')">${t('open')} →</button></div>
   </div>`).join('')}
  </div></div>`;
};

VIEWS.parties = async el => {
  await loadBase();
  el.innerHTML = `<div class="card"><h2>➕ ${t('parties')}</h2>
   <div class="row"><div class="field"><label>${t('name_l')} *</label><input id="p_name"></div>
   <div class="field"><label>${t('phone_l')}</label><input id="p_phone" oninput="waSameSync()"></div>
   <div class="field"><label>WhatsApp</label><input id="p_wa">
   <label class="small" style="display:block;margin-top:5px;font-weight:400"><input type="checkbox" id="p_wa_same" onchange="waSameToggle()"> ${t('wa_same_l')}</label></div></div>
   <div class="field"><label>${t('address_l')}</label><input id="p_addr"></div>
   <div class="field"><label>${t('email_l')}</label><input id="p_email" type="email" placeholder="client@example.com"></div>
   <div class="row"><div class="field"><label>${t('roles_l')}</label><div>
     ${['supplier', 'buyer', 'grinding'].map(r => `<label style="display:inline-block;margin-inline-end:12px"><input type="checkbox" class="p_role" value="${r}"> ${r === 'grinding' ? t('grinding') : t(r)}</label>`).join('')}</div></div>
   <div class="field"><label>${t('credit_limit')}</label><input id="p_credit" type="number"></div>
   <div class="field"><label>${t('open_date_l')}</label><input id="p_open_date" type="date" value="${todayStr()}"></div></div>
   <div class="field"><label>${t('opening')}</label>
     <div class="radiocards">
       <label class="radiocard"><input type="radio" name="p_open_dir" value="plus" checked><span>➕ ${t('owes_us')}</span></label>
       <label class="radiocard"><input type="radio" name="p_open_dir" value="minus"><span>➖ ${t('owe_client')}</span></label>
     </div>
     <input id="p_open" type="number" placeholder="Rs">
     <div class="small muted">${t('opening_hint')}</div></div>
   <p id="p_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="p_save" onclick="addParty()">${t('add')}</button> <button id="p_cancel" class="ghost" style="display:none" onclick="cancelPartyEdit()">${t('cancel_l')}</button></div>
  <div class="card">${xlBar('parties')}<div class="wrap"><table><tr><th>${t('party')}</th><th>${t('roles_l')}</th><th>${t('balance')}</th><th>${t('stock_l')}</th><th></th></tr>
   ${CACHE.parties.map(p => `<tr><td><span style="display:inline-flex;align-items:center;gap:7px">${avatarHTML(p.cuid, p.cavatar, p.caver, p.name)}<b>${esc(p.name)}</b></span><br><span class="muted small">${esc(p.phone || '')}</span>${p.open_date ? `<br><span class="muted small">📅 ${t('opened_l')}: ${dfmt(p.open_date)}</span>` : ''}</td>
     <td>${(p.roles || '').split(',').filter(Boolean).map(r => `<span class="badge">${r === 'grinding' ? t('grinding') : t(r)}</span>`).join('')}</td>
     <td class="num">${fmt(p.balance)}${balTag(p.balance)}</td>
     <td class="small">${t('rock')} ${tonsDisp(p.stock.rock_waiting_t)} · ${t('powder')} ${tonsDisp(p.stock.powder_ready_t)} / ${p.stock.bags_ready} ${t('bags')}</td>
     <td><button class="small" onclick="openParty(${p.id})">${t('khata_btn')}</button>
     <a class="small" target="_blank" href="/print/party/${p.id}?u=${PREFS.unit}">🖨</a>
     ${isOwner() ? `<button class="small ghost" onclick="editParty(${p.id})">${t('edit')}</button>` : ''}
     ${delBtn('parties', p.id)}</td></tr>`).join('')}</table></div></div>`;
};
window.waSameSync = () => { const s = $('#p_wa_same'); if (s && s.checked) $('#p_wa').value = $('#p_phone').value; };
window.waSameToggle = () => {
  const s = $('#p_wa_same'), wa = $('#p_wa'); if (!s || !wa) return;
  if (s.checked) { wa.value = $('#p_phone').value; wa.readOnly = true; }
  else wa.readOnly = false;
};
window.addParty = async () => {
  if (!reqCheck([['p_name', 'fl_name', 'text']])) return;
  const roles = [...document.querySelectorAll('.p_role:checked')].map(x => x.value);
  const dirEl = document.querySelector('input[name="p_open_dir"]:checked');
  const sign = dirEl && dirEl.value === 'minus' ? -1 : 1;
  try { await post('/api/parties', { name: val('p_name'), phone: val('p_phone'), whatsapp: val('p_wa'), email: val('p_email'), open_date: val('p_open_date'),
    address: val('p_addr'), roles, credit_limit: num('p_credit'),
    opening_balance: sign * Math.abs(num('p_open')) });
    okPopup(t('party_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.editParty = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = CACHE.parties.find(x => x.id === id); if (!r) return;
  EDIT_PARTY = id;
  $('#p_name').value = r.name || '';
  $('#p_phone').value = r.phone || '';
  $('#p_wa').value = r.whatsapp || '';
  const wsBox = $('#p_wa_same');
  if (wsBox) { wsBox.checked = !!(r.phone && r.whatsapp && String(r.phone) === String(r.whatsapp)); waSameToggle(); }
  $('#p_email').value = r.email || '';
  $('#p_addr').value = r.address || '';
  const roles = (r.roles || '').split(',').filter(Boolean);
  document.querySelectorAll('.p_role').forEach(cb => { cb.checked = roles.includes(cb.value); });
  $('#p_credit').value = r.credit_limit || '';
  $('#p_open_date').value = r.open_date || todayStr();
  const ob = +r.opening_balance || 0;
  const dirEl = document.querySelector(`input[name="p_open_dir"][value="${ob < 0 ? 'minus' : 'plus'}"]`);
  if (dirEl) dirEl.checked = true;
  $('#p_open').value = Math.abs(ob) || '';
  editSwap('p_save', 'updateParty()', 'p_cancel', 'p_editing');
};
window.updateParty = async () => {
  if (!reqCheck([['p_name', 'fl_name', 'text']])) return;
  const roles = [...document.querySelectorAll('.p_role:checked')].map(x => x.value);
  const dirEl = document.querySelector('input[name="p_open_dir"]:checked');
  const sign = dirEl && dirEl.value === 'minus' ? -1 : 1;
  try { await post('/api/parties', { id: EDIT_PARTY, name: val('p_name'), phone: val('p_phone'), whatsapp: val('p_wa'), email: val('p_email'), open_date: val('p_open_date'),
    address: val('p_addr'), roles, credit_limit: num('p_credit'),
    opening_balance: sign * Math.abs(num('p_open')) });
    EDIT_PARTY = null; okPopup(t('party_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.cancelPartyEdit = () => { EDIT_PARTY = null; render(); };

VIEWS.party = async el => {
  const d = await get('/api/parties/' + VIEW_ARG);
  const p = d.party;
  const canTrade = STATE.user.role === 'owner' || STATE.user.role === 'manager' || (STATE.user.perms || []).includes('trade');
  TRADE_MODE = 'buy'; TRADE_ITEM = 'rock';
  window._partyDetail = d;
  el.innerHTML = `<div class="card"><h2>${avatarHTML(p.cuid, p.cavatar, p.caver, p.name, 'uav uav-lg')} ${esc(p.name)} <span class="muted small">${(p.roles || '').split(',').filter(Boolean).map(r => t(r === 'grinding' ? 'grinding' : r)).join(', ')}</span></h2>
   ${p.open_date ? `<p class="small muted" style="margin:0 0 8px">📅 ${t('opened_l')}: ${dfmt(p.open_date)}</p>` : ''}
   <div class="grid">
    <div class="stat"><div class="n">${fmt(d.balance)}</div><div class="l">${t('balance')} ${d.balance > 0 ? '(' + t('to_receive') + ')' : d.balance < 0 ? '(' + t('to_pay') + ')' : '(' + t('bal_clear') + ')'}</div></div>
    <div class="stat"><div class="n">${tonsDisp(d.stock.rock_in_t)}</div><div class="l">${t('rock_in_full')}</div></div>
    <div class="stat"><div class="n">${tonsDisp(d.stock.rock_waiting_t)}</div><div class="l">${t('rock_waiting')}</div></div>
    <div class="stat"><div class="n">${tonsDisp(d.stock.powder_ready_t)}</div><div class="l">${t('powder_ready')} (${d.stock.bags_ready} ${t('bags')})</div></div>
    <div class="stat"><div class="n">${d.stock.grinding_loss_pct}%</div><div class="l">${t('grinding_loss')}</div></div>
   </div>
   <p><a target="_blank" href="/print/party/${p.id}?u=${PREFS.unit}">🖨 ${t('print')} ${t('ledger')}</a>
   ${p.whatsapp ? ` · <a target="_blank" href="https://wa.me/${String(p.whatsapp).replace(/^0/, '92').replace(/\D/g, '')}">💬 WhatsApp</a>` : ''}</p>
   <p><button onclick="waKhata(${p.id})">${t('wa_khata')}</button> <button class="ghost" onclick="emailKhata(${p.id})">📧 ${t('send_email_btn')}</button></p>
   <h3>📎 ${t('attachments')}</h3>${attachHTML('parties', p.id)}<div id="att_zone"></div>
   <button class="small" onclick="savePartyAttach(${p.id})">${t('upload_l')}</button></div>
${canTrade ? `${accHead('party','trade','🔄',t('trade_l'),t('accd_trade'))}<div class="card">
   <p class="small muted">${t('ledger_note_l')}</p>
   <p><button class="ghost small" onclick="ogBillFor(${p.id})">🧾 ${t('add_bill_l')}</button></p>
   <p id="tf_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <div class="row"><div class="field"><label>&nbsp;</label><div class="seg"><button type="button" id="tf_m_buy" class="segbtn on" onclick="tradeModeUI('buy')">${t('add_buy_l')}</button><button type="button" id="tf_m_sell" class="segbtn" onclick="tradeModeUI('sell')">${t('add_sell_l')}</button></div></div>
   <div class="field"><label>${t('date')}</label><input id="tf_date" type="date" value="${todayStr()}"></div></div>
   <div class="field"><label>${t('choose_item_l')}</label><div class="seg">
     <button type="button" id="tf_it_rock" class="segbtn on" onclick="tradeItemUI('rock')">${t('item_rock_l')}</button>
     <button type="button" id="tf_it_powder" class="segbtn" onclick="tradeItemUI('powder')">${t('item_powder_l')}</button>
     <button type="button" id="tf_it_other" class="segbtn" onclick="tradeItemUI('other')">${t('item_other_l')}</button></div></div>
   <div class="row" id="tf_g_rock"><div class="field"><label>${t('weight_l')} (${unitLabel()}) *</label><input id="tf_tons_rock" type="number" step="0.001"></div>
   <div class="field" id="tf_grade_f"><label>${t('grade')}</label><input id="tf_grade" type="number" step="0.1"></div>
   <div class="field"><label>${t('rate_l')}</label><input id="tf_rate_rock" type="number"></div>
   <div class="field" id="tf_ded_f"><label>${t('ded_l')}</label><input id="tf_ded" type="number" step="0.1" value="0"></div></div>
   <div class="row" id="tf_g_powder" style="display:none"><div class="field"><label>${t('weight_l')} (${unitLabel()}) *</label><input id="tf_tons_powder" type="number" step="0.001"></div>
   <div class="field"><label>${t('bags')}</label><input id="tf_bags" type="number" value="0"></div>
   <div class="field"><label>${t('rate_l')}</label><input id="tf_rate_powder" type="number"></div></div>
   <div class="row" id="tf_g_other" style="display:none"><div class="field"><label>${t('item_name_l')} *</label><input id="tf_iname"></div>
   <div class="field"><label>${t('qty_l')} *</label><input id="tf_qty" type="number" step="0.01"></div>
   <div class="field"><label>${t('unit_l')}</label><input id="tf_unit" placeholder="bags / pieces / kg"></div>
   <div class="field"><label>${t('unit_rate_l')}</label><input id="tf_urate" type="number"></div></div>
   <div class="field"><label>${t('note')}</label><input id="tf_note"></div>
   <button id="tf_save" onclick="saveLedgerTrade()">${t('add_buy_l')}</button> <button id="tf_cancel" class="ghost" style="display:none" onclick="cancelLedgerEdit()">${t('cancel_l')}</button></div>${accEnd()}` : ''}
  ${accHead('party','ledger','📒',t('ledger'),t('accd_khata'),'ledger')}<div class="card"><div class="wrap"><table>
   <tr><th>${t('date')}</th><th>${t('description')}</th><th class="num">${t('debit')}</th><th class="num">${t('credit')}</th><th class="num">${t('balance')}</th></tr>
   ${d.entries.map(e => `<tr><td>${e.date}</td><td>${esc(e.desc)}</td><td class="num">${e.debit ? fmtN(e.debit) : ''}</td><td class="num">${e.credit ? fmtN(e.credit) : ''}</td><td class="num">${fmtN(e.balance)}${balTag(e.balance)}</td></tr>`).join('')}
  </table></div></div>${accEnd()}`;
  loadAttachments('parties', p.id);
  if (PENDING_LEDGER_EDIT && Number(PENDING_LEDGER_EDIT.row.party_id) === Number(VIEW_ARG)) {
    const pe = PENDING_LEDGER_EDIT; PENDING_LEDGER_EDIT = null;
    prefillLedgerTrade(pe.row, pe.mode);
  }
};
let TRADE_MODE = 'buy', TRADE_ITEM = 'rock', EDIT_TRADE = null;
let PENDING_LEDGER_EDIT = null;
window.tradeUI = () => {
  ['buy', 'sell'].forEach(k => { const b = document.getElementById('tf_m_' + k); if (b) b.classList.toggle('on', k === TRADE_MODE); });
  ['rock', 'powder', 'other'].forEach(k => { const b = document.getElementById('tf_it_' + k); if (b) b.classList.toggle('on', k === TRADE_ITEM); });
  const g = (id, on) => { const e = document.getElementById(id); if (e) e.style.display = on ? '' : 'none'; };
  g('tf_g_rock', TRADE_ITEM === 'rock'); g('tf_g_powder', TRADE_ITEM === 'powder'); g('tf_g_other', TRADE_ITEM === 'other');
  g('tf_grade_f', TRADE_MODE === 'buy'); g('tf_ded_f', TRADE_MODE === 'buy');
  const sv = document.getElementById('tf_save');
  if (sv && !EDIT_TRADE) sv.textContent = TRADE_MODE === 'buy' ? t('add_buy_l') : t('add_sell_l');
};
window.tradeModeUI = m => { TRADE_MODE = m; tradeUI(); };
window.tradeItemUI = it => { TRADE_ITEM = it; tradeUI(); };
window.saveLedgerTrade = async () => {
  let body;
  if (TRADE_ITEM === 'other') body = { date: val('tf_date'), party_id: VIEW_ARG, item: 'other', item_name: val('tf_iname'),
    qty: num('tf_qty'), unit: val('tf_unit'), unit_rate: num('tf_urate'), note: val('tf_note') };
  else if (TRADE_ITEM === 'powder') body = { date: val('tf_date'), party_id: VIEW_ARG, item: 'powder',
    tons: toTonsVal(num('tf_tons_powder')), bags: parseInt(val('tf_bags')) || 0, rate_per_ton: num('tf_rate_powder'), note: val('tf_note') };
  else body = { date: val('tf_date'), party_id: VIEW_ARG, item: 'rock', tons: toTonsVal(num('tf_tons_rock')),
    grade_pct: num('tf_grade'), rate_per_ton: num('tf_rate_rock'), deduction_pct: TRADE_MODE === 'buy' ? num('tf_ded') : 0, note: val('tf_note') };
  if (EDIT_TRADE) body.id = EDIT_TRADE.id;
  try { const r = TRADE_MODE === 'buy' ? await post('/api/purchases', body) : await postSaleSave(body);
    if (!r) return;   // duplicate-sale warning declined — nothing was saved
    EDIT_TRADE = null; okPopup(t('saved_l')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.updatePurchase = () => saveLedgerTrade();
window.updateSale = () => saveLedgerTrade();
window.cancelLedgerEdit = () => { EDIT_TRADE = null; render(); };
window.cancelPurchaseEdit = () => cancelLedgerEdit();
window.cancelSaleEdit = () => cancelLedgerEdit();
window.editPurchase = async id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  let row = (PUR_CACHE || []).find(x => x.id === id);
  if (!row) { PUR_CACHE = await get('/api/purchases'); row = PUR_CACHE.find(x => x.id === id); }
  if (!row) return;
  PENDING_LEDGER_EDIT = { mode: 'buy', row };
  openParty(row.party_id);
};
window.editSale = async id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  let row = (SALE_CACHE || []).find(x => x.id === id);
  if (!row) { SALE_CACHE = await get('/api/sales'); row = SALE_CACHE.find(x => x.id === id); }
  if (!row) return;
  PENDING_LEDGER_EDIT = { mode: 'sell', row };
  openParty(row.party_id);
};
function prefillLedgerTrade(row, mode) {
  TRADE_MODE = mode; TRADE_ITEM = row.item || (mode === 'buy' ? 'rock' : 'powder');
  EDIT_TRADE = { id: row.id, mode };
  $('#tf_date').value = row.date || todayStr();
  $('#tf_note').value = row.note || '';
  if (TRADE_ITEM === 'other') { $('#tf_iname').value = row.item_name || ''; $('#tf_qty').value = row.qty || ''; $('#tf_unit').value = row.unit || ''; $('#tf_urate').value = row.unit_rate || ''; }
  else if (TRADE_ITEM === 'powder') { $('#tf_tons_powder').value = fromKgVal((row.tons || 0) * 1000); $('#tf_bags').value = row.bags || ''; $('#tf_rate_powder').value = row.rate_per_ton || ''; }
  else { $('#tf_tons_rock').value = fromKgVal((row.tons || 0) * 1000); $('#tf_grade').value = row.grade_pct || ''; $('#tf_rate_rock').value = row.rate_per_ton || ''; $('#tf_ded').value = row.deduction_pct || 0; }
  tradeUI();
  editSwap('tf_save', mode === 'buy' ? 'updatePurchase()' : 'updateSale()', 'tf_cancel', 'tf_editing');
  accOpen('party', 'trade');   // the edit form lives in the Trade section
}
window.waKhata = async pid => {
  try {
    const r = await get('/api/wa-statement/' + pid + '?lang=' + PREFS.lang + '&u=' + PREFS.unit);
    const phone = String(r.phone || '').replace(/\D/g, '');
    if (!phone) { msg(t('wa_no_phone'), 'warn'); return; }
    const num2 = phone.replace(/^0/, '92');
    window.open('https://wa.me/' + num2 + '?text=' + encodeURIComponent(r.text), '_blank');
  } catch (e) { msg(e.message, 'err'); }
};
window.emailKhata = async pid => {
  try {
    await post('/api/email/statement', { party_id: pid, lang: PREFS.lang, unit: PREFS.unit });
    okPopup(t('email_sent_ok'));
  } catch (e) { msg(e.message, 'err'); }
};
window.emailInvoice = async sid => {
  try {
    await post('/api/email/invoice', { sale_id: sid });
    okPopup(t('email_sent_ok'));
  } catch (e) { msg(e.message, 'err'); }
};
window.savePartyAttach = async pid => { const id = await uploadAttachment('parties', pid); if (id) { okPopup(t('saved')); loadAttachments('parties', pid); } else msg(t('choose_file'), 'warn'); };

/* Vehicle In and Vehicle Out are two SEPARATE pages (owner's order,
   27 Oct 2026): the old combined IN/OUT form confused him. Each page
   carries only its own direction's fields and submits only its own
   direction; the server endpoint stays shared. The old 'vehicles'
   view at the bottom redirects to Vehicle In so no stale link strands. */
let RATE_TYPE = 'factory';
let RENT_TO = 'seller';        // Mine-rate rent receiver: seller (khata) | driver (mill cash)
let BUYFROM_MANUAL = false;    // Buy-from picker follows the trip party until picked by hand
let EDIT_TRIP = null;          // trip id in edit mode (owner-only); null = new entry
let PENDING_TRIP_EDIT = null;  // set by the Own trade history: open this trip's edit on arrival
let TRIP_CACHE = [];           // last fetched trips — the edit prefill source
/* owner-edit state for the remaining entry forms (same pattern as trips:
   the Edit button lives in each list, prefill comes from the cached rows,
   Save swaps to an update call; the server enforces owner-only) */
let EDIT_PAY = null, PAY_CACHE = [];
let EDIT_EX = null, EX_CACHE = [];
let EDIT_PUR = null, PUR_CACHE = [];
let EDIT_SALE = null, SALE_CACHE = [];
let EDIT_W = null;
let EDIT_PO = null, PO_CACHE = [];
let EDIT_PARTY = null;
let EDIT_DEPT = null;
let EDIT_MC = null, MC_CACHE = [];
let EDIT_ME = null, ME_CACHE = [];
let EDIT_SC = null, SC_CACHE = [];
let EDIT_BAG = null;           // {tbl:'bag_movements'|'client_bags', id}
let BAG_CACHE = [];            // merged bags list rows (edit prefill source)
function editSwap(saveId, fn, cancelId, bannerId) {
  const sb = document.getElementById(saveId);
  if (sb) { sb.textContent = t('save_changes'); sb.setAttribute('onclick', fn); }
  const cb = document.getElementById(cancelId); if (cb) cb.style.display = '';
  const eb = document.getElementById(bannerId); if (eb) eb.style.display = '';
  window.scrollTo(0, 0);
}
const tripTopHTML = ctx => `
   <div class="row"><div class="field"><label>${t('date')}</label><input id="tr_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('party')}</label><select id="tr_party" onchange="tripPartyChanged()"><option value="">${t('own_opt')}</option>${partyOpts(null, ctx)}</select></div></div>
   <div class="row"><div class="field"><label>${t('vehicle')} *</label><input id="tr_vehicle" placeholder="LEA-1234"></div>
   <div class="field"><label>${t('driver')}</label><input id="tr_driver"></div>
   <div class="field"><label>${t('driver_phone_l')}</label><input id="tr_dphone" type="tel" placeholder="03xx-xxxxxxx"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button class="ghost small" onclick="repeatTrip()">↻ ${t('repeat_trip')}</button></div></div>`;
const tripListHTML = (trips, dir) => `<div class="card">${xlBar('trips')}<div class="wrap"><table><tr><th>${t('date')}</th><th>${t('party')}</th><th>${t('vehicle')}</th><th>${t('net')}</th>${dir === 'OUT' ? `<th>${t('bags')}</th>` : ''}<th>${t('grade')}</th><th></th></tr>
   ${trips.filter(x => x.direction === dir).slice(0, 60).map(x => `<tr><td>${x.date}</td><td>${esc(x.party_name)}${x.buy_from_party_id && x.buy_from_party_id !== x.party_id ? `<br><span class="muted small">${t('bought_from_l')}: ${esc(x.buy_from_name || '')}</span>` : ''}${dir === 'OUT' && x.own_sale_buyer_id ? `<br><span class="muted small">${t('sold_to_l')}: ${esc(x.own_sale_buyer_name || '')} @ Rs ${x.own_sale_rate}/t</span>` : ''}</td><td>${esc(x.vehicle_no)}</td><td>${kgDisp(x.net_kg)}</td>${dir === 'OUT' ? `<td>${x.bags}</td>` : ''}<td>${x.grade_pct || ''}</td>
   <td><a target="_blank" href="/print/trip/${x.id}?u=${PREFS.unit}&lang=${PREFS.lang}">🖨</a> ${isOwner() ? `<button class="small ghost" onclick="editTrip(${x.id},'${dir}')">${t('edit')}</button>` : ''} ${delBtn('trips', x.id)}</td></tr>`).join('')}</table></div></div>`;

VIEWS.vehicle_in = async el => {
  await loadBase();
  const trips = await get('/api/trips');
  TRIP_CACHE = trips; EDIT_TRIP = null;
  RATE_TYPE = 'factory';   // a fresh Vehicle In form starts on Factory ponch rate
  RENT_TO = 'seller'; BUYFROM_MANUAL = false;
  el.innerHTML = `<div class="card"><h2>🚛 ${t('vehicle_in')} <button class="small voicebtn" onclick="voiceFill('trip')">${t('voice')}</button></h2>
   <p class="small muted">${t('voice_hint')}</p>
   <p id="tr_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   ${tripTopHTML('vehicle_in')}
   <div class="row"><div class="field"><label>${t('net')} (${unitLabel()}) *</label><input id="tr_net" type="number"></div>
   <div class="field"><label>${t('grade')}</label><input id="tr_grade" type="number" step="0.1"></div></div>
   <div id="tr_purchase_block">
   <h3>🪨 ${t('rock_purchase_l')}</h3>
   <div class="row"><div class="field"><label>${t('rock_rate_l')}</label><input id="tr_rock_rate" type="number"></div>
   <div class="field"><label>${t('rate_type_l')}</label><div class="seg"><button type="button" id="rt_factory" class="segbtn on" onclick="rateTypeUI('factory')">${t('factory_rate_l')}</button><button type="button" id="rt_mine" class="segbtn" onclick="rateTypeUI('mine')">${t('mine_rate_l')}</button></div></div>
   <div class="field" id="tr_rent_f" style="display:none"><label>${t('rent_l')}</label><input id="tr_rent" type="number"></div></div>
   <div class="row"><div class="field"><label>${t('buy_from_l')}</label><select id="tr_buyfrom" onchange="buyFromPicked()"><option value="">${t('own_opt')}</option>${partyOpts(null, 'vehicle_in')}</select></div>
   <div class="field" id="tr_rentto_f" style="display:none"><label>${t('rent_to_l')}</label><div class="seg"><button type="button" id="rt_rseller" class="segbtn on" onclick="rentToUI('seller')">${t('rent_seller_l')}</button><button type="button" id="rt_rdriver" class="segbtn" onclick="rentToUI('driver')">${t('rent_driver_l')}</button></div></div></div>
   <div class="row"><div class="field" id="tr_freight_f" style="display:none"><label>${t('freight')} (Rs)</label><input id="tr_freight" type="number" value="0"></div>
   <div class="field" id="tr_fpayer_f" style="display:none"><label>${t('freight_payer')}</label><select id="tr_fpayer"><option value="mill">Mill</option><option value="party">${t('party')}</option></select></div></div>
   </div>
   <div class="field"><label>${t('note')}</label><input id="tr_note"></div>
   <button id="tr_save" onclick="addTrip('IN')">${t('save')}</button> <button id="tr_cancel" class="ghost" style="display:none" onclick="cancelTripEdit()">${t('cancel_l')}</button></div>
  ${tripListHTML(trips, 'IN')}`;
  purchaseUI();
  if (PENDING_TRIP_EDIT && PENDING_TRIP_EDIT.dir === 'IN') { const pe = PENDING_TRIP_EDIT; PENDING_TRIP_EDIT = null; editTrip(pe.id, 'IN'); }
};

VIEWS.vehicle_out = async el => {
  await loadBase();
  const trips = await get('/api/trips');
  TRIP_CACHE = trips; EDIT_TRIP = null;
  el.innerHTML = `<div class="card"><h2>🚚 ${t('vehicle_out')} <button class="small voicebtn" onclick="voiceFill('trip')">${t('voice')}</button></h2>
   <p class="small muted">${t('voice_hint')}</p>
   <p id="tr_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   ${tripTopHTML('vehicle_out')}
   <div class="row"><div class="field"><label>${t('net')} (${unitLabel()}) *</label><input id="tr_net" type="number" oninput="grindChargeCalc()"></div>
   <div class="field"><label>${t('bags')}</label><input id="tr_bags" type="number" value="0"></div>
   <div class="field"><label>${t('grade')}</label><input id="tr_grade" type="number" step="0.1"></div></div>
   <p id="tr_stock_hint" class="small muted" style="display:none;margin:2px 0 0"></p>
   <div class="row" id="tr_sold_row" style="display:none"><div class="field"><label>${t('sold_to_l')}</label><select id="tr_sold_to"><option value="">—</option>${partyOpts(null, 'sale')}</select></div>
   <div class="field"><label>${t('sale_rate_l')}</label><input id="tr_sold_rate" type="number"></div></div>
   <p id="tr_sold_hint" class="small muted" style="display:none;margin:2px 0 0">${t('sale_hint_l')}</p>
   <div class="row" id="tr_grind_row"><div class="field"><label>${t('grind_rate_l')}</label><input id="tr_grind_rate" type="number" oninput="grindChargeCalc()"></div>
   <div class="field"><label>${t('grind_charge_l')}</label><div id="tr_grind_charge" class="small muted" style="padding-top:8px">—</div></div></div>
   <div class="row"><div class="field"><label>${t('freight')} (Rs)</label><input id="tr_freight" type="number" value="0"></div>
   <div class="field"><label>${t('freight_payer')}</label><select id="tr_fpayer"><option value="mill">Mill</option><option value="party">${t('party')}</option></select></div>
   <div class="field"><label>${t('loading')} (Rs)</label><input id="tr_loading" type="number" value="0"></div>
   <div class="field"><label>${t('load_payer')}</label><select id="tr_bearer"><option value="party">${t('party')}</option><option value="mill">Mill</option></select></div>
</div>
   <div class="field"><label>${t('note')}</label><input id="tr_note"></div>
   <button id="tr_save" onclick="addTrip('OUT')">${t('save')}</button> <button id="tr_cancel" class="ghost" style="display:none" onclick="cancelTripEdit()">${t('cancel_l')}</button></div>
  ${tripListHTML(trips, 'OUT')}`;
  stockHint();
  tripOwnUI();
  if (PENDING_TRIP_EDIT && PENDING_TRIP_EDIT.dir === 'OUT') { const pe = PENDING_TRIP_EDIT; PENDING_TRIP_EDIT = null; editTrip(pe.id, 'OUT'); }
};

/* legacy route: the old combined Vehicles page now lands on Vehicle In */
VIEWS.vehicles = async el => { VIEW = 'vehicle_in'; render(); };

window.freightUI = () => {
  // Vehicle In page only: freight belongs to a Mine-rate purchase (the
  // mill pays the vehicle separately). A Factory ponch rate is the
  // delivered rate, so in Factory mode the freight fields stay hidden
  // and are never required.
  const on = RATE_TYPE === 'mine';
  const show = (id, x) => { const e = document.getElementById(id); if (e) e.style.display = x ? '' : 'none'; };
  show('tr_freight_f', on); show('tr_fpayer_f', on);
};
window.rateTypeUI = rt => {
  RATE_TYPE = rt;
  const f = $('#rt_factory'), m = $('#rt_mine'), rf = $('#tr_rent_f'), rtf = $('#tr_rentto_f');
  if (f) f.classList.toggle('on', rt === 'factory');
  if (m) m.classList.toggle('on', rt === 'mine');
  if (rf) rf.style.display = rt === 'mine' ? '' : 'none';
  if (rtf) rtf.style.display = rt === 'mine' ? '' : 'none';
  freightUI();
};
window.rentToUI = x => {
  RENT_TO = x;
  const s = $('#rt_rseller'), d = $('#rt_rdriver');
  if (s) s.classList.toggle('on', x === 'seller');
  if (d) d.classList.toggle('on', x === 'driver');
};
// Buy-from (27 Oct): the seller picker follows the trip party until
// the user picks a seller by hand; after that it stays put. The
// Vehicle Out page has no picker — the handler no-ops there.
window.tripPartyChanged = () => {
  const bf = document.getElementById('tr_buyfrom');
  if (bf && !BUYFROM_MANUAL) bf.value = val('tr_party');
  stockHint();
  tripOwnUI();
  purchaseUI();
};
/* Rock-purchase block visibility (owner, 28 Oct 2026): the whole
   purchase block on the Vehicle In page — rock rate, the Factory /
   Mine rate-type toggle, Buy from seller, Mine-rate rent + rent-to
   and freight — exists ONLY when the Party is Own (Mine): a gate purchase is always the mill
   buying for itself. A client party brings its own rock FOR
   GRINDING, so picking any client party hides the block AND clears
   its values: nothing stale can ride into the save (the submit
   handler reads these same inputs), and the server zeroes the
   fields for client-party IN trips regardless. The Vehicle Out
   page has no purchase block — the handler no-ops there. */
window.purchaseUI = () => {
  const blk = document.getElementById('tr_purchase_block'); if (!blk) return;   // Vehicle In only
  const own = !val('tr_party');
  blk.style.display = own ? '' : 'none';
  if (!own) {
    const rr = document.getElementById('tr_rock_rate'); if (rr) rr.value = '';
    const rt = document.getElementById('tr_rent'); if (rt) rt.value = '';
    const bf = document.getElementById('tr_buyfrom'); if (bf) bf.value = '';
    BUYFROM_MANUAL = false;
  }
};
/* Own-dispatch sale + grinding visibility (owner, 28 Oct 2026):
   Party = Own (Mine) on Vehicle Out shows the OPTIONAL sale fields
   (Powder sold to + Sale rate) and HIDES the Grinding rate — our own
   material is never charged grinding. Picking any party brings the
   Grinding rate back and hides + clears the sale fields, so a sale
   can never ride on a party trip. The server enforces both rules
   too (fields dropped / charge zeroed for the wrong party kind). */
window.tripOwnUI = () => {
  const row = document.getElementById('tr_sold_row'); if (!row) return;   // Vehicle Out only
  const own = !val('tr_party');
  row.style.display = own ? '' : 'none';
  const hint = document.getElementById('tr_sold_hint'); if (hint) hint.style.display = own ? '' : 'none';
  const gr = document.getElementById('tr_grind_row'); if (gr) gr.style.display = own ? 'none' : '';
  if (own) {
    const gi = document.getElementById('tr_grind_rate'); if (gi) gi.value = '';
    const gc = document.getElementById('tr_grind_charge'); if (gc) gc.textContent = '—';
  } else {
    const b = document.getElementById('tr_sold_to'); if (b) b.value = '';
    const r = document.getElementById('tr_sold_rate'); if (r) r.value = '';
  }
};
/* Powder-stock hint (Talha, 28 Oct 2026): on the Vehicle Out page,
   show the ground powder lying in the pool this dispatch will
   deduct from — the selected party's own powder, or the mill's Own
   stock when no party is picked — fetched from /api/trip-stock,
   which returns the same derivation the save-time gate checks.
   A gate-pass party (fx none) returns no figure and the hint hides.
   While editing, the trip's own previous net is added back
   server-side, matching the save check exactly. */
window.stockHint = async () => {
  const hint = document.getElementById('tr_stock_hint'); if (!hint) return;
  try {
    const r = await get('/api/trip-stock?party_id=' + encodeURIComponent(val('tr_party') || '')
      + (EDIT_TRIP ? '&exclude_trip=' + EDIT_TRIP : ''));
    if (!document.getElementById('tr_stock_hint')) return;
    if (r.available_t == null) { hint.style.display = 'none'; hint.textContent = ''; return; }
    hint.textContent = '📦 ' + t('stock_avail_l') + ': ' + tonsDisp(r.available_t);
    hint.style.display = '';
  } catch (e) { hint.style.display = 'none'; }
};
/* Powder-stock confirm (28 Oct 2026): when the server refuses an
   over-stock dispatch (HTTP 409, confirm_required), ask first —
   only a re-save carrying confirm_stock:true goes through, and the
   server writes that override into the audit history. Declining
   saves nothing. Same branded overlay family as the delete
   confirm, with its own promise plumbing. */
let _stockResolve = null;
window.stockConfirmAnswer = yes => {
  const ov = document.getElementById('stockpop'); if (ov) ov.style.display = 'none';
  if (_stockResolve) { const f = _stockResolve; _stockResolve = null; f(yes); }
};
const stockConfirmAsk = (availT, netT) => new Promise(res => {
  _stockResolve = res;
  let ov = document.getElementById('stockpop');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'stockpop'; ov.className = 'delpop';
    ov.innerHTML = '<div class="delcard"><div class="delicon">⚠️</div>'
      + '<div class="deltitle"></div><div class="deldesc"></div>'
      + '<div class="delrow"><button type="button" class="stockyes"></button>'
      + '<button type="button" class="ghost stockno"></button></div></div>';
    ov.querySelector('.stockyes').addEventListener('click', () => stockConfirmAnswer(true));
    ov.querySelector('.stockno').addEventListener('click', () => stockConfirmAnswer(false));
    ov.addEventListener('click', e => { if (e.target === ov) stockConfirmAnswer(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') stockConfirmAnswer(false); });
    document.body.appendChild(ov);
  }
  ov.querySelector('.deltitle').textContent = t('stock_warn_t');
  ov.querySelector('.deldesc').textContent = t('stock_warn_msg')
    .replace('{avail}', tonsDisp(availT)).replace('{net}', tonsDisp(netT));
  ov.querySelector('.stockyes').textContent = t('stock_anyway_l');
  ov.querySelector('.stockno').textContent = t('cancel_l');
  ov.style.display = 'flex';
});
/* Duplicate-sale confirm (28 Oct 2026): the mirror warning — a
   Ledger Sell that repeats an Own trip's recorded sale, or an Own
   trip sale that repeats a Ledger Sell, is refused (HTTP 409,
   confirm_required) until the user confirms it is a SEPARATE sale.
   Same overlay family + promise plumbing as the stock warning. */
let _dupResolve = null;
window.dupConfirmAnswer = yes => {
  const ov = document.getElementById('duppop'); if (ov) ov.style.display = 'none';
  if (_dupResolve) { const f = _dupResolve; _dupResolve = null; f(yes); }
};
const dupConfirmAsk = d => new Promise(res => {
  _dupResolve = res;
  let ov = document.getElementById('duppop');
  if (!ov) {
    ov = document.createElement('div');
    ov.id = 'duppop'; ov.className = 'delpop';
    ov.innerHTML = '<div class="delcard"><div class="delicon">⚠️</div>'
      + '<div class="deltitle"></div><div class="deldesc"></div>'
      + '<div class="delrow"><button type="button" class="dupyes"></button>'
      + '<button type="button" class="ghost dupno"></button></div></div>';
    ov.querySelector('.dupyes').addEventListener('click', () => dupConfirmAnswer(true));
    ov.querySelector('.dupno').addEventListener('click', () => dupConfirmAnswer(false));
    ov.addEventListener('click', e => { if (e.target === ov) dupConfirmAnswer(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') dupConfirmAnswer(false); });
    document.body.appendChild(ov);
  }
  ov.querySelector('.deltitle').textContent = t('dup_warn_t');
  const tpl = d.match_kind === 'trip' ? t('dup_trip_l') : t('dup_sell_l');
  ov.querySelector('.deldesc').textContent = tpl
    .replace('{buyer}', d.buyer_name || '').replace('{date}', d.date || '')
    .replace('{vehicle}', d.vehicle || '-').replace('{tons}', tonsDisp(d.tons || 0))
    .replace('{rate}', String(d.rate || 0));
  ov.querySelector('.dupyes').textContent = t('dup_anyway_l');
  ov.querySelector('.dupno').textContent = t('cancel_l');
  ov.style.display = 'flex';
});
/* Trip save wrapper: a plain save, unless a server guard answers
   confirm-required — the powder-stock gate first (the server checks
   it first too), then the duplicate-sale guard; each confirmed flag
   sticks on the body, so the two warnings can compose in sequence. */
const postTripSave = async body => {
  try { return await post('/api/trips', body); }
  catch (e) {
    if (!e.data || !e.data.confirm_required) throw e;
    if (e.data.reason === 'duplicate_sale') {
      const yes2 = await dupConfirmAsk(e.data);
      if (!yes2) return null;
      body.confirm_duplicate = true;
      return await postTripSave(body);
    }
    const yes = await stockConfirmAsk(e.data.available_t, e.data.net_t);
    if (!yes) return null;
    body.confirm_stock = true;
    return await postTripSave(body);
  }
};
/* Ledger sale save wrapper: only the duplicate-sale guard can answer
   confirm-required on /api/sales. */
const postSaleSave = async body => {
  try { return await post('/api/sales', body); }
  catch (e) {
    if (!e.data || !e.data.confirm_required || e.data.reason !== 'duplicate_sale') throw e;
    const yes = await dupConfirmAsk(e.data);
    if (!yes) return null;
    body.confirm_duplicate = true;
    return await post('/api/sales', body);
  }
};
window.buyFromPicked = () => { BUYFROM_MANUAL = true; };
window.grindChargeCalc = () => {
  const el2 = document.getElementById('tr_grind_charge'); if (!el2) return;
  const tons = toTonsVal(num('tr_net')), rate = num('tr_grind_rate');
  el2.textContent = rate > 0 ? (tonsDisp(tons) + ' × Rs ' + rate + ' = ' + fmt(tons * rate)) : '—';
};
window.repeatTrip = async () => {
  const v = val('tr_vehicle'); if (!v) { msg(t('vehicle_first'), 'warn'); return; }
  const r = await get('/api/last-trip?vehicle=' + encodeURIComponent(v));
  if (!r.id) { msg(t('no_old_trip'), 'warn'); return; }
  $('#tr_party').value = r.party_id || ''; $('#tr_driver').value = r.driver || '';
  const dp = document.getElementById('tr_dphone'); if (dp) dp.value = r.driver_phone || '';
  $('#tr_net').value = r.net_kg ? fromKgVal(r.net_kg) : ''; msg(t('filled_old') + ' ✓');
  tripPartyChanged();   // a fresh prefill: the Buy-from picker follows the party
};
window.addTrip = async dir => {
  try {
    if (!reqCheck([['tr_vehicle', 'fl_vehicle', 'text'], ['tr_net', 'fl_net', 'pos']])) return;
    const body = { date: val('tr_date'), direction: dir, party_id: val('tr_party') || null,
      vehicle_no: val('tr_vehicle'), driver: val('tr_driver'), driver_phone: val('tr_dphone'),
      net_kg: toKgVal(num('tr_net')), bags: parseInt(val('tr_bags')) || 0, grade_pct: num('tr_grade'),
      note: val('tr_note') };
    if (dir === 'IN') {
      // a Vehicle In submits ONLY IN fields: the rock purchase (rate,
      // rate type, rent) and — Mine rate only — freight. No loading,
      // no order link, no grinding charge exist on this page.
      body.rock_rate = num('tr_rock_rate'); body.rate_type = RATE_TYPE;
      body.rent = RATE_TYPE === 'mine' ? num('tr_rent') : 0;
      body.rent_to = RENT_TO;
      body.buy_from_party_id = val('tr_buyfrom') || null;
      body.freight = RATE_TYPE === 'mine' ? num('tr_freight') : 0;
      body.freight_payer = val('tr_fpayer');
      body.loading = 0; body.order_id = null;
    } else {
      // a Vehicle Out submits ONLY OUT fields: grinding rate, freight,
      // loading and the order link. No purchase fields exist here.
      body.grind_rate = num('tr_grind_rate');
      body.freight = num('tr_freight'); body.freight_payer = val('tr_fpayer');
      body.loading = num('tr_loading'); body.charge_bearer = val('tr_bearer');
      body.order_id = null;
      // Own dispatch only: the optional sale (buyer + rate) rides on
      // the trip itself; the server validates the pair and drops it
      // for any party trip.
      if (!body.party_id) {
        body.sale_buyer_id = val('tr_sold_to') ? Number(val('tr_sold_to')) : null;
        body.sale_rate = num('tr_sold_rate');
      }
    }
    const r = await postTripSave(body);
    if (!r) return;   // a guard warning was declined — nothing was saved
    const aid = await uploadAttachment('trips', r.id);
    tripSavedModal(r, aid);
  } catch (e) { msg(e.message, 'err'); }
};
// Voucher popup after a trip save (create OR owner edit): Print always;
// WhatsApp either auto-sent (the server says so only when the alerts
// really went out) or one-tap wa.me buttons for whichever of
// party / driver / owner has a number.
const tripSavedModal = (r, aid) => {
  const waBtn = (url, label) => url ? `<a target="_blank" href="${url}"><button type="button">💬 ${label}</button></a>` : '';
  const waHtml = r.wa_auto
    ? `<p class="small" style="margin-top:8px">✅ ${t('wa_auto_sent')}</p>`
    : `<div class="row" style="margin-top:8px">${waBtn(r.wa_party_url, t('wa_party_btn'))}${waBtn(r.wa_driver_url, t('wa_driver_btn'))}${waBtn(r.wa_owner_url, t('wa_owner_btn'))}</div>`;
  showModal(`<h2>✅ ${t('trip_saved')} ${kgDisp(r.net_kg)}${aid ? ' · ' + t('photo_attached') : ''}</h2>
   ${r.warning ? `<p class="msg warn">${esc(r.warning)}</p>` : ''}
   <div class="row" style="margin-top:8px"><a target="_blank" href="/print/trip/${r.id}?u=${PREFS.unit}&lang=${PREFS.lang}"><button type="button">🖨 ${t('print_voucher_l')}</button></a></div>
   ${waHtml}
   <div style="margin-top:12px"><button onclick="closeModal();render()">OK</button></div>`);
};
/* Owner-only trip EDIT (27 Oct): the same direction form, prefilled.
   Saving reposts the trip server-side in one transaction — the khata
   and stock end up exactly as if the corrected trip were entered once. */
window.editTrip = (id, dir) => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = TRIP_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_TRIP = id;
  $('#tr_date').value = r.date || todayStr();
  $('#tr_party').value = r.party_id || '';
  $('#tr_vehicle').value = r.vehicle_no || '';
  $('#tr_driver').value = r.driver || '';
  const dp = document.getElementById('tr_dphone'); if (dp) dp.value = r.driver_phone || '';
  $('#tr_net').value = r.net_kg ? fromKgVal(r.net_kg) : '';
  const _tb = document.getElementById('tr_bags'); if (_tb) _tb.value = r.bags || 0;   // OUT page only — the Vehicle In form has no Bags field (rock arrives by weight)
  $('#tr_grade').value = r.grade_pct || '';
  $('#tr_note').value = r.note || '';
  if (dir === 'IN') {
    $('#tr_rock_rate').value = r.rock_rate || '';
    rateTypeUI(r.rate_type === 'mine' ? 'mine' : 'factory');
    $('#tr_rent').value = r.rent || '';
    rentToUI(r.rent_to === 'driver' ? 'driver' : 'seller');
    const fr = document.getElementById('tr_freight'); if (fr) fr.value = r.freight || 0;
    const fp = document.getElementById('tr_fpayer'); if (fp) fp.value = r.freight_payer || 'mill';
    const bf = document.getElementById('tr_buyfrom');
    if (bf) { bf.value = r.buy_from_party_id || r.party_id || ''; BUYFROM_MANUAL = !!r.buy_from_party_id; }
    purchaseUI();   // Own: block shows with the prefilled values; client party: block hides + clears (server zeroes on save too)
  } else {
    $('#tr_grind_rate').value = r.grind_rate || '';
    grindChargeCalc();
    $('#tr_freight').value = r.freight || 0;
    $('#tr_fpayer').value = r.freight_payer || 'mill';
    $('#tr_loading').value = r.loading || 0;
    $('#tr_bearer').value = r.charge_bearer || 'party';
    const _sb = document.getElementById('tr_sold_to'); if (_sb) _sb.value = r.own_sale_buyer_id || '';
    const _sr = document.getElementById('tr_sold_rate'); if (_sr) _sr.value = r.own_sale_rate || '';
    tripOwnUI();   // Own: sale fields show (values kept), grind hides; party: sale clears, grind shows
  }
  if (dir === 'OUT') stockHint();
  const sb = document.getElementById('tr_save');
  if (sb) { sb.textContent = t('save_changes'); sb.setAttribute('onclick', `updateTrip('${dir}')`); }
  const cb = document.getElementById('tr_cancel'); if (cb) cb.style.display = '';
  const eb = document.getElementById('tr_editing'); if (eb) eb.style.display = '';
  window.scrollTo(0, 0);
};
window.updateTrip = async dir => {
  try {
    if (!EDIT_TRIP) return;
    if (!reqCheck([['tr_vehicle', 'fl_vehicle', 'text'], ['tr_net', 'fl_net', 'pos']])) return;
    const body = { id: EDIT_TRIP, date: val('tr_date'), direction: dir, party_id: val('tr_party') || null,
      vehicle_no: val('tr_vehicle'), driver: val('tr_driver'), driver_phone: val('tr_dphone'),
      net_kg: toKgVal(num('tr_net')), bags: parseInt(val('tr_bags')) || 0, grade_pct: num('tr_grade'),
      note: val('tr_note') };
    if (dir === 'IN') {
      body.rock_rate = num('tr_rock_rate'); body.rate_type = RATE_TYPE;
      body.rent = RATE_TYPE === 'mine' ? num('tr_rent') : 0;
      body.rent_to = RENT_TO;
      body.buy_from_party_id = val('tr_buyfrom') || null;
      body.freight = RATE_TYPE === 'mine' ? num('tr_freight') : 0;
      body.freight_payer = val('tr_fpayer');
      body.loading = 0; body.order_id = null;
    } else {
      body.grind_rate = num('tr_grind_rate');
      body.freight = num('tr_freight'); body.freight_payer = val('tr_fpayer');
      body.loading = num('tr_loading'); body.charge_bearer = val('tr_bearer');
      body.order_id = null;
      if (!body.party_id) {
        body.sale_buyer_id = val('tr_sold_to') ? Number(val('tr_sold_to')) : null;
        body.sale_rate = num('tr_sold_rate');
      } else {
        // party trip: the sale fields clear explicitly, so an edit
        // that moves a trip from Own to a party drops its sale
        body.sale_buyer_id = null; body.sale_rate = 0;
      }
    }
    const r = await postTripSave(body);
    if (!r) return;   // declined: stay in edit mode so the entry can be fixed
    EDIT_TRIP = null;
    tripSavedModal(r, null);
  } catch (e) { msg(e.message, 'err'); }
};
window.cancelTripEdit = () => { EDIT_TRIP = null; render(); };

let JOB_SHIFT = 'Day';
let EDIT_JOB = null;   // {kind:'job'|'prod', id, filter_kg} in edit mode (owner-only)
let GP_UNION = [];     // the merged list rows — the edit prefill source
window.jobShiftUI = s => {
  JOB_SHIFT = s;
  const d = $('#js_day'), n = $('#js_night');
  if (d) d.classList.toggle('on', s === 'Day');
  if (n) n.classList.toggle('on', s === 'Night');
};

VIEWS.grindprod = async el => {
  await loadBase();
  JOB_SHIFT = 'Day';   // a fresh entry form always opens on the Day shift
  const jobs = await get('/api/jobs');
  const prods = await get('/api/production').catch(() => []);
  const sessions = await get('/api/grind-sessions');
  const closures = await get('/api/shift-closures').catch(() => []);
  const running = sessions.filter(x => !x.ended);
  // union list: every job (with its linked production row's bags/times)
  // plus production rows that stand alone (older separate entries)
  const linked = {};
  prods.forEach(r => { if (r.job_id) linked[r.job_id] = r; });
  const union = [];
  jobs.forEach(j => { const p = linked[j.id];
    union.push({ kind: 'job', id: j.id, date: j.date, party_name: j.party_name, party_id: j.party_id,
      tons: j.tons, grade_pct: j.grade_pct, shift: j.shift,
      bags: p ? p.bags : (j.bags || 0),
      filter_bags: p ? (p.filter_bags || 0) : 0, filter_kg: p ? (p.filter_kg || 0) : 0,
      start_time: p ? p.start_time : '', end_time: p ? p.end_time : '',
      bag_source: p ? p.bag_source : '', entered_by: p ? p.entered_by : '',
      rate_per_ton: j.rate_per_ton, amount: j.amount, note: j.note }); });
  prods.forEach(r => { if (!r.job_id || !jobs.some(j => j.id === r.job_id))
    union.push({ kind: 'prod', id: r.id, date: r.date, party_name: r.party_name, party_id: r.party_id,
      tons: null, grade_pct: '', shift: '', bags: r.bags,
      filter_bags: r.filter_bags || 0, filter_kg: r.filter_kg || 0,
      start_time: r.start_time, end_time: r.end_time,
      bag_source: r.bag_source, entered_by: r.entered_by,
      rate_per_ton: 0, amount: 0, note: r.note }); });
  union.sort((a, b) => (b.date || '').localeCompare(a.date || '') || b.id - a.id);
  GP_UNION = union; EDIT_JOB = null;
  el.innerHTML = `${accHead('grindprod','session','⚙',t('now_grinding'),t('accd_session'))}<div class="card">
   ${running.length ? running.map(g => `<div class="kv"><span>${esc(g.party_id ? (CACHE.parties.find(p => p.id === g.party_id) || {}).name || '' : t('own_word'))} · ${esc(g.started)}</span><button class="small" onclick="stopGrind(${g.id})">${t('stop_l')}</button></div>`).join('') : `<span class="muted">${t('no_session')}</span>`}
   <div class="row" style="margin-top:8px"><div class="field"><label>${t('party')}</label><select id="gs_party"><option value="">${t('own_opt')}</option>${partyOpts(null, 'grindprod')}</select></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="startGrind2()">▶ ${t('start_l')}</button></div></div></div>${accEnd()}
  ${accHead('grindprod','entry','➕',t('grind_prod') + ' ' + t('entry_t'),t('accd_gp_entry'),'entry')}<div class="card"><div style="text-align:end;margin-bottom:4px"><button class="small voicebtn" onclick="voiceFill('job')">${t('voice')}</button></div>
   <div class="row"><div class="field"><label>${t('date')}</label><input id="job_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('party')}</label><select id="job_party"><option value="">${t('own_opt')}</option>${partyOpts(null, 'grindprod')}</select></div>
   <div class="field"><label>${t('shift_l')}</label><div class="seg"><button type="button" id="js_day" class="segbtn on" onclick="jobShiftUI('Day')">${t('day_l')}</button><button type="button" id="js_night" class="segbtn" onclick="jobShiftUI('Night')">${t('night_l')}</button></div></div>
   <div class="field"><label>${t('start_time')}</label><input id="job_start" type="time"></div>
   <div class="field"><label>${t('end_time')}</label><input id="job_end" type="time"></div></div>
   <div class="row"><div class="field"><label>${t('grade')}</label><input id="job_grade" type="number" step="0.1"></div>
   <div class="field"><label>${t('powder_bags')}</label><input id="job_outbags" type="number" step="1" min="0" oninput="jobTotalsUI()"></div>
   <div class="field"><label>${t('filter_bags_l')}</label><input id="job_filterbags" type="number" step="1" min="0" oninput="jobTotalsUI()"></div>
   <div class="field"><label>${t('bag_source')}</label><select id="job_src"><option value="mill">${t('mill_bags')}</option><option value="client">${t('client_bags_s')}</option></select></div></div>
   <div class="field"><label>${t('note')}</label><input id="job_note"></div>
   <p id="job_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <div id="job_totals" style="border:1px solid var(--line,#ddd);border-radius:10px;padding:6px 12px;margin:4px 0 10px"></div>
   <button id="job_save" onclick="addJob()">${t('save')}</button> <button id="job_cancel" class="ghost" style="display:none" onclick="cancelJobEdit()">${t('cancel_l')}</button></div>${accEnd()}
  ${closures.length ? `${accHead('grindprod','closures','🏭',t('shift_closures_l'),t('accd_closures'))}<div class="card">
   ${closures.map(c => `<div class="kv"><span>${alertDateDisp(c.date)} · ${c.shift === 'Night' ? t('night_l') : t('day_l')}</span><b>${c.reason === 'power' ? t('sa_reason_power') : t('sa_reason_technical')}${c.note ? ' · ' + esc(c.note) : ''} <span class="muted">(${esc(c.by_user || '')})</span></b></div>`).join('')}</div>${accEnd()}` : ''}
  ${accHead('grindprod','bagweights','⚖',t('bag_weights_l'),t('bag_weights_hint'))}<div class="card">
   <p class="small muted">${t('bag_weights_hint')}</p>
   <div class="row"><div class="field"><label>${t('powder_bag_kg_l')}</label><input id="bw_powder" type="number" step="0.1" min="0" value="${STATE.powder_bag_kg != null ? STATE.powder_bag_kg : 50}"></div>
   <div class="field"><label>${t('filter_bag_kg_l')}</label><input id="bw_filter" type="number" step="0.1" min="0" value="${STATE.filter_bag_kg != null ? STATE.filter_bag_kg : 50}"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="saveBagWeights()">${t('save')}</button></div></div></div>${accEnd()}
  ${accHead('grindprod','history','📋',t('entries_l'),t('accd_records'))}<div class="card">${xlBar('grinding')}<div class="wrap"><table><tr><th>${t('date')}</th><th>${t('party')}</th><th>${t('weight_l')}</th><th>${t('grade')}</th><th>${t('shift_l')}</th><th>${t('powder_bags')}</th><th>${t('source_l')}</th><th></th></tr>
   ${union.slice(0, 60).map(r => `<tr><td>${r.date}</td><td>${esc(r.party_name)}</td><td>${!r.tons ? '—' : tonsDisp(r.tons)}</td><td>${r.grade_pct || ''}</td><td>${r.shift ? (r.shift === 'Night' ? t('night_l') : t('day_l')) : ''}${r.start_time ? ` ${r.start_time}${r.end_time ? ' – ' + r.end_time : ''}` : ''}</td><td>${r.bags || ''}</td><td>${r.bag_source ? (r.bag_source === 'client' ? t('client_bags_s') : t('mill_bags')) : ''}</td><td>${isOwner() ? `<button class="small ghost" onclick="${r.kind === 'job' ? `editJob(${r.id})` : `editProd(${r.id})`}">${t('edit')}</button>` : ''} ${delBtn(r.kind === 'job' ? 'grinding_jobs' : 'production', r.id)}</td></tr>`).join('')}</table></div></div>${accEnd()}`;
  jobTotalsUI();
  /* Enter Now on a shift alert lands here with date + shift preset */
  if (GP_PREFILL) {
    const pf = GP_PREFILL; GP_PREFILL = null;
    const jd = document.getElementById('job_date'); if (jd) jd.value = pf.date;
    jobShiftUI(pf.shift);
    accOpen('grindprod', 'entry');
    const ob = document.getElementById('job_outbags'); if (ob) ob.focus();
  }
};
/* Live shift total on the merged entry: bags x the CURRENT bag-weight
   defaults (STATE, from the Bag weight defaults card) = kg = tons.
   Always rendered — the zero state shows all three lines at 0. */
window.jobTotalsUI = () => {
  const box = document.getElementById('job_totals');
  if (!box) return;
  const t3 = v => (Math.round((v || 0) * 1000) / 1000).toLocaleString('en-US', { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  const pb = parseInt(val('job_outbags')) || 0;
  const fb = parseInt(val('job_filterbags')) || 0;
  const pw = Number(STATE.powder_bag_kg != null ? STATE.powder_bag_kg : 50) || 50;
  const fw = Number(STATE.filter_bag_kg != null ? STATE.filter_bag_kg : 50) || 50;
  const pkg = pb * pw, fkg = fb * fw;
  box.innerHTML =
    `<div class="kv"><span>${t('powder')}</span><b>${pb} ${t('bags')} × ${fmtN(pw)} kg = ${fmtN(pkg)} kg = ${t3(pkg / 1000)} tons</b></div>` +
    `<div class="kv"><span>${t('filter_powder_l')}</span><b>${fb} ${t('bags')} × ${fmtN(fw)} kg = ${fmtN(fkg)} kg = ${t3(fkg / 1000)} tons</b></div>` +
    `<div class="kv"><span>${t('total_production_l')}</span><b>${fmtN(pkg + fkg)} kg = ${t3((pkg + fkg) / 1000)} tons</b></div>`;
};
window.saveBagWeights = async () => {
  try {
    const r = await post('/api/settings/bag-weights', { powder_bag_kg: num('bw_powder'), filter_bag_kg: num('bw_filter') });
    STATE.powder_bag_kg = r.powder_bag_kg; STATE.filter_bag_kg = r.filter_bag_kg;
    jobTotalsUI();
    okPopup(t('settings_saved'));
  } catch (e) { msg(e.message, 'err'); }
};
/* the old separate pages now land on the merged page */
VIEWS.grinding = async el => { VIEW = 'grindprod'; render(); };
VIEWS.production = async el => { VIEW = 'grindprod'; render(); };
window.startGrind2 = async () => { await post('/api/grind/start', { party_id: val('gs_party') || null }); okPopup(t('sess_started')); render(); };
window.addJob = async () => {
  try {
    // ONE merged save: the grinding job + (when powder bags were packed
    // or filter powder came out) exactly one linked production row —
    // the server writes both in a single transaction, so no total can
    // count the bags twice. NO ground-rock weight is collected: the
    // mill's register never weighs ground rock — rock consumption is
    // derived from the powder produced. No rate is collected either,
    // so nothing is sent for it and no charge posts here.
    const body = { date: val('job_date'), party_id: val('job_party') || null,
      grade_pct: num('job_grade'), shift: JOB_SHIFT, note: val('job_note'),
      out_bags: parseInt(val('job_outbags')) || 0,
      filter_bags: parseInt(val('job_filterbags')) || 0,
      bag_source: val('job_src'), start_time: val('job_start'), end_time: val('job_end') };
    const r = await post('/api/jobs', body);
    okPopup(t('job_saved') + (r.amount ? ' ' + fmt(r.amount) : '')); render();
  } catch (e) { msg(e.message, 'err'); }
};


VIEWS.warehouse = async el => {
  const w = await get('/api/warehouse');
  const g = await get('/api/godam').catch(() => ({ counts: [], adjustments: [] }));
  const isOwner = STATE.user.role === 'owner';
  const bagTons = p => tonsDisp(p.bags_ready_t != null ? p.bags_ready_t : (Number(p.bags_ready) || 0) * 0.05);
  const diffHTML = d => d === 0 ? '—' : `<b style="color:${d < 0 ? '#c0392b' : '#0c7a4e'}">${d > 0 ? '+' : ''}${d} (${d < 0 ? t('shortage') : t('excess')})</b>`;
  const bmoves = await get('/api/bag-moves').catch(() => []);
  const cbags = await get('/api/client-bags').catch(() => []);
  // ONE combined bags list: mill bardana moves + party custody bags
  const bagRows = [];
  BAG_CACHE = bagRows; EDIT_BAG = null;
  bmoves.forEach(r => bagRows.push({ tbl: 'bag_movements', id: r.id, date: r.date, type: 'mill',
    party: '', party_id: null, raw_dir: r.direction, dir: r.direction === 'in' ? t('dir_in_bags') : t('dir_out_bags'), bags: r.bags, note: r.note || '' }));
  cbags.forEach(r => bagRows.push({ tbl: 'client_bags', id: r.id, date: r.date, type: 'party',
    party: r.party_name || '', party_id: r.party_id || null, raw_dir: r.direction, dir: r.direction === 'received' ? t('received_opt') : t('returned_opt'), bags: r.bags, note: r.note || '' }));
  bagRows.sort((a, b) => (b.date || '').localeCompare(a.date || '') || b.id - a.id);
  const partyBagLines = w.parties.filter(x => x.client_bags_received || x.client_bags_returned || x.client_bags_left)
    .map(x => `${esc(x.party)}: ${t('came')} ${x.client_bags_received} · ${t('used_l')} ${x.client_bags_used} · ${t('returned_l')} ${x.client_bags_returned} · <b>${t('left_l')} ${x.client_bags_left}</b>`).join('<br>');
  el.innerHTML = `${accHead('warehouse','overview','🏬',t('warehouse'),t('accd_wh_overview'),'overview')}<div class="card">
   <div class="wrap"><table><tr><th>${t('party')}</th><th>${t('bags_made_l')}</th><th>${t('bags_out_l')}</th><th>${t('bags_ready_l')}</th><th>${t('bags_tons')}</th><th>${t('client_bags_s')}</th></tr>
   ${w.parties.map(p => `<tr><td>${esc(p.party)}</td><td>${p.bags_made}</td><td>${p.bags_out}</td><td><b>${p.bags_ready}</b></td>
     <td>${bagTons(p)}</td>
     <td>${t('came')} ${p.client_bags_received} · ${t('used_l')} ${p.client_bags_used} · ${t('returned_l')} ${p.client_bags_returned} · <b>${t('left_l')} ${p.client_bags_left}</b></td></tr>`).join('')}</table></div>
   <p class="small">${t('own_bags_line')}: ${t('made_l')} ${w.own.bags_made} · ${t('sold_l')} ${w.own.bags_sold} · ${t('bags_ready_l')} <b>${w.own.bags_ready}</b> · ${t('bags_tons')} <b>${bagTons(w.own)}</b></p>
   <p class="small">🧹 ${t('filter_powder_l')} (${t('own_word')}): <b>${fmtN((w.own && w.own.filter_bags) || 0)} ${t('bags')} · ${fmtN(w.filter_powder_kg || 0)} kg</b> (${tonsDisp((w.filter_powder_kg || 0) / 1000)})</p>
   <p class="small muted">${t('out_warn')}</p>
   ${(w.ageing || []).length ? `<p class="small">⏰ <b>${t('powder_ageing')}:</b> ${w.ageing.map(a => `${esc(a.party)} — ${a.bags} ${t('bags')} · ${tonsDisp(a.tons)} · ${a.days} ${t('days_waiting')}`).join(' · ')}</p>` : ''}</div>${accEnd()}
  ${accHead('warehouse','ginti','🧮',t('godam_ginti'),t('accd_ginti'))}<div class="card">
   <div class="row"><div class="field"><label>${t('date')}</label><input id="gc_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('party')}</label><select id="gc_party"><option value="">${t('own_opt')}</option>${partyOpts()}</select></div>
   <div class="field"><label>${t('counted_bags')} *</label><input id="gc_bags" type="number"></div>
   <div class="field"><label>${t('note')}</label><input id="gc_note"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="addGodamCount()">${t('count_save')}</button></div></div>
   <h3>${t('counts_history')}</h3>
   <div class="wrap"><table><tr><th>${t('date')}</th><th>${t('party')}</th><th>${t('book_bags')}</th><th>${t('counted_bags')}</th><th>${t('difference')}</th><th></th></tr>
   ${g.counts.map(c => { const adj = g.adjustments.find(a => a.count_id === c.id);
     return `<tr><td>${c.date}</td><td>${esc(c.party_name || t('own_word'))}</td><td>${c.book_bags}</td><td>${c.counted_bags}</td><td>${diffHTML(c.diff)}</td>
     <td>${c.diff !== 0 ? (adj ? `<span class="badge ${adj.status === 'approved' ? '' : adj.status === 'rejected' ? 'red' : 'amber'}">${t('ginti_adj')}: ${adj.status === 'pending' ? t('pending') : adj.status}</span>` : `<button class="small" onclick="reqAdjustment(${c.id})">${t('adj_request')}</button>`) : ''}</td></tr>`; }).join('') || `<tr><td class="muted">—</td></tr>`}</table></div>
   ${g.adjustments.length ? `<h3>${t('adj_history')}</h3><div class="wrap"><table><tr><th>${t('date')}</th><th>${t('party')}</th><th>${t('bags')}</th><th>${t('status')}</th><th></th></tr>
   ${g.adjustments.map(a => `<tr><td>${a.date}</td><td>${esc(a.party_name || t('own_word'))}</td><td>${a.bags > 0 ? '+' : ''}${a.bags}</td><td>${a.status === 'pending' ? t('pending') : a.status}</td>
   <td>${a.status === 'pending' && isOwner ? `<button class="small" onclick="adjDecide(${a.id},'approved')">✓ ${t('approve')}</button> <button class="small danger" onclick="adjDecide(${a.id},'rejected')">✗ ${t('reject')}</button>` : ''}</td></tr>`).join('')}</table></div>` : ''}</div>${accEnd()}
  ${accHead('warehouse','bags','🎒',t('bags') + ' — ' + t('bardana'),t('accd_bags'))}<div class="card">
   <div class="row"><div class="field"><label>${t('bag_type_l')}</label><select id="bg_type" onchange="bagTypeUI()"><option value="mill">${t('bags_mill_opt')}</option><option value="party">${t('bags_party_opt')}</option></select></div>
   <div class="field"><label>${t('date')}</label><input id="bg_date" type="date" value="${todayStr()}"></div>
   <div class="field" id="bg_party_f" style="display:none"><label>${t('party')}</label><select id="bg_party">${partyOpts(null, 'production')}</select></div>
   <div class="field"><label>${t('direction')}</label><select id="bg_dir"></select></div>
   <div class="field"><label>${t('bags')} *</label><input id="bg_bags" type="number"></div>
   <div class="field"><label>${t('note')}</label><input id="bg_note"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button id="bg_save" onclick="addBagsEntry()">${t('add')}</button> <button id="bg_cancel" class="ghost" style="display:none" onclick="cancelBagEdit()">${t('cancel_l')}</button></div></div>
   <p id="bg_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <p class="small muted">${t('bardana')}: <b>${w.bardana.left}</b> · ${t('bardana_used')}: <b>${w.bardana.used}</b> · ${t('bardana_in')}: ${w.bardana.in} · ${t('bardana_out')}: ${w.bardana.out}</p>
   ${partyBagLines ? `<p class="small muted">${t('party_bags_t')}:<br>${partyBagLines}</p>` : ''}
   <h3>${t('entries_l')}</h3>
   <div class="wrap"><table><tr><th>${t('date')}</th><th>${t('type_l')}</th><th>${t('party')}</th><th>${t('direction')}</th><th>${t('bags')}</th><th>${t('note')}</th><th></th></tr>
   ${bagRows.slice(0, 60).map(r => `<tr><td>${r.date}</td><td>${r.type === 'mill' ? t('bags_mill_opt') : t('bags_party_opt')}</td><td>${esc(r.party)}</td><td>${r.dir}</td><td>${r.bags}</td><td>${esc(r.note)}</td><td>${isOwner() ? `<button class="small ghost" onclick="editBagEntry('${r.tbl}',${r.id})">${t('edit')}</button>` : ''} ${delBtn(r.tbl, r.id)}</td></tr>`).join('') || `<tr><td class="muted">—</td></tr>`}</table></div></div>${accEnd()}
  ${accHead('warehouse','stockcount','📏',t('stock_count_t'),t('accd_stockcount'))}<div class="card">
   <div class="row"><div class="field"><label>${t('date')}</label><input id="sc_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('item_l')}</label><input id="sc_item" placeholder="powder_tons / bags / rock_tons"></div>
   <div class="field"><label>${t('counted_l')}</label><input id="sc_counted" type="number" step="0.01"></div>
   <div class="field"><label>${t('book_l')}</label><input id="sc_book" type="number" step="0.01"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button id="sc_save" onclick="addStockCount()">${t('add')}</button> <button id="sc_cancel" class="ghost" style="display:none" onclick="cancelStockCountEdit()">${t('cancel_l')}</button></div></div>
   <p id="sc_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <div id="sc_list"></div></div>${accEnd()}`;
  const sc = await get('/api/stock-counts');
  SC_CACHE = sc; EDIT_SC = null;
  $('#sc_list').innerHTML = '<div class="wrap"><table>' + sc.slice(0, 20).map(r => `<tr><td>${r.date}</td><td>${esc(r.item)}</td><td>${t('counted_l')} ${r.counted_qty}</td><td>${t('book_l')} ${r.book_qty}</td><td>${t('diff_l')} <b>${(r.counted_qty - r.book_qty).toFixed(2)}</b></td><td>${isOwner() ? `<button class="small ghost" onclick="editStockCount(${r.id})">${t('edit')}</button>` : ''} ${delBtn('stock_counts', r.id)}</td></tr>`).join('') + '</table></div>';
  bagTypeUI();
};
window.addGodamCount = async () => {
  try {
    if (!reqCheck([['gc_bags', 'fl_bags', 'num']])) return;
    const r = await post('/api/godam-counts', { date: val('gc_date'), party_id: val('gc_party') || null,
      counted_bags: parseInt(val('gc_bags')) || 0, note: val('gc_note') });
    okPopup(t('ginti_saved') + ' · ' + t('book_w') + ' ' + r.book_bags + ' · ' + t('ginti_w') + ' ' + r.counted_bags +
      ' · ' + t('difference') + ': ' + (r.diff > 0 ? '+' : '') + r.diff);
    render();
  } catch (e) { msg(e.message, 'err'); }
};
window.reqAdjustment = async id => {
  try { await post('/api/stock-adjustments', { count_id: id }); okPopup(t('adj_pending')); render(); }
  catch (e) { msg(e.message, 'err'); }
};
/* ONE Bags card serves both bag kinds: the type selector swaps the
   direction options and shows the party picker only for party bags.
   The two underlying records (and all stock math) stay separate. */
window.bagTypeUI = () => {
  const type = val('bg_type');
  const dir = document.getElementById('bg_dir');
  if (dir) dir.innerHTML = type === 'party'
    ? `<option value="received">${t('received_opt')}</option><option value="returned">${t('returned_opt')}</option>`
    : `<option value="in">${t('dir_in_bags')}</option><option value="out">${t('dir_out_bags')}</option>`;
  const pf = document.getElementById('bg_party_f');
  if (pf) pf.style.display = type === 'party' ? '' : 'none';
};
window.addBagsEntry = async () => {
  if (!reqCheck([['bg_bags', 'fl_bags', 'pos']])) return;
  try {
    if (val('bg_type') === 'party') {
      if (!reqCheck([['bg_party', 'party', 'text']])) return;
      await post('/api/client-bags', { date: val('bg_date'), party_id: val('bg_party'),
        direction: val('bg_dir'), bags: parseInt(val('bg_bags')) || 0, note: val('bg_note') });
    } else {
      await post('/api/bag-moves', { date: val('bg_date'), direction: val('bg_dir'),
        bags: parseInt(val('bg_bags')) || 0, note: val('bg_note') });
    }
    okPopup(t('saved')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.addStockCount = async () => { await post('/api/stock-counts', { date: val('sc_date'), item: val('sc_item'), counted_qty: num('sc_counted'), book_qty: num('sc_book') }); okPopup(t('saved')); render(); };
window.editStockCount = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = SC_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_SC = id;
  $('#sc_date').value = r.date || todayStr();
  $('#sc_item').value = r.item || '';
  $('#sc_counted').value = r.counted_qty;
  $('#sc_book').value = r.book_qty;
  editSwap('sc_save', 'updateStockCount()', 'sc_cancel', 'sc_editing');
};
window.updateStockCount = async () => { await post('/api/stock-counts', { id: EDIT_SC, date: val('sc_date'), item: val('sc_item'), counted_qty: num('sc_counted'), book_qty: num('sc_book') }); EDIT_SC = null; okPopup(t('saved')); render(); };
window.cancelStockCountEdit = () => { EDIT_SC = null; render(); };
window.editBagEntry = (tbl, id) => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = BAG_CACHE.find(x => x.tbl === tbl && x.id === id); if (!r) return;
  EDIT_BAG = { tbl, id };
  $('#bg_type').value = tbl === 'client_bags' ? 'party' : 'mill';
  bagTypeUI();
  if (tbl === 'client_bags') $('#bg_party').value = r.party_id || '';
  $('#bg_dir').value = r.raw_dir;
  $('#bg_date').value = r.date || todayStr();
  $('#bg_bags').value = r.bags;
  $('#bg_note').value = r.note || '';
  editSwap('bg_save', 'updateBagEntry()', 'bg_cancel', 'bg_editing');
};
window.updateBagEntry = async () => {
  if (!reqCheck([['bg_bags', 'fl_bags', 'pos']])) return;
  try {
    if (EDIT_BAG.tbl === 'client_bags') {
      if (!reqCheck([['bg_party', 'party', 'text']])) return;
      await post('/api/client-bags', { id: EDIT_BAG.id, date: val('bg_date'), party_id: val('bg_party'),
        direction: val('bg_dir'), bags: parseInt(val('bg_bags')) || 0, note: val('bg_note') });
    } else {
      await post('/api/bag-moves', { id: EDIT_BAG.id, date: val('bg_date'), direction: val('bg_dir'),
        bags: parseInt(val('bg_bags')) || 0, note: val('bg_note') });
    }
    EDIT_BAG = null;
    okPopup(t('saved')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.cancelBagEdit = () => { EDIT_BAG = null; render(); };

/* Owner-only EDIT of a merged entry (27 Oct): a job row edits the job
   AND its linked production row as one save; a standalone production
   row edits through the same form's production fields. The server
   rewrites both rows in one transaction, so warehouse / theka /
   Day-Night / Phosphate Detail all reflect the correction once. */
const gpFillForm = r => {
  $('#job_date').value = r.date || todayStr();
  $('#job_party').value = r.party_id || '';
  jobShiftUI(r.shift === 'Night' ? 'Night' : 'Day');
  $('#job_start').value = r.start_time || '';
  $('#job_end').value = r.end_time || '';
  $('#job_grade').value = r.grade_pct || '';
  $('#job_outbags').value = r.bags || 0;
  $('#job_filterbags').value = r.filter_bags || 0;
  $('#job_src').value = r.bag_source || 'mill';
  $('#job_note').value = r.note || '';
  jobTotalsUI();
  const sb = document.getElementById('job_save');
  if (sb) { sb.textContent = t('save_changes'); sb.setAttribute('onclick', 'updateJob()'); }
  const cb = document.getElementById('job_cancel'); if (cb) cb.style.display = '';
  const eb = document.getElementById('job_editing'); if (eb) eb.style.display = '';
  accOpen('grindprod', 'entry');   // the edit form lives in the Entry section
};
window.editJob = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = GP_UNION.find(x => x.kind === 'job' && x.id === id); if (!r) return;
  EDIT_JOB = { kind: 'job', id, filter_kg: r.filter_kg || 0 };
  gpFillForm(r);
};
window.editProd = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = GP_UNION.find(x => x.kind === 'prod' && x.id === id); if (!r) return;
  EDIT_JOB = { kind: 'prod', id, filter_kg: r.filter_kg || 0 };
  gpFillForm(r);
};
window.updateJob = async () => {
  try {
    if (!EDIT_JOB) return;
    let r;
    if (EDIT_JOB.kind === 'job') {
      const body = { id: EDIT_JOB.id, date: val('job_date'), party_id: val('job_party') || null,
        grade_pct: num('job_grade'), shift: JOB_SHIFT, note: val('job_note'),
        out_bags: parseInt(val('job_outbags')) || 0,
        filter_bags: parseInt(val('job_filterbags')) || 0,
        bag_source: val('job_src'), start_time: val('job_start'), end_time: val('job_end') };
      // a legacy kg-stored filter amount (no filter bags) rides along
      // untouched — the form only carries filter BAGS
      if (EDIT_JOB.filter_kg > 0 && !body.filter_bags) body.filter_kg = EDIT_JOB.filter_kg;
      r = await post('/api/jobs', body);
    } else {
      const body = { id: EDIT_JOB.id, date: val('job_date'), party_id: val('job_party') || null,
        bags: parseInt(val('job_outbags')) || 0,
        filter_bags: parseInt(val('job_filterbags')) || 0,
        bag_source: val('job_src'), start_time: val('job_start'), end_time: val('job_end'),
        note: val('job_note') };
      if (EDIT_JOB.filter_kg > 0 && !body.filter_bags) body.filter_kg = EDIT_JOB.filter_kg;
      r = await post('/api/production', body);
    }
    EDIT_JOB = null;
    okPopup(t('job_saved') + (r && r.amount ? ' ' + fmt(r.amount) : '')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.cancelJobEdit = () => { EDIT_JOB = null; render(); };

/* Own Trade is MERGED (owner's order, 27 Oct 2026): buying lives on
   Vehicle In (gate) and in the party Ledger (off-gate); selling lives
   on Vehicle Out (gate sale section) and in the party Ledger. The old
   standalone page redirects to Own Stock & Trade, which carries the
   stock position, the combined trade history and Direct Trade. */
VIEWS.owntrade = async el => { VIEW = 'ownstock'; render(); };
/* Orders are REMOVED (owner's order, 28 Oct 2026 — the mill does no
   advance booking). The table and stored order_id values are kept in
   the database, unrendered; this stale route lands on the Dashboard. */
VIEWS.orders = async el => { VIEW = 'dashboard'; render(); };

let DEAL_ITEM = 'rock';
let EDIT_DEAL = null;
let HISTORY_CACHE = [];
window.dealItemUI = it => {
  DEAL_ITEM = it;
  ['rock', 'powder', 'other'].forEach(k => { const b = document.getElementById('dl_it_' + k); if (b) b.classList.toggle('on', k === it); });
  const g = (id, on) => { const e = document.getElementById(id); if (e) e.style.display = on ? '' : 'none'; };
  g('dl_g_rock', it === 'rock'); g('dl_g_powder', it === 'powder'); g('dl_g_other', it === 'other');
  dealProfitCalc();
};
window.dealProfitCalc = () => {
  const el2 = document.getElementById('dl_profit'); if (!el2) return;
  let b = 0, s = 0;
  if (DEAL_ITEM === 'other') { b = num('dl_qty') * num('dl_buy_urate'); s = num('dl_qty') * num('dl_sell_urate'); }
  else if (DEAL_ITEM === 'powder') { b = toTonsVal(num('dl_tons_powder')) * num('dl_buy_rate'); s = toTonsVal(num('dl_tons_powder')) * num('dl_sell_rate'); }
  else { const t = toTonsVal(num('dl_tons_rock')); const billed = Math.round(t * (1 - num('dl_ded') / 100) * 1000) / 1000; b = billed * num('dl_buy_rate'); s = t * num('dl_sell_rate'); }
  el2.textContent = (b || s) ? fmt(s - b) : '—';
};
const dealBody = () => {
  const body = { date: val('dl_date'), buy_party_id: val('dl_buy_party'), sell_party_id: val('dl_sell_party'),
    item: DEAL_ITEM, note: val('dl_note') };
  if (DEAL_ITEM === 'other') { body.item_name = val('dl_iname'); body.qty = num('dl_qty'); body.unit = val('dl_unit');
    body.buy_unit_rate = num('dl_buy_urate'); body.sell_unit_rate = num('dl_sell_urate'); }
  else if (DEAL_ITEM === 'powder') { body.tons = toTonsVal(num('dl_tons_powder')); body.bags = parseInt(val('dl_bags')) || 0;
    body.buy_rate = num('dl_buy_rate'); body.sell_rate = num('dl_sell_rate'); }
  else { body.tons = toTonsVal(num('dl_tons_rock')); body.grade_pct = num('dl_grade'); body.deduction_pct = num('dl_ded');
    body.buy_rate = num('dl_buy_rate'); body.sell_rate = num('dl_sell_rate'); }
  return body;
};
window.addDeal = async () => {
  if (!reqCheck([['dl_buy_party', 'fl_party', 'text'], ['dl_sell_party', 'fl_party', 'text']])) return;
  try { const r = await post('/api/direct-deals', dealBody());
    okPopup(t('deal_saved') + ' — ' + t('profit_l') + ' ' + fmt(r.profit)); render(); } catch (e) { msg(e.message, 'err'); }
};
window.updateDeal = async () => {
  if (!EDIT_DEAL) return;
  try { const r = await post('/api/direct-deals', { id: EDIT_DEAL, ...dealBody() });
    EDIT_DEAL = null; okPopup(t('deal_saved') + ' — ' + t('profit_l') + ' ' + fmt(r.profit)); render(); } catch (e) { msg(e.message, 'err'); }
};
window.cancelDealEdit = () => { EDIT_DEAL = null; render(); };
window.showDealForm = () => { accOpen('ownstock', 'deal'); };
window.editDeal = dealId => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = HISTORY_CACHE.find(x => x.kind === 'deal' && x.deal_id === dealId); if (!r) return;
  showDealForm();
  EDIT_DEAL = dealId;
  $('#dl_date').value = r.date || todayStr();
  $('#dl_buy_party').value = r.buy_party_id || '';
  $('#dl_sell_party').value = r.sell_party_id || '';
  $('#dl_note').value = r.note || '';
  dealItemUI(r.item || 'rock');
  if ((r.item || 'rock') === 'other') { $('#dl_iname').value = r.item_name || ''; $('#dl_qty').value = r.qty || ''; $('#dl_unit').value = r.unit || ''; }
  else if (r.item === 'powder') { $('#dl_tons_powder').value = fromKgVal((r.tons || 0) * 1000); $('#dl_bags').value = r.bags || 0; }
  else { $('#dl_tons_rock').value = fromKgVal((r.tons || 0) * 1000); }
  /* rates: re-read from the two legs */
  const pur = PUR_CACHE.find(x => x.id === r.purchase_id), sal = SALE_CACHE.find(x => x.id === r.sale_id);
  if (pur && sal) {
    if ((r.item || 'rock') === 'other') { $('#dl_buy_urate').value = pur.unit_rate || ''; $('#dl_sell_urate').value = sal.unit_rate || ''; }
    else { $('#dl_buy_rate').value = pur.rate_per_ton || ''; $('#dl_sell_rate').value = sal.rate_per_ton || '';
           if (r.item === 'rock') { $('#dl_grade').value = pur.grade_pct || ''; $('#dl_ded').value = pur.deduction_pct || 0; } }
  }
  dealProfitCalc();
  editSwap('dl_save', 'updateDeal()', 'dl_cancel', 'dl_editing');
  accOpen('ownstock', 'deal');   // editSwap scrolled to top — bring the form back into view
};
window.deleteDeal = dealId => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  confirmDelete(t('direct_trade_l'), async () => {
    try { await post('/api/direct-deals/delete', { deal_id: dealId }); okPopup(t('deleted_ok')); render(); }
    catch (e) { msg(e.message, 'err'); } });
};
window.editGateRow = (tripId, dir) => {
  PENDING_TRIP_EDIT = { id: tripId, dir };
  VIEW = dir === 'IN' ? 'vehicle_in' : 'vehicle_out';
  render();
};
const tradeQtyTxt = r => {
  if (r.item === 'other') return `${esc(r.item_name || '')} ${r.qty || 0} ${esc(r.unit || '')}`;
  if (r.item === 'rock') return tonsDisp(r.tons);
  return `${tonsDisp(r.tons)} · ${r.bags || 0} ${t('bags')}`;
};
const histActions = r => {
  if (!isOwner()) return '';
  if (r.kind === 'deal')
    return `<button class="small ghost" onclick="editDeal('${r.deal_id}')">${t('edit')}</button> <button class="small ghost" onclick="deleteDeal('${r.deal_id}')">${t('delete_l')}</button>`;
  if (r.source === 'gate')
    return `<button class="small ghost" onclick="editGateRow(${r.trip_id},'${r.kind === 'buy' ? 'IN' : 'OUT'}')">${t('edit')}</button> ${delBtn('trips', r.trip_id)}`;
  const tbl = r.kind === 'buy' ? 'purchases' : 'sales';
  const fn = r.kind === 'buy' ? 'editPurchase' : 'editSale';
  return `<button class="small ghost" onclick="${fn}(${r.id})">${t('edit')}</button> ${delBtn(tbl, r.id)}`;
};
VIEWS.ownstock = async el => {
  const o = await get('/api/ownstock');
  const hist = await get('/api/trade-history').catch(() => ({ rows: [] }));
  HISTORY_CACHE = hist.rows || [];
  const [purs, sales] = await Promise.all([get('/api/purchases'), get('/api/sales')]);
  PUR_CACHE = purs; SALE_CACHE = sales;
  DEAL_ITEM = 'rock'; EDIT_DEAL = null;
  el.innerHTML = `${accHead('ownstock','summary','🏭',t('own_stock') + ' — ' + t('g_own'),t('accd_os_summary'),'summary')}<div class="card">
   <div class="grid">
    <div class="stat"><div class="ic">🪨</div><div class="n">${tonsDisp(o.rock_left_t)}</div><div class="l">${t('rock_lying')}</div><div class="l">${t('rock_bought')}: ${tonsDisp(o.rock_bought_t)} · ${t('rock_ground')}: ${tonsDisp(o.ground_t)} · ${t('rock_sold_l')}: ${tonsDisp(o.rock_sold_t || 0)} · ${t('outside_sent_l')}: ${tonsDisp(o.outside_sent_t || 0)}</div></div>
    <div class="stat"><div class="ic">📦</div><div class="n">${tonsDisp(o.powder_left_t)}</div><div class="l">${t('powder_lying')}</div><div class="l">${t('powder_made_l')}: ${tonsDisp(o.powder_made_t)} · ${t('powder_bought_l')}: ${tonsDisp(o.powder_bought_t || 0)} · ${t('powder_sold')}: ${tonsDisp(o.sold_t)} · ${t('dispatched_l')}: ${tonsDisp(o.dispatched_t)} · ${t('outside_recv_l')}: ${tonsDisp(o.outside_received_t || 0)}</div></div>
    <div class="stat"><div class="ic">🧹</div><div class="n">${tonsDisp(o.filter_t || 0)}</div><div class="l">${t('filter_powder_l')} (${t('own_word')}) · ${o.filter_bags || 0} ${t('bags')}</div></div>
    <div class="stat"><div class="ic gold">🧺</div><div class="n">${o.bags_ready}</div><div class="l">${t('bags_ready_l')} (${t('made_l')} ${o.bags_made} · ${t('sold_l')} ${o.bags_sold})</div></div>
   </div></div>
  <div class="card"><h3>📒 ${t('owntrade')} — ${t('summary_t')}</h3>
   <div class="kv"><span>${t('purchases_total')}</span><b>${fmt(o.purchases_total)}</b></div>
   <div class="kv"><span>${t('sales_total')}</span><b>${fmt(o.sales_total)}</b></div>
   <div class="kv"><span>${t('to_receive')}</span><b>${fmt(o.trade_receivable)}</b></div>
   <div class="kv"><span>${t('to_pay')}</span><b>${fmt(o.trade_payable)}</b></div></div>${accEnd()}
  ${accHead('ownstock','deal','🔀',t('direct_trade_l'),t('direct_note_l'))}<div class="card">
   <p class="small muted">${t('direct_note_l')}</p>
   <div class="row"><div class="field"><label>${t('date')}</label><input id="dl_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('buy_from_l')} (${t('party')})</label><select id="dl_buy_party">${partyOpts(null, 'purchase')}</select></div>
   <div class="field"><label>${t('sell_to_l')} (${t('party')})</label><select id="dl_sell_party">${partyOpts(null, 'sale')}</select></div></div>
   <div class="field"><label>${t('choose_item_l')}</label><div class="seg">
     <button type="button" id="dl_it_rock" class="segbtn on" onclick="dealItemUI('rock')">${t('item_rock_l')}</button>
     <button type="button" id="dl_it_powder" class="segbtn" onclick="dealItemUI('powder')">${t('item_powder_l')}</button>
     <button type="button" id="dl_it_other" class="segbtn" onclick="dealItemUI('other')">${t('item_other_l')}</button></div></div>
   <div id="dl_g_rock" class="row"><div class="field"><label>${t('weight_l')} (${unitLabel()}) *</label><input id="dl_tons_rock" type="number" step="0.001" oninput="dealProfitCalc()"></div>
   <div class="field"><label>${t('grade')}</label><input id="dl_grade" type="number" step="0.1"></div>
   <div class="field"><label>${t('ded_l')}</label><input id="dl_ded" type="number" step="0.1" value="0" oninput="dealProfitCalc()"></div></div>
   <div id="dl_g_powder" class="row" style="display:none"><div class="field"><label>${t('weight_l')} (${unitLabel()}) *</label><input id="dl_tons_powder" type="number" step="0.001" oninput="dealProfitCalc()"></div>
   <div class="field"><label>${t('bags')}</label><input id="dl_bags" type="number" value="0"></div></div>
   <div id="dl_g_other" class="row" style="display:none"><div class="field"><label>${t('item_name_l')} *</label><input id="dl_iname"></div>
   <div class="field"><label>${t('qty_l')} *</label><input id="dl_qty" type="number" step="0.01" oninput="dealProfitCalc()"></div>
   <div class="field"><label>${t('unit_l')}</label><input id="dl_unit" placeholder="bags / pieces / kg"></div></div>
   <div class="row" id="dl_rates"><div class="field"><label>${t('buy_rate_l')}</label><input id="dl_buy_rate" type="number" oninput="dealProfitCalc()"></div>
   <div class="field"><label>${t('sell_rate_l')}</label><input id="dl_sell_rate" type="number" oninput="dealProfitCalc()"></div>
   <div class="field"><label>${t('buy_rate_l')} / unit</label><input id="dl_buy_urate" type="number" oninput="dealProfitCalc()"></div>
   <div class="field"><label>${t('sell_rate_l')} / unit</label><input id="dl_sell_urate" type="number" oninput="dealProfitCalc()"></div>
   <div class="field"><label>${t('profit_l')}</label><div id="dl_profit" class="small muted" style="padding-top:8px">—</div></div></div>
   <div class="field"><label>${t('note')}</label><input id="dl_note"></div>
   <p id="dl_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="dl_save" onclick="addDeal()">${t('save')}</button> <button id="dl_cancel" class="ghost" style="display:none" onclick="cancelDealEdit()">${t('cancel_l')}</button></div>${accEnd()}
  ${accHead('ownstock','history','📒',t('trade_history_l'),t('accd_records'))}<div class="card"><p><button class="small" onclick="showDealForm()">➕ ${t('add_direct_l')}</button></p>
   ${xlBar('purchases')} ${xlBar('sales')}
   <div class="wrap" style="margin-top:10px"><table><tr><th>${t('date')}</th><th>${t('type_l')}</th><th>${t('party')} / ${t('detail_l')}</th><th>${t('item_l')}</th><th>${t('qty_l')}</th><th>${t('src_l')}</th><th class="num">${t('amount')}</th><th></th></tr>
   ${HISTORY_CACHE.map(r => r.kind === 'deal'
     ? `<tr><td>${r.date}</td><td colspan="4">${t('direct_trade_l')}: ${r.item === 'other' ? esc(r.item_name || '') + ' ' + (r.qty || 0) + ' ' + esc(r.unit || '') : (r.item === 'rock' ? t('item_rock_l') : t('item_powder_l')) + ' ' + tonsDisp(r.tons)} — ${t('buy_from_l')} ${esc(r.buy_party)}, ${t('sell_to_l')} ${esc(r.sell_party)} — <b>${r.profit >= 0 ? t('profit_l') : t('loss_l')} ${fmt(Math.abs(r.profit))}</b></td><td>${t('src_direct_l')}</td><td class="num">${fmt(r.sell_amount)}</td><td>${histActions(r)}</td></tr>`
     : `<tr><td>${r.date}</td><td>${r.kind === 'buy' ? '🟢 ' + t('add_buy_l') : '🔵 ' + t('add_sell_l')}</td><td>${esc(r.party)}${r.invoice_no ? ` · <a target="_blank" href="/print/invoice/${r.id}?u=${PREFS.unit}">🧾 ${esc(r.invoice_no)}</a> <button class="small ghost" onclick="emailInvoice(${r.id})" title="${t('send_email_btn')}">📧</button>` : ''}${r.note ? `<br><span class="muted small">${esc(r.note)}</span>` : ''}</td><td>${r.item === 'rock' ? t('item_rock_l') : r.item === 'powder' ? t('item_powder_l') : t('item_other_l')}</td><td>${tradeQtyTxt(r)}</td><td>${r.source === 'gate' ? t('src_gate_l') : r.source === 'excel' ? t('src_excel_l') : r.source === 'outside' ? t('src_outside_l') : t('src_ledger_l')}</td><td class="num">${fmt(r.amount)}</td><td>${histActions(r)}</td></tr>`).join('') || `<tr><td colspan="8" class="muted">—</td></tr>`}
   </table></div></div>${accEnd()}`;
};

let OUT_KIND = 'sent';
let EDIT_OUT = null, OUT_CACHE = [], OG_STOCK = null, OG_PRESET_FACTORY = null;
window.ogBillFor = id => { OG_PRESET_FACTORY = id; go('outside'); };
window.outKindUI = k => {
  OUT_KIND = k;
  ['sent', 'bill', 'sold'].forEach(x => { const b = document.getElementById('og_k_' + x); if (b) b.classList.toggle('on', k === x); });
  const g = (id, on) => { const e = document.getElementById(id); if (e) e.style.display = on ? '' : 'none'; };
  g('og_g_sent', k === 'sent'); g('og_g_bill', k === 'bill'); g('og_g_sold', k === 'sold'); g('og_g_recv', k === 'received');
  g('og_f_factory', k !== 'sold');
  if (k === 'bill') ogBillPrefill(false);
};
window.ogBillPrefill = keepUsed => {
  const fid = val('og_party');
  const sents = OUT_CACHE.filter(r => r.kind === 'sent' && String(r.party_id) === String(fid))
    .sort((a, b) => (String(b.date) + b.id) < (String(a.date) + a.id) ? -1 : 1);
  const rateEl = document.getElementById('og_b_rate');
  if (rateEl && sents.length && !EDIT_OUT) rateEl.value = sents[0].rate_per_ton || '';
  ogBillCalc(keepUsed);
};
window.ogBillCalc = keepUsed => {
  const bags = num('og_b_bags');
  const kg = (typeof STATE !== 'undefined' && STATE && STATE.powder_bag_kg) || 50;
  const pt = bags * kg / 1000;
  const pct = (typeof STATE !== 'undefined' && STATE && STATE.wastage_pct != null) ? STATE.wastage_pct : 5;
  const sug = pct >= 100 ? pt : pt / (1 - pct / 100);
  const info = document.getElementById('og_b_info');
  if (info) info.textContent = bags ? ('≈ ' + pt.toFixed(3) + ' t') : '';
  const usedEl = document.getElementById('og_b_used');
  if (usedEl && !keepUsed && bags) usedEl.value = sug.toFixed(3);
};
function ogBody() {
  const body = { kind: OUT_KIND, date: val('og_date'), vehicle_no: val('og_vehicle'), note: val('og_note') };
  if (OUT_KIND === 'sold') {
    return { date: val('og_date'), party_id: val('og_s_buyer'), item: 'powder', source: 'outside',
      og_factory_id: val('og_s_factory'), bags: num('og_s_bags'), rate_per_ton: num('og_s_rate'),
      note: val('og_note') };
  }
  body.party_id = val('og_party');
  if (OUT_KIND === 'sent') {
    body.tons = toTonsVal(num('og_tons')); body.grade_pct = num('og_grade');
    body.rate_per_ton = num('og_rate'); body.rock_rate = num('og_rock_rate');
    body.from_party_id = val('og_from') || null;
  } else if (OUT_KIND === 'bill') {
    body.bags = num('og_b_bags');
    const ru = val('og_b_used'); if (ru !== '') body.rock_used_t = parseFloat(ru);
    body.rate_per_ton = num('og_b_rate');
    body.paid_now = num('og_b_paid'); body.pay_method = val('og_b_method');
  } else { body.bags = num('og_r_bags'); }
  return body;
}
window.addOutside = async () => {
  const body = ogBody();
  try {
    if (OUT_KIND === 'sold') { await post('/api/sales', body); okPopup(t('saved_l')); }
    else { await post('/api/outside-grinding', body); okPopup(t('outside_saved')); }
    render();
  } catch (e) { msg(e.message, 'err'); }
};
window.updateOutside = async () => {
  if (!EDIT_OUT) return;
  const body = ogBody(); body.id = EDIT_OUT;
  try { await post('/api/outside-grinding', body); EDIT_OUT = null; okPopup(t('outside_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.cancelOutsideEdit = () => { EDIT_OUT = null; render(); };
window.editOutside = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = OUT_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_OUT = id;
  $('#og_date').value = r.date || todayStr();
  $('#og_party').value = r.party_id || '';
  $('#og_vehicle').value = r.vehicle_no || '';
  $('#og_note').value = r.note || '';
  outKindUI(r.kind);
  if (r.kind === 'sent') {
    $('#og_tons').value = fromKgVal((r.tons || 0) * 1000); $('#og_grade').value = r.grade_pct || '';
    $('#og_rate').value = r.rate_per_ton || ''; $('#og_rock_rate').value = r.rock_rate || '';
    $('#og_from').value = r.from_party_id || '';
  } else if (r.kind === 'bill') {
    $('#og_b_bags').value = r.bags || ''; ogBillCalc(true);
    $('#og_b_used').value = r.rock_used_t != null ? r.rock_used_t : '';
    $('#og_b_rate').value = r.rate_per_ton || '';
    $('#og_b_paid').value = r.paid_now || ''; $('#og_b_method').value = r.pay_method || 'cash';
  } else { $('#og_r_bags').value = r.bags || ''; }
  editSwap('og_save', 'updateOutside()', 'og_cancel', 'og_editing');
};
VIEWS.outside = async el => {
  await loadBase();
  const [rows, stock, sales] = await Promise.all([
    get('/api/outside-grinding'), get('/api/outside-stock'), get('/api/sales')]);
  OUT_CACHE = rows; OG_STOCK = stock; EDIT_OUT = null; OUT_KIND = 'sent';
  const facs = (stock && stock.factories) || [];
  const soldRows = (sales || []).filter(r => r.source === 'outside');
  el.innerHTML = `<div class="card"><h2>🏭 ${t('outside_grinding')}</h2>
   <p id="og_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <div class="row"><div class="field"><label>${t('date')}</label><input id="og_date" type="date" value="${todayStr()}"></div>
   <div class="field" id="og_f_factory"><label>${t('outside_mill_l')}</label><select id="og_party" onchange="if(OUT_KIND==='bill')ogBillPrefill(false)">${partyOpts(null, null)}</select></div>
   <div class="field"><label>&nbsp;</label><div class="seg"><button type="button" id="og_k_sent" class="segbtn on" onclick="outKindUI('sent')">🪨 ${t('rock_sent_l')}</button><button type="button" id="og_k_bill" class="segbtn" onclick="outKindUI('bill')">🧾 ${t('og_bill_l')}</button><button type="button" id="og_k_sold" class="segbtn" onclick="outKindUI('sold')">📦 ${t('og_sold_l')}</button></div></div></div>
   <div class="row" id="og_g_sent"><div class="field"><label>${t('from_mine_l')}</label><select id="og_from"><option value=""></option>${partyOpts(null, null)}</select></div>
   <div class="field"><label>${t('weight_l')} (${unitLabel()}) *</label><input id="og_tons" type="number" step="0.001"></div>
   <div class="field"><label>${t('grade')}</label><input id="og_grade" type="number" step="0.1"></div>
   <div class="field"><label>${t('grind_rate_l')}</label><input id="og_rate" type="number"></div>
   <div class="field"><label>${t('rock_rate_l')}</label><input id="og_rock_rate" type="number"></div></div>
   <div class="row" id="og_g_bill" style="display:none"><div class="field"><label>${t('powder_ground_l')} *</label><input id="og_b_bags" type="number" step="0.5" oninput="ogBillCalc(false)"> <span class="small muted" id="og_b_info"></span></div>
   <div class="field"><label>${t('rock_used_l')} (${unitLabel()})</label><input id="og_b_used" type="number" step="0.001"></div>
   <div class="field"><label>${t('grind_rate_l')}</label><input id="og_b_rate" type="number"></div>
   <div class="field"><label>${t('paid_now_l')}</label><input id="og_b_paid" type="number"></div>
   <div class="field"><label>${t('method')}</label><select id="og_b_method"><option value="cash">${t('cash')}</option><option value="bank">${t('bank')}</option><option value="online">${t('online')}</option><option value="cheque">Cheque</option></select></div></div>
   <div class="row" id="og_g_sold" style="display:none"><div class="field"><label>${t('sold_from_l')}</label><select id="og_s_factory">${partyOpts(null, null)}</select></div>
   <div class="field"><label>${t('sell_to_l')}</label><select id="og_s_buyer">${partyOpts(null, null)}</select></div>
   <div class="field"><label>${t('bags')} *</label><input id="og_s_bags" type="number" step="0.5"></div>
   <div class="field"><label>${t('sale_rate_l')}</label><input id="og_s_rate" type="number"></div></div>
   <div class="row" id="og_g_recv" style="display:none"><div class="field"><label>${t('bags')} *</label><input id="og_r_bags" type="number" step="0.5"></div></div>
   <div class="row"><div class="field"><label>${t('vehicle')}</label><input id="og_vehicle"></div>
   <div class="field"><label>${t('note')}</label><input id="og_note"></div></div>
   <button id="og_save" onclick="addOutside()">${t('save')}</button> <button id="og_cancel" class="ghost" style="display:none" onclick="cancelOutsideEdit()">${t('cancel_l')}</button></div>
  <div class="card"><h2>📊 ${t('og_overview_l')} — ${t('outside_grinding')}</h2>
   ${facs.map(f => `<div class="kv"><span>🏭 ${esc(f.factory)}</span><b>${t('sent_t_l')}: ${tonsDisp(f.sent_t)} · ${t('ground_l')}: ${tonsDisp(f.ground_used_t)} · ${t('powder_ground_l')}: ${f.powder_bags} ${t('bags')} (${tonsDisp(f.powder_t)}) · ${t('wastage_l')}: ${tonsDisp(f.wastage_t)} (${f.wastage_pct}%) · ${t('remaining_l')}: ${tonsDisp(f.remaining_t)} · ${t('powder_left_l')}: ${f.powder_left_bags} ${t('bags')} · ${t('og_charges_l')}: ${fmt(f.charges)}</b> <button class="small ghost" onclick="openParty(${f.factory_id})">${t('ledger')}</button></div>`).join('') || `<p class="muted">—</p>`}
   ${facs.length > 1 ? `<div class="wrap" style="margin-top:10px"><table><tr><th>${t('outside_mill_l')}</th><th class="num">${t('sent_t_l')}</th><th class="num">${t('remaining_l')}</th><th class="num">${t('powder_left_l')}</th><th class="num">${t('wastage_l')} %</th></tr>
   ${facs.map(f => `<tr><td>${esc(f.factory)}</td><td class="num">${tonsDisp(f.sent_t)}</td><td class="num">${tonsDisp(f.remaining_t)}</td><td class="num">${f.powder_left_bags} ${t('bags')}</td><td class="num">${f.wastage_pct}%</td></tr>`).join('')}</table></div>` : ''}
   ${xlBar('outside')}
   <div class="wrap" style="margin-top:10px"><table><tr><th>${t('date')}</th><th>${t('outside_mill_l')}</th><th>${t('type_l')}</th><th>${t('weight_l')}</th><th>${t('bags')}</th><th class="num">${t('amount')}</th><th></th></tr>
   ${rows.slice(0, 60).map(r => `<tr><td>${r.date}</td><td>${esc(r.party_name || '')}${r.from_name ? `<br><span class="muted small">${t('from_mine_l')}: ${esc(r.from_name)}</span>` : ''}</td><td>${r.kind === 'sent' ? '🪨 ' + t('rock_sent_l') : r.kind === 'bill' ? '🧾 ' + t('og_bill_l') : '📦 ' + t('powder_back_l')}</td><td>${tonsDisp(r.tons)}</td><td>${r.bags || ''}</td><td class="num">${r.kind === 'bill' && r.amount ? fmt(r.amount) : (r.kind === 'sent' && r.rock_amount ? fmt(r.rock_amount) : '')}</td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editOutside(${r.id})">${t('edit')}</button>` : ''} ${delBtn('outside_grinding', r.id)}</td></tr>`).join('') || `<tr><td colspan="7" class="muted">—</td></tr>`}</table></div>
   ${soldRows.length ? `<h3 style="margin-top:14px">📦 ${t('og_sold_l')}</h3><div class="wrap"><table><tr><th>${t('date')}</th><th>${t('sell_to_l')}</th><th>${t('outside_mill_l')}</th><th>${t('bags')}</th><th class="num">${t('amount')}</th><th></th></tr>
   ${soldRows.slice(0, 60).map(r => `<tr><td>${r.date}</td><td>${esc(r.party_name || '')}${r.invoice_no ? ` · <a target="_blank" href="/print/invoice/${r.id}?u=${PREFS.unit}">🧾 ${esc(r.invoice_no)}</a> <button class="small ghost" onclick="emailInvoice(${r.id})" title="${t('send_email_btn')}">📧</button>` : ''}</td><td>${esc(r.factory_name || '')}</td><td>${r.bags || ''}</td><td class="num">${fmt(r.amount)}</td><td>${delBtn('sales', r.id)}</td></tr>`).join('')}</table></div>` : ''}</div>`;
  if (OG_PRESET_FACTORY) {
    const p = document.getElementById('og_party');
    if (p) p.value = OG_PRESET_FACTORY;
    OG_PRESET_FACTORY = null;
    outKindUI('bill');
  }
};

VIEWS.workers = async el => {
  await loadBase();
  const payouts = await get('/api/payouts').catch(() => []);
  PO_CACHE = payouts; EDIT_W = null; EDIT_PO = null;
  el.innerHTML = `${accHead('workers','list','👷',t('workers'),t('accd_workers'),'list')}<div class="card">
   <div class="row"><div class="field"><label>${t('name_l')} *</label><input id="w_name"></div>
   <div class="field"><label>${t('type_l')}</label><select id="w_kind"><option value="theka">${t('theka_l')}</option><option value="salary">${t('salary_l')}</option></select></div>
   <div class="field"><label>${t('rate_ton_out')}</label><input id="w_rt" type="number"></div>
   <div class="field"><label>${t('rate_bag')}</label><input id="w_rb" type="number"></div>
   <div class="field"><label>${t('monthly_salary')}</label><input id="w_sal" type="number"></div></div>
   <div class="row"><div class="field"><label>${t('phone_l')}</label><input id="w_phone"></div>
   <div class="field"><label>${t('departments')}</label><select id="w_dept"><option value="">—</option>${deptOpts()}</select></div>
   <div class="field"><label>${t('device_code')}</label><input id="w_code"></div>
   <div class="field"><label>${t('start_date')}</label><input id="w_start" type="date" value="${todayStr()}"></div></div>
   <p id="w_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="w_save" onclick="addWorker()">${t('add')}</button> <button id="w_cancel" class="ghost" style="display:none" onclick="cancelWorkerEdit()">${t('cancel_l')}</button></div>
  <div class="card">${xlBar('workers')}<div class="wrap"><table><tr><th>${t('worker')}</th><th>${t('type_l')}</th><th>${t('departments')}</th><th class="num">${t('earned_l')}</th><th class="num">${t('taken_l')}</th><th class="num">${t('due_l')}</th><th></th></tr>
   ${CACHE.workers.map(w => `<tr><td><b>${esc(w.name)}</b><br><span class="muted small">${t('code_l')}: ${esc(w.device_code || '-')} · ${esc(w.phone || '')}</span></td>
   <td>${w.kind}${w.kind === 'theka' ? `<br><span class="small muted">${fmtN(w.rate_per_ton)}/t · ${fmtN(w.rate_per_bag)}/bag</span>` : `<br><span class="small muted">${fmt(w.monthly_salary)}/mo</span>`}</td>
   <td>${esc(w.department_name || '')}</td><td class="num">${fmt(w.earned)}</td><td class="num">${fmt(w.paid)}</td><td class="num"><b>${fmt(w.due)}</b></td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editWorker(${w.id})">${t('edit')}</button>` : ''} ${delBtn('workers', w.id)}</td></tr>`).join('')}</table></div>
   <p class="small muted">${t('theka_note')}</p></div>${accEnd()}
  ${accHead('workers','payouts','💰',t('payout_t'),t('accd_payouts'))}<div class="card">
   <div class="row"><div class="field"><label>${t('worker')}</label><select id="po_worker">${workerOpts()}</select></div>
   <div class="field"><label>${t('date')}</label><input id="po_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('amount')} *</label><input id="po_amt" type="number"></div>
   <div class="field"><label>${t('type_l')}</label><select id="po_kind"><option value="payment">${t('payment_l')}</option><option value="advance">${t('advance_l')}</option></select></div>
   <div class="field"><label>${t('method')}</label><select id="po_method"><option value="cash">${t('cash')}</option><option value="bank">${t('bank')}</option><option value="online">${t('online')}</option></select></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button id="po_save" onclick="addPayout()">${t('save')}</button></div></div>
   <p id="po_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="po_cancel" class="ghost" style="display:none" onclick="cancelPayoutEdit()">${t('cancel_l')}</button>
   <div class="wrap" style="margin-top:10px"><table><tr><th>${t('date')}</th><th>${t('worker')}</th><th>${t('type_l')}</th><th class="num">${t('amount')}</th><th>${t('method')}</th><th></th></tr>
   ${payouts.slice(0, 60).map(p => `<tr><td>${p.date}</td><td>${esc(p.worker_name || '')}</td><td>${esc(p.kind || '')}</td><td class="num">${fmt(p.amount)}</td><td>${esc(p.method || '')}</td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editPayout(${p.id})">${t('edit')}</button>` : ''} ${delBtn('worker_payouts', p.id)}</td></tr>`).join('') || `<tr><td colspan="6" class="muted">—</td></tr>`}</table></div></div>${accEnd()}`;
};
window.addWorker = async () => {
  if (!reqCheck([['w_name', 'fl_name', 'text']])) return;
  try { await post('/api/workers', { name: val('w_name'), kind: val('w_kind'), rate_per_ton: num('w_rt'), rate_per_bag: num('w_rb'),
    monthly_salary: num('w_sal'), phone: val('w_phone'), department_id: val('w_dept') || null, device_code: val('w_code'), start_date: val('w_start') });
    okPopup(t('worker_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.addPayout = async () => {
  try { await post('/api/payouts', { worker_id: val('po_worker'), date: val('po_date'), amount: num('po_amt'), kind: val('po_kind'), method: val('po_method') });
    okPopup(t('payout_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.editWorker = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = CACHE.workers.find(x => x.id === id); if (!r) return;
  EDIT_W = id;
  $('#w_name').value = r.name || '';
  $('#w_kind').value = r.kind || 'theka';
  $('#w_rt').value = r.rate_per_ton || '';
  $('#w_rb').value = r.rate_per_bag || '';
  $('#w_sal').value = r.monthly_salary || '';
  $('#w_phone').value = r.phone || '';
  $('#w_dept').value = r.department_id || '';
  $('#w_code').value = r.device_code || '';
  $('#w_start').value = r.start_date || todayStr();
  editSwap('w_save', 'updateWorker()', 'w_cancel', 'w_editing');
};
window.updateWorker = async () => {
  if (!reqCheck([['w_name', 'fl_name', 'text']])) return;
  try { await post('/api/workers', { id: EDIT_W, name: val('w_name'), kind: val('w_kind'), rate_per_ton: num('w_rt'), rate_per_bag: num('w_rb'),
    monthly_salary: num('w_sal'), phone: val('w_phone'), department_id: val('w_dept') || null, device_code: val('w_code'), start_date: val('w_start') });
    EDIT_W = null; okPopup(t('worker_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.cancelWorkerEdit = () => { EDIT_W = null; render(); };
window.editPayout = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = PO_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_PO = id;
  $('#po_worker').value = r.worker_id || '';
  $('#po_date').value = r.date || todayStr();
  $('#po_amt').value = r.amount || '';
  $('#po_kind').value = r.kind || 'payment';
  $('#po_method').value = r.method || 'cash';
  editSwap('po_save', 'updatePayout()', 'po_cancel', 'po_editing');
};
window.updatePayout = async () => {
  try { await post('/api/payouts', { id: EDIT_PO, worker_id: val('po_worker'), date: val('po_date'), amount: num('po_amt'), kind: val('po_kind'), method: val('po_method') });
    EDIT_PO = null; okPopup(t('payout_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.cancelPayoutEdit = () => { EDIT_PO = null; render(); };

VIEWS.departments = async el => {
  await loadBase();
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  el.innerHTML = `<div class="card"><h2>🏢 ${t('departments')}</h2>
   <div class="row"><div class="field"><label>${t('name_l')} *</label><input id="dp_name" placeholder="e.g. Grinding / Packing / Office"></div>
   <div class="field"><label>${t('checkin')}</label><input id="dp_in" type="time" value="08:00"></div>
   <div class="field"><label>${t('checkout')}</label><input id="dp_out" type="time" value="17:00"></div>
   <div class="field"><label>${t('ot_rate')}</label><input id="dp_otrate" type="number"></div></div>
   <div class="field"><label>${t('off_days')}</label><div>${days.map((d, i) => `<label style="display:inline-block;margin-inline-end:10px"><input type="checkbox" class="dp_off" value="${i}" ${i === 6 ? 'checked' : ''}> ${d}</label>`).join('')}</div></div>
   <div class="field"><label style="display:inline-block"><input type="checkbox" id="dp_ot" checked> ${t('ot_allowed')}</label></div>
   <p id="dp_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="dp_save" onclick="addDept()">${t('add')}</button> <button id="dp_cancel" class="ghost" style="display:none" onclick="cancelDeptEdit()">${t('cancel_l')}</button></div>
  <div class="card"><div class="wrap"><table><tr><th>${t('name_l')}</th><th>${t('shift_t2')}</th><th>${t('off_days')}</th><th>OT</th><th></th></tr>
   ${CACHE.departments.map(d => `<tr><td><b>${esc(d.name)}</b></td><td>${d.in_time} – ${d.out_time}</td>
   <td>${String(d.off_days || '').split(',').filter(x => x !== '').map(i => days[+i]).join(', ')}</td>
   <td>${d.overtime_allowed ? '✓ @ ' + fmtN(d.overtime_rate) + '/h' : '—'}</td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editDept(${d.id})">${t('edit')}</button>` : ''} ${delBtn('departments', d.id)}</td></tr>`).join('')}</table></div>
   <p class="small muted">${t('dept_note')}</p></div>`;
};
window.addDept = async () => {
  const off = [...document.querySelectorAll('.dp_off:checked')].map(x => +x.value);
  if (!reqCheck([['dp_name', 'fl_name', 'text']])) return;
  try { await post('/api/departments', { name: val('dp_name'), in_time: val('dp_in'), out_time: val('dp_out'),
    off_days: off, overtime_allowed: chk('dp_ot'), overtime_rate: num('dp_otrate') }); okPopup(t('dept_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.editDept = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = CACHE.departments.find(x => x.id === id); if (!r) return;
  EDIT_DEPT = id;
  $('#dp_name').value = r.name || '';
  $('#dp_in').value = r.in_time || '08:00';
  $('#dp_out').value = r.out_time || '17:00';
  $('#dp_otrate').value = r.overtime_rate || '';
  const off = String(r.off_days || '').split(',').filter(x => x !== '');
  document.querySelectorAll('.dp_off').forEach(cb => { cb.checked = off.includes(cb.value); });
  $('#dp_ot').checked = !!r.overtime_allowed;
  editSwap('dp_save', 'updateDept()', 'dp_cancel', 'dp_editing');
};
window.updateDept = async () => {
  const off = [...document.querySelectorAll('.dp_off:checked')].map(x => +x.value);
  if (!reqCheck([['dp_name', 'fl_name', 'text']])) return;
  try { await post('/api/departments/update', { id: EDIT_DEPT, name: val('dp_name'), in_time: val('dp_in'), out_time: val('dp_out'),
    off_days: off, overtime_allowed: chk('dp_ot'), overtime_rate: num('dp_otrate') }); EDIT_DEPT = null; okPopup(t('dept_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.cancelDeptEdit = () => { EDIT_DEPT = null; render(); };

VIEWS.attendance = async el => {
  await loadBase();
  const rows = await get('/api/attendance');
  const devices = await get('/api/devices');
  const punches = await get('/api/punches');
  const addr = STATE.lan_ip && STATE.device_port ? `http://${STATE.lan_ip}:${STATE.device_port}/iclock/cdata` : '';
  el.innerHTML = `${accHead('attendance','manual','🗓',t('att_manual'),t('accd_att_manual'),'manual')}<div class="card">
   <div class="row"><div class="field"><label>${t('worker')}</label><select id="at_worker">${workerOpts()}</select></div>
   <div class="field"><label>${t('date')}</label><input id="at_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('checkin')}</label><input id="at_in" type="time"></div>
   <div class="field"><label>${t('checkout')}</label><input id="at_out" type="time"></div>
   <div class="field"><label>${t('overtime')} ${t('hours')} ${t('ot_auto')}</label><input id="at_ot" type="number" step="0.25"></div>
   <div class="field"><label style="display:inline-block;margin-top:18px"><input type="checkbox" id="at_present" checked> ${t('present')}</label></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="addAttendance()">${t('save')}</button></div></div></div>${accEnd()}
  ${accHead('attendance','bio','🔐',t('bio_t'),t('accd_bio'))}<div class="card">
   <p class="small">${t('bio_note')}<br><b>${addr || ''}</b></p>
   <div class="row"><div class="field"><label>${t('machine_name_l')}</label><input id="dv_name"></div>
   <div class="field"><label>${t('serial_l')} *</label><input id="dv_serial"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="addDevice()">${t('add')}</button></div></div>
   <div class="wrap"><table><tr><th>${t('machine_l')}</th><th>Serial</th><th>${t('last_seen')}</th><th>${t('last_punch')}</th><th></th></tr>
   ${devices.map(d => `<tr><td>${esc(d.name)}</td><td>${esc(d.serial)}</td><td>${esc(d.last_seen || '-')}</td><td>${esc(d.last_punch || '-')}</td><td>${delBtn('biometric_devices', d.id)}</td></tr>`).join('')}</table></div>
   <h3>${t('csv_t')}</h3>
   <p class="small muted">${t('csv_note')}</p>
   <textarea id="bio_csv" rows="4" placeholder="device_code,date,time&#10;101,${todayStr()},08:05"></textarea>
   <button class="small" onclick="importBio()">${t('import_punches')}</button>
   <h3>${t('last_punches')}</h3>
   <div class="wrap"><table>${punches.slice(0, 15).map(p => `<tr><td>${t('code_l')} ${esc(p.device_code)}</td><td>${esc(p.punch_time)}</td><td class="small muted">${esc(p.device_serial || '')}</td></tr>`).join('') || '<tr><td class="muted">—</td></tr>'}</table></div></div>${accEnd()}
  ${accHead('attendance','register','📋',t('acc_register'),t('accd_records'))}<div class="card"><div class="wrap"><table><tr><th>${t('date')}</th><th>${t('worker')}</th><th>${t('present')}</th><th>${t('checkin')}</th><th>${t('checkout')}</th><th>${t('overtime')} h</th><th></th></tr>
   ${rows.slice(0, 80).map(r => `<tr><td>${r.date}</td><td>${esc(r.worker_name || '')}</td><td>${r.present ? '✓' : '—'}</td><td>${esc(r.check_in || '')}</td><td>${esc(r.check_out || '')}</td><td>${r.overtime_hours || 0}</td><td>${delBtn('attendance', r.id)}</td></tr>`).join('')}</table></div></div>${accEnd()}`;
};
window.addAttendance = async () => {
  try { const r = await post('/api/attendance', { worker_id: val('at_worker'), date: val('at_date'), present: chk('at_present'),
    check_in: val('at_in'), check_out: val('at_out'), overtime_hours: val('at_ot') });
    okPopup(t('att_saved') + ' ' + r.overtime_hours + ' h'); render(); } catch (e) { msg(e.message, 'err'); }
};
window.addDevice = async () => {
  try { const r = await post('/api/devices', { name: val('dv_name'), serial: val('dv_serial') }); okPopup(t('machine_reg') + ' ' + r.address); render(); } catch (e) { msg(e.message, 'err'); }
};
window.importBio = async () => {
  try { const r = await post('/api/bio/import', { csv: val('bio_csv') }); okPopup(t('import_done') + ' ✓ ' + r.imported + ' ' + t('import_punches_done') + ' ' + r.skipped + ' ' + t('skip_l')); render(); } catch (e) { msg(e.message, 'err'); }
};

VIEWS.leaves = async el => {
  await loadBase();
  const leaves = await get('/api/leaves');
  const appr = await get('/api/approvals');
  const isOwner = STATE.user.role === 'owner';
  el.innerHTML = `${accHead('leaves','leave','🌴',t('leave_t'),t('accd_leave'),'leave')}<div class="card">
   <div class="row"><div class="field"><label>${t('worker')}</label><select id="lv_worker">${workerOpts()}</select></div>
   <div class="field"><label>${t('from_l')}</label><input id="lv_from" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('to_l')}</label><input id="lv_to" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('type_l')}</label><select id="lv_kind"><option value="paid">Paid</option><option value="unpaid">Unpaid</option></select></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="addLeave()">${t('add')}</button></div></div>
   <div class="wrap"><table><tr><th>${t('worker')}</th><th>${t('from_l')} – ${t('to_l')}</th><th>${t('type_l')}</th><th>${t('status')}</th><th></th></tr>
   ${leaves.map(l => `<tr><td>${esc(l.worker_name || '')}</td><td>${l.from_date} – ${l.to_date}</td><td>${l.kind}</td><td>${l.status}</td>
   <td>${l.status === 'pending' && isOwner ? `<button class="small" onclick="decideLeave(${l.id},'approved')">✓ ${t('approve')}</button> <button class="small danger" onclick="decideLeave(${l.id},'rejected')">✗</button>` : ''}</td></tr>`).join('')}</table></div>
   <p class="small muted">${t('leave_note')}</p></div>${accEnd()}
  ${accHead('leaves','approvals','✅',t('approvals_t'),t('accd_approvals'))}<div class="card">
   <div class="row"><div class="field"><label>${t('type_l')}</label><select id="ap_type"><option value="overtime">Overtime</option><option value="att_correction">Attendance correction</option></select></div>
   <div class="field"><label>${t('worker')}</label><select id="ap_worker">${workerOpts()}</select></div>
   <div class="field"><label>${t('date')}</label><input id="ap_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('hours')} (overtime)</label><input id="ap_hours" type="number" step="0.25"></div>
   <div class="field"><label>${t('checkin')} (correction)</label><input id="ap_in" type="time"></div>
   <div class="field"><label>${t('checkout')} (correction)</label><input id="ap_out" type="time"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="addApproval()">${t('send_request')}</button></div></div>
   <div class="wrap"><table><tr><th>${t('type_l')}</th><th>${t('detail_l')}</th><th>By</th><th>${t('status')}</th><th></th></tr>
   ${appr.map(a => `<tr><td>${a.type}</td><td class="small">${esc(a.payload)}</td><td>${esc(a.requested_by)}</td><td>${a.status}</td>
   <td>${a.status === 'pending' && isOwner ? `<button class="small" onclick="decideAppr(${a.id},'approved')">✓</button> <button class="small danger" onclick="decideAppr(${a.id},'rejected')">✗</button>` : ''}</td></tr>`).join('')}</table></div></div>${accEnd()}`;
};
window.addLeave = async () => { await post('/api/leaves', { worker_id: val('lv_worker'), from_date: val('lv_from'), to_date: val('lv_to'), kind: val('lv_kind') }); okPopup(t('leave_saved')); render(); };
window.decideLeave = async (id, s) => { try { await post('/api/leaves/decide', { id, status: s }); okPopup(t('leave_done') + ' ' + s + ' ✓'); render(); } catch (e) { msg(e.message, 'err'); } };
window.addApproval = async () => {
  const type = val('ap_type');
  const payload = type === 'overtime'
    ? { worker_id: +val('ap_worker'), date: val('ap_date'), hours: num('ap_hours') }
    : { worker_id: +val('ap_worker'), date: val('ap_date'), check_in: val('ap_in'), check_out: val('ap_out'), present: true };
  await post('/api/approvals', { type, payload }); okPopup(t('request_sent')); render();
};
window.decideAppr = async (id, s) => { try { await post('/api/approvals/decide', { id, status: s }); okPopup(t('request_done') + ' ' + s + ' ✓'); render(); } catch (e) { msg(e.message, 'err'); } };

VIEWS.payments = async el => {
  await loadBase();
  const rows = await get('/api/payments');
  PAY_CACHE = rows; EDIT_PAY = null;
  const st = CACHE.settings || await get('/api/settings').catch(() => null); CACHE.settings = st;
  const banks = (st && st.banks) || [];
  el.innerHTML = `<div class="card"><h2>💰 ${t('payments')} <button class="small voicebtn" onclick="voiceFill('payment')">${t('voice')}</button></h2>
   <div class="row"><div class="field"><label>${t('date')}</label><input id="pay_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('party')}</label><select id="pay_party">${partyOpts()}</select></div>
   <div class="field"><label>${t('direction')}</label><select id="pay_dir"><option value="in">IN — ${t('to_receive')}</option><option value="out">OUT — ${t('to_pay')}</option></select></div>
   <div class="field"><label>${t('amount')} *</label><input id="pay_amount" type="number"></div>
   <div class="field"><label>${t('method')}</label><select id="pay_method" onchange="payMethodUI()">
     <option value="cash">${t('cash')}</option><option value="bank">${t('bank')}</option><option value="online">${t('online')}</option><option value="cheque">${t('cheque')}</option></select></div></div>
   <div class="row" id="pay_bank_row" style="display:none"><div class="field"><label>${t('bank')}</label>
     <select id="pay_bank">${banks.map(b => `<option>${esc(b)}</option>`).join('')}</select><input id="pay_bank_free"></div>
   <div class="field" id="pay_online_row"><label>${t('channel_l')}</label><select id="pay_online"><option>JazzCash</option><option>Easypaisa</option><option>Raast</option></select></div>
   <div class="field"><label>Ref No</label><input id="pay_ref"></div></div>
   <div class="row" id="pay_chq_row" style="display:none"><div class="field"><label>${t('cheque_no')}</label><input id="pay_chqno"></div>
   <div class="field"><label>${t('due_date')}</label><input id="pay_due" type="date"></div></div>
   <div class="field"><label>${t('note')}</label><input id="pay_note"></div>
   ${attachHTML('payments', 0)}
   <p id="pay_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="pay_save" onclick="addPayment()">${t('save')}</button> <button id="pay_cancel" class="ghost" style="display:none" onclick="cancelPaymentEdit()">${t('cancel_l')}</button></div>
  <div class="card">${xlBar('payments')}<div class="wrap"><table><tr><th>${t('date')}</th><th>${t('party')}</th><th></th><th class="num">${t('amount')}</th><th>${t('method')}</th><th>${t('note')}</th><th></th></tr>
   ${rows.slice(0, 80).map(r => `<tr><td>${r.date}</td><td>${esc(r.party_name)}</td><td>${r.direction}</td><td class="num">${fmt(r.amount)}</td>
   <td>${r.method}${r.bank_name ? ' · ' + esc(r.bank_name) : ''}${r.online_channel ? ' · ' + esc(r.online_channel) : ''}${r.ref_no ? ' · Ref ' + esc(r.ref_no) : ''}</td><td>${esc(r.note || '')}</td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editPayment(${r.id})">${t('edit')}</button>` : ''} ${delBtn('payments', r.id)}</td></tr>`).join('')}</table></div></div>`;
};
window.payMethodUI = () => {
  const m = val('pay_method');
  $('#pay_bank_row').style.display = (m === 'bank' || m === 'cheque' || m === 'online') ? '' : 'none';
  $('#pay_chq_row').style.display = m === 'cheque' ? '' : 'none';
};
window.addPayment = async () => {
  try {
    if (!reqCheck([['pay_party', 'fl_party', 'text'], ['pay_amount', 'fl_amount', 'pos']])) return;
    if (val('pay_method') === 'cheque' && !reqCheck([['pay_due', 'fl_due', 'text']])) return;
    const r = await post('/api/payments', { date: val('pay_date'), party_id: val('pay_party'), direction: val('pay_dir'),
      amount: num('pay_amount'), method: val('pay_method'), bank_name: val('pay_bank_free') || val('pay_bank'),
      online_channel: val('pay_online'), ref_no: val('pay_ref'), cheque_no: val('pay_chqno'), due_date: val('pay_due'), note: val('pay_note') });
    const aid = await uploadAttachment('payments', r.id);
    okPopup(t('payment_saved') + (aid ? ' ' + t('proof_attached2') : '')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.editPayment = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = PAY_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_PAY = id;
  $('#pay_date').value = r.date || todayStr();
  $('#pay_party').value = r.party_id || '';
  $('#pay_dir').value = r.direction || 'in';
  $('#pay_amount').value = r.amount || '';
  $('#pay_method').value = r.method || 'cash';
  payMethodUI();
  $('#pay_bank_free').value = r.bank_name || '';
  $('#pay_online').value = r.online_channel || 'JazzCash';
  $('#pay_ref').value = r.ref_no || '';
  $('#pay_chqno').value = r.cheque_no || '';
  $('#pay_due').value = r.due_date || '';
  $('#pay_note').value = r.note || '';
  editSwap('pay_save', 'updatePayment()', 'pay_cancel', 'pay_editing');
};
window.updatePayment = async () => {
  try {
    if (val('pay_method') === 'cheque' && !reqCheck([['pay_due', 'fl_due', 'text']])) return;
    const r = await post('/api/payments', { id: EDIT_PAY, date: val('pay_date'), party_id: val('pay_party'), direction: val('pay_dir'),
      amount: num('pay_amount'), method: val('pay_method'), bank_name: val('pay_bank_free') || val('pay_bank'),
      online_channel: val('pay_online'), ref_no: val('pay_ref'), cheque_no: val('pay_chqno'), due_date: val('pay_due'), note: val('pay_note') });
    const aid = await uploadAttachment('payments', r.id);
    EDIT_PAY = null;
    okPopup(t('payment_saved') + (aid ? ' ' + t('proof_attached2') : '')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.cancelPaymentEdit = () => { EDIT_PAY = null; render(); };

VIEWS.expenses = async el => {
  await loadBase();
  const rows = await get('/api/expenses');
  EX_CACHE = rows; EDIT_EX = null;
  const rep2 = await get('/api/expense-report');
  const st = await get('/api/settings').catch(() => null);
  const banks = (st && st.banks) || [];
  const mains = CACHE.heads.filter(h => !h.parent_id);
  const pend = rows.filter(r => r.status === 'pending');
  EX_PAID = 'owner';
  el.innerHTML = `${(STATE.user.role === 'owner' && pend.length) ? `<div class="card" style="border:2px solid #e0a800"><h2>⏳ ${t('pend_exp_t')} (${pend.length})</h2>
   ${pend.map(r => `<div class="kv"><span>${r.date} · ${esc(r.head_name || '')} · ${paidDisp(r)} → ${esc(r.paid_to || '')}</span><span><b>${fmt(r.amount)}</b>
   <button class="small" onclick="exStatus(${r.id},'approved')">✓ ${t('approve')}</button>
   <button class="small danger" onclick="exStatus(${r.id},'rejected')">✗ ${t('reject')}</button></span></div>`).join('')}
   <p class="small muted">${t('expense_ledger_note')}</p></div>` : ''}
  ${accHead('expenses','entry','🧾',t('expenses'),t('accd_expense_entry'),'entry')}<div class="card"><div style="text-align:end;margin-bottom:4px"><button class="small voicebtn" onclick="voiceFill('expense')">${t('voice')}</button></div>
   <div class="row"><div class="field"><label>${t('date')}</label><input id="ex_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('main_head')}</label><select id="ex_head" onchange="subHeadUI()"><option value="">—</option>${headOpts()}</select></div>
   <div class="field"><label>${t('sub_head')}</label><select id="ex_sub"><option value="">—</option></select></div>
   <div class="field"><label>${t('amount')} *</label><input id="ex_amount" type="number"></div></div>
   <div class="row"><div class="field"><label>${t('paid_by_l')}</label>
   <div class="seg"><button type="button" id="pb_owner" class="segbtn on" onclick="exPaidUI('owner')">Owner</button><button type="button" id="pb_manager" class="segbtn" onclick="exPaidUI('manager')">Manager</button><button type="button" id="pb_other" class="segbtn" onclick="exPaidUI('other')">Other</button></div></div>
   <div class="field" id="ex_pb_manager" style="display:none"><label>Manager / Staff</label><select id="ex_holder">${(CACHE.holders || []).map(h => `<option value="${h.id}">${esc(h.username)} (${esc(h.role)})</option>`).join('')}</select></div>
   <div class="field" id="ex_pb_other" style="display:none"><label>${t('name_l')}</label><input id="ex_pbname"></div>
   <div class="field"><label>${t('paid_to_l')}</label><input id="ex_to"></div></div>
   <div class="row"><div class="field"><label>${t('method')}</label><select id="ex_method" onchange="exMethodUI()"><option value="cash">${t('cash')}</option><option value="bank">${t('bank')}</option><option value="online">${t('online')}</option></select></div>
   <div class="field" id="ex_ch_bank" style="display:none"><label>${t('bank')}</label><select id="ex_bank"><option value="">—</option>${banks.map(b => `<option>${esc(b)}</option>`).join('')}</select><input id="ex_bank_free" style="margin-top:4px"></div>
   <div class="field" id="ex_ch_online" style="display:none"><label>${t('channel_l')}</label><select id="ex_channel"><option>JazzCash</option><option>Easypaisa</option><option>Raast</option></select></div>
   <div class="field" id="ex_refwrap" style="display:none"><label id="ex_ref_label">Ref No</label><input id="ex_ref"></div>
   <div class="field"><label>${t('note')}</label><input id="ex_note"></div></div>
   ${attachHTML('expenses', 0)}
   <p id="ex_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="ex_save" onclick="addExpense()">${t('save')}</button> <button id="ex_cancel" class="ghost" style="display:none" onclick="cancelExpenseEdit()">${t('cancel_l')}</button>
   <h3>${t('head_new')}</h3>
   <div class="row"><div class="field"><label>${t('head_name')}</label><input id="hd_name"></div>
   <div class="field"><label>${t('head_parent')}</label><select id="hd_parent"><option value="">— ${t('main_head')} —</option>${mains.map(h => `<option value="${h.id}">${esc(h.name)}</option>`).join('')}</select></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button class="ghost" onclick="addHead()">${t('head_add')}</button></div></div></div>${accEnd()}
  ${accHead('expenses','summary','📊',t('month_headwise'),t('accd_expense_summary'))}<div class="card">
   ${Object.entries(rep2.by_head).map(([h, subs]) => `<div class="kv"><span><b>${esc(h)}</b></span><span>${Object.entries(subs).map(([sv, v]) => `${esc(sv)}: ${fmt(v)}`).join(' · ')}</span></div>`).join('') || '<span class="muted">—</span>'}
   <h3>${t('paidto_wise')}</h3>${rep2.by_paid_to.map(r => `<div class="kv"><span>${esc(r.paid_to)}</span><b>${fmt(r.total)}</b></div>`).join('') || '<span class="muted">—</span>'}</div>${accEnd()}
  ${accHead('expenses','daycosts','⛽',t('day_costs'),t('accd_daycosts'))}<div class="card">
   <div class="row"><div class="field"><label>${t('day_costs')} — ${t('diesel_l')}</label><input id="dc_diesel" type="number" step="0.1"></div>
   <div class="field"><label>${t('elec_l')}</label><input id="dc_elec" type="number" step="0.1"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button class="ghost" onclick="addDayCosts()">${t('day_cost_save')}</button></div></div>
   <p class="small muted">${t('maint_note')}</p></div>${accEnd()}
  ${accHead('expenses','ledger','📋',t('entries_l'),t('accd_records'))}<div class="card">${xlBar('expenses')}<div class="wrap"><table><tr><th>${t('date')}</th><th>Head</th><th class="num">${t('amount')}</th><th>${t('paid_by_l')}</th><th>${t('paid_to_l')}</th><th>${t('method')}</th><th>${t('status')}</th><th></th></tr>
   ${rows.slice(0, 80).map(r => `<tr><td>${r.date}</td><td>${esc(r.head_name)}${r.sub_name ? ' / ' + esc(r.sub_name) : ''}</td><td class="num">${fmt(r.amount)}</td>
   <td>${esc(paidDisp(r))}</td><td>${esc(r.paid_to || '')}</td>
   <td>${esc(r.method || '')}${r.pay_channel ? ' · ' + esc(r.pay_channel) : ''}${r.pay_ref ? ' · Ref ' + esc(r.pay_ref) : ''}</td>
   <td>${r.status === 'pending' ? `<span class="badge-pend">⏳ ${t('pending')}</span>` : (r.status === 'rejected' ? `<span class="badge-rej">✗ ${t('rejected')}</span>` : '✓')}${(r.status === 'pending' && STATE.user.role === 'owner') ? ` <button class="small" onclick="exStatus(${r.id},'approved')">✓</button><button class="small danger" onclick="exStatus(${r.id},'rejected')">✗</button>` : ''}</td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editExpense(${r.id})">${t('edit')}</button>` : ''} ${delBtn('expenses', r.id)}</td></tr>`).join('')}</table></div></div>${accEnd()}`;
};
window.subHeadUI = () => { $('#ex_sub').innerHTML = '<option value="">—</option>' + headOpts('', val('ex_head')); };
let EX_PAID = 'owner';
window.paidDisp = r => { if (r.paid_kind === 'owner') return 'Owner'; if (r.paid_kind === 'manager') return 'Manager: ' + (r.paid_by || ''); return 'Other: ' + (r.paid_by || ''); };
window.exPaidUI = k => { EX_PAID = k;
  ['owner', 'manager', 'other'].forEach(x => { const b = $('#pb_' + x); if (b) b.classList.toggle('on', x === k); });
  const m = $('#ex_pb_manager'), o = $('#ex_pb_other');
  if (m) m.style.display = k === 'manager' ? '' : 'none';
  if (o) o.style.display = k === 'other' ? '' : 'none'; };
window.exMethodUI = () => { const m = val('ex_method');
  const b = $('#ex_ch_bank'), o = $('#ex_ch_online'), rf = $('#ex_refwrap'), lb = $('#ex_ref_label');
  if (b) b.style.display = m === 'bank' ? '' : 'none';
  if (o) o.style.display = m === 'online' ? '' : 'none';
  if (rf) rf.style.display = m === 'cash' ? 'none' : '';
  if (lb) lb.textContent = 'Ref No'; };
window.exStatus = async (id, s) => { try { await post('/api/expenses/status', { id, status: s });
  okPopup(s === 'approved' ? t('expense_approved') + ' ✓' : t('expense_rejected')); render(); } catch (e) { msg(e.message, 'err'); } };
window.addHead = async () => { await post('/api/heads', { name: val('hd_name'), parent_id: val('hd_parent') || null }); okPopup(t('head_saved')); render(); };
window.addExpense = async () => {
  try {
    const m = val('ex_method');
    if (!reqCheck([['ex_amount', 'fl_amount', 'pos'], ['ex_head', 'fl_head', 'text']])) return;
    const r = await post('/api/expenses', { date: val('ex_date'), head_id: val('ex_head') || null, sub_head_id: val('ex_sub') || null,
      amount: num('ex_amount'), paid_to: val('ex_to'), method: m, note: val('ex_note'),
      paid_kind: EX_PAID,
      paid_by_holder: EX_PAID === 'manager' ? ('user:' + val('ex_holder')) : '',
      paid_name: EX_PAID === 'other' ? val('ex_pbname') : '',
      pay_channel: m === 'bank' ? (val('ex_bank') || val('ex_bank_free')) : (m === 'online' ? val('ex_channel') : ''),
      pay_ref: m === 'cash' ? '' : val('ex_ref') });
    const aid = await uploadAttachment('expenses', r.id);
    let text = t('expense_saved') + (aid ? ' ' + t('bill_attached') : '');
    if (r.status === 'pending') text += ' — ⏳ ' + t('approval_pending');
    if (r.warning) text += ' — ⚠ ' + r.warning;
    okPopup(text); render();
    if (r.warning) msg(r.warning, 'warn');
  } catch (e) { msg(e.message, 'err'); }
};
window.editExpense = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = EX_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_EX = id;
  $('#ex_date').value = r.date || todayStr();
  $('#ex_head').value = r.head_id || '';
  subHeadUI();
  $('#ex_sub').value = r.sub_head_id || '';
  $('#ex_amount').value = r.amount || '';
  exPaidUI(r.paid_kind || 'owner');
  if (r.paid_kind === 'manager' && (r.paid_by_holder || '').startsWith('user:')) $('#ex_holder').value = r.paid_by_holder.slice(5);
  if (r.paid_kind === 'other') $('#ex_pbname').value = r.paid_by || '';
  $('#ex_to').value = r.paid_to || '';
  $('#ex_method').value = r.method || 'cash';
  exMethodUI();
  if (r.method === 'bank') { const b = $('#ex_bank'); if ([...b.options].some(o => o.value === r.pay_channel)) b.value = r.pay_channel; else $('#ex_bank_free').value = r.pay_channel || ''; }
  if (r.method === 'online') $('#ex_channel').value = r.pay_channel || 'JazzCash';
  $('#ex_ref').value = r.pay_ref || '';
  $('#ex_note').value = r.note || '';
  editSwap('ex_save', 'updateExpense()', 'ex_cancel', 'ex_editing');
  accOpen('expenses', 'entry');   // the edit form lives in the Expense Entry section
};
window.updateExpense = async () => {
  try {
    const m = val('ex_method');
    if (!reqCheck([['ex_amount', 'fl_amount', 'pos'], ['ex_head', 'fl_head', 'text']])) return;
    const r = await post('/api/expenses', { id: EDIT_EX, date: val('ex_date'), head_id: val('ex_head') || null, sub_head_id: val('ex_sub') || null,
      amount: num('ex_amount'), paid_to: val('ex_to'), method: m, note: val('ex_note'),
      paid_kind: EX_PAID,
      paid_by_holder: EX_PAID === 'manager' ? ('user:' + val('ex_holder')) : '',
      paid_name: EX_PAID === 'other' ? val('ex_pbname') : '',
      pay_channel: m === 'bank' ? (val('ex_bank') || val('ex_bank_free')) : (m === 'online' ? val('ex_channel') : ''),
      pay_ref: m === 'cash' ? '' : val('ex_ref') });
    const aid = await uploadAttachment('expenses', r.id);
    EDIT_EX = null;
    okPopup(t('expense_saved') + (aid ? ' ' + t('bill_attached') : '')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.cancelExpenseEdit = () => { EDIT_EX = null; render(); };
window.addDayCosts = async () => { await post('/api/day-costs', { date: todayStr(), diesel_litres: num('dc_diesel'), elec_units: num('dc_elec') }); okPopup(t('daycost_saved')); };

VIEWS.cashbook = async el => {
  const c = await get('/api/cashbook?date=' + todayStr());
  const de = await get('/api/dayend?date=' + todayStr());
  const bb = await get('/api/bankbook').catch(() => ({ banks: [] }));
  el.innerHTML = `${accHead('cashbook','cashbook','📖',t('cashbook') + ' — ' + c.date,t('accd_cashbook'),'cashbook')}<div class="card">
   <div class="wrap"><table><tr><th>${t('method')}</th><th class="num">IN</th><th class="num">OUT</th></tr>
   ${['cash', 'bank', 'online', 'cheque'].map(k => `<tr><td>${t(k) || k}</td><td class="num">${fmt(c.methods[k].in)}</td><td class="num">${fmt(c.methods[k].out)}</td></tr>`).join('')}
   <tr><td><b>${t('total_net')}</b></td><td class="num" colspan="2"><b>${fmt(c.total)}</b></td></tr></table></div></div>${accEnd()}
  ${accHead('cashbook','dayend','🌙',t('dayend_t') + ' — ' + de.date,t('accd_dayend'))}<div class="card">
   <div class="kv"><span>${t('vehicles_l')}</span><b>${de.trips} (IN ${tonsDisp(de.rock_in_t)} · OUT ${tonsDisp(de.powder_out_t)})</b></div>
   <div class="kv"><span>${t('ground_bags')}</span><b>${tonsDisp(de.ground_t)} · ${de.bags} ${t('bags')}</b></div>
   <div class="kv"><span>${t('day_l')} / ${t('night_l')} ${t('bags')}</span><b>${de.bags_day || 0} / ${de.bags_night || 0}${de.bags_unclassified ? ' (+' + de.bags_unclassified + ' ' + t('unspec_l') + ')' : ''}</b></div>
   ${(de.shift_closures || []).map(x => `<div class="kv"><span>🏭 ${t('closed_l')} — ${x.shift === 'Night' ? t('night_l') : t('day_l')}</span><b>${x.reason === 'power' ? t('sa_reason_power') : t('sa_reason_technical')}${x.note ? ' · ' + esc(x.note) : ''}</b></div>`).join('')}
   ${de.factory_closure ? `<div class="kv"><span>🏭 ${t('fc_was_closed_l')}</span><b>${esc(fcReasonLabel(de.factory_closure.reason, de.factory_closure.reason_text))}</b></div>` : ''}
   <div class="kv"><span>${t('powder_in_l')} · ${t('wastage_l')} (${de.wastage_pct}%)</span><b>${tonsDisp(de.powder_t || 0)} · ${tonsDisp(de.wastage_t || 0)}</b></div>
   <div class="kv"><span>${t('filter_powder_l')} (${t('own_word')})</span><b>${fmtN(de.filter_powder_kg || 0)} kg (${tonsDisp((de.filter_powder_kg || 0) / 1000)})</b></div>
   <div class="kv"><span>${t('cash_net')}</span><b>${fmt(de.cashbook.total)}</b></div>
   <div class="kv"><span>${t('expenses_l')}</span><b>${fmt(de.expense_total)}</b></div>
   <div class="kv"><span>${t('rent_mill_l')}</span><b>${fmt(de.rent_mill || 0)}</b></div>
   <div class="kv"><span>${t('de_gate_purch_l')}</span><b>${(de.gate_purchases || {}).count || 0} · ${tonsDisp((de.gate_purchases || {}).tons || 0)} · ${fmt((de.gate_purchases || {}).amount || 0)}${(de.gate_purchases || {}).rent_seller ? ' · ' + t('rent_l') + ' ' + fmt(de.gate_purchases.rent_seller) : ''}</b></div>
   <div class="kv"><span>${t('de_grind_earned_l')}</span><b>${fmt(de.grinding_earned || 0)}</b></div>
   <div class="kv"><span>${t('de_gate_sales_l')}</span><b>${(de.gate_sales || {}).count || 0} · ${tonsDisp((de.gate_sales || {}).tons || 0)} · ${fmt((de.gate_sales || {}).amount || 0)}</b></div>
   <div class="kv"><span>${t('de_trade_purch_l')}</span><b>${(de.trade_purchases || {}).count || 0} · ${fmt((de.trade_purchases || {}).amount || 0)}</b></div>
   <div class="kv"><span>${t('de_trade_sales_l')}</span><b>${(de.trade_sales || {}).count || 0} · ${fmt((de.trade_sales || {}).amount || 0)}</b></div>
   <div class="kv"><span>${t('de_direct_l')}</span><b>${(de.direct_trades || {}).count || 0} · ${fmt((de.direct_trades || {}).profit || 0)}</b></div>
   <div class="kv"><span>${t('de_payments_l')}</span><b>${fmt(de.payments_in || 0)} / ${fmt(de.payments_out || 0)}</b></div>
   <div class="kv"><span>${t('de_handovers_l')} / ${t('de_payouts_l')}</span><b>${fmt(de.cash_handovers || 0)} / ${fmt(de.worker_payouts || 0)}</b></div>
   <div class="kv"><span>${t('de_attendance_l')}</span><b>${de.attendance_present || 0}</b></div>
   <div class="kv"><span>🏭 ${t('outside_grinding')}</span><b>${t('sent_t_l')} ${tonsDisp((de.outside_grinding || {}).sent_t || 0)} · ${t('powder_back_l')} ${(de.outside_grinding || {}).produced_bags || 0} ${t('bags')} (${tonsDisp((de.outside_grinding || {}).produced_t || 0)}) · ${t('og_sold_l')} ${(de.outside_grinding || {}).sold_bags || 0} ${t('bags')} (${fmt((de.outside_grinding || {}).sold_amount || 0)}) · ${t('og_charges_l')} ${fmt((de.outside_grinding || {}).charges || 0)}</b></div>
   ${((de.outside_grinding || {}).mills || []).length > 1 ? de.outside_grinding.mills.map(m => `<div class="kv"><span>↳ ${esc(m.party_name || '')}</span><b>${tonsDisp(m.sent_t)} · ${m.produced_bags} ${t('bags')} · ${fmt(m.charges)}</b></div>`).join('') : ''}
   <div class="kv"><span>${t('now_grinding')}</span><b>${de.now_grinding.map(g => esc(g.party_name || t('own_word'))).join(', ') || '—'}</b></div>
   <button onclick="sendDayEnd()">📤 ${t('send_dayend')}</button></div>${accEnd()}
  ${accHead('cashbook','excel','📊',t('excel_range'),t('accd_excel'))}<div class="card">
   <div class="row"><div class="field"><label>${t('from_l')}</label><input id="cb_from" type="date" value="${todayStr().slice(0, 8)}01" onchange="cbDates()"></div>
   <div class="field"><label>${t('to_l')}</label><input id="cb_to" type="date" value="${todayStr()}" onchange="cbDates()"></div></div>
   <a id="cb_xlsx" href="/api/xl/export?module=cashbook&fmt=xlsx&from=${todayStr().slice(0, 8)}01&to=${todayStr()}"><button type="button" class="small ghost">${t('xl_download')}</button></a>
   <a id="cb_csv" href="/api/xl/export?module=cashbook&fmt=csv&from=${todayStr().slice(0, 8)}01&to=${todayStr()}"><button type="button" class="small ghost">⬇ CSV</button></a>
   <a id="cb_pdf" href="/api/xl/export?module=cashbook&fmt=pdf&from=${todayStr().slice(0, 8)}01&to=${todayStr()}"><button type="button" class="small ghost">⬇ PDF</button></a></div>${accEnd()}
  ${accHead('cashbook','bankbook','🏦','Bank Book',t('accd_bankbook'))}<div class="card">
   ${bb.banks.length ? bb.banks.map(b => `<h3>${esc(b.bank)} — ${t('bank_balance')}: <b>${fmt(b.balance)}</b></h3>
   <div class="kv"><span>${t('opening_bal')}</span><b>${fmt(b.opening)}</b></div>
   <div class="kv"><span>${t('payments_in_bank')}</span><b>+ ${fmt(b.in)}</b></div>
   <div class="kv"><span>${t('payments_out_bank')}</span><b>− ${fmt(b.out)}</b></div>
   <div class="kv"><span>${t('expenses_bank')}</span><b>− ${fmt(b.expenses)}</b></div>
   <div class="wrap"><table><tr><th>${t('date')}</th><th>${t('txn_type')}</th><th>${t('detail_l')}</th><th>${t('ref_chq')}</th><th class="num">${t('amount')}</th></tr>
   ${b.txns.map(x => `<tr><td>${x.date}</td><td>${esc(x.kind)}</td><td>${esc(x.detail)}</td><td>${esc(x.ref || '')}</td><td class="num">${fmt(x.amount)}</td></tr>`).join('')}</table></div>`).join('') : `<p class="muted">${t('bankbook_empty')}</p>`}</div>${accEnd()}`;
};
window.cbDates = () => {
  const q = `&from=${val('cb_from')}&to=${val('cb_to')}`;
  const x = document.getElementById('cb_xlsx'), c = document.getElementById('cb_csv');
  if (x) x.href = '/api/xl/export?module=cashbook&fmt=xlsx' + q;
  if (c) c.href = '/api/xl/export?module=cashbook&fmt=csv' + q;
  const pf = document.getElementById('cb_pdf');
  if (pf) pf.href = '/api/xl/export?module=cashbook&fmt=pdf' + q;
};
window.sendDayEnd = async () => {
  const de = await get('/api/dayend?date=' + todayStr());
  const text = `Day-End ${de.date}: ${de.trips}, IN ${tonsDisp(de.rock_in_t)}, ${tonsDisp(de.ground_t)}, OUT ${tonsDisp(de.powder_out_t)}, ${de.bags} bags, Rs ${Math.round(de.cashbook.total)}, Rs ${Math.round(de.expense_total)}`;
  msg(t('dayend_msg') + ' ' + text + ' ' + t('dayend_hint'));
};

VIEWS.cashinhand = async el => {
  const d = await get('/api/cash-hand');
  const isOwner = STATE.user.role === 'owner';
  const holderCard = h => `<div class="card" style="flex:1 1 220px;${h.over ? 'border:2px solid #c0392b' : ''}">
   <h3>👤 ${esc(h.name)}${h.is_user ? '' : ' <span class="small muted">(other)</span>'}</h3>
   <div class="kv"><span>${t('received_l')}</span><b>${fmt(h.received)}</b></div>
   <div class="kv"><span>${t('spent_l')}</span><b>${fmt(h.spent)}</b></div>
   <div class="kv"><span>${t('balance_in_hand')}</span><b style="${h.over ? 'color:#c0392b' : ''}">${fmt(h.balance)}</b></div>
   ${h.over ? `<p class="warn-red">⚠ ${t('over_warn')}</p>` : ''}
   ${h.pending_ack ? `<p class="badge-pend">⏳ ${h.pending_ack} ${t('ack_pending')}</p>` : ''}</div>`;
  const histTable = h => `<div class="wrap"><table><tr><th>${t('date')}</th><th>IN / OUT</th><th class="num">${t('amount')}</th><th>${t('note')}</th><th>${t('status')}</th></tr>
   ${h.history.slice().reverse().map(x => `<tr><td>${x.date}</td><td>${x.type === 'in' ? '⬇ ' + t('in_mila') : '⬆ ' + t('out_kharcha')}</td><td class="num">${fmt(x.amount)}</td><td>${esc(x.note || '')}</td>
   <td>${x.type === 'in' ? (x.status === 'pending' ? (h.key === 'user:' + STATE.user.id ? `<button class="small" onclick="ackHandover(${x.id})">${t('ack_btn')} ✓</button>` : `<span class="badge-pend">⏳ ${t('pending')}</span>`) : '✓ ' + t('confirmed_l')) : (x.status === 'pending' ? `<span class="badge-pend">⏳ ${t('pending')}</span>` : '✓')}</td></tr>`).join('')}</table></div>`;
  const countsList = h => h.counts.length ? `<h4>🧮 ${t('ginti_t')}</h4>
   ${h.counts.map(c => `<div class="kv"><span>${c.date} · ${fmt(c.counted)} · ${fmt(c.book)} ${c.note ? '· ' + esc(c.note) : ''}</span><b style="color:${c.diff < 0 ? '#c0392b' : (c.diff > 0 ? '#0c7a4e' : 'inherit')}">${c.diff > 0 ? '+' : ''}${fmt(c.diff)}${c.diff < 0 ? ' (' + t('kam') + ')' : (c.diff > 0 ? ' (' + t('zyada') + ')' : '')}</b></div>`).join('')}` : '';
  el.innerHTML = `
  ${isOwner ? `<div class="card"><h2>🤲 ${t('handover_t')}</h2>
   <div class="row"><div class="field"><label>${t('date')}</label><input id="ch_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('holder_l')}</label><select id="ch_user" onchange="chUserUI()"><option value="">— ${t('other_name')} —</option>${d.users.map(x => `<option value="${x.id}">${esc(x.username)} (${esc(x.role)})</option>`).join('')}</select></div>
   <div class="field" id="ch_namewrap"><label>${t('other_name')}</label><input id="ch_name"></div>
   <div class="field"><label>${t('amount')} *</label><input id="ch_amount" type="number"></div>
   <div class="field"><label>${t('note')}</label><input id="ch_note"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="addHandover()">${t('handover_save')}</button></div></div>
   <p class="small muted">${t('handover_note')} ${t('holder_limit_l')}: Rs ${fmt(d.rules.holder_limit)} · ${t('approval_limit_l')} Rs ${fmt(d.rules.approval_limit)}.</p></div>` : ''}
  <div class="card"><h2>💵 ${t('cashinhand')}${d.own_only ? ' ' + t('my_account') : ''}</h2>
   <div style="display:flex;flex-wrap:wrap;gap:10px">${d.holders.map(holderCard).join('') || '<span class="muted">—</span>'}</div>
   ${!d.own_only && d.holders.length ? `<div class="wrap" style="margin-top:10px"><table><tr><th>Holder</th><th class="num">${t('received_l')}</th><th class="num">${t('spent_l')}</th><th class="num">${t('balance_in_hand')}</th><th></th></tr>
   ${d.holders.map(h => `<tr${h.over ? ' style="background:#fdecea"' : ''}><td>${esc(h.name)}</td><td class="num">${fmt(h.received)}</td><td class="num">${fmt(h.spent)}</td><td class="num"><b>${fmt(h.balance)}</b></td><td>${h.over ? `<span class="warn-red">⚠ ${t('over_warn')}</span>` : ''}${h.pending_ack ? ` <span class="badge-pend">⏳ ${t('ack_pending')}</span>` : ''}</td></tr>`).join('')}</table></div>` : ''}</div>
  ${d.holders.map(h => `<div class="card"><h3>📜 ${esc(h.name)} — ${t('detail_word')}</h3>${histTable(h)}${countsList(h)}
   ${isOwner ? `<h4>🧮 ${t('ginti_t')}</h4><div class="row"><div class="field"><label>${t('date')}</label><input id="cc_date_${esc(h.key.replace(/[^a-zA-Z0-9]/g, ''))}" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('physical_cash')}</label><input id="cc_amt_${esc(h.key.replace(/[^a-zA-Z0-9]/g, ''))}" type="number"></div>
   <div class="field"><label>${t('note')}</label><input id="cc_note_${esc(h.key.replace(/[^a-zA-Z0-9]/g, ''))}"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button class="ghost" onclick="addCount('${esc(h.key)}')">${t('ginti_save')}</button></div></div>
   <p class="small muted">${t('ginti_book')}: <b>${fmt(h.balance)}</b> — ${t('ginti_note')}</p>` : ''}</div>`).join('')}`;
};
window.chUserUI = () => { const w = $('#ch_namewrap'); if (w) w.style.display = val('ch_user') ? 'none' : ''; };
window.addHandover = async () => {
  try {
    if (!reqCheck([['ch_amount', 'fl_amount', 'pos']])) return;
    if (!val('ch_user') && !(val('ch_name') || '').trim()) { errPopup(t('missing_t') + t('fl_holder')); const n = $('#ch_name'); if (n) n.classList.add('reqbad'); return; }
    const r = await post('/api/cash-handovers', { date: val('ch_date'), amount: num('ch_amount'),
      holder_user_id: val('ch_user') || null, holder_name: val('ch_name'), note: val('ch_note') });
    let text = t('handover_saved') + ' ✓ Rs ' + fmt(num('ch_amount')) + ' → ' + r.holder_name;
    if (r.status === 'pending') text += ' ' + t('ack_note2');
    if (r.warning) text += ' — ⚠ ' + r.warning;
    okPopup(text); render();
    if (r.warning) msg(r.warning, 'warn');
  } catch (e) { msg(e.message, 'err'); }
};
window.ackHandover = async id => { try { await post('/api/cash-handovers/ack', { id }); okPopup(t('ack_done')); render(); } catch (e) { msg(e.message, 'err'); } };
window.addCount = async key => {
  const suf = key.replace(/[^a-zA-Z0-9]/g, '');
  if (!reqCheck([['cc_amt_' + suf, 'fl_counted', 'num']])) return;
  try {
    const r = await post('/api/cash-counts', { holder_key: key, date: val('cc_date_' + suf), counted: num('cc_amt_' + suf), note: val('cc_note_' + suf) });
    okPopup(t('ginti_saved') + ' ✓ ' + t('book_w') + ' ' + fmt(r.book) + ' · ' + t('ginti_w') + ' ' + fmt(r.counted) + ' · ' + t('difference') + ': ' + (r.diff > 0 ? '+' : '') + fmt(r.diff) + (r.diff < 0 ? ' (' + t('kam') + ')' : (r.diff > 0 ? ' (' + t('zyada') + ')' : '')));
    render();
  } catch (e) { msg(e.message, 'err'); }
};
VIEWS.cheques = async el => {
  const rows = await get('/api/cheques');
  el.innerHTML = `<div class="card"><h2>🧾 ${t('cheques')}</h2>
   <p class="small muted">${t('chq_note')}</p>
   <div class="wrap"><table><tr><th>${t('due_date')}</th><th>${t('party')}</th><th>${t('cheque_no')}</th><th>${t('bank')}</th><th class="num">${t('amount')}</th><th>${t('status')}</th><th></th></tr>
   ${rows.map(c => `<tr><td>${c.due_date}</td><td>${esc(c.party_name || '')}</td><td>${esc(c.cheque_no)}</td><td>${esc(c.bank)}</td><td class="num">${fmt(c.amount)}</td>
   <td><span class="badge ${c.status === 'bounced' ? 'red' : c.status === 'pending' ? 'amber' : ''}">${c.status}</span></td>
   <td>${c.status === 'pending' ? `<button class="small" onclick="chqStatus(${c.id},'cleared')">${t('st_cleared')}</button> <button class="small danger" onclick="chqStatus(${c.id},'bounced')">${t('st_bounced')}</button>` : ''}</td></tr>`).join('') || `<tr><td class="muted">${t('no_cheque')}</td></tr>`}</table></div></div>`;
};
window.chqStatus = async (id, s) => { await post('/api/cheques/status', { id, status: s }); okPopup(t('cheque_done') + ' ' + s + ' ✓'); render(); };

VIEWS.reports = async el => {
  const month = todayStr().slice(0, 7);
  const p = await get('/api/pnl?month=' + month);
  const line = o => Object.entries(o).map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><b>${fmt(v)}</b></div>`).join('');
  const cpt = await get('/api/costperton').catch(() => null);
  const biz = await get('/api/party-business').catch(() => ({ rows: [] }));
  window._cpt = cpt;
  const per = v => v === null || v === undefined ? '—' : fmt(v);
  el.innerHTML = `${accHead('reports','pnl','📈',t('pnl_t') + ' — ' + month,t('accd_pnl'),'pnl')}<div class="card"><p style="text-align:end"><a class="small" target="_blank" href="/print/pnl">🖨 ${t('print')}</a></p>
   <h3>${t('pnl_income')} — ${fmt(p.income)}</h3>${line({ [t('grinding')]: p.grinding_income, [t('sale')]: p.sales_income })}
   <h3>${t('pnl_costs')} — ${fmt(p.costs)}</h3>${line({ [t('c_purchases')]: p.purchases, [t('c_outside')]: p.outside_grinding || 0, [t('c_expenses')]: p.expenses, [t('c_payouts')]: p.worker_payouts, [t('c_maint')]: p.maintenance, [t('c_freight')]: p.freight_mill, [t('c_loading')]: p.loading_mill, [t('c_rent')]: p.rent_mill || 0 })}
   <div class="kv" style="font-size:16px"><span><b>${t('pnl_net')}</b></span><b>${fmt(p.profit)}</b></div>
   <div class="kv"><span>🏭 ${t('fc_days_l')}</span><b>${p.factory_closed_days || 0} ${t('fc_days')}</b></div>
   ${(p.factory_periods || []).map(x => `<div class="kv"><span>↳ ${x.closed_from} → ${x.closed_to || '…'}</span><b>${x.days_in_month} ${t('fc_days')} · ${esc(fcReasonLabel(x.reason, x.reason_text))}</b></div><div class="kv"><span></span><span class="small muted">${esc(t('fc_gate_l').replace('{rock}', tonsDisp(x.gate_rock_t || 0)).replace('{pow}', tonsDisp(x.gate_powder_t || 0)))}</span></div>`).join('')}
   <p class="small muted">${t('cost_note')}</p></div>${accEnd()}
  ${accHead('reports','cpt','⚖️',t('cpt'),t('accd_cpt'))}<div class="card">
   <div class="row"><div class="field"><label>${t('period')}</label><select id="cpt_period" onchange="cptPeriod()">
     <option value="this">${t('this_month')}</option><option value="last">${t('last_month')}</option><option value="custom">${t('custom')}</option></select></div>
   <div class="field"><label>${t('from_l')}</label><input id="cpt_from" type="date" value="${month}-01"></div>
   <div class="field"><label>${t('to_l')}</label><input id="cpt_to" type="date" value="${todayStr()}"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button class="ghost" onclick="cptLoad()">${t('show')}</button></div></div>
   <div id="cpt_body">${cpt ? cptHTML(cpt) : ''}</div></div>${accEnd()}
  ${accHead('reports','biz','🤝',t('biz_summary'),t('accd_biz'))}<div class="card">
   <p class="small muted">${t('biz_note')}</p>
   <div class="wrap"><table><tr><th>${t('party')}</th><th class="num">${t('grinding_income')}</th><th class="num">${t('charges_l')}</th><th class="num">${t('sales_total')}</th><th class="num">${t('purchases_total')}</th><th class="num">${t('net_l')}</th></tr>
   ${(biz.rows || []).map(r => `<tr><td>${esc(r.party)}</td><td class="num">${fmt(r.grinding)}</td><td class="num">${fmt(r.charges)}</td><td class="num">${fmt(r.sales)}</td><td class="num">${fmt(r.purchases)}</td><td class="num"><b>${fmt(r.net)}</b></td></tr>`).join('')}</table></div></div>${accEnd()}`;
  function cptHTML(c){
    return `<div class="kv"><span>${t('tons_ground')}</span><b>${tonsDisp(c.tons_ground)}</b></div>
   <div class="kv"><span>${t('total_expenses')}</span><b>${fmt(c.expenses)}</b></div>
   <div class="kv"><span>${t('expense_per_ton')}</span><b>${per(c.expense_per_ton)}</b></div>
   <div class="kv"><span>${t('grinding_income')}</span><b>${fmt(c.grinding_income)}</b></div>
   <div class="kv"><span>${t('income_per_ton')}</span><b>${per(c.income_per_ton)}</b></div>
   <div class="kv"><span>${t('margin_per_ton')}</span><b>${per(c.margin_per_ton)}</b></div>
   <h3>${t('by_head')}</h3>${Object.entries(c.expenses_by_head || {}).map(([h, v]) => `<div class="kv"><span>${esc(h)}</span><b>${fmt(v)}</b></div>`).join('') || '<span class="muted">—</span>'}`;
  }
  window._cptHTML = cptHTML;
};
window.cptPeriod = () => {
  const v = val('cpt_period');
  const now = new Date();
  const iso = d => d.toISOString().slice(0, 10);
  if (v === 'this') { $('#cpt_from').value = iso(new Date(now.getFullYear(), now.getMonth(), 1)); $('#cpt_to').value = todayStr(); cptLoad(); }
  if (v === 'last') { $('#cpt_from').value = iso(new Date(now.getFullYear(), now.getMonth() - 1, 1)); $('#cpt_to').value = iso(new Date(now.getFullYear(), now.getMonth(), 0)); cptLoad(); }
};
window.cptLoad = async () => {
  const c = await get(`/api/costperton?from=${val('cpt_from')}&to=${val('cpt_to')}`);
  const box = document.getElementById('cpt_body');
  if (box && window._cptHTML) box.innerHTML = window._cptHTML(c);
};

VIEWS.phosdetail = async el => {
  const ds = window._pdDate || todayStr();
  const r = await get('/api/phosphate-detail?date=' + ds);
  const n3 = v => (Math.round((v || 0) * 1000) / 1000).toLocaleString('en-US', { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  el.innerHTML = `<div class="card"><h2>📒 ${t('phos_detail')} — ${r.date}
   <a class="small" target="_blank" href="/print/phosphate-detail?date=${r.date}">🖨 ${t('print')}</a></h2>
   <div class="row"><div class="field"><label>${t('date')}</label><input id="pd_date" type="date" value="${r.date}" onchange="pdDateChange()"></div></div>
   <p class="small muted">${t('pd_help')}</p>
   <div class="wrap"><table><tr><th class="num">${t('rock_in')}</th>
   <th class="num">${t('total_rock')}</th><th class="num">${t('day_l')}</th><th class="num">${t('night_l')}</th>
   <th class="num">${t('wastage_l')} (${r.wastage_pct}%)</th><th class="num">${t('powder_in_l')}</th><th class="num">${t('prev_powder_l')}</th>
   <th class="num">${t('dispatched_l')}</th>
   <th class="num">${t('bal_powder_l')}</th><th class="num">${t('bal_rock_l')}</th><th>${t('remarks_l')}</th></tr>
   <tr><td class="num">${n3(r.rock_in_t)}</td>
   <td class="num"><b>${n3(r.total_rock_t)}</b><br><span class="small muted">${t('prev_rock_l')} ${n3(r.total_stock_rock_t)} + ${t('rock_in')} ${n3(r.rock_in_t)}</span></td>
   <td class="num">${r.bags_day}</td><td class="num">${r.bags_night}</td>
   <td class="num">${n3(r.wastage_t)}</td><td class="num">${n3(r.powder_in_t)}</td><td class="num">${n3(r.prev_powder_t)}</td>
   <td class="num">${n3(r.dispatched_t)}</td>
   <td class="num"><b>${n3(r.balance_powder_t)}</b></td><td class="num"><b>${n3(r.balance_rock_t)}</b></td><td>${esc(r.remark || '')}</td></tr></table></div>
   ${r.bags_unclassified ? `<p class="small muted">${t('unspec_l')}: ${r.bags_unclassified}</p>` : ''}
   ${r.adj_bags ? `<div class="kv"><span>${t('ginti_adj')}</span><b>${r.adj_bags} ${t('bags')}</b></div>` : ''}
   ${r.bought_bags ? `<div class="kv"><span>${t('powder_bought_l')}</span><b>${r.bought_bags} ${t('bags')}</b></div>` : ''}
   <div class="row"><div class="field" style="flex:1"><label>${t('remarks_l')}</label><input id="pd_remark" value="${esc(r.remark || '')}"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button onclick="pdSaveRemark()">${t('save')}</button></div></div></div>
  <div class="card"><h2>🤝 ${t('pd_breakdown')}</h2>
   <div class="wrap"><table><tr><th>${t('party')}</th><th class="num">${t('rock_in')}</th><th class="num">${t('day_l')}</th>
   <th class="num">${t('night_l')}</th><th class="num">${t('powder_in_l')}</th>
   <th class="num">${t('dispatched_l')}</th><th class="num">${t('bal_powder_l')}</th></tr>
   ${(r.rows || []).map(x => `<tr><td>${esc(x.party)}</td><td class="num">${n3(x.rock_in_t)}</td><td class="num">${x.bags_day}</td>
   <td class="num">${x.bags_night}</td><td class="num">${n3(x.powder_t)}</td>
   <td class="num">${n3(x.dispatched_t)}</td><td class="num"><b>${n3(x.powder_balance_t)}</b></td></tr>`).join('')}</table></div></div>`;
};
window.pdDateChange = () => { window._pdDate = val('pd_date'); render(); };
window.pdSaveRemark = async () => {
  try {
    await post('/api/phosphate-detail/remark', { date: val('pd_date'), remark: val('pd_remark') });
    okPopup(t('saved')); window._pdDate = val('pd_date'); render();
  } catch (e) { msg(e.message, 'err'); }
};

VIEWS.recycle = async el => {
  el.innerHTML = `${accHead('recycle','deleted','🗑',t('deleted_entries'),t('accd_deleted'),'deleted')}<div class="card"><div id="rec_list"></div></div>${accEnd()}
  ${accHead('recycle','notifs','🔔',t('notifications'),t('accd_notifs'))}<div class="card"><div id="notif_list"></div></div>${accEnd()}
  ${accHead('recycle','audit','📜',t('audit_log'),t('accd_audit'))}<div class="card"><div id="audit_list"></div></div>${accEnd()}`;
  if (STATE.user.role === 'owner') {
    const rec = await get('/api/recycle');
    $('#rec_list').innerHTML = rec.length ? rec.map(r => `<div class="kv"><span>${r.created} — ${esc(r.table_name)} #${r.record_id} by ${esc(r.deleted_by)}</span><button class="small" onclick="restoreRec(${r.id})">${t('restore')}</button></div>`).join('') : '<span class="muted">—</span>';
    const nt = await get('/api/notifications');
    $('#notif_list').innerHTML = nt.slice(0, 30).map(n => `<div class="kv"><span>${n.is_read ? '' : '🔴 '}${esc(n.message || n.detail || '')}</span><span class="muted small">${n.created}</span></div>`).join('') || '<span class="muted">—</span>' +
      '<br><button class="small ghost" onclick="markRead()">' + t('all_read') + '</button>';
    const au = await get('/api/audit');
    $('#audit_list').innerHTML = '<div class="wrap"><table>' + au.slice(0, 40).map(a => `<tr><td>${a.created}</td><td>${esc(a.username)}</td><td>${esc(a.action)}</td><td>${esc(a.detail)}</td></tr>`).join('') + '</table></div>';
  } else {
    $('#rec_list').innerHTML = $('#notif_list').innerHTML = $('#audit_list').innerHTML = '<span class="muted">' + t('owner_only_note') + '</span>';
  }
};
window.restoreRec = async id => { try { await post('/api/restore-recycle', { id }); okPopup(t('restored_ok')); render(); } catch (e) { msg(e.message, 'err'); } };
window.markRead = async () => { await post('/api/notifications/read', {}); STATE.unread_notifications = 0; render(); };

VIEWS.alerts = async el => {
  const rows = await get('/api/alerts');
  const proofs = await get('/api/proofs');
  el.innerHTML = `${accHead('alerts','alerts','🔔',t('alerts') + ' — WhatsApp / SMS / Email',t('accd_alerts'),'alerts')}<div class="card">
   <p class="small muted">${t('wa_card_note')}</p>
   <button onclick="genAlerts()">${t('generated')}</button>
   <div class="wrap" style="margin-top:10px"><table><tr><th>${t('when_l')}</th><th>${t('type_l')}</th><th>${t('to_l2')}</th><th>${t('message_l')}</th><th>${t('status')}</th><th></th></tr>
   ${rows.slice(0, 60).map(a => { const num = a.channel === 'email' ? '' : String(a.target || '').replace(/\D/g, '').replace(/^0/, '92');
     return `<tr><td class="small">${a.created}</td><td>${a.kind}${a.channel ? `<br><span class="small muted">${esc(a.channel)}</span>` : ''}</td><td>${esc(a.target || '')}</td><td class="small">${esc(a.message)}</td>
   <td><span class="badge ${a.status === 'sent' ? '' : a.status === 'failed' ? 'red' : 'amber'}">${a.status}</span><br><span class="small muted">${esc(a.detail || '')}</span></td>
   <td>${num ? `<a target="_blank" href="https://wa.me/${num}?text=${encodeURIComponent(a.message)}"><button class="small">💬 wa.me</button></a>` : ''}
   ${a.channel === 'email' ? '' : `<button class="small ghost" onclick="resendAlert(${a.id})">${t('send')}</button>`}
   ${isOwner() ? `<button class="small danger" onclick="delAlert(${a.id})">${t('del')}</button>` : ''}</td></tr>`; }).join('')}</table></div></div>${accEnd()}
  ${accHead('alerts','proofs','🧾',t('proofs_t'),t('accd_proofs'))}<div class="card">
   <div class="wrap"><table><tr><th>${t('date')}</th><th>${t('party')}</th><th class="num">${t('amount')}</th><th>${t('proof_attach')}</th><th>${t('status')}</th><th></th></tr>
   ${proofs.map(p => `<tr><td>${p.date}</td><td><span style="display:inline-flex;align-items:center;gap:7px">${avatarHTML(p.cuid, p.cavatar, p.caver, p.party_name)}${esc(p.party_name || '')}</span></td><td class="num">${fmt(p.amount)}</td>
   <td>${p.attachment_id ? `<a href="/api/attachments/${p.attachment_id}/raw" target="_blank">📎 ${t('view_proof')}</a>` : esc(p.note || '')}</td><td>${p.status}</td>
   <td>${p.status === 'pending' ? `<button class="small" onclick="confirmProof(${p.id})">${t('confirm_pay')}</button> <button class="small danger" onclick="rejectProof(${p.id})">✗</button>` : ''}</td></tr>`).join('') || '<tr><td class="muted">—</td></tr>'}</table></div></div>${accEnd()}`;
};
window.genAlerts = async () => { const r = await post('/api/alerts/generate', {}); okPopup(r.generated + ' ' + t('reminder_made') + ' ✓'); render(); };
window.resendAlert = async id => { const r = await post('/api/alerts/send', { id }); msg(t('alert_status') + ': ' + r.status); render(); };
window.delAlert = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  confirmDelete('Alert #' + id, async () => {
    try { await post('/api/alerts/delete', { id }); render(); }
    catch (e) { msg(e.message, 'err'); }
  });
};
window.confirmProof = async id => { try { await post('/api/proofs/confirm', { id }); okPopup(t('proof_confirm_done')); render(); } catch (e) { msg(e.message, 'err'); } };
window.rejectProof = async id => { await post('/api/proofs/reject', { id }); okPopup(t('proof_rejected')); render(); };

/* ---------------- AI assistant: floating, draggable popup ----------------
   NOT a sidebar page any more: a round chat button lives on every screen
   after login; it can be dragged anywhere (mouse + touch) and its spot is
   remembered per user. History is kept for the session. */
let AI_CHAT = [];
let AI_OPEN = false;
let AI_POS = null;
try { AI_POS = JSON.parse(localStorage.getItem('mill_ai_pos') || 'null'); } catch (e) { AI_POS = null; }
function mountAI(){
  const old = document.getElementById('aiwrap');
  if (old) old.remove();
  if (!STATE.user) return;
  if (STATE.user.role === 'client') return;  // assistant API is owner/manager only (as before)
  if (STATE.user.role === 'staff' && !(STATE.user.perms || []).includes('reports')) return;  // staff: Reports permission only
  const wrap = document.createElement('div');
  wrap.id = 'aiwrap';
  wrap.innerHTML = `
   <div class="aipanel" id="aipanel" style="display:${AI_OPEN ? 'flex' : 'none'}">
     <div class="aihead"><span>🤖 ${t('assistant')}</span>
       <button type="button" class="ai-x" onclick="toggleAI(false)" aria-label="close">✕</button></div>
     <div class="chatbox" id="chat"></div>
     <div class="airow">
       <button type="button" class="voicebtn ai-mic" onclick="aiMic()" title="Voice">🎤</button>
       <input id="chat_q" placeholder="${t('ai_placeholder')}" onkeydown="if(event.key==='Enter')askAI()">
       <button type="button" class="ai-send" onclick="askAI()">${t('send')}</button>
     </div>
     <p class="small muted aihint">${t('ai_hint')}</p>
   </div>
   <button type="button" class="aifab" id="aifab" style="display:${AI_OPEN ? 'none' : 'flex'}" title="🤖 ${t('assistant')} — ${t('ai_drag')}">🤖</button>`;
  document.body.appendChild(wrap);
  const fab = document.getElementById('aifab');
  if (fab) {
    if (AI_POS) { fab.style.left = AI_POS.x + 'px'; fab.style.top = AI_POS.y + 'px'; fab.style.right = 'auto'; fab.style.bottom = 'auto'; }
    fab.addEventListener('pointerdown', aiDragStart);
    fab.addEventListener('click', () => { if (Date.now() - _aiUpAt > 350) toggleAI(); });
  }
  if (AI_OPEN) placePanel();
  drawAIChat();
}
let _aiUpAt = 0;
let _aiDrag = null;
function aiDragStart(e){
  const fab = document.getElementById('aifab');
  if (!fab) return;
  const r = fab.getBoundingClientRect();
  _aiDrag = { dx: e.clientX - r.left, dy: e.clientY - r.top, sx: e.clientX, sy: e.clientY, moved: false };
  document.addEventListener('pointermove', aiDragMove);
  document.addEventListener('pointerup', aiDragEnd, { once: true });
}
function aiDragMove(e){
  if (!_aiDrag) return;
  if (Math.abs(e.clientX - _aiDrag.sx) + Math.abs(e.clientY - _aiDrag.sy) > 6) _aiDrag.moved = true;
  if (!_aiDrag.moved) return;
  const fab = document.getElementById('aifab');
  if (!fab) return;
  const x = Math.min(Math.max(2, e.clientX - _aiDrag.dx), window.innerWidth - 58);
  const y = Math.min(Math.max(2, e.clientY - _aiDrag.dy), window.innerHeight - 58);
  fab.style.left = x + 'px'; fab.style.top = y + 'px'; fab.style.right = 'auto'; fab.style.bottom = 'auto';
  AI_POS = { x, y };
  if (AI_OPEN) placePanel();
}
function aiDragEnd(){
  document.removeEventListener('pointermove', aiDragMove);
  _aiUpAt = Date.now();
  if (_aiDrag && _aiDrag.moved && AI_POS) localStorage.setItem('mill_ai_pos', JSON.stringify(AI_POS));
  else if (_aiDrag && !_aiDrag.moved) toggleAI();
  _aiDrag = null;
}
function placePanel(){
  const p = document.getElementById('aipanel');
  const fab = document.getElementById('aifab');
  if (!p || !fab) return;
  if (window.innerWidth <= 760) {
    p.style.left = '8px'; p.style.right = '8px'; p.style.width = 'auto';
    p.style.top = 'auto'; p.style.bottom = '12px';
    return;
  }
  const r = fab.getBoundingClientRect();
  /* the launcher is hidden while the panel is open (zero rect then):
     fall back to its remembered spot so the panel stays anchored */
  const fx = r.width ? r.right : (AI_POS ? AI_POS.x + 56 : window.innerWidth - 22);
  const fy = r.width ? r.top : (AI_POS ? AI_POS.y : window.innerHeight - 78);
  const fb = r.width ? r.bottom : fy + 56;
  const W = 372, H = 500;
  const left = Math.min(Math.max(8, fx - W), window.innerWidth - W - 8);
  let top = fy - H - 10;
  if (top < 8) top = Math.min(fb + 10, window.innerHeight - H - 8);
  p.style.left = left + 'px'; p.style.top = Math.max(8, top) + 'px';
  p.style.right = 'auto'; p.style.bottom = 'auto'; p.style.width = W + 'px';
}
window.toggleAI = force => {
  AI_OPEN = (force !== undefined) ? !!force : !AI_OPEN;
  const p = document.getElementById('aipanel');
  if (!p) return;
  p.style.display = AI_OPEN ? 'flex' : 'none';
  /* the floating launcher must NEVER overlap the open popup: on phones
     it sat on top of the input row and hid the Send button */
  const fab = document.getElementById('aifab');
  if (fab) fab.style.display = AI_OPEN ? 'none' : 'flex';
  if (AI_OPEN) { placePanel(); drawAIChat(); const inp = document.getElementById('chat_q'); if (inp) inp.focus(); }
};
function drawAIChat(){
  const box = document.getElementById('chat');
  if (!box) return;
  box.innerHTML = AI_CHAT.length
    ? AI_CHAT.map((m, i) => m.who === 'me'
        ? `<div class="me"><span>${esc(m.text)}</span></div>`
        : `<div class="bot">${m.report ? `<pre class="aireport">${esc(m.report.text)}</pre>` : `<span>${esc(m.text)}</span>`}
           ${m.report ? `<div class="airow2"><button type="button" class="small" onclick="aiDownload(${i})">${t('download_file')}</button></div>` : ''}
           ${m.view && canView(m.view) ? `<div class="airow2"><button type="button" class="small" onclick="aiOpenView('${m.view}')">${t('open_view')} \u2192</button></div>` : ''}
           ${(m.suggest && m.suggest.length) ? `<div class="aichips"><span class="small muted">${t('ai_try')}</span>${m.suggest.map((s, j) => `<button type="button" class="aichip" onclick="aiAskQ(${i},${j})">${esc(s.label)}</button>`).join('')}</div>` : ''}</div>`).join('')
    : `<div class="bot"><span>${t('ai_hint')}</span></div>`;
  box.scrollTop = box.scrollHeight;
}
window.aiOpenView = v => { if (!canView(v)) return; VIEW = v; toggleAI(false); render(); };
/* ---------- Item I1: voice notifications poller ---------- */
window.toggleMute = () => {
  const m = localStorage.getItem('mill_mute') === '1' ? '0' : '1';
  localStorage.setItem('mill_mute', m);
  const b = document.getElementById('mutebtn'); if (b) b.textContent = m === '1' ? '🔇' : '🔊';
};
function evLine(e) {
  const tpl = { vehicle_in: 'ev_in', vehicle_out: 'ev_out', payment_in: 'ev_pay_in',
                payment_out: 'ev_pay_out', expense_pending: 'ev_exp_pending' }[e.kind];
  if (!tpl) return '';
  return t(tpl).replace('{party}', e.party || '').replace('{amount}', fmtN(e.amount || 0)).replace('{tons}', e.tons || '');
}
function evToast(text) {
  let d = document.getElementById('evtoast');
  if (!d) { d = document.createElement('div'); d.id = 'evtoast'; document.body.appendChild(d); }
  d.textContent = text; d.style.display = 'block';
  clearTimeout(window._evT); window._evT = setTimeout(() => { d.style.display = 'none'; }, 6000);
}
window.pollEvents = async () => {
  if (!STATE || !STATE.user || (STATE.user.role === 'client')) return;
  const v = STATE.voice || {};
  if (!v.voice_alerts) return;
  try {
    const wm = localStorage.getItem('mill_ev_wm') || '';
    const r = await get('/api/events?since=' + encodeURIComponent(wm));
    if (!wm) { if (r.latest) localStorage.setItem('mill_ev_wm', r.latest); return; }
    const muted = localStorage.getItem('mill_mute') === '1';
    for (const e of (r.events || [])) {
      const isVeh = e.kind === 'vehicle_in' || e.kind === 'vehicle_out';
      if (isVeh && !v.voice_vehicles) continue;
      if (!isVeh && !v.voice_payments) continue;
      const line = evLine(e);
      if (!line) continue;
      evToast(line);
      if (!muted && window.speechSynthesis) {
        try {
          const ut = new SpeechSynthesisUtterance(line);
          ut.lang = PREFS.lang === 'ur' ? 'ur-PK' : PREFS.lang === 'hi' ? 'hi-IN' : 'en-US';
          speechSynthesis.speak(ut);
        } catch (err) {}
      }
    }
    if (r.latest) localStorage.setItem('mill_ev_wm', r.latest);
  } catch (err) {}
};
window.startEvPoll = () => {
  if (window._evStarted) return;
  window._evStarted = true;
  window.pollEvents();
  setInterval(() => { if (!document.hidden) { window.pollEvents(); if (window.refreshPending) window.refreshPending(); } }, 20000);
};
window.aiDownload = i => {
  const m = AI_CHAT[i];
  if (!m || !m.report) return;
  const blob = new Blob([m.report.text], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = m.report.filename || 'report.txt';
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
};
/* Light conversation context (owner brief, 28 Oct 2026): remember the
   last intent / day / party so follow-ups like "aur bahar wali?",
   "kal ka bhi batao" and "us ka khata?" resolve instead of dead-ending. */
let AI_CTX = { lastIntent: null, lastDay: '', lastDayWord: '', lastParty: '', lastQ: '' };
function _aiResolveFollowup(q) {
  const low = ' ' + q.toLowerCase() + ' ';
  /* remember any party named outright */
  for (const p of (CACHE.parties || [])) {
    if (p.name && low.includes(' ' + String(p.name).toLowerCase() + ' ')) AI_CTX.lastParty = p.name;
  }
  /* "us ka khata?" / "us ki payment?" — pronoun + last party */
  if (/(^|\s)(us|is|un|usk|isk)\s*(ka|ki|kay|ke)\s/.test(low) || /(khata|balance|payment|hisaab|hisab|stock)/.test(low) && /(us|is|un)\s/.test(low)) {
    const wantsPay = /payment|adaigi|pais/.test(low);
    const wantsStock = /stock|maal|bori|bag/.test(low);
    if (AI_CTX.lastParty) {
      if (wantsPay) return AI_CTX.lastParty + ' ki payment kitni hui hai';
      if (wantsStock) return AI_CTX.lastParty + ' ka stock kitna hai';
      return AI_CTX.lastParty + ' ka balance kitna hai';
    }
    return '__ASK_PARTY__';
  }
  /* "aur bahar wali?" / "aur andar wali?" — same trip list, other direction */
  if (/aur\s+(bahar|andar)\s*wali/.test(low) && AI_CTX.lastIntent === 'trips') {
    const dir = /bahar/.test(low) ? 'gayi thi' : 'aayi thi';
    return 'gari kis ki ' + dir + (AI_CTX.lastDayWord ? ' ' + AI_CTX.lastDayWord : '');
  }
  /* "kal ka bhi batao" / "parso ka?" — same question, day shifted */
  const dm = low.match(/\b(aaj|aj|kal|parso)\b/);
  if (dm && /(bhi|batao|btao|dikhao|ka\?|ki\?)/.test(low) && AI_CTX.lastQ) {
    return AI_CTX.lastQ.replace(/\b(aaj|aj|kal|parso)\b/g, '').replace(/\s+/g, ' ').trim() + ' ' + dm[1];
  }
  return q;
}
async function _aiSend(q){
  AI_CHAT.push({ who: 'me', text: q });
  drawAIChat();
  const qSend = _aiResolveFollowup(q);
  if (qSend === '__ASK_PARTY__') {
    const chips = (CACHE.parties || []).slice(0, 3).map(p => ({ label: p.name, q: p.name + ' ka balance kitna hai' }));
    AI_CHAT.push({ who: 'bot', text: t('ai_which_party'), suggest: chips.length ? chips : null });
    drawAIChat();
    return;
  }
  try {
    const r = await get('/api/assistant?q=' + encodeURIComponent(qSend));
    AI_CHAT.push({ who: 'bot', text: r.answer, view: r.view || null, report: r.report || null,
                   suggest: (r.suggest && r.suggest.length) ? r.suggest : null });
    if (r.ctx) {
      if (r.ctx.lastIntent) AI_CTX.lastIntent = r.ctx.lastIntent;
      if (r.ctx.lastDay) AI_CTX.lastDay = r.ctx.lastDay;
      if (r.ctx.lastParty) AI_CTX.lastParty = r.ctx.lastParty;
    }
    AI_CTX.lastQ = qSend;
    const dw = qSend.toLowerCase().match(/\b(aaj|aj|kal|parso)\b/);
    AI_CTX.lastDayWord = dw ? dw[1] : AI_CTX.lastDayWord;
  } catch (e) { AI_CHAT.push({ who: 'bot', text: '⚠ ' + e.message }); }
  drawAIChat();
}
window.askAI = async () => {
  const inp = document.getElementById('chat_q');
  const q = inp ? inp.value.trim() : '';
  if (!q) return;
  if (inp) inp.value = '';
  await _aiSend(q);
};
/* suggestion chips: tapping one asks that topic's question */
window.aiAskQ = (i, j) => {
  const m = AI_CHAT[i];
  if (!m || !m.suggest || !m.suggest[j]) return;
  _aiSend(m.suggest[j].q);
};
window.aiMic = () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert(t('voice_hint')); return; }
  const rec = new SR();
  rec.lang = PREFS.lang === 'ur' ? 'ur-PK' : (PREFS.lang === 'hi' ? 'hi-IN' : 'en-US');
  rec.interimResults = false;
  rec.onresult = ev => {
    const inp = document.getElementById('chat_q');
    if (inp) { inp.value = ev.results[0][0].transcript; inp.focus(); }
  };
  rec.onerror = () => {};
  try { rec.start(); } catch (e) {}
};
/* old sidebar route now just opens the popup */
VIEWS.assistant = el => {
  el.innerHTML = `<div class="card"><h2>🤖 ${t('assistant')}</h2>
   <p class="muted">${t('ai_hint')}</p>
   <button onclick="toggleAI(true)">🤖 ${t('assistant')}</button></div>`;
  toggleAI(true);
};

VIEWS.data = async el => {
  const bk = await get('/api/backups');
  const tables = ['parties', 'trips', 'grinding_jobs', 'purchases', 'sales', 'production', 'payments', 'expenses', 'workers', 'worker_payouts', 'attendance', 'cheques', 'expense_heads', 'departments', 'leaves'];
  el.innerHTML = `${accHead('data','backup','💾',t('data_backup_t'),t('accd_backup'),'backup')}<div class="card">
   <p>${t('backup_folder_l')}: <b>${esc(bk.backup_dir || '')}</b> · ${t('last_backup_l')}: ${bk.backup_days === null ? t('never_l') : bk.backup_days + ' ' + t('days_ago_l')}</p>
   <button onclick="doBackup()">${t('backup_btn')}</button>
   <p class="small muted">${t('backup_note')}</p>
   <h3>${t('restore_t')}</h3>
   ${bk.files.map(f => `<div class="kv"><span>${esc(f)}</span><button class="small danger" onclick="doRestore('${esc(f)}')">${t('restore')}</button></div>`).join('') || '<span class="muted">' + t('no_backup') + '</span>'}</div>${accEnd()}
  ${accHead('data','export','📤',t('export_t'),t('accd_export'))}<div class="card">
   ${tables.map(x => `<a href="/api/export/${x}.csv"><button class="small ghost" style="margin:2px">${x}</button></a>`).join('')}</div>${accEnd()}
  ${accHead('data','import','📥',t('import_t'),t('accd_import'))}<div class="card">
   <div class="row"><div class="field"><label>${t('table_l')}</label><select id="im_table"><option>parties</option><option>trips</option><option>production</option><option>expenses</option><option>payments</option><option>workers</option><option>attendance</option></select></div></div>
   <textarea id="im_csv" rows="5" placeholder="${t('paste_ph')}"></textarea>
   <button class="small" onclick="importPreview()">${t('preview_l')}</button> <button class="small" onclick="importApply()">${t('import_t')}</button>
   <div id="im_out" class="small" style="margin-top:8px"></div></div>${accEnd()}
  ${STATE.user.role === 'owner' ? `${accHead('data','demo','🧪',t('demo_title'),t('accd_demo'))}<div class="card">
   <p class="small muted">${t('demo_text')}</p>
   ${STATE.demo_loaded ? `<button class="danger" onclick="removeDemo()">${t('demo_remove')}</button>` : `<button onclick="loadDemo()">${t('demo_load')}</button>`}</div>${accEnd()}` : ''}`;
};
window.doBackup = async () => { const r = await post('/api/backup', {}); okPopup(t('backup_done') + ' ' + r.file); render(); };
window.doRestore = async f => { if (!confirm(t('restore_confirm'))) return; const r = await post('/api/restore', { file: f }); okPopup(t('restore_done') + ' ' + r.safety_backup); render(); };
window.loadDemo = async () => { try { await post('/api/demo/load', {}); STATE.demo_loaded = true; okPopup(t('demo_loaded_msg')); render(); } catch (e) { msg(e.message, 'err'); } };
window.removeDemo = () => { confirmDelete(t('demo_remove'), async () => { try { await post('/api/demo/remove', {}); STATE.demo_loaded = false; okPopup(t('demo_removed_msg')); render(); } catch (e) { msg(e.message, 'err'); } }); };
window.importPreview = async () => { const r = await post('/api/import/preview', { table: val('im_table'), csv: val('im_csv') }); $('#im_out').innerHTML = `<b>${r.count} ${t('rows_l')}</b> — ${t('columns_l')}: ${esc((r.columns || []).join(', '))}<pre>${esc(JSON.stringify(r.preview, null, 1))}</pre>`; };
window.importApply = async () => { const r = await post('/api/import/apply', { table: val('im_table'), csv: val('im_csv') }); okPopup(t('import_done') + ' ' + r.imported + ' ' + t('rows_l')); render(); };

/* staff permission keys with EN + Urdu labels for the tick-box grid */
const PERMS_UI = [['dashboard', 'Dashboard', 'ڈیش بورڈ', 'डैशबोर्ड'], ['vehicles', 'Vehicles / Gate entry', 'گاڑیاں / گیٹ انٹری', 'गाड़ियाँ / गेट एंट्री'],
  ['grinding', 'Grinding & Production entry', 'پسائی و پیداوار انٹری', 'पिसाई और उत्पादन एंट्री'], ['production', 'Bags production (also opens Grinding & Production)', 'تھیلے پیداوار (پسائی و پیداوار بھی کھولتا ہے)', 'बोरे उत्पादन (पिसाई और उत्पादन भी खोलता है)'],
  ['trade', 'Trade (Buy / Sell / Outside)', 'تجارت (خرید / فروخت / باہر)', 'व्यापार (ख़रीद / बिक्री / बाहर)'], ['parties', 'Parties & Ledger', 'پارٹیاں / کھاتہ', 'पार्टियाँ / खाता'],
  ['payments', 'Payments', 'ادائیگیاں', 'भुगतान'], ['expenses', 'Expenses', 'اخراجات', 'खर्चे'],
  ['cashbook', 'Cash Book & Day-End', 'کیش بک / دن کا اختتام', 'कैश बुक / दिन-अंत'], ['workers', 'Workers / Attendance / Theka', 'مزدور / حاضری / ٹھیکہ', 'मज़दूर / हाज़िरी / ठेका'],
  ['reports', 'Reports', 'رپورٹس', 'रिपोर्ट']];
function permGridHTML(sel){
  sel = sel || [];
  return `<div class="permgrid">${PERMS_UI.map(([k, en, ur, hi]) =>
    `<label><input type="checkbox" class="nu_perm" value="${k}" ${sel.includes(k) ? 'checked' : ''}> ${PREFS.lang === 'ur' ? ur : PREFS.lang === 'hi' ? hi : en}</label>`).join('')}</div>`;
}
let LAST_USERS = [];
let EDIT_USER = null;
VIEWS.logins = async el => {
  await loadBase();
  const users = STATE.user.role === 'owner' ? await get('/api/users') : [];
  LAST_USERS = users;
  EDIT_USER = null;
  el.innerHTML = `<div class="card"><h2>👥 ${t('logins')}</h2>
   ${STATE.user.role !== 'owner' ? '<p class="muted">' + t('only_owner_logins') + '</p>' : `
   <div class="row"><div class="field"><label>${t('username')} *</label><input id="nu_user"></div>
   <div class="field"><label>${t('password')} *</label><input id="nu_pass" type="password"></div>
   <div class="field"><label>${t('email_l')}</label><input id="nu_email" type="email"></div>
   <div class="field"><label>${t('role_l')}</label><select id="nu_role" onchange="nuRoleUI()"><option value="manager">${t('role_manager_l')}</option><option value="staff">${t('role_staff_l')}</option>${STATE.edition === 'pc' ? '' : `<option value="client">${t('role_client_l')}</option>`}<option value="owner">${t('role_owner_l')}</option><option value="demo">${t('role_demo_l')}</option></select></div>
   <div class="field" ${STATE.edition === 'pc' ? 'style="display:none"' : ''}><label>${t('client_party')}</label><select id="nu_party" onchange="nuPartyEmail()"><option value="">—</option>${partyOpts()}</select></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><span><button id="nu_btn" onclick="addUser()">${t('add')}</button>
   <button class="ghost" id="nu_cancel" style="display:none" onclick="cancelEditUser()">${t('cancel_l')}</button></span></div></div>
   <div class="field" id="nu_perms_wrap" style="display:none"><label>${t('staff_access_t')}</label><div id="nu_perms">${permGridHTML([])}</div></div>
   <div class="wrap"><table><tr><th>${t('username')}</th><th>${t('role_l')}</th><th>${t('party')}</th><th>${t('access_staff')}</th><th></th></tr>
   ${users.map(x => `<tr><td><span style="display:inline-flex;align-items:center;gap:7px">${avatarHTML(x.id, x.has_avatar, x.avatar_ver, x.display_name || x.username)}<span>${esc(x.display_name || x.username)}${x.display_name ? `<br><span class="muted small">${esc(x.username)}</span>` : ''}${x.email ? `<br><span class="muted small">✉ ${esc(x.email)}</span>` : ''}${x.phone ? `<br><span class="muted small">📱 ${esc(x.phone)}</span>` : ''}</span></span></td><td>${t('role_' + x.role + '_l') || x.role}</td><td>${x.party_id ? esc((CACHE.parties.find(p => p.id === x.party_id) || {}).name || x.party_id) : ''}</td>
   <td class="small">${x.role === 'staff' ? (x.perms || []).map(p => { const f = PERMS_UI.find(q => q[0] === p); return f ? (PREFS.lang === 'ur' ? f[2] : PREFS.lang === 'hi' ? f[3] : f[1]) : p; }).join(', ') : ''}</td>
   <td><button class="small ghost" onclick="editUser(${x.id})">${t('edit')}</button> <button class="small ghost" onclick="resetPw(${x.id})">${t('reset_pw')}</button> <button class="small danger" onclick="delUser(${x.id})">${t('del')}</button></td></tr>`).join('')}</table></div>
   <p class="small muted">${STATE.edition === 'pc' ? t('staff_note_pc') : t('staff_note')}</p>`}</div>`;
};
window.nuRoleUI = () => { const w = $('#nu_perms_wrap'); if (w) w.style.display = val('nu_role') === 'staff' ? '' : 'none'; };
/* round 12: picking the party for a client login prefills the email
   box from the party's own email (only while the box is empty — the
   same one-way convenience as WhatsApp's 'Same as Phone') */
window.nuPartyEmail = () => {
  const em = $('#nu_email'); if (!em || em.value) return;
  const p = (CACHE.parties || []).find(x => String(x.id) === String(val('nu_party')));
  if (p && p.email) em.value = p.email;
};
window.editUser = id => {
  const x = LAST_USERS.find(u => u.id === id); if (!x) return;
  EDIT_USER = id;
  $('#nu_user').value = x.username; $('#nu_user').disabled = true;
  $('#nu_pass').value = '';
  $('#nu_email').value = x.email || '';
  $('#nu_role').value = x.role;
  $('#nu_party').value = x.party_id || '';
  $('#nu_perms').innerHTML = permGridHTML(x.perms || []);
  nuRoleUI();
  $('#nu_btn').textContent = t('save_changes');
  $('#nu_cancel').style.display = '';
  window.scrollTo(0, 0);
  msg(x.username + ' ' + t('edit_user_msg'));
};
window.cancelEditUser = () => { EDIT_USER = null; render(); };
window.addUser = async () => {
  const role = val('nu_role');
  const perms = role === 'staff' ? [...document.querySelectorAll('.nu_perm:checked')].map(x => x.value) : [];
  try {
    if (EDIT_USER) {
      await post('/api/users/update', { user_id: EDIT_USER, role, party_id: val('nu_party') || null, perms, email: val('nu_email') });
      EDIT_USER = null;
      okPopup(t('login_updated'));
    } else {
      if (!reqCheck([['nu_user', 'fl_user', 'text'], ['nu_pass', 'fl_pass', 'text']])) return;
      const _cr = await post('/api/users', { username: val('nu_user'), password: val('nu_pass'), role, party_id: val('nu_party') || null, perms, email: val('nu_email') });
      okPopup(t('login_created') + credLine(_cr.cred));
    }
    render();
  } catch (e) { msg(e.message, 'err'); }
};
/* round 12: the owner's result line after a credential send —
   per channel: sent, or not sent with the server's own reason */
function credLine(cred){
  if (!cred) return '';
  const f = c => !c ? '' : (c.sent ? '✓ ' + t('cred_sent_l') : '✗ ' + (c.detail || ''));
  return ' — WhatsApp: ' + f(cred.whatsapp) + ' · Email: ' + f(cred.email);
}
window.resetPw = async id => { const pw = prompt(t('new_pw')); if (!pw) return; const r = await post('/api/users/password', { user_id: id, password: pw }); okPopup('Password badal gaya ✓' + credLine(r.cred)); };
window.delUser = id => {
  const x = (typeof LAST_USERS !== 'undefined' ? LAST_USERS : []).find(u => u.id === id);
  confirmDelete('Login' + (x ? ': ' + x.username : ' #' + id), async () => {
    try { await post('/api/users/delete', { user_id: id }); okPopup(t('deleted_ok2')); render(); }
    catch (e) { msg(e.message, 'err'); }
  });
};

VIEWS.machines = async el => {
  await loadBase();
  const d = await get('/api/machines');
  ME_CACHE = d.entries; MC_CACHE = d.machines; EDIT_MC = null; EDIT_ME = null;
  const wtypes = [['Service', t('service')], ['Repair', t('repair')], ['Part Change', t('part_change')], ['Other', t('other_l')]];
  el.innerHTML = `${accHead('machines','machines','🔧',t('add_machine'),t('accd_machines'),'machines')}<div class="card">
   <div class="row"><div class="field"><label>${t('machine_name')} *</label><input id="mc_name"></div>
   <div class="field"><label>${t('note')}</label><input id="mc_note"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button id="mc_save" onclick="addMachine()">${t('add')}</button> <button id="mc_cancel" class="ghost" style="display:none" onclick="cancelMachineEdit()">${t('cancel_l')}</button></div></div>
   <p id="mc_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <div class="wrap"><table><tr><th>${t('machine_name')}</th><th>${t('note')}</th><th></th></tr>
   ${d.machines.map(m => `<tr><td><b>${esc(m.name)}</b></td><td>${esc(m.note || '')}</td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editMachine(${m.id})">${t('edit')}</button>` : ''} ${delBtn('machines', m.id)}</td></tr>`).join('') || '<tr><td class="muted">—</td></tr>'}</table></div></div>${accEnd()}
  ${accHead('machines','diary','📖',t('maint_diary'),t('accd_diary'))}<div class="card">
   <div class="row"><div class="field"><label>${t('date')}</label><input id="me_date" type="date" value="${todayStr()}"></div>
   <div class="field"><label>${t('machine_l')}</label><select id="me_machine">${d.machines.map(m => `<option value="${m.id}">${esc(m.name)}</option>`).join('')}</select></div>
   <div class="field"><label>${t('work_type')}</label><select id="me_type">${wtypes.map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select></div>
   <div class="field"><label>${t('cost_l')}</label><input id="me_cost" type="number" value="0"></div>
   <div class="field"><label>${t('next_due')}</label><input id="me_due" type="date"></div></div>
   <div class="field"><label>${t('detail_l')}</label><input id="me_detail"></div>
   <p id="me_editing" class="small" style="display:none;color:var(--gold,#b8860b)">${t('editing_l')}</p>
   <button id="me_save" onclick="addMachineEntry()">${t('save')}</button> <button id="me_cancel" class="ghost" style="display:none" onclick="cancelMachineEntryEdit()">${t('cancel_l')}</button>
   <div class="wrap" style="margin-top:10px"><table><tr><th>${t('date')}</th><th>${t('machine_l')}</th><th>${t('work_type')}</th><th>${t('detail_l')}</th><th class="num">${t('cost_l')}</th><th>${t('next_due')}</th><th></th></tr>
   ${d.entries.map(e => `<tr><td>${e.date}</td><td>${esc(e.machine_name || '')}</td><td>${esc(e.work_type)}</td><td>${esc(e.detail || '')}</td>
   <td class="num">${fmt(e.cost)}</td><td>${esc(e.next_due || '')}</td>
   <td>${isOwner() ? `<button class="small ghost" onclick="editMachineEntry(${e.id})">${t('edit')}</button> <button class="small danger" onclick="delMachineEntry(${e.id},${e.expense_id || 0})">${t('del')}</button>` : ''}</td></tr>`).join('') || '<tr><td class="muted">—</td></tr>'}</table></div>
   <p class="small muted">${t('linked_expense')}: Machine</p></div>${accEnd()}`;
};
window.addMachine = async () => {
  if (!reqCheck([['mc_name', 'fl_name', 'text']])) return;
  try { await post('/api/machines', { name: val('mc_name'), note: val('mc_note') }); okPopup(t('saved')); render(); }
  catch (e) { msg(e.message, 'err'); }
};
window.addMachineEntry = async () => {
  if (!reqCheck([['me_machine', 'fl_machine', 'text'], ['me_date', 'fl_date', 'text'], ['me_type', 'fl_work', 'text']])) return;
  try { await post('/api/machine-entries', { date: val('me_date'), machine_id: val('me_machine'),
    work_type: val('me_type'), detail: val('me_detail'), cost: num('me_cost'), next_due: val('me_due') });
    okPopup(t('maint_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.editMachine = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = MC_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_MC = id;
  $('#mc_name').value = r.name || '';
  $('#mc_note').value = r.note || '';
  editSwap('mc_save', 'updateMachine()', 'mc_cancel', 'mc_editing');
};
window.updateMachine = async () => {
  if (!reqCheck([['mc_name', 'fl_name', 'text']])) return;
  try { await post('/api/machines', { id: EDIT_MC, name: val('mc_name'), note: val('mc_note') }); EDIT_MC = null; okPopup(t('saved')); render(); }
  catch (e) { msg(e.message, 'err'); }
};
window.cancelMachineEdit = () => { EDIT_MC = null; render(); };
window.editMachineEntry = id => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  const r = ME_CACHE.find(x => x.id === id); if (!r) return;
  EDIT_ME = id;
  $('#me_date').value = r.date || todayStr();
  $('#me_machine').value = r.machine_id || '';
  $('#me_type').value = r.work_type || 'Service';
  $('#me_cost').value = r.cost || 0;
  $('#me_due').value = r.next_due || '';
  $('#me_detail').value = r.detail || '';
  editSwap('me_save', 'updateMachineEntry()', 'me_cancel', 'me_editing');
};
window.updateMachineEntry = async () => {
  if (!reqCheck([['me_machine', 'fl_machine', 'text'], ['me_date', 'fl_date', 'text'], ['me_type', 'fl_work', 'text']])) return;
  try { await post('/api/machine-entries', { id: EDIT_ME, date: val('me_date'), machine_id: val('me_machine'),
    work_type: val('me_type'), detail: val('me_detail'), cost: num('me_cost'), next_due: val('me_due') });
    EDIT_ME = null; okPopup(t('maint_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};
window.cancelMachineEntryEdit = () => { EDIT_ME = null; render(); };
window.delMachineEntry = (id, expenseId) => {
  if (!isOwner()) { msg(t('owner_only_edit'), 'err'); return; }
  confirmDelete(t('maint_entry') + ' #' + id, async () => {
    try {
      if (expenseId) { try { await post('/api/delete', { table: 'expenses', id: expenseId }); } catch (e) {} }
      await post('/api/delete', { table: 'machine_entries', id });
      okPopup(t('deleted_ok2')); render();
    } catch (e) { msg(e.message, 'err'); }
  }, t('rec_del_note'));
};

VIEWS.settings = async el => {
  const s = await get('/api/settings'); CACHE.settings = s;
  /* round 14: pill tabs instead of the accordion on this page.
     Every panel stays in the DOM ([hidden]) so saveSettings()
     keeps reading all st_* fields exactly as before. */
  const TABKEYS = ['profile', 'appearance', 'fontprint', 'voice', 'whatsapp', 'email', 'cash', 'banks'];
  let cur = accOpenKey('settings', 'profile');
  if (!TABKEYS.includes(cur) || (cur === 'appearance' && STATE.user.role !== 'owner')
      || (cur === 'whatsapp' && STATE.edition === 'pc')) cur = 'profile';
  const sTab = (key, icon, title) => `<button type="button" class="settab${cur === key ? ' active' : ''}" data-settab="${key}" role="tab" aria-selected="${cur === key}" onclick="setTab('${key}')"><span class="settabic">${icon}</span>${esc(title)}</button>`;
  const sPanel = (key, body) => `<div class="setpanel" data-setpanel="${key}" role="tabpanel"${cur === key ? '' : ' hidden'}>${body}</div>`;
  const tabs = [], panels = [];
  tabs.push(sTab('profile', '🏭', t('mill_profile')));
  panels.push(sPanel('profile', `<div class="card">
   <p class="small muted">${t('mill_profile_hint')}</p>
   <div class="row"><div class="field"><label>${t('mill_name_l')}</label><input id="st_name" value="${esc(s.mill_name)}"></div>
   <div class="field"><label>${t('mill_phone_l')}</label><input id="st_phone" value="${esc(s.mill_phone)}"></div></div>
   <div class="field"><label>${t('mill_addr_l')}</label><input id="st_addr" value="${esc(s.mill_address)}"></div>
   <div class="field"><label>${t('owner_wa_l')}</label><input id="st_owa" value="${esc(s.owner_whatsapp)}"></div>
   <div class="field"><label>${t('powder_age_days')}</label><input id="st_pagedays" type="number" value="${s.powder_age_days != null ? s.powder_age_days : 3}"></div>
   <div class="field"><label>${t('wastage_pct_l')}</label><input id="st_wastage" type="number" step="0.1" min="0" max="100" value="${s.wastage_pct != null ? s.wastage_pct : 5}"></div>
   <div class="field"><label>${t('day_shift_end_l')}</label><input id="st_dayend" type="time" value="${s.day_shift_end || '19:00'}"></div>
   <div class="field"><label>${t('night_shift_end_l')}</label><input id="st_nightend" type="time" value="${s.night_shift_end || '07:00'}"></div>
   <div class="field"><label>${t('vehicle_alert_time_l')}</label><input id="st_vatime" type="time" value="${s.vehicle_alert_time || '20:00'}"></div>
   <h3>🖼 ${t('logo_t')}</h3>
   ${s.has_logo ? `<img class="loginlogo" style="margin:0 0 8px" src="/branding/logo?v=${s.logo_ver || 0}" alt="logo">` : '<p class="small muted">' + t('logo_none') + '</p>'}
   <div class="row"><div class="field"><label>${t('logo_hint')}</label><input id="st_logo" type="file" accept="image/png,image/jpeg,image/webp"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><span><button class="small" onclick="uploadLogo()">${s.has_logo ? t('replace_logo') : t('upload_logo')}</button>
   ${s.has_logo ? '<button class="small danger" onclick="removeLogo()">' + t('remove_l') + '</button>' : ''}</span></div></div></div>`));
  if (STATE.user.role === 'owner') {
    tabs.push(sTab('appearance', '🎨', t('appearance_t')));
    panels.push(sPanel('appearance', `<div class="card">
   <p class="small muted">${t('theme_note')}</p>
   <div class="row"><div class="field"><label>${t('theme_colour_l')}</label>${accentDropdownHTML()}</div></div></div>`));
  }
  tabs.push(sTab('fontprint', '🔤', t('font_print_t')));
  panels.push(sPanel('fontprint', `<div class="card">
   <div class="row"><div class="field"><label>${t('ui_font_l')}</label><select id="st_uifont">${FONT_OPTS.map(k => `<option value="${k}" ${s.ui_font === k ? 'selected' : ''}>${t('font_' + k)}</option>`).join('')}</select></div>
   <div class="field"><label>${t('ui_size_l')}</label><select id="st_uisize">${['small', 'normal', 'large'].map(k => `<option value="${k}" ${s.ui_text_size === k ? 'selected' : ''}>${t('size_' + k)}</option>`).join('')}</select></div></div>
   <div class="row"><div class="field"><label>${t('print_font_l')}</label><select id="st_printfont">${FONT_OPTS.map(k => `<option value="${k}" ${s.print_font === k ? 'selected' : ''}>${t('font_' + k)}</option>`).join('')}</select></div>
   <div class="field"><label>${t('print_size_l')}</label><select id="st_printsize">${['small', 'normal', 'large'].map(k => `<option value="${k}" ${s.print_text_size === k ? 'selected' : ''}>${t('size_' + k)}</option>`).join('')}</select></div>
   <div class="field"><label>${t('print_bold_l')}</label><input id="st_printbold" type="checkbox" ${s.print_bold_headings ? 'checked' : ''}></div></div>
   <div class="row"><div class="field"><label>${t('print_copies_l')}</label><select id="st_printcopies">${[1, 2, 3].map(k => `<option value="${k}" ${(s.print_voucher_copies || 2) === k ? 'selected' : ''}>${k}</option>`).join('')}</select></div></div>
   <button onclick="saveSettings()">${t('save')}</button></div>`));
  tabs.push(sTab('voice', '🔊', t('voice_alerts_t')));
  panels.push(sPanel('voice', `<div class="card">
   <div class="row"><div class="field"><label>${t('voice_master_l')}</label><input id="st_vmaster" type="checkbox" ${s.voice_alerts ? 'checked' : ''}></div>
   <div class="field"><label>${t('voice_vehicles_l')}</label><input id="st_vveh" type="checkbox" ${s.voice_vehicles ? 'checked' : ''}></div>
   <div class="field"><label>${t('voice_payments_l')}</label><input id="st_vpay" type="checkbox" ${s.voice_payments ? 'checked' : ''}></div></div>
   <button onclick="saveSettings()">${t('save')}</button></div>`));
  if (STATE.edition !== 'pc') {
    tabs.push(sTab('whatsapp', '💬', t('wa_auto_t')));
    panels.push(sPanel('whatsapp', `<div class="card">
   ${infoBoxes('ib_wa_need', 'ib_wa_tips')}
   <p class="small muted">${t('wa_note')} <b>${(s.templates || []).map(x => esc(typeof x === 'string' ? x : x.name)).join(', ')}</b> (${esc(s.wa_token_hint || 'not set')})</p>
   <details class="guidebox"><summary>❓ ${t('wa_guide_t')}</summary><div class="small" style="line-height:1.7">${t('wa_guide')}</div></details>
   <div class="row"><div class="field"><label>Phone Number ID</label><input id="st_waid" value="${esc(s.wa_phone_id)}"></div>
   <div class="field"><label>Access Token</label><input id="st_watok" type="password" placeholder="${s.wa_token_set ? '•••• set hai' : 'token'}"></div></div>
   <h3>${t('sms_t')}</h3>
   <p class="small muted">${t('sms_note')}</p>
   <div class="row"><div class="field"><label>SMS API URL</label><input id="st_smsurl" value="${esc(s.sms_url)}"></div>
   <div class="field"><label>SMS key</label><input id="st_smskey" type="password" placeholder="${s.sms_key_set ? '•••• set hai' : ''}"></div>
   <div class="field"><label>Sender ID</label><input id="st_smssender" value="${esc(s.sms_sender)}"></div></div></div>`));
  }
  tabs.push(sTab('email', '📧', t('email_t')));
  panels.push(sPanel('email', `<div class="card">
   ${infoBoxes('ib_mail_need', 'ib_mail_tips')}
   <div class="row"><div class="field"><label>${t('mail_preset_l')}</label><select id="st_mailpreset" onchange="mailPreset(this.value)">${MAIL_PRESET_KEYS.map(k => `<option value="${k}" ${(s.mail_preset || 'custom') === k ? 'selected' : ''}>${esc(t('mail_preset_' + k))}</option>`).join('')}</select></div></div>
   ${MAIL_PRESET_KEYS.map(k => `<p class="small mailpnote" data-mailpreset="${k}"${(s.mail_preset || 'custom') === k ? '' : ' hidden'}>${t('mail_note_' + k)}</p>`).join('')}
   <p class="small muted">${t('email_note')}</p>
   <p class="small muted">${t('email_gmail_hint')}</p>
   <details class="guidebox"><summary>❓ ${t('email_guide_t')}</summary><div class="small" style="line-height:1.7">${t('email_guide')}</div></details>
   <div class="row"><div class="field"><label>${t('mail_on_l')}</label><input id="st_mailon" type="checkbox" ${s.mail_enabled ? 'checked' : ''}></div>
   <div class="field"><label>${t('smtp_host_l')}</label><input id="st_smtphost" value="${esc(s.smtp_host || '')}" placeholder="smtp.gmail.com"></div>
   <div class="field"><label>${t('smtp_port_l')}</label><input id="st_smtpport" type="number" value="${s.smtp_port || 587}"></div>
   <div class="field"><label>${t('smtp_sec_l')}</label><select id="st_smtpsec">${[['starttls', 'STARTTLS (587)'], ['ssl', 'SSL (465)'], ['none', 'None']].map(([k, l]) => `<option value="${k}" ${(s.smtp_security || 'starttls') === k ? 'selected' : ''}>${l}</option>`).join('')}</select></div></div>
   <div class="row"><div class="field"><label>${t('smtp_user_l')}</label><input id="st_smtpuser" value="${esc(s.smtp_user || '')}"></div>
   <div class="field"><label>${t('smtp_pass_l')}</label><input id="st_smtppass" type="password" placeholder="${s.smtp_pass_set ? '•••• set hai (' + esc(s.smtp_pass_hint || '') + ')' : ''}"></div></div>
   <div class="row"><div class="field"><label>${t('from_name_l')}</label><input id="st_fromname" value="${esc(s.smtp_from_name || '')}"></div>
   <div class="field"><label>${t('from_email_l')}</label><input id="st_fromemail" type="email" value="${esc(s.smtp_from_email || '')}"></div></div>
   <div class="field"><label>${t('sys_addr_l')}</label><input id="st_sysaddr" value="${esc(s.system_address || '')}" placeholder="https://…"></div>
   <p class="small muted">${t('sys_addr_hint')}</p>
   <h3>${t('mail_ev_t')}</h3>
   <div class="row"><div class="field"><label>${t('mail_ev_proof_l')}</label><input id="st_evproof" type="checkbox" ${s.mail_ev_proof ? 'checked' : ''}></div>
   <div class="field"><label>${t('mail_ev_payment_l')}</label><input id="st_evpay" type="checkbox" ${s.mail_ev_payment ? 'checked' : ''}></div></div>
   <div class="row"><div class="field"><label>${t('mail_ev_voucher_l')}</label><input id="st_evvoucher" type="checkbox" ${s.mail_ev_voucher ? 'checked' : ''}></div>
   <div class="field"><label>${t('mail_ev_dayend_l')}</label><input id="st_evdayend" type="checkbox" ${s.mail_ev_dayend ? 'checked' : ''}></div></div>
   <div class="row"><div class="field"><label>${t('mail_test_t')}</label><input id="st_testto" type="email"></div>
   <div class="field" style="flex:0"><label>&nbsp;</label><button class="small" onclick="testEmail()">${t('mail_test_btn')}</button></div></div>
   <p class="small muted">${t('mail_test_first')}</p>
   <p id="st_testmsg" class="small"></p>
   <button onclick="saveSettings()">${t('save')}</button></div>`));
  tabs.push(sTab('cash', '💵', t('cash_rules_t')));
  panels.push(sPanel('cash', `<div class="card">
   <div class="row"><div class="field"><label>${t('holder_limit_l')}</label><input id="st_cholderlimit" type="number" value="${s.cash_holder_limit != null ? s.cash_holder_limit : 200000}"></div>
   <div class="field"><label>${t('approval_limit_l')}</label><input id="st_capprovallimit" type="number" value="${s.cash_approval_limit != null ? s.cash_approval_limit : 25000}"></div></div>
   <h3>${t('bank_list_t')}</h3>
   ${(s.banks || []).map(b => `<div class="row"><div class="field"><label>${esc(b)} (${t('balance')})</label><input type="number" class="st_bank_open" data-bank="${esc(b)}" value="${(s.bank_opening || {})[b] != null ? (s.bank_opening || {})[b] : 0}"></div></div>`).join('') || '<p class="small muted">' + t('bank_open_hint') + '</p>'}
   <button onclick="saveSettings()">${t('save')}</button></div>`));
  tabs.push(sTab('banks', '🏦', t('bank_list_t')));
  panels.push(sPanel('banks', `<div class="card">
   <div class="field"><label>${t('bank_list_t')}</label><textarea id="st_banks" rows="3">${esc((s.banks || []).join('\n'))}</textarea></div>
   <div class="kv"><span>${t('db_file_l')}</span><b class="small">${esc(s.db_path || '')}</b></div>
   <div class="kv"><span>${t('bio_addr_l')}</span><b>http://${esc(s.lan_ip)}:${s.device_port}/iclock/cdata</b></div>
   <div class="row"><div class="field"><label>${t('backup_dir_l')}</label><input id="st_bdir" placeholder="khali = default"></div>
   <div class="field"><label>${t('move_db_l')}</label><input id="st_newdb" placeholder="e.g. E:\\MillData2"></div></div>
   <button onclick="saveSettings()">${t('save')}</button></div>`));
  el.innerHTML = `<div class="settabs" role="tablist" aria-label="${esc(t('settings'))}">${tabs.join('')}</div>`
    + panels.join('')
    + `<div class="setfoot"><button type="button" class="setsave" onclick="saveSettings()">💾 ${t('save_settings')}</button></div>`;
};
window.testEmail = async () => {
  const p = $('#st_testmsg'); if (p) p.textContent = '…';
  try {
    const r = await post('/api/settings/test-email', { to: val('st_testto') });
    if (p) { p.textContent = r.ok ? '✓ ' + t('mail_sent_to') + ' ' + r.to : '✗ ' + (r.detail || '');
             p.style.color = r.ok ? 'var(--ok,#0c7a4e)' : '#b00020'; }
  } catch (e) { if (p) { p.textContent = '✗ ' + e.message; p.style.color = '#b00020'; } }
};
window.uploadLogo = async () => {
  const f = $('#st_logo');
  if (!f || !f.files || !f.files[0]) { msg(t('logo_pick'), 'warn'); return; }
  try {
    const url = URL.createObjectURL(f.files[0]);
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });
    const scale = Math.min(1, 256 / Math.max(img.width || 1, img.height || 1));
    const cv = document.createElement('canvas');
    cv.width = Math.max(1, Math.round(img.width * scale));
    cv.height = Math.max(1, Math.round(img.height * scale));
    cv.getContext('2d').drawImage(img, 0, 0, cv.width, cv.height);
    URL.revokeObjectURL(url);
    const dataUrl = cv.toDataURL('image/png');
    const r = await post('/api/settings', { logo_data: dataUrl.split(',')[1], logo_mime: 'image/png' });
    STATE.mill.has_logo = true; STATE.mill.logo_ver = r.logo_ver;
    okPopup(t('logo_done')); render();
  } catch (e) { msg(e.message || 'Logo upload nahi hua', 'err'); }
};
window.removeLogo = () => {
  confirmDelete(t('logo_t'), async () => {
    try {
      const r = await post('/api/settings', { logo_remove: 1 });
      STATE.mill.has_logo = false; STATE.mill.logo_ver = r.logo_ver;
      okPopup(t('logo_removed')); render();
    } catch (e) { msg(e.message, 'err'); }
  });
};
window.saveSettings = async () => {
  try { const bankOpening = {};
    document.querySelectorAll('.st_bank_open').forEach(i => { bankOpening[i.getAttribute('data-bank')] = parseFloat(i.value) || 0; });
    const r = await post('/api/settings', { mill_name: val('st_name'), mill_phone: val('st_phone'), mill_address: val('st_addr'),
    owner_whatsapp: val('st_owa'), wa_phone_id: val('st_waid'), wa_token: val('st_watok'), sms_url: val('st_smsurl'),
    sms_key: val('st_smskey'), sms_sender: val('st_smssender'), banks: val('st_banks').split('\n').map(x => x.trim()).filter(Boolean),
    powder_age_days: num('st_pagedays'), wastage_pct: num('st_wastage'),
    day_shift_end: val('st_dayend'), night_shift_end: val('st_nightend'), vehicle_alert_time: val('st_vatime'),
    ui_font: val('st_uifont'), ui_text_size: val('st_uisize'),
    print_font: val('st_printfont'), print_text_size: val('st_printsize'),
    print_bold_headings: ($('#st_printbold') && $('#st_printbold').checked) ? 1 : 0,
    print_voucher_copies: parseInt(val('st_printcopies') || '2', 10), cash_holder_limit: num('st_cholderlimit'), cash_approval_limit: num('st_capprovallimit'), bank_opening: bankOpening,
    voice_alerts: ($('#st_vmaster') && $('#st_vmaster').checked) ? 1 : 0,
    voice_vehicles: ($('#st_vveh') && $('#st_vveh').checked) ? 1 : 0,
    voice_payments: ($('#st_vpay') && $('#st_vpay').checked) ? 1 : 0,
    mail_preset: val('st_mailpreset'),
    smtp_host: val('st_smtphost'), smtp_port: num('st_smtpport'), smtp_security: val('st_smtpsec'),
    smtp_user: val('st_smtpuser'), smtp_pass: val('st_smtppass'), smtp_from_name: val('st_fromname'),
    smtp_from_email: val('st_fromemail'), system_address: val('st_sysaddr'),
    mail_enabled: ($('#st_mailon') && $('#st_mailon').checked) ? 1 : 0,
    mail_ev_proof: ($('#st_evproof') && $('#st_evproof').checked) ? 1 : 0,
    mail_ev_payment: ($('#st_evpay') && $('#st_evpay').checked) ? 1 : 0,
    mail_ev_voucher: ($('#st_evvoucher') && $('#st_evvoucher').checked) ? 1 : 0,
    mail_ev_dayend: ($('#st_evdayend') && $('#st_evdayend').checked) ? 1 : 0,
    backup_dir: val('st_bdir'), new_db_folder: val('st_newdb') });
    STATE.mill.name = val('st_name'); STATE.mill.phone = val('st_phone'); STATE.mill.address = val('st_addr');
    STATE.voice = { voice_alerts: ($('#st_vmaster') && $('#st_vmaster').checked) ? 1 : 0,
      voice_vehicles: ($('#st_vveh') && $('#st_vveh').checked) ? 1 : 0, voice_payments: ($('#st_vpay') && $('#st_vpay').checked) ? 1 : 0 };
    STATE.font = { ui_font: val('st_uifont'), ui_text_size: val('st_uisize'), print_font: val('st_printfont'),
                   print_text_size: val('st_printsize'), print_bold_headings: ($('#st_printbold') && $('#st_printbold').checked) ? 1 : 0,
                   print_voucher_copies: parseInt(val('st_printcopies') || '2', 10) };
    applyFonts();
    document.title = (STATE.mill.name || t('app'));
    okPopup(t('settings_saved')); render(); } catch (e) { msg(e.message, 'err'); }
};

VIEWS.help = el => {
  const pc = STATE.edition === 'pc';
  const items = [t('help_1'), t('help_2'), t('help_3'), pc ? t('help_4_pc') : t('help_4'),
                 t('help_5'), pc ? t('help_6_pc') : t('help_6'), t('help_7'), t('help_8')];
  el.innerHTML = `<div class="card"><h2>❓ ${t('help')}</h2>
  <ol style="line-height:1.9">${items.map(x => `<li>${x}</li>`).join('')}</ol></div>`;
};

/* client view */
/* round 12: self-service profile — every login (owner / manager /
   staff / client) edits ONLY its own display name, phone/WhatsApp,
   email, picture and password. Username, role, permissions and the
   party link are owner-only and render here as plain text, never as
   controls. A client's contact save also updates the linked party. */
VIEWS.profile = async el => {
  const pr = await get('/api/profile');
  const u = STATE.user;
  const ro = u.role === 'demo';
  el.innerHTML = `<div class="card"><h2>👤 ${t('profile_t')}</h2>
   <div class="kv"><span>${t('username')}</span><b>${esc(pr.username)}</b></div>
   <div class="kv"><span>${t('role_l')}</span><b>${t('role_' + pr.role + '_l') || pr.role}</b></div>
   ${pr.party_name ? `<div class="kv"><span>${t('party')}</span><b>${esc(pr.party_name)}</b></div>` : ''}
   <div class="row" style="margin-top:12px;align-items:flex-start;gap:18px">
     <div class="field" style="flex:0 0 auto"><label>${t('avatar_l')}</label>
       <div>${avatarHTML(u.id, pr.has_avatar, pr.avatar_ver, pr.display_name || pr.username, 'prof-av')}</div>
       ${ro ? '' : `<label class="small ghost" style="display:inline-block;margin-top:8px;cursor:pointer;padding:4px 10px;border:1px solid var(--line);border-radius:8px">${t('avatar_change_l')}<input type="file" accept="image/png,image/jpeg,image/webp" style="display:none" onchange="avatarPick(this)"></label>
       ${pr.has_avatar ? `<button class="small danger" onclick="avatarRemove()">${t('avatar_remove_l')}</button>` : ''}
       <div class="small muted" style="max-width:190px;margin-top:6px">${t('avatar_hint')}</div>`}
     </div>
     <div style="flex:1;min-width:220px">
       <div class="field"><label>${t('disp_name_l')}</label><input id="pf_name" value="${esc(pr.display_name || '')}" ${ro ? 'disabled' : ''}></div>
       <div class="field"><label>${t('phone_wa_l')}</label><input id="pf_phone" value="${esc(pr.phone || '')}" ${ro ? 'disabled' : ''}></div>
       <div class="field"><label>${t('email_l')}</label><input id="pf_email" type="email" value="${esc(pr.email || '')}" ${ro ? 'disabled' : ''}></div>
       ${ro ? '' : `<button onclick="saveProfile()">${t('save_changes')}</button>`}
     </div>
   </div></div>
   ${ro ? '' : `<div class="card"><h2>🔑 ${t('password')}</h2>
   <div class="row"><div class="field"><label>${t('cur_pw_l')} *</label><input id="pf_curpw" type="password"></div>
   <div class="field"><label>${t('new_pw')} *</label><input id="pf_newpw" type="password"></div></div>
   <button onclick="saveProfilePw()">${t('save_changes')}</button></div>`}`;
};
window.saveProfile = async () => {
  try {
    const r = await post('/api/profile', { display_name: val('pf_name'), phone: val('pf_phone'), email: val('pf_email') });
    if (STATE.user && r.display_name !== undefined) STATE.user.display_name = r.display_name;
    okPopup(t('profile_saved')); render();
  } catch (e) { msg(e.message, 'err'); }
};
window.saveProfilePw = async () => {
  try { await post('/api/profile/password', { current_password: val('pf_curpw'), new_password: val('pf_newpw') }); okPopup(t('pw_changed_l')); render(); }
  catch (e) { msg(e.message, 'err'); }
};
window.avatarPick = inp => {
  const f = inp.files && inp.files[0]; if (!f) return;
  if (f.size > 2 * 1024 * 1024) { msg(t('avatar_hint'), 'err'); return; }
  const img = new Image();
  img.onload = () => {
    /* downscale to at most 256px on the longest side — the stored
       picture stays tiny; the server still enforces the 2 MB cap */
    const s = Math.min(1, 256 / Math.max(img.width, img.height));
    const c = document.createElement('canvas');
    c.width = Math.max(1, Math.round(img.width * s)); c.height = Math.max(1, Math.round(img.height * s));
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    const url = c.toDataURL('image/jpeg', 0.85);
    URL.revokeObjectURL(img.src);
    post('/api/profile/avatar', { avatar_data: url.split(',')[1], avatar_mime: 'image/jpeg' })
      .then(async () => { const st = await get('/api/state'); if (st && st.user) STATE.user = st.user; okPopup(t('profile_saved')); render(); })
      .catch(e => msg(e.message, 'err'));
  };
  img.onerror = () => msg(t('avatar_hint'), 'err');
  img.src = URL.createObjectURL(f);
};
window.avatarRemove = async () => {
  try { await post('/api/profile/avatar', { avatar_remove: 1 }); const st = await get('/api/state'); if (st && st.user) STATE.user = st.user; okPopup(t('profile_saved')); render(); }
  catch (e) { msg(e.message, 'err'); }
};
VIEWS.mykhata = async el => {
  const d = await get('/api/my/khata');
  el.innerHTML = `<div class="card"><h2>👤 ${esc(d.party.name)} — ${t('client_view')}</h2>
   <div class="grid">
    <div class="stat"><div class="n">${fmt(d.balance)}</div><div class="l">${t('balance')} ${d.balance > 0 ? '(' + t('to_receive') + ')' : d.balance < 0 ? '(' + t('to_pay') + ')' : '(' + t('bal_clear') + ')'}</div></div>
    <div class="stat"><div class="n">${tonsDisp(d.stock.rock_waiting_t)}</div><div class="l">${t('rock')} ${t('waiting_l')}</div></div>
    <div class="stat"><div class="n">${tonsDisp(d.stock.powder_ready_t)}</div><div class="l">${t('powder')} ${t('ready_l')} (${d.stock.bags_ready} ${t('bags')})</div></div>
   </div>
   <p><a target="_blank" href="/print/party/${d.party.id}?u=${PREFS.unit}">🖨 ${t('print')} ${t('khata')}</a></p></div>
  ${accHead('mykhata','khata','📒',t('khata'),t('accd_khata'),'khata')}<div class="card"><div class="wrap"><table>
   <tr><th>${t('date')}</th><th>${t('description')}</th><th class="num">${t('debit')}</th><th class="num">${t('credit')}</th><th class="num">${t('balance')}</th></tr>
   ${d.entries.map(e => `<tr><td>${e.date}</td><td>${esc(e.desc)}</td><td class="num">${e.debit ? fmtN(e.debit) : ''}</td><td class="num">${e.credit ? fmtN(e.credit) : ''}</td><td class="num">${fmtN(e.balance)}${balTag(e.balance)}</td></tr>`).join('')}</table></div></div>${accEnd()}
  ${accHead('mykhata','proof','🧾',t('upload_proof'),t('accd_proofup'))}<div class="card">
   <div class="row"><div class="field"><label>${t('amount')} *</label><input id="pf_amount" type="number"></div>
   <div class="field"><label>${t('date')}</label><input id="pf_date" type="date" value="${todayStr()}"></div></div>
   ${attachHTML('proofs', 0)}
   <div class="field"><label>${t('note')}</label><input id="pf_note" placeholder="JazzCash / bank slip no…"></div>
   <button onclick="sendProof()">${t('send')}</button>
   <h3>${t('my_proofs')}</h3>
   ${d.proofs.map(p => `<div class="kv"><span>${p.date} — ${fmt(p.amount)}</span><b>${t(p.status) || p.status}</b></div>`).join('') || '<span class="muted">—</span>'}</div>${accEnd()}`;
};
window.sendProof = async () => {
  try {
    const attId = await uploadAttachment('proofs', 0);
    await post('/api/proofs', { amount: num('pf_amount'), date: val('pf_date'), note: val('pf_note'), attachment_id: attId });
    okPopup(t('proof_sent')); render();
  } catch (e) { msg(e.message, 'err'); }
};

boot();
