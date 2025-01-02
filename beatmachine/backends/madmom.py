import glob
import typing as t

import numpy as np
from madmom.audio import Signal
from madmom.features.beats import DBNBeatTrackingProcessor, RNNBeatProcessor
import os
import site

# Look for models in the site-packages directory
SITE_PACKAGES = site.getsitepackages()[0]
MADMOM_MODEL_PATH = os.path.join(SITE_PACKAGES, 'madmom', 'models')


class MadmomDbnBackend:
    def __init__(self, min_bpm: int = 55, max_bpm: int = 215, fps: int = 100, model_count: int = 1) -> None:
        super().__init__()
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.fps = fps
        self.model_count = model_count
        
        # Initialize processors
        self.processor = RNNBeatProcessor(online=True, fps=self.fps)
        self.tracker = DBNBeatTrackingProcessor(min_bpm=self.min_bpm, max_bpm=self.max_bpm, fps=self.fps)

    def locate_beats(self, signal: np.ndarray, sample_rate: int) -> np.ndarray:
        madmom_signal = Signal(signal, sample_rate=sample_rate)
        activations = self.processor(madmom_signal)
        beats = self.tracker(activations)
        return (beats * madmom_signal.sample_rate).astype(np.int64)
