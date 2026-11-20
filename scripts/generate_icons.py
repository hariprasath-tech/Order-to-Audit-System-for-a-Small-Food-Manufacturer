"""
Generates valid PWA icons (192x192, 512x512, and 512x512 maskable) in pure Python.
Draws brand background (#D9541E) with the signature Murukku spiral symbol.
"""

import math
import os
import struct
import zlib


def create_png_icon(filepath, size, is_maskable=False):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    w, h = size, size
    cx, cy = w / 2.0, h / 2.0
    radius_max = (w * 0.40) if is_maskable else (w * 0.44)

    # Color definitions (RGBA)
    brand_bg = (217, 84, 30, 255)  # #D9541E
    brand_gold = (242, 181, 46, 255)  # #F2B52E
    white = (255, 255, 255, 255)
    corner_radius = 0 if is_maskable else (w * 0.22)

    raw_data = bytearray()

    for y in range(h):
        raw_data.append(0)  # filter type 0 (None)
        for x in range(w):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)

            # Maskable icons fill entire canvas; standard icons have rounded squircle
            inside_squircle = True
            if not is_maskable:
                qx = abs(x - cx) - (cx - corner_radius)
                qy = abs(y - cy) - (cy - corner_radius)
                if qx > 0 and qy > 0 and (qx * qx + qy * qy) > (corner_radius * corner_radius):
                    inside_squircle = False

            if not inside_squircle:
                raw_data.extend((0, 0, 0, 0))
                continue

            # Base background
            r, g, b, a = brand_bg

            # Spiral motif: r(theta) = a + b * theta
            # Check proximity to spiral rings
            if dist < radius_max:
                spiral_val = (dist / (w * 0.07)) - (angle / (2 * math.pi))
                ring_dist = abs(spiral_val - round(spiral_val))
                if ring_dist < 0.18 and dist > (w * 0.05):
                    # Blend gold / white
                    if dist < radius_max * 0.5:
                        r, g, b = white[:3]
                    else:
                        r, g, b = brand_gold[:3]
                elif dist <= (w * 0.06):
                    # Center core dot
                    r, g, b = white[:3]

            raw_data.extend((r, g, b, a))

    def make_chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    compressed = zlib.compress(bytes(raw_data), level=9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)

    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", compressed)
        + make_chunk(b"IEND", b"")
    )

    with open(filepath, "wb") as f:
        f.write(png_bytes)
    print(f"Generated {filepath} ({w}x{h}, {len(png_bytes)} bytes)")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    img_dir = os.path.join(base_dir, "static", "img")
    create_png_icon(os.path.join(img_dir, "icon-192.png"), 192, is_maskable=False)
    create_png_icon(os.path.join(img_dir, "icon-512.png"), 512, is_maskable=False)
    create_png_icon(os.path.join(img_dir, "icon-maskable-512.png"), 512, is_maskable=True)
