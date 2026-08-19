#from pathlib import Path
import pandas as pd
import numpy as np

#filePath = Path(r"D:\Ipsit\Python Projects\acuteShortageAnalysis\ACUTE SHORTAGE_18 AUG 2026.xlsx")
filePath = "data/ACUTE SHORTAGE_18 AUG 2026.xlsx"

def load_and_clean_data(file_path: str) -> pd.DataFrame:
    df = pd.read_excel(file_path, header=2)
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Filter out blank rows and summary Grand Total row
    df = df[df['CATEGORY'].notna()]
    df = df[~df['CATEGORY'].astype(str).str.upper().str.contains('GRAND TOTAL')].copy()

    # Standardize column naming variations
    rename_dict = {
        'TOTAL STK QTY': 'TOTAL STK',
        '7D SALE QTY': '7D SALE',
        'WH QTY': 'WH QT',
        'TRANSIT Q': 'TRANSIT QTY',
        'PACK Q': 'PACK QTY'
    }
    df = df.rename(columns=rename_dict)

    # Convert numeric fields
    numeric_cols = [
        'BASE STOCK', 'STOCK QTY', 'TRANSIT QTY', 'PACK QTY',
        'TOTAL STK', '7D SALE', 'S/E QTY', 'WH QT', 'PENDING PO QTY'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', '').str.replace('-', '0'),
                errors='coerce'
            ).fillna(0)

    # Metrics
    df['TOTAL_PIPELINE'] = df['TOTAL STK'] + df['WH QT'] + df['PENDING PO QTY']
    df['NET_DEFICIT'] = df['BASE STOCK'] - df['TOTAL_PIPELINE']

    # Days of Inventory (DOI)
    daily_sales = df['7D SALE'] / 7
    df['DAYS_OF_INVENTORY'] = np.where(
        daily_sales > 0,
        df['TOTAL STK'] / daily_sales,
        999  # Large buffer for items with 0 sales
    )

    # DOI Slicer Buckets
    bins = [-1, 7, 14, 21, 28, 35, 42, 49, 56, 60, np.inf]
    labels = [
        '≤ 7 Days',
        '8 - 14 Days',
        '15 - 21 Days',
        '22 - 28 Days',
        '29 - 35 Days',
        '36 - 42 Days',
        '43 - 49 Days',
        '50 - 56 Days',
        '57 - 60 Days',
        '> 60 Days (or Zero Sales)'
    ]
    df['DOI_BUCKET'] = pd.cut(df['DAYS_OF_INVENTORY'], bins=bins, labels=labels)

    return df


"""try:
    df1 = load_and_clean_data(filePath)
    print('Success>>>>>>>>>>>>>>>>',df1)
except Exception as e:
    print('Error>>>>>>>>>>>>>>') """