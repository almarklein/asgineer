import os
import inspect

import asgish

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def get_request_docs():
    """ Get the reference documentation from the source code.
    """
    parts = []

    for ob in (asgish.Request, asgish.handler2asgi):

        sig = str(inspect.signature(ob))
        if isinstance(ob, type):
            classname = ob.__name__
            parts.append(
                "### class ``{}{}``\n\n{}".format(classname, sig, get_doc(ob, 4))
            )
            for name, attr in ob.__dict__.items():
                if name.startswith("_") or not getattr(attr, "__doc__", None):
                    pass
                elif callable(attr):
                    sig = str(inspect.signature(attr))
                    sig = "(" + sig[5:].lstrip(", ") if sig.startswith("(self") else sig
                    parts.append(
                        "**``{}.{}{}``** - {}".format(
                            classname, name, sig, get_doc(attr, 8)
                        )
                    )
                else:
                    parts.append(
                        "**``{}.{}``** - {}".format(classname, name, get_doc(attr, 8))
                    )
            # parts.append('##')
        else:
            parts.append("### function ``{}{}``\n\n{}".format(ob.__name__, sig, get_doc(ob, 4)))

    return "\n".join(parts)


def get_doc(ob, dedent):
    """ Strip and dedent docstrings from an object. """
    lines = ob.__doc__.strip().splitlines()
    for i in range(1, len(lines)):
        lines[i] = lines[i][dedent:]
    lines.append("")
    return "\n".join(lines)


def main():

    # Read
    filename = os.path.join(THIS_DIR, "README.md")
    with open(filename, "rb") as f:
        text = f.read().decode().rstrip()

    # Insert docs
    docs = get_request_docs()
    lines = []
    skip = False
    for line in text.splitlines():
        if not skip:
            lines.append(line)
            if line.startswith("<!-- begin docs -->"):
                skip = True
                lines.extend(docs.splitlines())
        elif line.startswith("<!-- end docs -->"):
            lines.append(line)
            skip = False

    # Write back
    lines.append("")  # add empty line at end
    with open(filename, "wb") as f:
        f.write("\n".join(lines).encode())


if __name__ == "__main__":
    main()
