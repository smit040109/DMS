"""
GO OIL — Coupon print template engine (image-based).

This module composits the OFFICIAL approved CorelDraw artwork (exported to PDF by
the owner and rasterised to PNG) as the master print template and overlays ONLY
the dynamic fields onto it:

    * Coupon Value  (₹.. / .. Points)  — on the FRONT
    * QR Code       (secure v2 payload) — on the BACK
    * Visible Serial Number             — on the BACK (inside the QR white box)

The artwork itself (black die-cut circle, gold GOOiL logo, halftone texture,
CONGRATULATIONS ribbon, MECHANIC COUPON label, T&C etc.) is NEVER redrawn — it
comes straight from the owner's approved PNG templates in
``backend/assets/coupon_template``.

Print engine spec (per owner requirement):
    * Paper size : 11 x 17 inch
    * Coupon     : 35 mm round (die-cut) — FRONT & BACK identical physical size
    * Cutting-friendly auto grid (equal margins, mirrored back for duplex)
    * Auto sheet calculation, mixed values on one sheet, front & back sheets.
"""
from __future__ import annotations

import io
import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

# ── asset locations ────────────────────────────────────────────────────────
_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets", "coupon_template")
_FRONT_PNG = os.path.join(_ASSET_DIR, "coupon_front.png")
_BACK_PNG = os.path.join(_ASSET_DIR, "coupon_back.png")
_GEOM_JSON = os.path.join(_ASSET_DIR, "geometry.json")

# ── fonts (dynamic overlay only — artwork fonts stay in the PNG) ────────────
# Bundled with the app so print output is deploy-proof (no system-font reliance).
_FONT_DIR = os.path.join(_ASSET_DIR, "fonts")
_VALUE_FONT = os.path.join(_FONT_DIR, "FreeSansBold.ttf")            # has ₹ glyph
_VALUE_FONT_FALLBACK = os.path.join(_FONT_DIR, "LiberationSans-Bold.ttf")
_SERIAL_FONT = os.path.join(_FONT_DIR, "LiberationMono-Bold.ttf")

_GOLD = (242, 198, 52)          # value gold to match artwork
_GOLD_SHADOW = (0, 0, 0, 210)

# Print layout spec — 11 x 17 in sheet, 35 mm round coupon, cutting-friendly grid
PAGE_W_IN, PAGE_H_IN = 11.0, 17.0
COUPON_MM = 35.0
MIN_GAP_MM = 3.5                 # minimum cutting margin between coupons


def _auto_grid(page_w_pts: float, page_h_pts: float,
               d_pts: float, min_gap_pts: float) -> tuple[int, int]:
    """Largest COLS x ROWS grid of `d`-diameter coupons that fits `page`
    while keeping at least `min_gap` between/around coupons (cut-friendly)."""
    cols = max(1, int((page_w_pts - min_gap_pts) // (d_pts + min_gap_pts)))
    rows = max(1, int((page_h_pts - min_gap_pts) // (d_pts + min_gap_pts)))
    return cols, rows


from reportlab.lib.units import inch as _inch, mm as _mm  # noqa: E402  (grid calc)
# FIXED cutting-friendly grid: 7 columns x 11 rows = 77 coupons per 11x17in sheet
# (35 mm round die-cut). This is a business requirement — do not auto-shrink.
COLS, ROWS = 7, 11
PER_SHEET = COLS * ROWS          # 11x17 / 35mm → 7 x 11 = 77

_RENDER_PX = 480                 # per-coupon compose resolution (~350 DPI @ 35mm)

# ── Brand text crisp-redraw config (preserve artwork, only sharpen wording) ──
# The approved artwork bakes "Hi-Technoply Automotive" as a LOW-RES raster that
# looks pixelated when scaled. We mask ONLY that text strip and redraw the exact
# same wording with a clean bundled font — halftone dots + logo + ribbon stay.
_BRAND_TEXT = "Hi-Technoply Automotive"
# (y0_frac, y1_frac, target_text_width_frac) per side — tuned to the artwork
_BRAND_BAND = {
    "front": (0.350, 0.410, 0.60),
    "back": (0.294, 0.350, 0.52),
}
_BRAND_FILL = (252, 252, 252)          # crisp white, matches artwork
_BRAND_BG = (9, 8, 8, 255)             # near-black backdrop behind the wording


@lru_cache(maxsize=1)
def _geometry() -> Dict[str, Any]:
    with open(_GEOM_JSON) as fh:
        return json.load(fh)


@lru_cache(maxsize=2)
def _template(side: str) -> Image.Image:
    path = _FRONT_PNG if side == "front" else _BACK_PNG
    img = Image.open(path).convert("RGBA")
    try:
        _sharpen_brand_text(img, side)     # crisp "Hi-Technoply Automotive"
    except Exception:
        pass                               # never fail the print over cosmetics
    return img


def _sharpen_brand_text(img: Image.Image, side: str) -> None:
    """In-place: mask the pixelated 'Hi-Technoply Automotive' strip and redraw
    the SAME wording crisply. Halftone dots / logo / ribbon are preserved."""
    band = _BRAND_BAND.get(side)
    if not band:
        return
    W, H = img.size
    y0f, y1f, wf = band
    y0, y1 = int(y0f * H), int(y1f * H)
    xa, xb = int(0.12 * W), int(0.88 * W)

    # 1) build a mask of the existing (near-white) wording inside the strip
    rgb = np.asarray(img.convert("RGB"))
    sub = rgb[y0:y1, xa:xb]
    text_mask = (sub.min(axis=2) > 125).astype("uint8") * 255
    m = Image.fromarray(text_mask, "L").filter(ImageFilter.MaxFilter(9))

    # 2) paint over ONLY those pixels with the near-black backdrop
    backdrop = Image.new("RGBA", (xb - xa, y1 - y0), _BRAND_BG)
    img.paste(backdrop, (xa, y0), m)

    # 3) redraw the exact wording, centered, fitted to the artwork proportions
    draw = ImageDraw.Draw(img)
    cx = 0.5 * W
    cy = (y0 + y1) / 2
    max_w = wf * W
    max_h = (y1 - y0) * 0.92
    font = _fit_font(draw, _BRAND_TEXT, _VALUE_FONT_FALLBACK,
                     max_w, max_h, int(max_h * 1.25))
    _draw_centered(draw, cx, cy, _BRAND_TEXT, font, fill=_BRAND_FILL)


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(_VALUE_FONT_FALLBACK, size)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, font_path: str,
              max_w: float, max_h: float, start: int) -> ImageFont.FreeTypeFont:
    """Shrink the font until the text fits inside (max_w, max_h)."""
    size = start
    while size > 8:
        f = _font(font_path, size)
        bb = draw.textbbox((0, 0), text, font=f)
        if (bb[2] - bb[0]) <= max_w and (bb[3] - bb[1]) <= max_h:
            return f
        size -= 2
    return _font(font_path, 8)


def _draw_centered(draw: ImageDraw.ImageDraw, cx: float, cy: float, text: str,
                   font: ImageFont.FreeTypeFont, fill, shadow=None) -> None:
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x = cx - tw / 2 - bb[0]
    y = cy - th / 2 - bb[1]
    if shadow:
        off = max(1, font.size // 40)
        draw.text((x + off, y + off), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def format_value(coupon_type: str, coupon_value: Any) -> str:
    """₹300/- for cash, '20 Points' for reward — matches approved artwork."""
    try:
        v = float(coupon_value)
        v_str = f"{int(v)}" if v.is_integer() else f"{v:g}"
    except Exception:
        v_str = str(coupon_value)
    if (coupon_type or "").lower() == "cash":
        return f"\u20b9{v_str}/-"
    return f"{v_str} Points"


def render_coupon(side: str, *, value_text: Optional[str] = None,
                  qr_payload: Optional[str] = None, serial: Optional[str] = None,
                  px: int = _RENDER_PX) -> Image.Image:
    """Composite ONE coupon (front or back) at ``px`` resolution."""
    base = _template(side).resize((px, px), Image.LANCZOS).copy()
    W = H = px
    draw = ImageDraw.Draw(base)
    g = _geometry()

    if side == "front":
        v = g["value"]
        max_w = v["max_w"] * W
        max_h = v["max_h"] * H
        text = value_text or ""
        font = _fit_font(draw, text, _VALUE_FONT, max_w, max_h, int(max_h * 1.15))
        _draw_centered(draw, v["cx"] * W, v["cy"] * H, text, font,
                       fill=_GOLD, shadow=_GOLD_SHADOW)
    else:  # back — QR + serial inside the white box (artwork keeps its own T&C)
        box = g["qr_box"]
        bx0, by0 = box["x0"] * W, box["y0"] * H
        bx1, by1 = box["x1"] * W, box["y1"] * H
        # opaque white box covers the sample QR from the artwork
        draw.rounded_rectangle([bx0, by0, bx1, by1],
                               radius=int((bx1 - bx0) * 0.03), fill=(255, 255, 255))
        box_w = bx1 - bx0
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                           box_size=10, border=1)
        qr.add_data(qr_payload or "")
        qr.make(fit=True)
        qimg = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qs = int(box_w * 0.80)
        qimg = qimg.resize((qs, qs), Image.NEAREST)
        qx = int((bx0 + bx1) / 2 - qs / 2)
        qy = int(by0 + box_w * 0.04)
        base.paste(qimg, (qx, qy))
        if serial:
            strip_top = qy + qs
            strip_cy = (strip_top + by1) / 2
            sfont = _fit_font(draw, serial, _SERIAL_FONT,
                              box_w * 0.92, (by1 - strip_top) * 0.85,
                              int(box_w * 0.11))
            _draw_centered(draw, (bx0 + bx1) / 2, strip_cy, serial, sfont,
                           fill=(15, 15, 15))
    return base


def _coupon_payload(cp: Dict[str, Any]) -> str:
    """Secure v2 QR payload — never exposes UUID / secret / signature / db ids."""
    if cp.get("qr_version") == "v2" and cp.get("qr_ciphertext_b64") and cp.get("qr_signature_v2"):
        return f"GOOIL2|{cp['qr_ciphertext_b64']}|{cp['qr_signature_v2']}"
    # legacy fallback
    return f"{cp.get('coupon_code') or cp.get('visible_serial')}"


# ── Fast overlay renderers (used by build_print_pdf) ────────────────────────
# The big performance/size win: the STATIC artwork (front-per-value & back) is
# embedded ONCE as a shared image XObject. Per coupon we only overlay a tiny QR
# bitmap + vector serial text on the canvas instead of embedding a unique full
# raster for every single coupon (which made 1400-coupon PDFs ~250 MB & time out).

from reportlab.pdfbase import pdfmetrics          # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont      # noqa: E402

_SERIAL_PDF_FONT = "CouponSerialMono"
_serial_font_ready = False


def _ensure_serial_font() -> None:
    global _serial_font_ready
    if _serial_font_ready:
        return
    try:
        pdfmetrics.registerFont(TTFont(_SERIAL_PDF_FONT, _SERIAL_FONT))
    except Exception:
        pass
    _serial_font_ready = True


@lru_cache(maxsize=8)
def _front_base_reader(value_text: str) -> ImageReader:
    """Full FRONT artwork with the value baked in — one per distinct value."""
    return ImageReader(render_coupon("front", value_text=value_text))


@lru_cache(maxsize=1)
def _back_base_reader() -> ImageReader:
    """Static BACK artwork (with the sample-QR area whitened) — NO per-coupon
    QR/serial. Embedded once and reused for every back coupon."""
    base = _template("back").resize((_RENDER_PX, _RENDER_PX), Image.LANCZOS).copy()
    draw = ImageDraw.Draw(base)
    g = _geometry()
    box = g["qr_box"]
    W = H = _RENDER_PX
    bx0, by0 = box["x0"] * W, box["y0"] * H
    bx1, by1 = box["x1"] * W, box["y1"] * H
    draw.rounded_rectangle([bx0, by0, bx1, by1],
                           radius=int((bx1 - bx0) * 0.03), fill=(255, 255, 255))
    return ImageReader(base)


def _qr_reader(payload: str) -> ImageReader:
    """Small 1-bit QR bitmap for one coupon (cheap to generate & embed)."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                       box_size=4, border=1)
    qr.add_data(payload or "")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("1")
    return ImageReader(img)


def _qr_png(payload: str) -> bytes:
    """Module-level (picklable) QR→PNG bytes — used for parallel pre-generation."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                       box_size=4, border=1)
    qr.add_data(payload or "")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("1")
    b = io.BytesIO()
    img.save(b, format="PNG")
    return b.getvalue()


def _parallel_qr_pngs(payloads: List[str]) -> Optional[List[bytes]]:
    """Pre-generate all QR PNGs across CPU cores. Best-effort — returns None
    (caller falls back to serial) if the pool is unavailable. QR generation with
    ERROR_CORRECT_H is the dominant cost for large batches, so this cuts the wall
    time substantially on multi-core hosts."""
    if len(payloads) < 150:
        return None
    try:
        import concurrent.futures as _futures
        workers = min(8, max(2, (os.cpu_count() or 2)))
        with _futures.ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(_qr_png, payloads, chunksize=32))
    except Exception:
        return None


def build_print_pdf(coupons: List[Dict[str, Any]], *, side: str = "both",
                    title: str = "coupons",
                    lead_blank_sheet: bool = True,
                    pad_last_sheet: bool = True) -> bytes:
    """
    Build a commercial print-ready PDF (11x17in, 35 mm round die-cut, 7x11 = 77
    per sheet, cutting-friendly grid).

    Layout requirements (business):
      * ``lead_blank_sheet`` — a SINGLE BLANK "dye" sheet with 77 empty 35 mm
        circles is added ONCE at the very START of the whole document (before the
        front side only, used to calibrate the 35 mm die-cut). It is never
        repeated for the back side.
      * ``pad_last_sheet``  — the last partially-filled coupon sheet is padded up
        to 77 with blank 35 mm circles.

    ``side`` : 'front' | 'back' | 'both' (front sheets then mirrored back sheets).
    Returns PDF bytes.
    """
    if side not in ("front", "back", "both"):
        side = "both"

    _ensure_serial_font()
    g = _geometry()
    qbox = g["qr_box"]
    qx0, qy0, qx1, qy1 = qbox["x0"], qbox["y0"], qbox["x1"], qbox["y1"]
    qbw = (qx1 - qx0)                       # qr-box width as fraction of coupon

    page_w = PAGE_W_IN * inch
    page_h = PAGE_H_IN * inch
    d_pts = COUPON_MM * mm
    gap_x = (page_w - COLS * d_pts) / (COLS + 1)
    gap_y = (page_h - ROWS * d_pts) / (ROWS + 1)

    buf = io.BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=(page_w, page_h))

    n = len(coupons)
    n_sheets = max(1, (n + PER_SHEET - 1) // PER_SHEET)

    # Pre-generate all QR bitmaps in parallel (dominant cost for large batches).
    qr_pngs: Optional[List[bytes]] = None
    if side in ("back", "both"):
        qr_pngs = _parallel_qr_pngs([_coupon_payload(cp) for cp in coupons])

    def _pos(idx_in_sheet: int, mirror: bool):
        col = idx_in_sheet % COLS
        row = idx_in_sheet // COLS
        if mirror:                       # mirror columns for duplex back alignment
            col = COLS - 1 - col
        x = gap_x + col * (d_pts + gap_x)
        y = page_h - (gap_y + row * (d_pts + gap_y)) - d_pts
        return x, y

    def _blank_circle(idx_in_sheet: int, mirror: bool):
        x, y = _pos(idx_in_sheet, mirror)
        c.saveState()
        c.setLineWidth(0.5)
        c.setDash(2, 2)
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.circle(x + d_pts / 2.0, y + d_pts / 2.0, d_pts / 2.0, stroke=1, fill=0)
        c.restoreState()

    def _blank_sheet(mirror: bool):
        for i in range(PER_SHEET):
            _blank_circle(i, mirror)
        c.showPage()

    def _draw_back_overlay(x: float, y: float, cp: Dict[str, Any], gidx: int):
        # QR position (mirrors render_coupon geometry, mapped to page coords)
        qs = 0.80 * qbw                      # qr size as fraction of coupon
        qr_left = x + (qx0 + 0.10 * qbw) * d_pts
        qr_top_frac = qy0 + 0.04 * qbw
        qr_bottom_frac = qr_top_frac + qs
        qr_bottom = y + d_pts * (1.0 - qr_bottom_frac)
        qr_sz = qs * d_pts
        if qr_pngs is not None:
            reader = ImageReader(io.BytesIO(qr_pngs[gidx]))
        else:
            reader = _qr_reader(_coupon_payload(cp))
        c.drawImage(reader, qr_left, qr_bottom,
                    width=qr_sz, height=qr_sz, preserveAspectRatio=True)
        serial = cp.get("visible_serial") or cp.get("coupon_code")
        if serial:
            strip_cy_frac = ((qr_top_frac + qs) + qy1) / 2.0
            cy = y + d_pts * (1.0 - strip_cy_frac)
            fsz = max(4.0, 0.11 * qbw * d_pts)
            c.setFillColorRGB(0.06, 0.06, 0.06)
            try:
                c.setFont(_SERIAL_PDF_FONT, fsz)
            except Exception:
                c.setFont("Helvetica-Bold", fsz)
            cx = x + ((qx0 + qx1) / 2.0) * d_pts
            c.drawCentredString(cx, cy - fsz * 0.35, str(serial))

    def _draw_side(which: str, with_blank: bool):
        mirror = (which == "back")
        if with_blank:
            _blank_sheet(mirror)
        for s in range(n_sheets):
            chunk = coupons[s * PER_SHEET:(s + 1) * PER_SHEET]
            for i, cp in enumerate(chunk):
                x, y = _pos(i, mirror)
                if which == "front":
                    vt = format_value(cp.get("coupon_type"), cp.get("coupon_value"))
                    c.drawImage(_front_base_reader(vt), x, y, width=d_pts, height=d_pts,
                                preserveAspectRatio=True, mask="auto")
                else:
                    c.drawImage(_back_base_reader(), x, y, width=d_pts, height=d_pts,
                                preserveAspectRatio=True, mask="auto")
                    _draw_back_overlay(x, y, cp, s * PER_SHEET + i)
            # pad the remaining positions of the LAST sheet with blank circles
            if pad_last_sheet and len(chunk) < PER_SHEET:
                for i in range(len(chunk), PER_SHEET):
                    _blank_circle(i, mirror)
            c.showPage()

    # A single BLANK "dye" calibration sheet is emitted ONCE at the very start of
    # the whole document (before the FRONT side only) — never per side.
    if side in ("front", "both"):
        _draw_side("front", with_blank=lead_blank_sheet)
    if side in ("back", "both"):
        # When both sides are produced the lead blank already appeared before the
        # front sheets, so the back side must NOT repeat it. For a back-only PDF we
        # still want the single lead blank.
        _draw_side("back", with_blank=(lead_blank_sheet and side == "back"))

    c.save()
    buf.seek(0)
    return buf.read()
