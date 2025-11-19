def render_template(file: str, **variables: str) -> bytes:
    """
    Renders a template file that contains variables in the format {{ name }}
    :param file: file to render
    :param variables: key/value pairs
    :return:
    """
    with open(file, "r") as f:
        page = f.read()

        for key, value in variables.items():
            page = page.replace("{{ " + key + " }}", value)

        return page.encode("utf-8")
