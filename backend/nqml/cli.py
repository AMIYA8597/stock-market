import typer
from nqml.data.datasets import app as dataset_app

app = typer.Typer(help="NeuroQuant ML CLI")
app.add_typer(dataset_app, name="dataset", help="Dataset commands")

if __name__ == "__main__":
    app()
