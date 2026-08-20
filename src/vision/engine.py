"""Screen capture, OCR text locate, and template matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.vision.search_result import (
    FIRST_RESULT_ELEMENT,
    is_first_result_phrase,
    pick_first_search_result,
    text_matches_query,
)


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
        self.last_region = {"left": 0, "top": 0, "width": 0, "height": 0}

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
                self.last_region = {
                    "left": int(mon.get("left") or 0),
                    "top": int(mon.get("top") or 0),
                    "width": int(frame.shape[1]),
                    "height": int(frame.shape[0]),
                }
        except Exception as exc:
            self._capture_ok = False
            self._capture_error = str(exc)
            # Headless / restricted environments: synthetic frame
            frame = np.zeros((540, 960, 3), dtype=np.uint8)
            frame[:] = (32, 40, 48)
            self.last_region = {"left": 0, "top": 0, "width": 960, "height": 540}
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

    def _ocr_words(self, img) -> List[Dict[str, Any]]:
        import cv2

        try:
            import pytesseract
            from pytesseract import Output
        except Exception:
            return []
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        try:
            data = pytesseract.image_to_data(
                gray, lang=self.ocr_lang, output_type=Output.DICT
            )
        except Exception:
            return []
        words: List[Dict[str, Any]] = []
        n = len(data.get("text", []))
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
            words.append(
                {
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                    "label": text,
                    "conf": conf,
                    "line": data.get("line_num", [0] * n)[i],
                    "block": data.get("block_num", [0] * n)[i],
                }
            )
        return words

    def find_text(self, query: str, frame: Optional[np.ndarray] = None) -> DetectionResult:
        """Locate on-screen text via Tesseract OCR and return center coordinates."""
        img = frame if frame is not None else self.capture_screen()
        query_l = query.strip().lower()
        if not query_l:
            return DetectionResult(found=False, label=query, method="ocr")
        if is_first_result_phrase(query_l):
            return self.find_first_search_result(img)

        words = self._ocr_words(img)
        boxes = list(words)
        if not words:
            return DetectionResult(found=False, label=query, method="ocr", confidence=0.0, boxes=boxes)

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

        for item in words:
            if text_matches_query(item["label"], query_l):
                consider(item["label"], item["x"], item["y"], item["w"], item["h"], item["conf"])

        if " " in query_l and words:
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

    def find_first_search_result(self, frame: Optional[np.ndarray] = None) -> DetectionResult:
        img = frame if frame is not None else self.capture_screen()
        words = self._ocr_words(img)
        h, w = img.shape[:2]
        hit = pick_first_search_result(words, w, h)
        if not hit:
            return DetectionResult(
                found=False, label="first result", method="first-result", boxes=list(words)
            )
        return DetectionResult(
            found=True,
            x=int(hit["x"] + hit["w"] // 2),
            y=int(hit["y"] + hit["h"] // 2),
            width=int(hit["w"]),
            height=int(hit["h"]),
            label=str(hit.get("label") or "first result"),
            method="first-result",
            confidence=0.86,
            boxes=list(words) + [hit],
        )

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
        if is_first_result_phrase(element) or element == FIRST_RESULT_ELEMENT:
            return self.find_first_search_result(img)
        if prefer == "template":
            hit = self.find_template(element, img)
            if hit.found:
                return hit
            return self.find_text(element, img)
        hit = self.find_text(element, img)
        if hit.found:
            return hit
        return self.find_template(element, img)

    def frame_changed(
        self,
        before,
        after,
        *,
        threshold: float = 0.018,
    ) -> Dict[str, Any]:
        """Compare two RGB frames; used to verify that a click/open actually changed the UI."""
        import numpy as np

        if before is None or after is None:
            return {"changed": True, "score": 1.0, "note": "missing frame"}
        a = np.asarray(before)
        b = np.asarray(after)
        if a.shape != b.shape:
            return {"changed": True, "score": 1.0, "note": "size changed"}
        diff = float(np.mean(np.abs(a.astype("float32") - b.astype("float32"))) / 255.0)
        return {"changed": diff >= threshold, "score": round(diff, 4), "note": ""}

    def ocr_preview(self, frame=None, max_boxes: int = 24) -> DetectionResult:
        """Run OCR for the AI Agent screen-understanding panel."""
        img = frame if frame is not None else self.capture_screen()
        dummy = self.find_text("___no_match___", frame=img)
        dummy.found = bool(dummy.boxes)
        dummy.boxes = (dummy.boxes or [])[:max_boxes]
        dummy.label = f"{len(dummy.boxes)} OCR boxes"
        dummy.method = "ocr-preview"
        return dummy
