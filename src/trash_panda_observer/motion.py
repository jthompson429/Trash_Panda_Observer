"""Understandable running-background motion detection."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class MotionResult:
    total_area: int
    largest_area: float
    qualifying: bool
    triggered: bool


class MotionDetector:
    def __init__(
        self,
        *,
        pixel_threshold: int,
        minimum_total_area: int,
        minimum_largest_area: int,
        consecutive_frames: int,
        blur_kernel: int,
        morphology_kernel: int,
        background_alpha: float,
        roi: list[float] | None = None,
    ) -> None:
        if blur_kernel < 1 or blur_kernel % 2 == 0:
            raise ValueError("blur kernel must be a positive odd integer")
        if morphology_kernel < 1:
            raise ValueError("morphology kernel must be positive")
        if not 0 < background_alpha <= 1:
            raise ValueError("background alpha must be in (0, 1]")
        if consecutive_frames < 1:
            raise ValueError("consecutive frames must be positive")
        self.pixel_threshold = pixel_threshold
        self.minimum_total_area = minimum_total_area
        self.minimum_largest_area = minimum_largest_area
        self.consecutive_frames = consecutive_frames
        self.blur_kernel = blur_kernel
        self.kernel = np.ones((morphology_kernel, morphology_kernel), np.uint8)
        self.background_alpha = background_alpha
        self.roi = roi
        self.background: np.ndarray | None = None
        self.streak = 0

    def reset_streak(self) -> None:
        self.streak = 0

    def _crop(self, frame: np.ndarray) -> np.ndarray:
        if self.roi is None:
            return frame
        if len(self.roi) != 4 or any(not 0 <= value <= 1 for value in self.roi):
            raise ValueError("ROI must be four normalized values between 0 and 1")
        x, y, width, height = self.roi
        if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ValueError("ROI rectangle must fit within the frame")
        rows, columns = frame.shape[:2]
        return frame[
            round(y * rows) : round((y + height) * rows),
            round(x * columns) : round((x + width) * columns),
        ]

    def process(self, grayscale: np.ndarray) -> MotionResult:
        frame = self._crop(grayscale)
        blurred = cv2.GaussianBlur(
            frame, (self.blur_kernel, self.blur_kernel), 0
        )
        if self.background is None:
            self.background = blurred.astype(np.float32)
            return MotionResult(0, 0.0, False, False)

        difference = cv2.absdiff(blurred, cv2.convertScaleAbs(self.background))
        _ignored, mask = cv2.threshold(
            difference, self.pixel_threshold, 255, cv2.THRESH_BINARY
        )
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.dilate(mask, self.kernel, iterations=1)
        contours, _hierarchy = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        areas = [cv2.contourArea(contour) for contour in contours]
        total = int(cv2.countNonZero(mask))
        largest = max(areas, default=0.0)
        qualifying = (
            total >= self.minimum_total_area
            and largest >= self.minimum_largest_area
        )
        self.streak = self.streak + 1 if qualifying else 0
        triggered = self.streak == self.consecutive_frames
        cv2.accumulateWeighted(blurred, self.background, self.background_alpha)
        return MotionResult(total, largest, qualifying, triggered)
