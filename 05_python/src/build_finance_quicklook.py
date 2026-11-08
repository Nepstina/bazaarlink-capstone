"""
Build 03_excel/finance_quicklook.xlsx - the Finance quick-look dashboard.

Step 1 (openpyxl): Data table with formula columns, States lookup sheet,
Calc sheet and a one-page Dashboard (KPI cards, charts, dropdown filters,
conditional formatting).
Step 2 (Excel via COM, Windows only): pivot table, pivot chart and slicers,
then full recalculation and save.

Run after clean_data.py:
    python 05_python/src/build_finance_quicklook.py
"""

import os
import sys
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "02_data", "cleaned", "orders_master.csv")
OUT_DIR = os.path.join(ROOT, "03_excel")
OUT = os.path.join(OUT_DIR, "finance_quicklook.xlsx")

NAVY, TEAL, GREY = "1F3A5F", "2E86AB", "F2F4F7"
WHITE = Font(color="FFFFFF", bold=True)
thin = Side(style="thin", color="D0D5DD")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

STATES = [  # code, name, region
    ("AC", "Acre", "North"), ("AL", "Alagoas", "Northeast"), ("AP", "Amapa", "North"),
    ("AM", "Amazonas", "North"), ("BA", "Bahia", "Northeast"), ("CE", "Ceara", "Northeast"),
    ("DF", "Distrito Federal", "Central-West"), ("ES", "Espirito Santo", "Southeast"),
    ("GO", "Goias", "Central-West"), ("MA", "Maranhao", "Northeast"), ("MT", "Mato Grosso", "Central-West"),
    ("MS", "Mato Grosso do Sul", "Central-West"), ("MG", "Minas Gerais", "Southeast"), ("PA", "Para", "North"),
    ("PB", "Paraiba", "Northeast"), ("PR", "Parana", "South"), ("PE", "Pernambuco", "Northeast"),
    ("PI", "Piaui", "Northeast"), ("RJ", "Rio de Janeiro", "Southeast"), ("RN", "Rio Grande do Norte", "Northeast"),
    ("RS", "Rio Grande do Sul", "South"), ("RO", "Rondonia", "North"), ("RR", "Roraima", "North"),
    ("SC", "Santa Catarina", "South"), ("SP", "Sao Paulo", "Southeast"), ("SE", "Sergipe", "Northeast"),
    ("TO", "Tocantins", "North"),
]


def header(ws, row, cols, fill=NAVY):
    for c in cols:
        cell = ws.cell(row, c)
        cell.fill = PatternFill("solid", fgColor=fill)
        cell.font = WHITE
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def build_openpyxl():
    m = pd.read_csv(SRC, low_memory=False)
    m["purchase_date"] = pd.to_datetime(m["order_purchase_timestamp"]).dt.normalize()
    cols = ["order_id", "order_status", "purchase_date", "customer_state", "main_payment_type",
            "max_installments", "n_items", "item_revenue", "freight_value", "review_score",
            "delay_days", "is_late", "primary_category"]
    d = m[cols].copy()
    d["main_payment_type"] = d["main_payment_type"].fillna("no_payment")
    d["max_installments"] = d["max_installments"].fillna(0)
    n = len(d)
    last = n + 1

    wb = Workbook()
    dash = wb.active
    dash.title = "Dashboard"
    calc = wb.create_sheet("Calc")
    st = wb.create_sheet("States")
    data = wb.create_sheet("Data")
    wb.create_sheet("Pivot")
    notes = wb.create_sheet("Notes")

    # ---------------- Data sheet ----------------
    formula_cols = ["Month", "Year", "Delivered", "Delivery Status", "Region", "Freight Ratio", "Instalment Band"]
    data.append(cols + formula_cols)
    for i, r in enumerate(d.itertuples(index=False), start=2):
        vals = list(r)
        vals[2] = vals[2].to_pydatetime()
        vals = [None if (isinstance(v, float) and pd.isna(v)) else v for v in vals]
        vals += [
            f'=TEXT(C{i},"yyyy-mm")',                                   # TEXT function
            f"=YEAR(C{i})",                                             # DATE function
            f'=IF(B{i}="delivered",1,0)',                               # IF
            f'=IF(L{i}="","Not delivered",IF(L{i}=1,"Late","On time"))',  # nested IF
            f'=_xlfn.XLOOKUP(D{i},States!$A$2:$A$28,States!$C$2:$C$28,"Unknown")',  # XLOOKUP across sheets
            f'=IF(H{i}=0,"",I{i}/H{i})',
            f'=IF(F{i}<=1,"1 (single)",IF(F{i}<=3,"2-3",IF(F{i}<=6,"4-6","7+")))',
        ]
        data.append(vals)
    for row in data.iter_rows(min_row=2, min_col=3, max_col=3):
        for c in row:
            c.number_format = "yyyy-mm-dd"
    for col in ("H", "I"):
        for row in data[f"{col}2:{col}{last}"]:
            row[0].number_format = "#,##0.00"
    for row in data[f"S2:S{last}"]:
        row[0].number_format = "0.0%"
    tbl = Table(displayName="tblOrders", ref=f"A1:T{last}")
    tbl.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    data.add_table(tbl)
    widths = [34, 12, 12, 9, 13, 10, 8, 12, 11, 9, 9, 8, 26, 9, 7, 9, 14, 13, 10, 13]
    for i, w in enumerate(widths):
        data.column_dimensions[chr(65 + i)].width = w
    data.freeze_panes = "B2"

    R = lambda col: f"Data!${col}$2:${col}${last}"  # noqa: E731  fixed range helper

    # ---------------- States sheet ----------------
    st.append(["State", "State name", "Region", "Orders", "Revenue (BRL)", "AOV (BRL)", "Freight (BRL)",
               "Freight ratio", "On-time %", "Avg review"])
    for i, (code, name, region) in enumerate(STATES, start=2):
        crit = f'{R("D")},$A{i},{R("O")},Calc!$B$3'
        st.append([code, name, region,
                   f"=COUNTIFS({crit})",
                   f"=SUMIFS({R('H')},{crit},{R('P')},1)",
                   f"=IFERROR(E{i}/COUNTIFS({crit},{R('P')},1),0)",
                   f"=SUMIFS({R('I')},{crit},{R('P')},1)",
                   f"=IFERROR(G{i}/E{i},0)",
                   f'=IFERROR(COUNTIFS({crit},{R("Q")},"On time")/(COUNTIFS({crit},{R("Q")},"On time")+COUNTIFS({crit},{R("Q")},"Late")),0)',
                   f'=IFERROR(AVERAGEIFS({R("J")},{crit}),0)'])
    header(st, 1, range(1, 11))
    for row in st.iter_rows(min_row=2, max_row=28):
        row[3].number_format = "#,##0"
        for c in (row[4], row[5], row[6]):
            c.number_format = "#,##0"
        row[7].number_format = "0.0%"
        row[8].number_format = "0.0%"
        row[9].number_format = "0.00"
    st.conditional_formatting.add("E2:E28", DataBarRule(start_type="min", end_type="max", color="2E86AB"))
    st.conditional_formatting.add("I2:I28", ColorScaleRule(start_type="min", start_color="F8696B",
                                                           mid_type="percentile", mid_value=50, mid_color="FFEB84",
                                                           end_type="max", end_color="63BE7B"))
    st.conditional_formatting.add("H2:H28", CellIsRule(operator="greaterThan", formula=["0.25"],
                                                       fill=PatternFill("solid", fgColor="FFC7CE"),
                                                       font=Font(color="9C0006")))
    for i, w in enumerate([7, 20, 13, 9, 14, 10, 13, 11, 10, 10]):
        st.column_dimensions[chr(65 + i)].width = w
    st.freeze_panes = "A2"

    # ---------------- Calc sheet ----------------
    calc["A1"] = "Filter criteria (driven by Dashboard dropdowns)"
    calc["A1"].font = Font(bold=True)
    calc["A2"], calc["B2"] = "State criterion", '=IF(Dashboard!$C$4="All","*",Dashboard!$C$4)'
    calc["A3"], calc["B3"] = "Year criterion", '=IF(Dashboard!$F$4="All","<>",Dashboard!$F$4)'
    fs = f'{R("D")},$B$2,{R("O")},$B$3'  # filter criteria pair for SUMIFS/COUNTIFS

    # KPI block
    calc["A5"] = "KPI"; calc["B5"] = "Value"; header(calc, 5, [1, 2])
    kpis = [
        ("Orders", f"=COUNTIFS({fs})", "#,##0"),
        ("Delivered orders", f"=COUNTIFS({fs},{R('P')},1)", "#,##0"),
        ("Revenue (BRL)", f"=SUMIFS({R('H')},{fs},{R('P')},1)", '"R$ "#,##0'),
        ("AOV (BRL)", "=IFERROR(B8/B7,0)", '"R$ "#,##0.00'),
        ("Freight (BRL)", f"=SUMIFS({R('I')},{fs},{R('P')},1)", '"R$ "#,##0'),
        ("Freight ratio", "=IFERROR(B10/B8,0)", "0.0%"),
        ("On-time %", f'=IFERROR(COUNTIFS({fs},{R("Q")},"On time")/(COUNTIFS({fs},{R("Q")},"On time")+COUNTIFS({fs},{R("Q")},"Late")),0)', "0.0%"),
        ("Avg review score", f"=IFERROR(AVERAGEIFS({R('J')},{fs}),0)", "0.00"),
        ("Negative review %", f'=IFERROR(COUNTIFS({fs},{R("J")},"<=2")/COUNTIFS({fs},{R("J")},">=1"),0)', "0.0%"),
        ("Cancellation %", f'=IFERROR((COUNTIFS({fs},{R("B")},"canceled")+COUNTIFS({fs},{R("B")},"unavailable"))/B6,0)', "0.0%"),
    ]
    for i, (k, f, fmt) in enumerate(kpis, start=6):
        calc.cell(i, 1, k); calc.cell(i, 2, f).number_format = fmt

    # Monthly trend (Jan 2017 - Aug 2018 = complete months), uses DATE + TEXT
    calc["D5"], calc["E5"], calc["F5"], calc["G5"], calc["H5"] = "Month start", "Month", "Orders", "Revenue (BRL)", "On-time %"
    header(calc, 5, range(4, 9))
    for k in range(20):
        r = 6 + k
        calc.cell(r, 4, f"=DATE(2017,{1 + k},1)").number_format = "yyyy-mm-dd"
        calc.cell(r, 5, f'=TEXT(D{r},"mmm-yy")')
        mk = f'{R("N")},TEXT(D{r},"yyyy-mm"),{R("D")},$B$2'
        calc.cell(r, 6, f"=COUNTIFS({mk})").number_format = "#,##0"
        calc.cell(r, 7, f"=SUMIFS({R('H')},{mk},{R('P')},1)").number_format = "#,##0"
        calc.cell(r, 8, f'=IFERROR(COUNTIFS({mk},{R("Q")},"On time")/(COUNTIFS({mk},{R("Q")},"On time")+COUNTIFS({mk},{R("Q")},"Late")),0)').number_format = "0.0%"

    # Payment type
    calc["J5"], calc["K5"], calc["L5"], calc["M5"], calc["N5"] = "Payment type", "Orders", "Revenue (BRL)", "AOV (BRL)", "Share of revenue"
    header(calc, 5, range(10, 15))
    for i, p in enumerate(["credit_card", "boleto", "voucher", "debit_card"], start=6):
        pk = f'{fs},{R("E")},$J{i},{R("P")},1'
        calc.cell(i, 10, p)
        calc.cell(i, 11, f"=COUNTIFS({pk})").number_format = "#,##0"
        calc.cell(i, 12, f"=SUMIFS({R('H')},{pk})").number_format = "#,##0"
        calc.cell(i, 13, f"=IFERROR(L{i}/K{i},0)").number_format = "#,##0.00"
        calc.cell(i, 14, f"=IFERROR(L{i}/$B$8,0)").number_format = "0.0%"

    # Instalment band
    calc["J12"], calc["K12"], calc["L12"], calc["M12"] = "Instalments", "Orders", "Revenue (BRL)", "AOV (BRL)"
    header(calc, 12, range(10, 14))
    for i, b in enumerate(["1 (single)", "2-3", "4-6", "7+"], start=13):
        bk = f'{fs},{R("T")},$J{i},{R("P")},1'
        calc.cell(i, 10, b)
        calc.cell(i, 11, f"=COUNTIFS({bk})").number_format = "#,##0"
        calc.cell(i, 12, f"=SUMIFS({R('H')},{bk})").number_format = "#,##0"
        calc.cell(i, 13, f"=IFERROR(L{i}/K{i},0)").number_format = "#,##0.00"

    # Top 10 states by revenue: LARGE + INDEX/MATCH across sheets
    calc["P5"], calc["Q5"], calc["R5"], calc["S5"], calc["T5"], calc["U5"] = "Rank", "State", "State name", "Revenue (BRL)", "AOV (BRL)", "On-time %"
    header(calc, 5, range(16, 22))
    for k in range(1, 11):
        r = 5 + k
        calc.cell(r, 16, k)
        calc.cell(r, 19, f"=LARGE(States!$E$2:$E$28,P{r})").number_format = "#,##0"
        calc.cell(r, 17, f"=INDEX(States!$A$2:$A$28,MATCH(S{r},States!$E$2:$E$28,0))")
        calc.cell(r, 18, f"=INDEX(States!$B$2:$B$28,MATCH(Q{r},States!$A$2:$A$28,0))")
        calc.cell(r, 20, f"=INDEX(States!$F$2:$F$28,MATCH(Q{r},States!$A$2:$A$28,0))").number_format = "#,##0.00"
        calc.cell(r, 21, f"=INDEX(States!$I$2:$I$28,MATCH(Q{r},States!$A$2:$A$28,0))").number_format = "0.0%"
    for col, w in zip("ABCDEFGHIJKLMNOPQRSTU", [20, 16, 2, 12, 9, 9, 13, 10, 2, 13, 9, 13, 10, 10, 2, 6, 7, 18, 13, 10, 10]):
        calc.column_dimensions[col].width = w

    # ---------------- Dashboard ----------------
    dash.sheet_view.showGridLines = False
    for col in range(1, 22):
        dash.column_dimensions[chr(64 + col)].width = 9.5
    dash.column_dimensions["A"].width = 2
    dash.merge_cells("B1:U1")
    dash["B1"] = "BazaarLink  |  Finance Quick-Look Dashboard"
    dash["B1"].font = Font(size=18, bold=True, color="FFFFFF")
    dash["B1"].fill = PatternFill("solid", fgColor=NAVY)
    dash["B1"].alignment = Alignment(vertical="center", indent=1)
    dash.row_dimensions[1].height = 34
    dash["B2"] = ("Revenue = item price of delivered orders (freight excluded). On-time % = delivered on or before the "
                  "estimated date. Source: cleaned Olist data, Data sheet.")
    dash["B2"].font = Font(italic=True, size=9, color="667085")

    dash["B4"] = "State:"; dash["E4"] = "Year:"
    for c in ("B4", "E4"):
        dash[c].font = Font(bold=True); dash[c].alignment = Alignment(horizontal="right")
    dash["C4"] = "All"; dash["F4"] = "All"
    for c in ("C4", "F4"):
        dash[c].fill = PatternFill("solid", fgColor="FFF4CC"); dash[c].border = BOX; dash[c].font = Font(bold=True)
    st_list = ",".join(["All"] + [s[0] for s in STATES])
    dv1 = DataValidation(type="list", formula1=f'"{st_list}"', allow_blank=False,
                         showErrorMessage=True, error="Pick a state code from the list")
    dv2 = DataValidation(type="list", formula1='"All,2016,2017,2018"', allow_blank=False,
                         showErrorMessage=True, error="Pick a year from the list")
    dash.add_data_validation(dv1); dv1.add("C4")
    dash.add_data_validation(dv2); dv2.add("F4")
    dash["H4"] = "Pick a state and year: KPI cards, state table and payment charts update. Monthly trend follows the state filter."
    dash["H4"].font = Font(size=9, color="667085")

    cards = [("Orders", "Calc!B6", "#,##0"), ("Revenue", "Calc!B8", '"R$ "0.00,,"M"'),
             ("AOV", "Calc!B9", '"R$ "#,##0.00'), ("Freight ratio", "Calc!B11", "0.0%"),
             ("On-time %", "Calc!B12", "0.0%"), ("Avg review", "Calc!B13", "0.00"),
             ("Negative review %", "Calc!B14", "0.0%"), ("Cancellation %", "Calc!B15", "0.0%")]
    for k, (label, ref, fmt) in enumerate(cards):
        col = [2, 4, 7, 9, 12, 14, 17, 19][k]  # each card is 2 columns wide, in pairs
        dash.merge_cells(start_row=6, start_column=col, end_row=6, end_column=col + 1)
        dash.merge_cells(start_row=7, start_column=col, end_row=8, end_column=col + 1)
        lc = dash.cell(6, col, label)
        lc.font = Font(size=9, bold=True, color="FFFFFF"); lc.fill = PatternFill("solid", fgColor=TEAL)
        lc.alignment = Alignment(horizontal="center")
        vc = dash.cell(7, col, f"={ref}")
        vc.number_format = fmt; vc.font = Font(size=16, bold=True, color=NAVY)
        vc.alignment = Alignment(horizontal="center", vertical="center")
        for r in (7, 8):
            for cc in (col, col + 1):
                dash.cell(r, cc).fill = PatternFill("solid", fgColor=GREY)
    # Conditional formatting on KPI cards: on-time below 90% / negative review above 15% in red
    red = Font(size=16, bold=True, color="C00000")
    dash.conditional_formatting.add("L7", CellIsRule(operator="lessThan", formula=["0.9"], font=red))
    dash.conditional_formatting.add("Q7", CellIsRule(operator="greaterThan", formula=["0.15"], font=red))

    # Top 10 states table
    dash["N10"] = "Top 10 customer states by revenue"; dash["N10"].font = Font(bold=True, color=NAVY, size=11)
    hdrs = ["#", "State", "Name", "", "Revenue", "AOV", "On-time %"]
    for j, h in enumerate(hdrs):
        dash.cell(11, 14 + j, h)
    header(dash, 11, range(14, 21))
    dash.merge_cells("P11:Q11")
    for k in range(10):
        r = 12 + k
        cr = 6 + k
        dash.cell(r, 14, f"=Calc!P{cr}")
        dash.cell(r, 15, f"=Calc!Q{cr}")
        dash.merge_cells(start_row=r, start_column=16, end_row=r, end_column=17)
        dash.cell(r, 16, f"=Calc!R{cr}")
        dash.cell(r, 18, f"=Calc!S{cr}").number_format = "#,##0"
        dash.cell(r, 19, f"=Calc!T{cr}").number_format = "#,##0"
        dash.cell(r, 20, f"=Calc!U{cr}").number_format = "0.0%"
        for cc in range(14, 21):
            dash.cell(r, cc).border = BOX
            dash.cell(r, cc).font = Font(size=9)
    dash.conditional_formatting.add("R12:R21", DataBarRule(start_type="num", start_value=0, end_type="max", color="9BC2E6"))
    dash.conditional_formatting.add("T12:T21", CellIsRule(operator="lessThan", formula=["0.9"],
                                                          fill=PatternFill("solid", fgColor="FFC7CE"), font=Font(color="9C0006", size=9)))
    dash.conditional_formatting.add("T12:T21", CellIsRule(operator="greaterThanOrEqual", formula=["0.95"],
                                                          fill=PatternFill("solid", fgColor="C6EFCE"), font=Font(color="006100", size=9)))

    # Charts
    line = LineChart()
    line.title = "Monthly revenue (delivered, BRL) - Jan 2017 to Aug 2018"
    line.height, line.width = 7.2, 16.5
    line.add_data(Reference(calc, min_col=7, min_row=5, max_row=25), titles_from_data=True)
    line.set_categories(Reference(calc, min_col=5, min_row=6, max_row=25))
    line.y_axis.numFmt = "#,##0"
    line.y_axis.delete = False; line.x_axis.delete = False
    line.legend = None
    line.series[0].graphicalProperties.line.solidFill = NAVY
    line.series[0].graphicalProperties.line.width = 28000
    line.series[0].smooth = False
    dash.add_chart(line, "B10")

    bar = BarChart(); bar.type = "bar"
    bar.title = "Revenue share by payment type"
    bar.height, bar.width = 6.2, 8.2
    bar.add_data(Reference(calc, min_col=14, min_row=5, max_row=9), titles_from_data=True)
    bar.set_categories(Reference(calc, min_col=10, min_row=6, max_row=9))
    bar.y_axis.numFmt = "0%"; bar.legend = None
    bar.y_axis.delete = False; bar.x_axis.delete = False
    bar.series[0].graphicalProperties.solidFill = TEAL
    dash.add_chart(bar, "B25")

    bar2 = BarChart(); bar2.type = "col"
    bar2.title = "AOV by number of instalments (BRL)"
    bar2.height, bar2.width = 6.2, 8.2
    bar2.add_data(Reference(calc, min_col=13, min_row=12, max_row=16), titles_from_data=True)
    bar2.set_categories(Reference(calc, min_col=10, min_row=13, max_row=16))
    bar2.y_axis.numFmt = "#,##0"; bar2.legend = None
    bar2.y_axis.delete = False; bar2.x_axis.delete = False
    bar2.series[0].graphicalProperties.solidFill = NAVY
    dash.add_chart(bar2, "G25")

    dash["N24"] = "Pivot chart + slicers (filter the pivot only)"; dash["N24"].font = Font(bold=True, color=NAVY, size=11)

    # Print setup: one landscape page
    dash.page_setup.orientation = "landscape"
    dash.page_setup.fitToWidth = 1; dash.page_setup.fitToHeight = 1
    dash.sheet_properties.pageSetUpPr.fitToPage = True
    dash.print_area = "A1:W40"

    # Notes sheet: where each required Excel skill is used
    notes.append(["Skill required by brief", "Where it is used"])
    for row in [
        ("IF", "Data!P (Delivered), Data!Q (Delivery Status, nested IF), Data!T (Instalment Band), Calc!B2:B3"),
        ("COUNTIFS", "Calc KPI block, monthly table, payment table; States!D"),
        ("SUMIFS", "Calc!B8 Revenue, Calc!B10 Freight, monthly revenue, States!E"),
        ("AVERAGEIFS", "Calc!B13 Avg review; States!J"),
        ("TEXT", "Data!N (Month = TEXT(date,\"yyyy-mm\")), Calc!E (month labels)"),
        ("DATE / YEAR", "Calc!D (DATE(2017,n,1) month starts), Data!O (YEAR)"),
        ("XLOOKUP across sheets", "Data!R Region = XLOOKUP(state, States!A, States!C)"),
        ("INDEX-MATCH across sheets", "Calc!Q:U top-10 states from States sheet (with LARGE)"),
        ("Data validation", "Dashboard!C4 (state list), Dashboard!F4 (year list)"),
        ("Conditional formatting", "Dashboard KPI cards (red if on-time < 90% / negative > 15%), top-10 data bars and on-time colours; States colour scale and freight ratio > 25%"),
        ("Pivot table", "Pivot sheet: revenue and orders by payment type (delivered orders)"),
        ("Pivot chart", "Dashboard: revenue by payment type pivot chart"),
        ("Slicer", "Dashboard: Region and Year slicers connected to the pivot table"),
        ("One-page dashboard", "Dashboard sheet, landscape, fit to 1 page"),
    ]:
        notes.append(list(row))
    header(notes, 1, [1, 2])
    notes.column_dimensions["A"].width = 28; notes.column_dimensions["B"].width = 110

    os.makedirs(OUT_DIR, exist_ok=True)
    wb.save(OUT)
    print(f"step 1 saved ({n:,} data rows)")


def add_pivots_with_excel():
    """Use Excel (COM) to add a pivot table, pivot chart and slicers, recalc, save."""
    import win32com.client as win32
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    try:
        wb = xl.Workbooks.Open(OUT)
        xl.CalculateFull()
        pws = wb.Worksheets("Pivot")
        dash = wb.Worksheets("Dashboard")
        pc = wb.PivotCaches().Create(SourceType=1, SourceData="tblOrders")  # xlDatabase
        pt = pc.CreatePivotTable(TableDestination=pws.Range("A3"), TableName="ptPayment")
        pt.PivotFields("main_payment_type").Orientation = 1            # row
        pf = pt.PivotFields("order_status"); pf.Orientation = 3        # page filter
        pf.CurrentPage = "delivered"
        rev = pt.AddDataField(pt.PivotFields("item_revenue"), "Revenue (BRL)", -4157)  # xlSum
        rev.NumberFormat = "#,##0"
        cnt = pt.AddDataField(pt.PivotFields("order_id"), "Orders", -4112)              # xlCount
        cnt.NumberFormat = "#,##0"
        pt.PivotFields("main_payment_type").AutoSort(2, "Revenue (BRL)")               # descending
        try:
            pt.PivotFields("main_payment_type").PivotItems("no_payment").Visible = False
        except Exception:  # noqa: BLE001  item may not exist
            pass
        pws.Range("A1").Value = "Pivot: revenue and orders by payment type (delivered orders). Filter with the slicers on the Dashboard."

        # Pivot chart on the dashboard
        top = dash.Range("N25").Top
        left = dash.Range("N25").Left
        shp = dash.Shapes.AddChart2(201, 57, left, top, 330, 190)  # xlBarClustered
        ch = shp.Chart
        ch.SetSourceData(pt.TableRange1)
        ch.HasTitle = True
        ch.ChartTitle.Text = "Revenue by payment type (pivot)"
        # show only the revenue series (orders is on a different scale)
        for s in list(ch.SeriesCollection()):
            if s.Name == "Orders" or "Orders" in str(s.Name):
                s.Delete()
        ch.HasLegend = False
        ch.ShowAllFieldButtons = False

        # Slicers, placed to the right of the pivot chart
        for i, (field, cap, h) in enumerate([("Region", "Region", 150), ("Year", "Year", 95)]):
            sc = wb.SlicerCaches.Add2(pt, field)
            slc = sc.Slicers.Add(SlicerDestination=dash, Name=f"slc{field}", Caption=cap)
            slc.Top = top + (0 if i == 0 else 155)
            slc.Left = left + 336
            slc.Width = 110
            slc.Height = h
        xl.CalculateFull()
        dash.Activate()
        dash.Range("C4").Select()
        wb.Save()

        calc = wb.Worksheets("Calc")
        vals = {calc.Cells(r, 1).Value: calc.Cells(r, 2).Value for r in range(6, 16)}
        wb.Close(SaveChanges=False)
        return vals
    finally:
        xl.Quit()


if __name__ == "__main__":
    t = datetime.now()
    build_openpyxl()
    if sys.platform == "win32":
        try:
            vals = add_pivots_with_excel()
            print("step 2 done: pivot table, pivot chart, slicers added")
            for k, v in vals.items():
                print(f"  {k:20s} {v}")
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            print(f"Excel step failed ({e}); add the pivot table, chart and slicers by hand.")
    print(f"finished in {(datetime.now() - t).seconds}s -> {OUT}")
