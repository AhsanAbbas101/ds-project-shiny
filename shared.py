from pathlib import Path

import pandas as pd

app_dir = Path(__file__).parent
holidays = pd.read_excel(app_dir / "public_holidays.xlsx")
