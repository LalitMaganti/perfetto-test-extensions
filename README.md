# Perfetto Server Extensions

Server extensions let you share reusable SQL modules and UI macros through the
[Perfetto UI](https://ui.perfetto.dev) — with your team or the open source
community. Instead of everyone copy-pasting SQL queries or macro definitions,
you host them on a server and anyone with access can load them directly in the
UI.

Extension servers can be any HTTPS endpoint that serves the expected JSON
format. This repo is a template for the easiest option: hosting on GitHub. For
the full endpoint specification and other hosting options, see the
[Server Extensions RFC](https://github.com/google/perfetto/discussions/3227).

## Getting started

1. [Fork this repo](https://github.com/LalitMaganti/perfetto-test-extensions/fork), or [import it](https://github.com/new/import) if you want a private copy.

2. Edit `config.yaml` to set your extension's name and namespace:
   ```yaml
   name: My Extension
   namespace: com.example.myext
   ```

3. Add [SQL modules](https://perfetto.dev/docs/analysis/perfetto-sql-getting-started) as `.sql` files under `src/{module}/sql_modules/`.

   The filename determines the module name. For example, with namespace `com.example.myext`:
   - `src/default/sql_modules/helpers.sql` → `INCLUDE PERFETTO MODULE com.example.myext.helpers;`
   - `src/default/sql_modules/foo/bar.sql` → `INCLUDE PERFETTO MODULE com.example.myext.foo.bar;`

   You can organise SQL files into subdirectories — each path component becomes a dot-separated part of the module name.

4. Add [UI macros](https://perfetto.dev/docs/visualization/ui-automation) as `.yaml` files under `src/{module}/macros/`.

5. Push to `main`. A GitHub Action will build and commit the generated endpoint files automatically.

## Connecting to the Perfetto UI

1. Go to [Perfetto UI extension settings](https://ui.perfetto.dev/#!/settings/dev.perfetto.ExtensionServers).

2. Add your repo as a GitHub extension server.

### Private repos

If your repo is private, you'll need a GitHub personal access token:

1. Go to [GitHub personal access tokens](https://github.com/settings/personal-access-tokens) and click **Generate new token**.
2. Under **Repository access**, select **Only select repositories** and choose your extension repo.
3. Under **Permissions → Repository permissions**, set **Contents** to **Read-only**.
4. Generate the token and enter it in the Perfetto UI extension settings when adding your server.

