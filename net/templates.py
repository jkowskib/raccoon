def render_template(file: str, **variables: str) -> bytes:
    with open(file, "r") as f:
        page = f.read()

        for key, value in variables.items():
            page = page.replace("{{ " + key + " }}", value)

        return page.encode("utf-8")
