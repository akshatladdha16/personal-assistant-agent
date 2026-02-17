Dependencies decisions:
uv: written in rust , and much faster than pip. It creates uv.lock file that locks the dependencies with correct versioning. replaces requiremnets file with pyproject.toml. 
agent: langgraph as it creates cycles. real agents need looping throigh each action and observe it before finalizing the result. built in checkpointers that mkaes sure the state is intact if agent crashes in mid. 
Db : Supabase for postgresql.


Architecture decisions:
