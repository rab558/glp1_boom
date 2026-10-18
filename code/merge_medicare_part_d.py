
from pathlib import Path
import re
import sys
import pandas as pd

# Run from the glp1_boom repository root, or pass the data folder as an argument.
ROOT = (Path(sys.argv[1]) if len(sys.argv) > 1
        else Path(__file__).resolve().parent / 'Medicare_Pt_D_Spending')
ROOT = ROOT.resolve()
OUTPUT = ROOT / 'merged'
FIRST_YEAR, LAST_YEAR = 2016, 2024
METRICS = [
    'total_spending', 'total_dosage_units', 'total_claims', 'total_beneficiaries',
    'avg_spending_per_dosage_unit', 'avg_spending_per_claim',
    'avg_spending_per_beneficiary', 'outlier_flag',
]
SHEETS = {
    'drug': 'Spending & Utilization YTD',
    'manufacturer': 'Manufacturer Summary',
}


def release_year(path):
    if path.parent.name.isdigit() and len(path.parent.name) == 4:
        return int(path.parent.name)
    match = re.search(r'^DYT(?:20)?(\d{2})$', path.stem, re.IGNORECASE)
    return 2000 + int(match.group(1)) if match else None


def parse_sheet(path, kind):
    file = pd.ExcelFile(path)
    def norm(value):
        return re.sub(r'[^a-z0-9]+', '', str(value).lower())

    matches = [name for name in file.sheet_names
               if (norm(name).startswith('spendingutilizationytd') if kind == 'drug'
                   else norm(name).startswith('manufacturersummary'))]
    if len(matches) != 1:
        raise ValueError(f'{path.name}: expected one {kind} sheet, got {matches}')

    raw = pd.read_excel(file, sheet_name=matches[0], header=None)
    year_header_row = next((r for r in range(min(10, len(raw)))
                            if any(re.search(r'Calendar\s*Year\s*20\d{2}', str(v), re.I)
                                   for v in raw.iloc[r])), None)
    if year_header_row is None:
        raise ValueError(f'{path.name}: no calendar-year heading found in {matches[0]}')
    column_header_row = year_header_row + 1
    keys = ['brand_name', 'generic_name',
            'number_of_manufacturers' if kind == 'drug' else 'manufacturer']
    positions = []
    for col, heading in enumerate(raw.iloc[year_header_row]):
        hit = re.search(r'Calendar\s*Year\s*(20\d{2})', str(heading), re.I)
        if hit:
            positions.append((int(hit.group(1)), col))
    if not positions:
        raise ValueError(f'{path.name}: no annual groups found')

    expected = [
        'totalspending', 'totaldosageunits', 'totalclaims',
        'totalbeneficiaries', 'averagespendingperdosageunitweighted',
        'averagespendingperclaim', 'averagespendingperbeneficiary',
    ]
    results = {}
    for i, (year, start) in enumerate(positions):
        next_start = positions[i+1][1] if i+1 < len(positions) else raw.shape[1]
        names = [norm(v) for v in raw.iloc[column_header_row, start:next_start]]
        if len(names) < 7 or names[:4] != expected[:4] or not (
                names[4].startswith('averagespendingperdosageunit')
                and names[5].startswith('averagespendingperclaim')
                and names[6].startswith('averagespendingperbeneficiary')):
            raise ValueError(f'Unexpected metric layout in {path.name}, year {year}: {names}')
        has_outlier = len(names) >= 8 and 'outlier' in names[7]
        if len(names) > (8 if has_outlier else 7):
            trailing = names[8 if has_outlier else 7:]
            if i + 1 < len(positions) or not all(
                ('change' in n or 'growth' in n or n in ('', 'nan')) for n in trailing
            ):
                raise ValueError(f'Unrecognized extra columns in {path.name}, {year}: {trailing}')
        count = 8 if has_outlier else 7
        part = raw.iloc[column_header_row+1:, [0, 1, 2] + list(range(start, start+count))].copy()
        part.columns = keys + METRICS[:count]
        if not has_outlier:
            part['outlier_flag'] = pd.NA
        for col in keys:
            if col != 'number_of_manufacturers':
                part[col] = part[col].astype('string').str.strip().replace('', pd.NA)
        for col in METRICS:
            part[col] = pd.to_numeric(part[col].astype('string').str.strip(), errors='coerce')
        if kind == 'drug':
            part['number_of_manufacturers'] = pd.to_numeric(
                part['number_of_manufacturers'], errors='coerce')
        part = part.dropna(subset=['brand_name'])
        part = part.dropna(subset=['total_spending', 'total_claims', 'total_dosage_units'], how='all')
        part.insert(0, 'year', year)
        part['source_workbook'] = str(path.relative_to(ROOT))
        results[year] = part.reset_index(drop=True)
    return results


def main():
    if not ROOT.is_dir():
        raise FileNotFoundError(f'Folder not found: {ROOT.resolve()}')
    paths = sorted(p for p in ROOT.rglob('*.xlsx')
                   if p.stem.upper().startswith('DYT') and not p.name.startswith('~$'))
    releases = [(release_year(p), p) for p in paths]
    releases = [(year, path) for year, path in releases if year is not None]
    if not releases:
        raise FileNotFoundError(f'No DYT*.xlsx workbooks found under {ROOT.resolve()}')
    print('Workbooks found:', *(f'\n  {year}: {path}' for year, path in releases))
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for kind in SHEETS:
        parsed = {}
        for released, path in releases:
            for year, df in parse_sheet(path, kind).items():
                if FIRST_YEAR <= year <= LAST_YEAR:
                    parsed.setdefault(year, []).append((released, path, df))
        frames = []
        for year in range(FIRST_YEAR, LAST_YEAR+1):
            versions = parsed.get(year, [])
            if not versions:
                print(f'WARNING: {year} has no available data ({kind}).')
                continue
            exact = [entry for entry in versions if entry[0] == year]
            if exact:
                if len(exact) > 1:
                    raise ValueError(f'Duplicate release-year workbooks for {year}: {exact}')
                chosen = exact[0]
            else:
                newer = [entry for entry in versions if entry[0] > year]
                if not newer:
                    print(f'WARNING: {year} has only earlier releases, skipping ({kind})')
                    continue
                chosen = min(newer, key=lambda x: x[0])
                print(f'NOTE: {year} uses historical data from {chosen[1].name} ({kind})')
            frame = chosen[2]
            print(f'{kind:12} | {year} | {len(frame):6,} rows | {chosen[1].name}')
            frames.append(frame)
        if not frames:
            continue
        master = pd.concat(frames, ignore_index=True)
        key = ['year', 'brand_name', 'generic_name']
        if kind == 'manufacturer':
            key.append('manufacturer')
        duplicates = master.duplicated(key, keep=False)
        if duplicates.any():
            print(f'WARNING: {duplicates.sum()} records have repeated keys in {kind}; inspect them before aggregating.')
        filename = OUTPUT / f'part_d_{kind}_2016_2024.csv'
        master.to_csv(filename, index=False)
        print(f'Saved {filename} ({len(master):,} observations)\n')


if __name__ == '__main__':
    main()
