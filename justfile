

push commit_message:
    @git add .
    @git commit -am "{{ commit_message }}"
    @git push

install:
    @uv sync --all-groups


fmt:
    @uv run ruff check --fix .
    @ruff format .