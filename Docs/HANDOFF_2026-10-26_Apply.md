# Apply (prepayment -> GRN -> create invoice) handoff, 2026-10-26

## Workflows (Oracle/Apply)
- 4a_Read_Report: report rows, only Vendor Site Code = LC OPENING CHAR. LC no and company parsed from Description (`LC- DC BD...` keeps the DC prefix; `Ref- <same LC>` and trailing `S.R.L` handled; bank returned as 3rd field).
- 4c_LC_Receipt: GRN by LC + company. Order: full name, first word, Proper case, lower. Standard Chartered adds `-L` to the LC; company `M AND J` becomes `M&J`. Outputs Receipt_Number, Status, Supplier_Used (exact Oracle supplier name read from the found invoice).
- 4b_Lookup_All / 5_Test_Sheet: use 4c; Company is replaced by Supplier_Used when the GRN was found by a shorter name.
- 4_Open_Unit: always closes open forms first, then Switch Responsibility > Navigator > Invoices.
- 6_Open_Batch (Unit, Batch_Name default UNIT_RPA): clean start, Navigator > Invoice Batches, root BatchControl.xaml, clicks Invoices until "Invoice Workbench (UNIT Payable Invoice) - batch" shows.
- 6_Java_Entry: copy of root JavaEntry (window title and GFL names wildcarded). Root JavaEntry/Main untouched.
- 6_GRN_Match: copy of root GRNMatching (the "sequence" note read tolerates absence).
- 6a_Find_Invoice: F11 / invoice number / Ctrl+F11 in the batch workbench.
- 6b_Apply_Prepayment: Validate, Apply/Unapply (query prepayment number, tick Apply, OK on date Note, type Gl_Date, Apply/Unapply, Save, close form), Validate, Initiate Approval. Args Skip_Apply for retries.
- 6_Create_Invoice: one row end to end. Args: Unit, Open_Batch, Skip_Entry, Skip_Match, Invoice_Date (MANDATORY), Trading_Partner (bank), Site_Name, Prepayment_Invoice, Invoice_Amount, Currency, Description, LC_Number, Receipt_Number, Supplier_Name. New invoice number = prepayment invoice + "M".

## Rules learned
- Test server GL period is open for FEB 2026 only: always pass a Feb Invoice_Date (tests used 26-FEB-2026). Today's date gives APP-SQLAP-10006.
- Oracle Java check boxes and buttons in these dialogs need HARDWARE clicks (ui:Click SimulateClick=False). Simulated checks are ignored. The Invoice Actions dialog keeps old ticks: 6b unticks every box whose attribute `checked` = True first.
- Close the Apply form with its own title-bar button, not the main toolbar Close Form (that closes everything).
- Supplier in the match form must be the exact Oracle name (use Supplier_Used, never type a prefix; never pass non-ASCII names through CLI args).
- BatchControl fails if the batch form is already showing: Open_Batch always starts clean.
- Oracle search is case sensitive; stale hidden frames of other units can break wildcard selectors, so closing forms first matters.

## Verified live (GFL, test server)
- 5636610366 March-57M (Citibank, GRN 197876): Validated, Applied 750.00, Approval Initiated.
- 411012373533 June-71M (Standard Chartered, GRN 201802): Validated, Applied 1156.67, Approval Initiated.
- Each stage was verified, but the full chain (Create_Invoice with no Skip_* flags) has not run unattended. Untested: OK on the date Note then typing Gl_Date inside 6b.

## Not built yet
- Runner over report rows (read report, 4c lookup, Create_Invoice per row, log/report result).
- Other units (CAL, CGL, CWPL, GWN), batch names UNIT_RPA.
- Unfinished test leftovers are in the GFL_RPA batch only for the two finished invoices above (both complete).

## Run example (one row)
uip rpa run --file-path "Oracle/Apply/Oracle_Apply_6_Create_Invoice.xaml" --project-dir . --input-arguments "Unit=GFL" "Open_Batch:=true" "Invoice_Date=26-FEB-2026" ... (see args above)
