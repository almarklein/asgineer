"""
This module provides compatibility for different async libs. Currently
only supporting asyncio, but should not be too hard to add e.g. Trio,
once Uvicorn has Trio support.
"""

import asyncio


async def sleep(seconds):
    """ An async sleep function. Uses asyncio. Can be extended to support Trio
    once we support that.
    """

    if True:  # if asyncio
        await asyncio.sleep(seconds)


Event = asyncio.Event


async def wait_for_any_then_cancel_the_rest(*coroutines):
    """ Wait for any of the given coroutines to complete (or fail), and then
    cancels all the other co-routines.
    """
    # Note: ensure_future == create_task. Less readable, but py36 compatible.
    if True:  # if asyncio
        tasks = [asyncio.ensure_future(co) for co in coroutines]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
