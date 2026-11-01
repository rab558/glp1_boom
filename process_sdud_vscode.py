"""Create auditable, compact Medicaid SDUD panels from annual CSVs.

Install: python -m pip install pandas
Usage: Open this file in VS Code and click Run Python File. No command-line arguments.
Reads every *.csv in input directory recursively in chunks. Keeps source CSVs unchanged.
Drug-name matching is a CANDIDATE SCREEN, not an audited NDC classification.
"""
from __future__ import annotations
from pathlib import Path

# Paths are relative to this script, which belongs in the glp1_boom project root.
PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_ROOT / "data" / "state_drug_utilization"
OUTPUT_DIR = INPUT_DIR / "processed"
EXPECTED_YEARS = set(range(2020, 2025))
import re
import pandas as pd

# Drug names in SDUD are truncated; use anchored prefixes rather than arbitrary substrings.
# Tirzepatide is a dual GIP/GLP-1 agonist; combinations are reported separately.
PRODUCTS = {
    'OZEMPIC': ('Ozempic', 'Semaglutide', 'Novo Nordisk', 'core'),
    'WEGOVY': ('Wegovy', 'Semaglutide', 'Novo Nordisk', 'core'),
    'RYBELSUS': ('Rybelsus', 'Semaglutide', 'Novo Nordisk', 'core'),
    'MOUNJARO': ('Mounjaro', 'Tirzepatide', 'Eli Lilly', 'dual_gip_glp1'),
    'ZEPBOUND': ('Zepbound', 'Tirzepatide', 'Eli Lilly', 'dual_gip_glp1'),
    'TRULICITY': ('Trulicity', 'Dulaglutide', 'Eli Lilly', 'core'),
    'VICTOZA': ('Victoza', 'Liraglutide', 'Novo Nordisk', 'core'),
    'SAXENDA': ('Saxenda', 'Liraglutide', 'Novo Nordisk', 'core'),
    'BYETTA': ('Byetta', 'Exenatide', 'AstraZeneca', 'core'),
    'BYDUREON': ('Bydureon', 'Exenatide', 'AstraZeneca', 'core'),
    'ADLYXIN': ('Adlyxin', 'Lixisenatide', 'Sanofi', 'core'),
    'XULTOPHY': ('Xultophy', 'Insulin degludec / liraglutide', 'Novo Nordisk', 'combination'),
    'SOLIQUA': ('Soliqua', 'Insulin glargine / lixisenatide', 'Sanofi', 'combination'),
}
NUMERIC = ['Units Reimbursed','Number of Prescriptions','Total Amount Reimbursed',
           'Medicaid Amount Reimbursed','Non Medicaid Amount Reimbursed']
KEY = ['Year','State','Utilization Type','product','ingredient','manufacturer','category']
ALL_KEY = ['Year','State','Utilization Type']
RENAMES = {'Units Reimbursed':'units_observed',
           'Number of Prescriptions':'prescriptions_observed',
           'Total Amount Reimbursed':'total_reimbursement_observed',
           'Medicaid Amount Reimbursed':'medicaid_reimbursement_observed',
           'Non Medicaid Amount Reimbursed':'non_medicaid_reimbursement_observed'}
DETAIL_COLS = ['source_file','Year','Quarter','State','Utilization Type','NDC',
               'Product Name','product','ingredient','manufacturer','category',
               'Suppression Used']+NUMERIC


def classify(product_name: pd.Series) -> pd.DataFrame:
    name = product_name.fillna('').str.upper().str.strip()
    labels = name.str.extract(r'^(' + '|'.join(PRODUCTS) + r')(?=$|[^A-Z])', expand=False)
    records = [PRODUCTS.get(x, (None, None, None, None)) for x in labels]
    return pd.DataFrame(records, index=product_name.index,
                        columns=['product','ingredient','manufacturer','category'])


def group_summary(frame, keys, include_match=False):
    if frame.empty:
        return pd.DataFrame()
    f = frame.copy()
    f['rows'] = 1
    f['suppressed_rows'] = f['Suppression Used'].fillna('').astype(str).str.lower().eq('true').astype('int64')
    f['unsuppressed_rows'] = 1 - f['suppressed_rows']
    metrics = NUMERIC + ['rows','suppressed_rows','unsuppressed_rows']
    out = f.groupby(keys, dropna=False, sort=False)[metrics].sum(min_count=1).reset_index()
    # pandas sum(min_count=1) gives NaN if no numeric values exist for a group
    return out


def combine_partial(partials, keys):
    if not partials:
        return pd.DataFrame()
    z = pd.concat(partials, ignore_index=True)
    vals = [c for c in NUMERIC + ['rows','suppressed_rows','unsuppressed_rows'] if c in z]
    return z.groupby(keys,dropna=False,sort=True)[vals].sum(min_count=1).reset_index()


def process_one(path, out_dir, chunksize=175000):
    all_parts, glp_parts, drug_parts = [], [], []
    detected = set()
    raw_rows = candidate_rows = 0
    detail_path = out_dir / f'{path.stem}_glp1_ndc_quarter.csv'
    if detail_path.exists(): detail_path.unlink()
    wrote_header = False
    for frame in pd.read_csv(path, chunksize=chunksize, dtype={'NDC':'string',
                              'Labeler Code':'string','Product Code':'string','Package Size':'string'},
                              low_memory=False):
        missing = set(['Year','Quarter','State','Utilization Type','NDC','Product Name','Suppression Used'] + NUMERIC)-set(frame)
        if missing: raise ValueError(f'{path}: missing columns: {sorted(missing)}')
        raw_rows += len(frame)
        detected.update(pd.to_numeric(frame['Year'],errors='coerce').dropna().astype(int).unique().tolist())
        frame['NDC'] = frame['NDC'].str.zfill(11)
        frame['State'] = frame['State'].astype('string').str.strip().str.upper()
        frame['Utilization Type'] = frame['Utilization Type'].astype('string').str.strip().str.upper()
        for col in NUMERIC: frame[col] = pd.to_numeric(frame[col],errors='coerce')
        all_parts.append(group_summary(frame, ALL_KEY))
        classes = classify(frame['Product Name'])
        glp = frame.join(classes)
        glp = glp.loc[glp['product'].notna()].copy()
        candidate_rows += len(glp)
        if not glp.empty:
            glp['source_file'] = path.name
            glp[DETAIL_COLS].to_csv(detail_path,mode='a',header=not wrote_header,index=False)
            wrote_header = True
            glp_parts.append(group_summary(glp,KEY))
            # Include all NDC/product names for an auditable candidate mapping
            drug_parts.append(glp[['NDC','Product Name','product','ingredient','manufacturer','category']].drop_duplicates())
    all_out = combine_partial(all_parts,ALL_KEY)
    glp_out = combine_partial(glp_parts,KEY)
    mapping = pd.concat(drug_parts,ignore_index=True).drop_duplicates() if drug_parts else pd.DataFrame()
    print(f'{path.name}: {raw_rows:,} rows; {candidate_rows:,} GLP-1 candidate rows; years {sorted(detected)}')
    return all_out,glp_out,mapping,{'file':path.name,'source_rows':raw_rows,'glp_candidate_rows':candidate_rows,
                                   'years':','.join(map(str,sorted(detected)))}


def main(input_dir=INPUT_DIR, output_dir=OUTPUT_DIR):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    if not input_dir.is_dir():
        raise FileNotFoundError(
            f"Input folder not found: {input_dir}\n"
            "Put this script in your glp1_boom project root and verify the data folder."
        )
    files = sorted(input_dir.glob("sdud20[0-9][0-9].csv"))
    if not files:
        raise FileNotFoundError(f"No sdudYYYY.csv files found in: {input_dir}")
    present_years = set()
    for path in files:
        year = int(path.stem[-4:])
        if year not in EXPECTED_YEARS:
            raise ValueError(f"Unexpected year: {path.name}")
        present_years.add(year)
    missing_years = EXPECTED_YEARS - present_years
    if missing_years:
        raise FileNotFoundError(f"Missing SDUD file(s) for years: {sorted(missing_years)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    all_year, glp_year, mappings, logs = [], [], [], []
    print(f"Reading {len(files)} CSVs from {input_dir}", flush=True)
    for file in files:
        a, g, m, log = process_one(file, output_dir)
        file_year = int(file.stem[-4:])
        detected = {int(x) for x in log['years'].split(',') if x}
        if detected != {file_year}:
            raise ValueError(f"{file.name} has unexpected year values: {detected}")
        if not a.empty: all_year.append(a)
        if not g.empty: glp_year.append(g)
        if not m.empty: mappings.append(m)
        logs.append(log)

    all_out = combine_partial(all_year, ALL_KEY).rename(columns=RENAMES)
    glp_out = combine_partial(glp_year, KEY).rename(columns=RENAMES)
    all_out['has_suppression'] = all_out['suppressed_rows'] > 0
    glp_out['has_suppression'] = glp_out['suppressed_rows'] > 0
    all_out.to_csv(output_dir / 'all_drugs_state_year_type.csv', index=False)
    glp_out.to_csv(output_dir / 'glp1_state_product_year_type.csv', index=False)
    map_out = (pd.concat(mappings, ignore_index=True)
               .drop_duplicates().sort_values(['product','NDC'])) if mappings else pd.DataFrame()
    map_out.to_csv(output_dir / 'glp1_ndc_candidates_REVIEW.csv', index=False)
    pd.DataFrame(logs).to_csv(output_dir / 'ingestion_audit.csv', index=False)

    state_keys=['Year','State']
    summation=['units_observed','prescriptions_observed','total_reimbursement_observed',
               'medicaid_reimbursement_observed','non_medicaid_reimbursement_observed',
               'rows','suppressed_rows','unsuppressed_rows']
    full = all_out.groupby(state_keys)[summation].sum(min_count=1).reset_index().add_prefix('all_')
    full = full.rename(columns={'all_Year':'Year','all_State':'State'})
    subset = glp_out.loc[glp_out['category']!='combination'].groupby(state_keys)[summation].sum(min_count=1).reset_index().add_prefix('glp1_')
    subset = subset.rename(columns={'glp1_Year':'Year','glp1_State':'State'})
    result = full.merge(subset, on=state_keys, how='left')
    # A missing GLP-1 group means no candidate NDC was matched, not that a suppressed value is zero.
    for col in ['glp1_prescriptions_observed','glp1_total_reimbursement_observed']:
        result[col] = result[col].fillna(0)
    result['glp1_share_of_observed_reimbursement_pct'] = (
        100 * result['glp1_total_reimbursement_observed'] /
        result['all_total_reimbursement_observed'].replace(0, float('nan'))
    )
    result['has_any_suppression'] = result['all_suppressed_rows'] > 0
    result.to_csv(output_dir / 'state_year_glp1_vs_all.csv', index=False)
    print(f"\nSuccess: created outputs in {output_dir}")
    print("IMPORTANT: XX is a national aggregate; do not add it to state totals.")
    print("IMPORTANT: suppressed rows are not zeros; NDC classifications require review.")

if __name__=='__main__': main()
