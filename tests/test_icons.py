"""Preserve generated resource verification without obsolete starter adoption."""
import base64
import json
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]


class IconTests(unittest.TestCase):
    def test_png_is_real_rgba_and_exact_svg_payload(self):
        name = json.loads((ROOT / "template.json").read_text())["repository"]
        resources = ROOT / "component" / name / "Resources"
        png = (resources / "logo.png").read_bytes()
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">IIBBBBB", png[16:29]), (1024, 1024, 8, 6, 0, 0, 0))
        position = 8
        compressed = b""
        kinds = []
        while position < len(png):
            length = struct.unpack(">I", png[position:position + 4])[0]
            kind = png[position + 4:position + 8]
            payload = png[position + 8:position + 8 + length]
            checksum = struct.unpack(">I", png[position + 8 + length:position + 12 + length])[0]
            self.assertEqual(checksum, zlib.crc32(kind + payload) & 0xffffffff)
            kinds.append(kind)
            if kind == b"IDAT":
                compressed += payload
            position += length + 12
        # Critical chunks only IHDR/IDAT/IEND; ancillary metadata such as sRGB or eXIf is allowed.
        self.assertEqual(kinds[0], b"IHDR")
        self.assertEqual(kinds[-1], b"IEND")
        self.assertEqual({kind for kind in kinds if kind[:1].isupper()}, {b"IHDR", b"IDAT", b"IEND"})
        self.assertEqual(len(zlib.decompress(compressed)), 1024 * (1 + 1024 * 4))
        svg = ET.parse(resources / "logo.svg").getroot()
        href = svg[0].attrib["{http://www.w3.org/1999/xlink}href"]
        self.assertTrue(href.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode("".join(href.split(",", 1)[1].split()), validate=True), png)
        for logo in ("logo.png", "logo.svg"):
            self.assertEqual((resources / logo).read_bytes(), (ROOT / "assets" / logo).read_bytes())
