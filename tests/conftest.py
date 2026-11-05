"""Makes tests/ importable (csrf_helpers) under any pytest import mode."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
