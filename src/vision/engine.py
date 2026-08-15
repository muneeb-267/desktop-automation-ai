"""Screen capture, OCR text locate, and template matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class DetectionResult:
    found: bool
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    label: str = ""
    method: str = ""
    confidence: float = 0.0
    boxes: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def center(self) -> Tuple[int, int]:
        return self.x, self.y


class VisionEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = (config or {}).get("vision", {})
        paths = (config or {}).get("paths", {})
        self.ocr_lang = cfg.get("ocr_lang", "eng")
        self.template_threshold = float(cfg.get("template_threshold", 0.78))
        self.monitor_index = int(cfg.get("capture_monitor", 0))
        from src.config import resolve_path

        self.captures_dir = resolve_path(paths.get("captures_dir", "data/captures"))
        self.templates_dir = resolve_path(paths.get("templates_dir", "assets/templates"))
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._last_frame_rgb: Optional[np.ndarray] = None

    def capture_screen(self) -> np.ndarray:
        """Return RGB numpy array of the primary (or configured) monitor."""
        self._capture_ok = True
        self._capture_error = ""
        try:
            import mss
            from PIL import Image

            with mss.mss() as sct:
                monitors = sct.monitors
                idx = min(max(self.monitor_index, 0), len(monitors) - 1)
                # monitors[0] is virtual all; prefer monitors[1] when index 0 requested
                mon = monitors[1] if idx == 0 and len(monitors) > 1 else monitors[idx]
                shot = sct.grab(mon)
                img = Image.frombytes("RGB", shot.size, shot.rgb)
                frame = np.array(img)
        except Exception as exc:
            self._capture_ok = False
            self._capture_error = str(exc)
            # Headless / restricted environments: synthetic frame
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            frame[:] = (32, 40, 48)
        self._last_frame_rgb = frame
        return frame

    @property
    def last_capture_ok(self) -> bool:
        return bool(getattr(self, "_capture_ok", True))

    @property
    def last_capture_error(self) -> str:
        return str(getattr(self, "_capture_error", ""))

    @property
    def last_frame(self) -> Optional[np.ndarray]:
        return self._last_frame_rgb

    def save_capture(
        self,
        frame: Optional[np.ndarray] = None,
        label: str = "capture",
        boxes: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        import cv2

        img = frame if frame is not None else self.capture_screen()
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        if boxes:
            for box in boxes:
                x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
                cv2.rectangle(bgr, (x, y), (x + w, y + h), (0, 180, 80), 2)
                cv2.putText(
                    bgr,
                    str(box.get("label", "")),
                    (x, max(20, y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 180, 80),
                    1,
                    cv2.LINE_AA,
                )
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
        path = self.captures_dir / f"{safe_label}_{stamp}.png"
        cv2.imwrite(str(path), bgr)
        return str(path)

    def find_text(self, query: str, frame: Optional[np.ndarray] = None) -> DetectionResult:
        """Locate on-screen text via Tesseract OCR and return center coordinates."""
        import cv2

        img = frame if frame is not None else self.capture_screen()
        query_l = query.strip().lower()
        if not query_l:
            return DetectionResult(found=False, label=query, method="ocr")

        try:
            import pytesseract
            from pytesseract import Output

            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            # Mild denoise helps OCR on noisy desktop captures
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            data = pytesseract.image_to_data(
                gray, lang=self.ocr_lang, output_type=Output.DICT
            )
        except Exception:
            return DetectionResult(found=False, label=query, method="ocr", confidence=0.0)

        boxes: List[Dict[str, Any]] = []
        n = len(data.get("text", []))
        words: List[Dict[str, Any]] = []
        for i in range(n):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i])
            except (ValueError, TypeError):
                conf = -1.0
            if conf < 35:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            item = {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "label": text,
                "conf": conf,
                "line": data.get("line_num", [0] * n)[i],
                "block": data.get("block_num", [0] * n)[i],
            }
            boxes.append(item)
            words.append(item)

        best: Optional[DetectionResult] = None

        def consider(label: str, x: int, y: int, w: int, h: int, conf: float) -> None:
            nonlocal best
            cx, cy = x + w // 2, y + h // 2
            candidate = DetectionResult(
                found=True,
                x=cx,
                y=cy,
                width=w,
                height=h,
                label=label,
                method="ocr",
                confidence=max(0.0, min(1.0, conf / 100.0)),
                boxes=boxes,
            )
            if best is None or candidate.confidence > best.confidence:
                best = candidate

        # Single-word matches
        for item in words:
            text_l = item["label"].lower()
            if query_l in text_l or text_l in query_l:
                consider(item["label"], item["x"], item["y"], item["w"], item["h"], item["conf"])

        # Multi-word / phrase matches by joining same-line neighbors
        if " " in query_l and words:
            # Group by block+line
            lines: Dict[Tuple[Any, Any], List[Dict[str, Any]]] = {}
            for item in words:
                key = (item.get("block"), item.get("line"))
                lines.setdefault(key, []).append(item)
            for group in lines.values():
                group.sort(key=lambda w: w["x"])
                joined = " ".join(w["label"] for w in group)
                if query_l in joined.lower():
                    x0 = group[0]["x"]
                    y0 = min(w["y"] for w in group)
                    x1 = group[-1]["x"] + group[-1]["w"]
                    y1 = max(w["y"] + w["h"] for w in group)
                    avg_conf = sum(w["conf"] for w in group) / max(1, len(group))
                    consider(joined, x0, y0, x1 - x0, y1 - y0, avg_conf)
                else:
                    # Sliding window of consecutive words
                    for i in range(len(group)):
                        for j in range(i + 1, len(group) + 1):
                            chunk = group[i:j]
                            phrase = " ".join(w["label"] for w in chunk)
                            if query_l == phrase.lower() or query_l in phrase.lower():
                                x0 = chunk[0]["x"]
                                y0 = min(w["y"] for w in chunk)
                                x1 = chunk[-1]["x"] + chunk[-1]["w"]
                                y1 = max(w["y"] + w["h"] for w in chunk)
                                avg_conf = sum(w["conf"] for w in chunk) / max(1, len(chunk))
                                consider(phrase, x0, y0, x1 - x0, y1 - y0, avg_conf)

        if best:
            best.boxes = boxes
            return best
        return DetectionResult(found=False, label=query, method="ocr", boxes=boxes)

    def find_template(
        self, template_name: str, frame: Optional[np.ndarray] = None
    ) -> DetectionResult:
        """Match a template image from assets/templates against the screen."""
        import cv2

        img = frame if frame is not None else self.capture_screen()
        path = Path(template_name)
        if not path.is_file():
            path = self.templates_dir / template_name
        if not path.is_file():
            # try with common extensions
            for ext in (".png", ".jpg", ".jpeg", ".bmp"):
                candidate = self.templates_dir / f"{template_name}{ext}"
                if candidate.is_file():
                    path = candidate
                    break
        if not path.is_file():
            return DetectionResult(found=False, label=template_name, method="template")

        template = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if template is None:
            return DetectionResult(found=False, label=template_name, method="template")
        screen_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        th, tw = template.shape[:2]
        if max_val < self.template_threshold:
            return DetectionResult(
                found=False,
                label=template_name,
                method="template",
                confidence=float(max_val),
            )
        x, y = max_loc[0] + tw // 2, max_loc[1] + th // 2
        box = {"x": max_loc[0], "y": max_loc[1], "w": tw, "h": th, "label": template_name}
        return DetectionResult(
            found=True,
            x=x,
            y=y,
            width=tw,
            height=th,
            label=template_name,
            method="template",
            confidence=float(max_val),
            boxes=[box],
        )

    def locate(
        self,
        element: str,
        prefer: str = "ocr",
        frame: Optional[np.ndarray] = None,
    ) -> DetectionResult:
        img = frame if frame is not None else self.capture_screen()
        if prefer == "template":
            hit = self.find_template(element, img)
            if hit.found:
                return hit
            return self.find_text(element, img)
        hit = self.find_text(element, img)
        if hit.found:
            return hit
        return self.find_template(element, img)
