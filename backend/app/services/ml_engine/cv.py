import pandas as pd
import numpy as np

class PurgedWalkForwardCV:
    def __init__(self, n_splits=5, train_size=252, test_size=63, purge=1, embargo=2):
        self.n_splits = n_splits
        self.train_size = train_size
        self.test_size = test_size
        self.purge = purge
        self.embargo = embargo

    def split(self, X, y=None, groups=None):
        n = len(X)
        indices = np.arange(n)
        for i in range(self.n_splits):
            test_end = n - i * self.test_size
            test_start = test_end - self.test_size
            train_end = test_start - self.purge - self.embargo
            train_start = train_end - self.train_size

            if train_start < 0:
                break
                
            yield indices[train_start:train_end], indices[test_start:test_end]
