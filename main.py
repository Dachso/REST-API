from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field, field_validator
from datetime import date
import pandas as pd
import numpy as np
import uvicorn
import calendar
import babel.languages

app = FastAPI(title="Outgoing correspondence: sent by Thomas Mann.")

# Dataset laden + "clean"
df = pd.read_csv("outgoing.csv", sep=";", encoding="latin1")
df.replace({np.nan: "Daten fehlen"}, inplace=True)

# Muster
reference_code_pattern = r"^B-I-[A-Z]+-\d+$" # Erlaubt: "B-I-GROßBUCHSTABEN-ZAHL", z. B. "B-I-ALBER-3"
date_pattern = r"^(ca\.\s*)?(\d{2}\.\d{2}\.\d{4}|\d{2}\.\d{4}|\d{4})$" # Erlaubt: "ca. DD.MM.YYYY", "DD.MM.YYYY", "ca. MM.YYYY", "MM.YYYY", "ca. YYYY", "YYYY"
extent_pattern = r"\d+\sBl\./\d+\sS\." # Erlaubt: ZAHL Bl./ZAHL S.

# Thomas Manns Lebensdauer
birth_date = date(1875, 6, 6)
death_date = date(1955, 8, 12)

# Korrespondenz-Klasse
class Correspondence(BaseModel):
    reference_code: str = Field(
        ..., 
        description="Must be in the format B-I-UPPERCASE-NUMBERS, e.g. 'B-I-ALBER-3'.",
        pattern=reference_code_pattern
    )
    title: str
    scope_and_content: str
    date: str = Field(
        ..., 
        description="Must be in the format 'ca. DD.MM.YYYY', 'DD.MM.YYYY', 'ca. MM.YYYY', 'MM.YYYY', 'ca. YYYY', 'YYYY'.",
        pattern=date_pattern
    )
    notes_on_date: str
    extent: str = Field(
        ..., 
        description="Must be in the format NUMBER Bl./NUMBER S.",
        pattern=extent_pattern
    )
    language: str
    id: int = Field(
        ..., description="Must be greater or equal then 0.", ge=0
    )

    # Prüft, ob Signatur bereits existiert
    @field_validator("reference_code")
    @classmethod
    def check_reference_code_unique(cls, v):
        if v in df["Signatur"].values:
            raise ValueError(f"Die Signatur '{v}' existiert bereits.")
        return v
    
    # Prüft, ob Datum sinnvoll ist
    @field_validator("date")
    @classmethod
    def check_date_possible(cls, v: str):
        processed_date_str = v.replace("ca. ", "").strip()
        parts = processed_date_str.split(".")
        try:
            if len(parts) == 3: # DD.MM.YYYY
                d, m, y = map(int, parts)
                start_date = end_date = date(y, m, d)
            elif len(parts) == 2: # MM.YYYY
                m, y = map(int, parts)
                start_date = date(y, m, calendar.monthrange(y, m)[1])
            else: # YYYY
                y = int(parts[0])
                start_date = date(y, 1, 1)
                end_date = date(y, 12, 31)
        except ValueError as e:
            raise ValueError(f"Invalid date components in '{v}': {e}") from e
        if not (start_date <= death_date and end_date >= birth_date):
            raise ValueError(
                f"Datum '{v}' (interpretiert als {start_date:%d.%m.%y} - {end_date:%d.%m.%y}) "
                f"ist ausserhalb Thomas Mann's Lebensdauer (06.06.1875 - 12.08.1955)."
            )
        return v
    
    # Prüft, ob Sprache sinnvoll ist
    @field_validator("language")
    @classmethod
    def check_language_possible(cls, v: str):
        language_stripped = v.strip()
        german_names_dict = babel.languages.get_display_names("de")
        german_names_dict_lower = {name.lower() for name in german_names_dict.values()}
        if language_stripped.lower() not in german_names_dict_lower:
            raise ValueError(f"Die Sprache '{v}' ist keine deutsche Sprache.")
        return language_stripped

    # Prüft, ob ID bereits existiert
    @field_validator("id")
    @classmethod
    def check_id_unique(cls, v):
        if v in df["ID"].values:
            raise ValueError(f"Die ID '{v}' existiert bereits.")
        return v

# Liefert alle Einträge als JSON-Liste
@app.get("/all-correspondences")
async def get_all_correspondences():
    return df.to_dict(orient="records")

# Liefert einen Eintrag als JSON
@app.get("/correspondence/{id}")
async def get_one_correspondence(id: int = Path(..., ge=0)): # URL-Pfad-Parameter id ist erforderlich, muss ein Integer und mindestens 0 sein
    row = df.loc[df["ID"] == id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Correspondence not found.")
    return row.iloc[0].to_dict()

# Startet Uvicorn-Server
if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, log_level="info")