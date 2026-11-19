# agent-checks

Two scripts that turn Gradle output into a short JSON summary, so agents, people and CI read the same few lines instead of a full log. They belong in the Android repository, at `tools/agent-checks/`, where the kit's agents look for them first. The install script copies them there (`--with-repo-tools`, or `-WithRepoTools` on Windows).

Standard library only, Python 3.8 or later.

## gradle_summary.py

Runs a Gradle command, saves the full log, and prints a summary with the failed tasks and the compiler or resource errors as file, line and message. It exits with Gradle's own exit code, or 124 when it stopped the command for taking too long.

When the command is a bare `./gradlew` and the working directory has none, the script looks for it in the parent folders, up to the repository root, and runs Gradle from there. A wrapper path such as `./android/gradlew` runs as given.

```
python3 tools/agent-checks/gradle_summary.py -- ./gradlew :feature:orders:compileDebugKotlin :feature:orders:testDebugUnitTest
python tools\agent-checks\gradle_summary.py -- .\gradlew.bat :feature:orders:testDebugUnitTest
```

Options: `--out DIR` for the log folder (default `build/agent-checks`), `--max N` for the number of errors listed (default 20), and `--timeout MIN` to stop the command and its child processes after that many minutes. Connected tasks (`connected*`) stop after 9 minutes unless `--timeout` says otherwise, and `--timeout 0` turns the limit off. On Linux and macOS the command runs in its own process group, and the timeout stops the whole group, as does stopping the script itself; on Windows the timeout stops the process tree. A Gradle daemon that was already running is not part of either and keeps running.

An agent's shell call has its own limit: 2 minutes by default and 10 at most in Claude Code. Give Gradle runs the longest one (600000 ms), so the script stops a hang and prints its summary before the shell call is cut.

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
| `schema_version` | Format version of the summary, currently 2 |
| `source_revision` | `head` commit and whether the working tree was `dirty` |
| `command` | The command that ran (`null` for test_summary) |
| `tool_versions` | Script and Python versions |
| `status` | `passed` or `failed`; `timeout` for gradle_summary; `no_results` or `incomplete` for test_summary |
| `exit_code` | The command's exit code, or the script's for test_summary |
| `failures` | The recognized errors or failing tests, up to `--max` |
| `raw_log_path` | gradle_summary only: the full log, kept as evidence |
| `working_directory`, `timeout_minutes` | gradle_summary only: where Gradle ran, and the time limit applied (`null` for none) |
| `next_step` | The kit agent that diagnoses the result: `test-analyst` when only test tasks failed, `build-doctor` for any other failure or a timeout, `null` when nothing failed |
| `note` | What to do when nothing was recognized, or a caution |

When a command fails and no error line is recognized, `failures` is empty and `note` says to read the raw log. A summary never claims more than the log shows.

## In CI

The same commands work in CI. Keep the summary as a build artifact next to the raw log, and fail the job on the exit code, not on the summary.

## Tests

```
python -m unittest discover -s tests
```
