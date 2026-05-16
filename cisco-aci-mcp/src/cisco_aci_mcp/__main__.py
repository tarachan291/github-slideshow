"""Entry point: python -m cisco_aci_mcp"""

import asyncio
from .server import main

asyncio.run(main())
