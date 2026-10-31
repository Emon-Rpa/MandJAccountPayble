# Accounts Payable: 7-division architecture (2026-10-31)

Source: PDD "Account Payable.pdf" (sections 1-30) + current project files.
Goal: split the project into 7 isolated divisions. Each division has its own
Main, can run alone, and talks to the others only through files (never by
invoking another division's workflows).

```
             +--> 2 Invoice --> 3 Payment --> 4 Clear --> 7 Reconciliation
1 Prepare ---|        (rows with      (rows with      (rows with      (checks Clear
  Data       |         Invoice OK)     Payment OK)     Clear OK)        really hit GL)
             |
5 JV        (isolated: GL download of dummy account -> journal for EUR gain/loss)
6 Apply     (isolated: prepayment report -> GRN -> invoice + apply prepayment)
```

## Handoff contract (the "work file")

Division 1 writes one prepared workbook per statement (today:
`Desktop\Accounts Payable\Output\<statement>.xlsx`, sheets CASH / TT / GRN).
Divisions 2, 3, 4, 7 read that same workbook and each owns its own status columns.
A division only picks rows where the previous division's status is success and
its own status is empty, so any division can be re-run safely.

| Division | Picks rows where | Writes columns |
|---|---|---|
| 2 Invoice | `Report` empty (clean data) and `Invoice_Status` empty | `Invoice_Number`, `Invoice_Status` |
| 3 Payment | `Invoice_Status` = success and `Payment_Number` empty | `Payment_Number`, `Payment_Status` |
| 4 Clear | `Payment_Number` valid and `Clear_Transaction` empty | `Clear_Transaction` (status), `Clear_Date` |
| 7 Reconciliation | `Clear_Transaction` = success and `Recon_Status` empty | `Recon_Status`, `Recon_GL_Ref` |

`Invoice_Status`, `Payment_Number`, `Clear_Transaction` already exist in Main.xaml.
`Payment_Status`, `Clear_Date`, `Recon_*` are new (to confirm).

## Division -> files

Shared (Common): `login.xaml`, `Oracle_Login.xaml`, `OpenJava.xaml`, `Navigator.xaml`,
`WARNINGBOX.xaml`, `ok_pop_up.xaml`, `BatchControl.xaml`, `unit.xaml`,
`mail_report_send.xaml`, `text_report.xaml`, `Mail_Trigger.xaml`.

### 1 Prepare Data (PDD 1-4, 9-12 data side, 13-14)
Bank statement -> standard format -> advice mail -> advice PDF -> enriched rows.
- `Detect_Bank.xaml`, `Bank_Statement.xaml`, `SCB_statement.xaml`, `DhakaBank.xaml`
- `Advice_pdf.xaml`, `outlook_mailbox.xaml`
- `DB_advice_reader.xaml`, `CITI_advice_reader.xaml`, `HSBC_advice_reader.xaml`
- `EUR_Action.xaml`, `BBLCANDCMLC.xaml`, `CmLC.xaml`, `ReadExcel(entryData)AndLogin_Navigation.xaml`
- `Oracle/PO_Asset/Oracle_PO_Asset.xaml` (machinery: asset date by LC)
- Rules: `Excel/Cash_Management_Entry.xlsx` (SCB_Rules, Bank_Config, EUR_Patterns, CITI, DB...), `Excel/Bank_Maps.xlsx`
- Status: Dhaka tested; SCB/CITI/HSBC built, untested after rework. Open decisions:
  DBL Sight Payment / Transfer USD-BDT / Prepayment apply, CITI NEEDS DECISION, TBD rules.
  Machinery processing (PDD 12) not built.

### 2 Invoice (PDD 15-16, 17-23, 24)
Foreign prepayment (22), local standard (23), GRN matching (24).
- `OpenJava_Invoice.xaml`, `INVOICE_NUMBER_QUERY.xaml`, `GRN_NUMBER_QUERY.xaml`
- `Foregn_Local.xaml`, `JavaEntry.xaml`, `2Lines.xaml`, `unwanted_match_screen.xaml`
- `GRNMatching.xaml`, `Action_PrePayment.xaml`, `SearchLC&Create.xaml`
- Status: in Main.xaml "If INVOICE" (CASH / TT / GRN sheets). Works on SCB data; new banks not run.

### 3 Payment (PDD 8, 25-26)
- `Go_To_Payment.xaml`, `Payments.xaml`, `Enter_Adjust_Invoice.xaml`
- Status: in Main.xaml "If PAYMENT". Writes `Payment_Number`.

### 4 Clear
- `Clear_Transaction.xaml` (Bank tab > Clear > Account/Transaction > Find > tick > value date / GL)
- Status: in Main.xaml "If CLEAR". Writes `Clear_Transaction`.

### 5 JV (PDD 28-30), isolated
GL download of dummy account 15604010010 -> read last balance DR/CR -> journal
DR/CR Exchange Gain/Loss 35107010001 vs Dummy 15604010010.
- `Oracle/GL_Download/Oracle_GL_Download.xaml` (verified live)
- `Oracle/JV/Oracle_JV_From_GL.xaml`, `Oracle/JV/Oracle_JV.xaml`
- Status: full live run pending; Conversion Date step must be re-added; per-unit loop missing.
- `GL_CHECK/GL_DOWNLOAD.xaml` = old duplicate, retire.

### 6 Apply (PDD 27), isolated
Prepayment report -> LC -> GRN -> new invoice (prepayment no + "M") -> match -> apply prepayment.
- `Oracle/Apply/*` (Oracle_Apply_Main = entry), data in `Apply_File/`
- Status: verified live on GFL per stage. Untested: successful match + apply in one run,
  duplicate invoice suffix. Other units (CAL, CGL, CWPL, GWN) not run.

### 7 Reconciliation (new, not built)
For each cleared row: download GL for the bank's GL account (reuse Oracle_GL_Download
with account/company/date args) and confirm the cleared amount + reference appear.
Mismatch -> `Recon_Status` = not found, listed in the run report.

## Cleanup candidates (not part of any division)
`test.xaml`, `Main(Autosaved)`, `SCB_statement(Autosaved)`, `SelectAction(Autosaved)`,
`SelectAction.uiform`, `Form/BankListForm.uiform` (check use), `hs_err_pid9736.log`,
`replay_pid9736.log`, `Screenshot*.png`, `GL_CHECK/`.

## Proposed folder layout
```
Common/            shared login/Oracle helpers
1_Prepare_Data/    Prepare_Main.xaml + readers
2_Invoice/         Invoice_Main.xaml + entry/match
3_Payment/         Payment_Main.xaml
4_Clear/           Clear_Main.xaml
5_JV/              JV_Main.xaml (GL download + JV)
6_Apply/           Apply_Main.xaml (today Oracle/Apply)
7_Reconciliation/  Recon_Main.xaml
Main.xaml          thin dispatcher: mail keyword / argument -> division Main
```
Moving files changes every `WorkflowFileName` path; done with Studio closed,
then `uip rpa build` to verify, with a git commit before the move.
