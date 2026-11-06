"""
Image Processor module.
Implements core image operations matching ImageJ 1.54 ImageProcessor:
filters (Gaussian, Median, Sharpen, Sobel), brightness/contrast adjustment,
color type conversion, and IO.
"""

from typing import Optional, Tuple
import os
import cv2
import numpy as np
from PIL import Image
import tifffile


class ImageDocument:
    """
    Encapsulates an image in PyImageJ Studio (similar to ImagePlus in ImageJ).
    """

    def __init__(self, file_path: Optional[str] = None):
        self.file_path: Optional[str] = file_path
        self.title: str = os.path.basename(file_path) if file_path else "Untitled"
        self.original_image: Optional[np.ndarray] = None  # RGB or Grayscale
        self.current_image: Optional[np.ndarray] = None
        self.history: list = []

        if file_path:
            self.load(file_path)

    def load(self, file_path: str) -> bool:
        self.file_path = file_path
        self.title = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext in [".tif", ".tiff"]:
                img = tifffile.imread(file_path)
            else:
                img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
                if img is not None and img.ndim == 3 and img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            if img is None:
                pil_img = Image.open(file_path)
                img = np.array(pil_img)

            self.original_image = img
            self.current_image = img.copy()
            self.history = [self.current_image.copy()]
            return True
        except Exception as e:
            print(f"Error loading image {file_path}: {e}")
            return False

    def save(self, file_path: str) -> bool:
        if self.current_image is None:
            return False
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".tif", ".tiff"]:
                tifffile.imwrite(file_path, self.current_image)
            else:
                if self.current_image.ndim == 3 and self.current_image.shape[2] == 3:
                    out = cv2.cvtColor(self.current_image, cv2.COLOR_RGB2BGR)
                else:
                    out = self.current_image
                cv2.imwrite(file_path, out)
            return True
        except Exception as e:
            print(f"Error saving image: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self.current_image is not None

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.current_image.shape if self.current_image is not None else (0, 0)

    @property
    def width(self) -> int:
        return self.shape[1] if self.is_loaded else 0

    @property
    def height(self) -> int:
        return self.shape[0] if self.is_loaded else 0

    def get_grayscale(self) -> np.ndarray:
        if not self.is_loaded:
            return np.zeros((1, 1), dtype=np.uint8)
        if self.current_image.ndim == 2:
            return self.current_image
        return cv2.cvtColor(self.current_image, cv2.COLOR_RGB2GRAY)

    def push_undo(self):
        if self.current_image is not None:
            self.history.append(self.current_image.copy())
            if len(self.history) > 15:
                self.history.pop(0)

    def undo(self) -> bool:
        if len(self.history) > 1:
            self.history.pop()  # remove current
            self.current_image = self.history[-1].copy()
            return True
        return False

    def apply_filter(self, filter_name: str, **kwargs):
        if not self.is_loaded:
            return
        self.push_undo()
        fn = filter_name.lower()
        img = self.current_image

        if fn == "gaussian":
            sigma = kwargs.get("sigma", 1.5)
            ksize = int(2 * round(3 * sigma) + 1)
            self.current_image = cv2.GaussianBlur(img, (ksize, ksize), sigma)
        elif fn == "median":
            ksize = kwargs.get("ksize", 3)
            if ksize % 2 == 0:
                ksize += 1
            self.current_image = cv2.medianBlur(img, ksize)
        elif fn == "sharpen":
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            self.current_image = cv2.filter2D(img, -1, kernel)
        elif fn == "find_edges":
            gray = self.get_grayscale()
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            grad = np.hypot(sobelx, sobely)
            grad = (grad / (grad.max() + 1e-6) * 255).astype(np.uint8)
            self.current_image = grad
        elif fn == "invert":
            self.current_image = 255 - img

    def adjust_brightness_contrast(self, brightness: int = 0, contrast: float = 1.0):
        """
        brightness: -100 to 100
        contrast: 0.1 to 3.0
        """
        if not self.is_loaded:
            return
        self.push_undo()
        # g(x) = alpha * f(x) + beta
        adjusted = cv2.convertScaleAbs(self.current_image, alpha=contrast, beta=brightness)
        self.current_image = adjusted
