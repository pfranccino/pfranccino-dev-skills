# agent-checks

Two scripts that turn Gradle output into a short JSON summary, so agents, people and CI read the same few lines instead of a full log. They belong in the Android repository, at `tools/agent-checks/`, where the kit's agents look for them first. The install script copies them there (`--with-repo-tools`, or `-WithRepoTools` on Windows).

Standard library only, Python 3.8 or later.

## gradle_summary.py

Runs a Gradle command, saves the full log, and prints a summary with the failed tasks and the compiler or resource errors as file, line and message. It exits with Gradle's own exit code.

```
python3 tools/agent-checks/gradle_summary.py -- ./gradlew :feature:orders:compileDebugKotlin :feature:orders:testDebugUnitTest
python tools\agent-checks\gradle_summary.py -- .\gradlew.bat :feature:orders:testDebugUnitTest
```

Options: `--out DIR` for the log folder (default `build/agent-checks`), `--max N` for the number of errors listed (default 20).

## test_summary.py

Reads the JUnit XML reports of a module and prints each failing test with its message and the first stack frame in the project's own code. Exit code 0 when every test passed, 1 when some failed, 2 when there are no reports.

```
python3 tools/agent-checks/test_summary.py --module feature/orders
```

Options: `--results DIR` (repeatable) to read specific report folders, `--max N`.

## Summary fields

Both scripts print the same top-level fields:

| Field | Meaning |
| :--- | :--- |
| `schema_version` | Format version of the summary, currently 1 |
| `source_revision` | `head` commit and whether the working tree was `dirty` |
| `command` | The command that ran (`null` for test_summary) |
| `tool_versions` | Script and Python versions |
| `status` | `passed`, `failed` or `no_results` |
| `exit_code` | The command's exit code, or the script's for test_summary |
| `failures` | The recognized errors or failing tests, up to `--max` |
| `raw_log_path` | gradle_summary only: the full log, kept as evidence |
| `note` | What to do when nothing was recognized, or a caution |

When a command fails and no error line is recognized, `failures` is empty and `note` says to read the raw log. A summary never claims more than the log shows.

## In CI

The same commands work in CI. Keep the summary as a build artifact next to the raw log, and fail the job on the exit code, not on the summary.

## Tests

```
python -m unittest discover -s tests
```
