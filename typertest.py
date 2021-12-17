import typer


app = typer.Typer()


@app.command()
def hello(name: str):
    message = typer.style(f"Hello {name}!", fg=typer.colors.GREEN, bold=True)
    typer.echo(message)

@app.command()
def goodbye(name: str, formal: bool=False):
    if formal:
        typer.echo("Goodbye, Mr. " + name + ".")
    else:
        typer.echo(f"Bye, {name}!")


if __name__ == "__main__":
    app()
    