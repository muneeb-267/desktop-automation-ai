import numpy as np

from src.vision.engine import VisionEngine


def test_frame_changed_detects_difference():
    vis = VisionEngine({})
    a = np.zeros((40, 40, 3), dtype=np.uint8)
    b = np.zeros((40, 40, 3), dtype=np.uint8)
    b[:] = 255
    hit = vis.frame_changed(a, b, threshold=0.01)
    assert hit["changed"] is True
    same = vis.frame_changed(a, a, threshold=0.01)
    assert same["changed"] is False
