from fastapi import FastAPI, HTTPException, Path
import pandas as pd
import numpy as np
import uvicorn

app = FastAPI(title="Ausgehende Korrespondenz: gesendet von Thomas Mann")

# Dataset laden + "clean"
df = pd.read_csv("outgoing.csv", sep=";", encoding="latin1")
df.replace({np.nan: "Daten fehlen"}, inplace=True)

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

if __name__ == "__main__":
    uvicorn.run("main:app", port=5000, log_level="info")