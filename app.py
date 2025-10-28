# SMART Insulin Worksheet — Developed by Dr Parimal Swamy
# Streamlit App: Entry form → Dose calculations → Correction tables (40 mg bins)
# → Bolus calculator → PDF Summary export

import streamlit as st
import pandas as pd
import math
from io import BytesIO

# Try to import reportlab for PDF export (installed via requirements.txt)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

# --------------------------- Page setup ---------------------------
st.set_page_config(page_title="SMART Insulin Worksheet", page_icon="💉", layout="wide")
st.title("SMART Insulin Worksheet — Developed by Dr Parimal Swamy")
st.caption("Insulin dose calculator with regimen splits, 40 mg/dL correction bins, bolus tool, and PDF export.")

def round_unit(x, step=0.5):
    return step * round(float(x) / step)

# --------------------------- ENTRY FORM ---------------------------
with st.form("entry_form", clear_on_submit=False):
    st.subheader("Patient Details")
    colw1, colw2 = st.columns([1, 1])
    with colw1:
        pname = st.text_input("Patient name / ID", value="")
        wt = st.number_input("1) Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, step=0.5)
    with colw2:
        category = st.radio(
            "2) Risk category",
            ["Usual", "Hypoglycemia concern"],
            index=0,
            help="Select 'Hypoglycemia concern' for elderly, renal/hepatic impairment, autonomic neuropathy, erratic meals",
        )
        factor = st.select_slider(
            "3) Dose selection (units/kg)", options=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6], value=0.3
        )

    st.markdown("---")
    st.subheader("Visit Context")
    visit = st.selectbox(
        "4) Visit type",
        [
            "Initial prescription",
            "Repeat prescription (with previous TDD)",
            "Inadequate control (with previous TDD)",
            "Hypoglycemia (with previous TDD)",
        ],
        index=0,
    )

    prev_tdd = None
    if visit != "Initial prescription":
        prev_tdd = st.number_input(
            "Enter previous TDD (units)", min_value=0.0, max_value=300.0, value=40.0, step=0.5
        )

    st.markdown("---")
    st.subheader("Regimen Choice")
    regimen = st.radio(
        "5) Choose regimen",
        [
            "Basal",
            "Basal plus (one prandial)",
            "Premixed — twice a day",
            "Premixed — three times a day",
            "Basal bolus",
        ],
        index=0,
    )

    submitted = st.form_submit_button("Save & Continue")

# --------------------------- COMPUTE AND DISPLAY DOSING ---------------------------
if submitted:
    st.success("Entry captured.")
    st.write(
        {
            "patient": pname,
            "weight_kg": wt,
            "risk_category": category,
            "dose_factor_units_per_kg": factor,
            "visit_type": visit,
            "previous_TDD": prev_tdd,
            "regimen": regimen,
        }
    )

    st.markdown("---")
    st.header("Compute Doses from Entry")

    # Targets
    target = 130 if category == "Usual" else 140

    # Base TDD from weight & factor
    tdd_base = wt * factor

    # Visit logic for TDD
    adj_note = ""
    if visit == "Initial prescription":
        tdd = tdd_base
        adj_note = "Initial: TDD = weight × factor"
    elif visit == "Repeat prescription (with previous TDD)":
        tdd = prev_tdd or tdd_base
        adj_note = "Repeat: using previous TDD"
    elif visit == "Inadequate control (with previous TDD)":
        step = st.select_slider("Escalation step", options=[10, 15, 20], value=15)
        tdd = (prev_tdd or tdd_base) * (1 + step / 100)
        adj_note = f"Escalation: +{step}% applied to previous TDD"
    else:  # Hypoglycemia (with previous TDD)
        step = st.select_slider("De-escalation step", options=[10, 15, 20], value=15)
        tdd = (prev_tdd or tdd_base) * (1 - step / 100)
        adj_note = f"De-escalation: -{step}% applied to previous TDD"

    tdd = round_unit(tdd)

    col0, col1, col2, col3 = st.columns(4)
    with col0:
        st.metric("Weight (kg)", f"{wt:.1f}")
    with col1:
        st.metric("Dose factor (U/kg)", f"{factor}")
    with col2:
        st.metric("TDD (units)", f"{tdd}", help=adj_note)
    with col3:
        st.metric("Pre-meal goal", f"≤ {target} mg/dL")

    st.subheader("Regimen-specific Doses")

    if regimen == "Basal":
        st.markdown("**Basal (long-acting)**: start **10 U** _or_ **0.1–0.2 U/kg** after dinner")
        st.markdown(f"Weight-based range: **{round_unit(0.1*wt)}–{round_unit(0.2*wt)} U**")
        st.caption("Titrate ↑2 U every 3 days if fasting >130 mg/dL (or >140 mg/dL if hypoglycemia concern).")
    elif regimen == "Basal plus (one prandial)":
        st.markdown(
            "**Basal:** 10 U or 0.1–0.2 U/kg at bedtime; **One prandial:** 0.1 U/kg before largest meal"
        )
        st.markdown(
            f"Basal range: **{round_unit(0.1*wt)}–{round_unit(0.2*wt)} U** | One prandial: **{round_unit(0.1*wt)} U**"
        )
    elif regimen == "Premixed — twice a day":
        st.markdown(
            f"**Premix TDD = {tdd} U** → **2/3 breakfast:** {round_unit(tdd*2/3)} U, "
            f"**1/3 supper:** {round_unit(tdd*1/3)} U"
        )
    elif regimen == "Premixed — three times a day":
        st.markdown(
            f"**Premix TDD = {tdd} U** → **40% breakfast:** {round_unit(tdd*0.40)} U, "
            f"**30% lunch:** {round_unit(tdd*0.30)} U, **30% dinner:** {round_unit(tdd*0.30)} U"
        )
    else:  # Basal bolus
        st.markdown(
            f"**Basal-bolus TDD = {tdd} U** → **Basal 50%:** {round_unit(tdd*0.50)} U; "
            f"**Bolus total 50%:** {round_unit(tdd*0.50)} U"
        )
        st.markdown(f"≈ **{round_unit((tdd*0.50)/3)} U** before each meal")

    st.markdown("---")
    st.subheader("Correction Doses (real units; fixed 40 mg/dL bins)")

    corr_type = st.radio(
        "Correction insulin type", ["Rapid analogue (1800/TDD)", "Regular (1500/TDD)"], index=0, horizontal=True
    )
    cf = (1800.0 / tdd) if "Rapid" in corr_type else (1500.0 / tdd)

    # Fixed 40 mg/dL bins
    bins_40 = [(131, 170), (171, 210), (211, 250), (251, 290), (291, 330)]
    rows = []
    for lo, hi in bins_40:
        delta = max(0, lo - target)
        units_usual = max(1, int(math.ceil(delta / cf)))
        units_hypo = max(0, units_usual - 1)
        rows.append(
            {
                "Pre-meal (mg/dL)": f"{lo}-{hi}",
                "Usual (≤130) U": units_usual,
                "Hypo-concern (≤140) U": units_hypo,
            }
        )
    # >330 row with safety bump
    delta = max(0, 331 - target)
    units_usual = max(1, int(math.ceil(delta / cf))) + 5
    units_hypo = max(0, units_usual - 1)
    rows.append({"Pre-meal (mg/dL)": ">330", "Usual (≤130) U": units_usual, "Hypo-concern (≤140) U": units_hypo})

    df_corr = pd.DataFrame(rows)
    st.dataframe(df_corr, use_container_width=True)
    st.caption(f"Correction factor: **1 U ≈ {cf:.0f} mg/dL** ({corr_type}).")

    # --------------------------- PDF Summary ---------------------------
    st.subheader("Download PDF Summary")
    if REPORTLAB_OK:
        def build_pdf_summary():
            buf = BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            w, h = A4
            y = h - 2 * cm

            # Header
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2 * cm, y, "SMART Insulin Worksheet — Developed by Dr Parimal Swamy")
            y -= 0.8 * cm
            c.setFont("Helvetica", 10)
            c.drawString(2 * cm, y, f"Patient: {pname or '—'}   Weight: {wt:.1f} kg   Category: {category}")
            y -= 0.5 * cm
            c.drawString(2 * cm, y, f"Visit: {visit}   Factor: {factor} U/kg   TDD: {tdd} U   Goal: ≤ {target} mg/dL")
            y -= 0.7 * cm

            # Regimen section
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2 * cm, y, "Regimen-specific Doses")
            y -= 0.5 * cm
            c.setFont("Helvetica", 10)
            if regimen == "Basal":
                c.drawString(
                    2 * cm,
                    y,
                    f"Basal (long-acting): 10 U or 0.1–0.2 U/kg after dinner "
                    f"(range {round(0.1 * wt, 1)}–{round(0.2 * wt, 1)} U)",
                )
                y -= 0.5 * cm
            elif regimen == "Basal plus (one prandial)":
                c.drawString(
                    2 * cm, y, f"Basal 0.1–0.2 U/kg; One prandial 0.1 U/kg → {round(0.1 * wt, 1)} U before largest meal"
                )
                y -= 0.5 * cm
            elif regimen == "Premixed — twice a day":
                c.drawString(
                    2 * cm,
                    y,
                    f"Premix TDD {tdd} U → Breakfast (2/3): {round(tdd * 2 / 3, 1)} U; "
                    f"Supper (1/3): {round(tdd * 1 / 3, 1)} U",
                )
                y -= 0.5 * cm
            elif regimen == "Premixed — three times a day":
                c.drawString(
                    2 * cm,
                    y,
                    f"Premix TDD {tdd} U → 40% BF: {round(tdd * 0.40, 1)} U; 30% L: {round(tdd * 0.30, 1)} U; "
                    f"30% D: {round(tdd * 0.30, 1)} U",
                )
                y -= 0.5 * cm
            else:
                c.drawString(
                    2 * cm,
                    y,
                    f"Basal-bolus TDD {tdd} U → Basal 50%: {round(tdd * 0.50, 1)} U; "
                    f"Bolus total 50%: {round(tdd * 0.50, 1)} U (~{round((tdd * 0.50) / 3, 1)} U each)",
                )
                y -= 0.5 * cm

            # Correction table header
            y -= 0.2 * cm
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2 * cm, y, f"Correction doses ({corr_type}; 1 U ≈ {cf:.0f} mg/dL; bins 40 mg/dL)")
            y -= 0.5 * cm
            c.setFont("Helvetica", 10)
            # Render df_corr rows
            for _, r in df_corr.iterrows():
                if y < 2.5 * cm:
                    c.showPage()
                    y = h - 2 * cm
                    c.setFont("Helvetica", 10)
                c.drawString(
                    2 * cm,
                    y,
                    f"{r['Pre-meal (mg/dL)']}: Usual {int(r['Usual (≤130) U'])} U | "
                    f"Hypo {int(r['Hypo-concern (≤140) U'])} U",
                )
                y -= 0.4 * cm

            # Footer
            if y < 2.5 * cm:
                c.showPage()
                y = h - 2 * cm
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(
                2 * cm,
                1.9 * cm,
                "Add correction dose to scheduled pre-meal bolus. Adjust for renal/hepatic status; "
                "check ketones if >330 mg/dL or symptomatic.",
            )
            c.drawString(2 * cm, 1.4 * cm, "Signature: _______________________    Date: __/__/____")
            c.save()
            pdf = buf.getvalue()
            buf.close()
            return pdf

        pdf_bytes = build_pdf_summary()
        st.download_button(
            "🧾 Download PDF Summary",
            data=pdf_bytes,
            file_name=f"insulin_worksheet_{pname or 'patient'}.pdf",
            mime="application/pdf",
        )
    else:
        st.warning("PDF export not available (reportlab not installed). Add 'reportlab' to requirements.txt.")

# --------------------------- BOLUS CORRECTION CALCULATOR ---------------------------
st.markdown("---")
st.header("Bolus Correction Calculator")

st.write(
    "Estimate the **correctional insulin dose** for a given pre-meal glucose value, "
    "based on the chosen insulin type and TDD. (Result is **added** to the scheduled pre-meal bolus.)"
)

bol_tdd = st.number_input("Enter Total Daily Dose (TDD) (units)", min_value=5.0, max_value=300.0, value=50.0, step=0.5)
bol_type = st.radio("Type of Bolus Insulin", ["Regular (1500/TDD)", "Rapid Acting (1800/TDD)"], horizontal=True)
premeal_bs = st.number_input("Pre-meal Blood Sugar (mg/dL)", min_value=60, max_value=600, value=180)

isf = 1500 / bol_tdd if "Regular" in bol_type else 1800 / bol_tdd
units_usual = 0 if premeal_bs <= 130 else math.ceil((premeal_bs - 130) / isf)
units_hypo = 0 if premeal_bs <= 140 else math.ceil((premeal_bs - 140) / isf)

col1, col2 = st.columns(2)
with col1:
    st.metric("Usual Protocol (target ≤130)", f"{units_usual} units")
with col2:
    st.metric("Hypoglycemia-prone (target ≤140)", f"{units_hypo} units")

st.info("This correction dose is **added to the scheduled pre-meal insulin bolus** before the meal.")
st.caption(f"Insulin Sensitivity Factor (ISF): 1 unit lowers ≈ {isf:.0f} mg/dL")

st.subheader("Reference: Correction Table by Range (Fixed 40 mg/dL bins)")
ref_buckets = [(131, 170), (171, 210), (211, 250), (251, 290), (291, 330)]
rows_ref = []
for lo, hi in ref_buckets:
    delta_usual = max(0, lo - 130)
    delta_hypo = max(0, lo - 140)
    u_usual = max(1, int(math.ceil(delta_usual / isf)))
    u_hypo = max(0, int(math.ceil(delta_hypo / isf)))
    rows_ref.append({"Pre-meal (mg/dL)": f"{lo}-{hi}", "Usual (≤130) U": u_usual, "Hypo-prone (≤140) U": u_hypo})
delta_usual = max(0, 331 - 130)
delta_hypo = max(0, 331 - 140)
rows_ref.append(
    {
        "Pre-meal (mg/dL)": ">330",
        "Usual (≤130) U": max(1, int(math.ceil(delta_usual / isf))) + 5,
        "Hypo-prone (≤140) U": max(0, int(math.ceil(delta_hypo / isf))) + 4,
    }
)

st.dataframe(pd.DataFrame(rows_ref), use_container_width=True)
