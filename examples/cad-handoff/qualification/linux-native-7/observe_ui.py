"""Read the isolated Linux desktop's AT-SPI native UI tree; no CAD model or application API."""
import json
import os
from pathlib import Path

os.environ["DBUS_SESSION_BUS_ADDRESS"] = Path("/work/dbus-address.txt").read_text().strip()
import pyatspi


def inspect(node, path="", depth=0):
    result = {"path": path, "name": node.name, "role": node.getRoleName(), "children": []}
    state = node.getState()
    result["focused"] = state.contains(pyatspi.STATE_FOCUSED)
    result["enabled"] = state.contains(pyatspi.STATE_ENABLED)
    try:
        text = node.queryText()
        result["text"] = text.getText(0, text.characterCount)
    except NotImplementedError:
        pass
    if depth < 16:
        for i in range(node.childCount):
            try:
                result["children"].append(inspect(node.getChildAtIndex(i), path + "." + str(i), depth + 1))
            except Exception as error:
                result["children"].append({"path": path + "." + str(i), "error": str(error)})
    return result


if __name__ == "__main__":
    print(json.dumps(inspect(pyatspi.Registry.getDesktop(0)), ensure_ascii=False, indent=2))
