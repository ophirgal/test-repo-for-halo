"""``python3 -m newsletter export [-o FILE]`` — see ``newsletter.export``."""

import sys

from .export import main

sys.exit(main())
