from asyncio import Queue, sleep, wait_for
from json import dumps
from logging import getLogger

from template_cli.tracker import contributing_tasks

logger = getLogger()


async def json_out(q: Queue) -> None:
    endl = ''  # start with nothing prepended
    print('[')
    while not contributing_tasks:
        logger.debug(f'CONTRIBUTING TASKS: Waiting to begin: {contributing_tasks=}')
        await sleep(1)
    while contributing_tasks:
        try:
            result_coroutine = q.get()
            result = await wait_for(result_coroutine, 1)
            if result:
                print(f'{endl}{dumps(result, indent=4)}', end='')
                endl = ',\n'  # prepend to this line the previous line's endl (no trailing ',' for JSON correctness)
        except TimeoutError:
            logger.debug(f'CONTRIBUTING TASKS: Timeout: {contributing_tasks=}')
    print('\n]')
    q.task_done()
