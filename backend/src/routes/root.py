from src.routes import TAG, app


@app.get("/", tags=[TAG.Root])
def read_root():
    return {"Hello": "Museum APP"}
