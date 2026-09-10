"""Refresh worker using candidate-first cybersecurity scoring.

This intentionally leaves the existing worker.py untouched for safe rollback.
Once v2 is validated, the import can be merged into worker.py directly.
"""

import engine as eng
import match_v2
import worker

# Replace only the scoring/classification hook used by worker.refresh().
eng.process = match_v2.process_v2


if __name__ == "__main__":
    worker.refresh()
