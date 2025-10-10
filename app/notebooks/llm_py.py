from asyncio import run
from collections import namedtuple
from textwrap import dedent
from contextlib import asynccontextmanager
from random import Random
import os

from aiosqlite import connect
from fastapi.security import http
from httpx import AsyncClient
import typeset
from requests import get


def _set_env_from_file(var: str, file_path: str = "../keys/openai.txt"):
    """
    Reads an API key from a specified file and sets it as an environment variable.
    """
    if not os.environ.get(var):
        try:
            # The 'with open' statement ensures the file is closed automatically
            with open(file_path, 'r') as f:
                # Read the first line and strip any leading/trailing whitespace
                key = f.readline().strip()

            if key:
                os.environ[var] = key
                print(f"Successfully loaded {var} from {file_path}")
            else:
                print(f"Warning: {file_path} is empty.")

        except FileNotFoundError:
            print(f"Error: Key file not found at {file_path}. Please create the file.")

# --- Execution ---
# Set the environment variable OPENAI_API_KEY from the file
_set_env_from_file('OPENAI_API_KEY')


class Employee(namedtuple('EmployeeBase', 'name salary')):
    @classmethod
    def from_random(cls,name,*,random_state=None):
        rnd = random_state if random_state is not None else Random()
        return cls(
            name=name,
            salary=50_000 + round(rnd.uniform(0,100_000),-3)
        )


@asynccontextmanager
async def dummy_data(db,*,random_state=None):
    rnd= random_state if random_state is not None else Random()
    employees = [
        Employee.from_random(name=name, random_state=rnd)
        for name in 'Alice Bob Charlie Dana Evaan Frank Gina Harry'.split()
    ]
    create_table = dedent('''
     create table if not exists employees(
            name text
            ,salary real
            );
    ''').strip()
    insert = dedent('''
    insert into employees (name,salary) values (:name,:salary)
    ''').strip()

    await db.execute(create_table)
    await db.executemany(insert, (x._asdict() for x in employees))
    yield


async def main(
        root_url ="https://api.openai.com/v1",
        openai_api_key=os.environ['OPENAI_API_KEY'],
):
    async with connect(":memory:") as db, AsyncClient() as client:
        async with dummy_data(db=db):
            print(f"{db =}")
            print(f"{client =}")

            # async for row in await db.execute('select * from employees'):
            #     print(f'{row=}')
            url=f'{root_url}/responses'
            headers ={
                'Authorization': f'Bearer {openai_api_key}',
                'Content-Type': 'application/json',
            }
            json={
                'model' : 'gpt-4o',
                'input': 'What is 1+1',
                'instructions': 'Answer in specified question by writing SQL',
            }

            resp = (await client.post(url,headers=headers,json=json)).json()
            answer =resp['outputs'][0]['text']
            print({f'{answer=}'})




if __name__ == "__main__":
    run(main())