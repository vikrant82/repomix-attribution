"""Allow ``python -m repomix_attribution`` to run the CLI."""

import sys

from repomix_attribution.cli import main

sys.exit(main())
