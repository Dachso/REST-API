from fastapi import FastAPI, HTTPException, Path, Body
from pydantic import BaseModel, Field, field_validator
from datetime import date
from babel import Locale
import pandas as pd
import numpy as np
import uvicorn
import calendar
import webbrowser

app = FastAPI(title="Outgoing correspondence: sent by Thomas Mann.")

# Dataset laden + "clean"
df = pd.read_csv("outgoing.csv", sep=";", encoding="utf-8", na_values=[""])
df.replace({np.nan: "Daten fehlen"}, inplace=True)

# Muster
reference_code_pattern = r"^B-I-[A-Z]+-\d+(\.\d+)?$" # Erlaubt: "B-I-GROßBUCHSTABEN-ZAHL(.ZAHL)", z. B. "B-I-ALBER-3" oder "B-I-ALBER-3.1"
date_pattern = r"^(ca\.\s*)?(\d{2}\.\d{2}\.\d{4}|\d{2}\.\d{4}|\d{4})$" # Erlaubt: "ca. DD.MM.YYYY", "DD.MM.YYYY", "ca. MM.YYYY", "MM.YYYY", "ca. YYYY", "YYYY"
extent_pattern = r"^(\d+\sBl\./\d+\sS\.)(\s\+\s\d+\sBl\./\d+\sS\.)*$" # Erlaubt: ZAHL Bl./ZAHL S.( + ZAHL Bl./ZAHL S.)

# Thomas Manns Lebensdauer
birth_date = date(1875, 6, 6)
death_date = date(1955, 8, 12)

# Korrespondenz-Klasse
class Correspondence(BaseModel):
    reference_code: str = Field(
        ..., 
        description="Must be in the format B-I-UPPERCASE-NUMBERS(.NUMBERS), e.g. 'B-I-ALBER-3' or 'B-I-ALBER-3.1'.",
        pattern=reference_code_pattern,
        alias="Signatur"
    )
    title: str = Field(..., alias="Titel")
    scope_and_content: str = Field(..., alias="Form und Inhalt")
    date: str = Field(
        ..., 
        description="Must be in the format 'ca. DD.MM.YYYY', 'DD.MM.YYYY', 'ca. MM.YYYY', 'MM.YYYY', 'ca. YYYY', 'YYYY'.",
        pattern=date_pattern,
        alias="Entstehungszeitraum"
    )
    notes_on_date: str = Field(..., alias="Bemerkungen zur Datierung")
    extent: str = Field(
        ..., 
        description="Must be in the format NUMBER Bl./NUMBER S.( + NUMBER Bl./NUMBER S.).",
        pattern=extent_pattern,
        alias="Bemerkungen zum Umfang"
    )
    language: str = Field(..., alias="Sprachen")
    id: int = Field(
        ..., 
        description="Must be greater or equal than 0.",
        ge=0,
        alias="ID"
    )

    model_config = {
        "populate_by_name": True, # Damit Pydantic Aliasse im Request-Body erlaubt
        "json_schema_extra": {
            "example": {
                "Signatur": "B-I-CANT-1",
                "Titel": "Thomas Mann an Georg Cantor",
                "Form und Inhalt": "Kopie des Briefes vom 01.01.1900 aus Zürich, handschriftlich",
                "Entstehungszeitraum": "01.01.1900",
                "Bemerkungen zur Datierung": "",
                "Bemerkungen zum Umfang": "1 Bl./1 S.",
                "Sprachen": "Klingonisch",
                "ID": 42
            }
        } # Bsp. für den Request Body im Swagger UI
    }

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
    
    @staticmethod
    def get_german_language_names():
        locale = Locale("de")

        return locale.languages # dict: {"en": "Englisch", "de": "Deutsch", ...}
    
    # Prüft, ob Sprache sinnvoll ist
    @field_validator("language")
    @classmethod
    def check_language_possible(cls, v: str):
        language_stripped = v.strip()
        german_names = cls.get_german_language_names()
        german_names_lower = {name.lower() for name in german_names.values()}

        if language_stripped.lower() not in german_names_lower:
            raise ValueError(f"Die Sprache '{v}' ist keine bekannte Sprache auf Deutsch.")
        
        return language_stripped

# Liefert alle Einträge als JSON-Liste
@app.get("/all-correspondences")
async def get_all_correspondences():
    entry = df.to_dict(orient="records")

    return {"message": f"Einträge wurden erfolgreich abgerufen.", "correspondence": entry}

# Liefert einen Eintrag als JSON
@app.get("/correspondence/{id}")
async def get_one_correspondence(id: int = Path(..., ge=0)):
    row = df.loc[df["ID"] == id]
    
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Eintrag mit ID {id} nicht gefunden.")
    
    entry = row.iloc[0].to_dict()

    return {"message": f"Eintrag mit ID {id} wurde erfolgreich abgerufen.", "correspondence": entry}

# Postet einen Eintrag als DataFrame-Zeile
@app.post("/correspondence", status_code=201)
async def add_correspondence(correspondence: Correspondence):
    global df

    # ID einmalig?
    if correspondence.id in df["ID"].values:
        raise HTTPException(status_code=400, detail=f"ID '{correspondence.id}' existiert bereits.")
    
    # Signatur einmalig?
    if correspondence.reference_code in df["Signatur"].values:
        raise HTTPException(status_code=400, detail=f"Signatur '{correspondence.reference_code}' existiert bereits.")

    new_entry = {
        "Signatur": correspondence.reference_code,
        "Titel": correspondence.title,
        "Form und Inhalt": correspondence.scope_and_content,
        "Entstehungszeitraum": correspondence.date,
        "Bemerkungen zur Datierung": correspondence.notes_on_date,
        "Bemerkungen zum Umfang": correspondence.extent,
        "Sprachen": correspondence.language,
        "ID": correspondence.id
    }

    for key, value in new_entry.items():
        if isinstance(value, str):
            new_entry[key] = value.strip() or "Daten fehlen"

    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv("outgoing.csv", sep=";", index=False, encoding="utf-8") # Eintrag wird in Datei gespeichert

    return {"message": "Eintrag wurde erfolgreich hinzugefügt.", "correspondence": new_entry}

# Löscht einen Eintrag
@app.delete("/correspondence/{id}", status_code=200)
async def delete_correspondence(id: int = Path(..., ge=0)):
    global df
    row_index = df.index[df["ID"] == id].tolist()

    if not row_index:
        raise HTTPException(status_code=404, detail=f"Eintrag mit ID {id} nicht gefunden.")

    df = df.drop(index=row_index[0]).reset_index(drop=True)
    df.to_csv("outgoing.csv", sep=";", index=False, encoding="utf-8")

    return {"message": f"Eintrag mit ID {id} wurde erfolgreich gelöscht.", "deleted_id": id}

# Updatet einen Eintrag
@app.put("/correspondence/{id}", status_code=200)
async def replace_correspondence(id: int = Path(..., ge=0), correspondence: Correspondence = Body(...)):
    # Pfad-ID == Body-ID?
    if correspondence.id != id:
        raise HTTPException(status_code=400, detail=f"Body-ID {correspondence.id} muss mit Pfad-ID {id} übereinstimmen.")

    # Existiert ID?
    index = df.index[df["ID"] == id].tolist()
    if not index:
        raise HTTPException(status_code=404, detail=f"Eintrag mit ID {id} nicht gefunden.")
    row_index = index[0]

    # Signatur einmalig?
    existing_sigs = set(df.loc[df.index != row_index, "Signatur"].tolist())
    if correspondence.reference_code in existing_sigs:
        raise HTTPException(status_code=400, detail=f"Signatur '{correspondence.reference_code}' existiert bereits.")

    new_entry = {
        "Signatur": correspondence.reference_code,
        "Titel": correspondence.title,
        "Form und Inhalt": correspondence.scope_and_content,
        "Entstehungszeitraum": correspondence.date,
        "Bemerkungen zur Datierung": correspondence.notes_on_date or "Daten fehlen",
        "Bemerkungen zum Umfang": correspondence.extent,
        "Sprachen": correspondence.language,
        "ID": correspondence.id
    }

    for col, val in new_entry.items():
        df.at[row_index, col] = val

    df.to_csv("outgoing.csv", sep=";", index=False, encoding="utf-8")

    return {"message": f"Eintrag mit ID {id} wurde erfolgreich aktualisiert.", "correspondence": new_entry}

# Startet Uvicorn-Server
if __name__ == "__main__":
    url = "http://127.0.0.1:5000/docs"
    webbrowser.open(url)
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True, log_level="info")